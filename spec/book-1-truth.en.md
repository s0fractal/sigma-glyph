# Σ-GLYPH — Book I: TRUTH

**Version:** 0.5.2
**Type:** Bit-Exact Computational Core
**Status:** DRAFT STANDARD

> **Informative English translation.** This is an English rendering of the
> normative Σ-GLYPH Book I v0.5.2. The canonical, anchored source of record is
> [`book-1-truth.md`](book-1-truth.md) (Ukrainian). In any discrepancy the
> anchored source governs, until the maintainer roster adjudicates and re-anchors
> an English normative edition (§8). All hashes, byte strings, code, tables, ADR
> references, and RFC 2119 keywords are reproduced verbatim.

**Scope:** This document defines everything — and only what — two independent
nodes need in order to reach consensus on the hash of a computation's result.
Everything else (navigation, coordinates, lore) lives in separate documents,
which MUST NOT affect this Book.

The key words MUST / MUST NOT / SHOULD / MAY are per RFC 2119.

---

## 1. Structures

### 1.1. SigmaNodeV2

```text
enum OpCode : uint8 { LITERAL=0x00, REF=0x01, APPLY=0x02, DISSONANCE=0xFF }
// 0x03 and all other values: INVALID (see §1.2)
// Flags: F_ATOM=0x01, F_LEFT=0x02, F_RIGHT=0x04
```

| OpCode     | Flags (MUST equal)  | Semantics                         |
| ---------- | ------------------- | --------------------------------- |
| LITERAL    | `F_ATOM`            | `atom = SHA-256(DataBLOB)`        |
| REF        | `F_ATOM`            | `atom = TargetHash`               |
| APPLY      | `F_LEFT \| F_RIGHT` | `left = Fn`, `right = Arg`        |
| DISSONANCE | `F_ATOM`            | `atom = ReasonHash`               |

`Flags` bits outside the mask `0x07` MUST be zero.

**LITERAL — an inert commitment.** A canonical node holds a digest, not a blob.
The blob is never needed for reduction: LITERAL is a normal form, and combinators
are recognized by NodeHash (§3.2). Retrieving and validating the blob
(`SHA-256(blob) == atom` MUST) is a storage contract outside this Book.

Book I validates only the canonical bytes of a SigmaNodeV2. `resolve(h)` for a
LITERAL does not require the blob: materialization always succeeds (1 ATP) so
long as the node deserializes correctly per §4.1. Absence, availability, or
corruption of the external blob data committed via `atom` MUST NOT change the
canonical result hash, the kind of canonical failure, or the ATP spent that
`eval()` reports. A blob-retrieval API MAY validate `SHA-256(blob) == atom` and
report storage-level failures, but those failures are outside Book I and MUST NOT
be serialized as a Book I DISSONANCE. (ADR-004, gate 4/≥3, 2026-07.)

### 1.2. Invalid opcodes and format versioning

Any opcode outside the table in §1.1 (including `0x03`) makes the buffer invalid
(§4). Extending the node format in a content-addressed system is a rehash by
construction: the canonical bytes are the identity, so a "version bit" would not
provide hash compatibility. The normative degradation for future formats: a V2
validator, on encountering unknown bytes, MUST deterministically materialize the
Canonical Invalid Object (§4.2) — never UB. `0xFF` for DISSONANCE is chosen as a
sentinel maximally distant from the block of data opcodes.

## 2. Canonical Serialization and Hash

* **Layout:** `[Op:1][Flags:1][Atom?:32][Left?:32][Right?:32]`; optional fields
  strictly in the order Atom, Left, Right; `F_ATOM→Atom`, `F_LEFT→Left`,
  `F_RIGHT→Right`.
* **NodeHash = SHA-256(CanonicalBytes)**; internally 32 raw bytes; hex is
  presentation only.

## 3. Reduction Semantics

### 3.1. Rules (SKI Term Rewriting)

`⟨X⟩` — a node whose NodeHash equals the canonical constant X (§5).

