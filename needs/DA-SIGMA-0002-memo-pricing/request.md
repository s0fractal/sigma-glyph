# DA-SIGMA-0002: may a conforming implementation reuse a result it has already paid for — and at what price?

This is a case-derived demand packet. It is not a protocol proposal, a finding of
wrongdoing, or evidence that Σ-GLYPH has accepted a change. It asks for a
statement, and — only if that statement is "yes" — for a number that is already
derivable from Book I's own text.

## Blocked operation

Publish an implementation that answers a repeated Σ-GLYPH check without paying
for it twice, and still call it conforming.

Book I charges every agent for every materialization, and the conformance vectors
pin `atp_spent` exactly for each `(term, budget)`. An implementation that reuses a
normal form it already holds therefore reports a different spend and fails
conformance. On the packet's eight-term fixture the divergence is total: 12 ATP
against 1, 15 against 5, 8 of 8 terms.

Book I's text never mentions memoization. The prohibition is a **side effect of
pinning spend**, not a decision recorded anywhere — which is why this arrives as a
question rather than as a complaint.

## Evidence and reproducer

The fixture is eight SKI terms: four base terms and four composites built to
**demand** the base terms by hash, because that demand path is what a memo
answers. Everything else about the source case — populations, generations, an
ATP economy, hypotheses — is omitted; none of it is needed.

```
python3 needs/DA-SIGMA-0002-memo-pricing/fixtures/reproduce.py
```

- **R1** — the same hash, evaluated twice, costs the same both times (12/12,
  15/15, 13/13, 16/16). Book I never reuses a result.
- **R2** — a memo of normal forms priced at `size(nf)` reaches every oracle answer
  for 97 ATP against 185 (52.4%), with `size − (spent + 1)` at worst exactly **0**:
  the §3.4 bound holds, and holds tightly.
- **R3** — the same memo priced at 1 violates `size ≤ spent + 1` on 4 of 8 terms,
  worst excess +9.
- **R4** — the memoizing run and the oracle disagree about `atp_spent` on 8 of 8
  terms. That is the collision.

## Capability boundary

The capability asked for is a **position**, not an implementation: may a
conforming implementation reuse a normal form it holds for a demanded hash?

If the answer is no, say so in Book I, because at present the answer lives only in
the vectors and an implementer can reasonably read the specification and conclude
otherwise.

If the answer is yes, the price is not free either — but it is a **fork between
two numbers that differ by one**, and choosing between them is a decision only
Book I's owners can make.

Installing a normal form of size `k` where a thunk of size 1 stood grows the term
by `k − 1`. So:

- **`k − 1`** is the floor for the *theorem*. `size ≤ spent + 1` needs only
  `Δsize ≤ Δcost`, and R3 measures exactly that: sound at `k − 1`, broken at
  `k − 2`.
- **`k`** is the floor for the *discipline*. Every row of §3.4 satisfies the
  stronger `Δsize ≤ cost − 1` — an action costs more than it adds — and a memo
  install keeps that exactly when the price is at least `k`, with equality at `k`.

Whichever is chosen, two implementations that both memoize agree on `atp_spent`
only if they charge the same thing, which is why this needs a decision rather
than an implementation. The source repository implements `k`, on the grounds that
an action which merely fails to break the theorem is not the same as one that
behaves like every other action of the machine — but that reasoning belongs to
whoever owns §3.4.

*(This paragraph replaces one that claimed `k` was forced. It was off by one: the
claim was generalized from a measurement at a flat price of 1 without checking
the boundary, and the boundary is at `k − 1`. Correcting it before filing is the
reason a packet is written down before it is sent.)*

> In a size-priced machine, memoization can refund time and never space.

**Current workaround:** the ALife substrate memoizes strictly outside conformance
— off by default, priced at `size(nf)`, with every receipt recording that a memo
was used and the SHA-256 of the oracle beside it.

**Why it is insufficient:** the numbers it produces are not Σ-GLYPH numbers. An
ATP figure from a memoizing run cannot be compared with a Book I figure, cited in
a receipt someone will re-run, or replayed by a conforming implementation. Every
consumer that re-runs a budgeted check inherits the same split — `warrant`'s
`ski@v1` re-runs compare the hash *and* the budget.

**Counterexample that closes or reroutes this:** if Book I already fixes that
`atp_spent` is exactly determined and reuse is forbidden by design, this closes as
an existing contract and the substrate keeps its memo outside conformance
permanently. If any published ADR, profile or vector already prices reuse, it
closes as already-supported. The request survives only if the answer turns out to
be "nobody decided".

## Non-claims

- Filing this does not establish the source case's hypotheses. **ALIFE-EXP-002's
  H1 and H3 both FAIL against their preregistered criteria**, and nothing in this
  packet depends on them — the collision is arithmetic about ATP, not a result
  about artificial life.
- Merging this packet records demand and routing only. It adopts no protocol
  change, no memo action, and no price.
- The ATP figures describe the reference Python evaluator at the pinned target
  revision. They are not properties of the specification.
- The source repository claims no standing in Σ-GLYPH governance and proposes no
  specification text.
