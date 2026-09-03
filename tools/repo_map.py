#!/usr/bin/env python3
"""Resolve every document this repository names, and say where it actually is.

WHY THIS EXISTS
---------------
Four separate reviews in three days produced findings that were artefacts of not
knowing what was being looked at:

  * "the X1 files are missing from warrant" -- they were on master; the reviewer
    was reading a working tree parked on a feature branch;
  * "warrant-go prints 33/33" -- it prints 49/49; the reviewer read an archived
    evidence blob from an old run;
  * "the sibling pin is three weeks stale" -- it was same-day;
  * "ADR-008 lives only on unpushed branches, so this is a dangling reference" --
    it is on a pushed branch, publicly readable, just not on master.

The last one is the honest core of the class: `master` names ADR-008 six times,
ADR-004 twice and WRT-002 once, and none of them resolve here. A reader is left
to guess whether the document is missing, renamed, secret, or somewhere else --
and every reviewer guessed differently.

None of those were careless reviewers. They were reviewers without a map.

This generates the map from git, so it cannot drift the way a hand-written
inventory does -- two hand-written counts in this repository were wrong by 25
conformance vectors and one whole PyPI release until 2026-07-29.

WHAT IT DOES NOT DO
-------------------
It reports *where a document is*, never whether it is adopted, correct, or in
force. Location is a fact about git; status is a fact about governance, and
conflating the two is how "present on a branch" becomes "in effect".

USAGE
    python3 tools/repo_map.py            # write MAP.md
    python3 tools/repo_map.py --check    # non-zero if any reference resolves nowhere
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _main_checkout(root):
    """The main working tree, even when `root` is a linked worktree.

    `--git-common-dir` points at the ORIGINAL repository's `.git` for every
    linked worktree, so this is the one directory every worktree of a repo
    agrees on.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--path-format=absolute",
         "--git-common-dir"], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return root
    common = Path(result.stdout.strip())
    return common.parent if common.name == ".git" else root


def _find_sibling(root):
    """Locate the paired repository without asking what this directory is called.

    This was `root.parent / ("sigma-glyph" if root.name == "warrant" else
    "warrant")`, which reads the DIRECTORY NAME. Run from a worktree named
    `sigma-glyph-surface`, it looked for `warrant` beside the worktree, found
    nothing, and silently downgraded a resolved MAP row to "resolves nowhere" —
    a wrong answer rather than an error, in the tool whose whole job is to
    refuse unresolved citations.

    The repository is identified by its remote instead, and the search starts
    from the MAIN checkout so linked worktrees behave like it.
    """
    remote = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                            capture_output=True, text=True)
    this = "warrant" if "/warrant" in remote.stdout else "sigma-glyph"
    wanted = "sigma-glyph" if this == "warrant" else "warrant"
    for base in (_main_checkout(root).parent, root.parent):
        candidate = base / wanted
        if (candidate / ".git").exists():
            return candidate
    return _main_checkout(root).parent / wanted


SIBLING = _find_sibling(ROOT)

# Identifiers this project cites as if the reader knows where they live.
ID_RE = re.compile(r"\b(ADR-\d{3}|WRT-\d{3}|GOV-\d{3}|Book\s+I{1,3})\b")

# Identifiers whose filename does not contain the citation string. "Book I" is
# cited nine times in this repository and lives in a file called
# book-1-truth.md, so a substring search finds nothing and would report the most
# heavily cited document in the project as resolving nowhere.
ALIASES = {"Book I": "book-1", "Book II": "book-2", "Book III": "book-3"}
SCAN = ("SPEC.md", "README.md", "ARCHITECT.md", "ROADMAP.md")
SCAN_DIRS = ("proposals", "briefs", "spec", "profiles")


def git(repo, *args, ok_fail=False):
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    if r.returncode and not ok_fail:
        return ""
    return r.stdout


