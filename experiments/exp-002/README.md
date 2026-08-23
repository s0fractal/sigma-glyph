# EXP-002 fixtures — frozen before either implementation

These are the raw byte strings both sides of the bake-off will be given, and the
verdict each one deserves. They are frozen now, ahead of any Σ-GLYPH or WASM
code, so that neither implementation can be written against a target that moves.

```sh
python3 experiments/exp-002/validate_fixtures.py
```

## What the validator is, and what it is not

`validate_fixtures.py` is a **neutral reading of the contract**, not a
contestant. It imports neither implementation, will not be timed, and is not
part of the measurement. Its only job is to decide, independently of both sides,
what each byte string deserves — so that a fixture whose author was mistaken is
caught before anyone builds against it.

It decides canonicality the one way that needs no rule per defect: parse
strictly, re-serialise in canonical form, and require the result to equal the
input byte for byte. Duplicate members, leading zeros, stray whitespace,
unnecessary escapes and unsorted members all fall out of that single test rather
than out of a list somebody has to keep complete.

It also refuses a fixture whose bytes have changed since they were frozen, and a
composition that no longer matches what the preregistration promised.

## The composition

| Group | Count | What it covers |
| --- | --- | --- |
| positive | 12 | six `ACCEPT` and six `REJECT`, including both sides of the limit and a currency that differs only in case |
| negative | 18 | one per rejection cause named in the preregistration, plus type, size and shape violations |
| adversarial | 4 | deepest allowed nesting, largest allowed record, a duplicate member at the end of a long record, and an integer exactly at +2⁵³ |

Verdict counts cut across those groups: 9 `ACCEPT`, 6 `REJECT`, 19 `MALFORMED`.

## The rules that apply from here

A fixture may be **added** to both sides at once, with a change-log entry in the
preregistration. None may be **removed**, and none may be edited: the manifest
records each file's SHA-256, and the validator fails if the bytes move.

`MALFORMED` is a verdict, not an error channel. A run that crashes, hangs, or
exits without one of the three verdicts has failed that vector.