```text
R-I:  APPLY(⟨I⟩, x)                    →  x
R-K:  APPLY(APPLY(⟨K⟩, x), y)          →  x
R-S:  APPLY(APPLY(APPLY(⟨S⟩,x),y), z)  →  APPLY(APPLY(x,z), APPLY(y,z))
R-R:  REF(h)                           →  resolve(h)
```

**R-R unfolds exactly one level per step (MUST).** Transitive unfolding in a
single step is forbidden. Under v0.5 pricing (§3.4) a chain `REF→REF→…→T` of
length n costs n·(2+1) = 3n ATP: forcing each REF node (2) plus unfolding it (1);
conformance: vector `EV-TV9`. If the budget runs short — `DISSONANCE(ATP
Exhausted)`, regardless of how many levels remain.

### 3.2. Combinator recognition (MUST)

A node is I/K/S if and only if its NodeHash equals the corresponding constant of
§5.1. Identity by Hash.

### 3.3. The hash-thunk machine and reduction order (MUST)

The v0.5 abstract machine operates on **hash thunks**: a term under reduction is a
graph of materialized nodes whose children are either materialized nodes or
unresolved hashes (thunks). A thunk is compared against ⟨I⟩/⟨K⟩/⟨S⟩ by hash
without materialization; a thunk is materialized only when the leftmost-outermost
search demands it. Every machine action — a rule firing OR the materialization of
one node — is priced (§3.4).

```text
step(t):                                            // one priced action
  if t = thunk(h):
      if h ∈ {H(I),H(K),H(S)}: none                 // NF leaf by hash, §5.1
      else: force(h)                                // materialize one node
  elif t = REF(h):                fire R-R          // → thunk(h), one level
  elif t matches R-I|R-K|R-S at root: fire          // patterns are hash compares,
                                                    // arguments are NOT forced
  elif t = APPLY(f,a):
      if step(f) exists: act in f                   // descend the left spine
      elif step(a) exists: act in a                 // f normal → demand a
      else: none                                    // normal form
  else: none                                        // LITERAL, DISSONANCE
```

**The divergence class is closed normatively:** an unresolved subtree that
leftmost-outermost reduction does not demand — including deadness that appears
only after rewrites — MUST NOT affect the result. `APPLY(APPLY(⟨K⟩, x), missing)`
→ `x`, not Unresolved Reference; `S (K I) (K K) missing` → ⟨K⟩. (ADR-003;
findings by Codex + Gemini + DeepSeek, 2026-07.)

### 3.4. ATP: size-priced, hash-leaf model (MUST)

**Size** (hash-leaf model): each materialized node counts as 1; an unresolved
hash leaf counts as **exactly 1** regardless of what it denotes; a materialized
REF counts as 2 (the node + the thunk of its target); `size(APPLY) = 1 +
size(left) + size(right)`.

**Action prices:**

```text
cost(force h)  = size of the materialized node with thunk children
                 = 1 (LITERAL, DISSONANCE) | 2 (REF) | 3 (APPLY)
cost(R-R)      = 1        // REF node → thunk of the target, one level per step
cost(R-I)      = 1
cost(R-K)      = 1        // the discarded argument is NOT forced and NOT priced
cost(R-S)      = 1 + size(z)   // z in its current materialization; thunks in z = 1, not forced
```

* `eval(term_hash, atp: uint32)` → normal form | `DISSONANCE(ATP Exhausted)` |
  `DISSONANCE(Unresolved Reference)`. All three are canonical, deterministic, and
  identical on all nodes. The result is a node; its NodeHash is the canonical
  address of the result.
* The ATP budget is a `uint32`; ATP > 2³²−1 is implementation-defined (MAY
  reject/clamp); only canonical results are consensus-critical. A single step
  whose price exceeds 2³²−1 is unreachable for any canonical budget → ATP
  Exhausted, not implementation-defined.
