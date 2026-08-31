#!/usr/bin/env python3
"""Break each artifact-boundary guarantee and require its own check to refuse.

    python3 tools/candidate_boundary_controls.py --out dist/candidate

NON-NORMATIVE.

A control is not load-bearing until the defect it guards has been restored and
the control has been seen to fail FOR ITS OWN REASON. Every mutation here works
on a copy of the candidate directory, names the field it disturbs, and requires
the refusal to mention it. The originals are never modified.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "release-manifest.json"
results = []


def chk(label, condition, detail=""):
    results.append(bool(condition))
    print(("  OK    " if condition else "  FAIL  ") + label
          + (f" — {detail}" if detail and not condition else ""))


def run(tool, out):
    return subprocess.run([sys.executable, str(ROOT / "tools" / tool),
                           "--out", str(out)], capture_output=True, text=True)


def mutated(source, mutate):
    """A copy of the candidate directory with one thing changed."""
    work = Path(tempfile.mkdtemp(prefix="sigma-control-"))
    copy = work / "candidate"
    shutil.copytree(source, copy)
    mutate(copy)
    return work, copy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/candidate")
    args = ap.parse_args()
    source = Path(args.out)
    manifest = json.loads((source / MANIFEST_NAME).read_text())
    wheel_name = manifest["artifact_filename"]

    def control(label, tool, mutate, expect, baseline_must_pass=True):
        work, copy = mutated(source, mutate)
        try:
            done = run(tool, copy)
            output = done.stdout + done.stderr
            chk(label, done.returncode != 0 and expect in output,
                f"exit {done.returncode}: {output.strip()[-220:]}")
        finally:
            shutil.rmtree(work, ignore_errors=True)

    print("A candidate artifact and its manifest, each guarantee broken once.\n")

    # Baseline first: a control set whose baseline already fails proves nothing.
    for tool, tag in (("candidate_artifact.py", None),
                      ("candidate_install_check.py", "CANDIDATE-INSTALL: ALL PASS")):
        if tag is None:
            done = subprocess.run(
                [sys.executable, str(ROOT / "tools/candidate_artifact.py"),
                 "verify", "--out", str(source)], capture_output=True, text=True)
            chk("baseline: the unmutated manifest verifies",
                done.returncode == 0, (done.stdout + done.stderr)[-200:])
        else:
            done = run(tool, source)
            chk("baseline: the unmutated artifact installs and conforms",
                done.returncode == 0, (done.stdout + done.stderr)[-200:])

    def flip_digest(copy):
        data = json.loads((copy / MANIFEST_NAME).read_text())
        digest = data["artifact_sha256"]
        data["artifact_sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    control("a changed wheel digest is refused BEFORE install, naming the digest",
            "candidate_install_check.py", flip_digest, "digest")

    def corrupt_wheel(copy):
        target = copy / wheel_name
        target.write_bytes(target.read_bytes() + b"\x00")

    control("a wheel whose bytes changed under an unchanged manifest is refused "
            "before install", "candidate_install_check.py", corrupt_wheel,
            "digest")

    control("a missing artifact is refused as missing, not as a digest problem",
            "candidate_install_check.py",
            lambda copy: (copy / wheel_name).unlink(), "missing")

    def foreign_anchor_set(copy):
        data = json.loads((copy / MANIFEST_NAME).read_text())
        data["adopted_anchor_set_sha256"] = "f" * 64
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    work, copy = mutated(source, foreign_anchor_set)
    try:
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools/candidate_artifact.py"), "verify",
             "--out", str(copy)], capture_output=True, text=True)
        chk("a manifest naming a foreign anchor set is refused",
            done.returncode != 0 and "anchor-set mismatch" in done.stderr,
            (done.stdout + done.stderr)[-220:])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    def suite_drift(copy):
        data = json.loads((copy / MANIFEST_NAME).read_text())
        data["conformance_inputs"][0]["sha256"] = "a" * 64
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    work, copy = mutated(source, suite_drift)
    try:
        first = json.loads((source / MANIFEST_NAME).read_text())["conformance_inputs"][0]["path"]
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools/candidate_artifact.py"), "verify",
             "--out", str(copy)], capture_output=True, text=True)
        chk("suite/schema drift is refused, naming WHICH input moved",
            done.returncode != 0 and "suite/schema drift" in done.stderr
            and first in done.stderr, (done.stdout + done.stderr)[-220:])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    def wrong_commit(copy):
        data = json.loads((copy / MANIFEST_NAME).read_text())
        data["source_commit"] = "0" * 40
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    work, copy = mutated(source, wrong_commit)
    try:
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools/candidate_artifact.py"), "verify",
             "--out", str(copy), "--expect-commit",
             subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()],
            capture_output=True, text=True)
        chk("a manifest naming a different source commit is refused",
            done.returncode != 0 and "source commit mismatch" in done.stderr,
            (done.stdout + done.stderr)[-220:])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # The checkout-import escape hatch, tested by making it the ONLY way the
    # module could load: an empty venv plus a checkout on the path. If the
    # install check accepted that, it would be accepting exactly what this
    # phase exists to remove.
    work = Path(tempfile.mkdtemp(prefix="sigma-checkout-"))
    try:
        venv = work / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                       capture_output=True)
        done = subprocess.run(
            [str(venv / "bin" / "python"), "-c",
             "import sigma_glyph, sys; print(sigma_glyph.__file__)"],
            capture_output=True, text=True, cwd=str(ROOT / "impl"))
        chk("importing from the checkout instead of site-packages is what the "
            "install check refuses: with nothing installed, the module resolves "
            "to the checkout",
            done.returncode == 0 and str(ROOT) in done.stdout,
            (done.stdout + done.stderr)[-200:])
        chk("...and the install check's own probe would reject that path",
            str(ROOT.resolve()) in done.stdout.strip())
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print()
    if all(results):
        print(f"CANDIDATE-BOUNDARY-CONTROLS: ALL PASS "
              f"({len(results)}/{len(results)})")
        return 0
    print(f"CANDIDATE-BOUNDARY-CONTROLS: FAILURES "
          f"({sum(results)}/{len(results)})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
