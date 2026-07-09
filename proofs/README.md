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

TCB honesty (sharpened by the Kimi v0.6.4 focused review): the base LUT
facts (`lut_range`, `lut_zero`, `lut_size`), the 65536-case amplitude
fixed-point scan (`am_fixed_scan`) and the concrete `divRoundHalfUp`
witnesses use `native_decide`, which adds the Lean compiler to the trusted
base. The interference theorems are *reasoning*-symbolic but not
TCB-independent: `interfere_valid` consumes `lut_range`, `zero_amp_cascade`
and `crystallization` consume `lut_zero`/`native_decide` witnesses — so
their soundness transitively rests on the compiler too. Only the pure
integer lemmas (`divRoundHalfUp` bounds, `size_pos`) and `left_dominance_ph`
(via `Int.emod_eq_of_lt`) are fully kernel-checked with no `native_decide`
in their dependency cone. The differential bridge is the empirical check
that the Lean `interfere` is the oracle's, independent of the TCB question.

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

## Book I evaluator (`EvalMachine.lean`)

The v0.5 hash-thunk machine itself — the beating heart of Book I — is
modeled faithfully (mirrors `step5`/`eval_hash`): leftmost-outermost
reduction with lazy left-spine resolution and size-priced ATP, redex
recognition by hash (§3.1/§3.2), genesis I/K/S intrinsic (§5.1). It is
built on `MachineBytes`, so redex recognition uses the *proven*
serialization/hash layer, not a re-axiomatized one.

- **Totality is definitional** — `step` is well-founded on `sizeOf t`, `eval`
  is fuel-indexed structural recursion: `evalHash` is a *total function*, no
  partial/unsafe.
- **Determinism is definitional** — it is a function.
- `step_bounds` (via `fun_induction`) ⇒ `step_cost_le` (a fired action costs
  ≤ the remaining budget) and `step_cost_pos` (≥ 1: the §3.4 "minimum cost 1",
  so reduction cannot stall at zero cost).
- `eval_spent_le` / `evalHash_spent_le` — **`spent ≤ atp`**: the evaluator
  never overspends its budget, for ALL terms and budgets, now a theorem and
  not just a per-vector observation.
- `size_step` / `eval_size_bound` / `evalHash_size_bound` — the **ADR-001
  memory bound `size ≤ spent + 1`, proven directly on this concrete
  evaluator**. `size_step` is the exact §3.4 per-step accounting
  (`size t' + 1 ≤ size t + c` — every action grows the term by ≤ `cost − 1`;
  R-S, the only growing rule, holds *unconditionally*: the discarded ⟨S⟩ head
  is pure slack). This is the row-by-row step↔cost correspondence that
  `SizeBound.lean` assumed abstractly and `bridge_check.py` samples on live
  traces — here it is a theorem about the evaluator itself, no classifier.

**Bridge** — `eval_bridge_check.py`: no-`sorry` guard, compile (theorems check
on compile), and the executed Lean evaluator (`EvalRun.lean`) matched against
the live oracle on **all 33 eval conformance vectors** — result NodeHash AND
`atp_spent`, byte-exact — including Omega divergence (500 ATP → ATP
Exhausted), R-S size-pricing, genesis-intrinsic, store-isolation and stuck
forms. This is the empirical determinism/totality check: the total,
budget-respecting Lean function IS the oracle on the whole pinned surface.

## Mechanization status

The three ROADMAP formal-verification targets are covered — the Book I
memory bound (`SizeBound`), the Book II wave algebra (`WaveAlgebra`), Book I
byte-level correspondence (`MachineBytes`/`Sha256`) — plus a fourth: the
**Book I evaluator** (`EvalMachine`), giving Qwen's requested
determinism/totality (definitional) with the budget bound as a theorem and a
33-vector oracle differential. The Lean reduction relation *contains* redex
recognition (built on the proven byte layer), rather than deferring it to
vectors, and `EvalMachine.evalHash_size_bound` re-proves the ADR-001 memory
bound directly on the concrete evaluator — so the step-tag / row-by-row
correspondence that `SizeBound` assumed abstractly is now a theorem, not a
future classifier. The four fronts are *layered*, not independent:
`EvalMachine` is built on `MachineBytes`, which is built on `Sha256` — each
front stands on the proven one below it.

Not mechanized: `bridge_check.py` still samples the SizeBound premise on the
*Python oracle's* traces (a useful independent cross-check, since the Lean
proof is about the Lean model and the differential is what ties the two); a
Rust production implementation remains the last non-Lean Qwen item.

Toolchain: `curl …elan-init.sh | sh` (Lean pinned by `lean-toolchain`).
