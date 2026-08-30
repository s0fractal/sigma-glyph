# Σ-GLYPH — Book I: TRUTH

**Version:** 0.6.0
**Type:** Bit-Exact Computational Core
**Status:** DRAFT STANDARD

> **Informative English translation.** This is an English rendering of the
> normative Σ-GLYPH Book I v0.6.0. The canonical, anchored source of record is
> [`book-1-truth.md`](book-1-truth.md) (Ukrainian). In any discrepancy the
> anchored source governs, until the maintainer roster adjudicates and re-anchors
> an English normative edition (§8). All hashes, byte strings, code, tables, ADR
> references, and RFC 2119 keywords are reproduced verbatim.
>
> **That last sentence is checked, not promised.** `tools/spec_audit.py` requires
> this file and the normative one to carry the same 64-hex hashes in the same
> order, the same RFC 2119 keywords in the same order, and the same code blocks
> once translated words are set aside; it also re-derives every constant printed
> here from the constructions printed here. CI fails if the two texts drift.
>
> **This file is not anchored.** `spec/ANCHORS.txt` anchors the normative Book,
> not this rendering, so these bytes carry no integrity guarantee of their own —
> only the checked relationship above. If you are implementing from this text, read
> [`IMPLEMENTING.md`](IMPLEMENTING.md) first: it shows that every constant is
> derivable without our code, and states the two places where the Book still
> points at an implementation.

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

**Size — the semantic materialization measure** (hash-leaf model): each materialized node counts as 1; an unresolved
hash leaf counts as **exactly 1** regardless of what it denotes; a materialized
REF counts as 2 (the node + the thunk of its target); `size(APPLY) = 1 +
size(left) + size(right)`.

**What this bound is not (MUST NOT be read more widely).** `size` counts
materialized nodes. The bound `size ≤ spent + 1` is a statement about **semantic
materialization** and MUST NOT be presented as a bound on resident set size, heap
bytes, evaluator stack, the store's own index, hashing buffers or allocator
behaviour. The correspondence between this measure and a process's physical
resources is a separate refinement layer that this Book does not prove.

**Action prices:**

```text
cost(force h)  = size of the materialized node with thunk children
                 = 1 (LITERAL, DISSONANCE) | 2 (REF) | 3 (APPLY)
cost(R-R)      = 1        // REF node → thunk of the target, one level per step
cost(R-I)      = 1
cost(R-K)      = 1        // the discarded argument is NOT forced and NOT priced
cost(R-S)      = 1 + size(z)   // z in its current materialization; thunks in z = 1, not forced
```

* **Interface (MUST).** `eval(term_hash, atp: uint32, env)` → `Receipt`, where
  `env` is a **content environment** (§3.5): a partial map from NodeHash to bytes.
  Three inputs, not two — a demanded hash absent from the environment is a
  canonical result (§3.5), so content availability sits inside the semantics
  rather than beside them.

* **Receipt (MUST).** `Receipt = { exit, result_hash, atp_spent }`, where
  `exit ∈ { normal_form, atp_exhausted, unresolved_reference }`. All three exits
  are canonical, deterministic and identical on all nodes given the same
  **demanded** environment (§3.5). `result_hash` is the NodeHash of the term the
  machine returned.

* **`result_hash` alone does not identify `exit` (MUST NOT rely on it).**
  `DISSONANCE(ATP Exhausted)` is an ordinary term: it can sit in an environment
  and evaluate to a normal form, so the same `result_hash` means "finished" or
  "ran out" depending on how it was reached. A caller that must tell them apart
  MUST read `exit`.

* **Compatibility profile (MAY).** An implementation MAY offer the two-value form
  `eval(term_hash, atp, env) → (result_term, atp_spent)`. It loses no guarantee of
  this Book and is not deprecated; the one question it cannot answer is `exit`.
* The ATP budget is a `uint32`. A value outside that domain is not a budget: it
  MUST be refused per §3.6 — locally, before the environment is consulted, and
  not as a canonical exit. An implementation MUST NOT accept it by clamping to
  2³²−1: clamping turns a refusal to admit into a result of evaluation, and two
  engines, one of which clamps, diverge on the same input. Only canonical results
  are consensus-critical. A single step
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

**Content environment (MUST).** `env` is a partial map from hash to bytes with one
property: `SHA-256(bytes) = key` for every entry. The check is over the **raw
buffer and before §4.1 validation**: a buffer that fails validation does not
violate this property — it is failure mode (b) below and yields the Canonical
Invalid Object. "Is this a valid node" and "do these bytes belong under this key"
are different questions and must not be conflated: the first has a canonical
answer, the second has no canonical answer at all.

Bytes under a key they do not hash to **MUST NOT** be evaluated as that key's
node: they may be a perfectly valid SigmaNodeV2, and evaluating them would
violate Identity by Hash (§3.2) and let two conforming engines disagree while
both believe they are following the Book. The property MUST be checked for every
hash the evaluation actually resolves, and a mismatch detected on a resolved hash
MUST yield a local refusal (§3.6), not a canonical result.

An entry the evaluation never demanded **MUST NOT** change any canonical
`Receipt`: given the same answers to the demanded hashes, two conforming
implementations return the same `Receipt`, whatever else the environment holds.
That does not forbid a verifier from declining an environment for its own
reasons, including checking it more widely than the evaluation requires. Such a
step is **admission** (§3.6), not evaluation: it produces no `Receipt`, so there
is nothing to disagree about, and it MUST NOT be presented as a result of
evaluation.

