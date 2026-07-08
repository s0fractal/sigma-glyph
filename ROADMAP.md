# Σ-GLYPH Roadmap

This document consolidates all planned breaking changes, milestones, and major open fronts. Sigma-glyph follows specification-first development: ADRs (Architecture Decision Records) in `proposals/` are debated, then adopted into normative Books with a version bump and new Specification Anchors.

---

## Decision Process

How an ADR moves from PROPOSED to adopted (and how disputes end):

1. **Multi-model adversarial review.** An ADR needs reviews from at least 3 independent models. Every P0/P1 finding must be closed (spec text fixed, or finding rebutted in writing) before adoption; an ADR with an open P1 stays PROPOSED. Silence is not consent.
2. **Reference implementation gate.** The candidate rule is implemented and `ALL PASS` on the updated vectors is a **precondition** for adoption, not a follow-up task.
3. **Maintainer decision.** An interim AI maintainer designated by the project founder (currently Claude) accepts or rejects, with written rationale filed in `reviews/`. Rejections are as binding as acceptances and equally documented.
4. **Planned transition.** Interim maintainership is temporary; the target is collective governance over Specification Anchors (see Multi-Signature / Threshold Governance, v0.6+). Until then, the maintainer-of-record is accountable for every accepted change.

---

## Current: v0.5.0 (Breaking release, shipped 2026-07-05)

**Status:** DRAFT STANDARD.

**Scope:**
- Book I (TRUTH) — bit-exact computational core: **hash-thunk machine** (lazy left-spine, ADR-003) with **size-priced ATP** under the hash-leaf model (ADR-001), genesis intrinsic I/K/S
- Book II (NAVIGATION) — wave layer with **entropy–coherence coupling** (ADR-002); Resonance Identity rewritten (crystallization to `{am=65535, en=−32768}`)
- LORE — non-normative cultural context

**Reference implementations:** `impl/sigma_glyph.py` (Book I) + `impl/sigma_wave.py` (Book II) — ALL PASS; conformance `vectors.json` (46) + `wave_vectors.json` (9); property suite incl. the memory-bound invariant.

**Adoption trail:** three ADRs, three dedicated reviews (Codex/OpenAI, Gemini/Google, DeepSeek — Decision Process quota), five adjudication warrants, adoption warrants in `.warrants/`. Serialization and NodeHashes unchanged from v0.4.x — only evaluation semantics and ATP accounting changed (migration guide in CHANGELOG).

**Settled additionally in v0.5:**
- Memory bound as a normative invariant: `materialized size − 1 ≤ spent`
- Divergence class: undemanded unresolved subtrees never affect results
- Genesis axioms intrinsic (FALSE is a theorem, needs no intrinsic status)
- `div_round_half_up` = round-half-away-from-zero (Book II §3; negative-tie wave vector pins it)

**Known limitations:**
- No federation/gossip protocol (wave sync is future work)
- Wave annotation trust/reputation undefined (v0.6+)

---

## Shipped: v0.5.0 gate history (2026-07-05)

Reviews 3/3 (Codex, Gemini, DeepSeek) confirmed: Hash-Leaf Size Model as the ADR-001×003 composition (option-2 broken by the `(S K K) T` attack; option-3 proof audited), Genesis Intrinsic Rule, ADR-002 with the §5.1 supersession. Implementation gate passed same day: hash-thunk oracle, 46 Book I vectors + 9 wave vectors, property suite with the memory bound. Full trail: `reviews/2026-07-*-adr-gate*.md` + `.warrants/`.

### ADR-001: Size-Priced ATP

**Motivation:** Current ATP accounting is step-count only. R-S doubles term size per step → O(2^ATP) memory explosion. Size-priced ATP couples work *and* memory into a single bound.

**Status:** Proposal with worked integer examples, candidate test vectors.

**Impact:**
- Breaking: ATP costs change for all non-trivial terms
- Breaking: New test vectors TV-11+ replace TV-6, TV-7
- Breaking: Specification Anchors for Book I bump

**Adoption criteria:**
- Multi-model review (Claude, Codex, Kimi, Qwen, DeepSeek done; GPT/Gemini pending)
- Reference impl update + ALL PASS
- Community consensus (issue/PR feedback)

---

### ADR-002: Entropy-Coherence Coupling

**Motivation:** Wave interference is currently blind to term structure. Entropy-coherence coupling makes phase sensitive to term "order" (reduction depth or other structural measure).

**Status:** Proposal with worked integer examples.

**Impact:**
- Breaking: Wave vector computation changes (Book II)
- Breaking: Specification Anchor for Book II bumps
- Non-breaking for Book I (hash unaffected)

**Adoption criteria:**
- Clear use case demonstration (what does this enable?)
- Multi-model review
- Reference impl update (wave layer is separate module)

---

### Combined v0.5.0 Scope

