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

BOOKS = {"Book I": "spec/book-1-truth.md",
         "Book II": "spec/book-2-navigation.md",
         "Book III": "spec/book-3-federation.md"}

# A suite's `spec_version` is the version of the Book it conforms to. Two suites
# disagree with that on `master`, and correcting either means regenerating an
# ANCHORED file — a governed change, not a documentation fix. Each entry says
# what the file declares and what the Book says, and the run fails when an entry
# stops reproducing: a recorded discrepancy that outlives its defect is a lie
# with a date on it.
KNOWN = {
    "tests/spec_conformance/wave_vectors.json": ("0.5.2", "Book II",
        "declares Book I's version rather than Book II's; the suite was "
        "generated when the two coincided and nothing moved it since"),
    "tests/spec_conformance/federation_vectors.json": ("0.6.0", "Book III",
        "declares a Book III version one patch behind the shipped one"),
}


def book_version(path: str) -> str:
    text = (ROOT / path).read_text()
    found = re.search(r'^\*\*Version:\*\* *(\d+(?:\.\d+)*)', text, re.M)
    return found.group(1) if found else ""


def top_bundle() -> str:
    for line in (ROOT / "spec/ANCHORS.txt").read_text().splitlines():
        if line.startswith("== "):
            return line.split()[1]
    return ""


def check_suite_versions(problems: list[str]) -> int:
    """Each suite says which Book it conforms to. It should be that Book's."""
    pairs = (("tests/spec_conformance/vectors.json", "Book I"),
             ("tests/spec_conformance/wave_vectors.json", "Book II"),
             ("tests/spec_conformance/federation_vectors.json", "Book III"))
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
    found = re.search(r'E\.g\. (Book [IV]+) ships in (v[0-9.x]+) bundles at its '
                      r'own version (\d+(?:\.\d+)*)', text)
    if not found:
        problems.append("the bundle convention in ANCHORS.txt no longer carries an "
                        "example in the form this check reads, so nothing keeps it "
                        "true")
        return 0
    book, bundle, version = found.groups()
    actual = book_version(BOOKS[book])
    if actual != version:
        problems.append(f"ANCHORS' example says {book} ships at its own version "
                        f"{version}; {book} is at {actual}")
    prefix = bundle.rstrip("x").rstrip(".")
    if not top_bundle().startswith(prefix):
        problems.append(f"ANCHORS' example speaks of {bundle} bundles and the top "
                        f"section is {top_bundle()}")
    return 1


def check_readme_bundle(problems: list[str]) -> int:
    """README names the adopted bundle. ANCHORS is where it is adopted."""
    text = (ROOT / "README.md").read_text()
    found = re.search(r'### Current: (v\d+(?:\.\d+)*)', text)
    if not found:
        problems.append("README no longer names a current bundle in the form this "
                        "check reads")
        return 0
    top = top_bundle()
    if found.group(1) != top:
        problems.append(f"README calls {found.group(1)} current and the top ANCHORS "
                        f"section is {top}")
    return 1


def main() -> int:
    problems: list[str] = []
    checked = (check_suite_versions(problems) + check_bundle_example(problems)
               + check_readme_bundle(problems))

    print("versions on this tree")
    for name, path in BOOKS.items():
        print(f"  {name:9} {book_version(path)}")
    print(f"  GOV       {book_version('spec/GOV-anchors.md')}")
    print(f"  bundle    {top_bundle()}")
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
    print("\nVERSION-CHECK: every relation that is a fact about bytes holds, and "
          "the two that do not are recorded by name and fail if they are fixed "
          "without being removed here. Which number *ought* to move when a "
          "document changes is not checkable and is stated in spec/VERSIONS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
