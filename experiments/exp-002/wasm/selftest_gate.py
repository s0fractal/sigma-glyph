#!/usr/bin/env python3
"""Does the determinism gate fail *because of* the disagreement it exists for?

A selftest that makes the run fail for fifty other reasons proves nothing: delete
the check under test and it stays green. So this substitutes a `measure()` that
returns each fixture's own frozen verdict — everything else about the run stays
correct — and makes exactly one vector's five observations disagree. The run must
then fail with exactly that one error and no other.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run as runner  # noqa: E402

FIXTURES = HERE.parent / "fixtures"
FLAPPING_VECTOR = "pos-accept-at-limit"


def frozen_verdicts() -> dict[bytes, tuple[str, str]]:
    manifest = json.loads((HERE.parent / "fixtures.json").read_text())
    return {(FIXTURES / entry["file"]).read_bytes(): (entry["id"], entry["expected"])
            for entry in manifest["fixtures"]}


class OneFlappingVector:
    """Correct in every way except that one vector's five runs disagree."""

    def __init__(self) -> None:
        self.verdicts = frozen_verdicts()

    def __call__(self, engine, module, raw):
        identifier, verdict = self.verdicts[raw]
        distinct = 2 if identifier == FLAPPING_VECTOR else 1
        return verdict, 21401, [1e-5] * runner.RUNS_PER_VECTOR, 17, distinct


def main() -> int:
    runner.measure = OneFlappingVector()
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        code = runner.main()
    errors = captured.getvalue()

    disagreements = re.findall(r"distinct \(verdict, fuel, pages\)", errors)
    verdicts = re.findall(r"expected \w+, got", errors)
    fresh = re.findall(r"fresh process", errors)
    controls = [line for line in errors.splitlines()
                if "corrupted artifact" in line or "zero fuel" in line]

    problems = []
    if code == 0:
        problems.append("the run passed while a vector's five observations disagreed")
    if len(disagreements) != 1:
        problems.append(f"{len(disagreements)} disagreement errors, expected exactly 1")
    if verdicts:
        problems.append(f"{len(verdicts)} verdict mismatches — the substitute measure "
                        "is not returning the frozen verdicts")
    if fresh:
        problems.append(f"{len(fresh)} fresh-process complaints — the run is failing "
                        "for a reason other than the one under test")
    if controls:
        problems.append(f"controls failed as well: {controls[:1]}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        print(errors, file=sys.stderr)
        return 1
    print("OK   one vector's five observations disagreed, and the run failed with "
          f"exactly that error (exit {code})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
