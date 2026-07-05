# Σ-GLYPH — Appendix A: Complexity (NON-NORMATIVE)

**Version:** 0.4.6 (accompanies Book I 0.4.5)
**Status:** NON-NORMATIVE. Nothing here is a contract between nodes. Bounds describe the v0.4.x semantics (tree accounting, eager materialization); consensus lives in Book I only.
**Origin:** Claude Sonnet 4.5 review 2026-07, P3.1.

---

## 1. Per-rule size dynamics (exact, tree semantics)

Let `s(t)` be node count. Each rule fires for exactly 1 ATP in v0.4.x:

| Rule | Rewrite | Δsize |
|------|---------|-------|
| R-I | `(I a) → a` | −2 |
| R-K | `((K x) y) → x` | −(3 + s(y)) |
| R-S | `(((S x) y) z) → ((x z) (y z))` | **+ s(z) − 1** |
| R-R | `REF(h) → resolve(h)` | **+ s(resolve(h)) − 1** |

Only R-S and R-R grow the term, and each by strictly less than the size of the
node they duplicate/materialize. This is the seed of ADR-001's linear memory
bound: under size-priced ATP, `Δsize < cost` per step.

## 2. Worst-case growth is O(2^ATP) — but must be crafted

R-S can duplicate an argument that previous R-S firings already doubled:
`s_{n+1} ≤ 2·s_n`, hence `s_n ≤ s_0 · 2^n`. The bound is tight only for
deliberate duplication towers (each S feeding its own output back as `z`).

**Omega is NOT the worst case.** Measured (tool: `tools/complexity_metrics.py`,
integer-deterministic, machine-independent):

| term                | budget | spent | size_0 | size_max | depth_0 | depth_max | fetches | outcome       |
|---------------------|--------|-------|--------|----------|---------|-----------|---------|---------------|
| TV-4  I K           | 10     | 1     | 3      | 3        | 2       | 2         | 3       | normal form   |
| TV-5  S K K I       | 10     | 2     | 7      | 7        | 4       | 4         | 7       | normal form   |
| TV-6  S I I (I K)   | 100    | 5     | 9      | 11       | 4       | 4         | 9       | normal form   |
| TV-7  Omega, 200    | 200    | 200   | 11     | 87       | 4       | 23        | 11      | ATP Exhausted |
| TV-7  Omega, 1000   | 1000   | 1000  | 11     | 187      | 4       | 48        | 11      | ATP Exhausted |
| TV-9  REF→REF→K     | 10     | 2     | 1      | 1        | 1       | 1         | 3       | normal form   |
| TV-10 C1[λxy.x] S K | 16     | 4     | 11     | 11       | 6       | 6         | 11      | normal form   |

Omega's duplicated argument is the fixed subterm `S I I` (size 5), so growth is
**linear** (~1 node per 8 steps), not exponential. Real programs compiled via
C1 behave closer to TV-10 than to adversarial towers. The exponential envelope
matters for validator sizing, not for typical cost estimation.

## 3. Time

One step = leftmost-outermost redex search + rebuild, both O(size of the
current term). Whole evaluation:

```text
time(eval) = O( Σ_k size_k )  ⊆  O( ATP · size_max )
           ⊆  O( ATP · s_0 · 2^ATP )              worst case, v0.4.x
           →  O( ATP · (s_0 + ATP) )              under ADR-001 (size_max ≤ s_0 + ATP)
```

ATP bounds *work* (rule firings). It bounds neither memory nor wall-time
directly in v0.4.x — that is exactly the §3.6 quarantine and the ADR-001
motivation.

## 4. Space and fetches

- **Peak term size:** `size_max ≤ s_0 · 2^ATP` (v0.4.x); `≤ s_0 + ATP` under ADR-001.
- **Eager materialization (§3.5):** peak memory also includes the *full closure*
  of the root hash, resolved before reduction — even dead branches. ADR-003
  (lazy left-spine) would shrink this to the reduction-touched spine.
- **Fetches:** the reference oracle fetches the root closure once per `eval`
  plus one fetch per R-R firing (see `fetches` column; TV-9: 1 root + 2 R-R).

## 5. Implementation faults (§3.6 reminder)

Depth/size/fetch limits are local faults, never DISSONANCE. As of v0.4.6 the
reference oracle also maps host recursion exhaustion (`RecursionError`) to
`ResourceFault`: a term within `max_node_depth` MUST evaluate to a canonical
outcome, and a term beyond it MUST fault — never crash raw. Implementations in
languages with bounded call stacks should either recurse-proof their walkers
or size their stack to the advertised depth limit.

---

*Regenerate the table: `python3 tools/complexity_metrics.py`. If the table and
the tool disagree, the tool wins — same rule as Book I and its oracle.*
