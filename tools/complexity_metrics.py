#!/usr/bin/env python3
"""Deterministic complexity metrics for the appendix (spec/appendix-a-complexity.md).

Steps through the v0.5 hash-thunk evaluation, tracking size/depth/fetch
dynamics under the hash-leaf size model. All numbers are integer and
machine-independent — regenerating this table on any host yields identical
output.

    python3 tools/complexity_metrics.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

st = sg.Store()
for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES, sg.FALSE_BYTES):
    st.put(b)

A = lambda l, r: ("app", l, r)
Ig, Kg, Sg = ("lit", sg.sha(b"I")), ("lit", sg.sha(b"K")), ("lit", sg.sha(b"S"))


def put_tree(t):
    if t[0] == "app":
        put_tree(t[1])
        put_tree(t[2])
    return st.put(sg.term_bytes(t))


def metrics(name, h, atp):
    limits = dict(sg.DEFAULT_LIMITS)
    stats = {"fetches": 0}
    t, spent = ("thunk", h), 0
    smax, dmax = 1, 1
    bound_ok = True
    while True:
        try:
            r = sg.step5(t, atp - spent, st, stats, limits)
        except sg.BudgetExhausted:
            outcome = "ATP Exhausted"
            break
        except sg.Unresolved:
            outcome = "Unresolved"
            break
        if r is None:
            outcome = "normal form"
            break
        t = r[0]
        spent += r[1]
        smax = max(smax, sg.size(t))
        dmax = max(dmax, sg.depth(t))
        bound_ok = bound_ok and (sg.size(t) - 1 <= spent)
    return (name, atp, spent, smax, dmax, stats["fetches"],
            "yes" if bound_ok else "VIOLATED", outcome)


rows = [
    metrics("TV-4  I K",            put_tree(A(Ig, Kg)), 100),
    metrics("TV-5  S K K I",        put_tree(A(A(A(Sg, Kg), Kg), Ig)), 100),
    metrics("TV-6  S I I (I K)",    put_tree(A(A(A(Sg, Ig), Ig), A(Ig, Kg))), 100),
    metrics("TV-7  Omega, 500",     put_tree(A(A(A(Sg, Ig), Ig), A(A(Sg, Ig), Ig))), 500),
    metrics("TV-7  Omega, 2000",    put_tree(A(A(A(Sg, Ig), Ig), A(A(Sg, Ig), Ig))), 2000),
]
r1 = st.put(sg.ser(sg.REF, sg.F_ATOM, atom=sg.K_H))
rows.append(metrics("TV-9  REF->REF->K", st.put(sg.ser(sg.REF, sg.F_ATOM, atom=r1)), 100))
ck = sg.c1(("lam", "x", ("lam", "y", ("var", "x"))))
rows.append(metrics("TV-10 C1[\\xy.x] S K", put_tree(A(A(ck, Sg), Kg)), 100))
ghost = sg.sha(b"this node was never stored")
inner = put_tree(A(A(Sg, A(Kg, Ig)), A(Kg, Kg)))
rows.append(metrics("TV-11 S(KI)(KK) ghost",
                    st.put(sg.ser(sg.APPLY, 0x06, left=inner, right=ghost)), 100))

hdr = ("term", "budget", "spent", "size_max", "depth_max", "fetches",
       "size-1<=spent", "outcome")
w = [max(len(str(r[i])) for r in rows + [hdr]) for i in range(len(hdr))]
line = lambda r: "| " + " | ".join(str(r[i]).ljust(w[i]) for i in range(len(hdr))) + " |"
print(line(hdr))
print("|" + "|".join("-" * (w[i] + 2) for i in range(len(hdr))) + "|")
for r in rows:
    print(line(r))
