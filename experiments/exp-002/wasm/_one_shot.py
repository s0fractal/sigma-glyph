#!/usr/bin/env python3
"""Every fixture, once, in a process that has just started.

This exists for two measurements the parent cannot make about itself — cold start
including the runtime import, and OS-level peak RSS — and for one claim it must
not make on trust: that a freshly started process reaches the same verdicts. It
prints every id and verdict so the parent can compare them, and exits non-zero if
anything here fails.
"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

started = time.perf_counter()
import wasmtime  # noqa: E402  — the import is part of what cold start measures

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from profile_load import configured_engine, load_verified  # noqa: E402

FIXTURES = HERE.parent / "fixtures"
MANIFEST = HERE.parent / "fixtures.json"
VERDICTS = {0: "ACCEPT", 1: "REJECT", 2: "MALFORMED"}

engine = configured_engine()
module = load_verified(engine)
first_ready = time.perf_counter() - started

results = []
for fixture in json.loads(MANIFEST.read_text())["fixtures"]:
    raw = (FIXTURES / fixture["file"]).read_bytes()
    store = wasmtime.Store(engine)
    store.set_limits(memory_size=2 * 1024 * 1024)
    store.set_fuel(10_000_000)
    exports = wasmtime.Instance(store, module, []).exports(store)
    exports["memory"].write(store, raw, exports["input_ptr"](store))
    code = exports["verdict"](store, len(raw))
    results.append({"id": fixture["id"], "verdict": VERDICTS.get(code, f"code {code}")})

rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps({
    "cold_start_seconds": first_ready,
    "total_seconds": time.perf_counter() - started,
    "os_peak_rss_bytes": rss if sys.platform == "darwin" else rss * 1024,
    "python": ".".join(map(str, sys.version_info[:3])),
    "vectors": results,
}))
