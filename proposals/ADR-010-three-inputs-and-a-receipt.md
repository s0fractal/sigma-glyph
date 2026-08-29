# ADR-010: three inputs, a receipt, and one rule about who arbitrates

**Status:** CANDIDATE — **NOT ADOPTED**. Nothing in this document is in force.
Adoption is a threshold-authorised warrant over the `v0.7.0` anchor-set blob under
[`spec/GOV-anchors.md`](../spec/GOV-anchors.md) §3, preceded by a blind
multi-family gate over the exact bytes this candidate freezes. Merging the branch
does not adopt anything, and this file is written **before** the normative bytes
are edited so that its scope can be read against what was actually done.

**Supersedes** the candidate closed as `#24` (ADR-009), whose one correct move —
removing the reference oracle's precedence over Book I's prose — is carried
forward here inside a larger and coherent change. Its frozen anchors belong to a
tree that no longer exists and are not reused.

**Numbered 010.** `ADR-008` is the Resonant Precedent work on
`adr-008-rev15-candidate`; `ADR-009` is the superseded candidate. Two documents
under one number is a provenance collision even when only one is adopted.

## Why one candidate and not five

Each of the defects below is small. Together they are one defect: **Book I
describes a machine that is not the machine the model, the oracle and the suite
implement**, and every consumer has been reading the description.

- The Book prints `eval(term_hash, atp: uint32)`. The evaluator takes a store.
- An absent hash is a *canonical* outcome (§3.5), so availability is already
  inside consensus — and nothing bounded how far that reaches.
- A store is any object with `get`. Nothing said what makes it a content-addressed
  store, so bytes filed under a foreign key executed as that key's node until the
  audit of 2026-08-29.
- `result_hash` is offered as the answer, and it cannot say which of the three
  exits happened, because `DISSONANCE(ATP Exhausted)` is an ordinary term.
- The memory bound is a count of materialized nodes, and the word used for it in
  the paper's title is "memory".
- §7 makes the reference implementation the arbiter of the Book's own prose, and
  Books II and III repeat the construction — Book III attributing it to Book I §7.

Fixing any one of these while leaving the rest produces a Book that is precise
about one thing and wrong about its neighbours. That is why they move together.

## Scope, exactly

### Book I — the interface

`eval` is stated over **three** inputs: a term hash, a `uint32` budget, and a
**content environment**. A content environment is a partial map from NodeHash to
bytes with one property: the bytes under a key hash to that key. Bytes filed under
any other key MUST NOT be evaluated as that key's node — they may be a perfectly
valid SigmaNodeV2, and executing them would let two conforming engines disagree
while both believe they are following the Book.

Determinism is stated over the **demanded** environment: two engines that resolve
the same demanded hashes to the same bytes return the same receipt. That is what
the suite actually tests, since every implementation is handed the same store.

### Book I — how far availability reaches

Extending a content environment can change an `Unresolved` outcome and nothing
else. A settled answer — a normal form or an exhaustion — is stable under
everything an environment can gain. This is already a theorem
(`EvalMachine.evalHash_stable`) with a differential bridge; the candidate moves it
from something the repository proves into something the Book promises.

### Book I — the receipt

`eval` returns `{exit, result_hash, atp_spent}`. `exit` is one of `normal_form`,
`atp_exhausted`, `unresolved_reference`.

`result_hash` alone does not identify the exit and never did: a
`DISSONANCE(ATP Exhausted)` node can sit in a store and evaluate to a normal form,
so one hash means "finished" or "ran out" depending on how it was reached. The
Book says so rather than leaving a caller to discover it.

**Compatibility is explicit, not silent.** The existing two-value form
`eval_hash(h, atp, store) -> (term, spent)` remains available as a named
compatibility profile. It is not deprecated by this candidate and it loses no
guarantee; what it cannot do is answer "which exit", and the Book now says which
question it cannot answer. Four call sites in `warrant` use that form, all through
a store adapter keyed by node hash, and all were exercised against the current
oracle: identical results.

### Book I — admission is a boundary, not an outcome

