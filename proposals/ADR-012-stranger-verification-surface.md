# ADR-012: A stranger-facing evaluation surface

**Status:** DRAFT — non-normative product-surface proposal. Not implemented,
not gated, not adopted, and not part of any Specification Anchor. It proposes
no change to Books I–III, their schemas, their vectors, ATP pricing, or
governance.

**Origin:** the repository says that Sigma-Glyph exists so a stranger can
re-run someone else's bounded check. Today the shortest installed-package path
mostly runs the repository's own self-tests. A 2026-08-31 ecosystem analysis by
Kimi correctly identified the entry barrier, then proposed broad Python,
Jupyter, ML and DeFi surfaces that the machine does not provide. This ADR keeps
the diagnosis and rejects the scope expansion.

**Working thesis:**

> Sigma-Glyph should be a small, boring evaluator for content-addressed checks,
> not a sandbox for arbitrary Python. A stranger should be able to install it,
> re-run one foreign reason, inspect the full Receipt, and falsify the result by
> changing one input — without reading the Three Books and without trusting a
> repository checkout.

## 1. The problem

The implementation already exposes the semantic relation Book I defines:

```text
eval(term_hash, uint32_budget, partial_content_environment) -> Receipt
Receipt = { exit, result_hash, atp_spent }
```

The released Python surface does not yet make that relation a complete
stranger-facing workflow:

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

## 7. The first stranger walkthrough

The first product demonstration is not another self-test. It starts in a fresh
temporary directory with no checkout and uses the released wheel plus one
existing Warrant evidence pack.

The page and its generated transcript must show:

1. create a fresh virtual environment;
2. install one pinned `sigma-glyph` distribution and print what was installed;
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
| independent user reproduction | none until an external receipt is filed |
| peer review of the papers | none |

Mechanically derivable rows are generated from the release and conformance
artifacts. Social rows cite dated external evidence or say `none known`; they
must not be inferred from download counts, model reviews or internal CI.

## 9. A possible pytest adapter — later and thin

A pytest adapter is allowed only after the CLI and stranger walkthrough have
survived one independent use. It may re-run an already compiled, immutable
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

Book II and Book III remain available, but the first stranger-facing path does
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

### S2 — independent use

- ask for no testimonial and no broad adoption;
- obtain one independently executed transcript or one independent
  implementation report;
- record every sentence the user had to guess;
- treat each guessed sentence as a surface defect, not user error.

### S3 — optional adapter

Only after S2, decide whether a thin pytest adapter removes real friction. No
Jupyter, framework integrations or additional plugins are queued by this ADR.

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
8. The capability ledger says `none known` for independent use until evidence
   from outside the author/model lineage exists.
9. No anchored byte changes.
10. The implementation and documentation pass focused adversarial review; green
    local suites alone are not that review.

## 13. Success metrics

The first meaningful success is one person outside the author/model lineage who
installs the released artifact and reproduces the Receipt on their machine.

The second is an independent implementer who can say either:

- "my implementation agrees," or
- "I had to guess this exact sentence."

Both are stronger evidence than stars, package downloads, internal sibling use,
LLM agreement or another case study authored inside the same lineage.

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

If the hardened S1 vertical produces no independent use, freeze it. Do not add
ten integrations to compensate for the absence of one user.

## 15. Falsifiers

- The current Warrant walkthrough already provides the entire stranger journey,
  and a Sigma CLI would only duplicate it -> reject the CLI and improve the
  bridge documentation instead.
- A clean-environment user can already perform the raw Book I evaluation from
  the wheel without guessing store layout, exit semantics or limits -> the
  stated interface gap is smaller than claimed.
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
