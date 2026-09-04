#!/usr/bin/env python3
"""One derived view: which bytes carry which version label, and what stands behind each.

    python3 tools/evidence_view.py --warrant /absolute/path/to/warrant   # JSON on stdout
    python3 tools/evidence_view.py                                      # Sigma half only

NON-NORMATIVE. This projects existing owners into one machine-readable document.
It adopts, releases, registers, admits and publishes nothing, and it keeps no
table of its own: every value below is read from the file that owns it, or
computed from bytes, on the run that prints it.

FOUR SURFACES THAT MOVE SEPARATELY
----------------------------------
  sigma.protocol       the adopted bundle -- spec/ANCHORS.txt, its anchors
                       recomputed by tools/verify_anchors.py, the anchor-set
                       blob in .warrants, and the adoption verdict of
                       tools/anchor_governance.py under an OUT-OF-BAND trust
                       anchor (which only a Warrant operand can supply)
  sigma.distribution   the published package -- pyproject.toml, the git tag it
                       implies, and the evaluator bytes at that tag
  sigma.evaluators     the Book I module on this tree and the one at the
                       distribution tag, each by digest
  sigma.candidate      the frozen phase-4a receipt, referenced, not re-run
  warrant              Warrant-OWNED runtime selection: which `ski@vN` tag is
                       admitted, which is reserved, and which evaluator bytes
                       each admitted tag pins -- read from the operand's
                       trust/ski-runtime-evaluators.json and SPEC.md section 13.1

Book I semantics (the `**Version:**` header of the Book) is a fifth number and
is reported beside the bundle, never in place of it: spec/VERSIONS.md says what
each number governs.

WHAT A DIGEST PROVES
--------------------
Identity. Two equal digests are the same bytes; nothing more. A digest here does
not say the bytes conform, were adopted, were released, or are a runtime.
Conformance is the result of a verifier run; adoption is a threshold warrant;
a runtime tag is a Warrant registration. Where the view states one of those, it
names the tool whose result it reuses, and where it could not run that tool the
status is `unavailable` or the relation is `unchecked` -- never `holds`.

THE WARRANT OPERAND IS EXPLICIT
-------------------------------
Cross-repository data is read only from the checkout named by --warrant. With
no operand the Warrant-owned sections are typed unavailable; the view never
looks for a sibling directory, never reads $WARRANT, $SIGMA_GLYPH or $SIBLING,
and passes none of them to the tools it runs. An explicit operand that is not a
Warrant checkout is refused (exit 2), not degraded. The operand's revision is
reported as a local observation and constrains nothing.

STATUSES ARE NARROW
-------------------
A tag is `admitted_pinned` only when the SPEC table says `current`, the record
binds one module, and that module's bytes hash to the pin. Every other case has
its own name (reserved_no_evaluator, admitted_pin_MISMATCH, admitted_module_
MISSING, admitted_UNBOUND, record_spec_DISAGREE, record_only_UNREGISTERED) and
carries no identity credit. There is no top-level ok/verdict field: the summary
counts relations, and `credit_problems` refuses a view that widens any of this.

EXIT STATUS
    0  the view was printed and every relation that could be checked holds
    1  the view was printed and at least one relation FAILS (reasons on stderr)
    2  refused before printing anything (bad operand, or a source this view
       reads unconditionally is missing from the tree)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import candidate_artifact as ca  # noqa: E402
import version_check as vc  # noqa: E402

KIND = "sigma-glyph/evidence-view@v0"
ANCHORS = "spec/ANCHORS.txt"
LIVE_EVALUATOR = "impl/sigma_glyph.py"
BOOK_I = "spec/book-1-truth.md"
RECEIPT = "campaigns/phase-4a/candidate-receipt.json"
RECEIPT_KIND = "sigma-glyph/candidate-receipt@v0"
RECEIPT_FIELDS = ("artifact_filename", "artifact_sha256", "source_commit",
                  "software_version", "adopted_bundle",
                  "adopted_anchor_set_sha256", "checks_passed")
RUNTIME_RECORD = "trust/ski-runtime-evaluators.json"
RUNTIME_RECORD_KIND = "warrant/ski-runtime-evaluators@v0"
TRUST_ANCHOR = "trust/sigma-glyph-anchor-trust.json"
WARRANT_MARKERS = ("SPEC.md", "impl/warrant.py")

# Development and cross-repository overrides that other tools read. None is an
# operand of this view, and none reaches a subprocess it starts.
AMBIENT = ("SIGMA_GLYPH", "WARRANT", "WARRANT_PY", "WARRANT_POSITIONAL",
           "WARRANT_SIGMA_DIFFERENTIAL", "WARRANT_SKI_MAX_ATP", "SIBLING",
           "X1_SIBLING_REF")

HOLDS, FAILS, UNCHECKED = "holds", "FAILS", "unchecked"
ADMITTED = "admitted_pinned"
TAG_STATUSES = frozenset({
    ADMITTED, "reserved_no_evaluator", "admitted_pin_MISMATCH",
    "admitted_module_MISSING", "admitted_UNBOUND", "record_spec_DISAGREE",
    "record_only_UNREGISTERED"})
NO_BADGE_KEYS = ("ok", "verdict", "all_pass", "status", "passed", "green")
IDENTITY_NA = {"status": "not_applicable",
               "reason": "identity is stated only for an admitted tag whose "
                         "one bound module hashes to its pin"}


# Read unconditionally on every run. A view that reports on bytes it could not
# read is worse than no view, and a traceback is not a typed answer, so their
# absence is refused by name before anything is printed.
REQUIRED_SOURCES = (ANCHORS, LIVE_EVALUATOR, "pyproject.toml")


class Refused(Exception):
    """A bad operand or an unreadable tree. Nothing reaches stdout for one."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def scrubbed_env() -> dict:
    return {k: v for k, v in os.environ.items() if k not in AMBIENT}


