# ADR-005: Book II wave totality — partial pins, base-case waves, iteration vectors

**Status:** PROPOSED (2026-07-07) — needs the standard review gate; touches anchored `wave_vectors.json` and Book II §6, so adoption implies a release
**Origin:** Kimi k2.6 post-release audit of v0.5.0 (P1 ×2 + suite gap), 2026-07. All three claims verified against the oracle by the maintainer before filing.
**Gate reviews:** 1 of ≥3 — Gemini 3.1 Pro (2026-07-07) answers the decision criterion decisively for **R2**: any boolean logic compiled to SKI contains FALSE ≡ `APPLY(K,I)` as a subterm, so under R1 every such compound term is wave-silent — erased from Mass-based routing and Gravity discovery; a boolean primitive must not render the overlying structure topologically invisible. Verdict: R2 (full-vector defaults `{Am=65535, En=-32768}` for partially pinned entities) + absent base case for unpinned LITERALs. Proposed vectors `WV-FALSE-R2-PIN` and `WV-ITERATED-DECAY-6560` (the latter reproduced exactly by the maintainer: `interfere({0,6560,0}, self) = {0, 657, -256}`). (reviews/2026-07-gemini-adr45-gate.md §2)

## Problem

`wave()` is not total over well-formed terms, and the spec does not say what
happens where it is undefined.

1. **Partial pins.** Trinity (§6.1) pins full vectors `{Ph, Am, En}`; Grand
   Cross (§6.2), Time Anchor (§6.3) and Pantheon (§6.4) pin **Ph only**. §2
   says "Pin > Derived" but never defines field-level semantics: does a
   Ph-only pin override just the phase (Am/En derived), or the whole vector
   (Am/En = implementer's guess)?
2. **Zero-amplitude cascade.** If Am/En derive for FALSE:
   `interfere(K, I)` = `{ph=32768, am=0, en=-32512}` (verified against the
   oracle) — the LUT at phase-difference 32768 gives `amp_factor = 0`.
   Since `prod01` multiplies child amplitudes, **any ancestor of an am=0
   node has am=0**: every term containing FALSE is wave-silent. The 17
   vectors never compose a FALSE-containing term, so this is unpinned.
3. **Base case.** `Derived` is defined only for `APPLY`. A non-genesis,
   non-pinned LITERAL has no wave at all — the annotatable set is silently
   smaller than the set of well-formed SigmaNodeV2 terms.
4. **Iteration unpinned.** §5.1 states the design explicitly ("часткова
   прихильність згасає квадратично"), and the oracle confirms
   49151 → 36863 → 20735 → 6560 → 657 → 7 → 0, but no vector pins an
   iterated sequence — a wrong rounding that diverges only after several
   compositions would pass the suite today.

Wave ∉ hash (settled v0.3.0), so none of this can fork `eval()` — the
severity ceiling is P1 (implementers must guess), not P0. But Book II now
ships a normative conformance suite, and two conforming annotators can
currently disagree about every row of §6.2–§6.4.

## Candidate rules

- **R1 (field-level pins):** a pin overrides exactly the fields its table
  lists; unlisted fields derive where `Derived` applies. For FALSE this
  *accepts* the zero-amplitude cascade as semantics: FALSE is wave-silent,
  and silence propagates. (Philosophically consistent with LORE's Gravity
  reading — falsehood carries no amplitude — but that argument is
  non-normative by definition; the gate should weigh it as aesthetics,
  not evidence.)
- **R2 (full-vector defaults):** every pinned entity implicitly completes
  to `{Am=65535, En=-32768}` unless its table says otherwise. Kills the
  cascade for FALSE but asserts maximal amplitude for entities nobody
  computed — and contradicts `Derived` for any pin whose parent waves are
  known.
- **Base case (either way):** define `wave(LITERAL)` for unpinned nodes —
  candidate: annotation is simply **absent** (wave() is partial by design,
  and `interfere` with an absent operand is absent), stated explicitly.
- **Vectors:** whichever rule wins, pin (a) a FALSE-composing term, (b) a
  Ph-only-pin entity's full derived/defaulted vector, (c) one iterated
  self-interference chain (the decay sequence above).

## Decision criterion for the gate

Name a use where a FALSE-containing term's wave must be non-silent for
navigation to work (federation queries, LORE §Gravity flows). If one
exists, R1 is wrong in practice regardless of its elegance. If none does,
R1 is the smaller rule and the cascade is a theorem, not a bug.

## Interim state (until adjudicated)

The oracle implements bare `interfere` only; no pin table ships in code.
Implementers MUST NOT rely on any Am/En for §6.2–§6.4 entities, and MUST
NOT assume `wave()` is total. The 17 shipped vectors remain the only
normative wave surface.
