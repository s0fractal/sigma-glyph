#!/usr/bin/env python3
"""Do the six version numbers in this repository agree with each other?

There are six, in three schemes: each Book's own `**Version:**`, GOV-anchors'
document version, the conformance suites' `spec_version`, the suite package's
`suite_version`, and the `vX.Y.Z` release bundle in `spec/ANCHORS.txt`. Nothing
stated how they relate, so nothing could be wrong — and two of them are.

What is checkable is checked here. What is not is listed rather than implied:
version numbers are claims about intent, and only the relations below are facts
about bytes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BOOK_I = "Book I"
BOOK_II = "Book II"
BOOK_III = "Book III"
BOOKS = {BOOK_I: "spec/book-1-truth.md",
         BOOK_II: "spec/book-2-navigation.md",
         BOOK_III: "spec/book-3-federation.md"}
# Every anchored document that carries its own `**Version:**`, for the bundle
# convention's example. It used to be readable only for Books, so illustrating
# the convention with a document that does not move when a Book does -- which is
# exactly what the convention is about -- was not expressible.
VERSIONED = dict(BOOKS, **{"GOV-anchors": "spec/GOV-anchors.md"})

# A suite's `spec_version` is the version of the Book it conforms to. Two suites
# disagree with that on `master`, and correcting either means regenerating an
# ANCHORED file — a governed change, not a documentation fix. Each entry says
# what the file declares and what the Book says, and the run fails when an entry
# stops reproducing: a recorded discrepancy that outlives its defect is a lie
# with a date on it.
# Empty, and that is the record: both entries this carried -- wave_vectors
# declaring Book I's version, federation_vectors declaring a Book III version one
# patch behind -- were closed by regenerating each suite against its own Book in
# the v0.7.0 candidate. The checker fails when an entry stops reproducing, so
# leaving them would have been the failure rather than the fix.
KNOWN = {}


def book_version(path: str) -> str:
    text = (ROOT / path).read_text()
    found = re.search(r'^\*\*Version:\*\* *(\d+(?:\.\d+)*)', text, re.M)
    return found.group(1) if found else ""


def adopted_bundle_from(text: str) -> str:
    """Return the newest release section that is actually in force.

    Candidate sections deliberately sit above the adopted history while their
    bytes are reviewed.  Treating the first heading as current made a proposal
    rewrite README's statement about the live release before any warrant had
    adopted it.
    """
    for line in text.splitlines():
        if line.startswith("== ") and "CANDIDATE" not in line.upper():
            return line.split()[1]
    return ""


def top_bundle() -> str:
    return adopted_bundle_from((ROOT / "spec/ANCHORS.txt").read_text())


def check_suite_versions(problems: list[str]) -> int:
    """Each suite says which Book it conforms to. It should be that Book's."""
    pairs = (("tests/spec_conformance/vectors.json", BOOK_I),
             ("tests/spec_conformance/wave_vectors.json", BOOK_II),
             ("tests/spec_conformance/federation_vectors.json", BOOK_III))
    checked = 0
    for path, book in pairs:
        declared = json.loads((ROOT / path).read_text()).get("spec_version")
        expected = book_version(BOOKS[book])
        known = KNOWN.get(path)
        if declared == expected:
            if known:
                problems.append(
                    f"{path} now declares {declared}, which matches {book}. The "
                    "recorded discrepancy no longer reproduces — delete the entry")
            checked += 1
            continue
        if known and known[0] == declared and known[1] == book:
            continue
        problems.append(f"{path} declares spec_version {declared} and {book} is at "
                        f"{expected}; a suite's spec_version is the version of the "
                        "Book it conforms to")
    return checked