def run(argv, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                          env=scrubbed_env(), check=False)


def git_bytes(repo: Path, *args: str):
    """(returncode, stdout bytes) of one git command, or (None, b"") when
    `repo` is not itself the top of a git checkout -- a temp copy parked inside
    some other repository must not report that repository's HEAD as its own."""
    try:
        top = subprocess.run(["git", "-C", str(repo), "rev-parse",
                              "--show-toplevel"], capture_output=True,
                             env=scrubbed_env(), check=False)
    except OSError:
        return None, b""
    if top.returncode != 0 or Path(top.stdout.decode().strip()).resolve() != repo.resolve():
        return None, b""
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          env=scrubbed_env(), check=False)
    return done.returncode, done.stdout


def observed_revision(repo: Path) -> dict:
    rc, head = git_bytes(repo, "rev-parse", "HEAD")
    if rc != 0:
        return {"status": "unavailable",
                "reason": "not the top of a git checkout, or git unavailable"}
    _, dirty = git_bytes(repo, "status", "--porcelain", "--untracked-files=no")
    return {"status": "observed", "commit": head.decode().strip(),
            "tracked_tree": "dirty" if dirty.strip() else "clean",
            "note": "a local observation of this checkout, not a pinned artifact"}


def version_header(text: str) -> str:
    found = re.search(r'^\*\*Version:\*\* *(\d+(?:\.\d+)*)', text, re.M)
    return found.group(1) if found else ""


class Relations:
    def __init__(self):
        self.items = []

    def add(self, name: str, status: str, detail: str = ""):
        entry = {"relation": name, "status": status}
        if detail:
            entry["detail"] = detail
        self.items.append(entry)


# ---------------------------------------------------------------- sigma half

