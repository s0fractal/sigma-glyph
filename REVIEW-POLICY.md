# When a multifamily gate is worth running

Set by the project owner, 2026-08-30, after five rounds of the v0.7.0 gate.

> **Round 6 is the final multifamily gate for this normative candidate. After it,
> do not use OpenRouter for ordinary implementation, test, documentation, parser,
> or non-anchored changes. Codex + Claude review and the full repository matrix
> are sufficient. Reopen a multifamily gate only for a new normative/adoption
> candidate, a security/governance boundary, or an unresolved cross-review
> disagreement.**

## Why the v0.7.0 rounds were worth it

The candidate moves **anchored normative bytes**, adds new `MUST` clauses, and
corrects a specification already deposited at a DOI. Over five rounds the outside
families found P0s that the inside review had missed — including one, the
`FALSE`/`APPLY(K,I)` wave divergence, that had been in the tree since before this
candidate and was invisible while the reference oracle outranked the prose.

That is the case for a gate. It is not a case for gating everything.

## What does NOT need one

Implementation, refactoring, tests, documentation, parser and gate tooling, and
non-anchored experiments. Two reviewers and the full matrix decide those. A gate
run on every change is not more assurance; it is theatre paid for by the budget
that a real gate needs.

## What does

- final normative bytes before adoption;
- security, cryptography or governance boundaries;
- a public paper or Zenodo release;
- an unresolved disagreement between the standing reviewers;
- an occasional sampled audit — sampled, not per pull request.

## Rules of a round

- **One multifamily round per frozen candidate.**
- **A new round only if a finding changed normative semantics or an anchored
  suite.** Engine, test or gate-parser changes that move no anchor do not void a
  normative review.
- **`ADOPT` from models is adversarial evidence, not adoption.** The threshold
  warrant remains a separate act by the roster, and no number of model verdicts
  substitutes for it.

## What the rounds actually cost, for calibration

Six rounds, three families, a prompt of roughly 130–150 KB: about $12 of
OpenRouter credit, one round of which died mid-way on `HTTP 402` and had to be
re-delivered. Two families spent three rounds' worth of budget producing
reasoning traces and no verdict at all. The signal was real and it was not cheap,
which is the argument for spending it where the bytes are anchored.

The next valuable signal is not another round. It is an adopted anchor, a
deposited v2, and somebody using this who did not write it.
