#!/usr/bin/env python3
"""Run the checks, and only then write down that they passed.

    python3 tools/candidate_receipt.py --out dist/candidate \
        --receipt campaigns/phase-4a/candidate-receipt.json

NON-NORMATIVE.

WHY THIS IS NOT PART OF `build`
-------------------------------
The builder used to write "this artifact was built from this source commit and
CHECKED against these adopted specification inputs" into the manifest it
produced — while running no conformance at all. The sentence was true of the
process as a whole and false of the command that emitted it, which is the same
defect as a green check whose label outruns its predicate.

So `build` states build facts. This command runs the checks and writes a
separate receipt, and the receipt is the only file that says anything passed.

WHAT THE RECEIPT IS FOR
-----------------------
Committing it FREEZES the artifact digest. Without that, a consumer's CI
verifies a manifest against a wheel that the same builder produced moments
earlier, which shows only that a generator agrees with itself. A frozen receipt
lets a rebuild be compared with a digest that was reviewed, in a commit, before
the rebuild happened.

The receipt names the commit the artifact was built FROM. It cannot name its own
commit — writing it changes the tree — so `source_commit` is the build input and
the receipt lands in a later commit, exactly as a receipt should.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "release-manifest.json"

CHECKS = (
    ("manifest agrees with artifact and checkout", "candidate_artifact.py",
     ("verify",), "CANDIDATE-ARTIFACT: manifest agrees"),
    ("clean isolated install and conformance", "candidate_install_check.py",
     (), "CANDIDATE-INSTALL: ALL PASS"),
    ("artifact-boundary controls", "candidate_boundary_controls.py",
     (), "CANDIDATE-BOUNDARY-CONTROLS: ALL PASS"),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/candidate")
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args()

    out = Path(args.out).resolve()
    manifest = json.loads((out / MANIFEST_NAME).read_text())

    passed = []
    for label, tool, extra, tag in CHECKS:
        done = subprocess.run(  # noqa: S603 - fixed interpreter, fixed scripts
            [sys.executable, str(ROOT / "tools" / tool), *extra,
             "--out", str(out)], capture_output=True, text=True)
        output = done.stdout + done.stderr
        ok = done.returncode == 0 and tag in output
        print(("  OK    " if ok else "  FAIL  ") + label)
        if not ok:
            print(output.strip()[-400:], file=sys.stderr)
            print("CANDIDATE-RECEIPT: refusing to write a receipt for checks "
                  "that did not pass", file=sys.stderr)
            return 1
        passed.append({"check": label, "tool": tool, "verdict_line": tag})

    receipt = {
        "kind": "sigma-glyph/candidate-receipt@v0",
        "asserts": ("these checks were run against this artifact and passed. "
                    "The artifact digest below is FROZEN by committing this "
                    "file: a later rebuild that does not reproduce it has "
                    "changed something, and that is the point"),
        "artifact_filename": manifest["artifact_filename"],
        "artifact_sha256": manifest["artifact_sha256"],
        "source_commit": manifest["source_commit"],
        "software_version": manifest["software_version"],
        "adopted_bundle": manifest["adopted_bundle"],
        "adopted_anchor_set_sha256": manifest["adopted_anchor_set_sha256"],
        "build_pins": manifest["build_environment"]["build_pins"],
        "source_date_epoch": manifest["build_environment"]["source_date_epoch"],
        "checks_passed": passed,
        "does_not_assert": [
            "that the roster adopted this artifact",
            "that it reproduces on another OS, architecture or Python version",
            "anything about consumers other than the ones that cite it",
        ],
    }
    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"  artifact  {receipt['artifact_sha256']}")
    print(f"  built at  {receipt['source_commit']}")
    print(f"CANDIDATE-RECEIPT: {len(passed)} checks passed; frozen at "
          f"{receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
