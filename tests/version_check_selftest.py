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
    for failure in failures:
        print("FAIL", failure, file=sys.stderr)
    if failures:
        return 1
    print("VERSION-CHECK-SELFTEST: ALL PASS (candidate headings never become "
          "the adopted bundle)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
