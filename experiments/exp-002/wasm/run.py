#!/usr/bin/env python3
"""EXP-002, WASM side: measure the profile against the frozen fixtures.

The load path is in `profile_load.py` and checks the artifact's pinned digest
before Wasmtime sees it, so this side is judged on the same identity discipline
Sigma-Glyph gets from Book I rather than on the absence of one.

Every negative control here is a gate: a failure exits non-zero.
"""

from __future__ import annotations

import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import wasmtime

from profile_load import ArtifactMismatch, configured_engine, load_verified

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "fixtures"
MANIFEST = HERE.parent / "fixtures.json"
PIN = json.loads((HERE / "artifact.json").read_text())
REQUIRED_PYTHON = "3.13.15"
REQUIRED_WASMTIME = "48.0.0"
FUEL = 10_000_000
MEMORY_LIMIT = 2 * 1024 * 1024
RUNS_PER_VECTOR = 5
VERDICTS = {0: "ACCEPT", 1: "REJECT", 2: "MALFORMED"}


def enforce_pins() -> list[str]:
    """The preregistration pins the runtime, so the runner refuses to produce a
    result under anything else. A number measured on an unpinned interpreter is
    not the measurement that was preregistered."""
    from importlib.metadata import version

    problems = []
    running = platform.python_version()
    if running != REQUIRED_PYTHON:
        problems.append(f"python {running}, the preregistration pins {REQUIRED_PYTHON}")
    installed = version("wasmtime")
    if installed != REQUIRED_WASMTIME:
        problems.append(f"wasmtime {installed}, the preregistration pins "
                        f"{REQUIRED_WASMTIME}")
    if installed != PIN["runtime"]["wasmtime"]:
        problems.append(f"wasmtime {installed} does not match artifact.json's "
                        f"{PIN['runtime']['wasmtime']}")
    return problems


def cpu_model() -> str:
    """The processor, by model name, with nothing that identifies the machine."""
    try:
        if platform.system() == "Darwin":
            return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                  capture_output=True, text=True,
                                  check=True).stdout.strip()
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def measure(engine, module, raw: bytes) -> tuple[str, int, list[float], int]:
    timings = []
    verdict, fuel, pages = None, None, None
    for _ in range(RUNS_PER_VECTOR):
        store = wasmtime.Store(engine)
        store.set_limits(memory_size=MEMORY_LIMIT)
        store.set_fuel(FUEL)
        exports = wasmtime.Instance(store, module, []).exports(store)
        memory = exports["memory"]
        memory.write(store, raw, exports["input_ptr"](store))
        started = time.perf_counter()
        code = exports["verdict"](store, len(raw))
        timings.append(time.perf_counter() - started)
        verdict, fuel, pages = VERDICTS.get(code, f"code {code}"), FUEL - store.get_fuel(), memory.size(store)
    return verdict, fuel, sorted(timings), pages


def iqr(values: list[float]) -> float:
    if len(values) < 4:
        return max(values) - min(values)
    quantiles = statistics.quantiles(values, n=4, method="inclusive")
    return quantiles[2] - quantiles[0]