**Determinism is over the demanded environment (MUST).** Two implementations that
resolve the same **demanded** hashes to the same bytes return the same `Receipt`.
Stating identity of results without that condition would be false: a node holding
the bytes reaches a normal form where a node without them returns
`DISSONANCE(Unresolved Reference)`.

**Extending the environment (MUST).** Adding content can change **only** an
`unresolved_reference` exit. A settled exit — `normal_form` or `atp_exhausted` —
MUST remain the same `Receipt` under any extension that preserves the answers to
already-demanded hashes. (Mechanized as `EvalMachine.evalHash_stable`; the
differential bridge is `proofs/store_mono_bridge_check.py`.)

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

**Admission is a required deployment boundary (MUST), and not a canonical exit
(MUST NOT).** `eval` is total, so a stranger's term always terminates; that is not
the same as being affordable to run. A `uint32` admits up to 4,294,967,295 priced
actions, and because `size ≤ spent + 1` the budget chosen is also a licence over
memory. A verifier MUST therefore be able to refuse **before** executing, on a
budget it declines to spend. Such a refusal MUST NOT be serialized as a DISSONANCE
and MUST NOT be presented as the result of the computation: it says the verifier
declined, not what the term is. The concrete limit is local policy, outside this
Book.

**Input outside the declared domain (MUST).** An `atp` that is not a `uint32`, and
a `term_hash` that is not exactly 32 bytes, MUST be refused the same way —
locally, before the environment is consulted, and not as a canonical exit. This
changes behaviour relative to 0.5.2, where such values were accepted; the change
is deliberate, and an implementation MUST NOT present a refusal to admit as a
canonical result.

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

For `X ∈ {I,K,S}`, `SHA-256("X")` denotes SHA-256 of exactly one ASCII byte `X`,
with no quotation marks and no terminator. The values are fully determined by this
construction and are deliberately not duplicated here, to avoid creating a second
source of truth; the reference implementation is not a normative source for them.

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
machine-checkable set `tests/spec_conformance/vectors.json` is a normative part of
this edition. The prose of §7 and the records of the set MUST be mutually
consistent. An edition in which they disagree is non-conformant and MUST NOT be
used as a source of consensus until it is corrected and re-anchored. No
implementation, the reference one included, takes precedence over the normative
artifacts of the edition.

**What exactly must agree (MUST).** For each §7 test vector, the normative
representation of the prose's statement in the set is the record's fields: the
subject of the evaluation (`term` or `bytes`), the budget (`atp`), the
**canonical exit** (`expected.exit`), the **result classification**
(`expected.outcome`), the result hash (`expected.result_hash`) and the ATP spent
(`expected.atp_spent`). A disagreement between the prose and any of these
fields makes the edition non-conformant. The remainder of §7's prose explains
rules established in §3–§5 — environment access, lazy materialization, the
materialization bound — and is not an independent normative statement of this
section; those rules remain normative where they are established.

**The suite's schema (MUST).** The suite being normative, its shape is normative
too — and a shape cannot be declared by a version number: `format_version` names
a version and defines nothing. The suite's schema is a separate anchored file,
`spec/schemas/book1-conformance.schema.json`, anchored in `spec/ANCHORS.txt`
beside the suite it describes. It is **closed**: an unknown field makes a record
invalid, so the suite cannot grow a value that means something to one reader and
nothing to another. A record the schema rejects is not a record of this edition.

**`expected.exit` and `expected.outcome` are two different levels (MUST).**
`expected.exit` is `Receipt.exit` (§3.4) and its enum is closed: exactly
`normal_form`, `atp_exhausted`, `unresolved_reference`. `expected.outcome` is
**not an exit** but a suite-level classification of the result, and it adds one
value, `invalid_object`, which denotes a `normal_form` exit whose result is the
Canonical Invalid Object (§4.2). Such a run carries `exit = normal_form` and
`result_hash` = that object's hash. The two must not be conflated, which is why
they are separate fields: `exit` says **how** the evaluation ended, `outcome`
says **what** it ended on. An implementation that derives either from the other
is checking neither.

**§7 notation (MUST be read this way).** In the vectors below, `eval(·, atp)`
abbreviates evaluation of the named term with budget `atp` over this edition's
content environment — the `objects` of `tests/spec_conformance/vectors.json`. The
third input (§3.4) is not omitted; it is fixed by the set. `= ⟨X⟩` asserts the
exit `normal_form` with `expected.result_hash` equal to `H(X)`; "ATP Exhausted"
asserts `atp_exhausted`; "Unresolved Reference" asserts `unresolved_reference`.
The shorthand adds and changes no requirement: the normative statements remain
the record fields listed above.

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
`0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211`; `∀n : uint32 —
eval(Ω,n) = DISSONANCE(ATP Exhausted)`. The quantifier is bounded by the
declared budget domain: a value outside `uint32` is not a budget and yields a
local refusal (§3.6), not a canonical exit, so nothing is claimed about it here.

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
ATP. A bare intrinsic thunk: `eval(H(I), n)` = ⟨I⟩, 0 ATP for any `n : uint32`, no
store needed.

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
