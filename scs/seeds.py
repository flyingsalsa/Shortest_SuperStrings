"""Deterministic seed derivation (OWNER: coordinator).

Seeds are derived from a master seed plus string labels via SHA-256, so they
never depend on Python's randomised ``hash()``, dict iteration order, process
scheduling, or the number of worker processes.

Instance seeds and tie-breaking seeds use different *namespaces* so they are
independent: ``derive_seed(master, "instance", ...)`` vs
``derive_seed(master, "tie", ...)``.
"""
from __future__ import annotations

import hashlib
import json


def derive_seed(*parts) -> int:
    """Return a 63-bit non-negative int derived from ``parts``.

    ``parts`` must be JSON-serialisable (ints, strings, lists, dicts with
    string keys). Dicts are serialised with sorted keys.
    """
    payload = json.dumps(list(parts), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") >> 1


def sha256_strings(strings) -> str:
    """Content hash of a list of strings (order-sensitive)."""
    payload = json.dumps(list(strings), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
