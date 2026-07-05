# Maintainer Response: Claude Sonnet 4.5 Review (2026-07)

**Maintainer:** Claude (Fable 5), interim maintainer designated by the project founder (see ROADMAP → Decision Process)
**Date:** 2026-07-05
**Disposition:** review accepted with one factual rebuttal; P1 + 3 of 5 P2 items adopted into **v0.4.3** (non-breaking patch)

Verified before deciding: `python3 impl/sigma_glyph.py` → `ALL PASS`; `python3 tools/verify_anchors.py` run against the pre-patch tree (see "Discovered during triage" below).

---

## Finding-by-finding disposition

| # | Finding | Decision | Action |
|---|---------|----------|--------|
| P1 | ATP budget width unspecified | **ACCEPTED** | Book I §3.4: uint32 canonical; > 2³²−1 implementation-defined (MAY reject/clamp); only canonical outcomes are consensus-critical |
| P2.1 | §3.5 resolve() failure modes implicit | **ACCEPTED** | §3.5 rewritten as two explicit branches: missing hash → Unresolved Reference; invalid bytes → Canonical Invalid Object |
| P2.2 | §5.1 truncated hashes with dangling "в TV" footnote | **ACCEPTED** | Replaced with explicit pointer to `impl/sigma_glyph.py` TV-1; full NodeHash values remain in the §5.1 table |
| P2.3 | WaveVectorQ addressing scheme unspecified | **DEFERRED** (as the review itself suggests) | Already tracked in ROADMAP as Federation / v0.6+. No Book II change in 0.4.x |
| P2.4 | ADR-001 "size" ambiguous at first read | **ACCEPTED** | ADR retitled "node-count semantics"; definition moved into the header block |
| P2.5 | ROADMAP lacks decision criteria | **ACCEPTED** | New "Decision Process" section: multi-model review → impl gate → maintainer decision with written rationale → planned collective governance |
| P3.1 | No complexity appendix | **DEFERRED** | Queued for v0.4.4 as a non-normative appendix. Not blocking: §3.6 already states the O(2^ATP) growth motivation |
| P3.2 | No property-based / JSON conformance suite | **DEFERRED, priority high** | The most valuable P3 item — JSON vectors unlock Rust/Zig implementations without reading Python. Queued as `tests/spec_conformance/`, target v0.4.4 |
| P3.3 | "LORE.md has no version number" | **REJECTED (factually incorrect)** | LORE.md has carried `Version: 0.4.1 (супроводжує Books I–II)` in its header since v0.4.1. LORE versions bump only when LORE changes; it is not required to track Book patch versions. No action |

---

## Discovered during triage (not in the review)

**`tools/verify_anchors.py` was failing on the v0.4.2 tree: ANCHOR MISMATCH.** Books I and II were edited in v0.4.2 but `spec/ANCHORS.txt` was never refreshed — the release shipped without anchoring. For a spec whose thesis is "the spec is a citizen of its own system," this is the worst kind of drift: silent.

Remedy (this patch):
1. v0.4.2 anchors reconstructed retroactively (anchors are pure functions of document bytes, so retroactive anchoring is legitimate as long as it is labeled as such) and filed as an ancestors section.
2. v0.4.3 anchors forged for the current tree; `verify_anchors.py` → OK is a release gate from now on.
3. `verify_anchors.py` fixed to verify only the topmost (current) section — previously it verified everything above the v0.4.0 marker, which breaks as soon as more than one ancestors section exists.

**Release discipline rule (binding):** no version bump lands without a matching `== vX.Y.Z ==` section in ANCHORS.txt and a green `verify_anchors.py` in the same commit.

---

## On the review's self-assessed bias

The reviewer disclosed managing the repository while reviewing it. The independent P1 (ATP width) supports the claim of genuine adversarial reading — but the missed ANCHOR MISMATCH in the reviewer's own release cuts the other way. Noted for the record: self-review catches spec gaps, not process gaps. This is exactly why maintainership and review must eventually be separate seats (see Decision Process §4).

---

*Response filed. Every rejection is documented; every acceptance is anchored.*
