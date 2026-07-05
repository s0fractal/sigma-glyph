# ADR-003: Lazy Left-Spine Resolution (candidate for v0.5)

**Status:** PROPOSED (breaking: changes canonical outcomes for terms with unresolvable dead branches; do not merge into 0.4.x)
**Origin:** Codex follow-up review 2026-07 (eager-vs-lazy APPLY child materialization was unpinned and divergence-prone)
**Definition up front:** "lazy" here means resolution on demand of the *redex search*, not call-by-need sharing. ATP accounting stays tree-semantics.

## Problem

v0.4.x normativizes **eager** materialization (Book I §3.5): resolving an APPLY node recursively resolves both children before redex recognition. Consequence: `APPLY(APPLY(K, I), missing)` → `DISSONANCE(Unresolved Reference)`, even though normal-order reduction discards the missing argument without ever needing it.

This is safe and deterministic, but it has two costs:

1. **Liveness:** withholding any stored node — even one the computation provably never uses — blocks evaluation. The withholding attack surface (Book I attack table: "liveness, not safety") extends to dead branches.
2. **Semantic purity:** normal order's defining virtue is that K discards its argument *unevaluated*. Under eager materialization it is discarded unevaluated but not unfetched.

## Candidate rule

Redex recognition needs only hashes already present in materialized nodes (an APPLY node carries its children's 32-byte hashes; `is_glyph` is a hash comparison):

```text
resolve on demand, demand defined by leftmost-outermost search:
  - the root MUST resolve;
  - to test root redex patterns, resolve the left spine only
    (f, then f.left, then f.left.left — as deep as the patterns require);
  - an argument is resolved only when the search descends into it
    (i.e., when the function side is already in normal form)
    or when a fired rule makes it the new root/spine.
```

Under this rule:

```text
APPLY(APPLY(K, I), missing)  ->  I                      (dead arg never fetched)
APPLY(I, missing)            ->  R-I fires (1 ATP), missing becomes root,
                                 root resolve fails -> Unresolved Reference, spent=1
```

## Breaking impact

- `APPLY(APPLY(K,·), missing-dead-arg)` flips outcome: Unresolved Reference → normal form. Conformance vector `EV-K-DEAD-MISSING` (pinned in v0.4.5) inverts.
- TV-8-shaped terms keep their outcome but change `atp_spent` (0 → 1 in the example above): the firing now precedes the failed resolve.
- Book I §3.5 eager paragraph is replaced; Specification Anchor bumps.

## Synergy with ADR-001

Size-priced ATP charges `cost(R-R) = size(resolve(h))`. Under eager materialization a term pays fetch/validation for branches it never reduces; under lazy spine resolution, dead branches cost nothing — the two proposals compose into "you pay for exactly what the reduction touches."

## Trade-offs

- (+) Liveness: dead data cannot block computation.
- (+) Purest reading of normal order; natural for hash-level (Rust/Zig) implementations that never build a full tree.
- (−) Implementations must interleave resolution with search (thunks/hash-children); the reference oracle needs a representation change.
- (−) "Is this term evaluable?" is no longer equivalent to "is its full closure present?" — tooling that prefetches closures must not assume completeness is required.

## The divergence class (added per Codex ADR-gate review, 2026-07)

The direct-K case above is the *minimal* lazy/eager hash divergence, not the class. The class is:

> Any unresolved subtree that is not demanded by leftmost-outermost evaluation MUST NOT affect the result — including subtrees whose deadness appears only after one or more rewrites.

Verified members beyond direct K (oracle-checked on the eager side; lazy side derived and cross-checked with a present-value surrogate that the reduction never demands):

```text
EV-K-DEAD-NESTED-MISSING:  APPLY(APPLY(K,I), APPLY(I,missing))
  eager -> Unresolved Reference, 0 ATP;  lazy -> I, 1 ATP
EV-S-KI-KK-DEAD-Z:         S (K I) (K K) missing
  eager -> Unresolved Reference, 0 ATP;  lazy -> K (4 ATP: R-S, R-K, R-I, R-K)
```

The v0.5 vector set MUST include both a direct-K and an S-composed dead argument, and MUST pin the exact bytes of the `missing` hash (the root hash depends on it).

## Hash-thunk machine + genesis constants — OPEN

The abstract evaluator operates on hash thunks: a thunk MAY be compared against `I_H/K_H/S_H` without fetching bytes; a thunk is resolved only when it becomes the demanded root/spine position for the next transition.

**Decision candidate (2026-07-05, Codex + Gemini concurring): Genesis Intrinsic Rule.** The three *axioms* I/K/S (Book I §5.1) are intrinsic constants: implementations MUST NOT produce Unresolved Reference for their canonical hashes — their bytes are spec-pinned and derivable from the glyph names. Scoping correction (maintainer): FALSE is the First Theorem (§5.2), not an axiom, and needs no intrinsic status — its canonical bytes `0206‖H(K)‖H(I)` are constructible from intrinsic hashes without any store. Non-genesis hashes in the demanded spine MUST resolve in the store to be reported as part of a normal form, unless syntactically constructed by a completed rewrite. Needs vectors: bare `REF(K_H)` with empty store → K; bare unknown hash root → Unresolved.

**CONFIRMED by review 3 (DeepSeek): no consensus-divergence scenario** — synthesis-by-spec and store-lookup agree by collision resistance; a faulty store is caught by resolve validation. Adoption-PR text for Book I §5.1 (adopted from DeepSeek): *"Genesis intrinsic. The three axioms I, K, S are intrinsic constants. A conforming implementation MUST honour `REF(H(I|K|S))` without depending on the presence of those hashes in storage. The bytes are as given in this section; synthesis is deterministic."*

## Composition with ADR-001 — decision candidate: Hash-Leaf Size Model

See ADR-001 → "Composition with lazy resolution": resolved to a proved candidate (2026-07-05, Gemini ADR-gate review) — `size(t)` counts materialized nodes with unresolved hash leaves as 1; R-S never forces what it copies; R-R pays for exactly what it materializes; `growth < cost` holds globally. Final adoption gated on review 3 + hash-thunk reference implementation + vectors.

## Adoption criteria

Per ROADMAP → Decision Process: ≥3 independent model reviews, reference impl with updated vectors ALL PASS, maintainer adjudication with written rationale. Additionally blocked on: divergence-class vectors, hash-thunk machine decision, ADR-001 composition.
