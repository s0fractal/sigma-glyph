#!/usr/bin/env python3
"""Why a `spent`-based memory guard is a trap — shown, not asserted.

Book I's ADR-001 bound is `materialized size - 1 <= atp_spent` — an UPPER bound
only. So `spent` is NOT a proxy for a term's size: a divergent-but-bounded term
(Omega) keeps its size tiny while `spent` climbs without bound. A guard that
faulted on `spent` would wrongly kill such a term instead of returning the
canonical DISSONANCE(ATP Exhausted) that TV-7 mandates for every budget.

This is the executable form of Opus 4.8's v0.5.2 observation (already noted in
impl/sigma_glyph.py:eval_hash, ~line 205). It pins nothing new — the invariant
is property-tested and machine-checked (proofs/EvalMachine.lean:evalHash_size_bound);
this script just makes the reason visible. Illustration, not conformance:
lives in examples/, touches no anchored artifact.

    $ python3 examples/mem_diverge.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "impl"))
import sigma_glyph as sg

STEPS = 50

st = sg.Store()
for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES):
    st.put(b)

A = lambda l, r: ("app", l, r)
I = ("lit", sg.sha(b"I"))
S = ("lit", sg.sha(b"S"))


def put(t):
    if t[0] == "app":
        put(t[1])
        put(t[2])
    return st.put(sg.term_bytes(t))


# Omega = (S I I)(S I I) — the canonical non-terminating term.
W = A(A(S, I), I)
root = put(A(W, W))

t = ("thunk", root)
stats = {"fetches": 0}
limits = sg.DEFAULT_LIMITS
BIG = 10 ** 9              # effectively unbounded budget: observe divergence, not exhaustion

spent = 0
peak_size = sg.size(t)
print(f"{'step':>4}  {'spent':>7}  {'size(t)':>8}")
print(f"{0:>4}  {spent:>7}  {sg.size(t):>8}")
for step in range(1, STEPS + 1):
    r = sg.step5(t, BIG, st, stats, limits)
    if r is None:                          # normal form — will never happen for Omega
        print("reached normal form (unexpected for Omega)")
        break
    t, c = r
    spent += c
    peak_size = max(peak_size, sg.size(t))
    print(f"{step:>4}  {spent:>7}  {sg.size(t):>8}")

print()
print(f"After {STEPS} steps: spent = {spent}, peak size(t) = {peak_size}.")
print(f"`spent` grows linearly; the term's size never exceeds {peak_size}.")
print(f"A guard that faulted when spent passed, say, {peak_size + 5} would kill this")
print("divergent-but-bounded term — the exact class Opus 4.8 flagged. The memory")
print("fence in eval_hash therefore guards on measured size(t), never on spent.")
