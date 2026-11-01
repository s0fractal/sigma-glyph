# Which number means what

*Non-normative. Checked by [`tools/version_check.py`](../tools/version_check.py)
for the parts that are facts about bytes; the rest is stated here because it is
not checkable.*

This repository carries six version numbers in three schemes. When nothing said
how they relate, nothing could be wrong about them — and two of them were.

| Number | Where | What it governs | What moves it |
| --- | --- | --- | --- |
| **Book I version** | `**Version:**` in `spec/book-1-truth.md` | that document's bytes, and therefore its anchor | any edit to the Book; MINOR when a conforming implementation of the previous version could become non-conformant, PATCH when nothing observable changes |
| **sigma-resume version** | `**Version:**` in `spec/sigma-resume.md` (`1.0.0-rc.1`) | that document's bytes; its schema strings (`…@draft-1`) name record formats and move only when a format does | the same rule; it is not anchored yet, so its version is the only name its bytes have until it is |
| **`spec_version`** | each conformance suite | *the version of the Book the suite conforms to* | the Book moving, and the suite being regenerated against it |
| **`suite_version`** | `tests/spec_conformance/vectors.json` | the conformance-suite package, as released | adding or changing vectors, independently of the Book |
| **bundle `vX.Y.Z`** | section headings in `spec/ANCHORS.txt` | which exact bytes of every anchored file constitute a release | an adoption, which is a signed record (AGENTS.md rule 2); through v0.7.0 it was a threshold warrant under GOV-anchors §3 |
| **PyPI version** | `version` in `pyproject.toml`, the `sigma-glyph` distribution | the published Python modules | a distribution release per `PUBLISHING.md`; it may sit one bundle behind the adopted one |

The `vX.Y.Z` git tags and GitHub releases follow the PyPI version, not the
bundle: cutting a release creates a tag, and adopting a bundle in `ANCHORS.txt`
creates nothing in git. README's "Status by surface" names both, and
`version_check.py` holds its two headings to `ANCHORS.txt` and `pyproject.toml`.

## What independence means here

A Book untouched by a release keeps its bytes, its `**Version:**` header **and**
its anchor from the last release that changed it. That is the bundle convention,
and it is why Book I sat at `0.5.2` inside the `v0.6.x` bundles without anything
being wrong. `ANCHORS.txt` states the convention with an example, and the example
is a claim about this tree: `version_check.py` verifies it, because it went stale
once already and nothing noticed.

The bundle number is not a maximum of the others and not derived from them. It
names an adopted set of bytes. Reading it as "the version of the specification" is
the mistake this page exists to prevent.

## Two numbers that did not agree, and now do

`spec_version` means *the Book this suite conforms to*. Through v0.6.x two suites
declared another Book's version; the v0.7.0 bundle regenerated every suite against
its own Book, and `version_check.py` carries no recorded discrepancy since. Both
suites left with their Books on 2026-10-31.

## What this page cannot check

Whether a version number *ought* to have moved. That a Book's edit was a PATCH
rather than a MINOR is a judgement about whether a conforming implementation could
become non-conformant, and no tool here decides it. The versions above are checked
for agreement with one another, not for being the right numbers.
