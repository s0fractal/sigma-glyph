# ADR-002: Entropy–Coherence Coupling in interfere() (candidate for v0.5)

**Status:** PROPOSED (breaking: changes pinned Book II math)
**Origin:** Qwen review 2026-07

## Problem

v0.4 sets `new_en = clamp(avg(en1, en2))` — entropy ignores the interference outcome. Physically, coherent (constructive) interference creates order (entropy should fall); destructive interference creates disorder (entropy should rise). The current model decouples entropy from the wave physics it lives beside.

## Candidate rule

Let `r = LUT_COS[delta] ∈ [-32767, 32767]` (already computed in interfere()).

```text
delta_en = div_round_half_up(-r, 128)          // ∈ [-256, +256]
new_en   = clamp_i16( div_round_half_up(int32(en1)+int32(en2), 2) + delta_en )
```

## Worked examples (integer-exact)

| Alignment | delta | r | delta_en |
| --- | --- | --- | --- |
| Full constructive | 0 | 32767 | −256 (order created) |
| 60° | 10923 | 16383 | −128 |
| Orthogonal | 16384 | 0 | 0 (neutral) |
| Full destructive | 32768 | −32767 | +256 (disorder created) |

Coupling constant 128 gives a ±256 swing (~0.8% of the int16 range per event) — strong enough to accumulate over chains, weak enough not to dominate the average. Alternative constants are a free parameter of this ADR.

## Trade-offs

- (+) Entropy becomes a function of coherence — Gravity ("information flows toward En<0") finally has a mechanism, not just a slogan: repeated constructive resonance literally crystallizes structure.
- (+) Zero new state; reuses `r` already on hand; integer-exact and deterministic.
- (−) Changes interfere() outputs → any published wave-annotation vectors would need re-pinning (Book II anchor fork).
- (−) Needs a saturation analysis: long constructive chains drive en → −32768 (frozen order). Possibly desirable (crystallization), possibly needs a floor-approach damping.
