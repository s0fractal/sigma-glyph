# Which number means what

*Non-normative. Checked by [`tools/version_check.py`](../tools/version_check.py)
for the parts that are facts about bytes; the rest is stated here because it is
not checkable.*

This repository carries six version numbers in three schemes. Nothing said how
they relate, which is why nothing could be wrong about them — and two of them
were.

| Number | Where | What it governs | What moves it |
| --- | --- | --- | --- |
| **Book version** | `**Version:**` in each Book | that document's bytes, and therefore its anchor | any edit to that Book; MINOR when a conforming implementation of the previous version could become non-conformant, PATCH when nothing observable changes |
| **GOV-anchors version** | `spec/GOV-anchors.md` | the governance profile itself, which is meta to the protocol | its own §0 rules: a frozen schema or the seven-step mechanism changing requires a new tag, not an edit |
| **`spec_version`** | each conformance suite | *the version of the Book the suite conforms to* | the Book moving, and the suite being regenerated against it |
| **`suite_version`** | `tests/spec_conformance/vectors.json` | the conformance-suite package, as released | adding or changing vectors, independently of the Book |
| **bundle `vX.Y.Z`** | section headings in `spec/ANCHORS.txt` | which exact bytes of every anchored file constitute a release | a governed adoption, per GOV-anchors §3 |
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

`spec_version` means *the Book this suite conforms to*. Two suites disagreed:
`wave_vectors.json` declared **0.5.2**, which was Book I's version, while Book II
was at 0.6.1; `federation_vectors.json` declared **0.6.0** while Book III was at
0.6.1. Neither could be corrected without regenerating an **anchored** file, so
both were carried by name in `version_check.py`, which fails when a recorded
discrepancy stops reproducing without the record being removed.

The adopted `v0.7.0` bundle regenerates every suite against its own Book, which
closes both. The records were removed in the same change — leaving them would
have been the failure the mechanism exists to cause.

## What this page cannot check

Whether a version number *ought* to have moved. That a Book's edit was a PATCH
rather than a MINOR is a judgement about whether a conforming implementation could
become non-conformant, and no tool here decides it. The versions above are checked
for agreement with one another, not for being the right numbers.
