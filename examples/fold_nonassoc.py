#!/usr/bin/env python3
"""interfere() is not a merge — folding it is unsound. Shown, not asserted.

Book III forbids protocol-level interference folds (§1 MUST NOT). The reason is
concrete: interfere() is non-associative, so `(w1 . w2) . w3` and `w1 . (w2 . w3)`
give DIFFERENT results — grouping alone changes the answer. This is the executable
form of the ADR-006 "fold killer".

The counterexample already lives as an anchored conformance vector,
FV-FOLD-UNSOUND (tests/spec_conformance/federation_vectors.json), and as a Lean
theorem, fold_not_associative (proofs/WaveAlgebra.lean), re-checked against the
oracle by proofs/wave_bridge_check.py. This script reproduces it live from the
wave layer so a reader meeting interfere() in Book II can see the non-associativity
directly. Illustration, not conformance: lives in examples/, touches no anchored
artifact; the pinned guarantee remains FV-FOLD-UNSOUND.

    $ python3 examples/fold_nonassoc.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "impl"))
import sigma_wave as sw

# The FV-FOLD-UNSOUND operands, verbatim.
w1 = sw.W(0, 65535, 0)
w2 = sw.W(16384, 65535, 0)
w3 = sw.W(16384, 65535, 0)

left = sw.interfere(sw.interfere(w1, w2), w3)   # (w1 . w2) . w3
right = sw.interfere(w1, sw.interfere(w2, w3))  # w1 . (w2 . w3)


def show(w):
    return f"{{ph:{w['ph']:>5}, am:{w['am']:>5}, en:{w['en']:>5}}}"


print("operands:")
print(f"  w1 = {show(w1)}")
print(f"  w2 = {show(w2)}")
print(f"  w3 = {show(w3)}")
print()
print(f"(w1 . w2) . w3 = {show(left)}")
print(f"w1 . (w2 . w3) = {show(right)}")
print()
same = left == right
print(f"associative? {same}")
if not same:
    print(f"grouping alone changed am: {left['am']} vs {right['am']}.")
    print("interfere() is a pairwise coordinate op, not a mergeable aggregate —")
    print("this is why Book III §1 forbids protocol-level folds (ADR-006).")

# Fail loudly if this ever stops matching the anchored vector.
assert not same, "interfere() unexpectedly associative — contradicts FV-FOLD-UNSOUND"
assert (left["am"], right["am"], right["en"]) == (16384, 32768, -128), \
    "live result diverged from anchored FV-FOLD-UNSOUND expectation"
print()
print("matches anchored FV-FOLD-UNSOUND (left am=16384, right am=32768, en=-128).")
