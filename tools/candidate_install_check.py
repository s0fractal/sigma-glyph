#!/usr/bin/env python3
"""Install a candidate artifact into a clean environment and prove the boundary.

    python3 tools/candidate_install_check.py --out dist/candidate
    python3 tools/candidate_install_check.py --out dist/candidate --selftest

NON-NORMATIVE.

The claim under test is narrow and entirely internal:

    this specific artifact, identified by digest, can be installed into a clean
    environment and used there, with no Sigma source checkout reachable

Not portability. Not independent implementability. Not that anyone else has ever
installed it. One artifact, one clean environment, on this machine or this
runner.

The digest is verified BEFORE the wheel is installed, because verifying it after
would be verifying a file that had already been allowed to run code.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "release-manifest.json"
FAILED = "CANDIDATE-INSTALL: FAILURES"

# The old escape hatch this phase exists to close. Pointed at a path that cannot
# exist, so a fallback cannot fire without being noticed.
DEAD_PATH = "/nonexistent/sigma-glyph--must-not-be-found"

results = []


def chk(label, condition, detail=""):
    results.append(bool(condition))
    print(("  OK    " if condition else "  FAIL  ") + label
          + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install(wheel, work):
    """A clean venv with the wheel installed as a FILE, and nothing else."""
    venv = Path(work) / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                   capture_output=True)
    subprocess.run([str(venv / "bin" / "pip"), "install", "--quiet",
                    "--no-deps", str(wheel)], check=True, capture_output=True)
    return venv


def run_isolated(venv, work, code):
    """Run `code` with the checkout unreachable and the old override poisoned.

    `cwd` is outside the checkout, PYTHONPATH is emptied, and the historical
    `SIGMA_GLYPH` override points at a path that cannot exist — so a fallback to
    a source tree cannot succeed quietly. If the module still imports, it came
    from site-packages.
    """
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["SIGMA_GLYPH"] = DEAD_PATH
    environment["PYTHONNOUSERSITE"] = "1"
    return subprocess.run([str(venv / "bin" / "python"), "-c", code],
                          capture_output=True, text=True, cwd=str(work),
                          env=environment)


def check(out_dir):
    # Absolute: the release-surface check runs from a temp cwd, and a
    # relative --out resolved against it produced 'no such wheel' for a
    # wheel that was plainly there.
    out = Path(out_dir).resolve()
    manifest_path = out / MANIFEST_NAME
    if not manifest_path.is_file():
        print(f"CANDIDATE-INSTALL: no manifest at {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text())

    # 0. The artifact must be INSIDE the candidate directory. `artifact_filename`
    #    was used as given, so a manifest naming an absolute path to a wheel
    #    elsewhere verified and installed cleanly, and "the manifest sits beside
    #    the artifact" was a habit rather than an invariant.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from candidate_artifact import contained
    wheel, refusal = contained(out, manifest.get("artifact_filename"),
                               "artifact_filename")
    if not chk("the artifact is named as a plain filename inside the candidate "
               "directory", refusal is None, refusal or ""):
        print(FAILED)
        return 1

    # 1. Digest before install. The order is the point.
    if not chk("the artifact named by the manifest is present", wheel.is_file(),
               f"{wheel} is missing"):
        print(FAILED)
        return 1
    actual = sha256_file(wheel)
    if not chk("its digest matches the manifest BEFORE anything is installed",
               actual == manifest["artifact_sha256"],
               f"{actual[:16]}… vs {manifest['artifact_sha256'][:16]}…"):
        print("CANDIDATE-INSTALL: refusing to install an artifact whose digest "
              "does not match", file=sys.stderr)
        print(FAILED)
        return 1

    work = Path(tempfile.mkdtemp(prefix="sigma-install-"))
    try:
        venv = install(wheel, work)

        wanted = sorted({name for surface in manifest["api_surfaces"].values()
                         for name in surface["names"]})
        probe = ("import json, sigma_glyph as m;"
                 f"names = {wanted!r};"
                 "print(json.dumps({'file': m.__file__,"
                 " 'present': [n for n in names if hasattr(m, n)],"
                 " 'sys_path': __import__('sys').path}))")
        done = run_isolated(venv, work, probe)
        if not chk("the module imports in the clean environment",
                   done.returncode == 0, done.stderr.strip()[:200]):
            print(FAILED)
            return 1
        info = json.loads(done.stdout.strip().splitlines()[-1])
        module_file = Path(info["file"]).resolve()
        print(f"        module.__file__ = {module_file}")

        chk("it is imported from the venv's site-packages",
            str(venv.resolve()) in str(module_file), str(module_file))
        chk("and NOT from this checkout",
            str(ROOT.resolve()) not in str(module_file), str(module_file))
        chk("no entry of the interpreter's sys.path is inside this checkout",
            not any(str(ROOT.resolve()) in entry for entry in info["sys_path"]),
            str([e for e in info["sys_path"] if str(ROOT.resolve()) in e]))
        # Every member of every surface the manifest declares, one by one.
        for surface, declared in sorted(manifest["api_surfaces"].items()):
            missing = [name for name in declared["names"]
                       if name not in info["present"]]
            chk(f"every member of {surface} is present in the installed module",
                not missing, f"missing: {', '.join(missing)}")

        # 2. The conformance surface, run against the INSTALLED artifact.
        surface = subprocess.run(
            [sys.executable, str(ROOT / "tools/check_release_surface.py"),
             "--wheel", str(wheel), "--bin", str(venv / "bin")],
            capture_output=True, text=True, cwd=str(work))
        tag = "RELEASE SURFACE: ALL PASS"
        chk("the release-surface conformance passes against the installed "
            "artifact", tag in surface.stdout,
            (surface.stdout + surface.stderr).strip()[-300:])
        for line in surface.stdout.splitlines():
            if line.startswith("RELEASE SURFACE"):
                print(f"        {line[:150]}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print()
    if all(results):
        print(f"CANDIDATE-INSTALL: ALL PASS ({len(results)}/{len(results)}) — "
              f"one artifact, one clean environment, no checkout reachable")
        return 0
    print(f"{FAILED} ({sum(results)}/{len(results)})")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/candidate")
    args = ap.parse_args()
    return check(args.out)


if __name__ == "__main__":
    raise SystemExit(main())
