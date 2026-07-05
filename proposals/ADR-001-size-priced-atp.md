# ADR-001: Size-Priced ATP — node-count semantics (candidate for v0.5)

**Status:** PROPOSED (breaking: changes all ATP accounting; do not merge into 0.4.x)
**Origin:** Qwen review 2026-07 (OOM-before-ATP DoS vector)
**Definition up front:** everywhere in this ADR, `size(t)` = **node count under tree semantics** (the accounting model TV-6 makes normative) — not byte length, not depth. Deterministic by construction. (Clarity: Claude Sonnet 4.5 review, 2026-07.)

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

## Budget preflight — bounded cost measurement (added per Codex ADR-gate review, 2026-07)

`cost(R-R) = size(resolve(h))` as originally written only *moves* the OOM from the rewrite to the pricing preflight: sizing an attack payload can itself exhaust memory before ATP Exhausted can be canonicalized. Closure:

```text
Before a rewrite fires, compute its cost up to cap = remaining_atp + 1.
If cost > remaining_atp: eval returns DISSONANCE(ATP Exhausted), spent unchanged,
and the term is not rewritten. The preflight MUST NOT materialize more than cap
nodes. Missing hash during measurement -> DISSONANCE(Unresolved Reference);
invalid bytes during measurement -> Canonical Invalid Object.
```

This inherits Book I §3.4's v0.4.5 discipline under variable costs: `spent` never exceeds `atp`; an unaffordable step is Exhausted *before* any full materialization. A step whose bounded measurement exceeds `2^32 − 1` is unaffordable for every canonical budget → ATP Exhausted (not implementation-defined).

Candidate vectors: `EV-RR-SIZE-UNDER` (REF(APPLY(I,K)), atp 2 → Exhausted, spent 0), `EV-RR-SIZE-EXACT-REDUCIBLE` (same, atp 3 → Exhausted, spent 3 — R-R completes, no budget for R-I), `EV-RR-SIZE-EXACT-NORMAL` (REF(K), atp 1 → K, spent 1).

## Composition with lazy resolution (ADR-003) — OPEN, blocks joint adoption

R-S pricing needs `size(z)`; ADR-003's purpose is never fetching dead data. These conflict when z is duplicated by R-S and then discarded by K before being demanded (`S (K I) (K K) missing`: lazy reaches `K` without touching z; measuring `size(z)` kills that). Options on the table (Codex ADR-gate review):

1. **Strict size-priced R-S** — measure z always; ADR-003 liveness weakened.
2. **Lazy demand-priced R-S** — small fixed R-S cost, thunks charged when forced; memory-bound theorem must be rewritten for thunked terms.
3. **Hash-leaf size model** — unresolved hash counts as size 1 until forced; preserves laziness, changes the meaning of tree sizes, needs fresh vectors.

**Decision candidate (upgraded 2026-07-05, Gemini ADR-gate review): option 3 — Hash-Leaf Size Model.** Gemini supplied what upgrades this from a leaning to a candidate: (a) an attack breaking option 2 (`(S K K) T` with pre-materialized large `T`: growth `size(T)−1` at constant demand-cost — the bound collapses), and (b) a proof that option 3 preserves `growth < cost` globally: R-S pays `1 + size(z)` with unresolved hash leaves counting as 1 (copying a leaf adds exactly 1 node); R-R pays for precisely what it materializes. Maintainer refinement: under the hash-thunk machine R-R materializes **one node at a time**, so its cost is a small per-node increment — which dissolves the bounded-preflight problem above (no unbounded measurement remains; the preflight section stays as the fallback for eager implementations). Final adoption still gated on review 3 of ≥3 + reference implementation + fresh vectors.

## Decision needed

Adopt for v0.5 / reject / adopt with different coefficients (e.g., `1 + ceil(size(z)/k)`). Blocked on: bounded-measurement wording above (resolved in principle) and the ADR-003 composition question (open).
