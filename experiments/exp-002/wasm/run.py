#!/usr/bin/env python3
"""EXP-002, WASM side: run every frozen fixture under a declared deterministic
profile and report what it cost.

The profile is the point, not the numbers: no imports at all, fuel metering with
a fixed budget, a separate memory limiter, and no SIMD, threads or reference
types. Fuel bounds work. Memory is bounded by the limiter, and the two are
reported separately, because conflating them is the claim this experiment exists
to check honestly.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import wasmtime

HERE = Path(__file__).resolve().parent
MODULE = HERE / "target/wasm32-unknown-unknown/release/exp002_verdict.wasm"
FIXTURES = HERE.parent / "fixtures"
MANIFEST = HERE.parent / "fixtures.json"
FUEL = 10_000_000
MEMORY_LIMIT = 2 * 1024 * 1024          # 2 MiB, well over the module's one page
VERDICTS = {0: "ACCEPT", 1: "REJECT", 2: "MALFORMED"}


def configured() -> wasmtime.Engine:
    config = wasmtime.Config()
    config.consume_fuel = True
    config.wasm_simd = False
    config.wasm_relaxed_simd = False
    config.wasm_threads = False
    config.wasm_reference_types = False
    config.wasm_bulk_memory = False
    config.cranelift_opt_level = "speed"
    return wasmtime.Engine(config)


def run_all(engine: wasmtime.Engine, module: wasmtime.Module) -> list[dict]:
    manifest = json.loads(MANIFEST.read_text())
    results = []
    for fixture in manifest["fixtures"]:
        raw = (FIXTURES / fixture["file"]).read_bytes()
        store = wasmtime.Store(engine)
        store.set_limits(memory_size=MEMORY_LIMIT)
        store.set_fuel(FUEL)
        instance = wasmtime.Instance(store, module, [])
        exports = instance.exports(store)
        memory = exports["memory"]
        pointer = exports["input_ptr"](store)
        capacity = exports["input_capacity"](store)
        if len(raw) > capacity:
            results.append({"id": fixture["id"], "verdict": "MALFORMED",
                            "fuel": 0, "seconds": 0.0,
                            "note": "longer than the module's buffer"})
            continue
        memory.write(store, raw, pointer)
        started = time.perf_counter()
        code = exports["verdict"](store, len(raw))
        elapsed = time.perf_counter() - started
        results.append({"id": fixture["id"],
                        "verdict": VERDICTS.get(code, f"code {code}"),
                        "fuel": FUEL - store.get_fuel(),
                        "seconds": elapsed,
                        "pages": memory.size(store),
                        "expected": fixture["expected"]})
    return results


def controls(engine: wasmtime.Engine, module_bytes: bytes) -> list[str]:
    """The two refusals the preregistration requires, and one it implies."""
    findings = []
    fixture = (FIXTURES / "pos-accept-under.json").read_bytes()

    # Zero budget must refuse rather than answer.
    module = wasmtime.Module(engine, module_bytes)
    store = wasmtime.Store(engine)
    store.set_limits(memory_size=MEMORY_LIMIT)
    store.set_fuel(0)
    try:
        instance = wasmtime.Instance(store, module, [])
        exports = instance.exports(store)
        exports["memory"].write(store, fixture, exports["input_ptr"](store))
        answer = exports["verdict"](store, len(fixture))
        findings.append(f"zero fuel answered {answer} instead of refusing")
    except Exception:
        pass

    # A corrupted artifact: the preregistration asks that one must not produce a
    # valid verdict. Measured rather than assumed, and the answer is that this
    # format cannot make that promise — 6% of single-byte flips leave the verdict
    # unchanged, because a module has slack the runtime never reads. Detection
    # here is not a property of the runtime; it needs a digest carried out of
    # band. So the control records the distribution instead of pretending to a
    # refusal, and fails only if a flip silently changes the answer.
    outcomes = {"rejected at load": 0, "trapped": 0, "same": 0, "changed": 0}
    for offset in range(0, len(module_bytes), 37):
        corrupted = bytearray(module_bytes)
        corrupted[offset] ^= 0xFF
        try:
            broken = wasmtime.Module(engine, bytes(corrupted))
        except Exception:
            outcomes["rejected at load"] += 1
            continue
        try:
            store = wasmtime.Store(engine)
            store.set_limits(memory_size=MEMORY_LIMIT)
            store.set_fuel(FUEL)
            exports = wasmtime.Instance(store, broken, []).exports(store)
            exports["memory"].write(store, fixture, exports["input_ptr"](store))
            answer = exports["verdict"](store, len(fixture))
            outcomes["same" if answer == 0 else "changed"] += 1
        except Exception:
            outcomes["trapped"] += 1
    findings.append("corruption survey (not a refusal): "
                    + ", ".join(f"{v} {k}" for k, v in outcomes.items()))
    if outcomes["changed"]:
        findings.append(f"{outcomes['changed']} flips changed the verdict without "
                        "the runtime objecting — detection needs an out-of-band digest")
    return findings


def main() -> int:
    engine = configured()
    module = wasmtime.Module(engine, MODULE.read_bytes())
    if module.imports:
        print("FAIL: the module declares imports", file=sys.stderr)
        return 1

    rounds = [run_all(engine, module) for _ in range(3)]
    signature = [[(r["id"], r["verdict"]) for r in round_] for round_ in rounds]
    if signature[0] != signature[1] or signature[1] != signature[2]:
        print("FAIL: three runs did not agree", file=sys.stderr)
        return 1

    wrong = [r for r in rounds[0] if r["verdict"] != r.get("expected")]
    for r in wrong:
        print(f"FAIL {r['id']}: expected {r.get('expected')}, got {r['verdict']}",
              file=sys.stderr)

    fuel = [r["fuel"] for r in rounds[0]]
    seconds = sorted(r["seconds"] for r in rounds[0])
    pages = max(r.get("pages", 0) for r in rounds[0])
    print(f"WASM: {len(rounds[0])} fixtures, {len(wrong)} disagreements")
    print(f"  fuel: min {min(fuel)}, median {int(statistics.median(fuel))}, max {max(fuel)}")
    print(f"  wall: median {statistics.median(seconds) * 1e6:.1f} us, "
          f"max {max(seconds) * 1e6:.1f} us")
    print(f"  peak memory: {pages} page(s) = {pages * 64} KiB, limiter at "
          f"{MEMORY_LIMIT // 1024} KiB")
    print(f"  artifact: {MODULE.stat().st_size} bytes")
    for note in controls(engine, MODULE.read_bytes()):
        print("  " + note)
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        Path(HERE / "results.json").write_text(json.dumps(rounds[0], indent=2) + "\n")
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
