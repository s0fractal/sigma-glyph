# SonarCloud findings this repository accepts, and why

*Every entry names the rule, the site, and the reason. A finding that is not here
is not accepted — it is either fixed or it has not been looked at. The README must
not say "Sonar clean" while this file has entries.*

Read with `SECURITY-ASSUMPTIONS.md`: that file records what the system assumes,
this one records what a static analyser reports that we have decided not to change.

## Accepted

### `python:S3776` — cognitive complexity in a frozen reproduction fixture

`needs/DA-SIGMA-0002-memo-pricing/fixtures/reproduce.py`, `run()` and `main()`.

This file is evidence, not a tool. Its worth is that it is the thing that was run
when the packet was measured, and it pins ten values and the SHA-256 of the oracle
it ran against so that a later reader can tell whether they are looking at the
same measurement. Restructuring it for readability would improve nothing anyone
depends on and would make the artifact different from the one the disposition
cites. Suppressed by rule name at the two functions, pointing here.

The same rule **is** fixed wherever it appears in a tool — `spec_audit.py`,
`store_mono_bridge_check.py`, `repo_map.py` — because those are read and changed.

### `pythonsecurity:S8707` — directories created under an operator-supplied root

`examples/two-jurisdictions/demo.py`, three sites.

A demonstration script that builds two throwaway jurisdiction stores under either
a temporary directory or a path the operator passes with `--keep`. The
jurisdiction *name* is already constrained to a lowercase label and the root is
`realpath`-ed before use, so the traversal the rule warns about would have to be
supplied by the person running their own demo on their own machine.

What makes this acceptable is the trust boundary, not the arithmetic: nothing
here is reachable from a stranger's input. It is not the same shape as
`anchor_governance.py`'s replay path, which reads a file named on the command line
and is now checked for being a regular file before its contents are believed —
that one was fixed rather than accepted.

### `python:S2245` — a seeded PRNG in a differential bridge

`proofs/c1_bridge_check.py`, corpus generation.

`random.Random(20260717)` generates a fixed λ-term corpus for a differential
comparison. The seed is the point: the corpus must be the same on every run. No
security decision reads it. Suppressed at the line.

## Fixed rather than accepted, in the same pass

| Rule | Site | What it actually was |
| --- | --- | --- |
| `pythonsecurity:S8705` | `tools/hermes_review.py` | a revision taken from `argv` reached `git` where a leading `-` is an option, not a revision — the same shape that was a real defect in the agent gate. Now refused by pattern |
| `pythonsecurity:S8707` | `tools/anchor_governance.py` | `replay` opened whatever path it was given; a symlink or a device would have been read as governance vectors. Now required to be a regular file |
| `python:S8786` | `tools/spec_audit.py`, `tools/paper_claims.py` | two patterns that scanned super-linearly. Bounded |
| `python:S1481` | the DA-SIGMA-0002 reproducer | two prices recomputed and discarded; `at_price` is pure, so it was work nobody read. Deleted |
| `python:S5713` | `experiments/exp-002/validate_fixtures.py` | `UnicodeDecodeError` and `JSONDecodeError` named beside `ValueError`, which they both subclass |
| `python:S3776` | `proofs/store_mono_bridge_check.py` | the grow and shrink directions are now their own functions; the bridge reports the same 67 and 1153 |

## Not accepted, and not fixable here

### `python:S8495` — a function whose returns differ in length

`impl/sigma_glyph.py`, `force()`.

A Term is a tagged union: `("lit", atom)` and `("app", left, right)` have
different arities by construction, and the grammar is written out above the
function. A rule demanding one shape from every return is reading a sum type as a
record. Suppressed by name, with the reason in the docstring rather than only
here.
