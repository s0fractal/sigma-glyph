# Changelog

## v0.4.4 (2026-07)
- **New: `tests/spec_conformance/`** — machine-readable conformance suite (Sonnet 4.5 P3.2, the highest-priority deferred item).
  - `vectors.json` (format v1): 23 CAS objects + 34 vectors — genesis/serialization, 8 negative validation cases, eval vectors covering TV-4…TV-10 with exact-budget and under-budget boundaries, root-missing, bad-bytes-child (§3.5b), inert stored DISSONANCE. Normative observables: `result_hash` + `atp_spent` (tree semantics); dissonance outcomes compare uniformly via canonical DISSONANCE hashes.
  - `generate.py` — vectors are **computed from the oracle** (`impl/sigma_glyph.py`), never hand-written; regeneration is deterministic (byte-identical JSON).
  - `run_reference.py` — replays vectors against the oracle; doubles as runner-semantics documentation for Rust/Zig/other implementations.
  - `test_properties.py` — seeded stdlib-only property tests (1929 checks): serialization canonicity round-trip, deser totality under fuzz, eval determinism, ATP exactness (budget = spent reaches NF; spent−1 exhausts), normal forms are 0-ATP fixed points, C1 output purity + determinism.
- CI: regen-freshness gate (`generate.py` must produce no diff), conformance replay, property suite — all required on every push/PR.
- ANCHORS.txt: v0.4.4 section; `vectors.json` is now anchored alongside the Books (executable law gets an anchor too). Books unchanged — their anchors carry over from v0.4.3, and per the LORE precedent document versions bump only when the document changes.

**Impact:** Additive only. No spec text changes. No breaking changes. Multi-language implementations can now claim Book I conformance by passing `vectors.json`.

## v0.4.3 (2026-07)
- Book I §3.4: ATP budget width made normative — `uint32` canonical; ATP > 2³²−1 implementation-defined (MAY reject/clamp); only the three canonical outcomes are consensus-critical. Closes P1 (Claude Sonnet 4.5 finding).
- Book I §3.5: `resolve(h)` failure modes made explicit — missing hash → DISSONANCE(Unresolved Reference); bytes failing §4.1 → Canonical Invalid Object. (Sonnet P2.1.)
- Book I §5.1: truncated-hash footnote replaced with explicit pointer to `impl/sigma_glyph.py` TV-1 — one source of truth. (Sonnet P2.2.)
- ADR-001: retitled "node-count semantics"; `size(t)` definition moved into the header block. (Sonnet P2.4.)
- ROADMAP.md: new "Decision Process" section — multi-model review → impl gate → maintainer decision with written rationale → planned collective governance. (Sonnet P2.5.)
- **Anchor drift fixed:** v0.4.2 shipped without refreshing ANCHORS.txt (`verify_anchors.py` was failing). v0.4.2 anchors reconstructed retroactively and filed as ancestors; v0.4.3 anchors forged; `verify_anchors.py` now checks only the current section and green verification is a release gate.
- reviews/: Claude Sonnet 4.5 review filed (9.5/10); maintainer response with per-finding disposition (incl. one factual rejection: LORE is versioned since v0.4.1); settled points updated.

**Impact:** Clarifications only. No breaking changes. Reference impl unchanged. v0.4.3 is drop-in compatible with v0.4.2.

## v0.4.2 (2026-07)
- Book I §1.1: LITERAL validation timing clarified — normalize on on-demand validation at `resolve(h)`, eager validation is MAY. Closes P1 spec gap (DeepSeek finding).
- Book I §5.3: RESERVED hash bridge sentence — "reason hash, not opcode; doesn't affect deserialization."
- Book I §6: Explicit FV() definition for C1 compiler — normative annex now self-contained.
- Book II §4: LUT_COS range notation clarified — `d ∈ {0, 1, ..., 32768}` (integer inclusive).
- ROADMAP.md: Consolidated all pending breaking changes (ADR-001, ADR-002), v0.5 milestone, release discipline.
- reviews/: DeepSeek review filed (9.2/10); settled points updated.

**Impact:** Clarifications only. No breaking changes. Reference impl unchanged. v0.4.2 is drop-in compatible with v0.4.1.

## v0.4.1 (2026-07)
- Book I: "Signal Damped" demoted to Reserved (Era-1 legacy) — dead normative hash found by Qwen.
- Book II: Resonance Identity (self-application = quadratic amplitude map; MAX is the unique non-zero fixed point); 65534 range explanation.
- LORE: standing waves & self-reflection; Pantheon cultural-fork note.
- proposals/: ADR-001 (size-priced ATP, with computed vectors and memory bound), ADR-002 (entropy–coherence coupling, with worked integer examples).
- reviews/: Qwen review filed; settled points updated.

## v0.4.0 — "Cold Books" (2026-07)
- Restructured into three documents: Book I (Truth, hermetic core), Book II (Navigation, pure math), LORE (non-normative warmth). Per Kimi review.
- Canonical λ→SKI compiler profile C1 (normative annex; implemented, TV-10).
- Explicit R-R one-level-per-step rule + TV-9 (REF chain, 2 ATP).
- Mass formula; CP-24 collision warning; 65535 unit-scale rationale; RESERVED de-nostalgized; blob guards moved to implementation notes.
- Specification Anchor protocol; detached ANCHORS.txt for all three documents.

## v0.3.1 — "Sealed Contour" (2026-07)
- Resolution contract (§3.5): any resolve failure → DISSONANCE(Unresolved Reference), incl. APPLY children.
- Resource faults ≠ canonical dissonance (§3.6).
- LITERAL as inert commitment; BlobStore contract externalized.
- Pin > Derived annotation precedence (resolves FALSE 270° vs left-dominance 180°).
- Stress vectors: TV-6 duplication (tree=5 ATP vs sharing=4), TV-7 Omega, TV-8 unresolved child.
- SKI-only consensus hardened.
- Reference implementation (Book I, Milestone 1): ALL PASS.

## v0.3.0 — "Two Books" (2026-07)
- Wave removed from canonical bytes: WaveVectorQ is a view addressed by NodeHash, never part of identity.
- SKI rewriting as normative reduction semantics (normal order, ATP totalization). LAMBDA removed; binding dissolved.
- FALSE becomes structural: APPLY(K,I). Trinity = nominal axioms; everything else = structural theorems.
- LUT pinned: normative generation formula + SHA-256 arbiter.
- Law of Left Dominance (phase non-commutativity) made normative.
- Genesis re-forged (V2 waveless hashes); Era-1 preserved in migration appendix.

## v0.2.12 — Era-1 "Titanium Monolith" (2025)
- See archive/era-1/. Verified test vectors; genesis forge reconstructed post-hoc.
