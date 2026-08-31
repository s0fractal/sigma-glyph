# EXP-ADR011-01: a mechanical admission for computed Church naturals

**Status:** PRE-REGISTERED. Not started. No result may be cited from this
document until it carries one.

Pre-registered because ADR-011 is blocked on exactly this and the temptation is
to close the gap with a syntactic heuristic. Writing the hypothesis, the design
and the falsifiers down *before* measuring is the only thing that stops the
experiment from being shaped by what it finds.

## Why

`sigma-glyph/adr-011/church@v0` admits Church numerals **written out** and
refuses computed expressions. It therefore cannot settle `7+5=12`, the case that
motivated ADR-011 and the one measured at 601 ATP by
`manifesto/tools/glyphlib.py`. That harness admitted any lambda expression, which
is why it could run the case and why its result carries no domain argument.

## Hypothesis

There is a closed grammar over Church naturals whose every expression can be
shown, by structural induction, to observe to the constructor spine `Fⁿ(X)` —
making reflection and preservation arguable for computed expressions and not
only for literals.

    ChurchNatExpr := Numeral(k)
                   | Plus(ChurchNatExpr, ChurchNatExpr)
                   | Mult(ChurchNatExpr, ChurchNatExpr)

## What must be established, in order

1. **Pinned encodings.** Exact λ-terms for `Plus` and `Mult`, compiled by C1,
   with their NodeHashes recorded. An encoding that is merely "the usual one" is
   not pinned.
2. **Closure.** By induction over the grammar: if every leaf denotes a natural,
   every expression denotes a natural, and its observation reduces to `Fⁿ(X)`
   for that natural. The induction must name where it uses C1's correctness,
   which is itself assumed rather than mechanized.
3. **A decision procedure** that accepts exactly this grammar and rejects
   everything else, including terms that happen to denote naturals but are not
   built by it. **Both directions are failures of THIS experiment**, and the
   asymmetry between them is only in what they endanger:
   - **over-acceptance** admits a term the closure argument does not cover →
     unsound, and the experiment fails;
   - **under-acceptance** of an in-grammar expression → the implementation does
     not decide the domain it pre-registered, and the experiment fails as
     pre-registered even though nothing unsound shipped.

   Narrowing the grammar to fit a procedure that turned out to be weaker
   requires a **visible amendment to this file, or a new experiment** — not a
   reinterpretation after the results are known.
4. **Budget.** Whether the observation of an expression is affordable is a
   separate question from whether it is admissible, and the two must not be
   conflated: an admitted expression that exhausts is `UNSETTLED`, not
   inadmissible.

## Falsifiers, stated before measuring

- An expression in the grammar whose observation is not `Fⁿ(X)` → the closure
  argument is wrong and the grammar is not a domain.
- The decision procedure admitting a term outside the grammar → it is a
  heuristic, and this experiment has reproduced the error it exists to avoid.
- **The practical motivation fails**, decided mechanically on fixtures and a
  threshold chosen HERE, before measuring:

  ```text
  fixtures:  3+2=5, 5+5=10, 7+5=12
  cap:       50 000 ATP per side for the address route
  ratio:     total address-route ATP must be at most 1/100 of the in-language
             EQN total on the two fixtures where EQN terminates
             (EQN: 3+2=5 -> 260 780 ATP;  5+5=10 -> 26 212 480 ATP)

  fail if:   7+5=12 does not settle within the cap, OR
             either terminating fixture comes in above 1/100 of its EQN cost
  ```

  The ratio is 100×, written down now. State the standing of that number
  precisely, because it is **informed** preregistration, not blind: the EQN
  figures above and the church@v0 measurements already existed when it was
  chosen.

  > Threshold chosen after observing the related historical measurements, but
  > before implementing or measuring EXP-ADR011-01; its purpose is to prevent
  > adjustment after this experiment's results.

  So it does not protect against a threshold fitted to the prior harness. It
  protects against the one failure this experiment can still commit: moving the
  line once these results are in.

## What this experiment will NOT establish

- Admission of arbitrary SKI terms, or of any Church-natural expression outside
  the grammar.
- Anything about higher-order terms.
- A complexity bound; costs will be measured on fixtures and reported as
  measurements.

## Scope

Non-normative. Touches no anchored byte. If it succeeds it extends ADR-011's
profile with a second admitted domain; if it fails, ADR-011 stays a profile for
written-out numerals and says so.
