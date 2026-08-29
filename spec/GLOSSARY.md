# One thing, one name

*Non-normative. Book I governs; this page exists because the same quantity has
been called three things in three documents, and a reader could not tell whether
they were the same.*

## The measured quantity

**Size** — the hash-leaf measure of §3.4: every materialized node counts 1, an
unresolved hash counts exactly 1 whatever it denotes, a materialized `REF` counts
2, and `size(APPLY) = 1 + size(left) + size(right)`. It is a property of the term
the machine is holding, not of any process.

**ATP** — the single unsigned integer that prices actions. One action is a rule
firing or one node materialization; §3.4 gives the price of each.

**The theorem** — `size ≤ spent + 1` at every configuration, mechanized as
`EvalMachine.evalHash_size_bound`. Both sides are semantic: a count of nodes
against a count of paid actions.

## What the words mean, and what they do not

| Word | Means here | Does **not** mean |
| --- | --- | --- |
| **work** | priced semantic actions | host instructions, spine traversals, hashing, store lookups, cache behaviour |
| **memory** | `size`, the materialized-node count | heap bytes, RSS, evaluator stack, temporary old-and-new terms during a rewrite, GC, SHA buffers, store index, allocator fragmentation |
| **materialization** | turning one unresolved hash into a node | fetching a blob; §1.1 keeps blob retrieval outside the Book entirely |

The paper's title says "work and memory". Read against this table it is a claim
about **semantic** reduction cost and **semantic** peak materialization, and the
gap between that and a process's actual resource use is a refinement layer nobody
here has proved:

```
ATP
 ↓  theorem (mechanized)
semantic work / materialized size
 ↓  NOT PROVEN — representation, stack, GC, allocator, store index
runtime operations / heap / RSS
```

Naming that gap is not a retreat. A bound on semantic materialization is what
makes a stranger's computation *bounded*; what makes it *affordable* on a given
machine is a separate question, and `SECURITY-ASSUMPTIONS.md` SA-11 is where the
admission side of it lives.

## Three inputs, not two

`eval` takes a term hash, a budget **and a store**. An absent hash is a canonical
outcome (§3.5), so availability is inside the semantics. `EvalMachine.evalHash_stable`
bounds how far that reaches: extending a store can change **only** an `Unresolved`
answer, never a normal form and never an exhaustion. See
[`IMPLEMENTING.md`](IMPLEMENTING.md).

## Exit and result are different things

`result_hash` is the NodeHash of the term the machine returns. It does not say
which of the three exits occurred, because `DISSONANCE(ATP Exhausted)` is an
ordinary term: it can sit in a store and evaluate to a normal form, so one hash
can mean "finished" or "ran out". A caller that must tell them apart needs the
exit alongside the hash.
