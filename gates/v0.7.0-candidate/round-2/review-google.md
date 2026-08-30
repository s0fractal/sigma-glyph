<!--
family: google
model_requested: google/gemini-3.1-pro-preview
model_answered: google/gemini-3.1-pro-preview
requested_utc: 2026-08-29T17:04:27+00:00
answered_utc: 2026-08-29T17:06:33+00:00
finish_reason: stop
prompt_sha256: 7b7cb164bbb90151e61bcef8fd0cf92362d57432ef157767ce447251f1682ddb
system_sha256: a87d162d7a1c13ce15756bcf1565daf55701b91fd7e47ed432dfae4d3a819d2a
frozen_commit: 1e91131c891dcc8f8b02ee27957330ab2251e2b6
response_sha256: ed502d282ca8db739c591202f409a4d04925f4c3cc6aeb590a7074b5e0989caa
verdict: ADOPT
-->

This candidate is a rigorous, mathematically sound, and comprehensive repair of the Book I abstraction. It resolves the P0 and P1 findings from the previous gate without introducing new contradictions, and the edge cases are explicitly and carefully closed.

Here is the check of the claims and math:

**1. The Memory Bound Theorem (`size - 1 <= spent`)**
The proof holds exactly as stated. The maximum size increase per action is always strictly less than its ATP cost.
- `force(APPLY)` costs 3 ATP. The thunk (size 1) is replaced by an APPLY node (size 1) + 2 unresolved children (size 2) = new size 3. Increase = 2. `2 < 3`.
- `force(REF)` costs 2 ATP. Thunk (size 1) replaced by REF (size 1) + 1 child (size 1) = new size 2. Increase = 1. `1 < 2`.
- `R-S` costs `1 + size(z)`. The rewrite replaces `APPLY(APPLY(APPLY(S, x), y), z)` with `APPLY(APPLY(x, z), APPLY(y, z))`. Under the normative tree-accounting (no sharing), LHS size is `4 + size(x) + size(y) + size(z)`. RHS size is `3 + size(x) + size(y) + 2*size(z)`. The size increase is exactly `size(z) - 1`. The cost is `size(z) + 1`. The difference is strictly 2. `size(z) - 1 < size(z) + 1`.
Because every action's cost strictly exceeds the size it adds, the inequality `size - 1 <= spent` acts as an invariant throughout the evaluation.

**2. The CAS Property and Demand-Scoped Validation**
The candidate correctly fixes the P1 regarding when the environment (`env`) is validated. By specifying:
> *"Властивість MUST перевірятися для кожного хеша, який виконання фактично розв'язує; запис, якого виконання не вимагало, не впливає на результат."*
The spec elegantly distinguishes between the map's integrity (does the entry hash to the key?) and the node's validity (is it a valid `SigmaNodeV2`?). If the map lies, it's a local fault (the verifier refuses to compute). If the map is honest but the bytes are garbage, it falls under §4.1 and yields the `Canonical Invalid Object`. This perfectly bounds the blast radius of poisoned entries and prevents consensus divergence.

**3. `GOV-anchors.md` Pinning (the Unresolved P0 from Round 1)**
The candidate deliberately left the pinned dependencies in `GOV-anchors.md` at `v0.5.2 / 0.6.1 / 0.6.1`. This is **not a P0**, and Kimi's reading in the ADR is correct. A verifier authorizing the `v0.7.0` release blob applies the 7-step frozen mechanism of `GOV-anchors.md` §3. Step 2 requires schema validity and jurisdiction matching; nowhere does it require a string-matching validation of English prose from previous versions against the current bundle. Any verifier that fails the release because of the prose in `GOV-anchors.md` is violating the frozen 7-step mechanism and is non-conforming. Furthermore, `GOV-anchors`'s only semantic dependency on Book I is `NodeHash(LITERAL, SHA-256(bytes))`, which this candidate guarantees is untouched, leaving the mathematical binding intact.

**4. Wave Vectors Math (`div_round_half_up`)**
The phrasing about floor vs round-half-up causing a divergence on negative odd sums is mathematically correct. `avg(-1, -2) = -1.5`. Under `round-half-away-from-zero`, this yields `-2`. Added to `delta_en = -256`, the result is `-258`. If an implementer mistakenly used integer truncation (which in C/C++ or Go truncates towards zero: `-3 / 2 = -1`), the result would incorrectly be `-257`. Vector `WV-NEG-TIE` rightfully enforces this.

**5. Normative Precedence over Prose**
The candidate removes the reference implementation's status as an oracle over the prose and replaces it with the only correct rule for a standard: the prose and the vectors MUST be mutually consistent, and an edition where they diverge is non-conformant. The specific fields linking the prose to the vector schemas are properly defined for all three Books.

No contradictions, no unenforceabilities, no missing bounds.

VERDICT: ADOPT
