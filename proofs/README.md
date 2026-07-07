# Mechanized proofs

The assurance stack for Book I's normative memory bound
(`materialized_size − 1 ≤ spent`, §3.4) has three layers:

1. **Checked algebra** — `SizeBound.lean` (Lean 4 core, no mathlib):
   the seven-row accounting model of §3.4 entails the invariant by
   induction over traces, plus the preflight corollary
   (`size ≤ budget + 1`). Run: `lean proofs/SizeBound.lean`.
2. **Checked premise on live traces** — `bridge_check.py` drives the
   reference oracle step-by-step over adversarial terms (duplication
   towers, Ω, deep REF chains, dead branches, TV fixtures) and asserts
   every observed action satisfies the step-level premise the Lean
   proof consumes (`Δsize ≤ cost − 1`). Run: `python3 proofs/bridge_check.py`.
   NB (scope): the bridge does NOT prove row-by-row correspondence between
   runtime steps and the seven Lean constructors — it checks the weaker,
   theorem-sufficient inequality. Exact per-rule costs remain covered by the
   conformance vectors; a step-tag classifier is a possible future upgrade.
3. **Pinned end results** — the conformance vectors and property P7
   (`tests/spec_conformance/`).

What is NOT yet mechanized: byte-level machine correspondence
(serialization, hashing, redex recognition) and the Book II integer
algebra (interfere invariant preservation). Those are the next targets
on the formal-verification front (ROADMAP).

Toolchain: `curl …elan-init.sh | sh` (Lean pinned by `lean-toolchain`).
