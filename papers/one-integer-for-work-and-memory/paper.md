---
title: "One Integer for Semantic Work and Materialization: A Mechanized, Content-Addressed Combinator Machine over Term, Budget and Content Environment, and the Engineering of Trustworthy Proof Artifacts"
author: "Serhii Glova (independent) --- sergey.glova@gmail.com"
# The structured form below is for deposit metadata. It is NOT the `author`
# field: pandoc's default LaTeX template renders a list of maps by its
# truthiness, which is why every build of this paper so far has printed the
# word "true" on the title page where the author's name belongs.
authors:
  - name: Serhii Glova
    affiliation: independent
    email: sergey.glova@gmail.com
date: 2026-08-29
keywords:
  - combinatory logic
  - content addressing
  - semantic materialization
  - content-addressed computation
  - resource bounds
  - Lean 4
  - proof engineering
  - differential testing
classification: cs.LO, cs.PL
bibliography: references.bib
---

# Abstract

We present Σ-GLYPH Book I, a content-addressed combinator machine in which a
single unsigned integer budget — *ATP* — prices both the semantic work an
evaluation performs and the *peak number of nodes it materializes*, and we report
a layered Lean 4 mechanization of it. Three framing statements come first,
because an earlier version of this paper stated the first two wrongly in its
summary and did not state the third at all.

**Evaluation is a relation over three inputs, not two.** `eval` takes a term hash,
a `uint32` budget, **and a content environment** — a partial map from NodeHash to
bytes whose entries hash to their own key. A demanded hash absent from that
environment is a *canonical* outcome, so availability sits inside the semantics: a
node holding the bytes reaches a normal form where a node without them returns
`Unresolved Reference`, on the same term and the same budget. What bounds this is
a monotonicity theorem, `evalHash_stable`: extending an environment can change
**only** an unresolved outcome, never a normal form and never an exhaustion.

**The bound is semantic, not physical.** `size` counts materialized nodes. The
theorem says nothing about resident set size, heap bytes, evaluator stack, the
store's index, hashing buffers or allocator behaviour; the correspondence between
the two is a refinement layer we do not prove and do not claim.

**A result hash does not say how the run ended.** `eval` returns a receipt —
exit, result hash, ATP spent — and the hash alone never carried the exit:
`DISSONANCE(ATP Exhausted)` is an ordinary term, so one digest is reachable both
as an exhaustion and as a normal form. A consumer reading only the hash cannot
tell "finished" from "ran out", and because the budget is also the licence over
the verifier's memory, a verifier must be able to refuse a term *before*
evaluating it — a refusal that is a deployment decision and not a canonical
outcome.

The central theorem, `EvalMachine.evalHash_peak_size`, is
$\mathit{size} \le \mathit{atp} + 1$ at **every** configuration the run passes
through, proven *on a model of the actual hash-thunk evaluator* rather than on an
abstract cost algebra: the per-step accounting lemma `size_step` establishes that
every priced action grows the term by at most $\mathit{cost} - 1$, which is
exactly the row-by-row correspondence an abstract proof has to assume. A
companion theorem, `evalHash_settles`, shows that the machine's answer is a
configuration on which no further action fires — so a run ends because the
machine settled, not because a fuel counter cut it off, and every run exits
through exactly one of normal form, ATP-exhausted or unresolved-reference. The
mechanization is layered down to bytes — a from-scratch FIPS 180-4 SHA-256 in
core Lean, serialization injectivity, round-trip canonicity and validation
totality — so that redex recognition by hash is *derived* rather than
re-axiomatized. Forty-one theorems across five fronts are guarded; all sixteen
evaluator theorems have axiom cone
$\{\texttt{propext}, \texttt{Classical.choice}, \texttt{Quot.sound}\}$ exactly,
with `native_decide` confined to ten theorems in other fronts whose documented
trusted base already names the compiler.

We are equally explicit about what is *not* proven. The correspondence between
the Lean model and the running implementations is empirical: three differential
bridges execute the compiled Lean model against the reference oracle on 33
evaluation vectors, 334 byte buffers and 582 wave cases; three further bridges
check a weaker correspondence — 861 oracle steps against the premise the proof
consumes, 3000 random closed $\lambda$-terms against a transcription of the Lean
compiler model, and 1220 store perturbations against the monotonicity bound; and
a three-engine randomized fuzzer generates 5347 evaluation vectors per CI run.

Our second contribution is methodological, and we state it here in one paragraph
because it changes how much the first should be believed. The CI machinery that
asserts "these theorems hold and rest on these axioms" — not the Lean kernel, the
Python around it — was defeated twenty-one times over six internal hardening
rounds and five external reviews: by `sorryAx`, by a string literal that blinded
the comment stripper, by a `#print axioms` override installed *by the audited
module*, by vacuous theorems, by definition gutting that leaves every pinned
statement byte-identical, by an audit whose scope came from a config field
nothing compiled from, and — six rounds in — by a file walk that was not
recursive. Every bypass was reproduced against a green build; not one required a
kernel bug. §5 gives three representative vectors and the thesis that unifies
them (*a control whose scope is chosen by the thing it controls*); the full
taxonomy is a companion paper [@paperB2026].

---

# 1. Introduction

Suppose you are handed a computation by hash and asked to run it. Not a program
you wrote; a stranger's. You want three things before you agree. You want to know
it will stop. You want to know how much memory it can make you allocate before it
stops. And you want your answer to be the same as everybody else's answer, bit
for bit, so that "I ran it and got X" is a claim someone else can check rather
than a claim they must believe.

Existing designs give you subsets. The Ethereum Virtual Machine's gas
[@wood2014ethereum] bounds work and has been mechanized several times
[@hirai2017evm; @hildenbrandt2018kevm; @amani2018evm], but gas is not a memory
theorem: memory is priced through a separate, quadratic schedule, and no
statement of the form "peak allocation is a function of the budget" falls out of
the semantics. WebAssembly's deterministic profile [@wasmcore; @haas2017wasm]
gives reproducible execution and has a mechanized core [@watt2018wasm], but the
memory bound is an ambient property of the linear-memory limit, not a consequence
of the budget the caller supplies. Nock [@urbit2016] is small and deterministic
and has no budget at all. Unison [@unison] makes code content-addressed — the
identity discipline we also adopt — without a resource semantics. zkVMs
[@risczero; @sp1; @cairo2021] give you a proof that *this* execution happened
with *these* cycles, which is a per-execution certificate, not a universally
quantified theorem about all inputs.

Σ-GLYPH takes the narrow road. The machine is SKI combinatory logic
[@schonfinkel1924bausteine; @curry1958combinatory] over content-addressed nodes:
a term is a directed graph of 34- or 66-byte canonical records, each identified by
the SHA-256 of its own bytes, and reduction is leftmost-outermost. There is no
clock, no floating point, no network, no ambient state. The whole interface is

$$\mathit{result\_hash} = \mathrm{eval}(\mathit{term\_hash}, \mathit{atp}).$$

The design decision that makes this paper worth writing is the pricing. Under the
*hash-leaf size model* (ADR-001 composed with ADR-003), an unresolved hash counts
as exactly one node whatever it denotes, materializing one node costs its own
materialized size (1, 2 or 3), and the duplicating rule R-S costs
$1 + \mathit{size}(z)$ where $z$ is the duplicated argument in its *current*
materialization. The consequence, which Book I §3.4 states normatively, is that
every action costs strictly more than the size it adds — and therefore along any
execution

$$\mathit{materialized\_size}(t) - 1 \;\le\; \mathit{spent}.$$

One integer prices both axes. A caller who hands out a budget of $n$ has
simultaneously bounded the callee's work at $n$ actions and its peak materialized
graph at $n+1$ nodes, without a second knob, a second failure mode, or a heap
accountant.

**Contributions.**

1. **A combinator machine whose single budget provably bounds peak memory, with
   the theorem proven on the concrete evaluator** (§3, §4). `SizeBound.lean`
   proves the invariant over an abstract seven-row cost algebra with a
   reachability quantifier; `EvalMachine.lean` re-proves it on a Lean model that
   mirrors the reference evaluator's control flow, closing the row-correspondence
   gap the abstract proof must otherwise assume, and
   `EvalMachine.evalHash_peak_size` lifts it from the answer to every
   configuration of the run. The distinction is not cosmetic: on a store-backed
   $SKKI$ the trace peaks at 7 nodes and answers with 1, so a bound on the
   returned configuration is strictly weaker than a peak bound.

2. **Settling, and outcome classification, as theorems rather than comments**
   (§4.2). `eval_settles` / `evalHash_settles` establish that `evalHash` returns
   a configuration on which `step` fires nothing — the machine is settled when it
   answers — and therefore that every run exits through exactly one of `step`'s
   three non-firing results, i.e. one of Book I's three canonical outcomes.
   Totality and determinism remain *definitional* (a total Lean function with no
   `partial`, no `unsafe`); what was previously only a source comment is the
   claim that the fuel counter is never what stopped the machine.

