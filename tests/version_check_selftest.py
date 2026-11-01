#!/usr/bin/env python3
"""The version checker reads README's distribution heading only in its exact form, only
inside the Status section, and refuses rather than chooses when it appears twice."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import version_check as vc  # noqa: E402


def main() -> int:
    failures = []
    section = "## Status by surface\n\nprose\n\n"
    cases = {
        "the heading": (section + "### Distribution: 1.0.0\n\n## The specification\n", "1.0.0"),
        "post release": (section + "### Distribution: 0.6.6.post1\n", "0.6.6.post1"),
        "dev release": (section + "### Distribution: 0.9.0.dev0\n", "0.9.0.dev0"),
        "qualifier smuggled in": (section + "### Distribution: 1.0.0, tagged\n", ""),
        "label without number": (section + "### Distribution: next\n", ""),
        "duplicate conflicting": (section + "### Distribution: 1.0.0\n\ntext\n\n### Distribution: 9.9.9\n", ""),
        "duplicate agreeing": (section + "### Distribution: 1.0.0\n\n### Distribution: 1.0.0\n", ""),
        "twin heading after the section": (
            section + "### Distribution: 1.0.0\n\n## Later\n\n### Distribution: 9.9.9\n", ""),
        "heading outside the section": ("## Intro\n\n### Distribution: 1.0.0\n\n" + section + "text\n", ""),
        "no status section": ("### Distribution: 1.0.0\n", ""),
        "two status sections": (section + "### Distribution: 1.0.0\n\n" + section + "text\n", ""),
        "section title with a qualifier": ("## Status by surface (2026)\n\n### Distribution: 1.0.0\n", ""),
        "a trailing newline is not a qualifier": (section + "### Distribution: 1.0.0\n", "1.0.0"),
    }
    for name, (text, expected) in cases.items():
        got = vc.readme_distribution(text)
        if got != expected:
            failures.append(f"{name}: got {got!r}, expected {expected!r}")
        reported = bool(vc.readme_distribution_problems(text))
        if reported != (expected == ""):
            failures.append(f"{name}: read {got!r} but reported={reported}")
    for failure in failures:
        print("FAIL", failure, file=sys.stderr)
    if failures:
        return 1
    print("VERSION-CHECK-SELFTEST: ALL PASS (README's distribution heading is read only in its exact "
          "form, only inside the Status section, and refused rather than chosen when it appears twice)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
