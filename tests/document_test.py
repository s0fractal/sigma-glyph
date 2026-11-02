#!/usr/bin/env python3
"""spec/sigma-resume.md is a projection of the ledger: tools/document.py reproduces the released document byte for
byte, and refuses a store or a document version that would not.

Each case prints `ok   ID …` or `FAIL ID …`. An exception is a wrong value, so a mutant that makes the generator raise
is seen on the case's assertion. D01 is the correctness proof. tests/document_mutants.py breaks it and the refusals.

Needs warrant-graph (.github/warrant-requirements.txt), which the records are read with.

    python3 tests/document_test.py"""
import copy
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import document as D               # noqa: E402
from warrant import claims as C    # noqa: E402
from warrant.repo import Failed, Repo  # noqa: E402

SOURCE = "spec/sigma-resume.md"
TOOL = str(ROOT / "tools" / "document.py")
# The release, named by its commit's full id: a tag can move. The harness's copies of the tree have no .git, so it
# names the repository to read the release from.
RELEASE_TAG = "v1.0.0"
RELEASE_COMMIT = "321504a02c0d0a87eeb6b5dd4760a9b22a6d53af"
RELEASE_SHA256 = "0cc4945098d25e4487daceaf296f0f9e9015456b8a40ebbc7ef2a9041dd893ba"
# The document version that is v1.0.0's sigma-resume, whatever later versions say.
RELEASE_VERSION = "bcbbe30f585a93c95ee7de3ea38d609913d0f4c98d2901048f37340b2e88962c"
GIT = os.environ.get("SIGMA_RELEASE_GIT", str(ROOT))

failures = []


def check(case, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + case + ("" if ok else f" -- {detail}"))
    if not ok:
        failures.append(case)


