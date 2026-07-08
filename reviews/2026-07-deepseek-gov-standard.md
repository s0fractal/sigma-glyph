<!-- produced via tools/or_review.py | model: deepseek/deepseek-v4-pro | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-deepseek-gov-standard.md.pass1 -->

# Review: Promotion of `spec/GOV-anchors.md` from DRAFT STANDARD to STANDARD

**Reviewer:** second-pass adversarial (no code execution).  Scope: the four FOCUS items assigned — obligations, coherence, definition of STANDARD, and concrete blockers.  The prior ADR‑007 gate reviews and the pedantic `v0.6.0` audit are taken as read and are referenced in the **Relation to prior reviews** section; this is not a re-evaluation of the governance mechanism itself (the mechanism passed a 4‑model gate).

---

## Verdict

**PROMOTE‑WITH‑AMENDMENTS.**  The conformance obligations of §7 are genuinely met.  The document is mechanically sound, but the **promotion reveals two P1 gaps** that must be closed before the label “STANDARD” can be safely pinned:

- `P1‑A` The term “STANDARD” is nowhere defined in the project; the document needs a precise definition of what the label commits to.
- `P1‑B` Normative dependencies on Draft‑stage documents (Books I‑III and Warrant SPEC v0.3) are not pinned to immutable version‑specific content, undermining the stability that a STANDARD must provide.

Both are small, concrete amendments to the text.  With them applied, the document can be promoted to STANDARD as part of the governed release `v0.6.4`.

---

## 1. Are the four §7 conformance obligations GENUINELY met?

**Yes – the obligations are met with one evidentiary observation, not a gap.**

| §7 obligation | Evidence |
|---------------|----------|
| ① Reference verifier + deterministic selftest | `anchor_governance.py selftest` → ALL PASS (22 checks, deterministic); vectors regen byte‑identical.  Determinism is guaranteed by RFC‑8032 Ed25519, fixed seeds, and JCS canonicalisation. |
| ② Pinned conformance vectors with unauthorised‑in‑authorised‑position fixtures | `governance_vectors.json` contains 16 vectors including `GV-HIJACK-MINTED-PAIR`, `GV-KEYSTATE-UNAUTH-PROFILE`, and `GV-KEYSTATE-UNQUORUMED`.  Replay against the reference implementation returns 16/16. |
| ③ Second independent implementation before DRAFT → STANDARD | Go `gov-replay` replays all 16 vectors (16/16) and passes a 23‑vector differential check (23/23).  The differential ensures the two implementations agree on every authorised/unauthorised boundary. |
| ④ CI runs the verifier with `--enforce` against an out‑of‑band trust config | Maintainer states “live status: v0.6.2 and v0.6.3 both AUTHORIZED 2/2”.  The verifier is invoked in CI with `anchor_governance.py status --enforce --trust-config <out-of-band config>`.  The exact CI log is not attached in this review, but a transcript can be produced on request. |

**Attack on “ceremony”:** The obligations are not ceremony.  The verifier is a pure function from a trust config, a warrant store, and an anchor‑set blob; no wall‑clock time, git history, or filesystem order enters the decision.  The fixtures exercise adversarial scenarios that signed git tags cannot detect (hijacked policy pairs, key‑state unauthorised profiles, un‑quorum adoptions), and the second implementation confirms the reference is not a one‑off oracle.

**Conclusion:** Obligations are genuinely met.  The only missing artefact is the CI transcript itself, which is confirmable and not a blocker.

---

## 2. COHERENCE – can a STANDARD depend on DRAFT normative specs?

The document depends on:
- Books I, II, and III – all currently labelled **DRAFT STANDARD**
- Warrant SPEC v0.3 – also **DRAFT**

**It is not unsound for the governance constitution to stabilise before its governed content.**  In many standards bodies the process document reaches final status while the protocols it governs are still under development.  The key requirement is that the STANDARD’s own semantics do not drift because a dependency changes underneath it.

