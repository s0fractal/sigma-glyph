#!/usr/bin/env python3
"""Do the version numbers in this repository agree with each other?

Book I's own `**Version:**`, sigma-resume's, the conformance suite's
`spec_version` and `suite_version`, and the distribution in `pyproject.toml`.
Two relations are facts about bytes and are checked here: the suite's
`spec_version` is Book I's version, and README's one distribution heading names
the version `pyproject.toml` builds. Which number *ought* to move when a
document changes is not checkable and is stated in spec/VERSIONS.md.

The detached anchor registry (spec/ANCHORS.txt) and its "adopted bundle"
heading were retired with bundle-era governance on 2026-11-01: a release is
its tag's bytes and its adoption a signed record (AGENTS.md rule 2).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BOOK_I = "spec/book-1-truth.md"
RESUME = "spec/sigma-resume.md"
SUITE = "tests/spec_conformance/vectors.json"


def book_version(path: str) -> str:
    text = (ROOT / path).read_text()
    found = re.search(r'^\*\*Version:\*\* *(\d+(?:\.\d+)*(?:-[0-9A-Za-z.]+)?)\s*$', text, re.M)
    return found.group(1) if found else ""


def check_suite_version(problems: list[str]) -> int:
    """The suite says which Book I it conforms to. It should be this one."""
    declared = json.loads((ROOT / SUITE).read_text()).get("spec_version")
    expected = book_version(BOOK_I)
    if declared != expected:
        problems.append(f"{SUITE} declares spec_version {declared} and Book I is at {expected}; "
                        "a suite's spec_version is the version of the Book it conforms to")
    return 1


STATUS_SECTION = "## Status by surface"
# README's one distribution heading, in its bare number form: a qualifier cannot
# be smuggled in.
DISTRIBUTION = r'\d+(?:\.\d+)*(?:\.post\d+|\.dev\d+)?'


def readme_distribution_headings(text: str) -> tuple[int, list[tuple[int, str, bool]]]:
    """(number of "Status by surface" sections, [(line, bare number or "" when not in
    the exact form, inside that section)]) for every "### Distribution:" heading in
    the whole file: a second one anywhere is a second public claim."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.rstrip() == STATUS_SECTION]
    section = range(0)
    if len(starts) == 1:
        end = next((i for i in range(starts[0] + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        section = range(starts[0], end)
    found = []
    for i, line in enumerate(lines):
        match = re.match(r'^### Distribution:(.*)$', line)
        if match:
            exact = re.fullmatch(r' (' + DISTRIBUTION + r')\s*', match.group(1))
            found.append((i + 1, exact.group(1) if exact else "", i in section))
    return len(starts), found


def readme_distribution_problems(text: str) -> list[str]:
    """Why README's distribution heading cannot be read as exactly one claim; empty
    when there is one Status section and one bare heading inside it."""
    sections, hits = readme_distribution_headings(text)
    problems = []
    if sections != 1:
        problems.append(f"README carries {sections} '{STATUS_SECTION}' sections; the "
                        "distribution heading is read from exactly one")
    form = "'### Distribution: X.Y.Z'"
    if not hits:
        problems.append(f"README no longer names the distribution under {form}")
    elif len(hits) > 1:
        problems.append(f"README states the distribution {len(hits)} times "
                        f"({', '.join(f'line {line}' for line, _, _ in hits)}); one public "
                        f"claim, under {form} in the '{STATUS_SECTION}' section, is what can be checked")
    elif not hits[0][1]:
        problems.append(f"README line {hits[0][0]} does not state the distribution in the bare form {form}")
    elif not hits[0][2]:
        problems.append(f"README line {hits[0][0]} names the distribution outside the '{STATUS_SECTION}' section")
    return problems


def readme_distribution(text: str) -> str:
    """The distribution README states, or "" unless readme_distribution_problems is empty:
    two contradictory headings yield "", never the first one."""
    return "" if readme_distribution_problems(text) else readme_distribution_headings(text)[1][0][1]


def pyproject_version() -> str:
    found = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    return found.group(1) if found else ""


def check_readme(problems: list[str]) -> int:
    text = (ROOT / "README.md").read_text()
    problems.extend(readme_distribution_problems(text))
    dist = readme_distribution(text)
    if dist and dist != pyproject_version():
        problems.append(f"README calls {dist} the distribution and pyproject.toml says {pyproject_version()}")
    return 1


def main() -> int:
    problems: list[str] = []
    checked = check_suite_version(problems) + check_readme(problems)
    suite = json.loads((ROOT / SUITE).read_text())
    print("versions on this tree")
    print(f"  Book I    {book_version(BOOK_I)}")
    print(f"  resume    {book_version(RESUME)}")
    print(f"  pyproject {pyproject_version()}")
    print(f"  suite     spec_version {suite['spec_version']}, package {suite['suite_version']}")
    print(f"\nrelations checked : {checked}")
    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print("\nVERSION-CHECK: the suite's spec_version is Book I's, and README's distribution is pyproject's. "
          "Which number *ought* to move when a document changes is not checkable and is stated in "
          "spec/VERSIONS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