def refs_of(repo):
    """Local branches, origin branches and preserved archive tags."""
    out = []
    # Filter on the FULL refname: the short form of refs/remotes/origin/HEAD is
    # bare "origin", which does not end in "/HEAD" and so slipped through as a
    # local branch. MAP.md then listed a branch named `origin` marked "on origin:
    # no" -- a ref that does not exist, in the generated file a reviewer reads to
    # find out which refs do.
    for line in git(repo, "for-each-ref", "--format=%(refname)\t%(refname:short)",
                    "refs/heads", "refs/remotes/origin",
                    "refs/tags/archive").splitlines():
        full, _, short = line.partition("\t")
        if short and not full.endswith("/HEAD"):
            out.append(short)
    # master first: if a document is on the trunk that is the answer worth giving
    out.sort(key=lambda r: (r.split("/")[-1] != "master", r))
    return out


def find(repo, ident):
    """Every (ref, path) where a document with this identifier exists."""
    ident = ALIASES.get(" ".join(ident.split()), ident)
    hits = []
    seen_paths = set()
    for ref in refs_of(repo):
        matches = [p for p in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()
                   if ident.lower() in p.lower()]
        # Prefer the normative text over a translation of it. `Book I` matched
        # book-1-truth.en.md, the informative English rendering, and pointing a
        # reviewer at a translation while calling it the citation target is the
        # same ambiguity this file exists to remove.
        # Prefer the document over data that merely carries the identifier in
        # its filename: `ADR-009` resolved to an anchor-set blob because the blob's
        # path was shorter than the ADR's, which pointed a reader at bytes when
        # they asked for a decision record.
        matches.sort(key=lambda p: (not p.endswith(".md"), ".en." in p,
                                    "/archive/" in p, len(p)))
        for path in matches:
            if path not in seen_paths:
                hits.append((ref, path))
                seen_paths.add(path)
    return hits


def cited(repo):
    """Identifiers named by this repository's own normative and proposal text."""
    ids = {}
    files = [f for f in SCAN if (repo / f).exists()]
    for d in SCAN_DIRS:
        if (repo / d).is_dir():
            files += [str(p.relative_to(repo)) for p in (repo / d).rglob("*.md")]
    for f in files:
        try:
            text = (repo / f).read_text(errors="replace")
        except OSError:
            continue
        for m in ID_RE.findall(text):
            ids.setdefault(" ".join(m.split()), set()).add(f)
    return ids


def resolve(ident):
    here = find(ROOT, ident)
    there = find(SIBLING, ident) if SIBLING.exists() else []
    return here, there


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="non-zero if a citation resolves on no known ref; "
                         "needs the sibling repository checked out")
    ap.add_argument("--check-map", action="store_true",
                    help="non-zero if a citation is absent from the committed "
                         "MAP.md; works without the sibling, so CI can run it")
    ap.add_argument("--selftest", action="store_true",
                    help="prove --check-map can fail on the branch under "
                         "review, in a real detached shallow clone")
    return ap.parse_args()


def citation_rows(ids):
    rows, unresolved = [], []
    for ident in sorted(ids):
        here, there = resolve(ident)
        if here:
            ref, path = here[0]
            where = f"this repo, `{ref}`", f"`{path}`"
        elif there:
            ref, path = there[0]
            where = f"**{SIBLING.name}**, `{ref}`", f"`{path}`"
        else:
            where = ("**resolves nowhere**", "—")
            unresolved.append(ident)
        rows.append((ident, where[0], where[1], min(ids[ident])))
    return rows, unresolved


def check_committed_map(ids):
    path = ROOT / "MAP.md"
    if not path.exists():
        print("MAP.md is missing; run tools/repo_map.py", file=sys.stderr)
        return 1
    text = path.read_text()
    missing = [ident for ident in sorted(ids) if f"`{ident}`" not in text]
    for ident in missing:
        print(f"UNMAPPED: {ident} is cited but has no row in MAP.md -- "
              "regenerate with tools/repo_map.py", file=sys.stderr)
    stale = [line for line in text.splitlines() if "resolves nowhere" in line]
    for line in stale:
        print(f"UNRESOLVED in MAP.md: {line.strip()}", file=sys.stderr)
    wrong, unverifiable, absent = check_rows_resolve(text)
    print(f"REPO-MAP: {len(ids) - len(missing)}/{len(ids)} citations mapped, "
          f"{len(stale)} unresolved, {unverifiable} row(s) in a sibling repo and "
          f"{absent} whose ref this checkout does not have")
    return 1 if missing or stale or wrong else 0


REMOTE = "origin/"
TICK = "`"


