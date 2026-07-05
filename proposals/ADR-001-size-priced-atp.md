# ADR-001: Size-Priced ATP (candidate for v0.5)

**Status:** PROPOSED (breaking: changes all ATP accounting; do not merge into 0.4.x)
**Origin:** Qwen review 2026-07 (OOM-before-ATP DoS vector)

## Problem

Under v0.4 accounting (1 ATP per rewrite), R-S duplicates an arbitrary subterm for 1 ATP and R-R materializes an arbitrary stored term for 1 ATP. Term size can grow O(2^ATP): ATP bounds work, not memory. §3.6 correctly quarantines OOM as a non-canonical implementation fault, but an attacker can still craft terms that legally consume gigabytes within a small ATP budget — a DoS vector against validators.

## Candidate rule

```text
cost(R-I) = 1
cost(R-K) = 1
cost(R-S) = 1 + size(z)          // z = the duplicated argument, in nodes
cost(R-R) = size(resolve(h))     // materialization priced at materialized size
```

`size(t)` = node count under tree semantics (deterministic).

## Theorem (memory bound)

Per-step size deltas: R-I and R-K strictly shrink; R-S grows by `size(z) − 1 < cost`; R-R grows by `size(resolve(h)) − 1 < cost`. Hence over any evaluation:

```text
size(t_n) − size(t_0)  <  Σ cost_i  =  ATP_spent
```

Materialized term size is **linearly** bounded by budget. OOM DoS is closed at the semantic level; §3.6 local guards become a second fence, not the only one.

## Computed candidate vectors (reference implementation, 2026-07)

| Vector | ATP v0.4 | ATP size-priced | size₀ | size_max | growth ≤ ATP |
| --- | --- | --- | --- | --- | --- |
| TV-4 I·K | 1 | 1 | 3 | 3 | ✓ (0≤1) |
| TV-5 SKK·I | 2 | 3 | 7 | 7 | ✓ (0≤3) |
| TV-6 SII(I·K) | 5 | 8 | 9 | 11 | ✓ (2≤8) |
| TV-7 Ω, 200 steps | 200 | 637 | 11 | 87 | ✓ (76≤637) |

## Trade-offs

- (+) ATP becomes a joint work+memory bound; validator safety by construction.
- (+) Still fully deterministic under tree semantics; sharing implementations still report tree costs.
- (−) Breaks every published ATP vector (TV-4..TV-9 renumber); requires v0.5 fork with new Specification Anchor.
- (−) Budgeting becomes term-shape-dependent; agents must estimate sizes, not just steps. (Arguably a feature: it prices reality.)

## Decision needed

Adopt for v0.5 / reject / adopt with different coefficients (e.g., `1 + ceil(size(z)/k)`).
