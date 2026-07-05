# Σ-GLYPH — Appendix A: Complexity (NON-NORMATIVE)

**Version:** 0.5.0 (accompanies Book I 0.5.0)
**Status:** NON-NORMATIVE. Nothing here is a contract between nodes. Bounds describe the v0.5 semantics (hash-thunk machine, size-priced ATP, hash-leaf sizes); consensus lives in Book I only.
**Origin:** Claude Sonnet 4.5 review 2026-07, P3.1; rewritten for v0.5.

---

## 1. Per-action dynamics (exact, hash-leaf model)

Let `s(t)` be the hash-leaf size (Book I §3.4). Every action strictly earns its cost:

| Action | Cost | Δsize | Δsize < cost |
|--------|------|-------|--------------|
| force LITERAL/DISSONANCE | 1 | 0 (leaf for leaf) | ✓ |
| force REF | 2 | +1 | ✓ |
| force APPLY | 3 | +2 | ✓ |
| R-R (REF unwrap) | 1 | −1 | ✓ |
| R-I | 1 | ≤ −2 | ✓ |
| R-K | 1 | ≤ −(3 + s(y)) | ✓ |
| R-S | 1 + s(z) | + s(z) − 1 | ✓ |

**Memory bound (normative in Book I §3.4, verified here):** by induction over the table, `s(t) − 1 ≤ spent` along any evaluation. ATP is now a joint work-AND-memory bound — the v0.4 O(2^ATP) blow-up is gone by construction, and with it the preflight-OOM concern: forcing materializes one node at a time, each priced 1–3.

## 2. Time

One action = leftmost-outermost search (O(size of the materialized spine), with
O(1) glyph checks by hash) + O(1)–O(s(z)) rebuild. Whole evaluation:

```text
time(eval) = O( Σ_k size_k )  ⊆  O( spent² )     // size_k ≤ 1 + spent_k
```

Quadratic worst case in the budget, linear memory — a validator can size both
from `atp` alone before evaluating anything.

## 3. What you pay to look

Confirming a stored term normal requires forcing it — priced like everything
else. `eval(huge_tree_hash, small_atp)` exhausts deterministically instead of
materializing the tree: **the eager-verification DoS of v0.4.x is closed by
pricing, not by guards.** Conversely, dead branches are never forced (§3.3), so
`S (K I) (K K) missing` reaches ⟨K⟩ having paid nothing for `missing`.

## 4. Measured (deterministic, machine-independent)

Tool: `tools/complexity_metrics.py`. Note Omega: materialized size is now
*paid for* — 67 nodes at 500 ATP, 139 at 2000, `size−1 ≤ spent` throughout.

| term                  | budget | spent | size_max | depth_max | fetches | size-1<=spent | outcome       |
|-----------------------|--------|-------|----------|-----------|---------|---------------|---------------|
| TV-4  I K             | 100    | 4     | 3        | 2         | 1       | yes           | normal form   |
| TV-5  S K K I         | 100    | 12    | 7        | 4         | 3       | yes           | normal form   |
| TV-6  S I I (I K)     | 100    | 21    | 7        | 4         | 5       | yes           | normal form   |
| TV-7  Omega, 500      | 500    | 500   | 67       | 18        | 33      | yes           | ATP Exhausted |
| TV-7  Omega, 2000     | 2000   | 1998  | 139      | 36        | 71      | yes           | ATP Exhausted |
| TV-9  REF->REF->K     | 100    | 6     | 2        | 1         | 2       | yes           | normal form   |
| TV-10 C1[\xy.x] S K   | 100    | 20    | 11       | 5         | 5       | yes           | normal form   |
| TV-11 S(KI)(KK) ghost | 100    | 20    | 9        | 4         | 5       | yes           | normal form   |

## 5. Implementation faults (§3.6 reminder)

Depth/fetch limits remain local faults, never DISSONANCE. The size guard is
free (`1 + spent > limit`); the depth guard needs a traversal and MAY be
amortized — its cadence is an implementation choice, since it can never change
a canonical outcome. The reference oracle maps host recursion exhaustion
(`RecursionError`) to `ResourceFault`.

---

*Regenerate the table: `python3 tools/complexity_metrics.py`. If the table and
the tool disagree, the tool wins — same rule as Book I and its oracle.*