* **The exhaustion check precedes the action.** An action whose price is `c > atp
  − spent` is not performed: the result is `DISSONANCE(ATP Exhausted)` with
  `spent` unchanged. The minimum price of any action is 1, so at `spent == atp`
  exhaustion is decided **before** any access to storage (`eval(REF(missing), 0)`
  = ATP Exhausted). When the cost of a force becomes known only after fetching
  the bytes (the node's kind), bytes unaffordable under the budget are discarded
  without materialization — deterministically. A failed action (a resolve
  failure) is not priced. `eval` is total: an internal failure MUST NOT leave
  `eval` as anything other than a canonical `DISSONANCE`. (The v0.4.5 discipline,
  inherited with variable prices.)
* **Semantic memory bound (a theorem, a normative invariant):** along any
  execution `materialized_size(t) − 1 ≤ spent`, where `materialized_size(t)` is
  the **Size** of the current term per this section's definition (a tree
  node-count over the materialized graph; thunks = 1; nodes synthesized by
  reductions count — no "exclusion lemma" is needed, because each rule's increment
  is strictly less than its cost). Every action costs strictly more than the size
  it adds. Consequence for implementations: the bound gives a **preflight**
  estimate of memory from the budget (memory never exceeds `1 + atp`), but `spent`
  is an upper, NOT a lower, bound on size, so a fault-guard keyed on `spent`
  wrongly fails divergent terms of tiny size (Ω); a guard MUST measure the actual
  `size(t)`/depth. (ADR-001 + composition with ADR-003; proof: Gemini review;
  re-derivation: DeepSeek; correction of the guard discipline: Opus 4.8 review M1,
  2026-07.)
* The normative accounting model is tree semantics over the materialized graph:
  sharing MAY be used in execution, but the reported ATP MUST match the tree
  accounting.

### 3.5. Resolution Contract (MUST)

`resolve(h)`/`force(h)` is the single node-materialization operation by hash. Two
failure modes are distinguished explicitly: (a) `h` is not found in storage **and
is not an intrinsic axiom of §5.1** → `DISSONANCE(Unresolved Reference)`; (b) the
bytes fail §4.1 validation → the Canonical Invalid Object (§4.2) is materialized,
and the action is priced as a force of a DISSONANCE node (1).

**Materialization is lazy, on demand of the search (normative since v0.5).** Only
the thunk demanded by the leftmost-outermost search is forced: the left spine for
redex recognition, and the argument only when the functional part is normal. Dead
branches are never forced (§3.3). Historical note: in 0.4.x eager materialization
was normative; changing the results for terms with dead missing branches is a
deliberate breaking change in v0.5 (ADR-003).

### 3.6. Canonical failures vs local faults (MUST)

The canonical results are only the three of §3.4. A breach of an implementation's
local resource limits (depth, fetch count) is an **implementation fault**: an
execution failure that MUST NOT be serialized as a DISSONANCE. Since v0.5 memory
is bounded semantically (§3.4: size ≤ 1 + spent), so size faults are reachable
only at budgets on the order of the limit; guards remain a second fence. The
concrete limits are outside this Book (implementation notes).

### 3.7. Tooling (MAY, non-consensus)

Interfaces such as `trace_eval` (step-by-step trace, intermediate terms,
checkpointing) MAY exist; they are not part of consensus and MUST NOT change the
results of `eval`.

## 4. Validation

### 4.1. Deserialization (MUST)

1. `len >= 2`; read `[Op][Flags]`.
2. `Flags & ~0x07 == 0`; OpCode ∈ the table of §1.1; `Flags` exactly equals the
   normative value.
3. `expected_len = 2 + 32·popcount(Flags & 0x07)`; `len == expected_len`.
4. Any error → Canonical Invalid Object.

### 4.2. Canonical Invalid Object (MUST)

```text
ff01 || SHA-256("Invalid Object")
Bytes: ff017cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8
Hash:  af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507
```

## 5. Genesis

### 5.1. Axioms (nominal)

| Glyph | CanonicalBytes            | NodeHash |
| ----- | ------------------------- | -------- |
| I | `0001`+SHA-256("I") | `2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162` |
| K | `0001`+SHA-256("K") | `bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c` |
| S | `0001`+SHA-256("S") | `887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6` |