def check_bundle_example(problems: list[str]) -> int:
    """ANCHORS explains its own convention with an example. The example is a
    claim about this tree, and it went stale once already."""
    text = (ROOT / "spec/ANCHORS.txt").read_text()
    found = re.search(r'E\.g\. ([A-Za-z][\w -]{0,20}) ships in (v[0-9.x]+) bundles at its '
                      r'own version (\d+(?:\.\d+)*)', text)
    if not found:
        problems.append("the bundle convention in ANCHORS.txt no longer carries an "
                        "example in the form this check reads, so nothing keeps it "
                        "true")
        return 0
    book, bundle, version = found.groups()
    if book not in VERSIONED:
        problems.append(f"ANCHORS' example names {book}, which is not an "
                        'anchored document carrying its own version')
        return 0
    actual = book_version(VERSIONED[book])
    if actual != version:
        problems.append(f"ANCHORS' example says {book} ships at its own version "
                        f"{version}; {book} is at {actual}")
    prefix = bundle.rstrip("x").rstrip(".")
    if not top_bundle().startswith(prefix):
        problems.append(f"ANCHORS' example speaks of {bundle} bundles and the top "
                        f"section is {top_bundle()}")
    return 1


def readme_status_claims(text: str) -> tuple[str, str]:
    """The two version headings README's "Status by surface" section states.

    Returns (adopted bundle, distribution); either is "" when README does not
    carry that heading in the exact form.  The form is deliberately strict — a
    heading has to be the bare label and the bare number — so a qualifier
    cannot be smuggled into it, and so the retired "### Current: vX" heading,
    which called an adopted-but-unreleased bundle current, does not match.
    """
    bundle = re.search(r'^### Adopted bundle: (v\d+(?:\.\d+)*)\s*$', text, re.M)
    dist = re.search(r'^### Distribution: (\d+(?:\.\d+)*(?:\.post\d+)?)\s*$',
                     text, re.M)
    return (bundle.group(1) if bundle else "", dist.group(1) if dist else "")


def pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    found = re.search(r'^version = "([^"]+)"', text, re.M)
    return found.group(1) if found else ""


def check_readme_status(problems: list[str]) -> int:
    """README names the adopted bundle and the distribution, under two headings.

    ANCHORS is where a bundle is adopted; pyproject.toml is what a distribution
    is built from.  The two numbers differ whenever a bundle is adopted before
    anything is released, which is the normal case here — and a README that
    names only one of them, or names them under one label, is how "adopted"
    gets read as "released".
    """
    bundle, dist = readme_status_claims((ROOT / "README.md").read_text())
    checked = 0
    if not bundle:
        problems.append("README no longer names the adopted bundle under "
                        "'### Adopted bundle: vX.Y.Z'")
    else:
        top = top_bundle()
        if bundle != top:
            problems.append(f"README calls {bundle} the adopted bundle and the top "
                            f"ANCHORS section is {top}")
        checked += 1
    if not dist:
        problems.append("README no longer names the distribution under "
                        "'### Distribution: X.Y.Z'")
    else:
        declared = pyproject_version()
        if dist != declared:
            problems.append(f"README calls {dist} the distribution and "
                            f"pyproject.toml says {declared}")
        checked += 1
    return checked


def main() -> int:
    problems: list[str] = []
    checked = (check_suite_versions(problems) + check_bundle_example(problems)
               + check_readme_status(problems))

    print("versions on this tree")
    for name, path in BOOKS.items():
        print(f"  {name:9} {book_version(path)}")
    print(f"  GOV       {book_version('spec/GOV-anchors.md')}")
    print(f"  bundle    {top_bundle()}")
    print(f"  pyproject {pyproject_version()}")
    suite = json.loads((ROOT / 'tests/spec_conformance/vectors.json').read_text())
    print(f"  suite     spec_version {suite['spec_version']}, "
          f"package {suite['suite_version']}")
    print(f"\nrelations checked : {checked}")
    print(f"recorded discrepancies (governed to fix, not fixable here): {len(KNOWN)}")
    for path, (declared, book, why) in KNOWN.items():
        print(f"    {Path(path).name}: {declared} vs {book} — {why}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print(f"\nVERSION-CHECK: every relation that is a fact about bytes holds, with "
          f"{len(KNOWN)} recorded discrepancy(ies) — each of which fails this run "
          "if it is fixed without the record being removed. Which number *ought* "
          "to move when a document changes is not checkable and is stated in "
          "spec/VERSIONS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
