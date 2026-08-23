# EXP-004 — result

Judged against [`EXP-004-parallel-bound-preregistration.md`](../EXP-004-parallel-bound-preregistration.md),
written before the reducer existed. The corpus was committed at `3040b57`, before
`measure.py` was written. No net was added or removed after a number was known.

| | |
| --- | --- |
| reducer | Lafont's interaction combinators, `G`/`D<label>`/`E`, labelled duplicators as in HVM |
| corpus | 29 nets in four families, 21 of which normalise |
| schedules | sequential, shrink-first, grow-first, maximal-parallel |
| caps | 200,000 interactions or 40,000 agents, whichever comes first |

## The short version

**The bound transfers. The number stops describing the run.**

Peak memory is still bounded by one integer that also pays for work, under every
schedule, and the measurement confirms it on all 29 nets. But the interaction
count is schedule-invariant while the peak is not, so the single number is a
bound over schedules rather than a description of any particular one. How much
it loses is itself computable, which is the useful part — and there is one
regime where it loses everything.

## What was settled on paper, and stayed settled

Every rule changes the agent count by at most `+2`: commutation replaces two
agents with four, annihilation removes two, erasure against a binary agent
replaces two with two. So

    peak ≤ initial + 2 × interactions

and priced at 3 ATP per interaction this is exactly Book I's per-step shape,
`Δsize ≤ cost − 1`, telescoping to `size ≤ spent + initial`. The preregistration
said in advance that publishing this as a finding would be dressing arithmetic as
a result, and it is not published as one. It is *checked* on every row instead of
argued, and it never failed.

There is a structural reason it holds so easily, and it is worth more than the
arithmetic: **a duplicator can never copy an active pair.** Both principal ports
in an active pair are occupied by each other, so nothing can reach them to copy
them. Pending work cannot be duplicated. That is exactly the property λ-calculus
lacks, and it is why a single work-and-memory budget is more at home here than in
the setting Book I proves it for.

## H1 — confirmed. The peak is schedule-dependent

13 of the 21 normalising nets reached different peaks under different schedules.
The 8 that did not are the two control families plus one net already in normal
form: `dup-tree` has no shrinking interaction, so every schedule *must* agree, and
it did — a spread there would have meant the harness was inventing one.

## H2 — half right, and the half that is wrong matters

As an absolute count the gap grows without limit: `race-3-4` spreads by 8 agents,
`race-7-256` by 254, linearly in the size of the net. As a **ratio** it does not:
across every net that normalised, the worst schedule's peak stayed within **1.5×**
the best. H2 predicted the gap would not stay within a small constant. On
normalising nets, proportionally, it does.

## The finding neither hypothesis anticipated

**The spread is exactly the reordering of a fixed multiset, and it is computable
in advance.**

Strong confluence gives interaction nets uniform normalisation: every reduction
path to normal form performs the same interactions, and only their order may
differ. So the reachable peaks are the prefix sums of one fixed sequence of
`+2`/`0`/`−2` steps, and no two schedules can differ by more than

    2 × min(growing interactions, shrinking interactions)

That is a prediction, not an observation, and it holds on all 21 normalising nets
— reached **exactly** on 19 of them. The two that fall short (`random-1-48`,
`random-13-48`) fall short because the greedy schedules cannot reach the extreme
order, not because the bound is loose.

This is the answer to the question as asked. Σ-GLYPH's one integer survives the
move to a confluent parallel setting, and the precision it loses is not unknown:
it is bounded by a quantity computed from the same accounting that produced the
budget.

## Where it does break

On nets that do not normalise, the multiset is no longer fixed, and the schedule
decides whether memory is bounded at all.

`random-3-12` — twelve agents. At **equal work**, 200,000 interactions:

| schedule | peak agents |
| --- | --- |
| shrink-first | 14 |
| sequential | 16 |
| maximal-parallel | 20 |
| grow-first | ≥ 40,002 (stopped at the size cap) |

A factor of **2,857** on the same net doing the same amount of work. The bound
`size ≤ spent + initial` is still true here and still useless: it tracks what was
spent, and what was spent is a property of the schedule, not of the computation.
For a terminating computation that distinction collapses, which is why Book I
never has to make it.

## The part that does not transfer at all

Book I does not merely *bound* memory. It **refuses** an action it cannot afford,
checked before the action is taken. That discipline needs a total order on
actions and a counter read before each one.

With `k` interactions firing in one parallel step, deciding which are affordable
requires a shared counter and an order among the `k` — precisely the
serialisation interaction nets exist to avoid. And the transient is real, not
bookkeeping: measured inside a parallel step, where an implementation allocates
before it frees, the peak exceeded the step boundary on **14 of 29** nets, by up
to **2,268 agents**. A parallel machine must therefore either prepay the
worst-case transient or serialise the budget check. Neither is free, and this
experiment does not know which is cheaper.

**So the honest split is: the theorem transfers, the enforcement does not.** That
is a sharper statement than either outcome the preregistration anticipated.

## What this says about interaction counts as a cost model

An interaction count cannot price memory. It is invariant across schedules whose
peaks differ by up to 1.5× when they terminate and by three orders of magnitude
when they do not. Any cost model that reports interactions alone is reporting the
half of the pair that does not vary.

That is a claim about counting, **not about HVM**, whose implementation was not
measured, read, or run here. Nothing in this document is evidence about any
existing runtime.

## What else this cannot say

- The schedules are greedy, not optimal, so every spread reported is a **lower
  bound** on the true spread between the best and worst schedule.
- Memory is counted in agents. Counting wires too would scale the same quantity,
  since an interaction changes the wire count by a bounded amount as well.
- No λ-calculus encoding was measured. Nothing here is about λ-terms, real
  programs, or sharing as an optimisation — only about nets.
- Eight nets did not normalise within the caps. Whether they normalise at all was
  not determined and is not claimed either way.

## Controls

`measure.py` fails rather than reports if any schedule disagrees with another on
the interaction count, the multiset of rules, or the normal form; if any peak
exceeds `initial + 2 × interactions`; or if any spread exceeds what reordering
permits. All pass.

`selftest.py` breaks each of those controls in turn — a rule that allocates a
fifth agent, a schedule that leaves a redex unreduced, a price that under-reports
growth — and requires each one to fail **for its own reason**. A control that
cannot be made to fail is not a control, and a perturbation that breaks
everything attributes nothing.

| Date | Change | Result already known? |
| --- | --- | --- |
| 2026-08-23 | initial preregistration | no |
| 2026-08-23 | result recorded; no hypothesis, threshold or net was edited | — |