3. **A layered mechanization down to bytes** (§4). `Sha256.lean` is a total,
   from-scratch FIPS 180-4 SHA-256 in core Lean [@fips180-4]; `MachineBytes.lean`
   proves serialization injectivity, round-trip *and canonicity*, validation
   totality, and the §4.1 length law; `EvalMachine.lean` is built on top, so
   recognizing $\langle I \rangle$, $\langle K \rangle$, $\langle S \rangle$ by
   hash is a derived fact about the proven byte layer, not a fresh axiom.

4. **An honest, per-theorem account of the trusted base** (§4.4, §7). Ten of the
   41 guarded theorems are permitted `native_decide`, which puts the Lean
   compiler in the trusted base; the other 31 are not, and all sixteen evaluator
   theorems — including the peak-memory bound and the settling theorems — depend
   on the three standard Lean axioms alone. Where a property is empirical, we say
   so in the sentence that makes the claim.

5. **An account of what the guarded-theorem counts are worth** (§5). The CI
   apparatus asserting those counts was broken and repaired six times; we give
   three representative bypasses, the current guarantees, the residual gaps, and
   the thesis that unifies them — *a control whose scope is chosen by the thing it
   controls*. The full twenty-one-vector taxonomy, the six rounds and the external
   review data are a companion paper [@paperB2026].

We claim no new proof technique and no new logic. This is a systems and
proof-engineering paper: the interest, if there is any, lies in the composition
and in the failure modes we document.

---

# 2. Background: what "checkable" has to mean

Three properties are load-bearing for the use case — re-executing a stranger's
reason — and they interact.

**Identity is bytes.** Every node is a `SigmaNodeV2` record with the layout
`[Op:1][Flags:1][Atom?:32][Left?:32][Right?:32]`, and `NodeHash = SHA-256(bytes)`.
The flags are not free: each opcode has exactly one normative flag value, so
there is exactly one byte string per node and the encoding is canonical by
construction. This is the same discipline that JCS [@rfc8785] imposes on JSON and
that multihash [@multiformats] and IPFS [@benet2014ipfs] impose on content
addressing, and it matters for the same reason: if two byte strings can denote
one value, the hash is no longer an identity, and two honest nodes can disagree
about what they were asked to compute. Nix [@dolstra2006nix] and Unison
[@unison] make the same bet at different granularities.

**Divergence must be a value, not an event.** SKI is Turing-complete;
$\Omega = (SII)(SII)$ does not terminate. A machine that hangs is not checkable,
so the budget is not an optimization but a totality device: when the budget
cannot pay for the next action, evaluation returns a `DISSONANCE` node carrying
`SHA-256("ATP Exhausted")`, and that node has a hash like any other. The same
holds for a demanded hash that is absent from storage
(`SHA-256("Unresolved Reference")`) and for bytes that fail validation
(`SHA-256("Invalid Object")`). Failure is data.

**Memory has to be bounded by the same knob.** This is the point where a naive
design leaks. Under a flat "one gas per rewrite" schedule, R-S duplicates an
arbitrary subterm for constant cost, so term size grows $O(2^{\mathit{atp}})$: a
budget of 60 buys gigabytes. ADR-001 records this as an OOM-before-ATP denial of
service against validators, and it is not hypothetical — it is the ordinary
consequence of pricing rewrites rather than materialization. The literature on
resource-aware type systems [@hofmann2003aara; @hoffmann2012raml] and on
separation logics with time and space credits
[@gueneau2018fistful; @chargueraud2019unionfind; @moine2023space] attacks the
same problem from the language side, deriving bounds for programs written in a
rich language. Our setting is the dual one: the language is fixed and tiny, and
the bound is a property of the *machine*, universally quantified over all inputs,
so a caller needs no analysis of the term at all.

There is a fourth property, less philosophical: **laziness**. ADR-003 makes
materialization demand-driven along the left spine, so a subtree that
leftmost-outermost reduction never demands is never fetched. This is what makes
withholding data a liveness problem rather than a safety problem, and it composes
with the pricing: you pay for exactly what the reduction touches. It also creates
the tension that ADR-001 §"Composition" resolves — R-S needs $\mathit{size}(z)$
while ADR-003 exists to avoid touching $z$ — and the resolution is the hash-leaf
model: an unresolved hash contributes exactly 1, so measuring $z$ never forces
it.

---

# 3. The machine

We give the fragment of Book I v0.5.2 that the mechanization covers. The
normative source is `spec/book-1-truth.md` (Ukrainian); `spec/book-1-truth.en.md`
is an informative translation, and section numbers below refer to both.

## 3.1 Nodes, bytes, identity

$$\mathit{Node} ::= \mathrm{LITERAL}(a) \mid \mathrm{REF}(t) \mid \mathrm{APPLY}(l, r) \mid \mathrm{DISSONANCE}(r)$$

with $a, t, l, r, s$ all 32-byte hashes. Serialization (§2) is

$$
\begin{aligned}
\mathrm{ser}(\mathrm{LITERAL}(a)) &= \texttt{00}\;\texttt{01}\;a \\
\mathrm{ser}(\mathrm{REF}(t)) &= \texttt{01}\;\texttt{01}\;t \\
\mathrm{ser}(\mathrm{APPLY}(l,r)) &= \texttt{02}\;\texttt{06}\;l\,\|\,r \\
\mathrm{ser}(\mathrm{DISSONANCE}(r)) &= \texttt{FF}\;\texttt{01}\;r
\end{aligned}
$$

and $\mathrm{NodeHash}(n) = \mathrm{SHA\text{-}256}(\mathrm{ser}(n))$.
Deserialization (§4.1) accepts a buffer iff the opcode is in the table, the flag
byte *equals* the opcode's normative value, and
$\mathit{len} = 2 + 32\cdot\mathrm{popcount}(\mathit{flags})$ — hence 34 or 66
bytes, and nothing else. Opcode `0x03` is permanently reserved-invalid. Any
validation failure materializes the *Canonical Invalid Object*, a fixed
`DISSONANCE` node; there is no undefined behavior and no exception.

The genesis combinators are nominal, not magic:
$\langle I \rangle = \mathrm{LITERAL}(\mathrm{SHA\text{-}256}(\texttt{"I"}))$ and
likewise for $K$ and $S$; §5.1 pins their NodeHashes. Since v0.5 they are
*intrinsic*: an implementation must serve them from the paragraph, not from
storage, so a node cannot be denied $K$. `FALSE` is deliberately not an axiom —
it is $\mathrm{APPLY}(\langle K\rangle, \langle I\rangle)$, constructible from
the two axiom hashes with no store at all, which the spec phrases as "FALSE is a
theorem, not an axiom."

## 3.2 Terms, thunks, and the size model

The v0.5 abstract machine (§3.3) operates on *hash thunks*. A term under
reduction is a graph of materialized nodes whose children are either materialized
nodes or bare 32-byte hashes:

$$T ::= \mathbf{thunk}(h) \mid \mathbf{lit}(a) \mid \mathbf{ref}(t) \mid \mathbf{dis}(r) \mid \mathbf{app}(T, T)$$

Size, the quantity the bound is about, is (§3.4):

$$
\mathit{size}(\mathbf{app}(f,a)) = 1 + \mathit{size}(f) + \mathit{size}(a),\quad
\mathit{size}(\mathbf{ref}(\cdot)) = 2,\quad
\mathit{size}(\_) = 1
$$

A materialized REF counts 2 because it is a node plus the thunk of its target. An
unresolved thunk counts exactly 1 *regardless of what it denotes* — this is the
hash-leaf model, and it is what lets R-S price its argument without forcing it.

## 3.3 Reduction and pricing

The rewrite rules (§3.1) are the standard SKI set plus one-level reference
unfolding:

$$
\begin{aligned}
\text{R-I:}&\quad \mathrm{APPLY}(\langle I\rangle, x) \to x \\
\text{R-K:}&\quad \mathrm{APPLY}(\mathrm{APPLY}(\langle K\rangle, x), y) \to x \\
\text{R-S:}&\quad \mathrm{APPLY}(\mathrm{APPLY}(\mathrm{APPLY}(\langle S\rangle, x), y), z) \to \mathrm{APPLY}(\mathrm{APPLY}(x,z), \mathrm{APPLY}(y,z)) \\
\text{R-R:}&\quad \mathrm{REF}(h) \to \mathrm{resolve}(h) \quad\text{(exactly one level per step)}
\end{aligned}
$$

Reduction is leftmost-outermost, i.e. normal order [@barendregt1984lambda], so a
redex is reduced before its arguments. Combinator recognition is *identity by
hash* (§3.2): a node is $I$/$K$/$S$ iff its NodeHash equals the §5.1 constant. Crucially this test applies to thunks
without materializing them, which is what makes redex recognition $O(1)$ and lazy
simultaneously.

Prices (§3.4):

