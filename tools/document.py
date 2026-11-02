#!/usr/bin/env python3
"""A specification document as a projection of the Warrant ledger (`.warrant/`), rendered into `build/`.

A `document@1` lineage holds one document. A version's body names the document's `source` path, its sentences as
`claims` (claim@1 version ids, in document order) and its `prose` (the id of a blob, the canonical JSON list of the
strings before, between and after those sentences: one more than there are claims). The document is the interleaving
of the two, and nothing else: a version id fixes every byte, so a released document can be rendered again from any
later store. The form is warrant's `warrant-claims/document@1` (W5, 9144debd) without its literal grammar, its heading
pins and its per-sentence layout: here the prose is not all layout, and a claim holds its line breaks verbatim.

    python3 tools/document.py render [--version ID] [--stdout]      # build/<source> of each current document
    python3 tools/document.py check                                 # each current document against the store and tests
    python3 tools/document.py migrate --source S --actor A --key K  # once per source; see below

`render` refuses a store the claims check would refuse, and a version whose parts are not what it says (DOCUMENT_*).
A version's `source` is a signed string, not the operator's word on where to write: only a relative path of plain names
is one (DOCUMENT_SOURCE), and no symbolic link below the root is followed to read or write it. The only destination an
operator names is the shell's, through `--stdout`.
`check` also refuses what makes a current document no longer the whole story: a version of a claim that is not its
lineage's leaf (CLAIM_STALE), a live claim of the source the document does not hold (CLAIM_NOT_IN_DOCUMENT), one
lineage held twice (DOCUMENT_CLAIM_TWICE), a keyword of `.warrant/claims.json` `coverage` outside the positions of the
sentences (UNCLAIMED_KEYWORD; a copy of a sentence in the prose covers nothing), and, while the file is still committed,
a `source` that differs from the rendering (SPEC_NOT_PROJECTION).

`migrate` splits a committed source at its claims' sentences and files the first version, only when each sentence is
there exactly once, none overlaps another and the rendering reproduces the file byte for byte. It trusts the parser
with nothing, and refuses a source that has a document. With no `document@1` counted it files the schema instead, and
stops: the schema counts when `.warrant/v3.json`'s quorum of schema/authors stands behind it."""
import argparse
import hashlib
import re
import sys
from pathlib import Path

from warrant import claims as C
from warrant import jcs as J
from warrant import records as R
from warrant.repo import Failed, Repo, load_key
from warrant.store import Refused

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = "document@1"
SOURCE_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)*")
SCHEMA = {"name": DOCUMENT,
          "fields": {"state": "str", "source": "str", "claims": "refs", "prose": "ref", "because": "str?"},
          "states": {"current": None, "retired": None}, "closed": [], "successors": {}}


def clean_report(repo):
    """(report, snapshot) of a store the claims check would not refuse for what it is."""
    snap = repo.store.snapshot()
    rep = repo.report(snap)
    bad = C.store_problems(rep)
    if bad:
        raise Failed("STORE", f"{len(bad)} problem(s): {bad[0][0]} {bad[0][1]}")
    return rep, snap


def plain_source(source):
    """`source`, refused unless it is a relative path of plain names: no `..`, no root, no empty or hidden name."""
    if not SOURCE_PATH.fullmatch(source):
        raise Failed("DOCUMENT_SOURCE", f"{source!r} is no relative path of plain names")
    return source


def confined(root, relative):
    """The path of the plain `relative` below `root`, refused when a name on the way is a symbolic link."""
    at = Path(root)
    for name in relative.split("/"):
        at = at / name
        if at.is_symlink():
            raise Failed("DOCUMENT_SOURCE", f"{relative!r} goes through the symbolic link {at}")
    return at