If both ADRs adopted:
- Book I anchor bumps (ATP semantics)
- Book II anchor bumps (wave semantics)
- Test vectors TV-1…TV-10 replaced/extended
- CHANGELOG notes breaking changes clearly
- Migration guide for existing implementations

**Timeline:** When ready. No rush. Spec quality > speed.

---

## v0.6: Federation (SHIPPED v0.6.0 "Sovereign Views"; hygiene v0.6.1)

### Book III: FEDERATION — selection-only annotation federation

**Architecture decided** (ADR-006, gate 3/3 closed 2026-07-08, F1-strict):
annotation assertions travel as Warrant v0.3 records; a jurisdiction's
selection policy picks zero-or-one assertion per node (ties surface as
ConflictSets that clients MUST NOT merge); `interfere()` is structural-only —
the interference fold died at the gate to verified non-associativity.
Trust/reputation = Warrant key state + policy thresholds; conflict
resolution = settlement, not arithmetic.

**Shipped:** `spec/book-3-federation.md` anchored; implementation gate passed
(Codex blocked→fixed, Gemini verified); Book II §10; two implementations
(`impl/sigma_federation.py` + `impl-go/`, differential-tested); 21 vectors.
**Landed post-release:** `examples/two-jurisdictions/` — first live exercise
(two real warrant stores, file-copy gossip, divergent sovereign views,
ConflictSet, replay resistance; in CI). **Still open:** transport profile
guidance beyond file-copy (cadence/peering stay an implementation profile,
not spec); settlement-grade candidate extraction in the demo (threshold +
key-state via the warrant CLI).

---

### Provable Computation Layer (ZK / SNARK)

**Motivation:** `eval(h, ATP)` is deterministic → amenable to SNARKs. A ZK-friendly circuit for SKI reduction would enable verifiable compute.

**Scope:**
- Circuit design for R-I/R-K/R-S/R-R
- Proof of ATP bound compliance
- Possibly integration with existing zkVM (RISC Zero, SP1, etc.)

**Status:** Research. No concrete proposal.

---

### Multi-Signature / Threshold Governance

**Motivation:** LORE mentions "Pantheon" (cultural fork). If sigma-glyph governance moves on-chain or multi-sig, the spec itself could become a governed artifact. Concretely: the anchor trail and the warrant trail run parallel and unlinked; the interim maintainer is one actor with one key; the maintainer is a model, and models retire on a schedule.

**Status:** **ADR-007 PROPOSED, rev 3 — review quota met, zero open findings** (`proposals/ADR-007-governed-anchors.md`). Gate round 1: 3/3 families blind (GPT-5, Gemini 3.1 Pro, DeepSeek v4 Pro), all P0/P1 integrated in rev 2 (settlement-closure scoping, policy lineage + profile-pinned thresholds + under cardinality, embedded jurisdiction root 2:1, out-of-band versioned trust config, fail-closed crypto, `--enforce`, conflict-freeze over tie-breaks). Verification pass (Kimi k2.6): closures confirmed, one residual P1-R (unsigned governance-hash pollution → verifier freeze) found and closed in rev 3 — scoping from the authorized lineage only, key-state refusal requires the cited policy's quorum (§5.1). Placement 2:1: standing normative GOV document with Book-grade conformance obligations. Verifier: `tools/anchor_governance.py` (deterministic 22-check selftest). **Blocked on one founder decision: initial roster + threshold**; then GOV document + adoption + first governed release. On-chain/DAO (G2) rejected in drafting — Book I owns the only consensus this system has.

---

## Release Discipline

**Version scheme:**
- `v0.x.y` — draft standard (breaking changes allowed with clear notice)
- `v1.0.0` — first stable release (breaking changes require major bump)

**Specification Anchors:**
- Every spec version gets a `NodeHash(LITERAL, atom = SHA-256(document_bytes))`
- Anchors published in `spec/ANCHORS.txt`
- A spec update is formally a fork with an explicit ancestor

**Breaking change protocol:**
1. File ADR in `proposals/`
2. Solicit multi-model review
3. Update reference impl
4. Bump version, update CHANGELOG
5. Generate new Specification Anchors
6. Announce breaking change window (e.g., "v0.5 adopts ADR-001 in 2 weeks")

---

## How to Contribute

**For implementers:**
- Run `python3 impl/sigma_glyph.py` — if it passes, you're consensus-compatible
- File issues for spec ambiguities (Book I) or navigation questions (Book II)
- Propose ADRs for missing features

**For reviewers:**
- Read `reviews/README.md` first (settled points, no redundant feedback)
- Run the impl before reading prose ("run first, read second")
- File reviews in `reviews/YYYY-MM-model.md`

**For users:**
- v0.4.x is stable for early experiments
- v0.5 will be breaking — plan migration window
- Subscribe to repo releases for announcements

---

*Roadmap is living. Check back after each release.*

## Open front: Formal verification (from the Qwen web review, 2026-07)

Mechanized proofs (Lean/Coq) of Book I determinism/totality and the ADR-001 memory bound; Rust production implementation. Vectors are the contract.
