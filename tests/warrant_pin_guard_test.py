#!/usr/bin/env python3
"""Regression: WARRANT_PIN extraction fails HARD on a duplicate pin line.

A 2026-07 fresh-context adversarial review (P1) showed tools/test-all.sh's
old inline extraction failing OPEN: `sed -n '...p'` prints EVERY matching
line, so two WARRANT_PIN: lines yielded a two-line value; the per-line
`grep -qE '^[0-9a-f]{40}$'` validator still matched; curl then rejected the
malformed URL and both network parity checks skipped as "not reachable" —
a forbidden ci.yml state misdiagnosed as a network problem.

A second round-2 review then found three more, all in the same extraction:

  F9  a duplicate pin PASSED (rc=0) when ci.yml has no final newline: the
      count came from `sed | wc -l`, which counts NEWLINES, so N pin lines
      counted as N−1 — and `tr -d '[:space:]'` spliced the two values into
      one. Fixed by counting with `grep -c`, which counts an unterminated
      last line.
  F10 the same root cause the other way: one VALID pin with no final newline
      reported "has 0 WARRANT_PIN: lines" and hard-failed the matrix with a
      wrong message.
  F11 `tr -d '[:space:]'` also deleted INTERNAL whitespace, so
      `39724276887 30e114507…` was accepted as a 40-hex pin, and
      `${matches%%#*}` truncated the value at a `#` with no preceding space,
      which YAML keeps in the value. Both let the local matrix validate a
      DIFFERENT commit than CI resolves.

This test drives tools/read_warrant_pin.sh over fixture ci.yml files in a
temp dir and asserts: duplicate → hard error naming the duplicate condition
(with AND without a final newline); missing/malformed → hard error; internal
whitespace and a no-space `#` → hard error, never a truncated/spliced pin;
single pin (bare, commented, quoted, and with no final newline) → the pin.
Run: python3 tests/warrant_pin_guard_test.py
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

    # F9: the duplicate must still be caught with NO final newline (the old
    # `sed | wc -l` counted newlines, so two pin lines counted as one and the
    # spliced value validated — rc=0, a forbidden ci.yml state accepted)
    r = run_helper(head + f"  WARRANT_PIN:\n  WARRANT_PIN: {PIN}")
    check("F9 duplicate pin without a final newline fails hard",
          r.returncode != 0 and "2 WARRANT_PIN" in r.stderr,
          f"rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip()!r}")
    r = run_helper(head + f"  WARRANT_PIN: {PIN}\n  WARRANT_PIN: {PIN}")
    check("F9 two full pins without a final newline fail hard",
          r.returncode != 0 and "duplicate WARRANT_PIN" in r.stderr,
          f"rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip()!r}")

    # F11: a value with INTERNAL whitespace must never be spliced into a pin,
    # and a `#` with no preceding whitespace is part of the YAML value
    r = run_helper(head + f"  WARRANT_PIN: {PIN[:11]} {PIN[11:]}\n")
    check("F11 internally-spaced value is not accepted as a 40-hex pin",
          r.returncode != 0 and "not a 40-hex" in r.stderr,
          f"rc={r.returncode} out={r.stdout.strip()!r}")
    r = run_helper(head + f"  WARRANT_PIN: {PIN}#notacomment\n")
    check("F11 `#` without preceding whitespace stays in the value (no truncation)",
          r.returncode != 0 and "not a 40-hex" in r.stderr,
          f"rc={r.returncode} out={r.stdout.strip()!r}")

    # single well-formed pin, in the YAML forms real CI reads fine
    for name, line in [
            ("bare pin extracts", f"  WARRANT_PIN: {PIN}"),
            ("pin with trailing comment extracts", f"  WARRANT_PIN: {PIN}  # governance-pinned"),
            ("double-quoted pin extracts", f'  WARRANT_PIN: "{PIN}"'),
            ("single-quoted pin extracts", f"  WARRANT_PIN: '{PIN}'")]:
        r = run_helper(head + line + "\njobs: {}\n")
        check(name, r.returncode == 0 and r.stdout.strip() == PIN,
              f"rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip()!r}")

    # F10: one valid pin, no final newline — used to report "has 0
    # WARRANT_PIN: lines" and hard-fail the matrix with a wrong message
    r = run_helper(head + f"  WARRANT_PIN: {PIN}")
    check("F10 single valid pin without a final newline extracts",
          r.returncode == 0 and r.stdout.strip() == PIN,
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