def _row_ref_and_path(cells):
    """`(ref, path)` for a citation row, or `None` if the row is not one."""
    if len(cells) < 5 or not cells[1].startswith(TICK) or cells[2] == "Lives in":
        return None
    where, quoted = cells[2], cells[3]
    if "this repo" not in where:
        return "sibling", ""
    ref = where.split(TICK)[1] if TICK in where else "master"
    path = quoted.split(TICK)[1] if TICK in quoted else ""
    return (ref, path) if path else None


def _ref_is_live(ref):
    """A remote-tracking ref the remote no longer has resolves only here."""
    if ref.startswith("archive/"):
        return subprocess.run(
            ["git", "-C", str(ROOT), "ls-remote", "--exit-code", "--tags",
             "origin", f"refs/tags/{ref}"], capture_output=True).returncode == 0
    if not ref.startswith(REMOTE):
        return True
    # The branch under review is live by definition — we are standing on it.
    # Without this, a row naming the PR's own branch is reported STALE REF
    # whenever `ls-remote` cannot see it, and the row then fails for the wrong
    # reason: "the remote does not have this branch" instead of "this path is
    # not there". Two different defects must not share one message.
    if ref[len(REMOTE):] in _current_branch_names():
        return True
    return subprocess.run(
        ["git", "-C", str(ROOT), "ls-remote", "--exit-code", "--heads",
         "origin", ref.split("/", 1)[1]], capture_output=True).returncode == 0


def _current_branch_names():
    """Every name by which THIS checkout is the branch under review.

    A pull-request checkout is detached and has no local branch, so a row naming
    the PR's own branch was reported UNCHECKED and the gate exited 0. That is
    how a MAP row pointing at a renamed file passed CI: not by being verified,
    but by being unverifiable. `GITHUB_HEAD_REF` is the branch name on a
    pull_request event; `GITHUB_REF_NAME` covers the push event.
    """
    names = set()
    for variable in ("GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
        value = os.environ.get(variable, "").strip()
        if value:
            names.add(value)
    current = subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"],
                             capture_output=True, text=True)
    if current.returncode == 0 and current.stdout.strip():
        names.add(current.stdout.strip())
    return names


def _resolvable(ref, path):
    """Which spellings of `ref` this checkout has, and whether any holds `path`."""
    spellings = [ref, f"{REMOTE}{ref}", f"refs/remotes/{REMOTE}{ref}",
                 f"refs/tags/{ref}"]
    # If the row names the branch we are standing on, HEAD *is* that branch —
    # detached or not. Checking it here is what makes the row under review
    # verifiable in CI rather than skipped.
    #
    # Compare with the remote prefix removed: rows are written `origin/<branch>`
    # while GITHUB_HEAD_REF is the bare name, and matching them literally missed
    # every time — which left the row under review UNCHECKED exactly as before.
    bare = ref[len(REMOTE):] if ref.startswith(REMOTE) else ref
    if bare in _current_branch_names():
        spellings.insert(0, "HEAD")
    present = [r for r in spellings
               if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify",
                                  "--quiet", r], capture_output=True).returncode == 0]
    if not present:
        return None
    return any(subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{r}:{path}"],
                              capture_output=True).returncode == 0 for r in present)


