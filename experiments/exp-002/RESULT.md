# EXP-002 — result

Both sides, at their exact revisions, judged against the kill criteria fixed in
[`EXP-002-wasm-bakeoff-preregistration.md`](../EXP-002-wasm-bakeoff-preregistration.md)
before either existed. No threshold was edited after a number was known.

| | |
| --- | --- |
| fixtures | frozen at `9f0c990`, 34 vectors, unchanged since |
| WASM side | `9e8e47d` |
| Σ-GLYPH side | `c839766` |
| host | Apple M4 Pro, macOS, Python 3.13.15, Wasmtime 48.0.0, rustc 1.88.0 |

## The short version

The WASM side answers all thirty-four vectors, deterministically, inside its
budgets. The Σ-GLYPH side was never implemented, and stopped for a reason that no
amount of implementation would have changed: **there is no published way to turn
raw bytes into a term.** `eval` takes a term hash and a budget and no input; a
`LITERAL` commits a blob whose contents ADR-004 requires to be invisible to
reduction; C1 fixes λ→SKI and nothing about data.

So the two sides were never given the same input interface, and the honest
statement of the result is about that, not about a speed ratio.

## K1 — triggered, on its first clause

> *Σ-GLYPH cannot express the task under the published profile, or needs more
> than 50,000,000 ATP on any single vector → Σ-GLYPH is not a general default
> runtime for this class of check.*

**Triggered at the interface.** The task cannot be instantiated from the
preregistered raw-byte interface under the published profile without inventing a
frontend encoding, which §8 forbids. The preregistered consequence follows:
Σ-GLYPH is not a general default runtime for this class of check.

Three things this does **not** say, each of which the evidence forbids:

- not "SKI cannot parse JSON" — nothing here tests that, and the first
  measurement that seemed to show a wall turned out to be measuring the shape of
  the term I had chosen;
- not that the ATP ceiling was hit — no vector was ever run, because none could
  be constructed;
- not that this is a defect. It is a boundary of the published profile, and the
  same boundary `DA-SIGMA-0001` reached from the application side.

## K2, K3, K6 — not evaluable

Wall time, artifact size and authoring-effort ratio all compare two
implementations. There is one. Recording them as "Σ-GLYPH lost" would be
measuring an absence.

For the record, both clocks: the WASM side took **3 minutes 18 seconds** of agent
wall-clock for the implementation plus two review-driven correction rounds; the
Σ-GLYPH side took **about fifteen minutes** to reach the interface finding, of
which the floor measurements were most of it. Neither number is a human working
day, and they are not comparable to the three-day budget the preregistration
allows.

## K4 — not triggered

> *If WASM fails byte-identical determinism or exceeds its declared memory bound,
> it is not called a drop-in replacement.*

Five runs per vector in-process — **all five compared** as (verdict, fuel,
pages), not merely the last one kept — plus all thirty-four replayed in a freshly
started process with every id and verdict compared: identical throughout. Peak
linear memory 17 pages against a 2 MiB limiter. The condition did not fire, and
the phrase it guards is still not used: nothing here makes WASM a drop-in
replacement for anything, because the other side has no implementation to replace.

## K5 — passed by WASM, not evaluated for Σ-GLYPH

Both controls refuse and both are gates that exit non-zero:

- a corrupted artifact is rejected **before execution**, under the digest the
  verifier was given: `REFUSED before execution: artifact is da76bd4e…, expected
  e16eaa31…`;
- a zero fuel budget traps instead of answering.

Σ-GLYPH ran no controls because it ran nothing.

## The numbers the WASM side does have

Read from `wasm/results.json` as frozen at `9e8e47d`, which is the authoritative
receipt for this side. The prose in both write-ups was corrected to match it
after the freeze; the receipt itself was not re-run or rewritten.

| Measure | Value |
| --- | --- |
| vectors agreeing with the frozen verdicts | 34 / 34 |
| fuel | min 16,489 · median 21,401 · max 247,886 |
| per-vector median wall time | 10.458 µs, slowest vector 23.208 µs |
| per-vector IQR | median 0.708 µs |
| peak linear memory | 17 pages = 1,088 KiB (limiter 2,048 KiB) |
| cold start, fresh process | 15.576 ms including importing the runtime |
| OS peak RSS, fresh process | 37,440 KiB — the Python and Wasmtime process, not the module |
| artifact | 4,190 bytes, `sha256 e16eaa31e4bb0670…` |

## Metrics 9–12, which are the interesting ones

**Trusted computing base, split in two because it is two questions.**

*To re-execute the artifact*: Wasmtime's compiler and runtime, the Python harness
and profile loader, the digest implementation, and the host. The Rust toolchain
is **not** in this set — with a pinned digest, a verifier who re-runs the
committed `.wasm` never has to trust the compiler that produced it.

*To believe the artifact corresponds to its source*: rustc 1.88.0, Cargo and the
lockfile. That trust is only needed by someone who wants the source to mean
something, and it is a different question from whether the verdict is
reproducible.

Σ-GLYPH's execution base would be a small evaluator whose bound is a Lean
theorem, and it has nothing to rest on here, because the input never becomes a
term.

**Content addressing, and the asymmetry that nearly went unnoticed.** The first
version of this experiment handed corrupted bytes straight to Wasmtime, found no
detection, and wrote that up as a property of WASM. That was wrong: a Σ-GLYPH
term hash is not inside its own bytes either, and a verifier is told it out of
band. Once the WASM profile pins and checks a digest, the control passes on both
sides in principle. The difference that survives is **where the check lives** —
normative in Book I versus a wrapper this experiment wrote — and that is a real
difference in what an implementer has to get right, not a difference in what the
formats can do.

**Independent reconstruction.** The WASM artifact is a committed 4,190-byte file
with a pinned digest, a lockfile and a build recipe; a second implementer
reproduces it or refuses. A Σ-GLYPH artifact for this task cannot be reconstructed
by anyone, because the encoding that would produce it is not published — which is
the finding, stated as a metric.

**Special assumptions.** WASM needed four beyond the runtime: the digest wrapper,
a fuel budget, a memory limiter, and a declared subset with SIMD, threads and
reference types disabled. Σ-GLYPH needed one it could not have: a byte encoding.

## What follows, and what does not

The preregistered consequence of K1 stands: not a general default runtime for
this class of check. Whether that changes Σ-GLYPH's standing in the ecosystem is
an owner decision at the campaign's decision date, not a conclusion this document
may draw.

A byte or profile encoding is not a repair to be slipped into this experiment. It
belongs in EXP-003 with its own preregistration, or in an owner disposition on
`DA-SIGMA-0001`, which named the same gap first and from the other direction: the
kernel computes, and nothing published says how outside data becomes a
computation.

Recorded regardless of outcome, as promised, and prepared for publication as a
single result rather than as a partial one — the preregistration forbids
reporting one side while the other is still running. The side that did not run is
the one that produced the finding.
