#!/usr/bin/env python3
"""Controls for tools/evidence_view.py: it must refuse, and it must go red.

The view is a projection, so its whole value is that a wrong answer is
impossible to read as a right one. Three failure modes would destroy that and
none of them is visible in a green run:

  * it DISCOVERS the Warrant operand from ambient state, so the document
    silently describes some other checkout than the one the reader named;
  * it WIDENS a narrow status into credit -- a reserved tag, a missing module
    or a mismatched pin ends up looking like an admitted, byte-identical one;
  * it degrades a bad operand or an unreadable tree into a partial document
    instead of refusing.

Review of f3b7099 added two more, and the controls for them say so where they
sit:

  * it reads AMBIGUOUS input as an answer -- a record, table or producer that
    says two things collapses into whichever the parser saw last, so the same
    conflicting bytes mean different things depending on their order;
  * it CLAIMS MORE than it checks -- a relation whose sentence is wider than
    the predicate behind it is a false statement even when it holds.

So the controls below are mostly negative. Each names the exact status or
refusal it demands; "the tool exited non-zero" is never enough, because a
syntax error satisfies that too.

The Warrant half runs against SYNTHETIC operands built in a temp directory --
one minimal Warrant checkout per control, tampered in exactly one way. That is
deliberate: these controls must run with no network, no sibling checkout and no
clone, and they must never write to a real Warrant tree. Pass the optional
`--warrant DIR` to ALSO run one positive control against a real checkout.

Run: python3 tests/evidence_view_test.py [--warrant /abs/path/to/warrant]
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "tools" / "evidence_view.py"
sys.path.insert(0, str(ROOT / "tools"))
import evidence_view as ev  # noqa: E402

# Every override the view promises not to consult, pointed somewhere plausible.
# A discovery bug turns these into an answer instead of being ignored.
HOSTILE = {"SIGMA_GLYPH": "impl", "WARRANT": "python3 /nonexistent/warrant.py",
           "WARRANT_PY": "/nonexistent/warrant.py", "SIBLING": "",
           "WARRANT_POSITIONAL": "1", "WARRANT_SKI_MAX_ATP": "9",
           "WARRANT_SIGMA_DIFFERENTIAL": "1", "X1_SIBLING_REF": "master"}

SPEC_HEADER = """# Synthetic Warrant SPEC

### 13.0. Something above the runtime table

| `not@v9` | ignore | current | elsewhere |

### 13.1. SKI runtime evaluators

