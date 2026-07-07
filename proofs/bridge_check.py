#!/usr/bin/env python3
"""Bridge between the Lean proof and the reference oracle.

proofs/SizeBound.lean proves: IF every priced action satisfies the step-level
premise  Δsize ≤ Δspent − 1  (equivalently, growth < cost), THEN the §3.4
memory bound holds along every trace. The Lean file fixes that premise as
seven accounting rows; this script checks the premise against the REAL
machine: it drives impl/sigma_glyph.py step-by-step over adversarial terms
(duplication towers, Omega, deep REF chains, dead-branch terms, the TV
fixtures) and asserts every single observed step satisfies it.

Checked algebra (Lean) + checked premise on live traces (this file) +
pinned end-results (vectors, property P7) = the assurance stack.

Usage: python3 proofs/bridge_check.py   (from the repo root)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "impl"))
import sigma_glyph as sg  # noqa: E402

A = lambda l, r: ("app", l, r)
Ig, Kg, Sg = ("lit", sg.sha(b"I")), ("lit", sg.sha(b"K")), ("lit", sg.sha(b"S"))


def build_store():
    st = sg.Store()
    for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES, sg.FALSE_BYTES):
        st.put(b)
    return st


def put_tree(st, t):
    if t[0] == "app":
        put_tree(st, t[1])
        put_tree(st, t[2])
    return st.put(sg.term_bytes(t))


def trace_steps(st, h, budget):
    """Yield (size_before, size_after, cost) for every priced action."""
    t = ("thunk", h)
    spent, stats = 0, {"fetches": 0}
    while True:
        before = sg.size(t)
        try:
            r = sg.step5(t, budget - spent, st, stats, sg.DEFAULT_LIMITS)
        except (sg.BudgetExhausted, sg.Unresolved):
            return
        if r is None:
            return
        t, cost = r[0], r[1]
        spent += cost
        yield before, sg.size(t), cost


def main():
    st = build_store()
    payload = A(Ig, Kg)
    towers = []
    for _ in range(4):                        # S I I duplication towers
        payload = A(A(A(Sg, Ig), Ig), payload)
        towers.append(payload)
    W = A(A(Sg, Ig), Ig)
    terms = {
        "TV-4 I K": A(Ig, Kg),
        "TV-5 S K K I": A(A(A(Sg, Kg), Kg), Ig),
        "TV-6 S I I (I K)": A(A(A(Sg, Ig), Ig), A(Ig, Kg)),
        "Omega (budget 2000)": A(W, W),
        "K-dead-nested": A(A(Kg, Ig), A(Ig, A(Ig, Kg))),
        "S (K I) (K K) x": A(A(A(Sg, A(Kg, Ig)), A(Kg, Kg)), A(Ig, Ig)),
        **{f"dup-tower-{i+1}": t for i, t in enumerate(towers)},
    }
    # deep REF chain: REF -> REF -> ... -> K
    target = sg.K_H
    for _ in range(12):
        target = st.put(sg.ser(sg.REF, sg.F_ATOM, atom=target))
    terms["REF-chain-12"] = None  # handled specially below

    steps = viol = 0
    for name, t in terms.items():
        h = target if t is None else put_tree(st, t)
        budget = 2000 if "Omega" in name else 100000
        for before, after, cost in trace_steps(st, h, budget):
            steps += 1
            if not (after - before <= cost - 1):
                viol += 1
                print(f"VIOLATION {name}: size {before}->{after}, cost {cost}")
    print(f"steps observed: {steps}; premise (Δsize ≤ cost − 1) violations: {viol}")
    print("BRIDGE: PREMISE HOLDS ON ALL OBSERVED STEPS" if viol == 0 and steps > 500
          else "BRIDGE: FAILED")
    return 0 if viol == 0 and steps > 500 else 1


if __name__ == "__main__":
    sys.exit(main())