def check_rows_resolve(text):
    """Does each row's (ref, path) actually hold that document?

    Checking that an identifier appears somewhere in MAP.md is a check whose
    subject can be an arbitrary sentence: a row could name any ref and any path
    and still pass. A map whose rows are unverified is a map that cannot be cited
    as evidence of where anything lives, which is the only thing it is for.
    """
    wrong = unverifiable = absent = 0
    # Only the citation table. The refs table below it lists branches rather than
    # documents, and counting its rows as sibling citations reported nineteen
    # unverifiable rows where there is one — a true check with a false scope.
    for line in text.split("## Refs that exist", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        row = _row_ref_and_path(cells)
        if row is None:
            continue
        ref, path = row
        if ref == "sibling":
            unverifiable += 1
        elif not _ref_is_live(ref):
            wrong += 1
            print(f"STALE REF: MAP.md says {cells[1]} lives at {ref}, which the "
                  "remote does not have. It resolves only in this checkout",
                  file=sys.stderr)
        else:
            # Not being able to look is a different fact from looking and finding
            # nothing: a shallow checkout has no local branches, and collapsing
            # the two would make this fire hardest where it is least informative.
            held = _resolvable(ref, path)
            if held is None:
                absent += 1
                print(f"UNCHECKED: MAP.md says {cells[1]} lives at {ref}, which "
                      "this checkout does not have. Fetch it to verify the row",
                      file=sys.stderr)
            elif not held:
                wrong += 1
                print(f"MISPLACED: MAP.md says {cells[1]} lives at {ref}:{path}, "
                      "and no such object is there. A row nobody resolves is a "
                      "row that can say anything", file=sys.stderr)
    return wrong, unverifiable, absent


def check_resolutions(rows, unresolved):
    for ident in unresolved:
        print(f"UNRESOLVED: {ident} is cited but exists in neither repository "
              "on any local or origin ref", file=sys.stderr)
    print(f"REPO-MAP: {len(rows) - len(unresolved)}/{len(rows)} references resolve")
    return 1 if unresolved else 0


def map_header(origin, head, rows):
    output = [
        "# Map — where the documents this repository names actually live",
        "",
        "<!-- GENERATED by tools/repo_map.py. Do not edit; regenerate. -->",
        "",
        f"Repository `{origin}`, generated at commit `{head[:12]}`.",
        "",
        "This answers one question and only one: **given a document identifier",
        "cited somewhere in this repository, which ref holds it.** It says nothing",
        "about whether that document is adopted, correct, or in force — location is",
        "a fact about git, status is a fact about governance, and treating the",
        "first as the second is how \"present on a branch\" turns into \"in effect\".",
        "",
        "If you are reviewing this project: check the ref before reporting anything",
        "absent. Four reviews in three days reported things missing that were",
        "present on a ref the reviewer was not looking at.",
        "",
        "| Cited | Lives in | Path | First cited by |",
        "|---|---|---|---|",
    ]
    for ident, where, path, by in rows:
        output.append(f"| `{ident}` | {where} | {path} | `{by}` |")
    return output


def append_refs(output):
    output += [
        "",
        "## Refs that exist",
        "",
        "A branch is not the trunk, and an `archive/…` tag is preserved history.",
        "Both are readable and citable; neither is thereby **in force**.",
        "",
        "| Ref | Head | On origin |",
        "|---|---|---|",
    ]
    # Branches that exist ONLY on origin belong here too. Listing local refs
    # alone under-reported what a reader can fetch: after five merged branches
    # were deleted locally they vanished from the map while still being cited in
    # commit history, so the file answering "which refs exist" stopped answering
    # it. Deleting them was tidy; letting the map forget them was not.
    local = [r for r in refs_of(ROOT) if not r.startswith("origin/")]
    remote = {r.split("/", 1)[1] for r in refs_of(ROOT) if r.startswith("origin/")}
    for ref in local:
        sha = git(ROOT, "rev-parse", "--short", ref).strip()
        if ref.startswith("archive/"):
            on_origin = "yes (tag)" if _ref_is_live(ref) else "**no**"
        else:
            on_origin = "yes" if ref in remote else "**no**"
        output.append(f"| `{ref}` | `{sha}` | {on_origin} |")
    for ref in sorted(remote - set(local)):
        sha = git(ROOT, "rev-parse", "--short", f"origin/{ref}").strip()
        output.append(f"| `{ref}` | `{sha}` | origin only (fetch it) |")


def write_map(origin, head, rows, unresolved):
    output = map_header(origin, head, rows)
    append_refs(output)

    if unresolved:
        output += ["", "## Cited and resolving nowhere", "",
                   "These are named by this repository and exist in neither repository",
                   "on any ref known here. Either the document is unpublished, or the",
                   "citation is wrong; both are defects and neither is the reader's to",
                   "guess about.", ""]
        output += [f"- `{ident}`" for ident in unresolved]

    (ROOT / "MAP.md").write_text("\n".join(output) + "\n")
    print(f"MAP.md written: {len(rows)} references, {len(unresolved)} unresolved")
    return 0


def _first_citation_row(text):
    """`(identifier, ref_cell, path_cell)` of the first citation row.

    Any row will do: the control rewrites its ref and path, so what the row
    originally said is irrelevant. Taking one from the map rather than
    inventing a line keeps the surrounding table shape exactly as the parser
    expects it.
    """
    for line in text.split("## Refs that exist", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if _row_ref_and_path(cells) is None:
            continue
        if "this repo" not in cells[2]:
            continue
        return cells[1].strip("`"), cells[2], cells[3]
    return None


def selftest():
    """A wrong path must fail where CI actually stands: detached and shallow.

    The gate exited 0 on a MAP row pointing at a file that had been renamed,
    because a pull-request checkout is detached, the row named a branch this
    checkout had no local ref for, and "cannot look" was reported as UNCHECKED.
    The wrong row passed BY BEING UNVERIFIABLE.

    So the control reproduces that environment rather than describing it: a real
    `--depth 1` clone, checked out detached, with `GITHUB_HEAD_REF` set the way
    the pull_request event sets it.
    """
    import shutil
    import tempfile

    branch = (subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"],
                             capture_output=True, text=True).stdout.strip()
              or os.environ.get("GITHUB_HEAD_REF", ""))
    if not branch:
        print("SELFTEST: no current branch to stand in for the PR branch",
              file=sys.stderr)
        return 1

    failures = []
    work = tempfile.mkdtemp(prefix="repo-map-selftest-")
    try:
        # Built from HEAD's SHA, never from a branch name: in CI this runs
        # inside an ALREADY detached checkout, where `clone --branch <name>`
        # fails outright — which is how the first CI run of this control died.
        clone = Path(work) / "checkout"
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        steps = [
            ["git", "init", "--quiet", str(clone)],
            ["git", "-C", str(clone), "remote", "add", "origin", f"file://{ROOT}"],
            ["git", "-C", str(clone), "fetch", "--quiet", "--depth", "1",
             "origin", head],
            ["git", "-C", str(clone), "checkout", "--quiet", "--detach",
             "FETCH_HEAD"],
        ]
        for step in steps:
            done = subprocess.run(step, capture_output=True, text=True)
            if done.returncode != 0:
                print(f"SELFTEST: {' '.join(step[:4])} failed: "
                      f"{done.stderr.strip()[:200]}", file=sys.stderr)
                return 1
        # Give the clone the base ref too. actions/checkout leaves origin refs
        # present; without this the clone fails for reasons that have nothing to
        # do with the control, and a control that cannot pass on a healthy tree
        # proves nothing when it fails on a broken one.
        # Prefer the source's REMOTE-TRACKING master. Fetching plain `master`
        # takes that repository's local branch, which in a worktree checkout is
        # whatever it last had checked out — stale, and the staleness showed up
        # as a baseline MISPLACED that had nothing to do with the mutation.
        for spelling in ("refs/remotes/origin/master:refs/remotes/origin/master",
                         "master:refs/remotes/origin/master"):
            if subprocess.run(["git", "-C", str(clone), "fetch", "--quiet",
                               "--depth", "1", "origin", spelling],
                              capture_output=True).returncode == 0:
                break
        detached = subprocess.run(["git", "-C", str(clone), "branch",
                                   "--show-current"], capture_output=True,
                                  text=True).stdout.strip()
        if detached:
            failures.append("the clone is not detached, so the control would "
                            "not reproduce CI")

        environment = dict(os.environ, GITHUB_HEAD_REF=branch)

        def check(label):
            done = subprocess.run([sys.executable, "tools/repo_map.py",
                                   "--check-map"], cwd=clone, env=environment,
                                  capture_output=True, text=True)
            print(f"    {label}: exit {done.returncode}")
            return done

        # What this control is about is MISPLACED discrimination, not the
        # health of the inner clone. In CI the outer workspace is itself
        # shallow, so the inner clone cannot fetch a base ref and reports rows
        # it genuinely cannot see; asserting a clean baseline there made the
        # control fail for a reason that has nothing to do with the defect.
        # Baseline health is therefore reported, not required — and the
        # discriminating assertions are on MISPLACED.
        clean = check("unmodified map")
        if clean.returncode != 0:
            print("    (baseline is not clean in this environment; the "
                  "assertions below are on MISPLACED, which is the property "
                  "under test)")
        if "MISPLACED" in clean.stderr:
            failures.append("the unmodified map already reports MISPLACED, so "
                            "the mutation below would prove nothing")

        book = clone / "MAP.md"
        original = book.read_text()
        # Pick the target row from the map rather than naming one. This
        # hardcoded `ADR-012`, whose row named the feature branch; once that
        # branch merged, the row named `master`, the control's target was no
        # longer "the branch under review", and the selftest failed on master
        # for a reason that had nothing to do with the property it guards.
        # The control builds the row it tests, instead of hoping the map
        # contains a suitable one.
        #
        # Two earlier versions depended on the environment: one hardcoded the
        # ADR-012 row, which stopped naming the branch under review the moment
        # that branch merged; the next fell back to a master-owned row, which
        # CI cannot resolve at all, because a pull_request checkout has no
        # master ref. Both times the control could not test its property and
        # said so as a failure — better than passing, but still not a test.
        #
        # A row naming the branch under review resolves through HEAD, and HEAD
        # is the one ref every checkout has. So: point some citation row at
        # this branch and at a file that IS at HEAD, then at one that is not.
        book = clone / "MAP.md"
        original = book.read_text()

        anchor = _first_citation_row(original)
        if anchor is None:
            failures.append("MAP.md has no citation row to rewrite")
            broken = present = original
            target = None
        else:
            identifier, ref_cell, path_cell = anchor
            here = subprocess.run(["git", "-C", str(clone), "ls-tree", "-r",
                                   "--name-only", "HEAD", "proposals/"],
                                  capture_output=True, text=True).stdout.split()
            real = here[0] if here else None
            if real is None:
                failures.append("HEAD carries no proposals/ document to point a "
                                "row at")
                broken = present = original
                target = None
            else:
                target = (identifier, real)
                print(f"    row rewritten to name {branch} -> {real}")

                def row(path):
                    return original.replace(
                        f"| `{identifier}` | {ref_cell} | {path_cell} |",
                        f"| `{identifier}` | this repo, `{REMOTE}{branch}` | "
                        f"`{path}` |", 1)

                present = row(real)
                broken = row("proposals/NOT-THERE.md")
                if present == original or broken == original:
                    failures.append("could not rewrite the anchor row")

        # A row naming this branch and a file that IS here must not be MISPLACED.
        book.write_text(present)
        good = check(f"{target[0] if target else 'a'} row naming {branch}, "
                     f"pointing at a file that is here")
        if "MISPLACED" in good.stderr:
            failures.append("a row naming the branch under review and a file "
                            "that IS at HEAD was reported MISPLACED")

        # The same row pointing at a file that is not here must be.
        book.write_text(broken)
        dirty = check(f"{target[0] if target else 'a'} row naming {branch}, "
                      f"pointing at a file that is not")
        wanted = target[0] if target else ""
        misplaced = [line for line in dirty.stderr.splitlines()
                     if "MISPLACED" in line and wanted and wanted in line]
        if not misplaced:
            failures.append("a wrong path for the CURRENT branch's document was "
                            "not reported MISPLACED in a detached shallow "
                            "checkout — the exact hole this control exists for")
        elif dirty.returncode == 0:
            failures.append("it was reported MISPLACED but the gate still "
                            "exited 0")
        else:
            print(f"    -> {misplaced[0][:110]}")

        book.write_text(original)
        restored = check("map restored")
        if "MISPLACED" in restored.stderr:
            failures.append("MISPLACED persists after restoring the map")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print()
    for problem in failures:
        print(f"  FAIL  {problem}", file=sys.stderr)
    if failures:
        print(f"REPO-MAP-SELFTEST: FAILURES ({len(failures)})")
        return 1
    print("REPO-MAP-SELFTEST: ALL PASS — a wrong current-branch path fails "
          "even detached and shallow")
    return 0


def main():
    args = parse_args()
    if getattr(args, "selftest", False):
        return selftest()
    ids = cited(ROOT)
    rows, unresolved = citation_rows(ids)
    if args.check_map:
        return check_committed_map(ids)
    if args.check:
        return check_resolutions(rows, unresolved)
    head = git(ROOT, "rev-parse", "HEAD").strip()
    origin = git(ROOT, "remote", "get-url", "origin").strip()
    return write_map(origin, head, rows, unresolved)


if __name__ == "__main__":
    sys.exit(main())
