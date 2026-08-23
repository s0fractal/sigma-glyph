# EXP-004 — does the one-integer bound survive parallel interaction nets?

**Preregistration. No measurement has been taken.** Non-normative: nothing here
changes Book I or any released contract.

## The question, stated so it can fail

Book I proves `size ≤ spent + 1` at every configuration a run passes through, and
it rests on one per-step lemma: a fired action grows the term by at most
`cost − 1` (`size_step` in `EvalMachine.lean`). The schedule is fixed — leftmost
outermost, one action at a time.

Interaction nets make the opposite trade: rewriting is local and strongly
confluent, so independent reductions proceed in any order and still meet. The
question is whether a single integer can still price work *and* peak memory when
no order is fixed.

## What is already decided on paper, and should not be measured

Every interaction-combinator rule has a fixed net-size delta: annihilation
removes two nodes, commutation replaces two with four, erasure against a binary
agent leaves two. So `Δsize ≤ +2` per interaction, unconditionally, and

    peak ≤ initial + 2 × interactions

follows by the same telescoping Book I uses. Publishing that as a finding would
be dressing arithmetic as a result. **The form of the invariant transfers, and
this experiment does not claim credit for it.**

## What is genuinely open, and is what gets measured

Confluence promises the same *normal form* under any schedule. It promises
nothing about the *peak*. So:

**H1 — the peak is schedule-dependent.** Two schedules reducing the same net to
the same normal form reach different maximum sizes.

**H2 — the gap is not marginal.** Over the sampled nets, the worst schedule's
peak exceeds the best schedule's by a factor that grows with net size rather
than staying within a small constant.

**H3 — the interaction count is schedule-invariant**, or nearly so, for
interaction combinators.

If H1 is false, one integer prices both exactly as it does in Book I, and the
result is stronger than expected. If H1 is true, the honest statement is that a
single budget can still *bound* both, but only against the worst schedule: the
number you prepay stops predicting the memory you actually need, which is a
weaker guarantee than the sequential machine gives.

## Protocol

- implement Lafont's interaction combinators (γ, δ, ε) with the three rule
  families, in plain Python, no dependencies;
- two schedulers over the identical net: **sequential** (one redex at a time, a
  fixed deterministic choice) and **maximal-parallel** (every active pair
  reduced in one step, which is where confluence is doing the work);
- corpus: nets generated from a fixed seed list, plus hand-built nets that
  duplicate a shared structure, because duplication is where the peak lives;
- record per net: interactions, peak size, final size, and whether both
  schedules reach the same normal form;
- **negative control**: a net whose normal form differs between schedules would
  mean the implementation is wrong, not that confluence fails; the run fails
  rather than reports.

## What would make this worthless

Choosing nets after seeing the numbers. The corpus and the seeds are fixed in the
first commit of the implementation, before any measurement is recorded, and the
result is written whichever way it comes out.

## What this cannot say

It cannot say anything about HVM's internals, which are not measured here, and it
cannot say Book I's theorem is wrong or right in a setting Book I does not claim.
It measures one property of one small reducer, and the transfer question is about
the *shape* of the invariant, not about anyone's implementation.

| Date | Change | Result already known? |
| --- | --- | --- |
| 2026-08-23 | initial preregistration | no |
| 2026-08-23 | result recorded in exp-004/RESULT.md; nothing above was edited | — |
| 2026-08-23 | four review defects corrected in the result; nothing above was edited | yes |
| 2026-08-24 | five further defects corrected; corpus pinned by exact structure, not regenerated; nothing above was edited | yes |
