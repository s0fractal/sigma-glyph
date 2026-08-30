# Post-gate amendment — one narrow P1, no Round 7

Round 6 was the final multifamily gate for this candidate (`REVIEW-POLICY.md`).
This records what it produced and what was changed afterwards, so that nobody has
to reconstruct it from a conversation.

## What the final gate actually produced

**Not a clean three-family pass.** The honest description:

| Family | Model | Verdict | Status |
| --- | --- | --- | --- |
| google | `gemini-3.1-pro-preview` | **ADOPT** | verdict stated identically at head and tail |
| deepseek | `deepseek-v4-pro-0813` | **NO VERDICT** | delivery failure: 88 669-character reasoning trace, `finish_reason=length` |
| qwen | `qwen3-235b-a22b-2507` | **REJECT** | its P0 is `REFUTED_BY_FROZEN_BYTES` |

One adoption, one delivery failure, one refuted rejection — and one narrower P1
found afterwards, during the audit of the refuted rejection.

### Qwen's P0 — `REFUTED_BY_FROZEN_BYTES`

Its counterexample states `wave(APPLY(K,I)) → Ph=32768`. That is the behaviour
**before** this round's fix. Both engines return 49152, the suite records 49152,
and Book II §2 has always read
`wave(APPLY(f,a)) = complete(interfere(wave(f), wave(a)), pin(APPLY(f,a)))`, pin
included. The review asserts that "the specification as presented still contains
contradictory statements" and quotes none; its narrative is drawn from ADR-010's
account of Gemini's round-5 finding rather than from the text under review. This
is the second consecutive round in which this family reviewed the history instead
of the frozen subject.

Kept, not deleted — a reviewer's mistake about the subject is evidence about the
gate.

### The narrower P1 — `CONFIRMED_BY_OWNER_AUDIT`

Found while checking whether Qwen's claim held, and it is not the claim Qwen
made. **Book II never stated how to find a Pin.** `grep "за NodeHash"
spec/book-2-navigation.md` returned nothing: §6.2's tables carried a NodeHash
column and §2 carried the derived rule, but the normative sentence *"pin lookup
is by NodeHash, not by label"* existed only in Book III §5, added in this same
round. An implementer of Book II alone — no federation — could key the table by
the label in its left column and rebuild precisely the divergence that had just
been closed.

Severity P1, not P0: no two current implementations disagree, and every engine
and the suite already behave correctly. It is silence where an implementer must
guess.

## The amendment

Minimal, and the authority lives in one place.

- **Book II §2 gains clause 3**: `pin(x)` MUST resolve by the NodeHash of `x`
  under Book I §3.2, never by a label, name or alias spelling; the §6 tables show
  a label for the reader and the NodeHash column is the normative key; two
  different `WavePin`s for one NodeHash make the annotation profile
  non-conformant, which MUST be refused at load/admission **before any wave is
  answered**, and MUST NOT be resolved by write order. It says why it is
  normative there: an implementation of Book II without Book III must have it
  whole, and until 2026-08-30 the reference oracle looked pins up by name.
- **Book III §5 cites Book II §2.3 instead of restating it.** Two copies of one
  MUST drift apart. Book III keeps only the federation-specific addition: that
  the refusal is an annotation-profile refusal and not a Book I exit — not a
  `Receipt.exit`, not a DISSONANCE.

**Effect on bytes:** `spec/book-2-navigation.md` and `spec/book-3-federation.md`
re-anchored. Both vector suites regenerate **byte-identical** — the amendment
states an existing requirement in the Book that already owned it and changes no
behaviour. `verify_anchors`, `version_check`, `spec_audit` and the full matrix
are green, including the mutation controls that prove the identity invariant and
the load-time admission are load-bearing.

## Why there is no Round 7

By explicit owner disposition, recorded rather than inferred. Another round would
not produce a new independent signal from this ensemble:

- DeepSeek failed to deliver a verdict in three consecutive rounds, for transport
  reasons rather than review ones;
- Qwen reviewed the history rather than the frozen subject in two consecutive
  rounds;
- Gemini has already accepted the semantics this amendment states;
- the gap was found by the maintainer's own audit of a refuted finding, not by
  the ensemble.

**The narrow exception this establishes, stated so it is not stretched later:** a
finding from the *final* gate may be repaired without restarting the same
malfunctioning reviewer ensemble, when the change is minimal, written down here,
reviewed by both standing reviewers, and handed to the roster without pretending
it carries independent ratification. It is **not** a rule that normative bytes
may now move without a gate.

## Standing

This amendment was reviewed by Claude Opus 5 and by `codex@sigma-glyph` on an
exact diff. It adopts nothing. Adoption remains a threshold warrant filed by the
roster, and no model verdict — `ADOPT` included — substitutes for it.
