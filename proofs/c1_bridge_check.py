#!/usr/bin/env python3
"""Bridge for C1Compiler.lean: the Lean C1 model IS the oracle's §6 compiler.

The Lean proof (`mem_skiFv_c1`, `c1_closed`) is a statement about the Lean
*model* of C1. This bridge ties that model to the reference implementation:

  1. no `sorry`/`admit` sneaks past `lean` (the theorems actually check), and
  2. a faithful Python transcription of the Lean `abstr`/`c1` produces the SAME
     Book I SKI NodeHash as the oracle's `sigma_glyph.c1` on a battery of random
     CLOSED λ-terms — so the algorithm the Lean theorem proves total-on-closed
     is byte-for-byte the algorithm the oracle ships.

Deterministic (seeded). Run: python3 proofs/c1_bridge_check.py
"""
import os
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

LEAN = os.environ.get("LEAN", str(Path.home() / ".elan/bin/lean"))


# ---- faithful transcription of C1Compiler.lean (abstr / c1) into oracle terms ----
IG, KG, SG = ("lit", sg.sha(b"I")), ("lit", sg.sha(b"K")), ("lit", sg.sha(b"S"))


def ski_fv(m):
    # mirrors `Book1.C1.skiFv`
    if m[0] == "var":
        return [m[1]]
    if m[0] == "app":
        return ski_fv(m[1]) + ski_fv(m[2])
    return []                                    # lit (I/K/S)


def lean_abstr(x, m):
    # mirrors `Book1.C1.abstr` exactly (A-1, then A-2 `x∉FV → K M`, then A-3)
    if m[0] == "var":
        return IG if m[1] == x else ("app", KG, m)
    if m[0] == "app":
        if x in ski_fv(m):
            return ("app", ("app", SG, lean_abstr(x, m[1])), lean_abstr(x, m[2]))
        return ("app", KG, m)                    # A-2 before A-3 for applications
    return ("app", KG, m)                        # I / K / S : the A-2 catch-all


def lean_c1(t):
    # mirrors `Book1.C1.c1` exactly; output uses oracle SKI term tuples
    if t[0] == "var":
        return ("var", t[1])
    if t[0] == "lapp":
        return ("app", lean_c1(t[1]), lean_c1(t[2]))
    return lean_abstr(t[1], lean_c1(t[2]))       # lam


def rand_closed_lam(rng, scope, depth):
    """Generate a CLOSED λ-term (every var is bound): only emit a var already in
    `scope`; if the scope is empty, we must bind first (a λ)."""
    if depth <= 0 or (scope and rng.random() < 0.4):
        if scope and rng.random() < 0.6:
            return ("var", rng.choice(scope))
        # otherwise bind a fresh variable then use it
        v = f"v{rng.randint(0, 999)}"
        return ("lam", v, ("var", v))
    if rng.random() < 0.5:
        return ("lapp", rand_closed_lam(rng, scope, depth - 1),
                rand_closed_lam(rng, scope, depth - 1))
    v = f"v{rng.randint(0, 999)}"
    return ("lam", v, rand_closed_lam(rng, scope + [v], depth - 1))


def main():
    # 1. the Lean theorems actually check, with no sorry
    if "sorry" in (ROOT / "proofs/C1Compiler.lean").read_text() \
            or "admit" in (ROOT / "proofs/C1Compiler.lean").read_text():
        print("C1-BRIDGE: FAIL — sorry/admit present in C1Compiler.lean")
        return 1
    if os.path.exists(LEAN):
        p = subprocess.run([LEAN, str(ROOT / "proofs/C1Compiler.lean")],
                           capture_output=True, text=True)
        if p.returncode != 0:
            print("C1-BRIDGE: FAIL — lean did not check\n" + p.stdout + p.stderr)
            return 1
        print("ok  lean proofs/C1Compiler.lean checks (theorems, no sorry)")
    else:
        print(f"skip lean check (no lean at {LEAN})")

    # 2. Lean model == oracle on random closed λ-terms (NodeHash-exact)
    rng = random.Random(20260717)
    n = 3000
    for i in range(n):
        lam = rand_closed_lam(rng, [], rng.randint(1, 6))
        oracle = sg.term_hash(sg.c1(lam))
        model = sg.term_hash(lean_c1(lam))
        if oracle != model:
            print(f"C1-BRIDGE: DIVERGENCE at case {i}: {lam}\n"
                  f"  oracle={oracle.hex()} model={model.hex()}")
            return 1
    print(f"ok  Lean C1 model == oracle on {n} random closed λ-terms (NodeHash-exact)")
    print("C1-BRIDGE: ALL AGREE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