| Tag | Body versions | Status | Defined in |
|---|---|---|---|
"""
SPEC_FOOTER = "\n### 13.2. The section after\n\ntext\n"
ROW_V1 = "| `ski@v1` | `0.2` | current | §3.1 |\n"
ROW_V2 = "| `ski@v2` | — | reserved | §3.2 |\n"
MODULE = b"# synthetic ski@v1 evaluator bytes\n"
MODULE_PATH = "impl/ski_v1.py"

failures = []


def check(name, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + name
          + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# ------------------------------------------------------------------ fixtures

def write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def make_operand(directory: Path, *, rows=(ROW_V1, ROW_V2), record=None,
                 module=MODULE, drop_record=False) -> Path:
    """One minimal Warrant checkout: the two marker files, a section 13.1 table
    and a runtime-evaluator record. Every control varies exactly one of them."""
    write(directory / "SPEC.md", SPEC_HEADER + "".join(rows) + SPEC_FOOTER)
    write(directory / "impl" / "warrant.py", "# synthetic Warrant CLI\n")
    if module is not None:
        write(directory / MODULE_PATH, module)
    if not drop_record:
        if record is None:
            record = {"kind": ev.RUNTIME_RECORD_KIND,
                      "tags": {"ski@v1": {
                          "module": MODULE_PATH,
                          "sha256": ev.sha256_bytes(MODULE),
                          "semantics": "synthetic Book I edition"}}}
        write(directory / ev.RUNTIME_RECORD,
              json.dumps(record, indent=2) if isinstance(record, dict) else record)
    return directory


def stand_in_tree(directory: Path, *, receipt=None, tools=None) -> Path:
    """A stand-in Sigma tree, so a control can vary one INPUT FILE of this
    repository and still exercise the real CLI, its real file reads and the
    real subprocesses it starts -- rather than calling a helper with a
    hand-built object and catching whatever it raises.

    Every entry is a symlink to this checkout's, so nothing is copied and
    nothing can drift, with three exceptions: `tools/evidence_view.py` is a
    copy (the CLI derives its own root from its resolved path, and a symlink
    would resolve back here); the frozen receipt is written from `receipt` when
    one is given; and each `tools/<name>` in `tools` is written from its text
    instead of linked, which is how a control injects a producer fault.
    `.git` is left out, so the tree is not a checkout and reports no revision.
    """
    tools = dict(tools or {})
    (directory / "tools").mkdir(parents=True)
    for entry in ROOT.iterdir():
        if entry.name not in (".git", "tools", "campaigns"):
            (directory / entry.name).symlink_to(entry)
    for entry in (ROOT / "tools").iterdir():
        if entry.name not in {"evidence_view.py", *tools}:
            (directory / "tools" / entry.name).symlink_to(entry)
    shutil.copy2(VIEW, directory / "tools" / "evidence_view.py")
    for name, text in tools.items():
        write(directory / "tools" / name, text)
    if receipt is None:
        (directory / "campaigns").symlink_to(ROOT / "campaigns")
    else:
        write(directory / ev.RECEIPT, receipt)
    return directory


def run_view(*args, tree: Path = ROOT, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k not in ev.AMBIENT}
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(tree / "tools" / "evidence_view.py"), *args],
        cwd=str(tree), capture_output=True, text=True, env=env, check=False)


def view_of(operand: Path, **kwargs):
    """(exit status, parsed view or None) for one synthetic operand."""
    done = run_view("--warrant", str(operand), **kwargs)
    try:
        return done.returncode, json.loads(done.stdout), done.stderr
    except ValueError:
        return done.returncode, None, done.stderr


def tag_of(view, name):
    tags = view.get("warrant", {}).get("tags", {})
    entry = tags.get(name)
    return entry if isinstance(entry, dict) else {}


def relation(view, needle):
    for item in view.get("relations", []):
        if needle in item["relation"]:
            return item
    return {}


# ------------------------------------------------------- positive: Sigma half

def positive_sigma(temp: Path):
    done = run_view()
    view = json.loads(done.stdout) if done.stdout.strip() else {}
    check("no operand: exits 0 and prints one JSON document",
          done.returncode == 0 and view.get("kind") == ev.KIND,
          f"exit {done.returncode}")
    check("no operand: the Warrant half is typed unavailable, not empty",
          view.get("warrant", {}).get("status") == "unavailable"
          and view.get("warrant", {}).get("tags") == {"status": "unavailable"},
          json.dumps(view.get("warrant", {}))[:120])
    unchecked = [r for r in view.get("relations", []) if r["status"] == ev.UNCHECKED]
    check("no operand: every Warrant-dependent relation is unchecked, none holds",
          len(unchecked) == 4 and all("no --warrant operand" in r.get("detail", "")
                                      or "trust anchor" in r.get("detail", "")
                                      for r in unchecked),
          f"{len(unchecked)} unchecked")
    check("no operand: no top-level badge and no credit is widened",
          ev.credit_problems(view) == [], "; ".join(ev.credit_problems(view)))

    again = run_view()
    check("the same tree twice gives byte-identical output (deterministic)",
          again.stdout == done.stdout and again.returncode == done.returncode)

    # Missing/extra on the ACTUAL sources: every Sigma path the document names
    # has to be a file in this tree, or the document is describing bytes that
    # are not there.
    sigma = view.get("sigma", {})
    named = [sigma["protocol"]["owner"], sigma["distribution"]["owner"],
             sigma["evaluators"]["live"]["path"], sigma["candidate"]["receipt"]]
    named += [f["path"] for f in sigma["protocol"]["anchors"]["files"]]
    absent = [p for p in named if not (ROOT / p).is_file()]
    check("every Sigma source the view names exists in this tree", not absent,
          ", ".join(absent))
    check("the live evaluator digest is the digest of those bytes",
          sigma["evaluators"]["live"]["sha256"]
          == ev.sha256_file(ROOT / ev.LIVE_EVALUATOR))

    # The reserved tag must never acquire an evaluator through the Sigma half.
    check("the tree's own evaluator claims no Warrant tag without an operand",
          sigma["evaluators"]["live"]["admitted_warrant_tags_pinned_to_these_bytes"]
          == "unavailable")


# ------------------------------------------------------------ refusal: exit 2

def refusals(temp: Path):
    notdir = temp / "a-file"
    write(notdir, "x")
    plain = temp / "not-a-warrant"
    plain.mkdir()
    partial = temp / "half-a-warrant"
    write(partial / "SPEC.md", "# no impl/warrant.py here\n")

    cases = {
        "a relative --warrant path": "warrant",
        "--warrant naming a file": str(notdir),
        "--warrant naming a directory with no Warrant markers": str(plain),
        "--warrant missing one Warrant marker": str(partial),
        "--warrant overlapping this checkout": str(ROOT),
        "--warrant naming a parent of this checkout": str(ROOT.parent),
    }
    for name, operand in cases.items():
        done = run_view("--warrant", operand)
        check(f"refused (exit 2, no document): {name}",
              done.returncode == 2 and done.stdout == ""
              and "REFUSED" in done.stderr,
              f"exit {done.returncode}, {len(done.stdout)} bytes on stdout")

    # A tree that cannot answer must refuse by name rather than traceback.
    bare = temp / "bare-tree"
    bare.mkdir()
    try:
        ev.build_view(bare, None)
    except ev.Refused as refusal:
        named = all(source in str(refusal) for source in ev.REQUIRED_SOURCES)
        check("refused by name when a source the view always reads is missing",
              named, str(refusal))
    except Exception as other:  # noqa: BLE001 - the point is that it is typed
        check("refused by name when a source the view always reads is missing",
              False, f"{type(other).__name__}: {other}")
    else:
        check("refused by name when a source the view always reads is missing",
              False, "no refusal")


# ----------------------------------------------------- hostile ambient state

def ambient(temp: Path):
    clean = run_view()
    dirty = run_view(env_extra=HOSTILE)
    check("hostile ambient state does not conjure a Warrant operand",
          dirty.returncode == clean.returncode and dirty.stdout == clean.stdout,
          "the ambient run differs from the clean one")

    operand = make_operand(temp / "ambient-operand")
    clean_op = run_view("--warrant", str(operand))
    dirty_op = run_view("--warrant", str(operand), env_extra=HOSTILE)
    check("hostile ambient state does not alter an explicit operand's view",
          dirty_op.stdout == clean_op.stdout
          and dirty_op.returncode == clean_op.returncode)

    # SIBLING/WARRANT name the real thing an X1 run would use; with no operand
    # the document must still say "unavailable" rather than read them.
    real = {**HOSTILE, "SIBLING": str(temp / "ambient-operand"),
            "WARRANT": f"python3 {temp / 'ambient-operand' / 'impl' / 'warrant.py'}"}
    done = run_view(env_extra=real)
    view = json.loads(done.stdout)
    check("a reachable sibling in the environment is still not an operand",
          view["warrant"]["status"] == "unavailable"
          and "never discovered" in view["warrant"]["reason"])


# ----------------------------------- the Warrant half: positive, then tampered

def warrant_half(temp: Path):
    good = make_operand(temp / "good")
    status, view, err = view_of(good)
    v1 = tag_of(view, "ski@v1")
    check("synthetic operand: a pinned, present, current tag is admitted_pinned",
          status == 0 and v1.get("status") == ev.ADMITTED,
          f"exit {status}, status {v1.get('status')!r}")
    check("synthetic operand: the pin is confirmed by recomputing the bytes",
          v1.get("recomputed_sha256") == ev.sha256_bytes(MODULE)
          and v1.get("pinned_sha256") == v1.get("recomputed_sha256"))
    v2 = tag_of(view, "ski@v2")
    check("ski@v2 is reserved_no_evaluator: no module, no pin, no identity",
          v2.get("status") == "reserved_no_evaluator"
          and v2.get("module") is None and v2.get("pinned_sha256") is None
          and v2.get("identity") == ev.IDENTITY_NA,
          json.dumps(v2)[:160])
    check("a reserved tag admits no body version",
          v2.get("admitted_body_versions") == [])
    check("the operand's revision is reported as an observation, not a pin",
          view["warrant"]["revision"]["status"] == "unavailable"
          and view["warrant"]["ci_pin"]["operand_commit_is_pin"] is None)
    check("a clean synthetic operand widens nothing",
          ev.credit_problems(view) == [], "; ".join(ev.credit_problems(view)))

    pin_relation = ("every admitted ski tag binds exactly one evaluator whose "
                    "bytes hash to its pin")
    reserved_relation = "reserved stays reserved"

    # --- drift: the pinned bytes moved under the pin -----------------------
    drift = make_operand(temp / "drift", module=MODULE + b"# drifted\n")
    status, view, err = view_of(drift)
    tag = tag_of(view, "ski@v1")
    check("DRIFT: bytes that do not hash to the pin are admitted_pin_MISMATCH",
          status == 1 and tag.get("status") == "admitted_pin_MISMATCH"
          and relation(view, pin_relation).get("status") == ev.FAILS,
          f"exit {status}, status {tag.get('status')!r}")
    check("DRIFT: a mismatched tag carries no identity credit",
          tag.get("identity") == ev.IDENTITY_NA
          and "byte_identical" not in json.dumps(tag)
          and ev.credit_problems(view) == [])

    # --- missing: the pinned module is not in the operand ------------------
    gone = make_operand(temp / "module-gone", module=None)
    status, view, err = view_of(gone)
    tag = tag_of(view, "ski@v1")
    check("MISSING: an absent pinned module is admitted_module_MISSING, exit 1",
          status == 1 and tag.get("status") == "admitted_module_MISSING"
          and tag.get("recomputed_sha256") is None,
          f"exit {status}, status {tag.get('status')!r}")

    # --- missing: the operand carries no record at all ---------------------
    norecord = make_operand(temp / "no-record", drop_record=True)
    status, view, err = view_of(norecord)
    check("MISSING: no runtime record types the tags unavailable, exit 0",
          status == 0 and view["warrant"]["tags"] == {
              "status": "unavailable",
              "reason": f"no {ev.RUNTIME_RECORD} in the operand"}
          and view["warrant"]["runtime_record"]["status"] == "unavailable",
          f"exit {status}")
    check("MISSING: an unavailable record leaves the relations unchecked, "
          "never holding",
          relation(view, pin_relation).get("status") == ev.UNCHECKED
          and relation(view, reserved_relation).get("status") == ev.UNCHECKED)

    # --- missing: the SPEC carries no 13.1 table ---------------------------
    notable = make_operand(temp / "no-table")
    write(notable / "SPEC.md", "# Synthetic Warrant SPEC\n\n### 13.2. Other\n")
    status, view, err = view_of(notable)
    check("MISSING: no section 13.1 table types the tags unavailable, exit 0",
          status == 0 and view["warrant"]["tags"].get("status") == "unavailable"
          and relation(view, pin_relation).get("status") == ev.UNCHECKED,
          f"exit {status}")

    # --- extra: the record binds a tag the SPEC never registered -----------
    extra = make_operand(temp / "extra", record={
        "kind": ev.RUNTIME_RECORD_KIND,
        "tags": {"ski@v1": {"module": MODULE_PATH,
                            "sha256": ev.sha256_bytes(MODULE)},
                 "ski@v9": {"module": MODULE_PATH,
                            "sha256": ev.sha256_bytes(MODULE)}}})
    status, view, err = view_of(extra)
    tag = tag_of(view, "ski@v9")
    check("EXTRA: a tag bound by the record but absent from the SPEC is "
          "record_only_UNREGISTERED, exit 1",
          status == 1 and tag.get("status") == "record_only_UNREGISTERED"
          and relation(view, reserved_relation).get("status") == ev.FAILS,
          f"exit {status}, status {tag.get('status')!r}")
    check("EXTRA: an unregistered tag carries no identity credit",
          tag.get("identity") == ev.IDENTITY_NA
          and "byte_identical" not in json.dumps(tag)
          and ev.credit_problems(view) == [])

    # --- widening: evaluator bytes bound under the RESERVED tag ------------
    widened = make_operand(temp / "widened", record={
        "kind": ev.RUNTIME_RECORD_KIND,
        "tags": {"ski@v2": {"module": MODULE_PATH,
                            "sha256": ev.sha256_bytes(MODULE),
                            "semantics": "Book I 0.6.0"}}})
    status, view, err = view_of(widened)
    tag = tag_of(view, "ski@v2")
    check("WIDENING: bytes bound under a reserved tag are record_spec_DISAGREE, "
          "exit 1",
          status == 1 and tag.get("status") == "record_spec_DISAGREE"
          and relation(view, reserved_relation).get("status") == ev.FAILS,
          f"exit {status}, status {tag.get('status')!r}")
    check("WIDENING: a reserved tag with bytes is still not admitted_pinned "
          "and gets no identity",
          tag.get("status") != ev.ADMITTED
          and tag.get("identity") == ev.IDENTITY_NA
          and "byte_identical" not in json.dumps(tag))

    # --- unbound: the SPEC admits a tag the record binds to nothing --------
    unbound = make_operand(temp / "unbound", record={
        "kind": ev.RUNTIME_RECORD_KIND, "tags": {}})
    status, view, err = view_of(unbound)
    tag = tag_of(view, "ski@v1")
    check("UNBOUND: a current tag with no record entry is admitted_UNBOUND, "
          "exit 1",
          status == 1 and tag.get("status") == "admitted_UNBOUND"
          and relation(view, pin_relation).get("status") == ev.FAILS,
          f"exit {status}, status {tag.get('status')!r}")

    # --- the record itself has to be one unambiguous document -------------
    kind_relation = "is one unambiguous JSON object of kind"
    dup = make_operand(temp / "duplicate-member", record=(
        '{"kind": "%s", "kind": "other",\n "tags": {}}' % ev.RUNTIME_RECORD_KIND))
    status, view, err = view_of(dup)
    check("a runtime record with a duplicate JSON member FAILS, exit 1",
          status == 1 and relation(view, kind_relation).get("status") == ev.FAILS
          and "duplicate" in relation(view, kind_relation).get("detail", ""),
          f"exit {status}")
    wrongkind = make_operand(temp / "wrong-kind", record={
        "kind": "warrant/something-else@v0", "tags": {
            "ski@v1": {"module": MODULE_PATH, "sha256": ev.sha256_bytes(MODULE)}}})
    status, view, err = view_of(wrongkind)
    check("a runtime record of the wrong kind FAILS and binds no tag",
          status == 1 and relation(view, kind_relation).get("status") == ev.FAILS
          and tag_of(view, "ski@v1").get("status") == "admitted_UNBOUND",
          f"exit {status}")

    # --- a record must not reach outside the operand it names -------------
    escape = make_operand(temp / "escape", record={
        "kind": ev.RUNTIME_RECORD_KIND,
        "tags": {"ski@v1": {"module": "../../../etc/passwd",
                            "sha256": ev.sha256_bytes(MODULE)}}})
    status, view, err = view_of(escape)
    tag = tag_of(view, "ski@v1")
    check("a module path escaping the operand is not read: "
          "admitted_module_MISSING",
          status == 1 and tag.get("status") == "admitted_module_MISSING"
          and tag.get("recomputed_sha256") is None,
          f"exit {status}, status {tag.get('status')!r}")

    return good


# ------------------------------ the runtime table has to say exactly ONE thing

def ambiguous_runtime_table(temp: Path):
    """A SPEC section 13.1 that says two things must project no tag status.

    Found by review of f3b7099: the parser kept a dict by tag, so a table
    carrying both `ski@v1 current` and `ski@v1 reserved` meant `admitted_pinned`
    or `record_spec_DISAGREE` purely by which row came last. Both orders are
    controlled below, through the CLI, and their answers must agree.
    """
    unique = "says one thing"
    reserved_v1 = "| `ski@v1` | — | reserved | §3.1 |\n"
    answers = {}
    for name, rows in {
        "the current row last": (reserved_v1, ROW_V1, ROW_V2),
        "the reserved row last": (ROW_V1, reserved_v1, ROW_V2),
    }.items():
        operand = make_operand(temp / f"duplicate-{len(answers)}", rows=rows)
        status, view, err = view_of(operand)
        tags = view["warrant"]["tags"] if view else {}
        check(f"DUPLICATE tag row, {name}: no tag status is projected, exit 1",
              status == 1 and tags.get("status") == "unavailable"
              and "listed more than once" in tags.get("reason", "")
              and relation(view, unique).get("status") == ev.FAILS
              and tag_of(view, "ski@v1") == {},
              f"exit {status}, tags {json.dumps(tags)[:160]}")
        answers[name] = (status, tags, relation(view, unique).get("status"))
    check("DUPLICATE tag rows: the same conflicting SPEC gets the same answer "
          "in either row order",
          len(set(map(json.dumps, answers.values()))) == 1,
          json.dumps(answers)[:200])

    # A row of the SELECTED table that this parser cannot read must not vanish
    # into a smaller closed set of tags that then all look well-formed. Too few
    # cells, and -- found by review of aef98ec -- too many, which the lazy
    # regex groups of the old row pattern happily swallowed.
    for name, row in {
        "two cells where four are declared":
            "| `ski@v3` | two cells only |\n",
        "extra pipes past the four declared cells":
            "| `ski@v3` | `0.2` | current | §3.1 | and | more |\n",
    }.items():
        malformed = make_operand(temp / f"malformed-row-{len(row)}",
                                 rows=(ROW_V1, row, ROW_V2))
        status, view, err = view_of(malformed)
        tags = view["warrant"]["tags"] if view else {}
        check(f"MALFORMED row, {name}: the unreadable row is named and no tag "
              "status is projected, exit 1",
              status == 1 and tags.get("status") == "unavailable"
              and "unreadable row" in tags.get("reason", "")
              and tag_of(view, "ski@v1") == {} and tag_of(view, "ski@v3") == {},
              f"exit {status}, tags {json.dumps(tags)[:160]}")

    second_table = ("\n| Tag | Body versions | Status | Defined in |\n"
                    "| --- | --- | --- | --- |\n")
    for name, spec in {
        "two `### 13.1.` headings": (
            SPEC_HEADER + ROW_V1 + "\n### 13.1. A second runtime section\n"
            + second_table + ROW_V2 + SPEC_FOOTER),
        "two tag tables in one section": (
            SPEC_HEADER + ROW_V1 + "\nintervening prose\n" + second_table
            + ROW_V2 + SPEC_FOOTER),
    }.items():
        operand = make_operand(temp / f"ambiguous-{len(name)}")
        write(operand / "SPEC.md", spec)
        status, view, err = view_of(operand)
        tags = view["warrant"]["tags"] if view else {}
        check(f"AMBIGUOUS: {name} projects no tag status, exit 1",
              status == 1 and tags.get("status") == "unavailable"
              and "must be unique" in tags.get("reason", "")
              and relation(view, unique).get("status") == ev.FAILS,
              f"exit {status}, tags {json.dumps(tags)[:160]}")

    # Found by review of aef98ec: membership of the runtime table was decided
    # by a row that MATCHED, which hid precisely the rows that did not. Both of
    # these read as a clean `ski@v1 admitted_pinned`, exit 0. The table is now
    # recognised by the header it declares.
    unheaded_row = "| ski@v1 | — | reserved | §3.1 |\n"
    for name, spec, needle in (
        ("a runtime-looking table that declares no header",
         "# Synthetic Warrant SPEC\n\n### 13.1. SKI runtime evaluators\n\n"
         + unheaded_row + ROW_V1 + ROW_V2 + SPEC_FOOTER, "must be unique"),
        ("a SECOND headed table whose only row is unreadable",
         SPEC_HEADER + ROW_V1 + ROW_V2 + second_table + unheaded_row
         + SPEC_FOOTER, "must be unique"),
        ("a runtime header with no separator row beneath it",
         "# Synthetic Warrant SPEC\n\n### 13.1. SKI runtime evaluators\n\n"
         "| Tag | Body versions | Status | Defined in |\n" + ROW_V1 + ROW_V2
         + SPEC_FOOTER, "separator row"),
    ):
        operand = make_operand(temp / f"unselected-{len(spec)}")
        write(operand / "SPEC.md", spec)
        status, view, err = view_of(operand)
        tags = view["warrant"]["tags"] if view else {}
        check(f"TABLE SELECTION: {name} projects no tag status, exit 1",
              status == 1 and tags.get("status") == "unavailable"
              and needle in tags.get("reason", "")
              and relation(view, unique).get("status") == ev.FAILS
              and tag_of(view, "ski@v1") == {},
              f"exit {status}, tags {json.dumps(tags)[:200]}")

    # The honest unavailable path for an older operand is NOT this failure.
    notable = make_operand(temp / "no-table-relation")
    write(notable / "SPEC.md", "# Synthetic Warrant SPEC\n\n### 13.2. Other\n")
    status, view, err = view_of(notable)
    check("an operand with no section 13.1 at all leaves the uniqueness "
          "relation unchecked, not failing, exit 0",
          status == 0 and relation(view, unique).get("status") == ev.UNCHECKED,
          f"exit {status}, {json.dumps(relation(view, unique))[:160]}")


# --------------------------- the adoption verdict comes from a completed run

FAKE_GOVERNANCE = """import sys
sys.stdout.write({stdout!r})
raise SystemExit({exit!r})
"""


def adoption_boundary(temp: Path):
    """What the view accepts as "this bundle is adopted", at the consumer edge.

    Found by review of f3b7099: it took any line beginning with the bundle name
    and called it authorized when the rest merely STARTED WITH `AUTHORIZED`,
    ignoring the producer's exit status. A run killed mid-output, and a token
    that only begins that way, both earned adoption credit. The producer here is
    replaced by a stub so the boundary can be driven directly; none of this is a
    claim that tools/anchor_governance.py ever prints these.
    """
    top = ev.vc.top_bundle()
    name = "is AUTHORIZED under the out-of-band trust anchor"
    operand = make_operand(temp / "adoption-operand")
    write(operand / ev.TRUST_ANCHOR, "{}")

    def outcome(label, stdout, exit_status):
        tree = stand_in_tree(temp / f"adoption-{label}", tools={
            "anchor_governance.py": FAKE_GOVERNANCE.format(stdout=stdout,
                                                           exit=exit_status)})
        done = run_view("--warrant", str(operand), tree=tree)
        view = json.loads(done.stdout) if done.stdout.strip() else {}
        return (done.returncode, view,
                view.get("sigma", {}).get("protocol", {}).get("adoption", {}),
                relation(view, name))

    status, view, adoption, rel = outcome(
        "authorized", f"{top}   AUTHORIZED — quorum reached\n", 0)
    check("ADOPTION: a completed run whose one status line is the exact token "
          "AUTHORIZED holds",
          status == 0 and adoption.get("status") == "authorized"
          and rel.get("status") == ev.HOLDS and adoption.get("exit") == 0,
          f"exit {status}, {json.dumps(adoption)[:200]}")

    status, view, adoption, rel = outcome(
        "died", f"{top} AUTHORIZED partial output before failure\n", 1)
    check("ADOPTION: a producer that printed AUTHORIZED and then FAILED earns "
          "no credit; the relation is unchecked and the exit is recorded",
          adoption.get("status") == "unavailable"
          and rel.get("status") == ev.UNCHECKED
          and adoption.get("exit") == 1 and "exited 1" in adoption.get("reason", ""),
          f"{json.dumps(adoption)[:220]}")

    status, view, adoption, rel = outcome(
        "foreign-token", f"{top} AUTHORIZED_BUT_REVOKED\n", 0)
    check("ADOPTION: a status token that merely BEGINS with AUTHORIZED is "
          "unrecognised, not an adoption",
          adoption.get("status") == "unavailable"
          and rel.get("status") == ev.UNCHECKED
          and "unrecognised token" in adoption.get("reason", ""),
          f"{json.dumps(adoption)[:220]}")

    # Found by review of aef98ec: the old `(?![\w-])` boundary let through any
    # foreign token whose extra character was neither a word character nor a
    # hyphen. The producer emits a whitespace-separated token, so these are two
    # different words, not adoptions.
    for label, token in (("slashed", "AUTHORIZED/REVOKED"),
                         ("dotted", "AUTHORIZED.v2"),
                         ("extra-word", "AUTHORIZED REVOKED")):
        status, view, adoption, rel = outcome(
            label, f"{top} {token} — quorum reached\n", 0)
        check(f"ADOPTION: {token} is a foreign token, not the exact token "
              "AUTHORIZED",
              adoption.get("status") == "unavailable"
              and rel.get("status") == ev.UNCHECKED
              and "unrecognised token" in adoption.get("reason", ""),
              f"{json.dumps(adoption)[:220]}")

    status, view, adoption, rel = outcome(
        "missing-delimiter", f"{top} AUTHORIZED\n", 0)
    check("ADOPTION: AUTHORIZED without the producer's delimiter is incomplete",
          adoption.get("status") == "unavailable"
          and rel.get("status") == ev.UNCHECKED,
          f"{json.dumps(adoption)[:220]}")

    status, view, adoption, rel = outcome(
        "not-authorized", f"{top} NOT AUTHORIZED — no anchor-set blob in store\n", 1)
    check("ADOPTION: a definite negative verdict FAILS the relation, exit 1",
          status == 1 and adoption.get("status") == "not_authorized"
          and rel.get("status") == ev.FAILS,
          f"exit {status}, {json.dumps(adoption)[:200]}")

    status, view, adoption, rel = outcome(
        "two-lines", f"{top} AUTHORIZED — one\n{top} NOT AUTHORIZED — two\n", 0)
    check("ADOPTION: two status lines for the same bundle are not one answer",
          adoption.get("status") == "unavailable"
          and rel.get("status") == ev.UNCHECKED
          and "2 status line(s)" in adoption.get("reason", "")
          and adoption.get("verdict_line") is None,
          f"{json.dumps(adoption)[:220]}")

    status, view, adoption, rel = outcome(
        "no-line", "ERR: trust config invalid (want sigma-glyph.anchor-trust@v1)\n", 1)
    check("ADOPTION: a run that said nothing about this bundle is unchecked, "
          "with the producer's own words kept",
          adoption.get("status") == "unavailable"
          and rel.get("status") == ev.UNCHECKED
          and "0 status line(s)" in adoption.get("reason", "")
          and "trust config invalid" in adoption.get("reason", ""),
          f"{json.dumps(adoption)[:220]}")


# ------------------------------- the receipt projection matches its predicate

def candidate_receipt(temp: Path):
    """The receipt claim must not exceed what the view actually checks.

    Found by review of f3b7099: the relation said the receipt "carries its
    closed fields" while an invented member or `artifact_sha256: null` still
    held, and a JSON list at the root raised AttributeError instead of a typed
    refusal. The claim is now the projection -- presence and type of the fields
    read -- so these controls pin BOTH halves: what is rejected, and what is
    deliberately ignored and therefore must not be claimed.
    """
    name = "the frozen candidate receipt is one unambiguous JSON object"
    real = json.loads((ROOT / ev.RECEIPT).read_text())

    def outcome(label, payload):
        tree = stand_in_tree(temp / f"receipt-{label}", receipt=payload)
        done = run_view(tree=tree)
        view = json.loads(done.stdout) if done.stdout.strip() else {}
        return (done.returncode, view,
                view.get("sigma", {}).get("candidate", {}),
                relation(view, name))

    status, view, candidate, rel = outcome("untouched", json.dumps(real))
    check("RECEIPT: the stand-in tree with the real receipt still holds "
          "(the fixture is faithful)",
          status == 0 and rel.get("status") == ev.HOLDS
          and candidate.get("status") == "frozen_receipt_referenced",
          f"exit {status}, {rel}")

    status, view, candidate, rel = outcome("list-root", "[]")
    check("RECEIPT: a JSON list at the root is a typed MALFORMED, not a "
          "traceback: one document is still printed, exit 1",
          status == 1 and view.get("kind") == ev.KIND
          and candidate.get("status") == "MALFORMED"
          and "not an object" in candidate.get("reason", "")
          and rel.get("status") == ev.FAILS,
          f"exit {status}, {json.dumps(candidate)[:200]}")

    status, view, candidate, rel = outcome("not-json", "{ this is not json")
    check("RECEIPT: bytes that are not JSON are MALFORMED, exit 1",
          status == 1 and candidate.get("status") == "MALFORMED"
          and rel.get("status") == ev.FAILS,
          f"exit {status}, {json.dumps(candidate)[:200]}")

    status, view, candidate, rel = outcome(
        "not-utf8", b'{"kind": "\xff\xfe not utf-8"}')
    check("RECEIPT: bytes that are not UTF-8 are MALFORMED, not a traceback",
          status == 1 and candidate.get("status") == "MALFORMED"
          and rel.get("status") == ev.FAILS,
          f"exit {status}, {json.dumps(candidate)[:200]}")

    status, view, candidate, rel = outcome(
        "duplicate-member",
        '{"kind": "%s", "kind": "other", "source_commit": "x"}' % ev.RECEIPT_KIND)
    check("RECEIPT: a duplicate JSON member is rejected here too, not only in "
          "the runtime record",
          status == 1 and candidate.get("status") == "MALFORMED"
          and "duplicate JSON member" in candidate.get("reason", "")
          and rel.get("status") == ev.FAILS,
          f"exit {status}, {json.dumps(candidate)[:200]}")

    status, view, candidate, rel = outcome(
        "null-digest", json.dumps({**real, "artifact_sha256": None}))
    check("RECEIPT: a projected field present but not a string FAILS and names "
          "the field and the type found",
          status == 1 and rel.get("status") == ev.FAILS
          and "artifact_sha256: a NoneType, not a string" in rel.get("detail", ""),
          f"exit {status}, {json.dumps(rel)[:200]}")

    status, view, candidate, rel = outcome(
        "checks-not-objects", json.dumps({**real, "checks_passed": ["a tool"]}))
    check("RECEIPT: checks_passed that is not a list of objects FAILS instead "
          "of being read as one",
          status == 1 and rel.get("status") == ev.FAILS
          and "checks_passed" in rel.get("detail", "")
          and candidate.get("checks_passed_tools") == [],
          f"exit {status}, {json.dumps(rel)[:200]}")

    status, view, candidate, rel = outcome(
        "unknown-member", json.dumps({**real, "invented_field": True}))
    check("RECEIPT: an unknown member is IGNORED, and the claim says so rather "
          "than calling the receipt closed",
          status == 0 and rel.get("status") == ev.HOLDS
          and "closed" not in rel.get("relation", "")
          and "not closed-schema validation" in candidate.get("projection_only", "")
          and candidate.get("projected_fields") == list(ev.RECEIPT_STRINGS)
          + ["checks_passed"],
          f"exit {status}, {json.dumps(candidate)[:200]}")


# -------------------------------------- the widening guard can itself go red

def guard_controls(good: Path):
    base = ev.build_view(ROOT, str(good))
    check("guard: the unmutated synthetic view has no credit problems",
          ev.credit_problems(base) == [], "; ".join(ev.credit_problems(base)))

    def mutated(name, mutate, needle):
        view = copy.deepcopy(base)
        mutate(view)
        problems = ev.credit_problems(view)
        check(f"guard refuses: {name}",
              any(needle in p for p in problems),
              f"problems {problems}")

    for badge in ev.NO_BADGE_KEYS:
        mutated(f"a top-level {badge!r} badge",
                lambda v, k=badge: v.update({k: True}),
                f"top-level {badge!r}")

    def credit_a_reserved_tag(view):
        view["warrant"]["tags"]["ski@v2"]["identity"] = {
            "status": "checked_from_bytes",
            "bytes_at_named_sigma_commit": "byte_identical"}
    mutated("identity credit under a reserved status", credit_a_reserved_tag,
            "identity credit under status reserved_no_evaluator")

    mutated("an unknown tag status",
            lambda v: v["warrant"]["tags"]["ski@v2"].update({"status": "fine"}),
            "unknown status")

    mutated("the live evaluator claiming a tag that is not admitted",
            lambda v: v["sigma"]["evaluators"]["live"].update(
                {"admitted_warrant_tags_pinned_to_these_bytes": ["ski@v2"]}),
            "not admitted_pinned")

    mutated("summary counts that disagree with the relations list",
            lambda v: v["summary"].update({"relations_holding": 99}),
            "summary counts disagree")

    mutated("unchecked relations counted as holding",
            lambda v: v["summary"].update(
                {"relations_unchecked": 0,
                 "relations_holding": v["summary"]["relations_holding"]
                 + v["summary"]["relations_unchecked"]}),
            "summary counts disagree")

    mutated("tag statuses reported while the operand is unavailable",
            lambda v: v["warrant"].update({"status": "unavailable"}),
            "Warrant operand is unavailable")


# ------------------------------------------- optional: a real Warrant operand

def real_operand(operand: str):
    """The invariants that must hold for ANY real Warrant checkout.

    Deliberately NOT "ski@v1 is admitted and ski@v2 is reserved": that is a fact
    about one revision, and asserting it here would make this control a second,
    hand-maintained copy of the Warrant record -- the exact thing the view was
    built not to be. Measured 2026-09-04: sigma's `WARRANT_PIN`
    (0d147aa1...) PREDATES trust/ski-runtime-evaluators.json, so at the pin
    the tags are correctly typed `unavailable` and an earlier draft of this
    control went red over the view behaving exactly as specified. The admitted
    and reserved statuses are covered by the synthetic controls above, where the
    operand's contents are ours to fix.
    """
    path = Path(operand)
    if not path.is_absolute() or not path.is_dir():
        check(f"real operand {operand} is an absolute directory", False)
        return
    status, view, err = view_of(path)
    check("real operand: a document is produced, not a refusal or a traceback",
          status in (0, 1) and view is not None,
          f"exit {status}: {err.strip()[-300:]}")
    if view is None:
        return
    check("real operand: nothing is widened into credit",
          ev.credit_problems(view) == [], "; ".join(ev.credit_problems(view)))

    warrant = view["warrant"]
    check("real operand: the Warrant half reports that it was read",
          warrant["status"] == "checked", warrant["status"])

    tags = warrant.get("tags", {})
    if tags.get("status") == "unavailable":
        check("real operand: unreadable tags are typed unavailable with a "
              "reason, and no tag status is reported",
              bool(tags.get("reason")) and len(tags) == 2, json.dumps(tags)[:200])
    else:
        unknown = {t: e.get("status") for t, e in tags.items()
                   if isinstance(e, dict) and e.get("status") not in ev.TAG_STATUSES}
        check("real operand: every tag status comes from the narrow vocabulary",
              not unknown, json.dumps(unknown))
        # The one substantive claim: a Sigma-side view cannot promote the
        # reserved tag, whatever the operand says.
        check("real operand: ski@v2 is not admitted by this view",
              tag_of(view, "ski@v2").get("status") != ev.ADMITTED,
              tag_of(view, "ski@v2").get("status"))

    revision = warrant["revision"]
    check("real operand: the operand revision is never presented as a pin",
          (revision["status"] == "observed"
           and "not a pinned artifact" in revision["note"])
          or (revision["status"] == "unavailable" and bool(revision["reason"])),
          json.dumps(revision)[:200])
    is_pin = warrant["ci_pin"]["operand_commit_is_pin"]
    check("real operand: 'this operand is the CI pin' is only claimed when the "
          "two commits are equal",
          is_pin is None or is_pin == (revision.get("commit")
                                       == warrant["ci_pin"]["pin"]),
          f"operand_commit_is_pin={is_pin}")


def main() -> int:
    operand = None
    argv = sys.argv[1:]
    if argv[:1] == ["--warrant"] and len(argv) == 2:
        operand = argv[1]
    elif argv:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2

    temp = Path(tempfile.mkdtemp(prefix="evidence-view-controls-"))
    try:
        positive_sigma(temp)
        refusals(temp)
        ambient(temp)
        good = warrant_half(temp)
        ambiguous_runtime_table(temp)
        adoption_boundary(temp)
        candidate_receipt(temp)
        guard_controls(good)
        if operand:
            real_operand(operand)
        else:
            print("note  no --warrant operand: the real-checkout positive "
                  "control did not run (the synthetic controls did)")
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    if failures:
        print(f"\nEVIDENCE-VIEW-CONTROLS: {len(failures)} FAILED")
        for name in failures:
            print(f"  - {name}")
        return 1
    print("\nEVIDENCE-VIEW-CONTROLS: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
