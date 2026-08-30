#!/usr/bin/env python3
"""Run the Go tests and require exactly the tests we expect, all passing.

    python3 tools/go_test_gate.py

Called from `tools/test-all.sh` and from CI, so both gate on the same rule.

Three ways the obvious version fails, all of them met here:

1. **`go test ./... | grep -q '^ok'` passes on a package with no test functions
   at all.** `ok` reports a successful package, not a positive count. That is the
   defect this repository keeps finding — a check whose subject can quietly go
   empty — and it was written into the gate whose comment claimed to prevent it.
2. **Go caches results.** Two consecutive runs printed
   `ok ... (cached)`, so the gate proved nothing about *this* revision.
   `-count=1` disables it.
3. **A shell exit code alone cannot tell you a test was deleted.** CI checked
   only that, so removing a test would have made it greener.

So the expected set is CLOSED and written down. Removing a test fails the gate.
Adding one also fails it, which is the point: a new test is a deliberate change
to what is guaranteed, and it should cost one line here rather than appear
silently in a count nobody reads.

`impl-go/jcs_test.go` guards a Go/Python canonicalization split — a federation
consensus fork — and had never been executed by any gate before 2026-08-30. That
is the whole reason this file exists.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "impl-go"

# Keyed by PACKAGE, then by test. Not by test name alone: two packages can hold
# a test of the same name, and a name-keyed set answers "did something called
# TestAlpha run" instead of "did THIS test run". The first version of this file
# keyed `outcome` by (package, test), wrote a comment saying names could not
# collapse, and then compared `{name for _package, name in outcome}` -- throwing
# the package away one line later. A module with TestAlpha in two packages and
# one TestAlpha expected reported no problems.
EXPECTED = {
  "github.com/s0fractal/sigma-glyph/impl-go": {
      "TestNodeHashOfMatchesBookI":
          "Go's NodeHash against Book I's printed digests, nested cases included",
      "TestNodeHashOfRefusesUnhashableTerms":
          "a term with no bytes here has no identity, not an improvised key",
      "TestDerivedPinsFailClosedOnContradiction":
          "synonyms allowed, contradictory pins refused with digest and names",
      "TestAdmissionSpansFullPinsAndAliases":
        "admission sees every node-level source at once: an alias re-pinning a "
        "genesis node is refused, a synonym is allowed, sector coordinates stay "
        "out",
    "TestProfileIsClosedUnderDeclaredIdentity":
        "identity resolves within the profile handed in: declared hashes are "
        "honoured, labels bind once, unresolvable Pins and alias cycles are "
        "refused, and synonyms and long acyclic chains still pass",
    "TestStructuralPinRequiresALoadedProfile":
        "the profile is loaded once at startup; a query never builds it, and "
        "querying without one refuses instead of answering",
    "TestSameWavePinIsTypeSafe":
          "uint16(1) and \"1\" print alike and are not the same pin",
      "TestJCSLineSeparatorsRaw":
          "U+2028/U+2029 emitted raw, or Go and Python fork federation consensus",
      "TestJCSUnaffectedBodiesUnchanged":
          "the U+2028 fix did not disturb ordinary bodies: keys sorted, <&> not "
          "HTML-escaped, matching Python's json.dumps(ensure_ascii=False)",
  },
}


def pairs(expected):
    """{(package, test): why} from the nested table."""
    return {(package, test): why
            for package, tests in expected.items()
            for test, why in tests.items()}

# The closed set earned itself on its first run: `TestJCSUnaffectedBodiesUnchanged`
# was in the tree and in nobody's list of what Go guarantees -- not in the review
# that asked for this gate, and not in mine, because the command I read it from
# was truncated. A count would have said six and moved on.


def run(module):
    finished = subprocess.run(
        ["go", "test", "-count=1", "-json", "./..."],
        cwd=module, capture_output=True, text=True)
    events, malformed = [], []
    for line in finished.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            # Not skipped. An unreadable line could be an event this gate would
            # otherwise have acted on, and silently dropping it is how a gate
            # stops seeing the thing it gates.
            malformed.append(line)
    return finished, events, malformed


def evaluate(module, expected, report=True):
    """Problems with this module's tests against a closed expected set."""
    if not pairs(expected):
        return ["the expected set is empty, so this gate guarantees nothing"]
    finished, events, malformed = run(module)
    problems = []
    if malformed:
        problems.append(f"`go test -json` emitted {len(malformed)} line(s) that "
                        f"are not JSON; first: {malformed[0][:200]!r}")
    if not events:
        return problems + ["`go test -json` produced no events: "
                           + (finished.stdout[-400:] + finished.stderr[-400:]).strip()]

    # Keyed by (package, test). Two packages may hold a test of the same name,
    # and keying by name alone would collapse them -- one could vanish while the
    # other kept the gate green.
    outcome, cached = {}, False
    for event in events:
        name = event.get("Test")
        if name and "/" not in name and event.get("Action") in ("pass", "fail", "skip"):
            outcome[(event.get("Package", ""), name)] = event["Action"]
        if "(cached)" in (event.get("Output") or ""):
            cached = True
    if cached:
        problems.append("a cached result was reported; -count=1 should prevent it")

    want = pairs(expected)
    for key in sorted(set(want) - set(outcome)):
        problems.append(f"expected test did not run: {key[1]} in {key[0]} — "
                        f"{want[key]}")
    for key in sorted(set(outcome) - set(want)):
        problems.append(f"unexpected test {key[1]} in {key[0]}: add it to the "
                        f"expected set with a line saying what it guarantees")
    for key, action in sorted(outcome.items()):
        if key not in want:
            continue
        if action != "pass":
            problems.append(f"{key[1]} ({key[0]}): {action}")
        elif report:
            print(f"  OK    {key[1]}")

    if finished.returncode != 0 and not problems:
        problems.append(f"go test exited {finished.returncode} while every "
                        f"expected test passed — read the full output")
    return problems


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true",
                        help="prove this gate rejects what it claims to reject")
    if parser.parse_args(argv).selftest:
        return selftest()
    problems = evaluate(MODULE, EXPECTED)
    for problem in problems:
        print("  FAIL  " + problem, file=sys.stderr)
    if problems:
        print(f"\nGO-TEST-GATE: {len(problems)} problem(s)")
        return 1
    total = len(pairs(EXPECTED))
    print(f"\nGO-TEST-GATE: ALL PASS ({total}/{total} expected tests ran and "
          f"passed, and no others)")
    return 0