A verifier MUST be able to refuse a computation before performing it, on a budget
it declines to spend. That refusal is **not** a canonical outcome and MUST NOT be
serialized as a DISSONANCE — it says the verifier declined, not what the term
evaluates to. Confusing the two lets the party supplying the term decide what the
verifier reports.

Input outside the declared domain — a budget that is not a `uint32`, a term hash
that is not 32 bytes — is refused the same way, and refused *before* the
environment is consulted. **This is a behavioural change with a consumer-visible
edge**: before the 2026-08-29 audit, `atp = -1`, `1.5` and `True` were accepted.
They now raise. A consumer that passed a malformed budget got an answer and now
gets an error, and the Book must say that this is a refusal rather than a result.

### Book I — the bound is semantic

The mechanized bound is `size ≤ spent + 1` where `size` counts materialized nodes.
The Book names it a **semantic materialization bound** and states in the same
paragraph what it is not: not resident set size, not heap bytes, not evaluator
stack, not the store's own index, not allocator behaviour. Those live in a
refinement layer nobody here has proved.

### Books II and III — one rule, and no new arbiter

Both carry the same construction as Book I §7: on a disagreement between prose and
the machine-readable suite, the reference oracle wins. All three are replaced by
one rule: **the suite is a normative part of the edition; prose and records MUST
be mutually consistent; an edition where they disagree is non-conformant and MUST
NOT be used as a source of consensus until corrected and re-anchored; no
implementation, the reference one included, takes precedence.**

No tool is named in normative text. An earlier draft of ADR-009 put
`tools/spec_audit.py` into §7, which would have replaced one implementation's
authority with another's. Where a checker reaches, and where it does not, belongs
in `spec/IMPLEMENTING.md` and in CI.

Book III additionally attributes its rule to "the discipline of Book I §7". After
this edition that discipline is a different sentence, so the attribution is
corrected rather than left pointing at something that no longer says it.

### Versions

`spec/VERSIONS.md` is applied, and its decision is checked rather than quoted.

- **Book I 0.5.2 → 0.6.0.** MINOR, not PATCH: an implementation conformant to
  0.5.2 can be non-conformant here without changing a line. Foreign-key bytes that
  used to execute must now be refused, an out-of-domain budget that used to be
  accepted must now be refused, and an edition whose prose and suite disagree used
  to be usable and is now non-conformant. Each is a changed verdict for a
  documented state.
- **Books II and III 0.6.1 → 0.7.0.** MINOR, and two reviewers were right to
  press on why. `spec/VERSIONS.md`'s test is whether *an implementation*
  conformant to the previous version could become non-conformant, and the
  objection is that an arbitration rule binds editions rather than
  implementations. It binds both, because an implementation's conformance is
  judged against the edition's normative artifacts and this changes which
  artifact decides: under 0.6.1 the reference oracle had precedence, so an engine
  matching the oracle where the oracle and the suite disagreed was conformant;
  under 0.7.0 it is not. Round 1 added a second implementation-visible change to
  each — the record fields that carry a prose claim are now named for these
  suites' own schemas, so an auditor no longer has to transport Book I §7's field
  list onto a different shape by guesswork.
- **Bundle `v0.7.0`**, carrying all of them.
- Each suite's `spec_version` is set to the version of the Book it conforms to,
  which closes the two discrepancies `version_check.py` has been carrying by name
  since they were found. `suite_version` is the suite package's own number and is
  not touched by a Book moving.
- Every vector file is **regenerated by its generator**. No expected value is
  edited by hand, and the generators refuse to write a suite that disagrees with
  the values declared by hand from the spec.

## What this candidate does not do

It does not adopt anything. It does not promote the `v0.7.0` ANCHORS section from
CANDIDATE. It does not tag, release, publish or deposit. It does not make the
English rendering normative. It does not touch the old adopted anchors or the
blobs of any prior release, which stay exactly as they are.

It also does not claim the gate rounds behind ADR-009 transfer. Those reviewed a
different tree, and most of them reviewed the *enforcement* rather than the norm.

