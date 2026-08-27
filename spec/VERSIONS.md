# Which number means what

*Non-normative. Checked by [`tools/version_check.py`](../tools/version_check.py)
for the parts that are facts about bytes; the rest is stated here because it is
not checkable.*

This repository carries six version numbers in three schemes. Nothing said how
they relate, which is why nothing could be wrong about them — and two of them
are.

| Number | Where | What it governs | What moves it |
| --- | --- | --- | --- |
| **Book version** | `**Version:**` in each Book | that document's bytes, and therefore its anchor | any edit to that Book; MINOR when a conforming implementation of the previous version could become non-conformant, PATCH when nothing observable changes |
| **GOV-anchors version** | `spec/GOV-anchors.md` | the governance profile itself, which is meta to the protocol | its own §0 rules: a frozen schema or the seven-step mechanism changing requires a new tag, not an edit |
| **`spec_version`** | each conformance suite | *the version of the Book the suite conforms to* | the Book moving, and the suite being regenerated against it |
| **`suite_version`** | `tests/spec_conformance/vectors.json` | the conformance-suite package, as released | adding or changing vectors, independently of the Book |
| **bundle `vX.Y.Z`** | section headings in `spec/ANCHORS.txt` | which exact bytes of every anchored file constitute a release | a governed adoption, per GOV-anchors §3 |
| **PyPI version** | `warrant-verify` releases | the published verifier | its own release cadence |

## What independence means here

A Book untouched by a release keeps its bytes, its `**Version:**` header **and**
its anchor from the last release that changed it. That is the bundle convention,
and it is why Book I sits at `0.5.2` inside a `v0.6.x` bundle without anything
being wrong. `ANCHORS.txt` states the convention with an example, and the example
is a claim about this tree: `version_check.py` verifies it, because it went stale
once already and nothing noticed.

The bundle number is not a maximum of the others and not derived from them. It
names an adopted set of bytes. Reading it as "the version of the specification" is
the mistake this page exists to prevent.

## Two numbers that do not agree, and are not fixed here

`spec_version` means *the Book this suite conforms to*. Two suites disagree:

- `wave_vectors.json` declares **0.5.2**, which is Book I's version, while Book II
  is at **0.6.1**. The two coincided when the suite was generated and nothing
  moved it since.
- `federation_vectors.json` declares **0.6.0** while Book III is at **0.6.1** — one
  patch behind the shipped document.

Neither is corrected here, and the reason is not laziness: both files are
**anchored**, so changing a byte of either is a governed change with a new bundle
and an adoption warrant. They are recorded by name in `version_check.py`, which
fails if a discrepancy stops reproducing without the record being removed — a
recorded exception that outlives its defect is a lie with a date on it.

## What this page cannot check

Whether a version number *ought* to have moved. That a Book's edit was a PATCH
rather than a MINOR is a judgement about whether a conforming implementation could
become non-conformant, and no tool here decides it. The versions above are checked
for agreement with one another, not for being the right numbers.
