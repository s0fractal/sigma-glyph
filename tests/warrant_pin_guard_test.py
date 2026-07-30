#!/usr/bin/env python3
"""Regression: WARRANT_PIN extraction fails HARD on a duplicate pin line.

A 2026-07 fresh-context adversarial review (P1) showed tools/test-all.sh's
old inline extraction failing OPEN: `sed -n '...p'` prints EVERY matching
line, so two WARRANT_PIN: lines yielded a two-line value; the per-line
`grep -qE '^[0-9a-f]{40}$'` validator still matched; curl then rejected the
malformed URL and both network parity checks skipped as "not reachable" —
a forbidden ci.yml state misdiagnosed as a network problem.

This test drives tools/read_warrant_pin.sh over fixture ci.yml files in a
temp dir and asserts: duplicate → hard error naming the duplicate condition;
missing/malformed → hard error; single pin (bare, commented, quoted) → the
pin. Run: python3 tests/warrant_pin_guard_test.py
"""
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELPER = os.path.join(REPO, "tools", "read_warrant_pin.sh")
PIN = "3972427688730e114507dc6fa14808eff8458fb5"

failures = []


def check(name, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def run_helper(yml_text):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "ci.yml")
        with open(p, "w") as f:
            f.write(yml_text)
        r = subprocess.run(["bash", HELPER, p], capture_output=True, text=True)
    return r


def main():
    head = "name: ci\nenv:\n"

    # the reviewer's vector: a DUPLICATE pin line must be a hard, accurate error
    r = run_helper(head + f"  WARRANT_PIN: {PIN}\n  WARRANT_PIN: {PIN}\njobs: {{}}\n")
    check("duplicate pin fails hard (exit != 0)", r.returncode != 0)
    check("duplicate pin error names the duplicate condition (not network)",
          "duplicate WARRANT_PIN" in r.stderr and "2 WARRANT_PIN" in r.stderr,
          r.stderr.strip())

    # missing pin: hard error
    r = run_helper(head + "jobs: {}\n")
    check("missing pin fails hard", r.returncode != 0 and "0 WARRANT_PIN" in r.stderr,
          r.stderr.strip())

    # malformed pin (39 hex): hard error
    r = run_helper(head + f"  WARRANT_PIN: {PIN[:-1]}\njobs: {{}}\n")
    check("39-hex pin fails hard", r.returncode != 0 and "not a 40-hex" in r.stderr,
          r.stderr.strip())

    # single well-formed pin, in the YAML forms real CI reads fine
    for name, line in [
            ("bare pin extracts", f"  WARRANT_PIN: {PIN}"),
            ("pin with trailing comment extracts", f"  WARRANT_PIN: {PIN}  # governance-pinned"),
            ("double-quoted pin extracts", f'  WARRANT_PIN: "{PIN}"'),
            ("single-quoted pin extracts", f"  WARRANT_PIN: '{PIN}'")]:
        r = run_helper(head + line + "\njobs: {}\n")
        check(name, r.returncode == 0 and r.stdout.strip() == PIN,
              f"rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip()!r}")

    # and the real ci.yml still yields a single valid pin
    r = subprocess.run(["bash", HELPER], capture_output=True, text=True, cwd=REPO)
    ok = r.returncode == 0 and len(r.stdout.strip()) == 40
    check("real .github/workflows/ci.yml yields one 40-hex pin", ok,
          f"rc={r.returncode} out={r.stdout.strip()!r}")

    if failures:
        print(f"\nPIN-GUARD: {len(failures)} FAILED")
        return 1
    print("\nPIN-GUARD: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
