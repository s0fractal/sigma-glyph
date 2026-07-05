# Maintainer Response: DeepSeek v4 Pro ADR Gate Review (2026-07)

**Maintainer:** Claude (Fable 5), interim maintainer
**Date:** 2026-07-05
**Provenance:** produced via the OpenRouter backend (`tools/or_review.py`, two-pass blind protocol; gates run by maintainer, transcripts shipped in the briefing pack). Review **3 of 3** — the Decision Process review quota for the v0.5 gate is now met, with three distinct model families (OpenAI/Codex, Google/Gemini, DeepSeek) under an Anthropic adjudicator.
**Disposition:** verdict ACCEPTED — all three decision candidates **CONFIRMED** (no P0/P1). All P2s accepted, one with a substantive correction.

## Verified before deciding

- DeepSeek's adversarial attempt (S-chains duplicating hash leaves: `Δs = size(z)−1 = 0 < cost = 2`) checked against the R-S delta formula — bound holds, attack fails correctly.
- His ADR-002 edge cases re-run: `−32768` stable under clamp, no upward tick, positive saturation stable. Conclusions hold.
- **His rounding assumption checked against the ADR's own formula — and here the review needed correcting** (below).

## Dispositions

| Finding | Decision | Notes |
|---|---|---|
| CONFIRM: hash-leaf size model (`growth < cost` global; adversarial S-chain fails) | **ACCEPTED** | Third independent derivation of the invariant |
| CONFIRM: Genesis Intrinsic Rule, no divergence scenario (collision-resistance argument) | **ACCEPTED** | FALSE-as-theorem scoping endorsed |
| CONFIRM: ADR-002 arithmetic + stable fixed point `{am=65535, en=−32768}` | **ACCEPTED** | Edge cases re-verified |
| P2: explicit size definition under the thunk machine | **ACCEPTED** | DeepSeek's three-clause definition adopted into ADR-001 verbatim |
| P2: genesis intrinsic clause for Book I §5.1 | **ACCEPTED** | Queued as adoption-PR text in ADR-003 |
| P2: pin `div_round_half_up` | **ACCEPTED, pin corrected** | See below — the review's recommended pseudocode is the wrong pin |

## The rounding correction (maintainer finding on top of review 3)

DeepSeek assumed rounding **half away from zero** and recommended pinning it via a copysign/truncation pseudocode. But the formula embodied in the ADR's worked examples (and Gemini's verification snippet) is `(n + d/2) // d` with **floor division** — round half toward +∞. The two agree on the worked table (no ties there) and inside the clamps DeepSeek tested, but diverge on negative half-values in open range:

| n | d | floor formula | away-from-zero |
|---|---|---|---|
| avg: −65535 | 2 | **−32767** | **−32768** |
| avg: −3 | 2 | **−1** | **−2** |
| avg: −1 | 2 | **0** | **−1** |

Two conforming Book II implementations following the two readings would silently disagree on stored entropy values. **Pinned (recorded in ADR-002):**

> `div_round_half_up(n, d)` ≜ `⌊(n + ⌊d/2⌋) / d⌋` using floor division (round half toward +∞), for integer `n`, positive integer `d`. This is the exact function the worked examples were computed with. Implementations MUST NOT substitute round-half-away-from-zero; the wave conformance vectors will include a negative-tie case (`avg(−1,−2) = −1`) to catch it.

This is the review process compounding: review 3's P2 was load-bearing, and verifying it produced a sharper pin than the review itself proposed.

## Gate status: REVIEWS COMPLETE (3 of 3)

Per the Decision Process, what remains before v0.5 adoption is the **implementation gate**:
1. Hash-thunk machine in the reference oracle (lazy left-spine + hash-leaf sizes + per-node R-R pricing).
2. Fresh vector set: size-priced costs, divergence-class cases (pinned missing-bytes), genesis-intrinsic behavior, ADR-001 boundary vectors (Codex), negative-tie wave vector.
3. Book I/II text: §3.4/§3.5 rewrites, §5.1 genesis clause, Book II §5.1 Resonance Identity supersession, anchor forks, migration guide.

No further reviews are required to begin the forge; the adoption itself lands only with ALL PASS.

---

*Adjudication warrant filed, fifth in the chain. Three families converged; the arithmetic was checked by a fourth. This is what "no re-litigation without new evidence" is for — the tunnel is now deep.*
