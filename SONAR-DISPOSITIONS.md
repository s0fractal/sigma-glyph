# SonarCloud findings this repository accepts, and why

*Every entry names the rule, the site, and the reason. A finding that is not here
is not accepted — it is either fixed or it has not been looked at. The README must
not say "Sonar clean" while this file has entries.*

Read with `SECURITY-ASSUMPTIONS.md`: that file records what the system assumes,
this one records what a static analyser reports that we have decided not to change.
Dispositions for files that left the tree (the Warrant 0.x gates on 2026-10-19,
the echo on 2026-10-31) are at commit `96414ab`.

## Where the numbers stand

At `master@65aea5f` (2026-11-01) the analyser reported **13 unresolved**, no
security hotspots, security rating **C**. Two of the 13 are vulnerabilities:
`githubactions:S8541` in `publish.yml`, fixed in the same change as this
revision of the file, and `python:S2245`, accepted below. The other eleven are
code smells, sorted below into fixed, accepted and deferred.

## Accepted

### `python:S2245` — a seeded PRNG in a differential bridge

`proofs/c1_bridge_check.py`, corpus generation.

`random.Random(20260717)` generates a fixed λ-term corpus for a differential
comparison. The seed is the point: the corpus must be the same on every run. No
security decision reads it.

`# NOSONAR` at the line does not clear it — with the rule key and without. The
comment stays because it is true for a reader; the finding is accepted here
because the mechanism for suppressing it does not work in this analyser, and
silently pretending it is gone would be worse than saying so.

### `python:S3776` / `rust:S3776` — cognitive complexity in the kernels

`impl/sigma_resume.py` (three functions), `impl/sigma_provider.py` (one),
`impl-rs/src/main.rs` (one).

These are the reference transition and its consumer surface; each function
follows a numbered section of `spec/sigma-resume.md` or Book I branch by branch,
and splitting one moves a rule away from the sentence it implements. A change to
these files also changes the provider identity a consumer pins, and claims
acceptances are replays of exact bytes; neither is worth paying for a metric.
Refactoring belongs to a change that has its own reason to touch them.

## Fixed in the same change as this revision

| Rule | Site | What it was |
| --- | --- | --- |
| `githubactions:S8541` | `.github/workflows/publish.yml` | `pip install build twine` without `--only-binary :all:` could run a setup script; both are pure wheels, so the install is now wheels-only |
| `rust:S1612` | `impl-rs/src/main.rs`, `number_value` | a closure around `u8::is_ascii_digit` |

## Deferred, with the change that removes them

| Rule | Site | Why not now |
| --- | --- | --- |
| `python:S9409` (2) | `tools/check_release_surface.py` | both sites are in self-test fixtures for the retired `sigma_wave` module; the next change to that gate removes the fixtures rather than polishing them |
| `python:S3776` | `tools/suite_schema.py`, `check_record` | one closed-schema walk; it goes with the same tooling pass |
| `python:S1192` | `impl/sigma_provider.py`, `"sigma_resume.py"` ×3 | provider identity bytes, as above |
| `rust:S9045` | `impl-rs/src/main.rs`, `mod tests` | moving the module after the resume items is a 200-line diff with no behaviour; it goes with the next change to that file |

## Not accepted, and not fixable here

### `python:S8495` — a function whose returns differ in length

`impl/sigma_glyph.py`, `force()`.

A Term is a tagged union: `("lit", atom)` and `("app", left, right)` have
different arities by construction, and the grammar is written out above the
function. A rule demanding one shape from every return is reading a sum type as a
record. Suppressed by name, with the reason in the docstring rather than only
here.
