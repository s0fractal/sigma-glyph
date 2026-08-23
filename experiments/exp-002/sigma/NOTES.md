# Σ-GLYPH side — working notes and outcome

Kept as the preregistration requires: every construction, including the ones that
failed, and what each measurement actually shows.

## 1. The question asked before writing a parser

The largest record the contract allows is 4 KiB. If merely *walking* that many
inputs costs more than K1's 50,000,000 ATP, the answer is decided and no amount
of parser construction changes it. So the floor was measured first.

## 2. A chain is quadratic

Two encodings of the input as a linked structure, walked with a step that reads
one bit and ANDs it into a boolean:

| leaves | right fold | CPS fold |
| --- | --- | --- |
| 4 | 3,333 | 2,673 |
| 16 | 58,711 | 53,319 |
| 64 | 2,559,743 | 2,371,263 |

Per-leaf cost grows with the length already consumed — 833 ATP at four, 39,995 at
sixty-four.

`probe_cost.py` is a third shape, an eight-bit byte encoding walked with a
bounded accumulator, and reproduces from the committed file:

| bytes | ATP | per byte |
| --- | --- | --- |
| 4 | 3,370 | 842 |
| 16 | 52,710 | 3,294 |
| 32 | 316,862 | 9,901 |

Same shape again. **A disclosure about provenance**: an earlier variant of that
same file used a Church-numeral accumulator and cost 4.6M ATP at 32 bytes,
because the accumulator's own term grows as it is built. It was overwritten in
place during exploration rather than kept as a separate file, so that figure is
quoted from the run and is *not* reproducible from anything committed here. The
lesson it carried survived: a fold's accumulator must be bounded, and even
bounded it does not change the quadratic shape.

## 3. The shape was mine, not the evaluator's

A balanced tree with an associative combiner over the same leaves:

| leaves | ATP | per leaf |
| --- | --- | --- |
| 4 | 281 | 70 |
| 32 | 2,717 | 84 |
| 256 | 22,205 | 86 |

**Linear, at ≈86 ATP per Church-boolean leaf**, flat from sixteen upward.

That figure is exactly what it says and no more. **A leaf here is one constant
Church boolean, not a byte.** These probes never encoded a byte: both the chain
and the tree fed identical `TRUE` leaves, and the chain step read `value & 1`. A
byte needs at least eight bits plus a decoder, so any per-byte number is at least
an order of magnitude above this and has not been measured. The earlier draft of
this file extrapolated "≈86 ATP/byte" and "≈352k ATP for 4 KiB"; both are
withdrawn as unsupported.

What the probes do establish is worth keeping: the quadratic came from re-forcing
a structure as deep as the input. Every materialisation is priced and no result
is shared, so a chain is re-walked at each step and a tree of depth `log₂ n` is
not. That is a real and reusable fact about writing terms for this evaluator.

## 4. Admissibility check, which is where this stops

Before building transition tables, one question had to be answered: **which
published encoding turns raw fixture bytes into a term?** The preregistration
forbids inventing one for the benchmark, and two independent implementers must be
able to produce byte-identical artifacts from what is published.

The published surface answers it plainly:

- `eval(term_hash, atp)` (Book I §6) takes **no input**. Whatever is to be
  computed over must already be inside the term.
- A `LITERAL`'s atom is `SHA-256(DataBLOB)`, and ADR-004 states that the absence,
  availability or corruption of the external blob **must not** change the result
  hash, the failure kind or the ATP spent. Blob contents are deliberately
  invisible to reduction, so bytes cannot enter a computation that way.
- Profile C1 fixes λ→SKI compilation and nothing about data. Book I §6 says other
  frontend profiles may exist outside the standard, as ordinary SKI citizens with
  no special status.

So there is no published byte encoding to reproduce. Choosing one means fixing
bit order, the representation of a byte, whether the sequence is a chain or a
tree, and where application boundaries fall — every one of which changes the term
hash and the ATP. My chain-versus-tree probes are two such choices, and they
differ by two orders of magnitude at sixty-four leaves.

**Outcome: the task cannot be instantiated from the preregistered raw-byte
interface under the published profile without a new frontend encoding.**

## 5. What that is, and what it is not

It is the first clause of **K1**: Σ-GLYPH cannot express this task under the
published profile, so it is not a general default runtime for this class of
check. The trigger is at the interface, not in the mathematics.

It is **not** "SKI cannot parse JSON". Nothing here supports that sentence, and
§3 is the reason the preregistration forbids it: the first measurement suggested
a wall two hundred times over the ceiling, and the wall turned out to be the
shape I had chosen.

It is also not a defect to fix inside this experiment. A new byte or profile
encoding belongs in a separate EXP-003, or in an owner disposition on
`DA-SIGMA-0001` — which named this same gap from the other side: the kernel
computes, and the ecosystem has no shared name for turning outside data into a
computation.

The two sides of this bake-off were therefore never given the same input
interface, and saying so is more useful than a number:

```
WASM   : raw fixture bytes → standard linear memory → the pinned module
Σ-GLYPH: raw fixture bytes → an encoder nobody has published → a term graph → eval
```

That host-side encoder would have been an undeclared part of the contestant,
setting its ATP, its artifact hash and its reproducibility.

## 6. One narrowing, for accuracy

An earlier note said strict member ordering "is not a finite-state property
because keys are unbounded". The contract bounds the whole record to 4 KiB and 16
members, so the state space is finite. The real obstacle is that any summary
sufficient to compare adjacent keys grows with key length, making the state space
astronomically large rather than mathematically infinite. The distinction did not
end up mattering — the interface question stopped the attempt first — but the
weaker claim is the true one.

## One change made after the measurements

The three probes carried identical copies of the same scaffolding — store, compile
through C1, apply, force — which a duplication gate flagged. It is now
`probe_lib.py`, imported by all three. The helpers are the same code they ran
with, and every number in this file was re-produced from the factored versions
before this was written: 316,862 ATP at 32 bytes for `probe_cost`, 2,371,263 at
64 for the CPS chain, 86 ATP per leaf for the tree. Refactoring evidence is worth
saying out loud rather than doing quietly.

## Clock

Started 2026-08-23T13:28:35Z. Floor measurements, the admissibility check and
this write-up: under an hour of agent wall-clock. No transition tables were
built; construction stopped when the interface question was answered.