## How to check what it says against what it did

    python3 tools/version_check.py          # the six numbers agree
    python3 tools/spec_audit.py             # constants, §7 predicates, both texts
    python3 tests/spec_audit_selftest.py    # and the audit can still fail
    python3 tools/verify_anchors.py         # the candidate section's anchors
    python3 tests/spec_conformance/run_reference.py
    python3 proofs/store_mono_bridge_check.py

The unsigned `v0.7.0` anchor-set blob and the exact command that reproduces it
byte-for-byte are recorded in this branch once the bytes are frozen.

## Round 1 of the gate

Three families, blind, one prompt, over the frozen bytes of `1c2b6ca`:
`google/gemini-3.1-pro-preview`, `deepseek/deepseek-v4-pro-0813`,
`moonshotai/kimi-k3`. **Three REJECT.** Raw responses, prompt digest and
timestamps: `gates/v0.7.0-candidate/`.

- **P0, found independently by all three — `atp` out of domain.** §3.4 kept
  "ATP > 2³²−1 — implementation-defined (MAY reject/clamp)" while the new §3.6
  said a non-`uint32` budget MUST be refused. Two MUST-level clauses in the same
  Book, permitting and forbidding the same behaviour, with no priority between
  them; Book-priority is *between* Books and does not apply. Both DeepSeek and
  Kimi produced the same counterexample: `H(I)`, `atp = 2³²`, empty environment —
  one engine refuses, the other clamps and returns a normal form. This was a
  defect the candidate introduced: §3.6 was added and §3.4 was not amended.
  **Fixed** — §3.4 now says a value outside the domain is not a budget, refuses
  it per §3.6, and forbids clamping by name.
- **P1, found independently by DeepSeek and Kimi — when the CAS property is
  checked.** §3.5 required an implementation *that detects* a foreign-key
  mismatch to refuse, and never said whether detection is eager or
  demand-scoped. An eager validator refuses an environment whose poisoned entry
  is never demanded; a lazy one returns a normal form. **Fixed** — the property
  is checked for every hash the evaluation actually resolves, an undemanded entry
  does not affect the result, and a wider local check MUST end in the same local
  refusal rather than a different canonical exit.
- **P1/P2, Gemini and Kimi — §7's call shape.** The vectors wrote `eval(·, 4)`
  with two arguments under a rule this candidate itself adds, and stated a result
  without naming an exit. **Fixed** — §7 now says how its shorthand reads, and
  that it adds no requirement.
- **P2, Kimi — Books II and III imported Book I §7's rule without mapping it.**
  Their suites have different schemas, so "the same rule as Book I §7" left the
  field list to guesswork. **Fixed** in both, against each suite's own shape.
- **P0 for Gemini and DeepSeek, P3 for Kimi — GOV-anchors' dependency pin.**
  `spec/GOV-anchors.md` is defined against "Book I v0.5.2 / Book II v0.6.1 /
  Book III v0.6.1 as anchored in this release", and this candidate makes that
  sentence name versions the bundle no longer carries. **Not fixed, deliberately,
  and the disagreement is left standing rather than resolved by the author.**
  Kimi's reading is that leaving it is correct: the only Book I semantics
  GOV-anchors consumes is `NodeHash(LITERAL, SHA-256(bytes))`, which this
  candidate does not touch, so the pinned *semantics* hold; and GOV §0 makes
  re-pinning a governed breaking change, which would need its own MAJOR version
  and its own gate. Gemini's and DeepSeek's reading is that a governance verifier
  treating the pin as binding rejects the bundle while one applying only §3's
  seven steps authorizes it, which is a divergence about whether the release may
  be adopted at all. Both readings are recorded; the choice is the roster's,
  because a document that governs which bytes are the specification should not be
  amended by the author of the bytes it is being asked to govern.
- **Typo**, `преф лайт` → `префлайт` (§3.4), pre-existing. Fixed.

Round 1's verdicts do not carry to round 2: the bytes moved, so the gate is
re-run over the new freeze and the earlier REJECTs stand as a record of a
revision that is no longer proposed.

