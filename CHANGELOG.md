# Changelog

## v0.5.0 — "Priced Reality" (2026-07) — BREAKING

Adopts ADR-001 + ADR-003 (composed via the Hash-Leaf Size Model) and ADR-002, after 3/3 dedicated model reviews (Codex, Gemini, DeepSeek) and 5 adjudication warrants. **Serialization, validation, NodeHashes and C1 are unchanged — every v0.4 hash remains valid.** What changed is evaluation semantics and ATP accounting.

**Book I (0.4.5 → 0.5.0):**
- §3.3: the **hash-thunk machine** — terms are graphs of materialized nodes over unresolved hashes (thunks); redex patterns compare hashes without forcing; leftmost-outermost search forces only what it demands; genesis thunks are normal-form leaves. Divergence class normative: undemanded unresolved subtrees never affect results.
- §3.4: **size-priced ATP, hash-leaf model** — force costs 1/2/3 (atom/REF/APPLY), R-I/R-K/R-R cost 1, R-S costs `1 + size(z)` with thunks counting 1 and never forced. New normative invariant: `materialized size − 1 ≤ spent` (the memory bound). Exhaustion decided before every action; min-cost 1 check precedes even the fetch.
- §3.5: **lazy left-spine materialization normative** (eager was 0.4.x); §3.6 updated (size guard now free via the bound).
- §5.1: **Genesis Intrinsic** — I/K/S resolve without a store; FALSE is a theorem, constructible.
- §7: TV costs re-pinned (TV-4: 4 ATP; TV-5: 12; TV-6: 21; TV-9: 6; TV-10: 20); new TV-11 (divergence class) and TV-12 (genesis intrinsic).

**Book II (0.4.2 → 0.5.0):**
- §5: **entropy–coherence coupling** — `delta_en = div_round_half_up(−r, 128)`; constructive interference creates order, destructive creates disorder.
- §5.1: **Resonance Identity rewritten** — entropy drifts −256 per constructive self-application; the unique non-zero full-WaveVector fixed point is `{am=65535, en=−32768}` (crystallization; the Gravity mechanism).

**Vectors and implementations:**
- `vectors.json` format v2 (46 vectors): all eval expectations re-pinned; `store_subset` field for isolation vectors; flips vs v0.4: `EV-K-DEAD-MISSING` → I (was Unresolved), `EV-REF-MISSING-ATP1` → Exhausted (force priced). ghost bytes pinned: SHA-256("this node was never stored").
- **New `impl/sigma_wave.py`** (Book II oracle: LUT arbiter-checked, interfere with coupling) + `wave_vectors.json` (9 vectors incl. `WV-NEG-TIE` — catches floor-rounding implementations: `avg(−1,−2)` MUST be −2, away-from-zero per Book II §3).
- Property suite: +P7 memory bound (2103 checks); appendix A rewritten (time O(spent²), memory O(spent), "you pay to look").

**Migration from v0.4.x:**
1. Hashes, stores and blobs need no migration — identity layer untouched.
2. Re-budget every eval call: costs are ~2–4× step counts for small terms (materialization is priced). Rule of thumb: `3×(nodes to touch) + old step count + size of duplicated args`.
3. Terms relying on eager verification ("whole closure must exist") now reduce past dead missing branches — if you depended on Unresolved Reference as an availability check, check availability explicitly instead.
4. Wave annotations: recompute entropies; self-resonant structures drift to en=−32768 by design.
5. Anchors: Book I `0c4f39cc…`, Book II re-anchored; v0.4.6 anchors remain valid ancestors.

## v0.4.6 (2026-07)
- **New: `spec/appendix-a-complexity.md`** (NON-NORMATIVE) — per-rule size deltas (only R-S/R-R grow, each by < the duplicated size), O(2^ATP) worst-case envelope with the honest empirical note that Omega grows *linearly* (~1 node / 8 steps; the exponential bound needs crafted duplication towers), time/space bounds for v0.4.x vs ADR-001, fetch accounting. Closes Sonnet 4.5 P3.1 — the last deferred finding from that review.
- **New: `tools/complexity_metrics.py`** — regenerates the appendix table; integer-deterministic, machine-independent. Table vs tool: tool wins.
- **Oracle robustness (self-found, P1-class):** a term of depth 1500 — well within the promised `max_node_depth=4096` — crashed `eval` with a raw `RecursionError` (Python stack ceiling ~1000; same leak class as the Codex P1-A totality bug). Fixed: `eval_hash` scopes the interpreter recursion limit to the configured depth and maps residual `RecursionError` → `ResourceFault` (§3.6 local fault). Two new oracle tests: depth-1500 within limits → canonical outcome; depth-4500 beyond limits → ResourceFault, never a raw crash.
- ANCHORS.txt: v0.4.6 section; appendix anchored alongside the Books. Book I/II, LORE and vectors.json unchanged — anchors carry over (published vectors: **no changes**).

**Impact:** Additive doc + local-fault robustness fix. No spec text changes, no vector changes, no consensus-observable changes.

## v0.4.5 (2026-07)
- **Oracle bug fix (Codex follow-up P1):** `eval` could (a) leak a raw `Unresolved` exception through the post-step lookahead — violating the §3.4 totalization MUST — and (b) report `atp_spent > atp` by firing a rule it could not pay for. New loop: exhaustion is decided **before** any resolve of the next step; `spent` never exceeds `atp`; failed firings are not charged; `eval` is total.
- Book I §3.4: new normative bullet pinning the above (budget check precedes firing; `eval(REF(missing),0)` = ATP Exhausted, not Unresolved).
- Book I §3.5: **eager materialization normative in 0.4.x** — APPLY children resolve before redex recognition; a missing dead argument yields Unresolved Reference, not reduction past it (Codex follow-up P1: the gap was divergence-grade). Lazy left-spine resolution filed as **ADR-003** (v0.5 candidate; composes with ADR-001).
- Conformance suite: +5 vectors (39 total) — `EV-K-DEAD-MISSING`, `EV-REF-MISSING-ATP0/1`, `EV-I-REF-MISSING-ATP1/2` pin the new semantics and the exhaustion-vs-unresolved precedence.
- **Corrected published vectors:** `EV-TV4-IK-ATP0`, `EV-TV7-OMEGA-0` — `atp_spent` 1 → 0. These values were produced by the buggy loop and contradicted §3.4; a defective vector is corrected, not grandfathered (rationale in `reviews/2026-07-codex-v0.4.4-followup-response.md`). Outcome hashes unchanged.
- Version metadata (Codex P2): README "Current" line fixed (was stale at v0.4.0); `vectors.json` gains `suite_version` alongside `spec_version`; conformance claims must cite both plus `book1_anchor`.
- Release checklist extended: README version line + "did published vectors change" statement are now release gates.

**Impact:** Book I text clarified (2 additions), oracle semantics corrected on previously-unpinned edges, two published vector values corrected with rationale. No outcome-hash changes for any previously published vector.

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
