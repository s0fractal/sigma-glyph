#!/usr/bin/env python3
"""Book I §3.6 resource-fence parity: Python oracle vs the Rust implementation.

§3.6 says a local resource limit breach is an IMPLEMENTATION FAULT — a refusal
to execute — and MUST NOT be serialized as a DISSONANCE. impl/sigma_glyph.py
has always raised ResourceFault. impl-rs had no fences at all until v0.6.7: a
deep left spine or a nested-array vectors file drove `step`, `term_hash`,
`term_size`, the `Term` drop glue and the JSON parser into unbounded recursion,
and the process died with

    thread 'main' has overflowed its stack
    fatal runtime error: stack overflow, aborting          (SIGABRT, rc -6)

which is neither a canonical outcome nor a refusal — the caller learns nothing,
and README.md calls that binary safe by construction. No gate saw it:
tests/book1_fuzz.py generated terms of depth <= 5.

This test pins the three properties that matter:

  1. Below the fence both implementations still agree, exactly. A fence that
     fires early is a divergence, not a safety feature.
  2. Above it, BOTH refuse: Python raises ResourceFault, Rust exits nonzero
     with a message that names the fault and cites §3.6 — and neither reports
     a canonical outcome. Same category, per §3.6; the numeric limits are
     deliberately implementation-defined, so they are not required to match.
  3. A hostile vectors FILE (deep JSON nesting) is refused rather than parsed.

    python3 tests/book1_resource_fence.py
Env: RUST_BOOK1=path   (default ./impl-rs/target/release/book1)
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

RUST = os.environ.get("RUST_BOOK1", str(ROOT / "impl-rs/target/release/book1"))

# Under the Python oracle's default max_node_depth (4096) and under impl-rs's
# MAX_TERM_DEPTH (4096, chosen to mirror it).
SAFE_DEPTH = 2000
# Comfortably past both fences, and past the stack of the unfenced binary:
# depth 20000 reproduced the abort above on this machine.
HOSTILE_DEPTH = 20000
JSON_BOMB_DEPTH = 100000

ATP_EXHAUSTED = sg.term_hash(("dis", sg.R_ATP)).hex()
UNRESOLVED = sg.term_hash(("dis", sg.R_UNRES)).hex()

ok = []


def chk(name, cond, detail=""):
    ok.append(cond)
    print(("OK  " if cond else "FAIL"), name, "" if cond else detail)


def spine(depth):
    """`((… (I I) I) …) I` — a left spine `depth` APPLY nodes deep."""
    store, objects = sg.Store(), {}
    h = sg.I_H
    for _ in range(depth):
        b = sg.ser(sg.APPLY, 0x06, left=h, right=sg.I_H)
        h = store.put(b)
        objects[h.hex()] = b.hex()
    return h, objects, store


def vectors_doc(term_hex, atp, objects, expected):
    return {
        "format": "sigma-glyph-conformance", "format_version": 2,
        "spec_version": "0.5.2", "suite_version": "0.5.0",
        "book1_anchor": "n/a", "oracle": "tests/book1_resource_fence.py",
        "objects": objects,
        "vectors": [{"id": "SPINE", "kind": "eval", "term": term_hex,
                     "atp": atp, "expected": expected}],
    }


def run_rust(path):
    return subprocess.run([RUST, "conformance", path], capture_output=True, text=True)


def main():
    if not os.path.exists(RUST):
        print(f"BOOK1-FENCE: the Rust binary is missing at {RUST} — "
              f"build it (cd impl-rs && cargo build --release)")
        return 1

    with tempfile.TemporaryDirectory() as td:
        # ---- 1. below the fence: identical canonical answers -----------------
        h, objects, store = spine(SAFE_DEPTH)
        r, spent = sg.eval_hash(h, 4_000_000, store)
        result = sg.term_hash(r).hex()
        chk(f"python: depth-{SAFE_DEPTH} spine returns a canonical result "
            f"({result[:12]}…, {spent} ATP), no fault",
            result != ATP_EXHAUSTED and result != UNRESOLVED)
        path = os.path.join(td, "safe.json")
        with open(path, "w") as f:
            json.dump(vectors_doc(h.hex(), 4_000_000, objects,
                                  {"result_hash": result, "atp_spent": spent}), f)
        p = run_rust(path)
        chk(f"rust: depth-{SAFE_DEPTH} spine agrees exactly — the fence does not "
            f"fire on legitimate depth",
            p.returncode == 0 and "RUST-CONFORMANCE: ALL PASS (1/1)" in p.stdout,
            f"rc={p.returncode} {p.stdout.strip()[:300]} {p.stderr.strip()[:300]}")

        # ---- 2. above the fence: both refuse, neither invents an outcome -----
        h, objects, store = spine(HOSTILE_DEPTH)
        try:
            r, spent = sg.eval_hash(h, 4_000_000, store)
            chk(f"python: depth-{HOSTILE_DEPTH} spine raises ResourceFault", False,
                f"returned {sg.term_hash(r).hex()} / {spent} ATP instead")
        except sg.ResourceFault as fault:
            chk(f"python: depth-{HOSTILE_DEPTH} spine raises ResourceFault "
                f"({fault}), not a DISSONANCE", True)
        except RecursionError:
            chk(f"python: depth-{HOSTILE_DEPTH} spine raises ResourceFault", False,
                "RecursionError escaped — the §3.6 fault must be typed")

        path = os.path.join(td, "hostile.json")
        with open(path, "w") as f:
            json.dump(vectors_doc(h.hex(), 4_000_000, objects,
                                  {"result_hash": "00" * 32, "atp_spent": 0}), f)
        p = run_rust(path)
        blob = p.stdout + p.stderr
        chk(f"rust: depth-{HOSTILE_DEPTH} spine exits cleanly instead of aborting",
            p.returncode > 0,
            f"rc={p.returncode} (negative rc = killed by a signal, i.e. the "
            f"stack overflow this test exists for)\n{blob.strip()[:400]}")
        chk("rust: the refusal names a local resource fault and cites §3.6",
            "resource fault" in blob and "§3.6" in blob, blob.strip()[:400])
        chk("rust: the fault is NOT dressed up as a canonical outcome",
            "RUST-CONFORMANCE: ALL PASS" not in blob
            and ATP_EXHAUSTED not in blob and UNRESOLVED not in blob,
            blob.strip()[:400])
        chk("rust: no stack overflow reported", "overflowed its stack" not in blob,
            blob.strip()[:400])

        # ---- 3. a hostile vectors FILE ---------------------------------------
        bomb = os.path.join(td, "bomb.json")
        with open(bomb, "w") as f:
            f.write("[" * JSON_BOMB_DEPTH + "]" * JSON_BOMB_DEPTH)
        p = run_rust(bomb)
        blob = p.stdout + p.stderr
        chk(f"rust: {JSON_BOMB_DEPTH}-deep JSON nesting is refused, not parsed",
            p.returncode > 0 and "nesting" in blob
            and "overflowed its stack" not in blob,
            f"rc={p.returncode}\n{blob.strip()[:400]}")

    print(("\nBOOK1-FENCE: ALL PASS" if all(ok) else "\nBOOK1-FENCE: FAILURES PRESENT")
          + f" ({sum(ok)}/{len(ok)})")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
