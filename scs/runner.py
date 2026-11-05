"""Experiment runner (OWNER: Agent B).  See docs/INTERFACES.md sections 9-13.

Pipeline per instance: preprocess -> overlap matrix (timed separately) ->
greedy (every policy, random policy ``random_tie_runs`` times) -> exact DP once
(child process, timeout, memory guard) -> validation against the ORIGINAL
inputs -> one JSON row per (instance, algorithm, policy, tie_run), appended and
flushed (checkpointing).  Traces are produced by a separate, untimed call.
"""
from __future__ import annotations

import atexit
import dataclasses
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .schema import Instance
from .seeds import derive_seed, sha256_strings, sha256_text
from . import generators
from .sysinfo import git_version, sysinfo

RUNNER_VERSION = "1.0"
TERMINAL = {"ok", "timeout", "memory_limit", "skipped_n_too_large", "error"}
DEFAULT_POLICIES = ["lowest_id", "highest_id", "lex_merged", "random"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# validation (lazy import of Agent C's module, with a clearly marked fallback)
# ---------------------------------------------------------------------------

def check_superstring(original, superstring) -> list[str]:
    """Return the original strings missing from ``superstring``."""
    try:
        from .validate import check_superstring as _cs  # Agent C's validator
        return _cs(original, superstring)
    except ImportError:
        # FALLBACK (used only if scs/validate.py does not exist): plain containment.
        return [s for s in original if s not in superstring]


# ---------------------------------------------------------------------------
# config handling / instance expansion
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg.setdefault("greedy_policies", list(DEFAULT_POLICIES))
    cfg.setdefault("random_tie_runs", 5)
    cfg.setdefault("include_known", True)
    cfg.setdefault("trace_instances", 5)
    cfg.setdefault("workers", 1)
    ex = cfg.setdefault("exact", {})
    ex.setdefault("enabled", True)
    ex.setdefault("engine", "numpy")
    ex.setdefault("max_n", 16)
    ex.setdefault("timeout_s", 120)
    ex.setdefault("memory_mb", 4000)
    for k in ("name", "master_seed", "output_dir"):
        if k not in cfg:
            raise ValueError(f"config missing {k!r}")
    return cfg


def expand_instances(cfg: dict) -> list[Instance]:
    """All instances of a config in deterministic order (instance_id unique)."""
    out: list[Instance] = []
    seen: set[str] = set()
    master, name = cfg["master_seed"], cfg["name"]
    for spec in cfg.get("families", []):
        fam = spec["family"]
        grid = spec.get("grid", {})
        fixed = spec.get("fixed", {})
        keys = list(grid.keys())
        for combo in itertools.product(*[grid[k] for k in keys]):
            params = dict(fixed)
            params.update(dict(zip(keys, combo)))
            pk = generators.param_key(params)
            for rep in range(int(spec.get("reps", 1))):
                seed = derive_seed(master, "instance", name, fam, pk, rep)
                inst = generators.generate(fam, params, seed)
                inst.instance_id = f"{fam}-{hashlib.sha256(pk.encode()).hexdigest()[:8]}-r{rep}"
                inst.metadata["rep"] = rep
                out.append(inst)
    if cfg.get("include_known", True):
        out.extend(generators.known_instances())
    disc = cfg.get("include_discovered")
    if disc:
        for line in Path(disc).read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(Instance(**json.loads(line)))
    for inst in out:
        if inst.instance_id in seen:
            raise ValueError(f"duplicate instance_id {inst.instance_id}")
        seen.add(inst.instance_id)
    return out


def instance_record(inst: Instance) -> dict:
    d = dataclasses.asdict(inst)
    d["strings_sha256"] = sha256_strings(inst.strings)
    return d


def expected_keys(cfg: dict, instance_id: str) -> list[tuple]:
    keys: list[tuple] = []
    for pol in cfg["greedy_policies"]:
        if pol == "random":
            keys.extend(("greedy", pol, k) for k in range(int(cfg["random_tie_runs"])))
        else:
            keys.append(("greedy", pol, None))
    if cfg["exact"]["enabled"]:
        keys.append(("exact_dp", None, None))
    return [(instance_id,) + k for k in keys]


# ---------------------------------------------------------------------------
# exact DP in a child process (persistent worker, restarted after kill)
# ---------------------------------------------------------------------------

def _dp_child_main(conn) -> None:
    from scs import exact_dp as E  # import before announcing readiness
    conn.send("ready")
    while True:
        try:
            msg = conn.recv()
        except (EOFError, OSError):
            return
        if msg is None:
            return
        strings, overlaps, engine = msg
        try:
            fn = E.exact_dp_numpy if engine == "numpy" else E.exact_dp
            t0 = time.perf_counter()
            res = fn(strings, overlaps)
            dt = time.perf_counter() - t0
            conn.send({"ok": True, "length": res.length,
                       "superstring": res.superstring, "order": list(res.order),
                       "t_solve_s": dt})
        except BaseException as e:  # noqa: BLE001
            conn.send({"ok": False, "error": f"{type(e).__name__}: {e}"})


class DPWorker:
    """One reusable spawn-context child that runs exact DP.

    Process-level timeout (the child is killed) and RSS polling (killed above
    the memory budget).  A fresh child is started lazily after any kill, and
    also after a run that left the child holding > 1 GB.
    """

    def __init__(self) -> None:
        self.ctx = mp.get_context("spawn")
        self.proc = None
        self.conn = None
        atexit.register(self.close)

    def _start(self) -> None:
        parent, child = self.ctx.Pipe()
        self.proc = self.ctx.Process(target=_dp_child_main, args=(child,), daemon=True)
        self.proc.start()
        child.close()
        self.conn = parent
        if not self.conn.poll(120):
            self._kill()
            raise RuntimeError("DP child failed to start")
        self.conn.recv()  # "ready"

    def _kill(self) -> None:
        try:
            if self.proc is not None and self.proc.is_alive():
                self.proc.kill()
            if self.proc is not None:
                self.proc.join(10)
        except Exception:
            pass
        try:
            if self.conn is not None:
                self.conn.close()
        except Exception:
            pass
        self.proc = self.conn = None

    def close(self) -> None:
        try:
            if self.conn is not None and self.proc is not None and self.proc.is_alive():
                self.conn.send(None)
                self.proc.join(3)
        except Exception:
            pass
        self._kill()

    def run(self, strings, overlaps, engine: str, timeout_s: float,
            memory_mb: float) -> dict:
        """Returns dict(status, error, length, superstring, order, t_solve_s,
        t_wall_child_s, peak_rss_mb)."""
        import psutil
        t_req = time.perf_counter()
        fresh = self.proc is None or not self.proc.is_alive()
        if fresh:
            self._kill()
            self._start()   # spawn cost counted in t_wall_child_s, not in timeout
        t_solve_start = time.perf_counter()
        pr = psutil.Process(self.proc.pid)
        peak = 0
        self.conn.send((list(strings), overlaps, engine))
        status, payload = "ok", None
        while True:
            if self.conn.poll(0.02):
                try:
                    payload = self.conn.recv()
                except (EOFError, OSError):
                    status, payload = "error", {"error": "DP child died unexpectedly"}
                break
            try:
                rss = pr.memory_info().rss
                peak = max(peak, rss)
            except psutil.Error:
                rss = 0
            if rss > memory_mb * 1024 * 1024:
                status = "memory_limit"
                break
            if time.perf_counter() - t_solve_start > timeout_s:
                status = "timeout"
                break
            if not self.proc.is_alive() and not self.conn.poll(0):
                status, payload = "error", {"error": "DP child exited unexpectedly"}
                break
        wall = time.perf_counter() - t_req
        try:
            peak = max(peak, pr.memory_info().rss)
        except psutil.Error:
            pass
        out = {"status": status, "error": None, "length": None, "superstring": None,
               "order": None, "t_solve_s": None, "t_wall_child_s": wall,
               "peak_rss_mb": peak / 1048576.0}
        if status in ("timeout", "memory_limit"):
            out["error"] = (f"killed after {wall:.1f}s" if status == "timeout"
                            else f"RSS exceeded {memory_mb} MB")
            self._kill()
        elif status == "error" or not payload.get("ok", False):
            out["status"] = "error"
            out["error"] = (payload or {}).get("error", "unknown error")
            self._kill()
        else:
            out.update(length=payload["length"], superstring=payload["superstring"],
                       order=payload["order"], t_solve_s=payload["t_solve_s"])
            if peak > 1024 * 1024 * 1024:
                self._kill()   # release a big heap; restart lazily
        return out


_DP_WORKER: Optional[DPWorker] = None


def get_dp_worker() -> DPWorker:
    global _DP_WORKER
    if _DP_WORKER is None:
        _DP_WORKER = DPWorker()
    return _DP_WORKER


# ---------------------------------------------------------------------------
# per-instance processing
# ---------------------------------------------------------------------------

def overlap_features(M, n: int) -> dict:
    if n < 2:
        return {"frac_pos_overlap_pairs": None, "mean_overlap": None, "max_overlap": 0 if n else None}
    tot = pos = mx = 0
    for i in range(n):
        for j in range(n):
            if i != j:
                v = M[i][j]
                tot += v
                pos += v > 0
                mx = max(mx, v)
    pairs = n * (n - 1)
    return {"frac_pos_overlap_pairs": pos / pairs, "mean_overlap": tot / pairs,
            "max_overlap": mx}


def _tie_seed(cfg, instance_id, k):
    return derive_seed(cfg["master_seed"], "tie", instance_id, k)


def process_instance(task: dict) -> dict:
    """Compute all result rows of one instance.  Returns {'instance_id', 'rows'}.

    ``task``: instance (dict), cfg, code_version, need (set of keys still
    missing, as lists), trace (bool), out_dir.
    """
    from .preprocess import preprocess
    from .overlap import overlap_matrix
    from .greedy import greedy

    inst = Instance(**task["instance"])
    cfg = task["cfg"]
    need = {tuple(k) for k in task["need"]}
    code_version = task["code_version"]
    ex = cfg["exact"]
    keys_all = expected_keys(cfg, inst.instance_id)
    rows: list[dict] = []

    base = {
        "config_name": cfg["name"], "instance_id": inst.instance_id,
        "family": inst.family, "label": inst.label, "params": inst.params,
        "instance_seed": inst.seed,
    }

    def mk(algorithm, policy, tie_run, tie_seed, **kw) -> dict:
        row = dict(base)
        row.update(algorithm=algorithm, policy=policy, tie_run=tie_run,
                   tie_seed=tie_seed, status="ok", error=None)
        row.update(common)
        row.update(length=None, valid=None, superstring_sha256=None, order=None,
                   n_tie_steps=None, max_tied=None, sum_overlap=None,
                   t_solve_s=None, t_total_s=None)
        row.update(kw)
        row["code_version"] = code_version
        row["timestamp"] = _now()
        return row

    common: dict[str, Any] = {}
    try:
        t0 = time.perf_counter()
        pre = preprocess(inst.strings)
        t_pre = time.perf_counter() - t0
        retained = pre.retained
        n = len(retained)
        t0 = time.perf_counter()
        M = overlap_matrix(retained)
        t_ov = time.perf_counter() - t0
        rem = {"empty": 0, "duplicate": 0, "contained": 0}
        for r in pre.removals:
            rem[r.reason] += 1
        common = {
            "n_raw": len(inst.strings), "L_raw": sum(map(len, inst.strings)),
            "n": n, "L": sum(map(len, retained)),
            "ell": max(map(len, retained), default=0),
            "min_len": min(map(len, retained), default=0),
            "alphabet_size": len(set("".join(retained))),
            "n_removed_empty": rem["empty"], "n_removed_duplicate": rem["duplicate"],
            "n_removed_contained": rem["contained"],
            **overlap_features(M, n),
            "t_preprocess_s": t_pre, "t_overlap_s": t_ov,
        }

        def total(solve):
            return t_pre + t_ov + solve

        exact_out = None
        # ---- exact DP (once per instance) ----
        if ex["enabled"]:
            engine = ex["engine"]
            from .exact_dp import estimate_dp_memory_bytes
            est = estimate_dp_memory_bytes(n, engine)
            if n > ex["max_n"]:
                exact_out = {"status": "skipped_n_too_large",
                             "error": f"n={n} > max_n={ex['max_n']}"}
            elif est > ex["memory_mb"] * 1024 * 1024:
                exact_out = {"status": "skipped_n_too_large",
                             "error": f"estimated DP memory {est/1048576:.0f} MB > "
                                      f"budget {ex['memory_mb']} MB"}
            else:
                exact_out = get_dp_worker().run(retained, M, engine,
                                                float(ex["timeout_s"]),
                                                float(ex["memory_mb"]))
            row_kw = dict(status=exact_out["status"], error=exact_out.get("error"))
            if exact_out["status"] == "ok":
                missing = check_superstring(inst.strings, exact_out["superstring"])
                valid = (not missing) and len(exact_out["superstring"]) == exact_out["length"]
                row_kw.update(
                    length=exact_out["length"], valid=valid,
                    superstring_sha256=sha256_text(exact_out["superstring"]),
                    order=exact_out["order"], t_solve_s=exact_out["t_solve_s"],
                    t_total_s=total(exact_out["t_solve_s"]))
                if not valid:
                    row_kw.update(status="error",
                                  error=f"exact output invalid; missing={missing[:3]}")
            if "t_wall_child_s" in exact_out:
                row_kw["t_wall_child_s"] = exact_out["t_wall_child_s"]
                row_kw["peak_rss_mb"] = exact_out["peak_rss_mb"]
            row_kw["engine"] = engine
            if (inst.instance_id, "exact_dp", None, None) in need:
                rows.append(mk("exact_dp", None, None, None, **row_kw))
        opt = exact_out["length"] if exact_out and exact_out["status"] == "ok" else None

        # ---- greedy (timed, no trace) ----
        greedy_results = {}
        for pol in cfg["greedy_policies"]:
            runs = ([(k, _tie_seed(cfg, inst.instance_id, k))
                     for k in range(int(cfg["random_tie_runs"]))]
                    if pol == "random" else [(None, None)])
            for k, seed in runs:
                key = (inst.instance_id, "greedy", pol, k)
                if key not in need:
                    continue
                try:
                    t0 = time.perf_counter()
                    res = greedy(retained, policy=pol, seed=seed, trace=False, overlaps=M)
                    dt = time.perf_counter() - t0
                    missing = check_superstring(inst.strings, res.superstring)
                    valid = (not missing) and len(res.superstring) == res.length
                    kw = dict(status="ok", length=res.length, valid=valid,
                              superstring_sha256=sha256_text(res.superstring),
                              order=list(res.order), n_tie_steps=res.n_tie_steps,
                              max_tied=res.max_tied, sum_overlap=res.sum_overlap,
                              t_solve_s=dt, t_total_s=total(dt))
                    if not valid:
                        kw.update(status="error", error=f"greedy output invalid; missing={missing[:3]}")
                    elif opt is not None and res.length < opt:
                        kw.update(status="error",
                                  error=f"greedy length {res.length} < exact OPT {opt}")
                    greedy_results[(pol, k)] = res.length
                    rows.append(mk("greedy", pol, k, seed, **kw))
                except Exception as e:  # noqa: BLE001
                    rows.append(mk("greedy", pol, k, seed, status="error",
                                   error=f"{type(e).__name__}: {e}"))

        # ---- traces (separate, untimed) ----
        if task.get("trace"):
            _write_trace(task["out_dir"], inst, retained, M, cfg, exact_out, greedy_results)
    except Exception as e:  # noqa: BLE001  instance-level failure
        have = {(r["instance_id"], r["algorithm"], r["policy"], r["tie_run"]) for r in rows}
        for key in keys_all:
            if key in need and key not in have:
                _, alg, pol, k = key
                seed = _tie_seed(cfg, inst.instance_id, k) if (pol == "random") else None
                rows.append(mk(alg, pol, k, seed, status="error",
                               error=f"{type(e).__name__}: {e}"))
    return {"instance_id": inst.instance_id, "rows": rows}


def _write_trace(out_dir, inst, retained, M, cfg, exact_out, timed_lengths) -> None:
    from .greedy import greedy
    tr: dict[str, Any] = {"instance_id": inst.instance_id,
                          "retained": list(retained), "greedy": {}, "exact": None,
                          "consistent_with_timed_runs": True}
    for pol in cfg["greedy_policies"]:
        seed = _tie_seed(cfg, inst.instance_id, 0) if pol == "random" else None
        res = greedy(retained, policy=pol, seed=seed, trace=True, overlaps=M)
        name = f"{pol}_0" if pol == "random" else pol
        tr["greedy"][name] = dataclasses.asdict(res)
        timed = timed_lengths.get((pol, 0 if pol == "random" else None))
        if timed is not None and timed != res.length:
            tr["consistent_with_timed_runs"] = False
    if exact_out is not None:
        tr["exact"] = {k: exact_out.get(k) for k in
                       ("status", "error", "length", "order", "superstring")}
    d = Path(out_dir) / "traces"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{inst.instance_id}.json").write_text(json.dumps(tr), encoding="utf-8")


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # torn last line from an interrupted run
    return out


def run(config_path: str, resume: bool = False, workers: Optional[int] = None,
        only_family: Optional[str] = None, force: bool = False,
        retry_errors: bool = False) -> dict:
    cfg = load_config(config_path)
    if workers is not None:
        cfg["workers"] = workers
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    res_path = out_dir / "results.jsonl"
    inst_path = out_dir / "instances.jsonl"
    man_path = out_dir / "manifest.json"

    if res_path.exists() and res_path.stat().st_size > 0 and not (resume or force):
        raise SystemExit(f"{res_path} exists; use --resume to continue or --force to overwrite")
    if force and not resume:
        for p in (res_path, inst_path, man_path):
            if p.exists():
                p.unlink()
        tdir = out_dir / "traces"
        if tdir.exists():
            for p in tdir.glob("*.json"):
                p.unlink()

    instances = expand_instances(cfg)
    if only_family:
        instances = [i for i in instances if i.family == only_family]
    t_start = _now()
    code_version = git_version()

    # instances.jsonl (merge with existing records when resuming)
    recs: dict[str, dict] = {}
    if resume:
        for r in _read_jsonl(inst_path):
            recs[r["instance_id"]] = r
    for inst in instances:
        recs[inst.instance_id] = instance_record(inst)
    tmp = inst_path.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in recs.values()), encoding="utf-8")
    os.replace(tmp, inst_path)

    # resume bookkeeping
    existing = _read_jsonl(res_path)
    n_lines = (sum(1 for ln in res_path.read_text(encoding="utf-8").splitlines()
                   if ln.strip()) if res_path.exists() else 0)
    torn = len(existing) != n_lines       # a partially written last line
    if retry_errors:
        existing = [r for r in existing if r["status"] != "error"]
    if retry_errors or torn:
        res_path.write_text("".join(json.dumps(r) + "\n" for r in existing), encoding="utf-8")
    done = {(r["instance_id"], r["algorithm"], r["policy"], r["tie_run"])
            for r in existing if r["status"] in TERMINAL}

    # trace selection: first trace_instances per family + all known
    trace_ids: set[str] = set()
    per_fam: dict[str, int] = {}
    for inst in instances:
        c = per_fam.get(inst.family, 0)
        if inst.family == "known" or c < int(cfg["trace_instances"]):
            trace_ids.add(inst.instance_id)
        per_fam[inst.family] = c + 1

    tasks = []
    for inst in instances:
        need = [k for k in expected_keys(cfg, inst.instance_id) if k not in done]
        if not need:
            continue
        tasks.append({"instance": dataclasses.asdict(inst), "cfg": cfg,
                      "code_version": code_version, "need": need,
                      "trace": inst.instance_id in trace_ids,
                      "out_dir": str(out_dir)})
    print(f"[{cfg['name']}] {len(instances)} instances, {len(tasks)} to process "
          f"({len(instances) - len(tasks)} complete), workers={cfg['workers']}", flush=True)

    counts: dict[str, int] = {}
    n_rows = 0
    t0 = time.time()
    with open(res_path, "a", encoding="utf-8") as fout:
        def sink(result: dict, idx: int) -> None:
            nonlocal n_rows
            for row in result["rows"]:
                fout.write(json.dumps(row) + "\n")
                counts[row["status"]] = counts.get(row["status"], 0) + 1
                n_rows += 1
            fout.flush()
            os.fsync(fout.fileno())
            el = time.time() - t0
            eta = el / idx * (len(tasks) - idx)
            print(f"  {idx}/{len(tasks)} {result['instance_id']} "
                  f"elapsed {el:.0f}s eta {eta:.0f}s", flush=True)

        if int(cfg["workers"]) <= 1 or len(tasks) <= 1:
            for i, t in enumerate(tasks, 1):
                sink(process_instance(t), i)
        else:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            with ProcessPoolExecutor(max_workers=int(cfg["workers"]),
                                     mp_context=mp.get_context("spawn")) as pool:
                futs = [pool.submit(process_instance, t) for t in tasks]
                for i, f in enumerate(as_completed(futs), 1):
                    sink(f.result(), i)
    if _DP_WORKER is not None:
        _DP_WORKER.close()

    t_end = _now()
    manifest = {}
    if resume and man_path.exists():
        try:
            manifest = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    cfg_text = json.dumps(cfg, sort_keys=True)
    manifest.update({
        "name": cfg["name"], "config": cfg,
        "config_sha256": sha256_text(cfg_text),
        "master_seed": cfg["master_seed"],
        "generator_version": generators.GENERATOR_VERSION,
        "runner_version": RUNNER_VERSION,
        "sysinfo": sysinfo(), "git_commit": code_version,
        "n_instances": len(recs),
    })
    manifest.setdefault("runs", []).append({
        "start": t_start, "end": t_end, "argv": sys.argv, "resume": resume,
        "workers": cfg["workers"], "only_family": only_family,
        "instances_processed": len(tasks), "rows_written": n_rows,
        "status_counts": counts})
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[{cfg['name']}] done: {n_rows} rows, status counts {counts}", flush=True)
    return manifest