SELFTEST_MODULE = """module gate.selftest.invalid

go 1.21
"""

PASSING = """package probe

import "testing"

func TestAlpha(t *testing.T) {}
func TestBeta(t *testing.T)  {}
"""

ONE = "gate.selftest.invalid"


def selftest():
    """Build throwaway Go modules and require each rejection, for its own reason.

    The proof used to be a one-off run in a terminal, which means the next person
    to weaken this gate meets nothing. A gate whose negative controls live only in
    somebody's scrollback is exactly the shape of the defects it catches.

    Every control asserts the REASON it was rejected, not merely that something
    was. A control satisfied by any failure passes while the specific hole it
    guards is wide open -- which is how the package-collapse below survived a
    comment saying it could not happen.
    """
    expected = {ONE: {"TestAlpha": "a test that exists", "TestBeta": "another"}}
    single = {ONE: {"TestAlpha": "a test that exists"}}

    # (name, {relative path: source}, expected, required substring or None to pass)
    cases = [
        ("baseline: both expected tests run and pass",
         {"probe_test.go": PASSING}, expected, None),
        ("a missing expected test is rejected, by name",
         {"probe_test.go": PASSING.replace("func TestBeta(t *testing.T)  {}", "")},
         expected, "expected test did not run: TestBeta"),
        ("an unlisted test is rejected, by name",
         {"probe_test.go": PASSING + "\nfunc TestGamma(t *testing.T) {}\n"},
         expected, "unexpected test TestGamma"),
        ("a failing test is rejected, and named",
         {"probe_test.go": PASSING.replace(
             "func TestBeta(t *testing.T)  {}",
             'func TestBeta(t *testing.T) { t.Fatal("forced") }')},
         expected, "TestBeta"),
        ("a module with no tests at all is rejected",
         {"probe.go": "package probe\n"}, expected,
         "expected test did not run"),
        ("an empty expected set is rejected", {"probe_test.go": PASSING},
         {ONE: {}}, "guarantees nothing"),
        # The hole a comment claimed was closed: TestAlpha in TWO packages with
        # ONE expected. Keyed by name, this reported no problems at all.
        ("the same test name in two packages does not satisfy one expectation",
         {"a/probe_test.go": "package a\n\nimport \"testing\"\n\n"
                             "func TestAlpha(t *testing.T) {}\n",
          "b/probe_test.go": "package b\n\nimport \"testing\"\n\n"
                             "func TestAlpha(t *testing.T) {}\n"},
         single, "unexpected test TestAlpha in gate.selftest.invalid/"),
        ("restoration: the baseline still passes",
         {"probe_test.go": PASSING}, expected, None),
    ]

    problems = []
    for name, files, expect, required in cases:
        with tempfile.TemporaryDirectory() as temporary:
            module = Path(temporary)
            (module / "go.mod").write_text(SELFTEST_MODULE)
            for relative, source in files.items():
                target = module / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source)
            found = evaluate(module, expect, report=False)
        if required is None:
            ok, detail = not found, str(found)
        else:
            ok = any(required in problem for problem in found)
            detail = (f"expected a rejection mentioning {required!r}, got {found}")
        print(("  OK    " if ok else "  FAIL  ") + name
              + ("" if ok else f" — {detail}"))
        if not ok:
            problems.append(name)

    print()
    if problems:
        print(f"GO-TEST-GATE-SELFTEST: {len(problems)} control(s) did not hold")
        return 1
    print(f"GO-TEST-GATE-SELFTEST: ALL PASS ({len(cases)}/{len(cases)} controls, "
          f"each rejected for its own stated reason)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
