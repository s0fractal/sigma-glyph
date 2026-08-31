# ADR-012: A checkout-independent consumer surface

**Status:** DRAFT — non-normative product-surface proposal. Not implemented,
not gated, not adopted, and not part of any Specification Anchor. It proposes
no change to Books I–III, their schemas, their vectors, ATP pricing, or
governance. **This revision is a proposal only; no implementation is authorised
by it.**

**Renamed and rescoped, 2026-08-31.** The earlier revision was
`ADR-012-stranger-verification-surface.md`, written for a stranger who might
arrive. It is preserved unedited at `9b45f7965a9e8105f65b0f9be05ebe27474daf6b`
(local branch, unpublished; a bundle of that head was taken before the rebase).
The technical contract below is that revision's and is kept; what changed is who
it is for and how it is measured. Assume no outside implementer, user or
reviewer ever arrives: build for the owner's repositories, for future
clean-room rebuilds, and for agents that do not inherit the session in which a
feature was written.

External validation is still required for claims that are explicitly external —
independent implementability, novelty, general usefulness, portability across
uncontrolled implementations, public adoption. Nothing here claims any of
those, and internal use is not offered as evidence for them.

**Origin of the diagnosis:** a 2026-08-31 ecosystem analysis by Kimi correctly
identified the entry barrier, then proposed broad Python, Jupyter, ML and DeFi
surfaces that the machine does not provide. This ADR keeps the diagnosis and
rejects the scope expansion. The source is
`manifesto/quotes/Kimi/s0fractal_analysis.md` at manifesto commit
`f6d1c22ee50d`, file SHA-256
`1ba5b647d06290419f61ebb72cb3954140403dc2ba96707d08da6fafdb27742c`.

**Working thesis:**

> A consumer should be able to install one pinned artifact, supply the three
> inputs, and obtain the full Receipt — without vendoring the evaluator,
> without a Sigma source checkout, and without inheriting state from the
> machine the check was written on.

## 0. The gap this ADR exists to close

Three things are currently distinct, and the distance between them is the whole
problem:

```text
published package:       sigma-glyph 0.6.7
adopted specification:   anchor-set v0.7.0
current relation:        not yet one released, digest-pinned artifact
```

`0.6.7` is a real published package and a consumer can install it. `v0.7.0` is
the adopted anchor set, carried by warrant
`0e634c176b002d02d835e5c6436e4b254d065adeab4bc7704585339567ba46e1`. **Neither
identifies the other.** Installing the package does not tell a consumer which
specification edition it implements, and the anchor set does not name an
artifact a consumer can install. Nothing today closes that.

### 0.1 Four requirements already earned, not speculated

