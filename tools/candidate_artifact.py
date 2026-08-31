#!/usr/bin/env python3
"""Build a candidate Sigma-Glyph artifact and the manifest that describes it.

    python3 tools/candidate_artifact.py build   --out dist/candidate
    python3 tools/candidate_artifact.py verify  --out dist/candidate
    python3 tools/candidate_artifact.py selftest

NON-NORMATIVE. This changes no Book, suite, schema or anchor, and building an
artifact is not adopting one.

WHAT A CANDIDATE ARTIFACT IS
----------------------------
A wheel built from an exact source commit, named by its digest, and described by
a manifest that lives BESIDE it rather than inside it. The manifest asserts one
thing:

    this artifact was built from this source commit and checked against these
    adopted specification inputs

and specifically does NOT assert that the roster adopted the artifact. Adoption
is a threshold warrant over anchored bytes; a build is a build.

THE VERSION IS DELIBERATELY UNPUBLISHABLE
-----------------------------------------
`spec/VERSIONS.md` says the bundle number names an adopted set of bytes and is
not the software's version — so a wheel is not renumbered to `0.7.0` because the
adopted bundle is `v0.7.0`. Nor is it built as a bare `0.6.7`, which is a
published release: a second artifact carrying a published version with different
bytes is the confusion this whole phase exists to remove.

So the candidate carries a PEP 440 LOCAL VERSION — `0.6.7+phase4a.<commit>`.
PyPI rejects local versions outright, which makes the artifact structurally
unpublishable rather than merely unauthorised. `pyproject.toml` in the checkout
is never edited; the version is applied to a build copy.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The shape of the surface a consumer binds to. Not the package version: a
# consumer cares that `eval_receipt` exists and that a Receipt carries three
# named fields, not which release it came from.
API_VERSION = "book1-eval-receipt/1"
API_SURFACE = ("eval_receipt",)
RECEIPT_FIELDS = ("exit", "result_hash", "atp_spent")

MANIFEST_NAME = "release-manifest.json"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args, cwd=ROOT):
    done = subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True, check=True)
    return done.stdout.strip()


def source_commit():
    """The commit this artifact is built from. A dirty tree has no such commit."""
    dirty = git("status", "--porcelain")
    if dirty:
        raise SystemExit(
            "candidate_artifact: the working tree is dirty, so there is no "
            "commit this artifact would be built from. Commit or stash first:\n"
            + dirty)
    return git("rev-parse", "HEAD")


def adopted_inputs():
    """The adopted bundle, its anchor-set blob, and the anchored suites/schemas.

    Derived from the tree, never carried as a constant here: the anchor-set
    digest is found by CONTENT — the blob whose (path, anchor) pairs are exactly
    what `spec/ANCHORS.txt` lists for the newest release.
    """
    import re
    anchors = (ROOT / "spec/ANCHORS.txt").read_text()
    releases = re.findall(r"^== (\S+?) ==\s*$", anchors, re.M)
    if not releases:
        raise SystemExit("candidate_artifact: ANCHORS.txt names no release")
    bundle = releases[0]
    section = anchors.split(f"== {bundle} ==")[1].split("\n== ")[0]
    listed = re.findall(r"^([0-9a-f]{64})\s+(\S+)\s*$", section, re.M)
    if not listed:
        raise SystemExit(f"candidate_artifact: {bundle} lists no anchored file")

    wanted = {(path, anchor) for anchor, path in listed}
    anchor_set = None
    for blob in sorted((ROOT / ".warrants/blobs").glob("*")):
        if not blob.is_file():
            continue
        try:
            document = json.loads(blob.read_text())
        except (ValueError, OSError, UnicodeDecodeError):
            continue
        carried = {(entry.get("path"), entry.get("anchor"))
                   for entry in document.get("anchors", [])}
        if carried == wanted:
            anchor_set = blob.name
            break
    if anchor_set is None:
        raise SystemExit(
            f"candidate_artifact: no blob in .warrants/blobs carries exactly "
            f"the {bundle} anchor set, so the manifest could not name it")

    # A CLOSED list of (path, sha256, anchor). One aggregate digest would not
    # say which suite or schema moved, and there is more than one of each.
    inputs = []
    for anchor, path in sorted(listed, key=lambda pair: pair[1]):
        if "/spec_conformance/" in path or "/schemas/" in path:
            inputs.append({"path": path,
                           "sha256": sha256_file(ROOT / path),
                           "anchor": anchor})
    return bundle, anchor_set, inputs


def candidate_version(commit):
    """`<declared>+phase4a.<commit7>` — a PEP 440 local version."""
    import re
    declared = re.search(r'^version\s*=\s*"([^"]+)"',
                         (ROOT / "pyproject.toml").read_text(), re.M)
    if not declared:
        raise SystemExit("candidate_artifact: pyproject.toml declares no version")
    return f"{declared.group(1)}+phase4a.{commit[:7]}"


def build(out_dir):
    commit = source_commit()
    version = candidate_version(commit)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="sigma-candidate-"))
    try:
        # Build from a COPY of the tracked tree, with the version rewritten
        # there. The checkout's own pyproject keeps saying 0.6.7, so the
        # repository never disagrees with what is published.
        tracked = git("ls-files", "-z").split("\0")
        source = work / "src"
        for name in filter(None, tracked):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        project = source / "pyproject.toml"
        import re
        project.write_text(re.sub(r'^version\s*=\s*"[^"]+"',
                                  f'version = "{version}"',
                                  project.read_text(), count=1, flags=re.M))

        venv = work / "buildenv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                       capture_output=True)
        pip = venv / "bin" / "pip"
        subprocess.run([str(pip), "install", "--quiet", "build"], check=True,
                       capture_output=True)
        subprocess.run([str(venv / "bin" / "python"), "-m", "build", "--wheel",
                        "--outdir", str(work / "dist"), str(source)],
                       check=True, capture_output=True)

        wheels = sorted((work / "dist").glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit(f"candidate_artifact: expected one wheel, got {wheels}")
        wheel = out / wheels[0].name
        shutil.copy2(wheels[0], wheel)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    bundle, anchor_set, inputs = adopted_inputs()
    manifest = {
        "kind": "sigma-glyph/candidate-release-manifest@v0",
        "asserts": ("this artifact was built from this source commit and "
                    "checked against these adopted specification inputs. It "
                    "does NOT assert that the artifact was adopted by the "
                    "roster: adoption is a threshold warrant over anchored "
                    "bytes, and this is a build"),
        "artifact_filename": wheel.name,
        "artifact_sha256": sha256_file(wheel),
        "source_commit": commit,
        "software_version": candidate_version(commit),
        "software_version_is_unpublishable": (
            "PEP 440 local version. PyPI rejects local versions, so this "
            "artifact cannot be published even by accident"),
        "api_version": API_VERSION,
        "adopted_bundle": bundle,
        "adopted_anchor_set_sha256": anchor_set,
        "conformance_inputs": inputs,
        "build_environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
        },
        "reproducibility": {
            "measured": ("two clean builds of this commit are byte-identical "
                         "WHEN SOURCE_DATE_EPOCH is set, and differ when it is "
                         "not"),
            "what_differs_without_it": ("only the zip entry timestamps of "
                                        "dist-info/* — every member's bytes are "
                                        "identical. Recorded rather than "
                                        "smoothed over: 'reproducible' without "
                                        "naming the condition would be false"),
            "this_manifest_pins": ("one specific artifact, by digest. It does "
                                   "not claim that rebuilding reproduces it "
                                   "under an unspecified environment"),
        },
    }
    (out / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  wheel     {wheel.name}")
    print(f"  sha256    {manifest['artifact_sha256']}")
    print(f"  version   {manifest['software_version']}")
    print(f"  commit    {commit}")
    print(f"  bundle    {bundle}  anchor-set {anchor_set[:16]}…")
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    print(f"  epoch     {epoch if epoch else 'UNSET — this build is not '
                                            'byte-reproducible'}")
    print(f"CANDIDATE-ARTIFACT: built {wheel}")
    return 0


def verify(out_dir, expect_commit=None):
    """Check the manifest against the artifact and against this checkout."""
    out = Path(out_dir)
    manifest_path = out / MANIFEST_NAME
    if not manifest_path.is_file():
        print(f"CANDIDATE-ARTIFACT: no manifest at {manifest_path}",
              file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text())
    problems = []

    wheel = out / manifest["artifact_filename"]
    if not wheel.is_file():
        problems.append(f"missing artifact: the manifest names "
                        f"{manifest['artifact_filename']}, which is not here")
    else:
        actual = sha256_file(wheel)
        if actual != manifest["artifact_sha256"]:
            problems.append(f"artifact digest mismatch: manifest says "
                            f"{manifest['artifact_sha256'][:16]}…, the file is "
                            f"{actual[:16]}…")
        else:
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
            for module in ("sigma_glyph.py", "sigma_wave.py",
                           "sigma_federation.py"):
                if module not in names:
                    problems.append(f"the wheel does not ship {module}")

    bundle, anchor_set, inputs = adopted_inputs()
    if manifest.get("adopted_anchor_set_sha256") != anchor_set:
        problems.append(
            f"anchor-set mismatch: the manifest names "
            f"{str(manifest.get('adopted_anchor_set_sha256'))[:16]}…, this "
            f"checkout's adopted set is {anchor_set[:16]}…")
    if manifest.get("adopted_bundle") != bundle:
        problems.append(f"bundle mismatch: manifest {manifest.get('adopted_bundle')}, "
                        f"checkout {bundle}")

    recorded = {entry["path"]: entry for entry in manifest.get("conformance_inputs", [])}
    current = {entry["path"]: entry for entry in inputs}
    for path in sorted(set(recorded) | set(current)):
        if path not in recorded:
            problems.append(f"conformance input not in the manifest: {path}")
        elif path not in current:
            problems.append(f"manifest names an input this checkout does not "
                            f"anchor: {path}")
        elif recorded[path]["sha256"] != current[path]["sha256"]:
            problems.append(
                f"suite/schema drift: {path} was {recorded[path]['sha256'][:16]}…"
                f" when the manifest was written, is {current[path]['sha256'][:16]}… now")
        elif recorded[path]["anchor"] != current[path]["anchor"]:
            problems.append(f"anchor drift for {path}")

    if expect_commit and manifest.get("source_commit") != expect_commit:
        problems.append(f"source commit mismatch: manifest "
                        f"{str(manifest.get('source_commit'))[:12]}, expected "
                        f"{expect_commit[:12]}")

    for problem in problems:
        print(f"  FAIL  {problem}", file=sys.stderr)
    if problems:
        print(f"CANDIDATE-ARTIFACT: {len(problems)} problem(s)")
        return 1
    print(f"CANDIDATE-ARTIFACT: manifest agrees with the artifact and with "
          f"this checkout ({len(current)} conformance inputs)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("build", "verify", "selftest"))
    ap.add_argument("--out", default="dist/candidate")
    ap.add_argument("--expect-commit")
    args = ap.parse_args()
    if args.command == "build":
        return build(args.out)
    if args.command == "verify":
        return verify(args.out, args.expect_commit)
    from candidate_artifact_selftest import selftest
    return selftest(args.out)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