def anchors_section(root: Path, rel: Relations):
    text = (root / ANCHORS).read_text()
    headings = re.findall(r"^== (\S+)(.*?) ==\s*$", text, re.M)
    first = headings[0][0] if headings else ""
    listed = {}
    if headings:
        section = text.split(f"== {first}{headings[0][1]} ==", 1)[1].split("\n== ")[0]
        listed = {path: anchor for anchor, path in
                  re.findall(r"^([0-9a-f]{64})\s+(\S+)\s*$", section, re.M)}
    done = run([sys.executable, "tools/verify_anchors.py"], cwd=root)
    files = []
    for line in done.stdout.splitlines():
        found = re.match(r"^(OK|FAIL)\s+(\S+)\s+([0-9a-f]{64})$", line.strip())
        if found:
            status, path, got = found.groups()
            files.append({"path": path, "listed": listed.get(path),
                          "recomputed": got,
                          "status": "match" if status == "OK" else "MISMATCH"})
    lines = done.stdout.strip().splitlines()
    verdict = lines[-1] if lines else ""
    ok = (done.returncode == 0 and verdict == "anchors verified" and files
          and all(f["status"] == "match" for f in files)
          and {f["path"] for f in files} == set(listed))
    rel.add("the anchors of the first ANCHORS.txt section recompute from the "
            "bytes on this tree (tools/verify_anchors.py)",
            HOLDS if ok else FAILS,
            "" if ok else "; ".join(f["path"] for f in files
                                    if f["status"] != "match") or verdict)
    return {"tool": "tools/verify_anchors.py", "section_verified": first,
            "verdict": verdict, "files": files,
            "formula": "NodeHash(LITERAL, atom=SHA-256(document_bytes))"}, first


def protocol_section(root: Path, warrant: Path | None, rel: Relations):
    anchors, first = anchors_section(root, rel)
    top = vc.top_bundle()
    rel.add("the first ANCHORS.txt section is the adopted bundle (a candidate "
            "section above the history is not adopted)",
            HOLDS if top and first == top else FAILS,
            f"first section {first!r}, adopted bundle {top!r}")
    anchor_set = None
    try:
        bundle, anchor_set, _inputs = ca.adopted_inputs()
    except SystemExit as refusal:
        rel.add("one blob in .warrants/blobs carries exactly the adopted anchor "
                "set", FAILS, str(refusal))
    else:
        rel.add("one blob in .warrants/blobs carries exactly the adopted anchor "
                "set", HOLDS if bundle == top else FAILS,
                f"blob names {bundle!r}, adopted bundle {top!r}")
        if bundle != top:
            anchor_set = None

    adoption = adoption_section(root, warrant, top, rel)
    books = {name: vc.book_version(path) for name, path in vc.VERSIONED.items()}
    return {
        "owner": ANCHORS,
        "adopted_bundle": top,
        "book_versions": books,
        "anchor_set_sha256": anchor_set,
        "anchors": anchors,
        "adoption": adoption,
        "note": ("a bundle heading is a governance label over anchored bytes: "
                 "not a git tag, not a release, not a wheel, not a runtime tag"),
    }, top, anchor_set


def adoption_section(root: Path, warrant: Path | None, top: str, rel: Relations):
    name = ("the adopted bundle is AUTHORIZED under the out-of-band trust "
            "anchor (tools/anchor_governance.py status --trust-config)")
    if warrant is None:
        rel.add(name, UNCHECKED, "no --warrant operand carries a trust anchor")
        return {"status": "unavailable",
                "reason": "authority is a fact of the out-of-band trust anchor, "
                          "which lives in the Warrant checkout; none was named"}
    trust = warrant / TRUST_ANCHOR
    if not trust.is_file():
        rel.add(name, UNCHECKED, f"operand carries no {TRUST_ANCHOR}")
        return {"status": "unavailable",
                "reason": f"the operand revision carries no {TRUST_ANCHOR}"}
    done = run([sys.executable, "tools/anchor_governance.py", "status",
                "--trust-config", str(trust)], cwd=root)
    line = next((l.strip() for l in done.stdout.splitlines()
                 if l.split() and l.split()[0] == top), "")
    rest = line[len(top):].strip() if line else ""
    authorized = rest.startswith("AUTHORIZED")
    rel.add(name, HOLDS if authorized else FAILS,
            line or f"no status line for {top}: {done.stdout.strip()[-200:]}")
    return {"status": "authorized" if authorized else "not_authorized",
            "tool": "tools/anchor_governance.py status --trust-config",
            "trust_anchor": {"path": TRUST_ANCHOR, "sha256": sha256_file(trust),
                             "read_from": "warrant operand"},
            "verdict_line": line,
            "note": ("a threshold warrant over anchored bytes, replayed under the "
                     "operand's trust anchor; adoption is not a release")}


