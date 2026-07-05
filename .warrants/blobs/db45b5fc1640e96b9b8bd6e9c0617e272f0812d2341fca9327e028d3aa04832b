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

## Current: v0.4.x (Stable)

**Status:** DRAFT STANDARD — stable enough for early adoption.

**Scope:**
- Book I (TRUTH) — bit-exact computational core, consensus-complete
- Book II (NAVIGATION) — wave/coordinate annotation layer (non-interfering)
- LORE — non-normative cultural context

**Reference implementation:** `impl/sigma_glyph.py` — ALL PASS on test vectors TV-1…TV-10.

**Settled:**
- SKI reduction semantics (normal order, ATP totalization)
- Canonical bytes = identity (content-addressed)
- Wave removed from hash (view, not identity)
- LUT pinned (SHA-256 arbiter)
- C1 λ→SKI compiler (normative annex)

**Known limitations:**
- No federation/gossip protocol (wave sync is future work)
- No size-priced ATP (tree semantics only; see ADR-001)
- No entropy-coherence coupling (see ADR-002)

---

## Next: v0.5.0 (Breaking)

**Planned adoption:** ADR-001 and/or ADR-002 (both are independent, both are breaking).

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

## Future: v0.6+ (Speculative)

### Federation / Gossip Protocol

**Motivation:** Book II defines wave vectors but not how nodes sync them. A wave annotation layer needs a propagation protocol.

**Scope:**
- Wave sync protocol (pub/sub over libp2p or similar)
- Conflict resolution for competing annotations
- Trust/reputation for wave publishers
- Possibly a Book III: FEDERATION

**Status:** Open front. No ADR yet.

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

**Motivation:** LORE mentions "Pantheon" (cultural fork). If sigma-glyph governance moves on-chain or multi-sig, the spec itself could become a governed artifact.

**Scope:**
- Multi-sig over Specification Anchors
- Voting protocol for ADR adoption
- Possibly a smart contract or DAO

**Status:** Cultural. No technical proposal yet.

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