def parts(rep, snap, version):
    """(body, prose, [claim bodies]) of the document version `version`, refused unless each part is what it says."""
    rec = rep["_recs"].get(version)
    if rec is None or rec["schema"] != DOCUMENT or rep["_basis"].get(version) != "SIGNED":
        raise Failed("DOCUMENT_UNKNOWN", f"{version} is no signed {DOCUMENT} version of this store")
    body = rec["body"]
    plain_source(body["source"])
    claims = body.get("claims") or []
    prose = snap.json_blob(body.get("prose"))
    if not (isinstance(prose, list) and all(isinstance(p, str) for p in prose) and len(prose) == len(claims) + 1):
        raise Failed("DOCUMENT_PROSE", f"{version[:12]}: its prose is no list of {len(claims) + 1} strings")
    held = []
    for c in claims:
        r = rep["_recs"].get(c)
        if r is None or r["schema"] != C.CLAIM or rep["_basis"].get(c) != "SIGNED" or r["body"]["source"] != body["source"]:
            raise Failed("DOCUMENT_CLAIM", f"{version[:12]}: {c[:12]} is no signed claim of {body['source']}")
        held.append(r["body"])
    return body, prose, held


def interleave(prose, texts):
    out = [prose[0]]
    for text, gap in zip(texts, prose[1:]):
        out += [text, gap]
    return "".join(out).encode("utf-8")


def render(rep, snap, version):
    """The document's bytes: a function of the version's id and nothing else."""
    _, prose, held = parts(rep, snap, version)
    return interleave(prose, [b["text"] for b in held])


def current(rep):
    """{source: leaf version} of the document lineages not retired, refused when a source's document is not one chain."""
    out, recs = {}, rep["_recs"]
    for L, lin in sorted(rep["lineages"].items()):
        if lin["schema"] != DOCUMENT:
            continue
        if lin["verdict"] == "FORK" or lin["leaf"] is None:
            raise Failed("DOCUMENT_FORK", f"lineage {L[:12]} forks")
        body = recs[lin["leaf"]]["body"]
        if body["state"] == "retired":
            continue
        if body["source"] in out:
            raise Failed("DOCUMENT_TWICE", f"{body['source']!r} has two documents")
        out[body["source"]] = lin["leaf"]
    return out


def keyword_problems(prose, held, keywords):
    """The positions of keywords, outside a heading line, that lie whole in no claim's position in the document."""
    text, spans, at = prose[0], [], len(prose[0])
    for b, gap in zip(held, prose[1:]):
        spans.append((at, at + len(b["text"])))
        at += len(b["text"]) + len(gap)
        text += b["text"] + gap
    word = "|".join(r"\s+".join(map(re.escape, k.split(" "))) for k in sorted(keywords, key=len, reverse=True))
    out = []
    for m in re.finditer(rf"(?<![A-Za-z0-9_])(?:{word})(?![A-Za-z0-9_])", text):
        if text.startswith("#", text.rfind("\n", 0, m.start()) + 1):
            continue
        if not any(a <= m.start() and m.end() <= b for a, b in spans):
            out.append(("UNCLAIMED_KEYWORD", f"{m.group(0)} at offset {m.start()} is in no claim's sentence"))
    return out


def problems(rep, snap, version, keywords, root=None):
    """[(code, detail)] that keep document version `version` from being its source's whole, current form, with the
    file its source names below `root`, if there is one."""
    body, prose, held = parts(rep, snap, version)
    recs, source, out = rep["_recs"], body["source"], []
    lineage_of = {v: L for L, lin in rep["lineages"].items() if lin["schema"] == C.CLAIM for v in lin["versions"]}
    live = C.live(rep)
    seen = set()
    for c in body["claims"]:
        L = lineage_of.get(c)
        if L in seen:
            out.append(("DOCUMENT_CLAIM_TWICE", f"{recs[c]['body']['id']} is held twice"))
        seen.add(L)
        if L not in live or rep["lineages"][L]["leaf"] != c:
            out.append(("CLAIM_STALE", f"{recs[c]['body']['id']} ({c[:12]}) is not its live lineage's leaf"))
    out += [("CLAIM_NOT_IN_DOCUMENT", f"{b['id']} of {source} is not in the document")
            for L, b in sorted(live.items()) if b["source"] == source and L not in seen]
    out += keyword_problems(prose, held, keywords)
    committed = confined(root, source) if root else None
    if committed and committed.exists() and committed.read_bytes() != interleave(prose, [b["text"] for b in held]):
        out.append(("SPEC_NOT_PROJECTION", f"the committed {source} is not the rendering of {version[:12]}"))
    return out


