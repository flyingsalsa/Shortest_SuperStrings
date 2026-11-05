"""Machine / software provenance (OWNER: Agent B)."""
from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=_ROOT, capture_output=True,
                           text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def git_version() -> str:
    """Commit hash, with '-dirty' appended if the working tree has changes
    to tracked files or untracked (non-ignored) files."""
    h = _git("rev-parse", "HEAD")
    if h is None:
        return "unknown"
    st = _git("status", "--porcelain")
    return h + ("-dirty" if st else "")


def _pkg_version(name: str) -> str | None:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None


def cpu_name() -> str:
    name = platform.processor() or ""
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                               r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name = winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except Exception:
            pass
    return name or platform.machine()


def sysinfo() -> dict:
    try:
        import psutil
        ram = psutil.virtual_memory().total
        logical = psutil.cpu_count(logical=True)
        physical = psutil.cpu_count(logical=False)
    except Exception:
        ram = logical = physical = None
    return {
        "python": sys.version.replace("\n", " "),
        "python_version": platform.python_version(),
        "packages": {p: _pkg_version(p) for p in ("numpy", "matplotlib", "psutil")},
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu_name(),
        "cpu_count_logical": logical,
        "cpu_count_physical": physical,
        "ram_bytes": ram,
        "git_commit": git_version(),
    }