def distribution_section(root: Path):
    version = vc.pyproject_version()
    tag = f"v{version}" if version else ""
    tagged = {"status": "unavailable", "tag": tag,
              "reason": f"tag {tag!r} is not in this clone (shallow or tagless "
                        "checkout, or no checkout), so its bytes cannot be read"}
    rc, out = git_bytes(root, "rev-parse", "--verify", "--quiet",
                        f"refs/tags/{tag}^{{commit}}") if tag else (None, b"")
    if rc == 0:
        commit = out.decode().strip()
        rc_mod, module = git_bytes(root, "cat-file", "blob", f"{tag}:{LIVE_EVALUATOR}")
        rc_book, book = git_bytes(root, "cat-file", "blob", f"{tag}:{BOOK_I}")
        if rc_mod == 0:
            tagged = {"status": "read_from_git", "tag": tag, "commit": commit,
                      "path": LIVE_EVALUATOR, "sha256": sha256_bytes(module),
                      "book_i_version_at_tag": version_header(book.decode(errors="replace"))
                      if rc_book == 0 else "",
                      "note": "the module bytes at the distribution's git tag, "
                              "read from git, not from PyPI"}
    return {
        "owner": "pyproject.toml",
        "pyproject_version": version,
        "release_tag": tag,
        "tagged_evaluator": tagged,
        "pypi": {"status": "not_read",
                 "note": "the published index is not fetched here; "
                         "PUBLISHING.md and README 'Status by surface' own that "
                         "claim, and version_check.py holds README to pyproject"},
    }


def version_check_section(root: Path, rel: Relations):
    done = run([sys.executable, "tools/version_check.py"], cwd=root)
    verdict = next((l for l in done.stdout.splitlines()
                    if l.startswith("VERSION-CHECK:")), "")
    fails = [l for l in done.stderr.splitlines() if l.startswith("FAIL")]
    rel.add("the six version numbers agree with each other "
            "(tools/version_check.py)", HOLDS if done.returncode == 0 else FAILS,
            "; ".join(fails))
    return {"tool": "tools/version_check.py", "exit": done.returncode,
            "verdict": verdict[:160]}


def candidate_section(root: Path, top: str, anchor_set, rel: Relations):
    name = "the frozen candidate receipt is present and carries its closed fields"
    path = root / RECEIPT
    if not path.is_file():
        rel.add(name, FAILS, f"{RECEIPT} is missing")
        return {"status": "MISSING", "receipt": RECEIPT}
    try:
        receipt = json.loads(path.read_text())
    except ValueError as failure:
        rel.add(name, FAILS, f"{RECEIPT} is not JSON: {failure}")
        return {"status": "MALFORMED", "receipt": RECEIPT}
    missing = [f for f in RECEIPT_FIELDS if f not in receipt]
    ok = receipt.get("kind") == RECEIPT_KIND and not missing
    rel.add(name, HOLDS if ok else FAILS,
            "" if ok else f"kind {receipt.get('kind')!r}, missing {missing}")
    checks = receipt.get("checks_passed") or []
    return {
        "status": "frozen_receipt_referenced",
        "receipt": RECEIPT,
        "receipt_sha256": sha256_file(path),
        "kind": receipt.get("kind"),
        "artifact_filename": receipt.get("artifact_filename"),
        "artifact_sha256": receipt.get("artifact_sha256"),
        "source_commit": receipt.get("source_commit"),
        "software_version": receipt.get("software_version"),
        "adopted_bundle": receipt.get("adopted_bundle"),
        "adopted_anchor_set_sha256": receipt.get("adopted_anchor_set_sha256"),
        "checks_passed_tools": [c.get("tool") for c in checks
                                if isinstance(c, dict)],
        "names_this_trees_adopted_bundle": (
            receipt.get("adopted_bundle") == top
            and receipt.get("adopted_anchor_set_sha256") == anchor_set),
        "note": ("a reference to a committed receipt: its checks are not re-run "
                 "and its artifact is not rebuilt here "
                 "(tools/candidate_freeze_check.py does that). The artifact is "
                 "unpublishable by construction, not adopted, and reached by no "
                 "Warrant runtime tag"),
    }