$$
\begin{aligned}
\mathrm{cost}(\mathbf{force}\;h) &= \mathit{size} \text{ of the materialized node} = 1 \mid 2 \mid 3 \\
\mathrm{cost}(\text{R-R}) = \mathrm{cost}(\text{R-I}) = \mathrm{cost}(\text{R-K}) &= 1 \\
\mathrm{cost}(\text{R-S}) &= 1 + \mathit{size}(z)
\end{aligned}
$$

Two disciplines make this total and deterministic. First, **the exhaustion check
precedes the action**: an action whose price exceeds $\mathit{atp} - \mathit{spent}$
is not performed, and evaluation returns ATP Exhausted with `spent` unchanged. In
particular $\mathrm{eval}(\mathrm{REF}(\textit{missing}), 0)$ is ATP Exhausted,
decided before any storage access — the outcome cannot depend on what the store
contains. Second, the minimum price of any action is 1, so evaluation strictly
draws down the budget and cannot spin at zero cost.

## 3.4 The bound

Every rule's size increment is strictly less than its price. R-I and R-K shrink;
force-LITERAL is size-neutral at cost 1; force-REF adds 1 at cost 2; force-APPLY
adds 2 at cost 3; R-R turns a 2-node REF into a 1-node thunk at cost 1; and R-S,
the only growing rule, adds $\mathit{size}(z) - 1$ at cost $1 + \mathit{size}(z)$
— it duplicates $z$ but discards the $\langle S \rangle$ spine node, and under
the hash-leaf model copying an unresolved leaf adds exactly one node. Hence
along any execution

$$\mathit{size}(t) - 1 \le \mathit{spent} \le \mathit{atp},$$

at every point of the execution and not merely at its end, which gives a caller a
preflight memory estimate of $\mathit{atp} + 1$ nodes.
Book I §3.4 adds a warning that a 2026-07 review forced: because `spent` is an
*upper*, not a lower, bound on size, an implementation must not use `spent` as a
live fault trigger — $\Omega$ is a tiny term that spends everything — and a guard
must measure actual `size(t)`.

## 3.5 Canonical compilation

Book I §6 fixes exactly one $\lambda \to$ SKI compiler, Profile C1, so that two
humans writing the same $\lambda$-term get the same hash. It is textbook bracket
abstraction [@turner1979implementation] with the rules applied *strictly in
order*: $A(x,x) = \langle I\rangle$; then $A(x,M) = K\,M$ when $x \notin FV(M)$;
then $A(x, MN) = S\,A(x,M)\,A(x,N)$. The ordering is normative and is not an
optimization: C1 performs no $\eta$-reduction and does not canonicalize
extensionally, so $C1[\lambda x.\lambda y.x] = S(KK)I \ne \langle K \rangle$ — a
separate citizen, extensionally equal to $K$. Rice's theorem is the reason the
spec gives, and it is the right one: syntactic canonicity is achievable,
semantic canonicity is not.

## 3.6 The third input, and how far it reaches

`eval(term_hash, uint32 atp, env)`. The Lean model has always been
`evalHash (h) (atp) (st)` and the reference oracle has always been
`eval_hash(h, atp, store, …)`; what was missing was the third argument in the
sentence people read. A demanded hash absent from `env` is a canonical outcome, so
two conforming engines with the same term and the same budget can return different
canonical results — the counterexample is one line long, and the conformance suite
could not have caught it, because every implementation is handed the same prepared
store.

`env` is not "anything with a `get`". It is a partial map whose bytes hash to
their own key. Bytes filed under a foreign key are a real hazard rather than a
theoretical one: until the audit of 2026-08-29 the reference oracle **executed**
them as that key's node, which is an Identity-by-Hash violation that would let two
engines disagree while both believed they were following the Book.

What bounds the third input is `EvalMachine.evalHash_stable`: if `env2` answers
every lookup `env1` answers, a settled exit — normal form or exhaustion — is the
same receipt under both. Only `unresolved_reference` can change. The hypothesis is
stated on lookups rather than as set inclusion on purpose: `storeGet` returns the
first entry whose hash matches, so a larger store could answer with different
bytes of the same hash, and ruling that out by assuming SHA-256 injective would
assume something false by counting.

The differential bridge is `proofs/store_mono_bridge_check.py`, and it is the
sixth: it grows each vector's store with the rest of the suite and with eight
nodes belonging to no vector, and shrinks it by removing each demanded node in
turn — **67 grown and 1153 shrunk over 33 evaluation vectors**. The shrink
direction carries the weight: removing bytes must yield `Unresolved` or nothing,
never a different verdict.

## 3.7 The receipt, and what a result hash cannot say

`eval` returns `{exit, result_hash, atp_spent}`, where `exit` is exactly one of
`normal_form`, `atp_exhausted` and `unresolved_reference`.

The hash alone never identified the exit. `DISSONANCE(ATP Exhausted)` is an
ordinary term: put it in a store and evaluate it, and it is a normal form. So
`8bb0006f4c0a…` is reachable both as an exhaustion and as a normal form, and a
caller reading only the hash cannot tell "finished" from "ran out". This is not a
hypothetical — `tests/receipt_test.py` produces both and fails if either half
stops being true.

The two-value form remains available as a named compatibility profile, and a
receipt still unpacks as a pair, so the four call sites in `warrant` that consume
`ski@v1` reasons are unchanged and were exercised against this oracle.

## 3.8 Admission: totality is not affordability

`eval` is total, so a stranger's term always terminates. A `uint32` budget admits
up to 4,294,967,295 priced actions, and because
$\mathit{size} \le \mathit{spent} + 1$ the budget the stranger chooses is also
their licence over the verifier's memory. The party
supplying the term was deciding how much the verifier spends discovering that it
terminates.

A verifier must therefore be able to refuse **before** executing. That refusal is
not a canonical outcome and must not be serialized as a DISSONANCE: it says the
verifier declined, not what the term evaluates to. `impl/sigma_glyph.py` carries
`admit()` and a `VERIFIER_LIMITS` preset; the default limits leave the cap unset,
because this module is also the conformance oracle and an oracle that refuses is
not an oracle. Nothing forces a verifier to choose the preset, and no consumer of
Σ-GLYPH reasons elsewhere has been changed — which is the assumption, not the
mitigation.

## 3.9 Where the specification stands

The adopted edition is bundle **v0.6.7**, with Book I at its own version 0.5.2,
anchor `a98a03bd…`. Book I 0.5.2 prints the two-argument interface. A candidate —
`proposals/ADR-010`, bundle `v0.7.0` — states the three inputs, the receipt, the
CAS condition, the monotonicity bound, admission, and one arbitration rule shared
by all three Books. **It is not adopted**, it has not passed a gate, and this paper
does not describe it as in force. What this section describes is the machine,
which has always had three inputs; what the Book prints is a separate fact, and
the candidate is the proposal to make them agree.

---

# 4. The mechanization

All proofs are Lean 4 v4.31.0 [@demoura2021lean4], **core only, no mathlib**.
The pinned toolchain is `proofs/lean-toolchain`. Ten `.lean` files total 1404
lines: `Sha256.lean` (110), `MachineBytes.lean` (282), `EvalMachine.lean` (440),
`WaveAlgebra.lean` (203), `C1Compiler.lean` (138), `SizeBound.lean` (97),
`LutData.lean` (17 lines holding a 206 KB generated table), and three `*Run.lean`
I/O runners (49 + 49 + 19) which prove nothing and exist to feed the differential
bridges.

The five fronts are *layered, not independent*:
`Sha256 → MachineBytes → EvalMachine` is a genuine dependency chain, so the
evaluator's redex recognition is stated over the proven serialization layer
rather than over an axiomatized `is_glyph` predicate. This is the structural
difference from a mechanization that models reduction and treats byte identity as
given.

## 4.1 Bytes (`Sha256.lean`, `MachineBytes.lean`)

`Sha256.sha256 : List UInt8 → List UInt8` is FIPS 180-4 written out: the round
constants, `H0`, the four $\Sigma/\sigma$ functions, `pad` (whose zero count is
computed arithmetically so the definition is total by construction), and a
compression loop over `Std.Range`. There is no `partial`, no `unsafe`, no
`extern`. What is *not* claimed: there is no proof that this function is SHA-256.
Its correctness is established differentially, against FIPS digest vectors and
against the oracle, and we say so in §7.

On top of it, `MachineBytes.lean` proves:

| Theorem | Claim |
|---|---|
| `serialize_injective` | distinct well-formed nodes never share canonical bytes |
| `deser_serialize` | round-trip: parsing canonical bytes returns the node |
| `serialize_deser` | **canonicity**: a valid buffer *is* the serialization of its parse — no second byte form exists for any node |
| `deser_wf` | validation only ever yields well-formed nodes (totality of the parser) |
| `valid_lengths` | §4.1 rule 3: a valid buffer is 34 or 66 bytes |
| `reserved_opcode_invalid` | §1.2: `0x03` never parses |
| `lit_bytes_disjoint` | byte-0 discrimination under `glyph_eq`'s $O(1)$ redex test |