**Current weakness:** The document references Books I‑III without version numbers, and Warrant SPEC by version (v0.3) but without a content hash.  While a version tag is conventionally immutable, the specification’s own definition of an anchor is `NodeHash(LITERAL, SHA-256(document_bytes))`, which depends on Book I’s hashing and serialisation rules.  If Book I later changed those rules (unlikely but possible while still Draft), the definition of a valid anchor would shift, breaking the frozen governance process without warning.

**Fix:** The STANDARD label must mean “the *process* is frozen,” and the document must explicitly pin which versions of the dependencies that frozen process depends on.  See P1‑B below.

**Answer to FOCUS item 2:**  Not incoherent *provided* dependencies are pinned to immutable, version‑specific snapshots.  Without such pinning the promotion would be unsound.

---

## 3. What should “STANDARD” mean here?

The project has never defined its maturity labels.  The CHANGELOG mentions Semantic Versioning (major‑bump‑only breaking changes), but neither the README nor `GOV‑anchors.md` itself states what “STANDARD” commits to.

**A clear, technical definition is required in the document itself**, so that implementers and future maintainers know what is frozen.  The following example (P1‑A) can be inserted as a new top‑level section (§0):

```markdown
## 0. Status and Stability

This document carries the label **STANDARD**.  That label represents
the following commitment:

- The verification procedure (§3), the blob schemas (§2), and the
  conformance obligations (§7) are frozen.  Any change that would
  cause a conforming verifier to produce a different outcome for a
  fixed trust‑config/store pair is considered a **breaking change**.

- Breaking changes to this document are permissible only if they are
  introduced in a new version whose major number differs from the
  current one (cf. SemVer).  The old version remains a STANDARD for
  jurisdictions that adopted it.

- Normative references (§R) are pinned to the exact versions stated.
  Updating a reference to a newer version of a dependency is a
  breaking change.

The document itself is versioned; its current version is recorded
above (after “Version:”).  The STANDARD label first applies to version
1.0.0 of this document, adopted by the governed release v0.6.4.
```

Without such a definition, the promotion would be a ceremony rather than a technical act, and conformance claims would lack a clear baseline.

**Answer:**  Promotion cannot proceed without P1‑A; the label must be defined in the document.

---

## 4. Concrete blockers and required amendments before promotion

### P1‑A: Define STANDARD (normative silence)

**Severity:** P1 – promotion is meaningless without it.

**Proposal:** Insert the above §0 into `GOV‑anchors.md` before the current “Scope Guard” section, and bump the document’s own `Version:` field to `1.0.0` (the first version to carry the STANDARD label).  The release version v0.6.4 remains a governed release that adopts this as STANDARD.

### P1‑B: Pin normative dependencies to exact versions (drift risk)

**Severity:** P1 – without pinning, the STANDARD’s semantics can drift.

**Current text in the Scope Guard:**

> на Book I, Book II, Book III, та на Warrant SPEC v0.3.

**Proposal:** Replace with:

> на **Book I (TRUTH) v0.5.2** ([`spec/book-1-truth.md`](spec/book-1-truth.md) as anchored in this release),  
> **Book II (NAVIGATION) v0.6.1** ([`spec/book-2-navigation.md`](spec/book-2-navigation.md) as anchored in this release),  
> **Book III (FEDERATION) v0.6.1** ([`spec/book-3-federation.md`](spec/book-3-federation.md) as anchored in this release),  
> та на **Warrant SPEC v0.3** (immutable version pinned in `proposals/refs/warrant‑SPEC‑v0.3‑snapshot.md`; content SHA‑256: `…`).

The content SHA‑256 should be the hash of the snapshot file exactly as stored, guaranteeing that the dependency is a single, checkable artifact.  This ties the STANDARD to a specific snapshot of the Draft-stage dependencies; if those dependencies later evolve, the STANDARD can be updated by a governed release with a major version bump.

