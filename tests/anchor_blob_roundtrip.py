#!/usr/bin/env python3
"""Does `make-blob` emit the bytes whose hash it reports?

An anchor-set blob's identity is its SHA-256, and a threshold warrant signs that
digest. So the documented way to obtain the blob — redirect the command's output —
must produce exactly the bytes the command hashed. It did not: stdout carried a
trailing newline that the digest did not cover, so `make-blob > set.json` wrote a
file whose hash was not the hash the same run had just printed.

That is a defect nobody notices by reading, because both numbers look right on
their own. This runs the real CLI, hashes what came out of it, and requires the
two to agree.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JURISDICTION = "a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a"


def main() -> int:
    run = subprocess.run(
        [sys.executable, "tools/anchor_governance.py", "make-blob",
         "--jurisdiction", JURISDICTION], capture_output=True, cwd=ROOT)
    if run.returncode != 0:
        print(f"FAIL make-blob exited {run.returncode}: "
              f"{run.stderr.decode()[:300]}", file=sys.stderr)
        return 1

    emitted = hashlib.sha256(run.stdout).hexdigest()
    reported = run.stderr.decode().split()[-1].strip()
    problems = []
    if emitted != reported:
        problems.append(f"the command reported {reported[:16]}… and emitted bytes "
                        f"hashing to {emitted[:16]}…, so redirecting its output "
                        "cannot reproduce the artifact it named")
    if run.stdout.endswith(b"\n"):
        problems.append("stdout ends with a newline; canonical bytes do not, and "
                        "appending one changes the identity a warrant signs")

    # And the candidate the ADR froze, when it is present in this tree.
    candidate = ROOT / "proposals/adr-009-v0.6.8-anchor-set.unsigned.json"
    if candidate.exists():
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        expected = "d993116bb4e2bd8738a2c45c6c7a962669078227a325731efd3aa63648b2a008"
        if digest != expected:
            problems.append(f"the committed candidate blob hashes to {digest[:16]}…, "
                            f"and ADR-009 froze {expected[:16]}…")
        if candidate.read_bytes().endswith(b"\n"):
            problems.append("the committed candidate blob ends with a newline")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print(f"ANCHOR-BLOB ROUNDTRIP: the CLI's own output hashes to the digest it "
          f"reports ({reported[:12]}…), and the frozen candidate blob still "
          "hashes to what ADR-009 recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
