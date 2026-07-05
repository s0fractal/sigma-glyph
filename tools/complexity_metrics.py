#!/usr/bin/env python3
"""Deterministic complexity metrics for the appendix (spec/appendix-a-complexity.md).

Steps through eval manually, tracking size/depth/fetch dynamics under tree
semantics. All numbers are integer and machine-independent — regenerating this
table on any host yields identical output.

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
    t = sg.load(h, st, stats, limits)
    s0, d0 = sg.size(t), sg.depth(t)
    smax, dmax, spent = s0, d0, 0
    while True:
        if sg.is_normal(t):
            outcome = "normal form"
            break
        if spent >= atp:
            outcome = "ATP Exhausted"
            break
        try:
            t = sg.step(t, st, stats, limits)
        except sg.Unresolved:
            outcome = "Unresolved"
            break
        spent += 1
        smax = max(smax, sg.size(t))
        dmax = max(dmax, sg.depth(t))
    return (name, atp, spent, s0, smax, d0, dmax, stats["fetches"], outcome)


rows = [
    metrics("TV-4  I K",            put_tree(A(Ig, Kg)), 10),
    metrics("TV-5  S K K I",        put_tree(A(A(A(Sg, Kg), Kg), Ig)), 10),
    metrics("TV-6  S I I (I K)",    put_tree(A(A(A(Sg, Ig), Ig), A(Ig, Kg))), 100),
    metrics("TV-7  Omega, 200",     put_tree(A(A(A(Sg, Ig), Ig), A(A(Sg, Ig), Ig))), 200),
    metrics("TV-7  Omega, 1000",    put_tree(A(A(A(Sg, Ig), Ig), A(A(Sg, Ig), Ig))), 1000),
]
r1 = st.put(sg.ser(sg.REF, sg.F_ATOM, atom=sg.K_H))
rows.append(metrics("TV-9  REF->REF->K", st.put(sg.ser(sg.REF, sg.F_ATOM, atom=r1)), 10))
ck = sg.c1(("lam", "x", ("lam", "y", ("var", "x"))))
rows.append(metrics("TV-10 C1[\\xy.x] S K", put_tree(A(A(ck, Sg), Kg)), 16))

hdr = ("term", "budget", "spent", "size_0", "size_max", "depth_0", "depth_max", "fetches", "outcome")
w = [max(len(str(r[i])) for r in rows + [hdr]) for i in range(len(hdr))]
line = lambda r: "| " + " | ".join(str(r[i]).ljust(w[i]) for i in range(len(hdr))) + " |"
print(line(hdr))
print("|" + "|".join("-" * (w[i] + 2) for i in range(len(hdr))) + "|")
for r in rows:
    print(line(r))
