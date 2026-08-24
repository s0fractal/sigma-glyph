#!/usr/bin/env python3
"""Does the documented command reproduce the blob ADR-009 froze?

An anchor-set blob's identity is its SHA-256, and a threshold warrant signs that
digest. Two things therefore have to hold, and the first version of this file
checked them separately and never joined them: the command must emit the bytes
whose hash it prints, and those bytes must be the committed candidate. Checking
each alone let a green run print the CLI's digest for one release beside the
frozen digest of another and call that agreement.

The reproduction runs in a copied tree — `make-blob` refuses to see a section
whose header is labelled a candidate, so the header is promoted in the copy and
never in the repository.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "proposals/adr-009-v0.7.0-anchor-set.unsigned.json"
JURISDICTION = "a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a"
ANCESTOR = "d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5"
FROZEN = "1a4ebb99c56945d21ab0cef76e212b29205878d59e5b542724df8685f98d8111"


def reproduce(into: Path) -> subprocess.CompletedProcess:
    # The whole tools directory: anchor_governance imports its sibling
    # warrant_sig for the one signing-message construction.
    shutil.copytree(ROOT / "tools", into / "tools",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (into / "spec").mkdir()
    anchors = (ROOT / "spec/ANCHORS.txt").read_text()
    (into / "spec/ANCHORS.txt").write_text(
        re.sub(r'== (v[\d.]+) \(CANDIDATE[^)]*\) ==', r'== \1 ==', anchors))
    return subprocess.run(
        [sys.executable, str(into / "tools/anchor_governance.py"), "make-blob",
         "--jurisdiction", JURISDICTION, "--ancestor", ANCESTOR],
        capture_output=True, cwd=into)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        run = reproduce(Path(temporary))
    if run.returncode != 0:
        print(f"FAIL make-blob exited {run.returncode}: "
              f"{run.stderr.decode()[:300]}", file=sys.stderr)
        return 1

    emitted = hashlib.sha256(run.stdout).hexdigest()
    reported = run.stderr.decode().split()[-1].strip()
    committed = CANDIDATE.read_bytes() if CANDIDATE.exists() else None

    problems = []
    if emitted != reported:
        problems.append(f"the command reported {reported[:16]}… and emitted bytes "
                        f"hashing to {emitted[:16]}…, so redirecting its output "
                        "cannot reproduce the artifact it named")
    if run.stdout.endswith(b"\n"):
        problems.append("stdout ends with a newline; canonical bytes do not, and "
                        "appending one changes the identity a warrant signs")
    if committed is None:
        problems.append(f"{CANDIDATE.name} is missing, so there is nothing to "
                        "reproduce and this check has no subject")
    elif committed != run.stdout:
        problems.append(f"the reproduction is not byte-identical to the committed "
                        f"blob: {hashlib.sha256(committed).hexdigest()[:16]}… "
                        f"committed, {emitted[:16]}… reproduced")
    elif emitted != FROZEN:
        problems.append(f"both agree on {emitted[:16]}…, and ADR-009 froze "
                        f"{FROZEN[:16]}…")

    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        return 1
    print(f"ANCHOR-BLOB ROUNDTRIP: the documented command reproduces the committed "
          f"blob byte for byte, and all three digests are {FROZEN[:12]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
