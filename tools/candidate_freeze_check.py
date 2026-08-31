#!/usr/bin/env python3
"""Rebuild the artifact a committed receipt froze, and compare digests.

    python3 tools/candidate_freeze_check.py \
        --receipt campaigns/phase-4a/candidate-receipt.json

NON-NORMATIVE.

WHAT THIS ANSWERS
-----------------
A consumer that verifies a manifest against a wheel the same builder produced
moments earlier has learned that a generator agrees with itself. It has not
learned that the artifact is the reviewed one.

This rebuilds from the commit the receipt names, with the epoch and build pins
the receipt records, and requires the digest the receipt froze. A mismatch means
something changed — the source, the builder, the pinned backend, or the build
environment — and which of those it is worth knowing.

The rebuild happens in a detached `git worktree` at the receipt's
`source_commit`, so the current checkout is not disturbed and the commit being
built is unambiguous.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def under_repo(path, what):
    """A path argument, resolved and required to be inside this repository.

    Every subprocess below runs a script of this repository over a directory the
    caller names. Validating the directory here means the argument cannot point
    the tooling at something outside the tree it is describing, and it turns a
    confusing failure deep inside a build into one refusal with a reason.
    """
    resolved = Path(path).resolve()
    root = ROOT.resolve()
    if root != resolved and root not in resolved.parents:
        raise SystemExit(f"{what} must be inside {root}, got {resolved}")
    return resolved


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True,
        check=check)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args()

    receipt = json.loads(under_repo(args.receipt, "--receipt").read_text())
    commit = receipt["source_commit"]
    frozen = receipt["artifact_sha256"]
    print(f"  receipt froze {frozen}")
    print(f"  built from    {commit}")

    if git("cat-file", "-e", f"{commit}^{{commit}}", check=False).returncode != 0:
        print(f"FREEZE-CHECK: this checkout does not have {commit[:12]}, so the "
              f"frozen artifact cannot be rebuilt. Fetch it rather than "
              f"skipping: a freeze nobody can re-derive is a number in a file",
              file=sys.stderr)
        return 1

    work = Path(tempfile.mkdtemp(prefix="sigma-freeze-"))
    tree = work / "src"
    try:
        git("worktree", "add", "--detach", "--quiet", str(tree), commit)
        environment = {"SOURCE_DATE_EPOCH": str(receipt["source_date_epoch"])}
        done = subprocess.run(
            [sys.executable, str(tree / "tools/candidate_artifact.py"), "build",
             "--out", str(work / "out")],
            capture_output=True, text=True, cwd=str(tree),
            env={**__import__("os").environ, **environment})
        if done.returncode != 0:
            print(done.stdout + done.stderr, file=sys.stderr)
            print("FREEZE-CHECK: the rebuild itself failed", file=sys.stderr)
            return 1
        rebuilt = json.loads(
            (work / "out/release-manifest.json").read_text())
        print(f"  rebuilt       {rebuilt['artifact_sha256']}")
        if rebuilt["artifact_sha256"] != frozen:
            print(f"FREEZE-CHECK: the rebuild does NOT reproduce the frozen "
                  f"artifact.\n"
                  f"  frozen  {frozen}\n"
                  f"  rebuilt {rebuilt['artifact_sha256']}\n"
                  f"  build pins recorded: {receipt['build_pins']}\n"
                  f"  build pins used:     "
                  f"{rebuilt['build_environment']['build_pins']}\n"
                  f"  epoch recorded: {receipt['source_date_epoch']}, used: "
                  f"{rebuilt['build_environment']['source_date_epoch']}\n"
                  f"Something changed. Which one it is, is the useful part.",
                  file=sys.stderr)
            return 1
    finally:
        git("worktree", "remove", "--force", str(tree), check=False)
        shutil.rmtree(work, ignore_errors=True)

    print(f"FREEZE-CHECK: the rebuild reproduces the frozen artifact "
          f"{frozen[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
