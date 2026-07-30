#!/usr/bin/env python3
"""Regression: the bridge soundness guard rejects both reviewer bypass vectors.

A 2026-07 fresh-context adversarial review proved two vectors that compiled
clean under `lean` (exit 0) AND passed every bridge's old textual guard
(`\\b(sorry|admit)\\b` / `^\\s*axiom`):

  1. `theorem ... := sorryAx _ true`   — word boundary defeated by the `A`;
  2. `private axiom oops : False` + `:= oops.elim` — line-start anchor
     defeated by the modifier (any of private/protected/noncomputable/@[...]).

This test asserts BOTH layers of the replacement guard (proofs/proof_guard.py)
reject both vectors, and that the guard stays quiet on the real proof files
(e.g. MachineBytes.lean's comment containing the word "axiom" must NOT trip
it). All Lean scratch files live in a temp dir — nothing touches proofs/.

Needs `lean` for the semantic layer; exit 2 if unavailable (like the bridges).
Run: python3 tests/proof_guard_test.py
"""
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "proofs"))
import proof_guard  # noqa: E402

VECTOR_SORRYAX = (
    "theorem memory_bound : (1 : Nat) = 2 := sorryAx _ true\n")
VECTOR_PRIV_AXIOM = (
    "private axiom oops : False\n"
    "theorem memory_bound : (1 : Nat) = 2 := oops.elim\n")
VECTOR_ATTR_AXIOM = (
    "@[simp] axiom oops2 : (2 : Nat) = 3\n"
    "theorem memory_bound : (2 : Nat) = 3 := oops2\n")
CLEAN = (
    "-- a comment mentioning sorry, admit and axiom must not trip the guard\n"
    "/- nor a block comment: private axiom -/\n"
    "theorem memory_bound : (1 : Nat) = 1 := rfl\n")

failures = []


def check(name, ok):
    print(("ok    " if ok else "FAIL  ") + name)
    if not ok:
        failures.append(name)


def main():
    lean = proof_guard.find_lean()
    if lean is None:
        print("proof_guard test needs `lean` for the #print axioms layer; exit 2")
        return 2

    # --- textual layer -----------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        for name, body, want_reject in [
                ("textual rejects sorryAx vector", VECTOR_SORRYAX, True),
                ("textual rejects private-axiom vector", VECTOR_PRIV_AXIOM, True),
                ("textual rejects attribute-axiom vector", VECTOR_ATTR_AXIOM, True),
                ("textual accepts clean file (comments mentioning the words)",
                 CLEAN, False)]:
            p = os.path.join(td, "V.lean")
            with open(p, "w") as f:
                f.write(body)
            check(name, bool(proof_guard.textual_guard(p)) == want_reject)

    # the real proof files must stay clean (no false positive regression)
    for f in sorted(os.listdir(os.path.join(REPO, "proofs"))):
        if f.endswith(".lean"):
            probs = proof_guard.textual_guard(os.path.join(REPO, "proofs", f))
            check(f"textual quiet on proofs/{f}", not probs)

    # --- semantic layer (#print axioms), end-to-end through lean -----------
    cases = [
        ("axiom_guard rejects sorryAx vector", VECTOR_SORRYAX, True),
        ("axiom_guard rejects private-axiom vector", VECTOR_PRIV_AXIOM, True),
        ("axiom_guard accepts clean proof", CLEAN, False),
    ]
    for name, body, want_reject in cases:
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "GuardCase.lean"), "w") as f:
                f.write(body)
            err = (proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
                   or proof_guard.axiom_guard(lean, ["GuardCase"],
                                              ["memory_bound"], td))
            check(name, bool(err) == want_reject)
            if err and want_reject:
                print(f"      (guard said: {err[:100]})")

    # a deleted/renamed load-bearing theorem must fail, not skip
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "GuardCase.lean"), "w") as f:
            f.write(CLEAN)
        err = (proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
               or proof_guard.axiom_guard(lean, ["GuardCase"],
                                          ["memory_bound", "gone_theorem"], td))
        check("axiom_guard fails on a missing theorem name", bool(err))

    if failures:
        print(f"\nPROOF-GUARD: {len(failures)} FAILED")
        return 1
    print("\nPROOF-GUARD: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
