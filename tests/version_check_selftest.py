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
    # headings. The reader must take exactly those, and must not take the retired
    # single "Current" label — that label is how an adopted-but-unreleased bundle
    # came to be read as a release.
    readme_cases = {
        "both headings": (
            "### Adopted bundle: v0.7.0\n\ntext\n\n### Distribution: 0.6.7\n",
            ("v0.7.0", "0.6.7")),
        "post release": ("### Distribution: 0.6.6.post1\n", ("", "0.6.6.post1")),
        "retired current label": (
            "### Current: v0.7.0\n### Previous: v0.6.7\n", ("", "")),
        "qualifier smuggled in": (
            "### Adopted bundle: v0.7.0 (released)\n"
            "### Distribution: 0.6.7, tagged\n", ("", "")),
        "label without number": ("### Adopted bundle: next\n", ("", "")),
    }
    for name, (text, expected) in readme_cases.items():
        got = vc.readme_status_claims(text)
        if got != expected:
            failures.append(f"readme {name}: got {got!r}, expected {expected!r}")

    for failure in failures:
        print("FAIL", failure, file=sys.stderr)
    if failures:
        return 1
    print("VERSION-CHECK-SELFTEST: ALL PASS (candidate headings never become "
          "the adopted bundle; README's bundle and distribution headings are "
          "read separately and only in their exact form)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