# ---------------------------------------------------------------------------
# DP runtime scaling study
# ---------------------------------------------------------------------------

def run_scaling(config_path: str, resume: bool = False, force: bool = False) -> None:
    """Time exact DP (numpy; python up to ``python_max_n``) and greedy
    (lowest_id) on random instances (alphabet 4, lengths uniform 5-12 by default,
    retained mode) for n = n_min.. until an engine times out / is refused."""
    from .preprocess import preprocess
    from .overlap import overlap_matrix
    from .greedy import greedy
    from .exact_dp import estimate_dp_memory_bytes

    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    name = cfg["name"]
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "scaling.jsonl"
    if path.exists() and path.stat().st_size > 0 and not (resume or force):
        raise SystemExit(f"{path} exists; use --resume or --force")
    if force and not resume and path.exists():
        path.unlink()
    existing = _read_jsonl(path)
    done = {(r["n"], r["rep"], r["engine"]) for r in existing}
    stopped: dict[str, int] = {}
    for r in existing:               # engines already stopped in a previous run
        if r["status"] != "ok":
            stopped[r["engine"]] = min(stopped.get(r["engine"], 10**9), r["n"])

    params_base = {"alphabet": cfg.get("alphabet", 4), "len_dist": "uniform",
                   "len_min": cfg.get("len_min", 5), "len_max": cfg.get("len_max", 12),
                   "n_mode": "retained"}
    engines = list(cfg.get("engines", ["numpy", "python"]))
    py_max = int(cfg.get("python_max_n", 12))
    timeout_s = float(cfg.get("timeout_s", 120))
    mem_mb = float(cfg.get("memory_mb", 4000))
    reps = int(cfg.get("reps", 5))
    g_rep = int(cfg.get("greedy_repeats", 3))
    code_version = git_version()
    worker = get_dp_worker()

    with open(path, "a", encoding="utf-8") as fout:
        def emit(row):
            row.update(config_name=name, code_version=code_version, timestamp=_now())
            fout.write(json.dumps(row) + "\n")
            fout.flush()
            os.fsync(fout.fileno())
            print(f"  n={row['n']} rep={row['rep']} {row['engine']}: {row['status']} "
                  f"t={row.get('t_solve_s')}", flush=True)

        for n in range(int(cfg.get("n_min", 4)), int(cfg.get("n_max", 22)) + 1):
            params = dict(params_base, n=n)
            pk = generators.param_key(params)
            active = [e for e in engines
                      if e not in stopped and not (e == "python" and n > py_max)]
            if not active:
                break
            for rep in range(reps):
                seed = derive_seed(cfg["master_seed"], "instance", name, "random", pk, rep)
                inst = generators.generate("random", params, seed)
                inst.instance_id = f"scaling-n{n}-r{rep}"
                pre = preprocess(inst.strings)
                ret = pre.retained
                M = overlap_matrix(ret)
                info = {"n": n, "rep": rep, "instance_id": inst.instance_id,
                        "n_retained": len(ret), "L": sum(map(len, ret)),
                        "ell": max(map(len, ret), default=0),
                        "n_target_reached": inst.metadata["n_target_reached"]}
                if ("greedy_lowest_id" not in stopped
                        and (n, rep, "greedy_lowest_id") not in done):
                    ts = []
                    for _ in range(g_rep):
                        t0 = time.perf_counter()
                        g = greedy(ret, policy="lowest_id", seed=None, trace=False, overlaps=M)
                        ts.append(time.perf_counter() - t0)
                    emit(dict(info, engine="greedy_lowest_id", status="ok", error=None,
                              length=g.length, t_solve_s=min(ts), t_solve_all_s=ts))
                for e in active:
                    if e in stopped or (n, rep, e) in done:
                        continue
                    est = estimate_dp_memory_bytes(len(ret), e)
                    if est > mem_mb * 1048576:
                        emit(dict(info, engine=e, status="skipped_n_too_large",
                                  error=f"estimated {est/1048576:.0f} MB > {mem_mb} MB",
                                  est_mem_bytes=est))
                        stopped[e] = n
                        continue
                    r = worker.run(ret, M, e, timeout_s, mem_mb)
                    row = dict(info, engine=e, status=r["status"], error=r["error"],
                               length=r["length"], t_solve_s=r["t_solve_s"],
                               t_wall_child_s=r["t_wall_child_s"],
                               peak_rss_mb=r["peak_rss_mb"], est_mem_bytes=est)
                    emit(row)
                    if r["status"] != "ok":
                        stopped[e] = n
    worker.close()
    print(f"scaling done -> {path}", flush=True)