The full 32-byte values of SHA-256("I"/"K"/"S") are in `impl/sigma_glyph.py`
(TV-1); they are deliberately not duplicated here, to avoid creating a second
source of truth.

**Genesis intrinsic (MUST, since v0.5).** The three axioms I, K, S are intrinsic
constants: a conforming implementation MUST serve `resolve/force` of their
canonical hashes without depending on those bytes being present in storage — the
bytes are given by this paragraph, and the synthesis is deterministic.
`DISSONANCE(Unresolved Reference)` for H(I)/H(K)/H(S) MUST NOT occur. A thunk with
an intrinsic hash is a normal form without materialization (§3.3). FALSE (§5.2)
is a theorem, not an axiom: it needs no intrinsic status, its bytes are
constructed from H(K), H(I) without storage. (Candidacy: Codex + Gemini;
confirmation without dissent: DeepSeek, 2026-07.)

### 5.2. The First Theorem

`FALSE ≡ APPLY(K,I)`; Bytes `0206‖H(K)‖H(I)`; Hash
`65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098`.

### 5.3. Reason Hashes (MUST)

```text
SHA-256("Invalid Object")       = 7cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8
SHA-256("ATP Exhausted")        = dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd7032e090
SHA-256("Unresolved Reference") = 75daae55453d9a98bfadb847d70b73fdd0be91d3b6ef8511d22fc42aa2c7c8e2
```

**Reserved (Era-1 legacy):** `SHA-256("Signal Damped") =
7dc48fe882dc426083223e5fb26889ace68aa8f54abd4e37690b72327b87748c`. This is a
reserved *reason hash*, not an opcode; it does not affect deserialization. No V2
rule produces this DISSONANCE; the hash is reserved for a possible network layer
(damping) and MUST NOT be used by Book I implementations. (Finding: Qwen review,
2026-07.)

## 6. Canonical Lambda→SKI Compiler, Profile C1 (Normative Annex)

The consensus layer accepts only SKI terms. For inter-human compatibility exactly
one canonical compiler is defined. The input is a closed lambda term (no free
variables); the output is a Book I SKI term.

**Free variables (FV)** are defined in the usual capture-avoiding sense: `FV(x) =
{x}`, `FV(M N) = FV(M) ∪ FV(N)`, `FV(λx.M) = FV(M) \ {x}`. The compiler MUST NOT
bind a variable that is free in its body.

```text
C1[x]        = x
C1[(M N)]    = APPLY(C1[M], C1[N])
C1[λx.M]     = A(x, C1[M])

A(x, x)      = ⟨I⟩
A(x, M)      = APPLY(⟨K⟩, M)                      if x ∉ FV(M)
A(x, (M N))  = APPLY(APPLY(⟨S⟩, A(x,M)), A(x,N))
```

* The A rules are checked strictly in this order. η-reduction and any other
  optimizations MUST NOT be applied in profile C1.
* C1 is deterministic: the same input → the same bytes → the same hash on any
  implementation.
* C1 does **not** minimize and does **not** canonicalize extensionally:
  `C1[λx.λy.x] = S(KK)I ≠ ⟨K⟩` — a separate citizen, extensionally equal to K.
  Decidable extensional equality does not exist (Rice); C1's canonicity is
  syntactic, not semantic.
* Frontends with other profiles MAY exist outside the standard; their artifacts
  are ordinary SKI citizens with no special status.

## 7. Test Vectors (MUST PASS)

**TV-1 (LITERAL I):** Bytes
`0001a83dd0ccbffe39d071cc317ddf6e97f5c6b1c87af91919271f9fa140b0508c6c`; Hash
`2f33694d…330f4162` (full in §5.1).

**TV-2 (FALSE):** Bytes `0206‖H(K)‖H(I)`; Hash `65cd957f…38a32098`.

**TV-3 (DISSONANCE ATP):** Bytes
`ff01dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd7032e090`; Hash
`8bb0006f4c0a51a645877c10db80b7360b0d34f6f826e5737d0847f8b1493176`.