`serialize_deser` is the one that earns its place. Round-trip alone
($\mathrm{deser} \circ \mathrm{ser} = \mathrm{id}$) is compatible with a second,
non-canonical encoding of the same node; canonicity
($\mathrm{ser} \circ \mathrm{deser} = \mathrm{id}$ on valid buffers) is what makes
the hash an identity. Together with `serialize_injective` it says the map from
well-formed nodes to valid buffers is a bijection, and the hash layer above adds
only the collision assumption, which is stated and not proven.

Five further theorems pin the spec's constants end-to-end: `genesis_I`,
`genesis_K`, `genesis_S` recompute $\mathrm{SHA\text{-}256}(\mathrm{ser}(\mathrm{LITERAL}(\mathrm{SHA\text{-}256}(\texttt{"I"}))))$
inside the proof assistant and compare against the §5.1 hex;
`false_is_a_theorem` does the same for $\mathrm{APPLY}(\langle K\rangle,\langle I\rangle)$;
`invalid_object_pins` for the §4.2 object. These five use `native_decide` and are
the byte front's only entries in the compiler-trusting set.

## 4.2 The evaluator (`EvalMachine.lean`)

`EvalMachine.step : Term → Nat → Store → StepResult` mirrors the reference
implementation's `step5`: leftmost-outermost descent along the left spine, redex
heads recognized by `glyphEq` (a hash comparison that is `false` on any
application, so R-K and R-S fire only on the exact spine shapes), thunk forcing
priced by the materialized node's size, and the genesis intrinsic handled before
any store lookup. `eval` iterates it under fuel; `evalHash h atp st` starts from
`.thunk h` with fuel `atp + 1`.

**Totality and determinism are definitional, not theorems.** `step` is
well-founded on `sizeOf t`; `eval` is structural recursion on fuel; `evalHash` is
a total Lean function with no `partial` and no `unsafe`. Determinism is the
statement that it is a function. This is a stronger form of the property than a
theorem about a relation, and it is also a weaker claim than it may sound: it is
a fact about the Lean model, and the model's agreement with any implementation is
empirical (§4.5, §6). Definitional totality also says less than one wants: it
guarantees `evalHash` *answers*, not that the answer is a settled configuration
rather than a trace truncated by the fuel counter. That gap is what
`eval_settles` closes.

The proven statements:

- `step_bounds` — for any fired action, $1 \le c \le \mathit{rem}$. Proved by
  `fun_induction step` followed by `grind [size_pos, size]`. The file documents
  the manual skeleton `grind` automates, per branch, because a tactic that
  discharges eight cases at once is exactly where a reader loses the ability to
  audit. This transparency note was added in response to a 2026-07 focused
  review.
- `step_cost_le`, `step_cost_pos` — its two projections: an action never costs
  more than the remaining budget, and never costs zero.
- `eval_spent_le`, `evalHash_spent_le` — $\mathit{spent} \le \mathit{atp}$ for
  **all** terms, budgets and fuel. Previously a per-vector observation; here a
  theorem.
- `eval_settles`, `evalHash_settles` — **fuel sufficiency**: whenever
  $\mathit{atp} - \mathit{spent} < \mathit{fuel}$,
  `step (eval fuel t atp spent st).1 (atp - (eval …).2) st = .nf`. The proof is a
  four-case induction: each accepted action costs at least 1 (`step_cost_pos`)
  and at most what remains (`step_cost_le`), so the remaining budget strictly
  decreases and the fuel counter cannot be what stopped the machine.
  `evalHash_settles` instantiates it at the fuel `evalHash` actually passes,
  $\mathit{atp}+1$.
