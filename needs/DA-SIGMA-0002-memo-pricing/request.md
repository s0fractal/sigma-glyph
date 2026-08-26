# DA-SIGMA-0002: may a conforming implementation reuse a result it has already paid for?

**The answer is yes, and Book I already says so.** This packet asked the question
without having found the sentence that settles it. What follows is the corrected
record: the case that prompted it, the answer §3.4 gives, and the decision that
turns out to be ALife-side rather than Σ-GLYPH's.

It is filed as a record of demand and routing. It proposes no specification text
and asks for no change.

## Correction, 2026-08-26 — the premise was wrong

The filed version said: *"Book I's text never mentions memoization. The
prohibition is a side effect of pinning spend, not a decision recorded anywhere."*

That is false. Book I §3.4 ends with:

> «Нормативна модель обліку — tree semantics над матеріалізованим графом:
> **шаринг MAY застосовуватись у виконанні, але звітований ATP MUST збігатися з
> tree-обліком**.»

Sharing **MAY** be used in execution; the *reported* ATP **MUST** match tree
accounting. A conforming implementation may therefore already take a result from
a memo and skip the work — it must simply report the canonical price. The
capability this packet asked for exists, and the contract is one sentence long.

The reproducer's R1 was read as *"Book I never reuses a result"*. It shows only
that the **accounting** is identical on a second evaluation, which is a different
claim, and the one §3.4 requires.

Found by an external review (Codex) of the filed packet, verified against the
spec at the pinned revision, and corrected here rather than quietly. Two further
errors it found are corrected below.

## What was actually blocked, restated

The ALife substrate wanted an agent to buy a normal form somebody else had
already derived, and to have that **cost less ATP** — because in a population,
what an agent can afford decides whether it settles at all.

§3.4 permits the *reuse* and fixes the *price*. So the substrate can skip the
work and must still report the tree figure. What it cannot do is call its cheaper
number `atp_spent` and stay conforming — and it should not want to: that number
is a **metabolic accounting of its own**, and naming it after Σ-GLYPH's would
make two incomparable quantities share a word.

That is an application-side decision, and the packet's own counterexample clause
anticipated this outcome: *"If Book I already fixes that atp_spent is exactly
determined, this closes as an existing contract."*

## Evidence and reproducer

```
python3 needs/DA-SIGMA-0002-memo-pricing/fixtures/reproduce.py
```

Eight SKI terms; Book I and nothing else. The script **refuses to run** against an
oracle whose SHA-256 is not the `413d1f98…` this packet pins, and its verdict is
pinned to ten exact values — both corrections from the same review, and both
demonstrable:

- mutating the `max(1, size(nf)−1)` arm so that it contradicts the packet now
  prints `NOT REPRODUCED (9/10)` and exits 1. The filed version printed
  `REPRODUCED` and exited 0;
- appending one comment to the oracle now aborts with both digests. The filed
  version loaded whatever it found and reported success.

What it measures:

- **R1** the same hash evaluated twice costs the same both times (12/12, 15/15,
  13/13, 16/16) — the *accounting*, not the work;
- **R2** a run charging `size(nf)` for an installed normal form reaches every
  oracle answer for 97 ATP against 185, with worst `size − (spent+1)` exactly 0;
- **R3** the bound under four prices: `size(nf)` 0/8 violations,
  `max(1, size(nf)−1)` 0/8, `max(1, size(nf)−2)` 4/8, flat 1 4/8 with worst
  excess +9;
- **R4** that accounting reports a different `atp_spent` on 8 of 8 terms — which
  is precisely why §3.4 requires the tree figure instead.

### The floor is `max(1, k − 1)`, not `k − 1`

The filed version said the theorem's floor is `size(nf) − 1`. **Four of the eight
fixture normal forms have size 1**, where that is zero — and §3.4 fixes the
minimum price of any action at 1. The floor is `max(1, k − 1)`; `k` is what
additionally preserves the per-row discipline (`Δsize ≤ cost − 1`) that every row
of §3.4 satisfies, with equality. For an ALife action, `k` is the cleaner choice
for exactly that reason, and it is an ALife choice.

### The `warrant` claim was too large

The filed version said every consumer that re-runs a budgeted check inherits the
split, "warrant's `ski@v1` re-runs compare the hash *and* the budget". They do
not. SPEC §3.1 step 3: *"pass iff the result's NodeHash equals `expect`"*; `atp`
is the pinned **input** budget and `atp_spent` is not compared. At the fixture's
budget the oracle and a memoizing run return the same hash, so no verdict
diverges. Divergence needs a budget boundary — where a different accounting has
already changed Book I semantics, which §3.4 forbids reporting as Book I.

## Non-claims

- Merging this records demand and routing only. It adopts nothing.
- The source case's own hypotheses are not established: ALIFE-EXP-002's H1 and H3
  both fail against their preregistered criteria, and nothing here depends on
  them.
- The ATP figures describe the reference Python evaluator at the pinned revision.
- The source repository claims no standing in Σ-GLYPH governance, and does not
  classify this packet. `disposition.json` remains the owner's to write.
