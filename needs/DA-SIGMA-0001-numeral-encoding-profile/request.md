# DA-SIGMA-0001: a named encoding profile for integer-valued comparisons

This is a case-derived demand packet from
[Decision Archaeology](https://github.com/s0fractal/decision-archaeology). It is
not a protocol proposal, not a finding about anyone's conduct, and not evidence
that this repository has accepted anything. Merging it records that the demand
exists and where it was routed.

## Blocked operation

A public investigation case needs to publish one arithmetic check —
`178530840.00 + 157960871.70 == 336491711.70` over two public procurement
records — as a Σ-GLYPH term, so that a reader who trusts neither the
investigator nor their code can re-execute the check and get the same verdict.

The check runs today. What does not work is the part Σ-GLYPH exists for: a
second party, encoding the same claim independently, does not arrive at the same
`term_hash`. §6 fixes how a lambda term becomes SKI; nothing fixes how a decimal
amount becomes a lambda term. §6 says so plainly — other frontend profiles MAY
exist outside the standard as ordinary SKI citizens with no special status.
For a compiler frontend that is the right answer. For a *claim* that has to
survive being handed to a stranger, it means the hash pins the encoder rather
than the assertion.

## Evidence and reproducer

`fixtures/amounts.json` carries the two amounts and their published sum, and
nothing else from the case. `fixtures/reproduce.py` builds the same claim twice,
from this repository's own `impl/sigma_glyph.py` at the pinned revision:

```
python3 needs/DA-SIGMA-0001-numeral-encoding-profile/fixtures/reproduce.py
```

- positional, 36-bit, LSB-first ripple-carry over C1-compiled booleans:
  **61,479 ATP**, verdict TRUE, term `025e3c7632c63385…`;
- the same term with the sum altered by one minor unit: **not TRUE** — the check
  is falsifiable, not decorative;
- the same claim as Church numerals: **~61 ATP per unit of magnitude**, i.e.
  ~2.05×10¹² ATP for these amounts — expressible, but not runnable by a stranger
  on a laptop, which is the same as not being checkable.

That contrast is the reason this packet asks about encoding rather than about
arithmetic. The kernel is sufficient. The agreement is missing.

## Capability boundary

The request is for a capability, not an implementation: a named, versioned
encoding profile for integer-valued comparisons — minor-unit scaling, fixed
width, bit order, and the boolean normal form a verdict reduces to — such that
two parties who share no code produce the same term bytes for the same claim.
The adder in `fixtures/` is evidence that the need is real, and is deliberately
not offered as the answer.

The counterexample that closes this: if such an encoding is already published
here, or if the owner holds that encoding conventions are application-side by
design, then Decision Archaeology publishes its own profile and this request is
`already-supported` or `application-adapter` — not a protocol change.

## Owner disposition

Owner-side replay at the pinned evaluator revision reproduced the exact term,
ATP cost, and both negative counterexamples. The request is classified
`application-adapter`: Book I §6 already defines the ownership boundary by
placing non-C1 frontend profiles outside the standard. Decision Archaeology is
therefore the canonical owner of the narrow encoding needed by its case. This
classification records routing only; it does not adopt that encoding here.

## Non-claims

- Nothing here asserts that the procurement case's hypothesis is true.
- The ATP figures describe the reference Python evaluator at the pinned
  revision; they are not a property of the specification.
- No adoption, review, or roster authority is claimed by this packet or by the
  branch that carries it.