- `size_step` — the exact §3.4 per-step accounting:
  $\mathit{size}(t') + 1 \le \mathit{size}(t) + c$. R-S is the only growing rule
  and holds *unconditionally*: the discarded $\langle S\rangle$ head is pure
  slack, so no leaf assumption on $z$ is needed.
- `eval_size_bound`, `evalHash_size_bound` — the ADR-001 bound,
  $\mathit{size}(\mathrm{result}) \le \mathit{spent} + 1$, on the concrete
  evaluator.
- `evalHash_peak_size` — **peak** memory:
  $\mathit{size}(\texttt{eval}\;k\;(\texttt{.thunk}\;h)\;\mathit{atp}\;0\;\mathit{st}).1 \le \mathit{atp} + 1$
  for every $k$. The quantifier over $k$ is what makes it a peak bound: `eval k`
  runs at most $k$ actions and its fuel-out branch returns the configuration
  reached, so $k = 0, 1, 2, \dots$ enumerates the configurations of the
  $\mathit{atp}+1$ run. The proof composes `eval_size_bound` at each $k$ with
  `eval_spent_le` to replace $\mathit{spent}_k$ by $\mathit{atp}$.

**Outcome classification, stated at the right scope.** `evalHash_settles` says
`step` fires nothing on the returned configuration; `eval` reaches its exits only
through `step`'s `.nf`, `.exhausted` and `.unresolved` results, whose returned
terms are respectively the settled term, `.dis rATP` and `.dis rUnres`. So every
run exits through **exactly one of three** — normal form,
`DISSONANCE(ATP Exhausted)`, `DISSONANCE(Unresolved Reference)`. What is *not*
claimed, and the artifact is explicit about this, is that the three outcome
*terms* are pairwise distinct: a term materialized from the store can itself
reduce to the ATP-Exhausted leaf, so a normal-form exit may return the same term
an exhausted exit would. The trichotomy is a property of the machine's **exit**,
not of the term it hands back. A reader who wants to distinguish the three from
the result hash alone cannot; that is a deliberate consequence of failure being
ordinary data.

The two theorems are also non-vacuous in the way one should check. For a
store-backed $SKKI$ at $\mathit{atp}=50$, the $(k, \mathit{size}, \mathit{spent})$
trace is $(0,1,0)$, $(1,3,3)$, $(2,5,6)$, $(3,7,9)$, $(4,7,11)$, $(5,1,12)$ —
peak 7, returned configuration 1 — so `evalHash_size_bound` genuinely does not
imply `evalHash_peak_size`, and the fuel quantifier is load-bearing. On the same
trace `step` fires on the returned configuration for $k = 0..4$ and is `.nf` only
from $k \ge 5$, so `eval_settles`'s hypothesis
$\mathit{atp} - \mathit{spent} < \mathit{fuel}$ is load-bearing too. (We
reproduced both traces against the branch's unmodified `EvalMachine.lean`.)

**Status.** All sixteen evaluator theorems are guarded on `master`. The three
that close the settling and peak claims — `eval_settles`, `evalHash_settles`,
`evalHash_peak_size` — were developed on a branch and merged at `35d8aea`, where
they were re-pinned against a guard that had moved twice underneath them (§5.4,
§5.5); the five that state store monotonicity (§3.6) merged later still. We
verified the merged state independently: the eval bridge reports sixteen guarded
theorems with standard axioms only, and we reproduced both traces above against
`master`'s unmodified `EvalMachine.lean`. One nuance the project's own governance
discipline demands: the most recent *adopted* anchor set is `v0.6.7` at
`16a1355`, and all eight of these theorems merged after it, so they are on the
branch in force but are not covered by an adoption warrant (§7).

This is the paper's main technical claim, so it is worth being precise about what
`SizeBound.lean` adds and what it does not. `SizeBound.lean` abstracts the
machine to a pair $\langle \mathit{size}, \mathit{spent}\rangle$, gives seven
constructors for the priced actions, and proves `memory_bound` over an inductive
reachability relation — so it quantifies over *all reachable states*, which is
the peak-memory statement. But the seven rows are *assumed* to correspond to the
real machine's actions; the file says so in its header. `EvalMachine.size_step`
discharges that assumption, on the real control flow, with no classifier, and
`evalHash_peak_size` supplies the missing quantifier. The two files are now
complementary in a narrower sense than before: `SizeBound` has a reachability
relation over an abstract model, while `EvalMachine` has both the correspondence
and a peak bound over the concrete one. We keep `SizeBound` in the guarded set
because its seven-row presentation is what Book I §3.4 normatively states and
what an independent implementer would check against — not because the evaluator
proof depends on it, which it does not.

## 4.3 Compiler and wave algebra

`C1Compiler.lean` models §6 and proves `mem_skiFv_abstr` ($A(x,\cdot)$ removes
exactly $x$ from the free variables), `mem_skiFv_c1` (C1 preserves free variables
exactly) and `c1_closed` (a closed $\lambda$-term compiles to a variable-free SKI
term). The last one converts a runtime check into a theorem: the reference
implementation's "free variable escapes abstraction" guard *cannot fire* on
closed input. Two TV-10 vectors are pinned by `rfl`. This front's entire axiom
cone is `{propext}` — the guard's allowed set for it is exactly that, not the
broader standard set, so the documented claim and the enforced claim are the same
sentence.

`WaveAlgebra.lean` mechanizes Book II's integer interference algebra, which sits
*above* identity as an optional navigation view and never inside it. It proves
range closure (`interfere_valid`), the zero-amplitude cascade, the Law of Left
Dominance (`left_dominance_ph`), the Resonance Identity (`crystallization`: the
unique non-zero fixed point of self-interference is
$\{\mathit{am}=65535, \mathit{en}=-32768\}$), and two negative results used as
design evidence — `fold_not_associative` and `not_commutative`, which are the
machine-checked form of the ADR-006 argument that folding interference is
unsound. We include this front because it is part of the artifact, not because
Book I depends on it; ignoring Book II entirely leaves Book I intact.

## 4.4 The trusted base, per theorem

Forty-one theorems are guarded, distributed as: `size` 2, `bytes` 12, `eval` 16,
`wave` 6, `c1` 5. The registry pins **44** statements: the three extra are
unguarded wave lemmas whose `native_decide` trust axioms guarded theorems borrow,
pinned in what they say — see [@paperB2026]. Nineteen further theorems are
registered as deliberately unguarded (helper lemmas: list-append inverses, LUT range facts, `divRoundHalfUp`
bounds). The per-front axiom policy is machine-enforced, not documentary:

| Front | Allowed axioms | `native_decide` permitted for |
|---|---|---|
| `size` | propext, Classical.choice, Quot.sound | — (none) |
| `eval` | propext, Classical.choice, Quot.sound | — (none) |
| `bytes` | propext, Classical.choice, Quot.sound | the 5 genesis / FALSE / invalid-object pins |
| `wave` | propext, Classical.choice, Quot.sound | 5 of 6 (`left_dominance_ph` excepted) |
| `c1` | **propext only** | — (none) |

So `native_decide` — which evaluates a decision procedure with the compiled
evaluator and therefore adds the Lean compiler to the trusted base, and which
mathlib disallows for exactly this reason [@mathlib2020] — is confined to ten of
the 36 guarded theorems, each of which is a *concrete computation* (a digest, a 32769-entry
LUT scan, a 65536-case amplitude fixed-point scan) rather than a structural
claim. In particular the evaluator front, which carries every claim this paper
leads with, admits none: we verified independently, with `#print axioms` at the
toolchain the repository pins, that `evalHash_peak_size`, `evalHash_size_bound`,
`eval_settles`, `evalHash_settles` and `evalHash_spent_le` each depend on
`{propext, Classical.choice, Quot.sound}` and nothing else. The wave front's
honesty note is sharper than the headline: `interfere_valid` is *reasoning*-symbolic
but consumes `lut_range`, which is `native_decide`, so its soundness rests
transitively on the compiler too. Only the pure integer lemmas and
`left_dominance_ph` are compiler-independent in that front.

## 4.5 What ties the model to the code

Nothing in Lean does. The Lean model is a Lean model. What ties it to the running
system is five differential bridges, in the tradition of differential testing
[@mckeeman1998differential; @yang2011csmith]:

- `eval_bridge_check.py` executes the compiled Lean evaluator via `EvalRun.lean`
  and compares result NodeHash *and* `atp_spent` against the reference oracle on
  all 33 evaluation vectors.
- `byte_bridge_check.py` runs the Lean pipeline on 334 buffers — every
  conformance CAS object including the deliberately malformed Era-1 `0x03` one,
  the genesis bytes, and roughly 250 adversarial mutations (truncation,
  out-of-mask flags, wrong-in-mask flags, reserved opcode, op/flag swap) —
  comparing CAS keys, §4.1 verdicts and round-trips.
- `wave_bridge_check.py` regenerates `LutData.lean` byte-identically and compares
  the Lean `interfere` against the oracle on a 582-case deterministic boundary
  grid.
- `c1_bridge_check.py` compares a Python transcription of the Lean `abstr`/`c1`
  against the oracle on 3000 random closed $\lambda$-terms, NodeHash-exact.
- `bridge_check.py` drives the oracle step-by-step over adversarial terms and
  asserts the SizeBound premise ($\Delta\mathit{size} \le \mathit{cost} - 1$) on
  every observed action.

Two of these five deserve a warning label, and the repository supplies it: only
three (`byte`, `eval`, `wave`) actually execute compiled Lean. `bridge_check.py`
checks the Python oracle against the *premise* the Lean proof consumes, and
`c1_bridge_check.py` compares a hand-written transcription. And no differential
can ever exercise a `Prop`-valued definition — `Valid`, `Wf`, `Reach`, `Step`,
`Inv` — which is precisely where each theorem's hypotheses live. That gap is what
§5 is about.

---

# 5. Integrity of proof artifacts

A machine-checked theorem in a repository makes two claims. The first is
mathematical: the kernel accepted a proof term. The second is bureaucratic: *the
thing the kernel accepted is the thing the README says it accepted.* The first
claim is what proof assistants are for and it is in excellent shape. The second
is a software supply-chain problem [@torresarias2019intoto; @slsa], it is the one
a reader of §4 actually depends on, and in our experience it is where everything
went wrong.

This section states the problem and our position on it. The full account — a
taxonomy of twenty-one reproduced bypasses over six internal hardening rounds and
five external reviews — is a companion paper [@paperB2026]; we summarize only
what a reader of the mechanization needs in order to calibrate how much the
guarded-theorem counts in §4.4 are worth.

**The starting point.** `lean` exits 0 on a file containing `sorry`. It is a
warning. So "CI compiled the proofs" is not "CI checked the proofs", and a
repository that gates on compilation gates on nothing in particular. The standard
remedy is a script that compiles, queries each headline theorem's axiom
dependencies with `#print axioms`, and fails the build on anything unexpected.
Ours was about forty lines. Over eight days of adversarial review it became 1465
lines of Python, a 179 KB pin registry and a 981-line regression suite asserting
122 properties — machinery 2.4× the size of the 1404 lines of Lean it guards.
Every bypass in that history was demonstrated end-to-end: not "this check has a
theoretical gap" but *here is a file, here is the green CI output, here is the
falsehood it certified.*

**Three representative vectors**, chosen because each defeats a defense a reader
would reasonably assume sufficient.

*An axiom check verifies how something was proven, never what.* Replacing a
theorem's statement with `theorem memory_bound : True := trivial` leaves the
axiom cone clean — `trivial` needs no axioms — so the guard printed "OK
`#print axioms` clean (std axioms only)" and the bridge printed
`PREMISE HOLDS ON ALL OBSERVED STEPS`, exit 0. The same hole admits a weakened
hypothesis or an altered conclusion. The fix is to pin each guarded theorem's
*elaborated statement*, structurally dumped so notation cannot make the displayed
form differ from the elaborated one.

*Pinning a statement does not pin what the statement is about.* Deleting one
constructor from the inductive reachability relation of `SizeBound.lean` — a
four-line diff — shrinks `memory_bound` to a claim about the single state
$\langle 1,0\rangle$; `def Valid (_w : Wave) : Prop := False` makes
`interfere_valid`, `left_dominance_ph` and `crystallization` simultaneously
vacuous. In every case every pinned statement dump stayed byte-identical and
every bridge stayed green, including `WAVE-BRIDGE: ALL AGREE (582/582)`. The fix
is to pin, from the kernel environment, the transitive definition dependency set
of each guarded statement — a definition by type *and* value, an inductive by
type *and* constructor list — and to treat an unpinned dependency as a hard
failure so a new one cannot appear silently.

*An audit whose scope is a configuration field is not an audit.* The
definition-pinning scope was read from a per-front `build` list that nothing
actually compiled from, and the driver silently dropped every constant owned by a
module outside it. Deleting one module name therefore disabled the whole control
for that front and restored both of the P1s above: wave `build` shortened by one
entry, plus `Valid := False`, gave `WAVE-BRIDGE: ALL AGREE (582/582)`, rc 0,
*while printing* "every definition they are stated in terms of matches its pin".
The fix is an inversion — derive the scope as the complement of a small,
separately declared core-Lean allowance, so it cannot shrink by editing a list
the same commit edits.

**The thesis.** These are not unrelated bugs. Every vector we found instantiates
one shape: **a control whose scope is chosen by the thing it controls.** The
axiom cone is chosen by the theorem's own proof; the axiom *answer* was, until we
fixed it, chosen by the audited module, which could install syntax overriding
`#print axioms` and hand the guard a fabricated list; the comment stripper's view
of a file was chosen by a string literal inside it; the set of declarations by
their own line breaks; the set of files by which directory they sit in. The
defense that generalizes is not a longer denylist but that inversion: derive
scope from something the audited artifact cannot edit, and make an unpinned,
unregistered or unclaimed entity a failure rather than a silent skip. Two
corollaries recur — *UNRUN is not PASS*, and *a scan that finds nothing is
indistinguishable from a scan that never ran.*

**What this means for §4.** Not one of the twenty-one bypasses required a bug in
the Lean kernel; every one type-checked. Independent re-checkers such as
`lean4checker` [@lean4checker] and `lean4lean` [@lean4lean] raise assurance about
the mathematical claim and would have caught none of them, because the proofs
really are valid — of the wrong proposition. So the counts in §4.4 rest on
machinery that has been broken six times and repaired six times, most recently
by an outside reviewer who observed that the guard's file walk was not recursive,
so a `proofs/Sub/Evil.lean` containing `axiom backdoor : False` was read by
nothing while CI exited 0. We state the current guarantees precisely — statements
and transitive definition dependencies pinned from the kernel environment, axioms
queried through `Environment.importModules` as data rather than elaboration,
scope derived rather than configured, the guarded set claimed by identity, and
one recursive enumeration feeding every source-layer check — and we note the
residual gaps rather than footnote them: no differential can exercise a
`Prop`-valued definition, which is exactly where each theorem's hypotheses live;
the `*Run.lean` runners are unproven I/O plumbing and the one place `partial` is
allowed; regeneration can launder any drift and is therefore never run by CI; and
`GUARD_CLAIMS.txt` is a review-visibility control, not an authority. The reader
who wants the evidence behind those sentences should read the companion paper;
the reader who wants only the calibration should take away that §4's numbers are
as good as a human reading of one JSON diff.

---

# 6. Evaluation

All figures below were measured at commit `1c2b6ca` — the frozen v0.7.0
candidate — on an Apple-silicon macOS host (arm64, Darwin 25.5.0) with Lean
4.31.0, from a clean tree extracted with `git archive` and containing no `.olean`
cache. Every number is reproducible with the commands named. Figures in the
deposited version of this paper were taken at `35d8aea` on a different host OS
release and are not directly comparable; these replace them rather than
supplementing them.

## 6.1 Proof checking

| Bridge | Wall (s) | Guarded theorems | Differential |
|---|---:|---:|---|
| `bridge_check.py` (SizeBound) | 5.07 | 2 | 861 oracle steps, 0 premise violations |
| `byte_bridge_check.py` | 2.15 | 12 | 334 / 334 buffers agree |
| `eval_bridge_check.py` | 4.96 | 16 | 33 / 33 eval vectors agree (hash **and** `atp_spent`) |
| `wave_bridge_check.py` | 37.39 | 6 | 582 / 582 boundary cases agree |
| `c1_bridge_check.py` | 1.32 | 5 | 3000 random closed $\lambda$-terms agree |
| `store_mono_bridge_check.py` | 0.07 | — | 67 grown / 1153 shrunk over 33 eval vectors |
| **all six, one cold sequential run** | **47.4** | **41** | |
| `tests/proof_guard_test.py` | 43.11 | — | 122 checks, 0 failures |

The per-bridge figures and the all-six figure are separate measurements (the
per-bridge column sums to 51.0 s, slightly above the sequential run — run-to-run
variance on a laptop, not a warm cache). Each Lean bridge builds its own `.olean`
artifacts in a private temporary directory, so no figure benefits from one. The
guard regression suite now costs about as much as all six bridges together,
because most of its 122 checks compile a fixture through `lean`.

The store-monotonicity bridge is the one entry that invokes no `lean` at all: it
is a differential over the reference oracle alone, which is why it costs 0.07 s
and guards no statement of its own. The theorem it exercises, `evalHash_stable`,
is one of the sixteen the evaluator bridge guards.

The evaluator front carries the growth of this revision: eleven guarded theorems
became sixteen with the store-monotonicity chain, and the registry now pins 156
definitions. The equational form of `eval_settles` — `step … = .nf` rather than a
`match … | .step _ _ => False` phrasing — was chosen deliberately: the registry
pins compiler-generated auxiliaries like `EvalMachine.step.match_3` alongside
ordinary definitions, and a match-shaped statement would have added another.

The wave front dominates the bridges: `LutData.lean`'s 32769-entry table and the
`native_decide` scans account for roughly four-fifths of the total. Bare kernel
type-checking of the small files is negligible — `SizeBound.lean` 0.20 s,
`C1Compiler.lean` 0.27 s, `Sha256.lean` 0.21 s — so the wall time is guard
machinery and compiled evaluation, not proof search.

## 6.2 Conformance and differential agreement

`tests/spec_conformance/vectors.json` holds **49** vectors: 33 `eval`, 8 `object`
(serialization/hash), 8 `deserialize` (byte-rejection), over 36 preloaded CAS
objects one of which is deliberately malformed. The evaluation vectors' outcome
distribution is 17 normal form, 12 ATP-exhausted, 3 unresolved-reference, 1
invalid-object — i.e. more than half exercise a failure path, which is the point:
in this design the failure paths are the consensus-critical ones.

The property suite (`tests/spec_conformance/test_properties.py`, fixed seed
`0x516`) runs **2103 checks in 0.04 s**, of which P7 — the memory-bound property
— is **150 random traces**, and P2 is deserialization totality over **2000 random
byte buffers**. (We flag this because `SizeBound.lean`'s header comment described
P7 as covering "~2000 random traces" until commit `a58d5d6` corrected it: the
2000 belongs to P2 and the 2103 is the suite-wide check count. The same commit
corrected the conformance README's governance-scenario count from 16 to 20. Both
are small, and both are the kind of drift §5 is about.)

The randomized three-engine fuzzer `tests/book1_fuzz.py` generates random SKI
terms (depth 1–5, mixing genesis leaves, random literals, resolvable REFs and
deliberately absent "ghost" REFs) crossed with an ATP grid per term — including
$0$, $\mathit{spent}-1$, $\mathit{spent}$, $\mathit{spent}+1$ and $2^{32}-1$ —
and replays every generated vector through three engines: the Python oracle, the
Rust implementation, and `warrant-go`'s native evaluator. CI runs three fixed
seeds — 1337, 4242, 20240717 — at 200 terms each on every push, which at
`1c2b6ca` generate 1792, 1776 and 1779 vectors: **5347 generated evaluation
vectors per CI run**, all agreeing, at about 9.8 s per seed locally with two of
the three engines present. The seeds are fixed so that a divergence is
reproducible.

## 6.3 Implementations

| Implementation | Lines | SHA-256 | Book I evaluator |
|---|---:|---|---|
| `impl/sigma_glyph.py` (oracle) | 618 | `hashlib` | yes |
| `impl-rs/src/main.rs` | 1112 | from scratch, zero crate dependencies | yes |
| `warrant-go` (external repo, CI-pinned) | — | Go stdlib | yes |
| `impl-go/main.go` (in-tree) | 1948 | Go stdlib | **no** — Book III / governance only |

The Rust implementation is worth a sentence: 1112 lines, no dependencies at all,
its own SHA-256, `overflow-checks = true` in the release profile, and it replays
the oracle-generated vectors byte-exact. The in-tree Go implementation covers
Books II–III and governance and contains no Book I evaluator; the third Book I
engine is `warrant-go`, in a separate repository, pinned in CI by commit hash.
So the honest phrase is **three separately implemented engines from one
development lineage**, not "three independent implementations", and anyone
reading the latter anywhere in this repository should read it as the former.

The Lean artifact is 1404 lines across ten files. The integrity machinery around
it — `proof_guard.py` (1465), `theorem_pins.json` (179 KB),
`tests/proof_guard_test.py` (981) and six bridge scripts (929) —
is now **2.4×** the size of the proofs it guards, up from 1.8× before the last
three rounds. That ratio is the honest cost of the second claim in §5. It is also
the strongest quantitative argument for §7's concern that the guard work, while
the most visible output of this period, may not have been the most valuable one.

---

# 7. Limitations

We list these in descending order of how much they should change a reader's
confidence.

**The guard work may be the streetlight, not the keys.** The one external
reviewer that executed the suites found no bypass and instead attacked the
priority: hardening a proof guard is defence against adversarial third-party
proofs, and this project has had zero external contributors, so six rounds went
to hypothetical pull requests from oneself while the friction a first real user
meets — policies authored by hand in SKI combinators — went unaddressed. We think
that is largely correct, we record it because suppressing it would undercut the
paper's own method, and we do not resolve the tension in our favour; the
companion paper argues both sides at length [@paperB2026]. For §4's purposes the
consequence is narrow: the guarded-theorem counts rest on machinery whose
development was chosen for legibility rather than by a threat model.

**One implementation lineage.** The Python oracle, the Rust implementation and
`warrant-go` are all written by the same author (with model assistance) from the
same specification text, in a period of weeks. Agreement between them is real
evidence about specification ambiguity and about coding slips, and it is weak
evidence about *specification* error: three implementations of a wrong sentence
agree perfectly. Nor is the specification yet in a state that makes an
independent implementation easy: the normative Book I is Ukrainian, the English
rendering is explicitly informative and is not itself anchored, and §7 designates
the reference oracle as the arbiter where the prose and the normative vector suite
disagree — which tells an implementer that their disagreement with the
specification is settled by code they must read to consult. No external party has
implemented Book I. That is the single most valuable missing datum in this
paper.

> **Both corrections this paper carried as notes are now in its text.** The
> deposited version at [10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651)
> gave a wrong reason for the missing independent implementation, and named two
> arguments where the evaluator takes three. Those were repaired here by
> rewriting the claims rather than by appending a third note; the deposited PDF
> is unchanged and remains the historical artifact.

**The model–code gap is empirical and finite.** No theorem relates
`EvalMachine.lean` to `impl/sigma_glyph.py`. What relates them is 33 evaluation
vectors, 334 byte buffers, 582 wave cases, 3000 $\lambda$-terms and 5347
fuzzer-generated vectors per CI run — a large finite sample of a space we make no
claim to have covered. There is no verified refinement, no extraction, and no
proof that the Lean `Store` (a list with linear `find?`) is a faithful model of a
content-addressed store.

**The trichotomy is about the exit, not the term.** `evalHash_settles` proves
every run ends on a settled configuration and therefore exits through exactly one
of `step`'s three non-firing results. It does **not** prove the three outcome
*terms* are pairwise distinct, and they are not: a term materialized from the
store can itself reduce to the ATP-Exhausted leaf, so a normal-form exit can
return the term an exhausted exit would have returned. A caller who needs to
distinguish "it finished" from "it ran out" must be told the exit, not handed the
result hash. Relatedly, nothing in the evaluator front proves that the
`.dis rATP` / `.dis rUnres` leaves carry the reason strings Book I §5.3 mandates;
that correspondence lives in the byte front and in the vectors' `result_hash`.

**`native_decide` is in the trusted base for ten theorems.** Every genesis hash
pin, the FALSE constant, the Canonical Invalid Object, and five of six wave
theorems trust the Lean compiler in addition to the kernel. The evaluator front
does not. We consider the byte-front pins acceptable because they now carry an
independent differential against the oracle, and we consider the wave front's
dependence properly disclosed rather than eliminated.

**SHA-256 is not proven to be SHA-256.** `Sha256.lean` is a transcription of FIPS
180-4 [@fips180-4], checked against FIPS digest vectors and the oracle. There is
no equivalence proof against a reference specification of the kind HACL*
provides [@zinzindohoue2017hacl]. Collision resistance is assumed, not proven,
and the specification says so.

**The reported commit is ahead of the adopted one, twice over.** The proofs and
implementation this paper describes are on `master`; the specification text of
§3.9 is on a candidate branch that has passed no gate. The most recent
governance-adopted anchor set is `v0.6.7` at `16a1355`, and eight of the sixteen
evaluator theorems of §4.2 and §3.6 merged after it. So they are on the branch
in force but are not covered by an adoption warrant, and under this project's own
rules location is a fact about git while adoption is a threshold signature. A
reader who wants only adopted material should check out the tag and will find
eight evaluator theorems rather than sixteen, thirty-three guarded theorems
rather than forty-one, and a Book I that states two arguments to `eval`.

**The threshold was met; independent custody was not.** The v0.6.7 adoption
warrant carries two valid signatures against a 2-of-3 policy — but the signers
are the human principal (`s0fractal`) and a *delegated model actor*
(`claude-fable-5`) operating under that human's authority, not two independent
parties. The project documents this itself and counts it: of the six times the
threshold has been exercised, three pair two keys that sat in one directory on
one host, which is one custody and not a quorum. The maintainer offered a third
roster key and the signing actor declined to use it, on the grounds that a
cryptographically valid signature attributing its act to a different model would
be exactly the provenance forgery the project exists to prevent. We report the
adoption as a satisfied *policy*, never as independent attestation, and we note
that the project's own security-assumptions document says no independent gate has
run against any of this.

**No review of this work was independent.** All six internal guard rounds were
fresh-context sessions with models from a single family, prompted by the author.
Five external reviews crossed model families but not the prompting operator or
the framing, which is the definition the project itself uses when it declines to
call them a gate: no independent adversarial gate has run against any of this,
and none of the guard commits carries the project's own governance adoption. One
external reviewer's finding was worth all six internal rounds on the dimension
that mattered — it saw the assumption the internal attacks shared — and four
reviewers between them produced four confident P0 claims that a single command
refutes. Both halves of that sentence should be weighted; §5 of the companion
paper gives the full table [@paperB2026].

**Reproduction is not read-only.** `tests/proof_guard_test.py` writes and then
deletes a real `proofs/Helper.lean` while testing the unaudited-file vector. Run
it on a clean tree.

**The guard lives in the artifact it guards.** An external review named this
**V22, "Edit the Cop"**: `proof_guard.py`, `theorem_pins.json`,
`GUARD_CLAIMS.txt`, the regression suite and the workflow that runs them all sit
in the repository they police. `GUARD_CLAIMS.txt` says as
much itself — whoever can change the registry can change the claims; it is
visibility control, not authority. §5's thesis, applied one level up, lands on
§5's own machinery.

The reviewer marked it a candidate rather than a reproduced exploit, because they
could not read the repository's protection settings. Those were then read and the
condition held: **rulesets empty, `master` unprotected**. Anyone with push could
move the branch, guard and all.

`master` now requires a pull request and five checks read from live runs, with
branches up to date, force-pushes and deletions refused, and admin enforcement on.
That was tested rather than assumed: with enforcement off, an admin's direct push
succeeded and had to be reverted by a forward commit; with it on, the same push is
rejected.

**The recursion is narrowed to one door, not closed.** A pull request can still
change a theorem, the guard, the tests and the workflow together, and the required
checks are the ones that pull request defines; no review is required, so an author
can merge their own. Closing it needs a verifier that does not live in the
candidate revision — a reusable workflow pinned to a protected ref, a separate
verifier repository, or a governance commitment over the verifier's hash. None
exists, and no claim of an independent guard should rest on branch protection.

Finally, an honest note about scope: this paper describes Book I plus the Book II
algebra. Books II and III (navigation and federation) exist, are specified, and
are mechanized only in the narrow sense reported in §4.3. Nothing about
federation is proven here.

---

# 8. Related work

**Verified systems.** seL4 [@klein2009sel4], CompCert [@leroy2009compcert] and
CakeML [@kumar2014cakeml] establish the discipline this work aspires to and
exceed it by a wide margin on the axis that matters most: they prove refinement
between a specification and executable code. We do not. Our contribution on that
axis is negative and methodological — we report precisely which link is missing
and what empirical evidence stands in for it.

**Resource bounds.** Automatic amortized resource analysis
[@hofmann2003aara; @hoffmann2012raml] and separation logics with time credits
[@gueneau2018fistful; @chargueraud2019unionfind] derive per-program bounds in
rich languages; Moine et al. [@moine2023space] address heap space specifically,
which is the closest work in spirit to our memory theorem. The difference is
quantification: they bound a given program, we bound a fixed machine over all
programs, which is possible only because the machine is small enough to make the
per-rule inequality $\Delta\mathit{size} < \mathrm{cost}$ hold uniformly.

**Metered virtual machines.** The EVM [@wood2014ethereum] has been mechanized in
Isabelle/HOL [@hirai2017evm; @amani2018evm] and in K [@hildenbrandt2018kevm];
these are far larger and more mature mechanizations than ours, of a far larger
machine. To our knowledge none of them yields a theorem of the form "peak
memory $\le f(\text{gas})$", because the EVM's memory expansion is a separate
priced resource rather than a consequence of the instruction schedule.
WebAssembly [@haas2017wasm; @wasmcore] with a mechanized core semantics
[@watt2018wasm] and a deterministic profile gives reproducibility but places
memory bounds in the embedder. Nock [@urbit2016] is comparable in size and
minimality and has no budget.

**Content-addressed computation.** Unison [@unison] is the closest sibling: code
is identified by the hash of its normalized form, which is the same
"hash-is-identity" bet. Nix [@dolstra2006nix], IPFS [@benet2014ipfs] and
multiformats [@multiformats] apply it to artifacts rather than to reduction. None
of these prices execution.

**Verified execution certificates.** zkVMs [@risczero; @sp1; @cairo2021] give a
succinct proof that a specific execution occurred within specific limits. That is
strictly stronger *per execution* and strictly weaker as a design property: it
certifies a run, not a machine. The two are complementary; a size-priced machine
is a plausible zkVM guest precisely because its resource behavior is a theorem.

**Canonicalization and signature pitfalls.** Our byte-canonicity theorems
(`serialize_deser`, `serialize_injective`) are the combinator-machine analogue of
JCS [@rfc8785], and the failure mode they exclude is the one Chalkias et al.
[@chalkias2020eddsa] document for EdDSA [@rfc8032]: an underspecified encoding
admits multiple valid representations, and independent implementations then
disagree about identity. That the sibling Warrant protocol [@warrant2026] signs
Σ-GLYPH-addressed records is why we treat this as a security property rather than
an aesthetic one.

**Proof-artifact integrity.** The adjacent literature concerns the
trustworthiness of the checker itself — the de Bruijn criterion and
Pollack-consistency [@barendregt2005challenge; @wiedijk2012pollack], Lean's type
theory [@carneiro2019lean], independent re-checkers [@lean4checker; @lean4lean] —
and proof engineering at scale [@ringer2019qed]; the supply-chain framings of
in-toto [@torresarias2019intoto] and SLSA [@slsa] treat build provenance rather
than the semantics of what was built. We are not aware of prior work
cataloguing attacks on the CI machinery that asserts a repository's claims about
its own proofs, which is the gap the companion paper [@paperB2026] addresses and
which §5 summarizes.

---

# 9. Conclusion

The technical result is small and, we think, clean: if you price materialization
by materialized size and price duplication by the current size of what is
duplicated — counting an unresolved hash as exactly one node — then every action
of a leftmost-outermost combinator machine costs strictly more than the size it
adds, and one integer budget bounds both work and peak memory. The proof is
mechanized twice: once over an abstract cost algebra with a reachability
quantifier, and once on a Lean model of the concrete hash-thunk evaluator, whose
per-step accounting lemma discharges the correspondence the abstract version has
to assume. The mechanization stands on a proven byte layer down to a from-scratch
SHA-256, so redex recognition by hash is derived rather than assumed.

The result we did not expect to be writing about is the second one. The CI
apparatus asserting that these theorems hold, and rest on these axioms, was
defeated twenty-one ways without a single kernel bug — and, after six adversarial
rounds against it, by the plain fact that its file walk never entered a
subdirectory. Each bypass was a green build certifying a falsehood, and each was
reproduced before it was fixed. The narrow lesson is that a machine-checked proof
in a repository is two claims, that proof assistants have solved the first, and
that the second is currently defended by scripts nobody reviews. The broader one
is that the failures share a shape — *a control whose scope is chosen by the thing
it controls* — for which the fix is not a longer denylist but inverting the
direction of the choice. We develop both in a companion paper [@paperB2026]; here
they serve as the calibration for §4's numbers.

Our next steps are the ones the limitations dictate, in order: a policy frontend
usable by an engineer who does not know SKI, because the sharpest external
critique we received is that we hardened the most visible surface rather than the
one a user meets first; an external implementation of Book I from the English
specification by someone who has not read our code — the single most valuable
missing datum, and one no amount of internal work can supply; and an independent
adversarial pass by a reviewer we did not prompt.

---

# 10. Artifact availability

The artifact is the repository:

> **https://github.com/s0fractal/sigma-glyph** [@sigmaglyph2026]
> branch `spec/book1-v0.7.0-candidate`, figures measured at commit
> `1c2b6ca42cb95cdc035fc887cd0587a5758862d7`

Every figure in §6 was measured at that commit. The paper text itself is later on
the same branch, because a paper cannot state the hash of the commit that carries
it; what the two commits differ in is this file, the other paper's front matter,
this directory's `README.md` and `build.sh`, `tools/paper_claims.py`,
`tools/test-all.sh` and `.github/workflows/ci.yml`. Every surface §6 measures —
`proofs/`, `impl/`, `impl-rs/`, `impl-go/`, `tests/` and `spec/` — is
byte-identical between them, which `git diff` reports as empty. It is **not** `master` and **not** an adopted release: it
is the head of the draft pull request carrying the v0.7.0 specification
candidate, and the Book bytes on it have not passed a gate. What it carries that
`master` does not is the candidate spec text of §3.9 and the store-monotonicity
theorems and bridge; the evaluator, the guard and the conformance vectors it runs
are the ones described throughout. The most recent governance-adopted anchor set
remains the tag `v0.6.7` at `16a1355`; §7 and §3.9 explain the difference.

MIT for the implementation, CC-BY-4.0 for the specification texts. The v0.6.7
anchor set was adopted under the project's 2-of-3 threshold policy (adoption
warrant `b4dc05e307b8`, two valid signatures, which we verified independently);
§7 states why that is a satisfied policy and not independent attestation.

**Packaging.** The stack's three Python packages are published on PyPI and were
installed into a clean virtual environment and run by the maintainer:
`sigma-glyph` 0.6.7, `warrant-verify` 0.6.0 and `oaip` 0.3.0, all uploaded
2026-07-31 through GitHub Actions OIDC Trusted Publishing. We verified the
versions, filenames and upload timestamps against the PyPI JSON API rather than
against the repository's own documentation, which at the time of writing still
described earlier versions as the latest. No third party has installed them, so
we claim *published and installed by the maintainer* and nothing stronger. Note
also that `sigma-glyph`'s distribution ships the Book I–III Python modules only:
the specification, the conformance vectors, the Lean proofs and the Rust and Go
implementations live in the repository, so the artifact for this paper is the
checkout, not the wheel.

**Prerequisites**: Python 3.10+, and `elan` for the pinned Lean toolchain
(`leanprover/lean4:v4.31.0`, read from `proofs/lean-toolchain`). The Rust and Go
surfaces additionally need `cargo` and `go`; the Lean surfaces need nothing else
— no mathlib, no network.

**One command re-runs every surface behind §6.1 and §6.2:**

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
git checkout 1c2b6ca42cb95cdc035fc887cd0587a5758862d7
tools/test-all.sh
```

That reproduces the *agreement* columns — the vector, buffer, boundary-case,
$\lambda$-term and perturbation counts, and the pass verdicts. It does **not** reproduce
the wall-clock column: `test-all.sh` times nothing and reports no durations. Each
figure in that column was taken by timing the named script on its own, from a
tree extracted with `git archive`, and the sequential figure by timing the six in
one loop. Nor does `test-all.sh` run the three CI fuzz seeds of §6.2; it runs one
smaller seed (`--terms 60 --seed 20260730`), and the 5347-vector figure comes
from `.github/workflows/ci.yml`'s three.

`test-all.sh` prints `ALL GREEN` only if every surface ran. A surface that could
not be checked — no `lean` on `PATH`, no network for the cross-repo parity pulls
— is named in the verdict and the script exits 2. (Until 2026-07-29 it printed
`ALL GREEN` and exited 0 after skipping, which is itself an instance of §5's
thesis; `proof_guard.py` invoked with no arguments did the same thing until
`5e75e9b`.) `ALLOW_SKIPS=1` is how a reader says the gap was deliberate.

To reproduce the proof results alone, offline:

```bash
python3 proofs/bridge_check.py        # SizeBound guard + 861 oracle steps
python3 proofs/byte_bridge_check.py   # BYTE-BRIDGE: ALL AGREE (334/334)
python3 proofs/eval_bridge_check.py   # EVAL-BRIDGE: ALL AGREE (33/33)
python3 proofs/wave_bridge_check.py   # WAVE-BRIDGE: ALL AGREE (582/582)
python3 proofs/c1_bridge_check.py     # C1-BRIDGE: ALL AGREE (3000 terms)
python3 proofs/store_mono_bridge_check.py  # STORE-MONO: ALL AGREE (67 / 1153)
python3 tests/proof_guard_test.py     # PROOF-GUARD: ALL PASS (122 checks)
```

Each Lean bridge runs the integrity guard of §5 before it runs anything else,
and fails closed if `lean` is absent (exit 2, never a silent skip). Total cold
wall time for the six bridges on the machine described in §6 is 47.4 s; the guard
regression adds 43.1 s. Run the guard regression on a clean tree: several of its
vectors write and then remove real files under `proofs/`, including a
subdirectory, as part of testing the unaudited-file and non-recursive-walk cases.

---

# Acknowledgements

The adversarial review rounds of §5 were conducted by fresh-context language
model sessions prompted by the author; the reproductions they produced are the
evidence for every vector reported. Earlier design decisions recorded in ADR-001
through ADR-007 — in particular the hash-leaf size model, whose proof and
independent re-derivation are cited in Book I §3.4 — came out of a multi-model
review protocol documented in `reviews/`. Neither process constitutes an
independent audit, and §7 says so.

The Lean formalizations, the reference implementations, and much of this prose
were written by AI models — OpenAI Codex and GPT, Anthropic Claude, Moonshot
Kimi, Google Gemini and Antigravity, DeepSeek, Alibaba Qwen, and Zhipu GLM —
working under the direction of the author, who specified the system, stated the
theorems to be proven, and curated the adversarial review process. The
per-model review ledger, with dates and dispositions, is preserved in the
repository under `reviews/`; the counts there are the honest record of which
model found what, including the rounds that found nothing.

That authorship claim is deliberately explicit rather than buried, because the
paper's own argument is about not taking a producer's word for its output. Every
theorem is checked by the Lean 4 kernel, which does not care who wrote the
tactic script; the trusted-base caveats, `native_decide` among them, are stated
in `proofs/README.md` and in §7. What a model wrote and what a kernel accepted
are two different claims, and only the second one carries weight here.
