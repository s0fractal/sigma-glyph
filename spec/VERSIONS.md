# Which number means what

*Non-normative. Checked by [`tools/version_check.py`](../tools/version_check.py)
for the parts that are facts about bytes; the rest is stated here because it is
not checkable.*

This repository carries six version numbers in three schemes. When nothing said
how they relate, nothing could be wrong about them — and two of them were.

| Number | Where | What it governs | What moves it |
| --- | --- | --- | --- |
| **Book I version** | `**Version:**` in `spec/book-1-truth.md` | that document's bytes, and therefore its anchor | any edit to the Book; MINOR when a conforming implementation of the previous version could become non-conformant, PATCH when nothing observable changes |
| **sigma-resume version** | `**Version:**` in `spec/sigma-resume.md` | that document's bytes; its schema strings (`…@draft-1`) name record formats and move only when a format does | the same rule |
| **`spec_version`** | each conformance suite | *the version of the Book the suite conforms to* | the Book moving, and the suite being regenerated against it |
| **`suite_version`** | `tests/spec_conformance/vectors.json` | the conformance-suite package, as released | adding or changing vectors, independently of the Book |
| **release `vX.Y.Z`** | the git tag, `version` in `pyproject.toml`, the `sigma-glyph` distribution | the exact bytes of every document and module at that tag, and the published Python modules | a release per `PUBLISHING.md`, cut once its adoption record is accepted (AGENTS.md rules 2 and 5) |

Through v0.7.0 a *bundle* (`spec/ANCHORS.txt`, adopted by threshold warrant under
GOV-anchors §3) named the bytes of a release apart from its tag; the registry was
retired on 2026-11-01 (`history/RETIREMENT-2026-11-ANCHORS.md`), and a release is
now its tag. `version_check.py` holds README's distribution heading to
`pyproject.toml` and the suite's `spec_version` to Book I's version.

## What independence means here

A document untouched by a release keeps its bytes, its `**Version:**` header
**and** its SpecAnchor from the last release that changed it. That is why Book I
sat at `0.5.2` in the `v0.6.x` releases and at `0.6.0` through `v0.7.x` and
`v0.8.0` without anything being wrong.

**The wire identifiers do not follow the document versions.** Book I 1.0.0 states the
semantics of 0.6.0 unchanged, and `runtime_semantics_id =
"sigma-book1-0.6.0/hash-thunk/leftmost-outermost"` names that semantics revision, not
the document's version; sigma-resume's `…@draft-1` schema strings name byte formats.
Both are inside every `computation_id`, so they move only when the semantics or the
format does.

The release number is not a maximum of the document versions and not derived from
them. It names a set of bytes at a tag. Reading it as "the version of the
specification" is the mistake this page exists to prevent.

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