## Round 2 of the gate

Same three families, fresh contexts, over the frozen bytes of round 2:
**ADOPT** (Gemini 3.1 Pro), **REJECT** (DeepSeek v4 Pro), **NO VERDICT** (Kimi
k3). Raw responses: `gates/v0.7.0-candidate/round-2/`.

- **P0, DeepSeek — round 1's own fix contradicted itself.** §3.5 said an
  undemanded entry "does not affect the result" and, one sentence later, that a
  permitted wider check MUST end in a local refusal. So a poisoned entry nobody
  demands both must not and may change the outcome. Counterexample: `H(I)`,
  `atp = 10`, canonical `I` bytes filed under the zero key. **Fixed** — the
  confusion was between *the result* and *whether a verifier agrees to compute at
  all*. An undemanded entry MUST NOT change any canonical `Receipt`; a verifier
  declining such an environment is exercising admission (§3.6), which produces no
  `Receipt` and therefore has nothing to disagree about.
- **P1, DeepSeek — `NodeHash(bytes) = key` was undefined for invalid buffers.**
  A buffer failing §4.1 is not a node, so it has no NodeHash — yet failure mode
  (b) prices materializing the Canonical Invalid Object, which is reachable only
  if the key check passed. **Fixed** — the property is `SHA-256(bytes) = key`
  over the raw buffer, checked before validation, and the two questions are named
  as different: whether a buffer is a valid node has a canonical answer, whether
  bytes belong under a key has none. This is what the reference oracle has always
  done (`node_hash(b) != h` before `deser(b)`), so no vector changes.
- **NO VERDICT, Kimi.** Cut off mid-reasoning at a 24 000-token reply budget.
  That is a fact about the budget, not about the candidate; `--max-tokens` now
  exists, defaults to 40 000, and is recorded in every review.
- **GOV-anchors.** Gemini reversed its round-1 P0 to "not a P0", citing Kimi's
  round-1 reasoning by name. DeepSeek held it at P0.

### A weakening of this gate, recorded rather than glossed

From round 2 the prompt carries this ADR, and this ADR carries the previous
round's dispositions — which necessarily include why a reviewer was disagreed
with. Reviewers are blind to each other **within** a round and are **not** blind
to earlier rounds' arguments. Round 2 made that concrete: one family reversed a
P0 on the strength of another family's round-1 argument. That is a legitimate
change of mind and it is **not** independent confirmation. On the GOV-anchors
question the honest count is therefore one line of reasoning with two
subscribers, not two independent findings, against one standing P0.

The alternative — withholding the dispositions — would leave reviewers unable to
see what changed and why, which trades a known weakness for a worse one. The
weakness is named here so that nobody reads the vote total as more than it is.

## Round 3 of the gate — incomplete

Frozen at `gates/v0.7.0-candidate/round-3/`, anchor set `4c93717a…`.

**ADOPT** (Gemini 3.1 Pro), **NO VERDICT** (DeepSeek), **NO VERDICT** (Kimi). Both
NO VERDICTs are `HTTP Error 402: Payment Required`: the OpenRouter account ran out
of credit partway through the round. DeepSeek was retried at a smaller reply
budget and returned 402 again.

This is one verdict, not a gate, and it is not recorded as one. The two families
that raised round 2's findings have not seen the edits those findings produced —
DeepSeek in particular has not been asked whether §3.5 now closes the P0 it
found. No substitute model was used: swapping in a cheaper model from the same
family would change the reviewer set mid-gate, and spending more is the account
holder's decision.

**The candidate therefore has no gate.** Adoption needs a completed round over
these exact bytes, and that is a prerequisite independent of, and additional to,
the signature threshold.

| Date | Change | Bytes already edited? |
| --- | --- | --- |
| 2026-08-29 | scope fixed, before any normative edit | no |
| 2026-08-29 | round 1: three REJECT; four findings fixed, one recorded unresolved | yes, after the gate saw them |
| 2026-08-29 | round 2: ADOPT / REJECT / NO VERDICT; both findings were round 1's own repair | yes, after the gate saw them |