def split_at_claims(text, sentences):
    """The prose of `text` around `sentences` in their document order, as (prose, [indexes into sentences]), refused
    unless each sentence is there exactly once and none overlaps another."""
    found = []
    for i, s in enumerate(sentences):
        if text.count(s) != 1:
            raise Failed("MIGRATE_AMBIGUOUS", f"{s[:60]!r} is there {text.count(s)} time(s)")
        found.append((text.index(s), i))
    prose, end = [], 0
    for at, i in sorted(found):
        if at < end:
            raise Failed("MIGRATE_OVERLAP", f"{sentences[i][:60]!r} overlaps the sentence before it")
        prose.append(text[end:at])
        end = at + len(sentences[i])
    prose.append(text[end:])
    return prose, [i for _, i in sorted(found)]


def migrate(repo, source, actor, key):
    path = confined(repo.root, plain_source(source))
    rep, _ = clean_report(repo)
    if not any(s == DOCUMENT for s in rep["schemas"]):
        if any(p["name"] == DOCUMENT for p in rep["schemas_pending"].values()):
            raise Failed("SCHEMA_PENDING", f"{DOCUMENT} is filed and short of its quorum of schema/authors")
        return "schema", repo.file(actor, key, [R.record("schema", actor, 0, SCHEMA)])
    if source in current(rep):
        raise Failed("DOCUMENT_EXISTS", f"{source} has a document: file a new version, not a migration")
    data = path.read_bytes()
    live = {L: b for L, b in C.live(rep).items() if b["source"] == source}
    lineages = sorted(live)
    prose, order = split_at_claims(data.decode("utf-8"), [live[L]["text"] for L in lineages])
    versions = [rep["lineages"][lineages[i]]["leaf"] for i in order]
    if interleave(prose, [live[lineages[i]]["text"] for i in order]) != data:
        raise Failed("MIGRATE_NOT_IDENTICAL", f"the split of {source} does not render to its bytes")
    blob = repo.store.put_blob(J.canon(prose))
    body = {"state": "current", "source": source, "claims": versions, "prose": blob}
    return "document", repo.file(actor, key, [R.record("entity", actor, 0, body, DOCUMENT, refs=[blob, *versions])])


def render_command(repo, version, stdout):
    rep, snap = clean_report(repo)
    versions = [version] if version else list(current(rep).values())
    if not versions:
        raise Failed("DOCUMENT_MISSING", f"this store holds no current {DOCUMENT}")
    if stdout and len(versions) != 1:
        raise Failed("DOCUMENT_UNKNOWN", f"--stdout holds one document and there are {len(versions)}")
    for v in versions:
        data = render(rep, snap, v)
        if stdout:
            sys.stdout.buffer.write(data)
            continue
        out = confined(repo.root, "build/" + rep["_recs"][v]["body"]["source"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f"{out} {hashlib.sha256(data).hexdigest()} from {v}")
    return 0


def check_command(repo):
    rep, snap = clean_report(repo)
    keywords = C.config(repo.root).get("coverage", ["MUST"])
    docs = current(rep)
    if not docs:
        raise Failed("DOCUMENT_MISSING", f"this store holds no current {DOCUMENT}")
    found = []
    for source, v in sorted(docs.items()):
        found += problems(rep, snap, v, keywords, repo.root)
        print(f"document: {source} is {v}")
    for code, detail in found:
        print(f"{code} {detail}")
    print(f"documents: {len(docs)}; {len(found)} problem(s)")
    return 1 if found else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--version")
    r.add_argument("--stdout", action="store_true")
    sub.add_parser("check")
    m = sub.add_parser("migrate")
    m.add_argument("--source", required=True)
    m.add_argument("--actor", required=True)
    m.add_argument("--key", required=True)
    a = ap.parse_args(argv)
    try:
        repo = Repo(a.root)
        if a.cmd == "migrate":
            what, ids = migrate(repo, a.source, a.actor, load_key(a.key, repo.root))
            print(f"filed the {what}: {ids[0]}")
            return 0
        return render_command(repo, a.version, a.stdout) if a.cmd == "render" else check_command(repo)
    except Failed as e:
        print(f"REFUSED {e.code} {e}", file=sys.stderr)
        return 2
    except Refused as e:
        print(f"REFUSED STORE {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"REFUSED IO {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
