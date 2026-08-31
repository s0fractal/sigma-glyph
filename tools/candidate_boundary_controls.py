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

# Named once. Sonar was right that four copies of each of these is four places
# for one of them to drift.
INSTALL_CHECK = "candidate_install_check.py"
ARTIFACT_TOOL = "candidate_artifact.py"

results = []


def chk(label, condition, detail=""):
    results.append(bool(condition))
    print(("  OK    " if condition else "  FAIL  ") + label
          + (f" — {detail}" if detail and not condition else ""))


def run(tool, out, *extra):
    """Run one of THIS repository's tools. The executable and the script are
    fixed here; only the directory under test varies."""
    if tool not in (INSTALL_CHECK, ARTIFACT_TOOL):
        raise ValueError(f"not a tool of this repository: {tool!r}")
    return subprocess.run(  # noqa: S603 - fixed interpreter, fixed script
        [sys.executable, str(ROOT / "tools" / tool), *extra, "--out", str(out)],
        capture_output=True, text=True)


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

    def control(label, tool, mutate, expect):
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
            done = run(ARTIFACT_TOOL, source, "verify")
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
            INSTALL_CHECK, flip_digest, "digest")

    def corrupt_wheel(copy):
        target = copy / wheel_name
        target.write_bytes(target.read_bytes() + b"\x00")

    control("a wheel whose bytes changed under an unchanged manifest is refused "
            "before install", INSTALL_CHECK, corrupt_wheel, "digest")

    control("a missing artifact is refused as missing, not as a digest problem",
            INSTALL_CHECK, lambda copy: (copy / wheel_name).unlink(), "missing")

    # THE CONTAINMENT BYPASS. A directory holding only a manifest, with
    # `artifact_filename` set to an absolute path to a wheel somewhere else,
    # used to verify AND install cleanly.
    def point_outside(copy):
        outside = copy.parent / "elsewhere"
        outside.mkdir(exist_ok=True)
        shutil.move(str(copy / wheel_name), str(outside / wheel_name))
        data = json.loads((copy / MANIFEST_NAME).read_text())
        data["artifact_filename"] = str(outside / wheel_name)
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    control("an artifact_filename that is an ABSOLUTE path outside the "
            "candidate directory is refused, not followed",
            INSTALL_CHECK, point_outside, "plain filename")

    def traverse(copy):
        data = json.loads((copy / MANIFEST_NAME).read_text())
        data["artifact_filename"] = f"../{wheel_name}"
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    control("an artifact_filename containing a traversal is refused",
            INSTALL_CHECK, traverse, "plain filename")

    def escaping_symlink(copy):
        outside = copy.parent / "escape"
        outside.mkdir(exist_ok=True)
        shutil.move(str(copy / wheel_name), str(outside / wheel_name))
        (copy / wheel_name).symlink_to(outside / wheel_name)

    control("a symlink escaping the candidate directory is refused, not "
            "followed", INSTALL_CHECK, escaping_symlink, "outside")

    # Every declared API member, broken one at a time.
    def drop_member(surface, member):
        def mutate(copy):
            data = json.loads((copy / MANIFEST_NAME).read_text())
            data["api_surfaces"][surface]["names"] = [
                name for name in data["api_surfaces"][surface]["names"]
                if name != member]
            (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))
        return mutate

    manifest_surfaces = json.loads((source / MANIFEST_NAME).read_text())["api_surfaces"]
    for surface, declared in sorted(manifest_surfaces.items()):
        for member in declared["names"]:
            work, copy = mutated(source, drop_member(surface, member))
            try:
                done = run(ARTIFACT_TOOL, copy, "verify")
                chk(f"dropping {member} from {surface} is refused",
                    done.returncode != 0 and "member list" in done.stderr,
                    (done.stdout + done.stderr)[-160:])
            finally:
                shutil.rmtree(work, ignore_errors=True)

    def foreign_anchor_set(copy):
        data = json.loads((copy / MANIFEST_NAME).read_text())
        data["adopted_anchor_set_sha256"] = "f" * 64
        (copy / MANIFEST_NAME).write_text(json.dumps(data, indent=2))

    work, copy = mutated(source, foreign_anchor_set)
    try:
        done = run(ARTIFACT_TOOL, copy, "verify")
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
        done = run(ARTIFACT_TOOL, copy, "verify")
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
        head = subprocess.run(  # noqa: S603 - fixed argv
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True).stdout.strip()
        done = run(ARTIFACT_TOOL, copy, "verify", "--expect-commit", head)
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