These came out of Phase 2 (`manifesto`, PR #1) by running things, and they are
the concrete content of the gap above.

1. **Checkout coupling is real and current.**
   `manifesto:tools/glyphlib.py` reaches the evaluator through a hardcoded
   absolute path — `SIGMA_GLYPH`, defaulting to
   `/Users/s0fractal/Projects/sigma-glyph` — and falls back to nothing. A
   consumer that does this has a dependency on one machine's directory layout.
   **Requirement:** no consumer may require a Sigma source checkout, a
   repository-relative path, or a mutable environment variable to reach the
   evaluator.

2. **Clean install works. This is a positive witness, and its scope is exact.**
   With `SIGMA_GLYPH` pointed at a path that does not exist and
   `sigma-glyph==0.6.7` installed from PyPI, all eleven checks of
   `manifesto:tools/aie_errata_check.py` pass in CI, reproducing the same ATP
   figures (27 and 601) as the source checkout. That demonstrates
   **clean-install consumption of a compatible evaluator API by a real
   consumer**. It does not demonstrate that the PyPI artifact represents the
   adopted anchor set, and it is not offered as that.

3. **A version pin is not a content-addressed boundary.**
   `pip install sigma-glyph==0.6.7` pins a *version*, not a wheel digest. Two
   installs of one version can differ, and nothing in the consumer notices.
   **Requirement:** the boundary is pinned by artifact digest, and a digest
   mismatch fails closed at install or at first use.

4. **Replay reads the bytes the receipt names.**
   The `manifesto` SSD pack does not regenerate: its declared command reports
   `refuted: 3` where the committed receipt records `refuted: 0`, because
   repo-layer claims re-read the *current* file rather than the bytes their
   own recorded `dep.sha256` names. **Requirement:** replaying a historical
   receipt MUST read dependency bytes from the pack or the CAS, addressed by
   digest. Reading the current file is a **drift check** — a different
   operation, reported as drift, never as a refutation of the original
   settlement.

## 0.2 Honest scope statements

Stated here rather than buried, because each one is a thing this ADR could be
misread as providing:

- `ADR-011` is a **merged, non-normative** proposal. Merging it adopted nothing.
- `EXP-ADR011-01` **has not started**.
- `church@v0` **cannot settle `PLUS 7 5`** — the case ADR-011 was written about.
- **Portable equality settlement remains blocked**: Sigma has no adopted
  content-addressed profile descriptor, and this ADR does not propose one.
- This proposal exposes **adopted Book I evaluation**. It adds no kernel
  equality, no raw-byte frontend, no Python-to-SKI compilation, and no
  universal application language.
- Internal use is evidence of usefulness **to this ecosystem**. It is not
  evidence of general public utility or of independent implementability.

## 1. The problem

The implementation already exposes the semantic relation Book I defines:

```text
eval(term_hash, uint32_budget, partial_content_environment) -> Receipt
Receipt = { exit, result_hash, atp_spent }
```

The released Python surface does not yet make that relation a complete
checkout-independent consumer workflow:

- `python -m sigma_glyph` runs the module self-test rather than evaluating a
  supplied term;
- the wheel intentionally omits the conformance corpora, so a wheel-only run
  cannot replay the normative vectors;
- the quick start begins with three local implementations and three Books,
  while the first user question is smaller: "can I run this exact check?";
- Warrant already packages `ski@v1` checks and authority, but Sigma-Glyph has no
  equally small raw evaluation command beneath that bridge;
- the repository's honest limitations are spread across the README, the
  security assumptions, the implementation guide, the papers and reviews.

This is a distribution and interface problem, not a missing reduction rule.

## 2. Evidence that bounds the answer

### 2.1 The interface has three semantic inputs

The content environment is not optional context. The same term and budget can
settle or return `unresolved_reference` depending on which demanded blobs are
present. Any simple API that accepts only a hash and an ATP budget repeats the
two-input error corrected in Book I v0.6.0.

### 2.2 A result hash is not a Receipt

`DISSONANCE(ATP Exhausted)` is also an ordinary term. The same result hash can
therefore occur with `exit=normal_form` or `exit=atp_exhausted`. A public
surface must return and test `exit`, `result_hash` and `atp_spent` separately.

### 2.3 The raw-byte frontend does not exist

`experiments/exp-002/RESULT.md` triggered K1 at the interface: the
pre-registered raw-byte task could not be instantiated under the published
Sigma-Glyph profile without inventing a new frontend encoding. Profile C1 is a
canonical lambda-to-SKI compiler; it is not a Python, JSON, notebook or ML
frontend.

### 2.4 The filed application needs do not ask for a Python runtime

The two classified packets under `needs/` ask about numeral encoding and memo
pricing. One was routed to an application profile; the other was already
supported without a protocol change. Neither is evidence that arbitrary Python
should enter Sigma-Glyph.

### 2.5 Warrant already owns the envelope

Warrant owns signed decision records, expected results, policy, authority,
settlement and evidence-pack transport. Re-inventing any of those here would
create two formats for one claim. Sigma-Glyph owns deterministic evaluation and
conformance. The bridge should remain thin.

## 3. Proposed decision

Ship one deliberately narrow distribution surface with four parts:

1. a command that evaluates one Book I term and prints one full Book I Receipt;
2. a reproducible conformance bundle for implementers;
3. one clean-environment walkthrough that re-runs a foreign Warrant reason and
   includes falsifying controls;
4. a compact capability ledger that says what the released surface does and
   does not establish.

The first release of this surface MUST NOT add a language, a pack format, a
truth predicate, a trust registry, a network fetch during reduction, or a new
normative document.

## 4. Ownership boundary

| Concern | Owner | This ADR may do |
| --- | --- | --- |
| canonical bytes, evaluation, Receipt | Book I | expose the adopted relation |
| term compilation | C1 or an external named frontend profile | accept an already compiled term |
| expected verdict and executable reason | Warrant `ski@v1` | consume or produce no rival envelope |
| signatures, authority, settlement | Warrant | report none of them |
| filesystem CAS adapter | distribution implementation | define a local, non-normative adapter |
| local resource admission | verifier/operator | expose explicit limits and refusals |
| Python/pytest/Jupyter semantics | their own runtimes | make no claim about them |

The phrase **verification surface** in this ADR means verification that the
Book I computation re-executed as specified. It does not mean that its premise
was true, its policy appropriate, its signer authorized, or its conclusion
accepted.

## 5. Candidate command-line surface

The spelling is provisional until implemented and adversarially reviewed. Its
semantic shape is not:

```bash
sigma-glyph eval \
  --term <64-lowercase-hex NodeHash> \
  --atp <uint32> \
  --blob-dir <directory> \
  --max-atp <local admission ceiling> \
  --max-node-depth <local ceiling> \
  --max-materialized-nodes <local ceiling> \
  --max-store-fetches <local ceiling> \
  --json
```

### 5.1 Inputs

- `--term` is exactly one Book I NodeHash.
- `--atp` is exactly one uint32 budget.
- `--blob-dir` is a partial content environment: regular files named by their
  lowercase 64-hex NodeHash and containing the raw canonical bytes under that
  hash. A Warrant store can pass its existing `.warrants/blobs` directory
  directly.
- local implementation fences are explicit operator policy. At minimum the
  released Python verifier exposes `max_atp`, `max_node_depth`,
  `max_materialized_nodes` and `max_store_fetches`, with conservative defaults.

The implementation validates the term and budget before store access. It reads
the store demand-first, never walks the directory recursively, never follows a
symlink outside the declared blob directory, and verifies every blob against
the filename before admitting it into the content environment.

### 5.2 Canonical success output

On a canonical Book I execution, stdout is exactly one JSON object carrying the
three fields Book I defines:

```json
{
  "exit": "normal_form",
  "result_hash": "<64-lowercase-hex>",
  "atp_spent": 17
}
```

The other canonical exits are `atp_exhausted` and
`unresolved_reference`. They also exit the process successfully: they are
results of the semantic machine, not local command failures.

There is deliberately no generic `ok` field. Sigma-Glyph computes. A named
profile or Warrant check decides whether the Receipt satisfies a claim.

### 5.3 Local refusal and fault surface

Invalid caller input, local admission refusal and implementation/resource fault
are not Book I exits and MUST NOT be serialized as a Receipt.

The CLI must distinguish at least:

```text
0  canonical Book I Receipt, including exhaustion or unresolved reference
2  caller input or local policy refused before evaluation
3  local implementation/resource fault
```

Diagnostics go to stderr and name the boundary that refused. Exact diagnostic
JSON, if later needed, is a distribution contract and not a Book I outcome.

### 5.4 Library surface

The library continues to expose the adopted relation rather than a truth-like
wrapper:

```python
receipt = sigma_glyph.eval_receipt(term_hash, atp, content_env, limits)
```

This ADR rejects an API shaped like:

```python
verify(term_hash, atp).ok
```

It omits the content environment, collapses the Receipt, and leaves `ok`
undefined.

### 5.5 What re-execution still trusts

This surface moves trust; it does not abolish it. The operator still trusts the
installed wheel or binary, its language/runtime and host, SHA-256, the local
resource fences, and the claim that the supplied term is the check they meant
to run. The conformance bundle gives executable evidence about named behavior;
it does not prove that the installed implementation refines the Lean model or
that the check asks the right semantic question.

The walkthrough therefore pins and verifies the distribution artifact before
installation, prints the implementation and supported Book anchor, and keeps
the executable Receipt separate from authority and semantic acceptance. A green
re-execution establishes bounded artifact behavior under named inputs, not the
truth of an external claim.

## 6. The conformance bundle

The installed wheel and the normative conformance artifact solve different
problems and should not pretend otherwise.

For every distribution release that claims support for an adopted bundle,
publish a reproducibly built release asset containing only existing governed
material and its runner contract:

```text
MANIFEST.json
SHA256SUMS
spec/book-1-truth.md
spec/schemas/book1-conformance.schema.json
tests/spec_conformance/vectors.json
tests/spec_conformance/README.md
```

`MANIFEST.json` records:

- distribution version;
- adopted bundle version and full anchor-set digest;
- full digests of every included file;
- source commit;
- build recipe and `SOURCE_DATE_EPOCH`;
- the exact command used to replay it with each shipped implementation.

The asset is packaging, not a fourth source of normative truth. Every included
normative byte must equal the byte named by the adopted anchor set. Build CI
must reproduce the archive byte-for-byte, download it back, verify every digest
and run every advertised command from the downloaded copy.

An implementation that passes the bundle may claim conformance to the named
predicates and vectors. It may not claim independent validation, correctness of
every sentence, physical-memory bounds, or external adoption.

## 7. The first consumer walkthrough

The first demonstration is not another self-test, and it is not aimed at a
stranger. It starts in a fresh temporary directory with **no Sigma checkout**
and uses one digest-pinned artifact plus one existing Warrant evidence pack —
because that is precisely the condition §13.3 requires and
`manifesto:tools/glyphlib.py` currently fails.

The page and its generated transcript must show:

1. create a fresh virtual environment;
2. download one `sigma-glyph` wheel, **verify its SHA-256 against the digest
   the release names**, install that local artifact and print what was
   installed. A version pin is not sufficient here (§0.1.3): the check is on
   the artifact digest, and a mismatch aborts;
3. download one evidence pack with a published SHA-256;
4. identify the Warrant `ski@v1` term, budget and blob directory without
   rewriting them into a Sigma-specific envelope;
5. run `sigma-glyph eval` offline and obtain the expected full Receipt;
6. run the Warrant verifier/checker and show what extra question Warrant answers;
7. execute the negative controls below.

Network use is named and counted. After installation and pack download,
re-execution is offline.

### Required negative controls

Each control is a gate, exits non-zero where non-zero is expected, and is shown
by mutation to fail for its own reason:

| Mutation | Required observation |
| --- | --- |
| replace one blob under a pinned filename | refused before its bytes reach evaluation; CAS mismatch named |
| remove one demanded blob | canonical `unresolved_reference`, not a local error |
| change `atp` outside uint32 | refusal before store access |
| claim an ATP budget above local policy | local admission refusal, not `atp_exhausted` |
| change only the expected exit in the Warrant check | Warrant check fails even if `result_hash` is unchanged |
| change only the expected result hash | Warrant check fails and names the result field |
| change the artifact digest of the installed wheel | install or first use fails closed, naming the expected and actual digest |
| change the Book anchor or anchor-set digest the artifact declares | the consumer refuses rather than evaluating under an unnamed edition |
| add or retype one JSON field of the Receipt | the consumer refuses the output shape rather than ignoring the field |
| replay a receipt whose dependency bytes have since changed on disk | the **pinned** bytes are read from the pack/CAS and the replay still settles; a separate drift check reports the on-disk difference as drift, never as a refutation (§0.1.4) |

The transcript is generated by running the commands on the page. A parser-only
documentation gate is useful but cannot substitute for that execution.

## 8. Capability ledger

Add one short, generated-or-evidence-linked surface that a new reader can
understand without reconstructing claims from the whole repository. The initial
ledger should say, in substance:

| Capability or evidence | Honest status |
| --- | --- |
| deterministic evaluation for fixed term/budget/valid partial store | provided by Book I |
| full canonical Receipt | provided |
| semantic materialized-node bound | provided under the theorem's assumptions |
| physical RSS/heap/stack bound | not provided |
| arbitrary Python execution | not provided |
| Python/Jupyter-to-SKI compiler | not provided |
| raw JSON/byte frontend | not provided; EXP-002 stopped here |
| authority or policy acceptance | Warrant/application concern |
| implementations outside one author/model lineage | none known |
| independent user reproduction | **none, and not sought by this ADR.** Listed in NOT CLAIMED, never as a delivery gate, prerequisite or kill condition |
| peer review of the papers | none |

Mechanically derivable rows are generated from the release and conformance
artifacts. Social rows cite dated external evidence or say `none known`; they
must not be inferred from download counts, model reviews or internal CI.

## 9. A possible pytest adapter — later and thin

A pytest adapter is considered only if an owned consumer demonstrates need
during S2 or S3 (§11). It may re-run an already compiled, immutable
check:

```python
@pytest.mark.sigma_check(
    warrant="fixtures/check.warrant",
    store="fixtures/.warrants",
)
def test_foreign_reason(receipt):
    assert receipt.exit == "normal_form"
```

It MUST NOT:

- compile the decorated Python function into SKI;
- describe ordinary Python execution as Sigma-verified;
- define a second check or evidence-pack schema;
- hide the term hash, budget, store commitment, exit or local limits;
- turn a skipped replay into a pass.

If the adapter needs any of those, it is not an adapter. It is a new frontend or
protocol and requires a separately filed need, preregistration and ADR.

## 10. Explicit non-goals

This proposal does not include:

- arbitrary Python, notebook or ML-pipeline execution;
- a Python-to-SKI compiler;
- a raw-byte or JSON frontend;
- a kernel `EQ` primitive or adoption of ADR-011;
- DSSE, signatures, trust registries, policy or settlement;
- network access during reduction;
- a SaaS endpoint;
- DeFi, smart-contract, legal or scientific-paper positioning;
- Book II/III redesign;
- a claim that stars, downloads or model agreement are external validation.

Book II and Book III remain available, but the first consumer path does
not require them. Navigation and federation are advanced layers, not entrance
requirements for Book I evaluation.

## 11. Delivery order

### S0 — freeze the surface before code

- adversarially review the three inputs, Receipt and local error separation;
- decide one filesystem-CAS adapter without making it normative;
- publish exact command examples and expected exit codes;
- write the negative controls before implementation.

### S1 — one executable vertical

- implement the Python CLI over `eval_receipt`;
- execute the clean-environment walkthrough;
- build and download-back the conformance artifact;
- make wheel-surface, transcript and negative-control gates mandatory for the
  files they cover.

### S2 — integrate Warrant and manifesto

The two owned consumers, each against the digest-pinned artifact:

- Warrant's `ski@v1` evidence/replay path;
- the `manifesto` SSD pack, starting by removing the hardcoded `SIGMA_GLYPH`
  path from `tools/glyphlib.py` (§0.1.1);
- for each: the glue removed, the three inputs supplied, the full Receipt
  preserved without boolean collapse, and the negative controls proving the
  consumer depends on the released boundary rather than on a checkout;
- record every sentence an integrator had to guess, and treat each as a surface
  defect rather than integrator error.

### S3 — upgrade/drift drill and maintenance observation

- run the seven-mutation breaking-change drill of §A.5 across both consumers;
- run the upgrade path: it must reproduce the pinned behaviour or fail closed,
  never silently change a receipt;
- run the replay/drift split: pinned bytes replay, on-disk difference reports as
  drift (§0.1.4);
- observe maintenance cost over the two consumers and report §13.7's balance,
  including when it is negative.

### Optional adapter

A thin pytest adapter is considered **only if an owned consumer demonstrates
need** during S2 or S3. It is not scheduled, and nothing in S2 or S3 waits on
it. No Jupyter, framework integrations or additional plugins are queued by this
ADR.

## 12. Acceptance criteria

The candidate surface is ready to merge as a non-normative distribution feature
only when all of the following are true:

1. A fresh virtual environment, outside the checkout, installs the pinned wheel
   and evaluates the frozen foreign term.
2. The output compares all three Receipt observables separately.
3. Exhaustion and unresolved content are successful canonical executions;
   caller refusal and local fault are not.
4. Every negative control is shown rejecting its own mutation for its own
   reason.
5. No command executes shell text from the pack or follows a content path
   outside the declared blob directory.
6. The conformance archive is reproducible, download-back verified and bound to
   the adopted anchor set it names.
7. The walkthrough contains no command the released wheel does not provide and
   no output copied from a different run.
8. Both owned consumers run against the digest-pinned artifact and neither
   requires a Sigma source checkout, a repository-relative path, a mutable
   environment variable or a hidden cache (§13.1–13.3).
9. No anchored byte changes.
10. The implementation and documentation pass focused adversarial review; green
    local suites alone are not that review.

## 13. Success metrics

Every external-adoption metric is removed. The earlier revision measured
success by "one person outside the author/model lineage", which is not
measurable by this project and not what the surface is for. These seven are
measurable inside it, and each is a gate rather than an impression.

1. **Two owned repositories consume the same released, digest-pinned artifact.**
   The first two are Warrant's `ski@v1` evidence/replay path and the
   `manifesto` SSD pack.
2. **Neither consumer vendors or reimplements the evaluator.** No copied
   `sigma_glyph.py`, no reimplemented reduction, no second serializer.
3. **Neither consumer requires a Sigma source checkout, a repository-relative
   path, a mutable environment variable, or a hidden local cache.** Today
   `manifesto:tools/glyphlib.py` fails this outright (§0.1.1).
4. **A clean environment reproduces the same full Receipt from the same three
   inputs** — same `exit`, same `result_hash`, same `atp_spent`.
5. **An upgrade either reproduces the pinned behaviour or fails closed at the
   boundary.** It never silently changes a receipt.
6. **Mutating each of `exit`, `result_hash`, `atp_spent`, blob bytes, artifact
   digest, Book anchor and output schema makes at least one consumer gate fail
   for the named reason.** Seven mutations, seven named failures.
7. **The shared layer removes more from the consumers than it adds — judged
   semantically, not by line count.** Lines removed versus added is kept as a
   *descriptive* figure, reported per consumer including when negative, but it
   is not the gate: a reformat can win it and a test suite can lose it. The gate
   is five findings, each yes or no:
   - the named checkout, environment-variable and path adapters are **deleted**
     (for `manifesto`, the hardcoded `SIGMA_GLYPH` lookup in
     `tools/glyphlib.py`);
   - **no duplicated evaluator or serializer** remains in either consumer;
   - the consumer **no longer makes local semantic decisions on Sigma's
     behalf** — no re-derived exits, no locally invented equality, no
     reinterpreted budgets;
   - every **added packaging, configuration and test responsibility is
     enumerated**, not summarised;
   - the balance of those four **may come out negative**, and when it does the
     surface is frozen rather than argued for.

Both consumers must be inspected live before the integration seam is asserted.
Nothing in §14's plan may be written from remembered repository structure.

## 14. Kill criteria and routing rules

Stop this proposal rather than expanding it when any of the following occurs:

- the CLI needs Python semantics, a raw-byte language or an implicit compiler;
- the walkthrough needs a new evidence envelope instead of Warrant's;
- `ok` cannot be defined without importing policy or authority;
- the filesystem adapter starts deciding canonical semantics;
- a pytest/Jupyter integration requires hiding any of the three semantic inputs;
- a conformance bundle differs from the anchored bytes it claims to package.

Route each pressure to its owner:

- new frontend encoding -> `needs/` packet plus a separate experiment/ADR;
- decision envelope or expected verdict -> Warrant;
- authority/settlement -> Warrant policy and jurisdiction;
- new canonical result or ATP rule -> Book I candidate and governed re-anchor;
- application ergonomics -> application adapter, without protocol status.

If the hardened S1 vertical cannot carry **both owned consumers** off a
checkout — or if §13.7's balance comes out negative — freeze it. Do not add
integrations to compensate: the surface exists to remove duplicated semantics
from two repositories, and a surface that does not is not improved by a third
consumer.

## 15. Falsifiers

- Warrant's existing path already gives both owned consumers everything this
  surface would, and a Sigma CLI would only duplicate it -> reject the CLI and
  improve the bridge documentation instead.
- A clean environment can already perform the raw Book I evaluation from the
  released artifact without guessing store layout, exit semantics or limits ->
  the stated interface gap is smaller than claimed.
- The filesystem CAS adapter cannot remain an implementation detail -> stop and
  file the profile explicitly before shipping it.
- An external implementer cannot consume the conformance artifact without the
  Python oracle acting as arbiter -> the bundle fails its purpose.
- The only demand for pytest requires compiling arbitrary Python -> do not build
  the adapter.

## 16. Epistemic ledger

**ESTABLISHED**

- Book I's three-input relation and full Receipt exist in the adopted bundle.
- The released wheel's default module command is a self-test, not a supplied-term
  evaluator.
- The wheel omits the conformance corpora and announces replay skips.
- EXP-002 stopped at the missing raw-byte frontend.

**PROPOSED, NOT MEASURED**

- that the CLI above materially lowers the barrier;
- that a separate conformance asset is preferable to shipping corpora in the
  wheel;
- that pytest users want a thin precompiled-check adapter.

**NOT CLAIMED**

- product-market fit;
- uniqueness among verifiable runtimes;
- mathematical guarantees for Python, ML, legal, financial or scientific
  workflows;
- independent validation or external demand.

The proposal succeeds by making one already-existing guarantee easier to use.
It fails if it needs to invent a larger machine to appear useful.

---

# Appendix A — Implementation plan (PLAN ONLY)

**No implementation code is authorised by this ADR.** This appendix exists so
that the two integrations can be falsified before anything is built. Phase 4
does not start because this PR is green.

## A.1 Minimal interface

```text
sigma-glyph eval \
  --term <hex64> \
  --atp <uint32> \
  --blob-dir <path> \
  --max-* <explicit-local-limits> \
  --json
```

The executable/package name is a packaging decision, not a normative Book
change. Nothing here alters `eval`'s three inputs or the Receipt.

## A.2 Output and process status

On successful Book I evaluation, the **full Receipt only**:

```json
{
  "exit": "normal_form | atp_exhausted | unresolved_reference",
  "result_hash": "<hex64>",
  "atp_spent": 0
}
```

**No `ok` field.** `atp_exhausted` and `unresolved_reference` are canonical
exits — successful executions of the evaluator — and MUST NOT be reported as
process failures. Malformed caller input, a rejected content environment, and
local resource or tool faults need separate non-zero process exits with
machine-readable diagnostics. The exact taxonomy is pinned before
implementation; adding a code later is a contract change.

## A.3 Store boundary

- validate term hash, ATP value, path and local-limit arguments **before any
  store read**;
- fetch only hashes evaluation demands;
- never recurse over or trust an entire directory;
- reject path and symlink escapes;
- verify every loaded blob against the hash used to request it;
- distinguish missing content from malformed content from a local I/O or
  resource fault;
- state whether blob filenames are lowercase hex, and whether extra files are
  ignored or rejected.

## A.4 Release and conformance asset

A release artifact installable in a clean environment and **pinned by
cryptographic digest** — the requirement §0.1.3 names, and the thing
`pip install sigma-glyph==0.6.7` does not provide. Its conformance asset derives
from the adopted anchor-set bytes and identifies: release/package version;
source commit; Book I anchor and anchor-set digest; suite/schema digests;
supported platform and toolchain matrix; the exact command and a **closed** test
inventory. No network access after installation for local replay.

**The binding is one-directional, and that is deliberate.** An earlier draft of
this appendix required that "the artifact names the anchor set, and the anchor
set names the artifact". The second half is not achievable here: the adopted
anchor set is anchored bytes, so making it name an artifact means rewriting
those bytes and re-anchoring under governance — which this ADR explicitly
excludes. Requiring it would have made the acceptance criterion unsatisfiable
by anything this ADR authorises.

The achievable boundary:

- the **release manifest names the anchor set** it was built against;
- the manifest carries the **artifact digest**, the **source commit**, and the
  **suite/schema digests**;
- if a verifiable link in the other direction is wanted, a **separate Warrant
  release record** binds artifact digest to adopted anchor set — a record, not
  an edit;
- **the adopted anchor set is not rewritten**, at any point, by anything here.

A reverse binding inside the anchor set itself is a separate future governance
proposal. It is not an acceptance criterion of this ADR, and §0's gap is closed
from the artifact side only.

## A.5 Consumer integration plan

For **Warrant** (`ski@v1` evidence/replay) and **manifesto** (SSD pack),
each specified separately after inspecting the live consumer:

- the exact current glue or evaluator code to be removed — for manifesto this
  begins with the hardcoded `SIGMA_GLYPH` path in `tools/glyphlib.py`;
- the pinned artifact digest and the installation boundary;
- the three inputs the consumer supplies;
- how the full Receipt is preserved without boolean collapse;
- clean-environment reproduction;
- upgrade procedure, and rollback / fail-closed behaviour;
- negative controls proving the consumer depends on the released boundary
  rather than on a copied implementation or a source checkout.

**SSD replay specifically.** Dependency bytes are read from the pack or the CAS
by digest. The current-file read becomes a separate drift check with its own
output. A receipt that no longer reproduces because a file moved underneath it
is a drift report, not a refutation — today it is reported as `refuted`, which
is the defect (§0.1.4).

### Breaking-change drill

Each mutated independently; each must fail at the consumer that claims to bind
that field, and for the stated reason:

`exit` · `result_hash` · `atp_spent` · one demanded blob byte · package/artifact
digest · Book anchor or anchor-set digest · a JSON field name/type or an
unexpected field.

A **closed** test set is preferred: adding or removing a test is itself a
visible contract change.

## A.6 Kill criteria

Freeze or delete the surface if, after the two integrations, any of these
remains true:

- it requires a new language or frontend to be useful;
- it creates a second envelope, signing or authority protocol;
- consumers still vendor evaluator logic or require a Sigma checkout;
- it adds more maintained glue than it removes;
- full Receipt fields are collapsed or discarded at either consumer;
- upgrades cannot be pinned and made fail-closed;
- the only demonstrated benefit is that Sigma can call itself through a new
  wrapper.