def tried(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {getattr(e, 'code', '')} {e}"


def git(*a):
    return subprocess.run(["git", "-C", GIT, *a], capture_output=True).stdout


def cli(*a, root=ROOT, env=None):
    return subprocess.run([sys.executable, "-B", TOOL, "--root", str(root), *a], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def code_of(f, *a):
    """The code of the refusal `f` raises, or None."""
    try:
        f(*a)
    except Failed as e:
        return e.code
    return None


def codes(rep, snap, version, committed=None, keywords=None):
    return {c for c, _ in D.problems(rep, snap, version, keywords if keywords is not None else coverage, committed)}


released = git("show", f"{RELEASE_COMMIT}:{SOURCE}")
repo = Repo(ROOT)
loaded = tried(D.clean_report, repo)
rep, snap = loaded if isinstance(loaded, tuple) else ({"_recs": {}, "_basis": {}, "lineages": {}}, None)
coverage = C.config(ROOT)["coverage"]
leaf = tried(lambda: D.current(rep)[SOURCE])

# ---- the correctness proof
check("D00", git("rev-parse", f"{RELEASE_TAG}^{{commit}}").decode().strip() == RELEASE_COMMIT
      and hashlib.sha256(released).hexdigest() == RELEASE_SHA256,
      f"the tag {RELEASE_TAG} or the released bytes are not the pinned ones")
rendered = tried(D.render, rep, snap, RELEASE_VERSION)
check("D01", rendered == released, f"the release's document version does not render to {RELEASE_TAG}'s bytes: {str(rendered)[:120]}")

# ---- the generator, as a command, into build/
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "first.md"
    first = cli("render", "--out", str(out))
    second = cli("render", "--out", str(Path(td) / "second.md"), env={"PYTHONHASHSEED": "7", "TZ": "Asia/Tokyo", "LC_ALL": "C"})
    same = out.exists() and (Path(td) / "second.md").exists() and out.read_bytes() == (Path(td) / "second.md").read_bytes()
    check("D02", first.returncode == 0 and same and out.read_bytes() == (ROOT / SOURCE).read_bytes(),
          f"render is not deterministic or is not the committed file: {first.stderr[:200]}")
default = cli("render")
built = ROOT / "build" / SOURCE
check("D03", default.returncode == 0 and built.exists() and built.read_bytes() == (ROOT / SOURCE).read_bytes()
      and git("check-ignore", f"build/{SOURCE}").strip() == f"build/{SOURCE}".encode(),
      f"render does not fill an ignored build/: {default.stderr[:200]}")
full = cli("check")
check("D04", full.returncode == 0 and full.stdout.strip().endswith("documents: 1; 0 problem(s)"), f"check: {full.stdout[-300:]} {full.stderr[:200]}")


# ---- a version whose parts are not what it says
def variant(mutate):
    """(report, snapshot, version) of a copy of the report with a new leaf: the document's body after `mutate(body,
    prose)`. Records are read from memory, so the store's own checks are not what refuses these."""
    r = {**rep, "_recs": dict(rep["_recs"]), "_basis": dict(rep["_basis"]), "lineages": copy.deepcopy(rep["lineages"])}
    body = copy.deepcopy(rep["_recs"][leaf]["body"])
    prose = list(snap.json_blob(body["prose"]))
    mutate(body, prose, r)
    v = "f" * 64
    r["_recs"][v], r["_basis"][v] = dict(rep["_recs"][leaf], body=body), "SIGNED"
    return r, types.SimpleNamespace(json_blob=lambda h: prose), v


def drop_first_claim(body, prose, _):
    del body["claims"][0]
    prose[0:2] = [prose[0] + prose[1]]


def add_keyword(body, prose, _):
    prose[-1] += "\nA host MUST do this.\n"


def copy_a_sentence_into_prose(body, prose, r):
    """A keyword covered by nothing but a copy of a claim's sentence: the sentence is in the document twice, one of
    them a claim. warrant.claims.unclaimed finds the sentence by its words and counts both."""
    prose[-1] += "\n" + r["_recs"][body["claims"][0]]["body"]["text"]


def claim_of_another_source(body, prose, r):
    body["claims"][0] = next(lin["leaf"] for L, lin in r["lineages"].items()
                             if lin["schema"] == C.CLAIM and r["_recs"][L]["body"]["source"] != SOURCE)


def supersede_first_claim(body, prose, r):
    c = body["claims"][0]
    L = next(L for L, lin in r["lineages"].items() if c in lin["versions"])
    r["_recs"]["e" * 64] = r["_recs"][c]
    r["_basis"]["e" * 64] = "SIGNED"
    r["lineages"][L]["versions"] = [*r["lineages"][L]["versions"], "e" * 64]
    r["lineages"][L]["leaf"] = "e" * 64


def retire_first_claim(body, prose, r):
    c = body["claims"][0]
    L = next(L for L, lin in r["lineages"].items() if c in lin["versions"])
    r["_recs"][c] = dict(r["_recs"][c], body=dict(r["_recs"][c]["body"], state="retired"))
    r["lineages"][L]["leaf"] = c


def refusal(case, want, f):
    got = tried(f)
    check(case, got == want or (isinstance(got, set) and want in got), f"wanted {want}, got {got}")


refusal("D10", "CLAIM_NOT_IN_DOCUMENT", lambda: codes(*variant(drop_first_claim)))
refusal("D11", "DOCUMENT_CLAIM_TWICE", lambda: codes(*variant(
    lambda b, p, _: (b["claims"].insert(1, b["claims"][0]), p.insert(1, "")))))
refusal("D12", "CLAIM_STALE", lambda: codes(*variant(supersede_first_claim)))
refusal("D13", "CLAIM_STALE", lambda: codes(*variant(retire_first_claim)))
refusal("D14", "DOCUMENT_PROSE", lambda: code_of(D.render, *variant(lambda b, p, _: p.pop())))
refusal("D15", "DOCUMENT_CLAIM", lambda: code_of(D.render, *variant(claim_of_another_source)))
refusal("D16", "UNCLAIMED_KEYWORD", lambda: codes(*variant(add_keyword)))
refusal("D17", "SPEC_NOT_PROJECTION", lambda: codes(rep, snap, leaf, (ROOT / SOURCE).read_bytes() + b"\n"))
refusal("D18", "DOCUMENT_UNKNOWN", lambda: code_of(D.render, rep, snap, rep["_recs"][leaf]["body"]["claims"][0]))


def unsigned(what):
    """The refusal of `render` when the document's version (or its first claim) is no signed record of the store."""
    r, s, v = variant(lambda *_: None)
    r["_basis"][v if what == "document" else r["_recs"][v]["body"]["claims"][0]] = "UNSIGNED"
    return code_of(D.render, r, s, v)


refusal("D22", "DOCUMENT_UNKNOWN", lambda: unsigned("document"))
refusal("D23", "DOCUMENT_CLAIM", lambda: unsigned("claim"))
d24 = tried(lambda: codes(*variant(lambda b, p, _: p.__setitem__(-1, p[-1] + "\n## A heading that says MUST\n"))))
check("D24", d24 == set(), f"a keyword in a heading is no claim's to hold: {d24}")


def other_document(state, verdict="OK"):
    """A report with a second lineage of the source, in `state`, or the one lineage marked with `verdict`."""
    r = {**rep, "_recs": dict(rep["_recs"]), "lineages": copy.deepcopy(rep["lineages"])}
    if verdict != "OK":
        L = next(L for L, lin in r["lineages"].items() if leaf in lin["versions"])
        r["lineages"][L].update(verdict=verdict, leaf=None)
        return r
    v = "d" * 64
    r["_recs"][v] = dict(rep["_recs"][leaf], body=dict(rep["_recs"][leaf]["body"], state=state))
    r["lineages"][v] = {"schema": D.DOCUMENT, "verdict": "OK", "leaf": v, "versions": [v]}
    return r


refusal("D25", "DOCUMENT_FORK", lambda: code_of(D.current, other_document("current", verdict="FORK")))
refusal("D26", "DOCUMENT_TWICE", lambda: code_of(D.current, other_document("current")))
check("D27", tried(lambda: D.current(other_document("retired"))[SOURCE]) == leaf, "a retired lineage took the source")


# D19: what the reading by words misses and the positions do not. A sentence with a keyword, also copied into the prose.
def d19():
    r, s, v = variant(copy_a_sentence_into_prose)
    prose = s.json_blob(None)
    held = [r["_recs"][c]["body"] for c in r["_recs"][v]["body"]["claims"]]
    text = D.interleave(prose, [b["text"] for b in held]).decode()
    words = C.unclaimed(text, [b["text"] for b in held], coverage)
    return not words and "UNCLAIMED_KEYWORD" in codes(r, s, v)


check("D19", tried(d19) is True, f"{tried(d19)}")


# ---- a store that is not what was filed
def tampered(what, cmd="render"):
    """The exit status and refusal of `cmd` over a copy of the store with `what` done to it."""
    with tempfile.TemporaryDirectory() as td:
        dot = Path(td) / ".warrant"
        shutil.copytree(ROOT / ".warrant", dot)
        what(dot)
        got = cli(cmd, *(("--out", str(Path(td) / "out.md")) if cmd == "render" else ()), root=td)
        return got.returncode, got.stderr


def forge_prose(dot):
    """A blob whose name is its hash, and a document line naming it: the line's signature no longer holds."""
    blob = rep["_recs"][leaf]["body"]["prose"]
    lines = (dot / "records.jsonl").read_text().splitlines(keepends=True)
    forged = hashlib.sha256(b"[]").hexdigest()
    (dot / "blobs" / forged).write_bytes(b"[]")
    (dot / "records.jsonl").write_text("".join(ln.replace(blob, forged) for ln in lines))


def drop_document(dot):
    lines = (dot / "records.jsonl").read_text().splitlines(keepends=True)
    (dot / "records.jsonl").write_text("".join(ln for ln in lines if '"schema":"document@1"' not in ln))


def lengthen_blob(dot):
    blob = rep["_recs"][leaf]["body"]["prose"]
    (dot / "blobs" / blob).write_bytes((dot / "blobs" / blob).read_bytes() + b" ")


def refused(case, code, what, cmd="render"):
    got = tried(tampered, what, cmd)
    check(case, isinstance(got, tuple) and got[0] == 2 and f"REFUSED {code} " in got[1], f"{got}")


refused("D20", "STORE", forge_prose)
refused("D21", "STORE", lengthen_blob)
refused("D28", "DOCUMENT_MISSING", drop_document, "check")
refused("D29", "DOCUMENT_MISSING", drop_document)


# ---- the one parser, for the first version only
refusal("D30", "MIGRATE_AMBIGUOUS", lambda: code_of(D.split_at_claims, "a b a", ["a"]))
refusal("D31", "MIGRATE_AMBIGUOUS", lambda: code_of(D.split_at_claims, "a b", ["c"]))
refusal("D32", "MIGRATE_OVERLAP", lambda: code_of(D.split_at_claims, "abcd", ["abc", "bcd"]))
check("D33", tried(D.split_at_claims, "x b y a z", ["a", "b"]) == (["x ", " y ", " z"], [1, 0]), "the split")
refusal("D34", "DOCUMENT_EXISTS", lambda: code_of(D.migrate, repo, SOURCE, "claude", None))

print(f"\nDOCUMENT: {'ALL PASS' if not failures else 'FAILURES ' + ' '.join(failures)}")
sys.exit(1 if failures else 0)
