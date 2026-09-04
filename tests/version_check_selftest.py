#!/usr/bin/env python3
"""The version checker must not confuse a candidate with an adopted release."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import version_check as vc  # noqa: E402


def main() -> int:
    cases = {
        "ordinary history": ("== v0.6.7 ==\n== v0.6.6 ==\n", "v0.6.7"),
        "candidate above adopted": (
            "== v0.7.0 (CANDIDATE — not in force) ==\n== v0.6.7 ==\n",
            "v0.6.7"),
        "multiple candidates": (
            "== v0.8.0 (candidate) ==\n== v0.7.0 (CANDIDATE) ==\n"
            "== v0.6.7 ==\n", "v0.6.7"),
        "no adopted release": ("== v0.7.0 (CANDIDATE) ==\n", ""),
    }
    failures = []
    for name, (text, expected) in cases.items():
        got = vc.adopted_bundle_from(text)
        if got != expected:
            failures.append(f"{name}: got {got!r}, expected {expected!r}")

    # README states the adopted bundle and the distribution under two separate
    # headings, inside its one "Status by surface" section. The reader must take
    # exactly those, and must not take the retired single "Current" label — that
    # label is how an adopted-but-unreleased bundle came to be read as a release.
    # It must also refuse to choose when a label appears twice: the first match
    # of two contradictory headings kept the check green over a README that
    # made both claims.
    section = "## Status by surface\n\nprose\n\n"
    readme_cases = {
        "both headings": (
            section + "### Adopted bundle: v0.7.0\n\ntext\n\n### Distribution: 0.6.7\n"
            "\n### Evaluator bytes and Warrant runtime tags\n\n## The Three Books\n",
            ("v0.7.0", "0.6.7")),
        "post release": (section + "### Distribution: 0.6.6.post1\n", ("", "0.6.6.post1")),
        "retired current label": (
            section + "### Current: v0.7.0\n### Previous: v0.6.7\n", ("", "")),
        "qualifier smuggled in": (
            section + "### Adopted bundle: v0.7.0 (released)\n"
            "### Distribution: 0.6.7, tagged\n", ("", "")),
        "label without number": (section + "### Adopted bundle: next\n", ("", "")),
        "duplicate conflicting bundle": (
            section + "### Adopted bundle: v0.7.0\n\ntext\n\n"
            "### Adopted bundle: v9.9.9\n\n### Distribution: 0.6.7\n",
            ("", "0.6.7")),
        "duplicate conflicting distribution": (
            section + "### Adopted bundle: v0.7.0\n\n### Distribution: 0.6.7\n\n"
            "text\n\n### Distribution: 9.9.9\n",
            ("v0.7.0", "")),
        "duplicate agreeing bundle": (
            section + "### Adopted bundle: v0.7.0\n\n### Adopted bundle: v0.7.0\n"
            "\n### Distribution: 0.6.7\n",
            ("", "0.6.7")),
        "duplicate bundle with qualifier": (
            section + "### Adopted bundle: v0.7.0\n\n"
            "### Adopted bundle: v9.9.9 (released)\n\n### Distribution: 0.6.7\n",
            ("", "0.6.7")),
        "twin heading after the section": (
            section + "### Adopted bundle: v0.7.0\n\n### Distribution: 0.6.7\n\n"
            "## The Three Books\n\n### Adopted bundle: v9.9.9\n",
            ("", "0.6.7")),
        "headings outside the section": (
            "## Intro\n\n### Adopted bundle: v0.7.0\n\n### Distribution: 0.6.7\n\n"
            + section + "text\n",
            ("", "")),
        "no status section": (
            "### Adopted bundle: v0.7.0\n\n### Distribution: 0.6.7\n", ("", "")),
        "two status sections": (
            section + "### Adopted bundle: v0.7.0\n\n### Distribution: 0.6.7\n\n"
            + section + "text\n",
            ("", "")),
        "section title with a qualifier": (
            "## Status by surface (2026)\n\n### Adopted bundle: v0.7.0\n\n"
            "### Distribution: 0.6.7\n",
            ("", "")),
    }
    for name, (text, expected) in readme_cases.items():
        got = vc.readme_status_claims(text)
        if got != expected:
            failures.append(f"readme {name}: got {got!r}, expected {expected!r}")
    # The reporter and the reader agree: a case yields "" for a label exactly
    # when the reporter names that label.
    for name, (text, expected) in readme_cases.items():
        problems = " ".join(vc.readme_status_problems(text))
        for label, claim in zip(("adopted bundle", "distribution"), expected):
            if claim and label in problems:
                failures.append(f"readme {name}: {label} read as {claim!r} but "
                                f"also reported: {problems}")
            if not claim and label not in problems:
                failures.append(f"readme {name}: {label} refused but not reported: "
                                f"{problems!r}")
    if vc.readme_status_problems(readme_cases["both headings"][0]):
        failures.append("readme both headings: clean README reported as a problem")

    for failure in failures:
        print("FAIL", failure, file=sys.stderr)
    if failures:
        return 1
    print("VERSION-CHECK-SELFTEST: ALL PASS (candidate headings never become "
          "the adopted bundle; README's bundle and distribution headings are "
          "read separately, only in their exact form, only inside the Status "
          "section, and refused rather than chosen when a label appears twice)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
