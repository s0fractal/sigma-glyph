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

- **Book II §2 gains clause 3**, stated **extensionally**:
  `NodeHash(x) = NodeHash(y)` ⇒ `pin(x) = pin(y)`. Two spellings of one node
  yield one `WavePin`. Labels and alias names are permitted as **descriptors** —
  an implementation MAY accept them and MAY keep an internal index by name, since
  the equality constrains the result and not the mechanism. What makes a
  descriptor safe is profile admission: two different `WavePin`s for one NodeHash
  make the profile non-conformant, which MUST be refused at load/admission
  **before any wave is answered** and MUST NOT be resolved by write order. The §6
  NodeHash column is the normative key of a row; rows **without** one — `V` in
  §6.2, for instance — are sector coordinates (§2.1) and assign no `WavePin` at
  all.

  The first draft of this clause said lookup MUST be by NodeHash and "never by a
  label, name or alias spelling". That was **stronger than all three
  implementations and over-specified the mechanism**: Python's `wave("FALSE")`
  applies `ALIASES[term]` directly, `sigma_federation` does the same, and Go's
  `namedWave()` applies `alias.Pin` directly. Their observable semantics are
  correct because admission guarantees equivalent spellings cannot disagree — so
  the specification states that guarantee, not an internal map. Caught by
  `codex@sigma-glyph` on exact-diff review of `032f83f`.
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

**The amended anchor set is a committed artifact, not a reproducible
computation.** `round-6/anchor-set.json` is the **pre-amendment** subject the
gate saw and is left untouched. What adoption would bind is
`round-6/post-amendment-anchor-set.json`:

    SHA-256  abf10f2a9c932f31e28973c41658ba728501fef438b35b7538e78c21d37adf59

An earlier revision of this file named a digest that existed only as a command a
reader could re-run. Adoption must bind bytes that are in the repository.

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

## Review standing

| Reviewer | Exact head | Verdict |
| --- | --- | --- |
| `codex@sigma-glyph` | `032f83f` | **REQUEST CHANGES** — four findings, all accepted and addressed here |
| `codex@sigma-glyph` | this head | **pending** |
| Claude Opus 5 | this head | authored the amendment; not an independent review of it |

An earlier revision of this file recorded Codex as having reviewed the exact diff
**before that review happened**. It had not. The actual first verdict was REQUEST
CHANGES, and it is recorded above with the SHA it was given against; the second
row stays `pending` until a verdict exists to put in it. Writing down an approval
that has not been given is the same failure as any other check whose description
outruns what it did.

Codex's four findings on `032f83f`, all accepted: the new MUST was stronger than
the implementations and over-specified mechanism (fixed extensionally, above);
the post-amendment anchor set existed only as a computation (committed, above);
this file claimed a review that had not occurred (corrected, here); and clause 3
sat after an unnumbered paragraph, splitting `1, 2` from `3` while Book III cites
§2.3 (moved directly under item 2).

It adopts nothing. Adoption remains a threshold warrant filed by the roster, and
no model verdict — `ADOPT` included — substitutes for it.