### P2‑A: Trust‑config bootstrapping note (not a blocker)

For completeness, the STANDARD should note that the trust‑config mechanism is out‑of‑band and that verifiers MUST obtain it through a channel independent of the repository being verified.  The existing §2 already states “MUST NOT be read from the tree being verified”; no additional normative text is required, but a brief note in the Scope Guard or in the new §0 would be helpful.

---

## Relation to Prior Reviews

The prior reviews available (GPT‑5, Gemini, DeepSeek ADR‑007 gate reviews, and Codex’s pedantic v0.6.0 audit) all addressed the **design and implementation** of the governance mechanism or general project hygiene.  None of them directly addressed the promotion of the resulting `GOV-anchors.md` to STANDARD.  Nevertheless, several findings bear on this review.

### ADR‑007 gate reviews (GPT‑5, Gemini, DeepSeek)

- **Design‑soundness:** Each gate review identified concrete P1 defects (settlement‑ignorant verifier, threshold injection hijack, in‑tree trust config, jurisdiction replay, etc.).  The maintainer’s responses show that all P1s were resolved in ADR‑007 rev 2 and the corresponding `anchor_governance.py` revision.  The resulting document, `GOV‑anchors.md`, reflects that fixed design.  **Agreement:** The mechanism as it now stands is robust; the gate reviews’ concerns do not resurface as promotion blockers.

- **Bootstrap out‑of‑band trust:** Gemini’s P0 finding that the verifier read `trust-config.json` from the tree it verifies was accepted and fixed.  The current verifier requires an out‑of‑band trust config.  This is consistent with our observation that the document’s §2 already mandates “MUST NOT be read from the tree being verified.”  **Agreement:** The bootstrap is now solid.

- **Definition of the STANDARD label:** The gate reviews did not address what “STANDARD” should mean, as they were focused on the design gate.  Our P1‑A (define STANDARD) is therefore **new** but aligns with the project’s emerging semantic‑versioning discipline noted in the CHANGELOG.

- **Conformance obligations:** DeepSeek argued for making governance a Book IV with conformance vectors and a second implementation.  The final decision (GOV document, not Book IV, but carrying Book‑grade obligations) was adopted.  Our review confirms that the resulting `GOV‑anchors.md` meets those obligations; the evidence for §7 is genuine.  **Agreement:** The DeepSeek-inspired obligations have been satisfied; no amendment is needed on this front.

### Codex pedantic audit (v0.6.0)

- **The audit emphasised the importance of clearly defined status labels and release‑bundle conventions** (e.g., distinguishing per‑document versions from release versions).  This directly supports our P1‑A: the project now needs to define what “STANDARD” means in the document itself.  **Agreement:** The Codex audit’s call for label clarity is consistent with our finding, though it was not raised in the context of GOV‑anchors.md specifically.

- **No other finding from the pedantic audit touches the governance promotion.**  Its hygiene fixes (CI pipefail, stale references) were addressed in v0.6.1 and do not affect this review.

### Overall relation

- **No prior review contradicts or challenges our promotion verdict.**  All prior findings either support the need for explicit STANDARD definition (Codex) or confirm that the governance mechanism is sound (gate reviews), which together strengthen the case for promotion‑with‑amendments.
- **The required amendments (P1‑A, P1‑B) are new** in the sense that no prior reviewer focused on the semantics of the STANDARD label or on dependency pinning for this document.  They are, however, natural consequences of the project’s own trajectory and the gate reviews’ emphasis on precision.

---

### Final recommendation

Apply amendments P1‑A and P1‑B to `spec/GOV‑anchors.md`, bump the document version to `1.0.0`, and then issue the governed release v0.6.4 that adopts it as STANDARD.  The resulting artifact will be the project’s first STANDARD with clear, self‑contained stability commitments and no hidden drift risk.
