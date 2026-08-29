# Why determinism, content addressing, and a proven bound — and why all three

Σ-GLYPH has three properties that look like separate engineering choices and are
not. This file records what they are jointly for, because the answer is not
visible from any one of them and has never been written down in one place.

## The target

**Accept a change from anyone, judged only by the proof attached to it.**

Not by who sent it. Not by their standing in the system. By a proof the receiver
**executes itself** — not reads, not trusts because an authority signed it.

That target is what makes the three properties non-negotiable, because executing
a stranger's proof means executing a stranger's code, and that fails in three
separate ways:

| failure | what stops it |
|---|---|
| the proof lies about its result | **determinism** — the same term reduces to the same value for everyone, so a result is a claim anyone can recheck rather than a report about the sender's machine |
| "the same proof" is a promise, not a fact | **content addressing** — a proof is named by the hash of its own bytes, so *identity* is checkable instead of asserted |
| the proof never halts, or grows the semantic term without bound | **a single integer bounding work AND semantic materialization, proven in Lean** |

Drop any one and the target collapses. Determinism without a bound is a halting
problem with extra steps. A bound without determinism bounds the wrong thing.
Both without content addressing means you cannot say which proof you ran.

## The third one is the load-bearing one, and it is the least obvious

A proven joint semantic bound, combined with a receiver-chosen admission cap, is
what lets a receiver say to an unknown sender:

> send me a computation; I will spend at most this much on it and not one step
> more

and have the reduction bound be a **theorem** rather than a timeout or promise.
The decision to accept that amount remains local policy.

A timeout is a policy: it can be misconfigured, raced, or disabled, and it tells
you nothing before you start. `Σ-GLYPH`'s bound is a property of the evaluator
under the admitted budget, known before execution and machine-checked. Without
it, "we accept computations from anyone" is an open denial-of-service with a
nice name.

This is why the Lean development covers **work and semantic materialized size
together in one integer** rather than either alone. It does not prove a bound on
RSS, stack, allocator overhead, store indexes or hashing buffers; those remain an
implementation and deployment obligation.

## Where warrant fits

`warrant` is the envelope: who decided, under which policy, for what reason, and
whether that reason still holds. Threshold signatures are how the zone widens —
to change the rules you must gather a quorum **under the current rules**.

Σ-GLYPH is what makes a `because` mean something. A reason that re-executes is
only useful if re-executing it is safe, deterministic, and cheap to bound — which
is the paragraph above.

## The circularity this is designed to break

"Agents build an ecosystem and prove it" hides a question: prove it *to whom*?

If to other agents under the same rules, the circle is closed and establishes
nothing outside itself — the same way three implementations agreeing byte-exact
establish only that one process reached one conclusion three times. This
repository says that about its own implementations elsewhere and means it.

The circle is broken by **an arbiter that is not a participant**: the Lean
kernel, a deterministic evaluator with a proven bound, RFC 8785 as an externally
fixed function. Not an authority — something that can be re-executed to the same
answer by someone who trusts none of the parties.

**That is what "transparent and verifiable rules" has to mean. Not that the rules
are published. That the arbiter belongs to none of the parties it judges.**

## What this does not yet reach, stated plainly

The envelope is nearly finished. The engine is proven. **The language reasons are
written in is tiny.**

WPL today expresses fact declarations plus one boolean expression: comparisons,
`in`, `&&`, `||`, `!`. Enough for "two of three signed" and "this hash is in that
list". Not enough for almost any claim worth accepting a change from a stranger
over.

So the boundary of what an autonomous builder can be trusted with is **the
boundary of what can carry a machine-checkable proof** — not the boundary of what
a model can do. Today that boundary sits at roughly:

- bytes hash to X — trivial
- a threshold is satisfied — mechanical
- a Lean theorem holds — by the kernel
- a deterministic check passed inside its budget — by re-execution
- a test passed — only if deterministic and sandboxed
- a change preserves behaviour — only against a specification you must also trust
- a design is good — no

Widening that list without losing determinism or the proven bound is the real
next problem in this direction. Every new construct either preserves both or
quietly breaks them, and quietly is the dangerous word.

## Honest limits on the whole idea

This describes a world in which no human is in the loop. Three independent
sources examined in 2026-08 all assume the opposite, and are coherent because of
it: an agent-orchestration system whose own guidance says releasing is "an
operator-only action performed by a human outside the task loop"; a survey of 128
publications whose threat model is an honest researcher's sloppiness and whose
conclusion asks for "meaningful human oversight"; and an audit arguing existing
telemetry plus a transparency log already satisfies enterprise requirements.

Their shared unstated premise is that **a human is a free verifier**. While that
holds, the machinery here is overhead. This file describes what the design is
for, not evidence that anyone needs it — and the most likely failure of this
project remains that the cryptography is right and nobody needed it. See
`SECURITY-ASSUMPTIONS.md` for what is actually established, which is much less.
