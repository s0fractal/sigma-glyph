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


def run_view(*args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k not in ev.AMBIENT}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(VIEW), *args], cwd=str(ROOT),
                          capture_output=True, text=True, env=env, check=False)


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
