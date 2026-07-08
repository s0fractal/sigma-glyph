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

## Book II wave algebra (`WaveAlgebra.lean`)

The §5 `interfere()` integer algebra is mechanized against the generated
LUT (`LutData.lean`, written by `gen_lut_lean.py`, which imports the
oracle's table and therefore inherits the Book II §4 SHA-256 arbiter
fail-fast; encoded as a string literal because a 32769-element array
literal elaborates quadratically). Theorems:

- `interfere_valid` — **range closure**: valid operands give valid results
  (the §3 width guarantee behind the int64 implementer note);
- `zero_amp_cascade` — §6.2's "the zero-amplitude cascade is a theorem",
  now literally one;
- `left_dominance_ph` — §5.2 Law of Left Dominance;
- `crystallization` — §5.1 Resonance Identity: the unique non-zero fixed
  point of self-interference is `{am = 65535, en = −32768}` (phase free);
- `fold_not_associative` / `not_commutative` — the ADR-006 fold killer and
  Left Dominance as machine-checked witnesses (FV-FOLD-UNSOUND operands).

**Bridge** — `wave_bridge_check.py`: (a) `LutData.lean` regenerates
byte-identically; (b) no `sorry`/`axiom` sneaks past `lean`'s exit code;
(c) the Lean `interfere` (executed via `WaveRun.lean`) agrees with the
live oracle on a 582-case deterministic boundary grid incl. the
crystallization point, the FV-FOLD-UNSOUND triple and negative-tie
parities. Run: `python3 proofs/wave_bridge_check.py`.

TCB honesty: LUT-dependent facts (`lut_range`, the 65536-case amplitude
fixed-point scan, the concrete witnesses) use `native_decide`, which adds
the Lean compiler to the trusted base for those facts; the symbolic
theorems (`interfere_valid`, cascade, dominance, the crystallization
skeleton) do not. The differential bridge is the empirical check that the
Lean `interfere` is the oracle's.

What is NOT yet mechanized: byte-level machine correspondence
(serialization, hashing, redex recognition). That is the next target on
the formal-verification front (ROADMAP).

Toolchain: `curl …elan-init.sh | sh` (Lean pinned by `lean-toolchain`).
