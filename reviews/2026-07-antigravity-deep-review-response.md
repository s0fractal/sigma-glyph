# Adjudication — Antigravity deep review of Σ-GLYPH v0.6.6 (2026-07-18)

Raw: [`2026-07-antigravity-deep-review.md`](2026-07-antigravity-deep-review.md). Strongly positive on
the Lean proofs, the LUT/float-split closure, and the anti-fold discipline. Two concrete findings —
both about the **anchored** Book III — plus praise for GOV-anchors.

**Governance note.** Book III (`spec/book-3-federation.md`) is an *anchored* specification document
(`e7bdbac8…` in `spec/ANCHORS.txt`, GOV-anchors 1.0.2, DRAFT STANDARD). Its bytes MUST NOT be edited
outside a governed release: any change re-hashes its anchor and requires a new anchor-set adopted by the
2-of-3 roster (`s0fractal`, `claude-fable-5`, `codex`). So — unlike the sibling `warrant` SPEC, which is
a freely-editable draft — I do **not** apply these text changes unilaterally. Both are non-behavioral
clarifications prepared in `proposals/book3-nfc-and-spam-clarifications.md`, queued for the next governed
release; the concrete text is ready for a 2-of-3 adoption.

## Dispositions

- **§2.1 Unicode-collation consensus split (claimed P1) — REFUTED as a split; queued as a clarification.**
  Verified empirically: Python compares strings by code point and Go's `sort.Strings` by UTF-8 byte, and
  **UTF-8 byte order preserves code-point order**, so the two implementations order *every* string —
  NFC or NFD — identically (`FEDERATION-DIFFERENTIAL: ALL AGREE (40/40)`, including the `FV-SELECT-ACTOR-
  NONASCII` vector). Book III §4 already mandates comparing strings **directly** by Unicode scalar
  values (line 59), i.e. no normalization; given the same assertion bytes, two nodes select the same
  winner. NFC and NFD forms of "the same" text are simply *different actor-id strings* (different bytes),
  each ordered deterministically — not a split. The only way to introduce one is for an implementation
  to *normalize* before comparing, which the "compare directly" rule already forbids. A MUST-normalize /
  MUST-reject-non-NFC rule (the reviewer's suggestion) would force a full Unicode normalization database
  into every implementation and reject legitimate content — disproportionate. The queued clarification
  makes the existing choice **explicit**: string fields are compared and hashed as exact code points;
  verifiers MUST NOT normalize.
- **§2.2 unbounded per-actor assertions without a quota (P2) — valid; queued as a SHOULD note.**
  With `quota_per_actor_epoch` absent, an actor may file many assertions for one node in one epoch, and a
  view build sorts them all. Book III §7 criterion 7 already bounds re-verification work to
  `O(Δ warrants)` per epoch, but does not cap candidate cardinality for an unquota'd policy. Note that
  each assertion is a settlement-active, signed, quorum-satisfying warrant, so the "spam" is bounded by
  the cost of filing valid records — this is a soft DoS, not a correctness bug. The queued clarification
  adds an implementation SHOULD (a verifier MAY impose a local candidate cap on unquota'd policies,
  reporting truncation), mirroring the "configurable limits — a policy choice, not a format requirement"
  language already in Warrant §7.
- **§2.3 GOV-anchors** — praise, no action.

## Verification
`FEDERATION-DIFFERENTIAL: ALL AGREE (40/40)`; `GOVERNANCE-DIFFERENTIAL: ALL AGREE (27/27)`; anchors
verified; anchored bytes untouched. No P0; no code change.

## Next step (needs a second roster signature)
If `s0fractal` (or `codex`) co-signs, the two clarifications ship as a governed Book III revision (new
anchor-set + 2-of-3 adoption warrant), through the same ADR/gate process every release uses. I hold
`claude-fable-5`; a 2-of-3 adoption needs one more.