def gates(engine) -> list[str]:
    """Controls that must refuse. Each failure is returned and fails the run."""
    failures = []
    raw = (HERE / PIN["file"]).read_bytes()
    fixture = (FIXTURES / "pos-accept-under.json").read_bytes()

    # 1. A corrupted artifact, checked against the digest the verifier was given.
    corrupted = bytearray(raw)
    corrupted[len(raw) // 2] ^= 0xFF
    try:
        load_verified(engine, bytes(corrupted))
        failures.append("a corrupted artifact loaded under the pinned digest")
    except ArtifactMismatch:
        pass

    # 2. Zero budget must refuse rather than answer.
    module = load_verified(engine)
    store = wasmtime.Store(engine)
    store.set_limits(memory_size=MEMORY_LIMIT)
    store.set_fuel(0)
    try:
        exports = wasmtime.Instance(store, module, []).exports(store)
        exports["memory"].write(store, fixture, exports["input_ptr"](store))
        answer = exports["verdict"](store, len(fixture))
        failures.append(f"zero fuel answered {answer} instead of refusing")
    except Exception:
        pass
    return failures


def mutation_survey(engine, step: int = 37) -> dict:
    """An observation, not a control: what raw Wasmtime does with flipped bytes
    when nobody checks the digest first. It says what the runtime alone catches,
    which is a different question from what the profile catches."""
    raw = (HERE / PIN["file"]).read_bytes()
    fixture = (FIXTURES / "pos-accept-under.json").read_bytes()
    outcomes = {"rejected at load": 0, "trapped": 0, "same verdict": 0,
                "different verdict": 0}
    offsets = list(range(0, len(raw), step))
    for offset in offsets:
        corrupted = bytearray(raw)
        corrupted[offset] ^= 0xFF
        try:
            module = wasmtime.Module(engine, bytes(corrupted))
        except Exception:
            outcomes["rejected at load"] += 1
            continue
        try:
            store = wasmtime.Store(engine)
            store.set_limits(memory_size=MEMORY_LIMIT)
            store.set_fuel(FUEL)
            exports = wasmtime.Instance(store, module, []).exports(store)
            exports["memory"].write(store, fixture, exports["input_ptr"](store))
            answer = exports["verdict"](store, len(fixture))
            outcomes["same verdict" if answer == 0 else "different verdict"] += 1
        except Exception:
            outcomes["trapped"] += 1
    return {"offsets_sampled": len(offsets), "step": step, "outcomes": outcomes}


def fresh_process(expected: list[dict]) -> tuple[dict, list[str]]:
    """A process that has just started must reach the same verdicts, and saying so
    requires comparing all of them rather than trusting one."""
    result = subprocess.run([sys.executable, str(HERE / "_one_shot.py")],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return ({}, [f"fresh process exited {result.returncode}: "
                     f"{result.stderr.strip()[:200]}"])
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ({}, ["fresh process produced no readable report"])

    problems = []
    if report.get("python") != REQUIRED_PYTHON:
        problems.append(f"fresh process ran python {report.get('python')}")
    seen = {row["id"]: row["verdict"] for row in report.get("vectors", [])}
    for vector in expected:
        if vector["id"] not in seen:
            problems.append(f"fresh process skipped {vector['id']}")
        elif seen[vector["id"]] != vector["verdict"]:
            problems.append(f"fresh process says {vector['id']} is "
                            f"{seen[vector['id']]}, in-process said {vector['verdict']}")
    extra = set(seen) - {v["id"] for v in expected}
    problems.extend(f"fresh process reported an unknown vector {name}" for name in extra)
    return (report, problems)


def main() -> int:
    mismatched = enforce_pins()
    if mismatched:
        for problem in mismatched:
            print("REFUSED:", problem, file=sys.stderr)
        return 1
    engine = configured_engine()
    try:
        module = load_verified(engine)
    except ArtifactMismatch as refused:
        print(f"REFUSED before execution: {refused}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text())

    vectors, disagreements = [], []
    for fixture in manifest["fixtures"]:
        raw = (FIXTURES / fixture["file"]).read_bytes()
        verdict, fuel, timings, pages = measure(engine, module, raw)
        vectors.append({"id": fixture["id"], "expected": fixture["expected"],
                        "verdict": verdict, "fuel": fuel,
                        "median_seconds": statistics.median(timings),
                        "iqr_seconds": iqr(timings),
                        "runs": RUNS_PER_VECTOR, "pages": pages})
        if verdict != fixture["expected"]:
            disagreements.append(f"{fixture['id']}: expected {fixture['expected']}, "
                                 f"got {verdict}")

    cold, fresh_problems = fresh_process(vectors)
    control_failures = gates(engine) + fresh_problems
    survey = mutation_survey(engine)

    report = {
        "schema": "sigma-glyph.exp-002-wasm-result@v0",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {"machine": platform.machine(), "system": platform.system(),
                 "release": platform.release(), "cpu": cpu_model(),
                 "python": platform.python_version()},
        "runtime": {"wasmtime": __import__("importlib.metadata", fromlist=["version"])
                    .version("wasmtime"),
                    "pins_enforced": {"python": REQUIRED_PYTHON,
                                      "wasmtime": REQUIRED_WASMTIME}},
        "artifact": {"file": PIN["file"], "sha256": PIN["sha256"],
                     "bytes": PIN["bytes"], "rustc": PIN["build"]["rustc"]},
        "protocol": {"runs_per_vector": RUNS_PER_VECTOR, "fuel_budget": FUEL,
                     "memory_limit_bytes": MEMORY_LIMIT},
        "vectors": vectors,
        "cold_start": cold,
        "controls": {"passed": not control_failures, "failures": control_failures},
        "mutation_survey": survey,
    }
    (HERE / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    fuel = [v["fuel"] for v in vectors]
    medians = [v["median_seconds"] for v in vectors]
    print(f"WASM: {len(vectors)} vectors x {RUNS_PER_VECTOR} runs, "
          f"{len(disagreements)} disagreements")
    print(f"  fuel: min {min(fuel)}, median {int(statistics.median(fuel))}, max {max(fuel)}")
    print(f"  per-vector median wall: {statistics.median(medians) * 1e6:.1f} us "
          f"(slowest vector {max(medians) * 1e6:.1f} us)")
    print(f"  per-vector IQR: median {statistics.median([v['iqr_seconds'] for v in vectors]) * 1e6:.2f} us")
    print(f"  peak memory: {max(v['pages'] for v in vectors)} pages, "
          f"OS RSS in a fresh process {cold.get('os_peak_rss_bytes', 0) // 1024} KiB")
    print(f"  cold start: {cold.get('cold_start_seconds', 0) * 1000:.1f} ms, "
          f"fresh process replayed {len(cold.get('vectors', []))} vectors")
    print(f"  artifact: {PIN['bytes']} bytes, sha256 {PIN['sha256'][:16]}…")
    print(f"  controls: {'all refuse' if not control_failures else 'FAILED'}")
    print(f"  mutation survey (no digest check): {survey['outcomes']}")
    for line in disagreements + control_failures:
        print("FAIL", line, file=sys.stderr)
    return 1 if (disagreements or control_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