# -------------------------------------------------------------- warrant half

def validated_operand(root: Path, operand: str | None) -> Path | None:
    if operand is None:
        return None
    path = Path(operand)
    if not path.is_absolute():
        raise Refused(f"--warrant must be an absolute path, got {operand!r}")
    if not path.is_dir():
        raise Refused(f"--warrant {operand} is not a directory")
    resolved = path.resolve()
    top = root.resolve()
    if resolved == top or top in resolved.parents or resolved in top.parents:
        raise Refused(f"--warrant {operand} overlaps this checkout; the Warrant "
                      "operand is a separate tree")
    absent = [m for m in WARRANT_MARKERS if not (resolved / m).is_file()]
    if absent:
        raise Refused(f"--warrant {operand} is not a Warrant checkout "
                      f"(missing {', '.join(absent)})")
    return resolved


def inside(directory: Path, relative) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    target = (directory / rel).resolve()
    return target if directory.resolve() in target.parents else None


def spec_runtime_rows(spec_text: str):
    """The `### 13.1.` runtime-tag table of Warrant's SPEC.md, by tag."""
    start = re.search(r"^### 13\.1\..*$", spec_text, re.M)
    if not start:
        return None
    body = spec_text[start.end():]
    nxt = re.search(r"^### ", body, re.M)
    body = body[:nxt.start()] if nxt else body
    rows = {}
    for line in body.splitlines():
        found = re.match(r"^\|\s*`([a-z0-9-]+@v\d+)`\s*\|\s*(.*?)\s*\|\s*(.*?)"
                         r"\s*\|\s*(.*?)\s*\|\s*$", line)
        if found:
            tag, bodies, status, defined = found.groups()
            rows[tag] = {"body_versions_cell": bodies, "status_cell": status,
                         "defined_in_cell": defined}
    return rows


def reject_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON member {key!r}")
        out[key] = value
    return out


def ci_pin_section(root: Path, operand_commit, rel: Relations):
    done = run(["bash", "tools/read_warrant_pin.sh"], cwd=root)
    pin = done.stdout.strip() if done.returncode == 0 else None
    rel.add("exactly one WARRANT_PIN is readable from ci.yml "
            "(tools/read_warrant_pin.sh)", HOLDS if pin else FAILS,
            "" if pin else done.stderr.strip()[:200])
    return {"source": ".github/workflows/ci.yml WARRANT_PIN",
            "pin": pin,
            "operand_commit_is_pin": (operand_commit == pin)
            if pin and operand_commit else None,
            "note": ("the pin is CI's verified compatible baseline; the operand "
                     "revision is a local observation and constrains nothing")}


def identity_section(root: Path, entry: dict, recomputed: str,
                     tagged: dict, rel: Relations):
    source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
    commit, path = source.get("commit"), source.get("path")
    out = {"status": "checked_from_bytes",
           "sigma_commit_named_by_record": commit,
           "sigma_path_named_by_record": path}
    name = ("the admitted evaluator's bytes are the bytes at the Sigma "
            "commit and path the Warrant record names")
    rc, blob = (git_bytes(root, "cat-file", "blob", f"{commit}:{path}")
                if commit and path else (None, b""))
    if rc == 0:
        same = sha256_bytes(blob) == recomputed
        out["bytes_at_named_sigma_commit"] = "byte_identical" if same else "DIFFER"
        rel.add(name, HOLDS if same else FAILS, f"{commit}:{path}")
    else:
        out["bytes_at_named_sigma_commit"] = "unavailable"
        rel.add(name, UNCHECKED, "the named commit is not readable in this "
                "clone" if commit and path else "the record names no commit/path")
    if tagged.get("status") == "read_from_git":
        out["sigma_distribution_tag_module"] = {
            "tag": tagged["tag"],
            "relation": "byte_identical" if tagged["sha256"] == recomputed else "differ",
            "note": "an observation, not a constraint: a later admitted tag may "
                    "legitimately pin bytes from a different Sigma tag"}
    else:
        out["sigma_distribution_tag_module"] = {"tag": tagged.get("tag"),
                                                "relation": "unavailable"}
    return out


