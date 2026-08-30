#!/usr/bin/env python3
"""Break the conformance suite four ways and require four different failures.

    python3 tests/conformance_runner_selftest.py

`run_reference.py` used to call the two-value `eval_hash` and compare only the
result hash and the spend. `expected.outcome` was in the file, described as
informative, and checked by nobody — so when the suite recorded a classification
no engine had been asked to agree with, everything stayed green.

The runner now reads a `Receipt` and checks `exit`, `result_hash`, `atp_spent`
and the classification as four separate claims. This proves they are four: each
mutation below must fail its own check and no other. A control that fails for the
wrong reason is not a control, so the reason is asserted too.

`exit` and `outcome` are mutated independently on purpose. They agree on 32 of
the 33 evaluation vectors, which is exactly the condition under which one can
quietly stand in for the other.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "tests/spec_conformance/vectors.json"
RUNNER = ROOT / "tests/spec_conformance/run_reference.py"


def run_against(document):
    """Run the reference runner over a suite handed to it, not over the repo's."""
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary) / "vectors.json"
        staged.write_text(json.dumps(document))
        finished = subprocess.run([sys.executable, str(RUNNER), str(staged)],
                                  capture_output=True, text=True, cwd=ROOT)
    return finished.returncode, finished.stdout + finished.stderr


def failing_checks(output):
    return {line.split(None, 2)[1] + " " + line.split(None, 3)[2].split()[0]
            for line in output.splitlines() if line.startswith("FAIL ")}


def pick(document, predicate):
    for vector in document["vectors"]:
        if vector.get("kind") == "eval" and predicate(vector):
            return vector
    raise SystemExit("no evaluation vector matches; the suite changed shape")


def main():
    baseline = json.loads(SUITE.read_text())
    code, output = run_against(baseline)
    if code != 0:
        print("the suite does not pass as it stands; fix that before trusting "
              "any mutation result", file=sys.stderr)
        print(output, file=sys.stderr)
        return 1

    cases = []

    # 1. exit alone. Chosen where exit and outcome AGREE, so a runner that
    #    derived one from the other would report both failing, or neither.
    document = json.loads(SUITE.read_text())
    target = pick(document, lambda v: v["expected"]["exit"] == "normal_form"
                  and v["expected"]["outcome"] == "normal_form")
    target["expected"]["exit"] = "atp_exhausted"
    cases.append(("a declared exit changed", document, f"{target['id']} exit",
                  {f"{target['id']} outcome"}))

    # 2. outcome alone, on the one vector where they legitimately differ.
    document = json.loads(SUITE.read_text())
    target = pick(document, lambda v: v["expected"]["outcome"] == "invalid_object")
    target["expected"]["outcome"] = "normal_form"
    cases.append(("the classification changed where it differs from the exit",
                  document, f"{target['id']} outcome", {f"{target['id']} exit"}))

    # 3. result hash alone.
    document = json.loads(SUITE.read_text())
    target = pick(document, lambda v: True)
    digest = target["expected"]["result_hash"]
    target["expected"]["result_hash"] = ("0" if digest[0] != "0" else "1") + digest[1:]
    cases.append(("a declared result hash changed", document,
                  f"{target['id']} result_hash", set()))

    # 4. spend alone.
    document = json.loads(SUITE.read_text())
    target = pick(document, lambda v: v["expected"]["atp_spent"] > 0)
    target["expected"]["atp_spent"] += 1
    cases.append(("a declared spend changed", document,
                  f"{target['id']} atp_spent", set()))

    problems = []
    for name, document, must_fail, must_not_fail in cases:
        code, output = run_against(document)
        failed = failing_checks(output)
        if code == 0:
            problems.append(f"{name}: the runner still passed")
        elif must_fail not in failed:
            problems.append(f"{name}: expected {must_fail!r} to fail, got {sorted(failed)}")
        elif failed & must_not_fail:
            problems.append(f"{name}: also failed {sorted(failed & must_not_fail)}, "
                            f"so the checks are not independent")
        else:
            print(f"  OK    {name} → {must_fail} fails, and only it")
            continue
        print(f"  FAIL  {name}")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        print(f"CONFORMANCE-RUNNER-SELFTEST: {len(problems)} control(s) did not hold")
        return 1
    print("CONFORMANCE-RUNNER-SELFTEST: ALL PASS — exit, outcome, result_hash "
          "and atp_spent each fail on their own")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
