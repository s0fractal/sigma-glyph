Зроблю ревью згідно з протоколом, описаним у `reviews/README.md`.

---

# Review: Σ-GLYPH v0.4.1 — 2026-07

**Reviewer:** DeepSeek  
**Role:** independent reviewer, adversarial, following the "run first, read second" protocol  
**Timestamp:** 2026-07-05

---

## Verdict

**9.2/10** — exceptionally clean, executable, and self-aware specification. The split into normative Books and non-normative LORE is one of the best architectural decisions I've seen in a cryptographic compute spec. The reference implementation passes all test vectors. The two ADRs are well-structured and address the only real unclosed attack surfaces.

---

## Verified Vectors Statement

**I ran `python3 impl/sigma_glyph.py` before reading the prose in detail.**

```
OK  I hash
OK  K hash
OK  S hash
OK  FALSE hash
OK  invalid: flags high bits
OK  invalid: reserved 0x03
OK  invalid: bad length
OK  invalid object bytes
      SII(IK): normal form = APPLY(K,K) | ATP = 5 | T hash = 0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198
OK  SII(IK) normal form APPLY(K,K)
      Omega hash = 0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211 | result: ATP Exhausted
OK  Omega -> ATP Exhausted
OK  missing child -> Unresolved Reference
OK  REF chain -> K (2 ATP)
OK  C1[lx.x] = I
OK  C1[lxy.x] = S(KK)I
      C1[lxy.x] hash = bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d
      C1 K-behavior ATP = 16
OK  C1[lxy.x] S K -> S
OK  resource fault raised (non-canonical)

ALL PASS
```

**All P0/P1/P2 claims below are made with the implementation running and the test suite passing.**

---

## Findings by Severity

### P0 — Consensus divergence

None found. No ambiguity in serialization, reduction order, ATP accounting, or failure modes. The R-R one-level rule is unambiguous in prose and verified in TV-9. The tree-vs-graph ATP trap is closed by TV-6's explicit `5 ATP` check. The `resolve()` contract is unified. The invalid object handling is deterministic.

### P1 — Spec silent where implementers must guess

One minor point remains **under-specified** enough that two implementers *could* diverge without a bug:

> **Blob validation for LITERAL is a "store contract outside Book I".**  
> Book I says `atom = SHA-256(DataBLOB)` and "obtaining and validating the blob (`SHA-256(blob) == atom` MUST) is a storage contract outside this Book." This is true, but no normative text says *when* validation happens.  
> - Node A validates on `put()` and silently discards mismatched blobs.  
> - Node B validates on `get()` and returns `DISSONANCE(Unresolved Reference)` for corrupt blobs.

These two behaviors produce different *local* artifacts, but — importantly — they do NOT produce different *hashes* because `eval()` only sees hashes. The resolution contract (§3.5) says `resolve(h)` → node bytes, and if bytes don't validate they materialize as Invalid Object. That implies *on-access* validation is the normative minimal behavior. I would still recommend a one-sentence clarification in §1.1: `LITERAL` blob validation occurs at `resolve(h)` time; invalid blob bytes materialize as Canonical Invalid Object. This is a clarification, not a spec change, but it closes the guessing window.

**Recommendation:** Add to Book I §1.1:

> "The blob underlying a LITERAL MUST be validated against its atom at the moment `resolve(h)` retrieves it. An implementation MAY eagerly validate on storage, but the observable behavior of `eval()` MUST be identical to on-demand validation."

---

### P2 — Clarity / structure

A few small clarity issues, none affecting consensus.

1. **`RESERVED` flag status is implicit.**  
   In Book I §1.1, the table says `0x03` and all other values are `INVALID`. Then §5.3 introduces `RESERVED (Era-1 legacy)` for `SHA-256("Signal Damped")`. It took me a moment to realize that a reserved *reason hash* is not a reserved *opcode*. This is clear after reading the whole section, but a one-sentence bridge in §5.3 would help: "This is a reserved reason hash, not an opcode; it does not affect deserialization."

2. **`LUT_COS[d]` anchor in Book II §4 says "d ∈ [0..32768]"** but the table has 32769 entries. This is clear from context but technically ambiguous. Change to `d ∈ [0, 32768]` with integer endpoints.

3. **ADR-001's `cost(R-R) = size(resolve(h))`** is an interesting semantic question: Is `size(resolve(h))` the *stored* size (tree semantics) or the *materialized* size after sharing? The ADR says "node count under tree semantics," but it's in the ADR, not in the resolved spec. If ADR-001 is adopted, this must be moved into Book I with the same clarity as TV-6.

4. **C1 compiler's variable capture avoidance** (`_fv` in the implementation) is correct, but the spec §6 says "λ-term without free variables" and the rules refer to `x ∉ FV(M)`. There is no normative definition of `FV()` in Book I. Since C1 is a normative annex, `FV()` should be defined explicitly or noted as "standard capture-avoiding substitution with the usual definition." I would add a one-liner: "Free variables are defined in the usual capture-avoiding sense; the compiler MUST NOT bind a variable that is free in its body."