def tags_section(root: Path, warrant: Path, record: dict, rows: dict,
                 tagged: dict, rel: Relations):
    record_tags = record.get("tags") if isinstance(record.get("tags"), dict) else {}
    names = ({t for t in rows if t.startswith("ski@")} | set(record_tags))
    tags = {}
    for tag in sorted(names):
        row = rows.get(tag)
        ent = record_tags.get(tag)
        current = row is not None and row["status_cell"].strip() == "current"
        entry = {
            "spec_status": row["status_cell"] if row else None,
            "spec_body_versions": row["body_versions_cell"] if row else None,
            "spec_defined_in": row["defined_in_cell"] if row else None,
            "admitted_body_versions": (
                re.findall(r"`(\d+\.\d+)`", row["body_versions_cell"])
                if current else []),
        }
        if ent is None:
            status = "admitted_UNBOUND" if current else "reserved_no_evaluator"
            entry.update({"module": None, "pinned_sha256": None,
                          "recomputed_sha256": None, "identity": IDENTITY_NA})
            if status == "reserved_no_evaluator":
                entry["note"] = ("reserved in Warrant SPEC section 13.1 and admitted "
                                 "in no body version; no evaluator bytes are "
                                 "shipped or pinned. Admission is a Warrant "
                                 "registration act in a new body version, not "
                                 "something a Sigma edit or release can do")
        else:
            ent = ent if isinstance(ent, dict) else {}
            module = ent.get("module")
            target = inside(warrant, module)
            recomputed = (sha256_file(target)
                          if target is not None and target.is_file() else None)
            if row is None:
                status = "record_only_UNREGISTERED"
            elif not current:
                status = "record_spec_DISAGREE"
            elif recomputed is None:
                status = "admitted_module_MISSING"
            elif recomputed != ent.get("sha256"):
                status = "admitted_pin_MISMATCH"
            else:
                status = ADMITTED
            entry.update({"module": module, "pinned_sha256": ent.get("sha256"),
                          "recomputed_sha256": recomputed,
                          "semantics": ent.get("semantics"),
                          "source": ent.get("source")})
            entry["identity"] = (identity_section(root, ent, recomputed, tagged, rel)
                                 if status == ADMITTED else IDENTITY_NA)
        entry["status"] = status
        tags[tag] = entry

    bad_pins = [t for t, e in tags.items()
                if e["status"] in ("admitted_pin_MISMATCH",
                                   "admitted_module_MISSING", "admitted_UNBOUND")]
    rel.add("every admitted ski tag binds exactly one evaluator whose bytes "
            "hash to its pin", HOLDS if not bad_pins else FAILS,
            ", ".join(f"{t}: {tags[t]['status']}" for t in bad_pins))
    widened = [t for t, e in tags.items()
               if e["status"] in ("record_spec_DISAGREE", "record_only_UNREGISTERED")]
    rel.add("no evaluator bytes are bound under a tag the Warrant SPEC does not "
            "admit (reserved stays reserved)", HOLDS if not widened else FAILS,
            ", ".join(f"{t}: {tags[t]['status']}" for t in widened))
    return tags


