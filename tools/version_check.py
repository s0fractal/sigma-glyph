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


STATUS_SECTION = "## Status by surface"
# The two status headings README states, each with the bare number form it
# has to take.  A qualifier cannot be smuggled into either, and the retired
# "### Current: vX" heading, which called an adopted-but-unreleased bundle
# current, matches neither.
STATUS_LABELS = {"Adopted bundle": r'v\d+(?:\.\d+)*',
                 "Distribution": r'\d+(?:\.\d+)*(?:\.post\d+)?'}


def readme_status_headings(text: str) -> tuple[int, dict[str, list[tuple[int, str, bool]]]]:
    """Every status heading README carries, and where each one sits.

    Returns (number of "Status by surface" sections, {label: [(line number,
    bare number or "" when the heading is not in the exact form, inside the
    Status section)]}).  Headings are collected from the whole file, not only
    from the section: a second "### Adopted bundle:" heading anywhere is a
    second public claim, and reading only the first one, or only the one in
    the section, is how two contradictory claims stayed green.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.rstrip() == STATUS_SECTION]
    section = range(0)
    if len(starts) == 1:
        end = next((i for i in range(starts[0] + 1, len(lines))
                    if lines[i].startswith("## ")), len(lines))
        section = range(starts[0], end)
    found: dict[str, list[tuple[int, str, bool]]] = {label: [] for label in STATUS_LABELS}
    for i, line in enumerate(lines):
        match = re.match(r'^### (Adopted bundle|Distribution):(.*)$', line)
        if not match:
            continue
        label, rest = match.groups()
        exact = re.fullmatch(r' (' + STATUS_LABELS[label] + r')\s*', rest)
        found[label].append((i + 1, exact.group(1) if exact else "", i in section))
    return len(starts), found


def readme_status_problems(text: str) -> list[str]:
    """Why README's status headings cannot be read as exactly two claims.

    Empty when there is one "Status by surface" section and each label appears
    exactly once, in the bare form, inside that section.  Anything else — a
    missing heading, a duplicate with a different number, a heading outside
    the section, a qualifier — fails closed rather than picking a winner.
    """
    sections, found = readme_status_headings(text)
    problems = []
    if sections != 1:
        problems.append(f"README carries {sections} '{STATUS_SECTION}' sections; "
                        "the status headings are read from exactly one")
    for label, hits in found.items():
        number = "vX.Y.Z" if label == "Adopted bundle" else "X.Y.Z"
        form = f"'### {label}: {number}'"
        if not hits:
            problems.append(f"README no longer names the {label.lower()} under {form}")
            continue
        if len(hits) > 1:
            where = ", ".join(f"line {line}" for line, _, _ in hits)
            problems.append(f"README states the {label.lower()} {len(hits)} times "
                            f"({where}); one public claim, under {form} in the "
                            f"'{STATUS_SECTION}' section, is what can be checked")
            continue
        line, number_found, inside = hits[0]
        if not number_found:
            problems.append(f"README line {line} does not state the {label.lower()} "
                            f"in the bare form {form}")
        elif not inside:
            problems.append(f"README line {line} names the {label.lower()} outside "
                            f"the '{STATUS_SECTION}' section")
    return problems


def readme_status_claims(text: str) -> tuple[str, str]:
    """The two version headings README's "Status by surface" section states.

    Returns (adopted bundle, distribution); either is "" unless README carries
    exactly one heading with that label, in the exact bare form, inside its one
    "Status by surface" section.  A duplicate heading with a conflicting number
    therefore yields "", not the first match: the check fails instead of
    endorsing one of two contradictory public claims.
    """
    sections, found = readme_status_headings(text)
    claims = []
    for label in STATUS_LABELS:
        hits = found[label]
        ok = sections == 1 and len(hits) == 1 and hits[0][1] and hits[0][2]
        claims.append(hits[0][1] if ok else "")
    return (claims[0], claims[1])


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
    gets read as "released".  Each heading has to occur exactly once, in the
    Status section: two headings with the same label are two claims, and this
    check does not choose between them.
    """
    text = (ROOT / "README.md").read_text()
    problems.extend(readme_status_problems(text))
    bundle, dist = readme_status_claims(text)
    checked = 0
    if bundle:
        top = top_bundle()
        if bundle != top:
            problems.append(f"README calls {bundle} the adopted bundle and the top "
                            f"ANCHORS section is {top}")
        checked += 1
    if dist:
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