The prices below are v0.5 (size-priced, hash-leaf, §3.4). The exhaustive
machine-checkable set is `tests/spec_conformance/vectors.json` (normative; on any
discrepancy with the prose, the oracle `impl/sigma_glyph.py` wins).

**TV-4 (I·K):** `APPLY(⟨I⟩,⟨K⟩)` hash
`51d8148feda28f17304c9ed6c34d9d548c83a84c380f4dd1ba0a037ceb9d4d3e`;
`eval(·,4)=⟨K⟩`, **4 ATP** (force the root 3 + R-I 1); `eval(·,0)` = ATP Exhausted,
spent 0 — with no access to storage at all; `eval(·,2)` = ATP Exhausted, spent 0 —
the root bytes discarded (force costs 3 > 2); `eval(·,3)` = ATP Exhausted, spent
3.

**TV-5 (SKK·I):** hash
`c9f57b3f594d7b72b0855b0d6fabba89e6ccdf6840c8f84aeb5fd4707300bbfc`;
`eval(·,12)=⟨I⟩`, **12 ATP** (3 forces of 3 + R-S 2 + R-K 1).

**TV-6 (Duplication Stress):** `S I I (I·K)` hash
`0379bafee726f493bffc153163b7165b916efe0bd661cf99bc2f834f36db8198`; normal form
`APPLY(⟨K⟩,⟨K⟩)`; exactly **21 ATP**; along the execution `size − 1 ≤ spent` (the
semantic memory bound, §3.4).

**TV-7 (Omega):** `Ω = (SII)(SII)` hash
`0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211`; `∀n:
eval(Ω,n) = DISSONANCE(ATP Exhausted)`.

**TV-8 (Unresolved Child):** `APPLY(⟨I⟩, ghost)` with ghost absent →
`DISSONANCE(Unresolved Reference)`, spent 4: R-I fires lazily WITHOUT forcing
ghost, then ghost becomes the demanded root and is not forced.

**TV-9 (REF chain):** store: `r1=REF(H(K))`, `r2=REF(r1)`; `eval(r2, 6)=⟨K⟩`,
exactly **6 ATP** (2 forces of 2 + 2 R-R of 1); `eval(r2, 1)` = ATP Exhausted,
spent 0 (force costs 2).

**TV-10 (C1 compiler):** `C1[λx.x] = ⟨I⟩`. `C1[λx.λy.x] =
APPLY(APPLY(⟨S⟩,APPLY(⟨K⟩,⟨K⟩)),⟨I⟩)`, hash
`bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d`;
`eval(APPLY(APPLY(C1[λxy.x],⟨S⟩),⟨K⟩), 20) = ⟨S⟩`, 20 ATP.

**TV-11 (Divergence class, v0.5):** ghost = SHA-256(ASCII `this node was never
stored`), absent from storage. `APPLY(⟨FALSE⟩, ghost)` (= `(K I) ghost`) → ⟨I⟩, 7
ATP; `APPLY(S (K I) (K K), ghost)` → ⟨K⟩, 20 ATP. In 0.4.x both gave Unresolved
Reference — this is a deliberate breaking change (ADR-003).

**TV-12 (Genesis intrinsic, v0.5):** `REF(H(K))` on an **empty** store → ⟨K⟩, 3
ATP. A bare intrinsic thunk: `eval(H(I), n)` = ⟨I⟩, 0 ATP, no store needed.

**Negatives:** flags outside 0x07; Flags not matching the opcode; opcode 0x03;
length ≠ expected — all → Canonical Invalid Object.

## 8. Specification Anchor (Update Protocol)

Every published version of this Book is anchored in the system itself:
`SpecAnchor(v) = NodeHash(LITERAL, atom = SHA-256(document_bytes))`. By
construction the anchor cannot be contained in the document it hashes; it is
published detached (the ANCHORS file / the genesis registry). A change to the
standard = a new LITERAL = a new anchor; an "update" is always a fork with an
explicit ancestor, and version reconciliation is by anchors, not by file names.

---

*This Book defines what is true. All that is warm lives elsewhere.*