def warrant_section(root: Path, warrant: Path | None, tagged: dict,
                    rel: Relations):
    unchecked = ("every admitted ski tag binds exactly one evaluator whose "
                 "bytes hash to its pin",
                 "no evaluator bytes are bound under a tag the Warrant SPEC "
                 "does not admit (reserved stays reserved)",
                 "the admitted evaluator's bytes are the bytes at the Sigma "
                 "commit and path the Warrant record names")
    if warrant is None:
        for name in unchecked:
            rel.add(name, UNCHECKED, "no --warrant operand")
        return {"status": "unavailable",
                "reason": ("no --warrant operand. The Warrant checkout is an "
                           "explicit cross-repository operand; it is never "
                           "discovered from a sibling directory or an "
                           "environment variable"),
                "tags": {"status": "unavailable"}}

    revision = observed_revision(warrant)
    section = {"status": "checked", "operand": str(warrant),
               "revision": revision,
               "ci_pin": ci_pin_section(root, revision.get("commit"), rel),
               "spec": {"path": "SPEC.md",
                        "sha256": sha256_file(warrant / "SPEC.md")}}
    record_path = warrant / RUNTIME_RECORD
    if not record_path.is_file():
        for name in unchecked:
            rel.add(name, UNCHECKED, f"operand carries no {RUNTIME_RECORD}")
        section["runtime_record"] = {
            "status": "unavailable", "path": RUNTIME_RECORD,
            "reason": "the operand revision carries no runtime-evaluator record, "
                      "so no tag binding can be derived from bytes here"}
        section["tags"] = {"status": "unavailable",
                           "reason": f"no {RUNTIME_RECORD} in the operand"}
        return section
    try:
        record = json.loads(record_path.read_text(),
                            object_pairs_hook=reject_duplicates)
    except ValueError as failure:
        record = {}
        rel.add(f"{RUNTIME_RECORD} is one unambiguous JSON object of kind "
                f"{RUNTIME_RECORD_KIND}", FAILS, str(failure))
    else:
        ok = isinstance(record, dict) and record.get("kind") == RUNTIME_RECORD_KIND
        rel.add(f"{RUNTIME_RECORD} is one unambiguous JSON object of kind "
                f"{RUNTIME_RECORD_KIND}", HOLDS if ok else FAILS,
                "" if ok else f"kind {record.get('kind')!r}" if isinstance(record, dict)
                else "not an object")
        if not ok:
            record = {}
    section["runtime_record"] = {
        "status": "read", "path": RUNTIME_RECORD,
        "sha256": sha256_file(record_path), "kind": record.get("kind"),
        "enforced_by": ("Warrant's own tests/ski_runtime_evaluators.py holds this "
                        "record to impl/warrant.py SKI_EVALUATORS; that test is "
                        "referenced, not run here")}
    rows = spec_runtime_rows((warrant / "SPEC.md").read_text(errors="replace"))
    if rows is None:
        for name in unchecked:
            rel.add(name, UNCHECKED, "SPEC.md carries no section 13.1 runtime table")
        section["tags"] = {"status": "unavailable",
                           "reason": "SPEC.md section 13.1 runtime table not found"}
        return section
    section["tags"] = tags_section(root, warrant, record, rows, tagged, rel)
    section["tags_note"] = ("ski@* tags only; a tag is a Warrant name for one "
                            "evaluator digest and one Book I edition, not a Sigma "
                            "protocol version")
    return section


# ------------------------------------------------------------------- guard

def credit_problems(view: dict) -> list[str]:
    """Why this view widens a status into credit. Empty when it does not."""
    problems = []
    for key in NO_BADGE_KEYS:
        if key in view:
            problems.append(f"top-level {key!r}: the view carries no global badge")
    warrant = view.get("warrant", {})
    tags = warrant.get("tags", {})
    if warrant.get("status") != "checked" and any(
            isinstance(e, dict) and "status" in e and k != "status"
            for k, e in tags.items()):
        problems.append("tag statuses reported while the Warrant operand is "
                        "unavailable")
    admitted = set()
    for tag, entry in tags.items():
        if not isinstance(entry, dict) or tag == "status":
            continue
        status = entry.get("status")
        if status not in TAG_STATUSES:
            problems.append(f"{tag}: unknown status {status!r}")
            continue
        if status == ADMITTED:
            admitted.add(tag)
            continue
        if json.dumps(entry).find("byte_identical") >= 0:
            problems.append(f"{tag}: identity credit under status {status}")
        identity = entry.get("identity")
        if identity != IDENTITY_NA:
            problems.append(f"{tag}: identity must be not_applicable under {status}")
    live = view.get("sigma", {}).get("evaluators", {}).get("live", {})
    reaching = live.get("admitted_warrant_tags_pinned_to_these_bytes")
    if isinstance(reaching, list) and not set(reaching) <= admitted:
        problems.append("live evaluator lists a tag that is not admitted_pinned")
    summary = view.get("summary", {})
    relations = view.get("relations", [])
    counts = {s: sum(1 for r in relations if r.get("status") == s)
              for s in (HOLDS, FAILS, UNCHECKED)}
    if (summary.get("relations_holding") != counts[HOLDS]
            or summary.get("relations_failing") != counts[FAILS]
            or summary.get("relations_unchecked") != counts[UNCHECKED]):
        problems.append("summary counts disagree with the relations list")
    return problems


