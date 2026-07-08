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

## Book I byte-level machine correspondence (`MachineBytes.lean` + `Sha256.lean`)

The §1.1/§2/§4.1 serialization layer is mechanized: `Node`, canonical
`serialize` (`[Op][Flags][Atom?][Left?][Right?]` with the normative
per-opcode flags), `deserialize` (§4.1 validation), and
`nodeHash = SHA-256 ∘ serialize` over a from-scratch FIPS 180-4 SHA-256
in core Lean (`Sha256.lean`, total — no `partial`/`unsafe`). Theorems:

- `serialize_injective` — distinct well-formed nodes never share canonical
  bytes (identity is injective; the hash layer above adds only CP-24);
- `deser_serialize` / `serialize_deser` — round-trip AND **canonicity**:
  a valid buffer is the unique serialization of its parse (no second byte
  form for any node);
- `deser_wf`, `valid_lengths` (§4.1 rule 3: valid buffers are 34 or 66
  bytes), `reserved_opcode_invalid` (§1.2: opcode `0x03` never parses);
- `lit_bytes_disjoint` — the byte-0 discrimination under `glyph_eq`'s O(1)
  redex recognition;
- **genesis pins** — `H(I)/H(K)/H(S)` (TV-1), the §4.2 Canonical Invalid
  Object, and `false_is_a_theorem` (§5.2: `H(APPLY(⟨K⟩,⟨I⟩))`) recomputed
  end-to-end (`serialize ∘ sha256`) and pinned to the spec constants — so
  "FALSE is a theorem, not an axiom" is now a `native_decide` fact.

**Bridge** — `byte_bridge_check.py`: no-`sorry` guard; FIPS 180-4 digest
vectors; and the executed Lean pipeline (`BytesRun.lean`) matched against
the live oracle on **334 buffers** — every conformance CAS object (incl.
the deliberately malformed Era-1 `0x03` one), the genesis bytes, and ~250
adversarial mutations (truncation, out-of-mask flags, wrong-in-mask flags,
reserved opcode, op/flag swap): CAS keys, §4.1 verdicts and round-trips
all agree. Run: `python3 proofs/byte_bridge_check.py`.

TCB honesty: the SHA-256 correctness and the genesis pins rest on
`native_decide` (Lean compiler in the trusted base) plus the FIPS/oracle
differential; the structural theorems (injectivity, round-trip,
canonicity, validation totality) are symbolic.

## Mechanization status

The three ROADMAP formal-verification targets are now covered: the Book I
memory bound (`SizeBound`), the Book II wave algebra (`WaveAlgebra`), and
Book I byte-level correspondence (`MachineBytes`/`Sha256`). Not mechanized:
row-by-row correspondence between runtime evaluator steps and the seven
`SizeBound` constructors (the `bridge_check` step-tag classifier — a bridge
upgrade, not a missing theorem), and the evaluator's reduction semantics
themselves (redex recognition is pinned by the conformance vectors, not
yet by a Lean reduction relation).

Toolchain: `curl …elan-init.sh | sh` (Lean pinned by `lean-toolchain`).