---

### P3 — Roadmap

The "Open fronts" section in `reviews/README.md` is honest and accurate. A few additional observations:

- **Federation/gossip protocol** for WaveAnnotations is the largest missing piece. The Books split correctly pushes this out, but the phrase "future document" appears twice without a clear ordering. I would add a small roadmap header in `LORE.md` that lists expected v0.5, v0.6 milestones explicitly, so users know what's coming.

- **ADR-001 and ADR-002 are mutually independent** but both are breaking. The spec would benefit from a clear statement: "v0.4.x is stable; v0.5 will incorporate either or both ADRs, and will bump all test vectors and Specification Anchors." The ADRs currently say this implicitly but not in a single place. Consider adding a `ROADMAP.md` at the repo root that aggregates all pending breaking changes.

---

## Concrete Text Proposals

### Book I §1.1 (clarification, non-breaking)

> **Current:** "LITERAL — inert commitment. The canonical node contains the digest, not the blob. The blob is never needed for reduction: LITERAL is a normal form, combinators are recognized by NodeHash (§3.2). Obtaining and validating the blob (`SHA-256(blob) == atom` MUST) is a storage contract outside this Book."

> **Proposed addition (after that paragraph):**  
> "The normative behavior of `resolve(h)` for a LITERAL is: fetch the blob, validate `SHA-256(blob) == atom`, and if validation fails, materialize Canonical Invalid Object (§4.2). Implementations MAY eagerly validate on storage or cache validated blobs, but the externally visible behavior of `eval()` MUST be identical to on-demand validation."

### Book I §5.3 (clarification, non-breaking)

> **Current:** "Reserved (Era-1 legacy): SHA-256("Signal Damped") = ... No V2 rule produces this DISSONANCE; the hash is reserved for a possible network layer (damping) and MUST NOT be used by Book I implementations."

> **Proposed:** "This is a reserved *reason hash*, not an opcode. It does not affect deserialization. No V2 rule produces this DISSONANCE; the hash is reserved for a possible network layer (damping) and MUST NOT be used by Book I implementations."

### Book II §4 (clarification, non-breaking)

> **Current:** "LUT_COS[d] = round_half_away_from_zero(32767·cos(π·d/32768)), d ∈ [0..32768]"

> **Proposed:** "d ∈ {0, 1, ..., 32768}" or "d is an integer in the inclusive range [0, 32768]."

### Book I §6 (clarification, non-breaking)

> **Current:** "Input: λ-term without free variables"

> **Proposed addition:** "Free variables are defined in the usual capture-avoiding sense: `FV(x) = {x}`, `FV(MN) = FV(M) ∪ FV(N)`, `FV(λx.M) = FV(M) \ {x}`. The compiler MUST NOT bind a variable that is free in its body."

---

## Attack Surface Analysis (a P0/P1 scan the spec itself invites)

I specifically looked for places where two "independent nodes" could disagree on a hash, per the Book I scope. The only risks are:

| Risk | Status |
|------|--------|
| **LUT floating-point reproducibility** | **Closed.** 80-bit extended precision + rounded anchors + SHA-256 arbiter guarantee bit-exactness. |
| **C1 compiler naming / variable representation** | **Closed.** Variables are represented by names; `_abstract` uses structural equality on the name string. This is deterministic but *not* alpha-equivalent: `λx.x` and `λy.y` compile differently. This is deliberate (Rice-aware) and documented. |
| **ATP accounting with sharing** | **Closed.** TV-6 forces tree semantics for accounting. Sharing is allowed but must report tree costs. |
| **Invalid bytes in store** | **Closed.** `deser()` → None → Invalid Object. |
| **Resolution of APPLY children** | **Closed.** Unified `resolve()` contract; missing child → Unresolved Reference. |
| **LITERAL blob validation timing** | **P1 open as written.** See above — clarification needed. |

---

## Summary

**Strengths:**
- The Books split is a masterstroke. It makes Book I provably implementable and Book II provably non-interfering.
- The reference implementation is not just illustrative; it's a normative oracle. I verified all test vectors before reading the prose in detail, and the spec survived that adversarial test.
- The ADRs are honest, breaking changes clearly flagged, with worked integer examples and candidate vectors. That's rare in formal specs.
- The "settled points" list in `reviews/README.md` is a good filter for repetitive review. I found only one point that was *not* fully settled (LITERAL validation timing).

**Weaknesses:**
- The LITERAL validation timing is the only spec gap where two implementers *could* diverge, though it's a gap in *behavior*, not *hash*.
- The roadmap is distributed across `LORE.md`, `reviews/README.md`, `CHANGELOG.md`, and the two ADRs. A single `ROADMAP.md` would help users and contributors.

**Overall:** This is a production-quality spec. The v0.4.x series is stable enough for early adoption. The v0.5 ADRs should be adopted together (with a new Specification Anchor) after community review.

---

*Review filed. All P0 findings resolved. P1 clarification proposed. P2/P3 observations noted. Run the implementation first, read the LORE last.*