# -------------------------------------------------------------------- build

def build_view(root: Path, operand: str | None) -> dict:
    warrant = validated_operand(root, operand)
    absent = [p for p in REQUIRED_SOURCES if not (root / p).is_file()]
    if absent:
        raise Refused(f"this tree is missing {', '.join(absent)}, which the view "
                      "reads on every run")
    rel = Relations()
    protocol, top, anchor_set = protocol_section(root, warrant, rel)
    distribution = distribution_section(root)
    tagged = distribution["tagged_evaluator"]
    live_sha = sha256_file(root / LIVE_EVALUATOR)
    warrant_view = warrant_section(root, warrant, tagged, rel)
    tags = warrant_view.get("tags", {})
    reaching = ([t for t, e in tags.items() if isinstance(e, dict)
                 and e.get("status") == ADMITTED and e.get("pinned_sha256") == live_sha]
                if warrant_view["status"] == "checked" and "status" not in tags
                else "unavailable")
    evaluators = {
        "live": {"path": LIVE_EVALUATOR, "sha256": live_sha,
                 "tree_book_i_version": protocol["book_versions"]["Book I"],
                 "admitted_warrant_tags_pinned_to_these_bytes": reaching,
                 "note": ("the Book I reference on this tree. A digest names "
                          "bytes; it does not make them a runtime, and a version "
                          "label shared with a historical candidate does not make "
                          "these bytes that candidate")},
        "tagged": tagged,
    }
    view = {
        "kind": KIND,
        "asserts": ("what this tree's owners state, recomputed from bytes where "
                    "bytes exist, with each verifier's result reused under its "
                    "name. A digest proves identity only. Nothing here is "
                    "adopted, released, registered or admitted by being listed"),
        "sigma": {
            "revision": observed_revision(root),
            "protocol": protocol,
            "distribution": distribution,
            "evaluators": evaluators,
            "candidate": candidate_section(root, top, anchor_set, rel),
            "version_check": version_check_section(root, rel),
        },
        "warrant": warrant_view,
        "relations": rel.items,
        "not_asserted": [
            "that any evaluator conforms: conformance is a verifier run, cited "
            "by name where reused",
            "that the distribution on PyPI matches anything: the index is not read",
            "that a reserved tag will be admitted, or with which bytes",
            "that the operand's revision is the one CI pins, unless "
            "warrant.ci_pin.operand_commit_is_pin is true",
            "independent review, custody or adoption outside this project's "
            "own governance records",
        ],
    }
    view["summary"] = {
        "relations_holding": sum(1 for r in rel.items if r["status"] == HOLDS),
        "relations_failing": sum(1 for r in rel.items if r["status"] == FAILS),
        "relations_unchecked": sum(1 for r in rel.items if r["status"] == UNCHECKED),
        "note": "counts, not a verdict; an unchecked relation is not a holding one",
    }
    return view


def render(view: dict) -> str:
    return json.dumps(view, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--warrant", metavar="DIR",
                    help="absolute path of the Warrant checkout to read "
                         "(explicit; never discovered)")
    args = ap.parse_args()
    try:
        view = build_view(ROOT, args.warrant)
    except Refused as refusal:
        print(f"EVIDENCE-VIEW: REFUSED {refusal}", file=sys.stderr)
        return 2
    problems = [f"{r['relation']}: {r.get('detail', '')}".rstrip(": ")
                for r in view["relations"] if r["status"] == FAILS]
    problems += credit_problems(view)
    sys.stdout.write(render(view))
    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        print(f"EVIDENCE-VIEW: {len(problems)} relation(s) FAIL", file=sys.stderr)
        return 1
    print(f"EVIDENCE-VIEW: {view['summary']['relations_holding']} relation(s) "
          f"hold, {view['summary']['relations_unchecked']} unchecked",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
