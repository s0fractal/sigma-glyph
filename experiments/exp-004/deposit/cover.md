---
title: "Does One Integer Still Price Work and Memory in Parallel? A Preregistered Experiment on Interaction Combinators"
author:
  - name: Serhii Glova
    affiliation: independent
    email: sergey.glova@gmail.com
date: 2026-08-24
keywords:
  - interaction nets
  - interaction combinators
  - resource bounds
  - preregistration
  - parallel reduction
  - scheduling
classification: cs.LO, cs.PL
---

# What this document is

Σ-GLYPH Book I proves that a single unsigned integer prices both the work an
evaluation performs and the peak memory it materialises, at every configuration
of a **sequential** machine. This report asks whether that carries over to a
setting where reduction is local and confluent and no order is fixed, and answers
it by measuring one small reducer for Lafont's interaction combinators.

It is short, and it is deliberately narrow. It measures nets, not programs; it
measures one reducer, not any existing runtime; and half of its question is
settled by arithmetic rather than by experiment, which the preregistration says in
advance so that the arithmetic cannot later be presented as a discovery.

# Why the two parts are printed together

The point of this record is as much the method as the result. What follows is:

- **Part I — the preregistration**, exactly as committed at
  [`d3eea63`](https://github.com/s0fractal/sigma-glyph/commit/d3eea63), *before*
  the reducer existed. It fixes three hypotheses, names what would make the
  experiment worthless, and states that the result would be written whichever way
  it came out.
- **Part II — the result**, which was written after the measurement and then
  corrected three times in review. Its corrections section names what earlier
  versions claimed and why those statements were wrong, rather than repairing
  them silently.

Neither part has been edited to agree with the other. Where the preregistration's
wording turned out to be ambiguous — hypothesis H2 says "a factor that grows with
net size" without fixing whether the factor is absolute or relative — the result
says so and the hypothesis text is left alone, because editing a hypothesis after
the numbers is the one thing a preregistration exists to prevent.

# Provenance

| | |
| --- | --- |
| repository | <https://github.com/s0fractal/sigma-glyph> |
| preregistration | `experiments/EXP-004-parallel-bound-preregistration.md` |
| result, code, receipt | `experiments/exp-004/` |
| corpus | 29 nets, pinned by exact structure in `fixtures.json` |
| receipt | `results.json`, byte-identical across two local replays and a Linux CI runner |
| controls | nine, each broken in turn by `selftest.py` and required to fail for its own reason |

The deposited snapshot of the repository accompanies this document. On the
archived commit, the experiment's own workflow re-derives `results.json` and
fails if it differs from the committed one.

# What this record does not claim

It is not peer reviewed. A DOI is a permanent address and a frozen artifact; it
is not a venue and not an endorsement.

It is not evidence about HVM or any other runtime: none was measured, read or
run. Its statement about interaction counts is a statement about counting.

Its schedules are greedy rather than optimal, so every difference it reports
between schedules is a lower bound. Its transient-memory figures depend on an
allocation discipline that was chosen and declared, not derived from the rewrite
rules. Its observation that peaks stayed within 1.5× across schedules on
normalising nets is a property of 29 nets and not a bound.

# Author contribution and model use

The reducer, the corpus, the harness, the controls and this prose were written by
an AI model (Anthropic Claude, `claude-opus-5`) working under the author's
direction and authority. Three rounds of adversarial review were conducted by
separate fresh-context model sessions — OpenAI Codex and a second Claude session —
prompted by the author.

That review found nine defects, **six of them in the controls rather than in the
measurement**: a schedule capped on rounds instead of interactions, a receipt
carrying one schedule's count for four, a transient formula that did not match its
own description, an allocation profile checked only through its difference so that
`5` and `3` passed where the reducer does `4` and `2`, a batch schedule that
truncated the round it was evidence about, and a reserved-then-released figure
assembled from maxima of different rounds. None of the six was anticipated by the
session that wrote the controls.

This is not independent audit. All reviewers were language-model sessions
prompted by the same author, and the finding above is the reason the review
happened at all rather than a reason to trust the artifact more.

\newpage

# Part I — The preregistration

*Committed at `d3eea63`, before any reducer or measurement existed. Reproduced
here unedited.*

