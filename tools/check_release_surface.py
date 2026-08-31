#!/usr/bin/env python3
"""Fail when the built wheel cannot do what the docs tell a stranger to do.

WHY THIS EXISTS
---------------
Every suite in this repository runs from a CHECKOUT, where `impl/` sits next to
`tests/spec_conformance/`. A wheel is a different artifact with a different
filesystem, and this gate exists because that difference shipped: when this file
was written nothing had been published yet, and the first time anyone ran the
0.6.6 wheel from a fresh venv:

    python -m sigma_wave        -> FAIL wave_vectors.json present   (13/14, exit 1)
    python -m sigma_federation  -> FileNotFoundError traceback       (exit 1)

Both are the same defect: a self-test that resolves its replay corpus relative to
`__file__` and treats "the distribution does not ship it" as "the check failed".
Green CI could not see it, because CI never installs the wheel. This gate is what
makes that state unpublishable rather than merely embarrassing on release day.

WHAT IT CHECKS
--------------
1. The WHEEL is read as a zip, first, before anything from it runs: name, version
   (against pyproject), and exactly which files ship.
2. The installed modules come from the venv's site-packages — not from a checkout
   that happens to be on `sys.path`. Every module the wheel claims is importable.
3. The three self-tests are run from a directory that is NOT the checkout, and
   their output is classified: exit 0, the machine tag present, no `FAIL`, no
   traceback, and the SKIP notices exactly where the wheel's contents say they
   must be.
4. The QUICKSTART "Compute one thing" snippet — the one piece of documented API
   a stranger types — is executed against the installed package and against the
   checkout, and the two outputs must be byte-identical. That is the documented
   claim ("Two strangers running this get byte-identical hashes"), executed.
5. EVERY VERB, not just the default one. See below.

EVERY VERB IS CLASSIFIED, AND EVERY VERB IS RUN
-----------------------------------------------
This gate used to run `python -m <module>` and nothing else. `sigma_wave gen` and
`sigma_federation gen` therefore shipped for four releases having never once been
executed from outside a checkout — where they end in a FileNotFoundError
traceback, because `_REPO` resolves to site-packages' parent. The same shape (a
verb the gate does not run) produced a live PyPI defect in the sibling `oaip`
project the same week.

So the modules DECLARE their verbs (`sigma_wave.VERBS`), this file CLASSIFIES
each one RUNNABLE or NOT_RUNNABLE for an installed copy, and the gate EXECUTES
all of them from outside a checkout. A verb the module declares and this table
does not classify fails the gate; so does a verb that behaves unlike its class.
Adding a verb without deciding what it does to a stranger is no longer possible
quietly.

NOT_RUNNABLE is a positive claim, not an exemption: the verb must REFUSE —
non-zero exit, a message that says what it needs — and must not traceback.
"It crashes, which is non-zero, so it passes" is exactly the confusion this
project keeps finding.

THE SKIP EXPECTATION IS GROUNDED, NOT ASSUMED
---------------------------------------------
Asserting "the replay is skipped" would rot the day someone ships the vectors as
package data: the skip would become wrong and the assertion would still pass. So
the expectation is DERIVED from the wheel's own file list (`expected_skips`). Ship
the corpora and this gate flips to demanding that the replay actually RAN.

    python3 tools/check_release_surface.py                        # this checkout
    python3 tools/check_release_surface.py --wheel W --bin V/bin   # the artifact
    python3 tools/check_release_surface.py --selftest              # the classifier

Exit 0 = the artifact under test behaves as documented.

WHERE IT STOPS
--------------
It does not verify signatures, does not check the Rust/Go implementations (they
do not ship in the wheel), and cannot test the OIDC publish path — that only
exists inside GitHub Actions. A green run here says the Python distribution is
honest about itself, nothing more.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALL_PASS = "ALL PASS"
WAVE_PASS = "WAVE: ALL PASS"
FEDERATION_PASS = "FEDERATION: ALL PASS"
REPLAY_SKIP = "recorded-vector replay"
CHECKOUT_REQUIRED = "requires a source checkout"

# The distribution's contract: these three modules, importable at top level.
MODULES = ("sigma_glyph", "sigma_wave", "sigma_federation")

# (module, machine tag the suite MUST print, floor on the number of OK lines)
#
# The floors are deliberate. A self-test that skipped EVERYTHING would still
# print its ALL PASS tag, and "ALL PASS (0/0)" must not be a release-blessing
# outcome. These numbers are what the property checks — the half that needs no
# repo data — counted when this gate was written. Raising one is a normal part of
# adding checks; lowering one is a claim that the artifact does less, and should
# have to be typed on purpose.
SUITES = (
    ("sigma_glyph", ALL_PASS, 35),
    ("sigma_wave", WAVE_PASS, 13),
    ("sigma_federation", FEDERATION_PASS, 15),
)

# Replay corpora live in the repo. If a build starts shipping them, the expected
# behaviour of the installed self-tests changes, and this map is where the gate
# finds that out (see `expected_skips`).
CORPORA = {
    "tests/spec_conformance/wave_vectors.json": ("sigma_wave", REPLAY_SKIP),
    "tests/spec_conformance/federation_vectors.json": ("sigma_federation", REPLAY_SKIP),
    "tests/spec_conformance/vectors.json": ("sigma_federation", "Book I unreachable fixture"),
}

TRACEBACK = "Traceback (most recent call last)"

# --------------------------------------------------------------------------
# The verb matrix. "" is the default, no-argument invocation.
#
# RUNNABLE     — a stranger with `pip install sigma-glyph` may type it and it
#                must work: exit 0, no traceback.
# NOT_RUNNABLE — it cannot work off a checkout, and must SAY SO: non-zero exit,
#                no traceback, and an explanation containing the given phrase.
#                The phrase is part of the contract; a bare non-zero exit tells
#                the user nothing and is what the FileNotFoundError already did.
#
# `gen` is NOT_RUNNABLE by decision, not by accident: it regenerates the
# conformance corpus, which is only meaningful beside the spec text its values
# are read off and the committed vectors the output must be diffed against.
# Shipping the corpus as package data would make the verb "run" while producing
# a file nobody can compare to anything — the appearance of the fix, not the fix.
# --------------------------------------------------------------------------
RUNNABLE = "RUNNABLE"
NOT_RUNNABLE = "NOT_RUNNABLE"

VERB_TABLE = {
    ("sigma_glyph", ""): (RUNNABLE, None),
    ("sigma_wave", ""): (RUNNABLE, None),
    ("sigma_federation", ""): (RUNNABLE, None),
    ("sigma_wave", "gen"): (NOT_RUNNABLE, CHECKOUT_REQUIRED),
    ("sigma_federation", "gen"): (NOT_RUNNABLE, CHECKOUT_REQUIRED),
}

# A verb name no module declares. Typing it must be refused, not silently
# treated as "run the self-test and report success for a command that does not
# exist" — which is what all three modules did before v0.6.7.
UNDECLARED_VERB = "no-such-verb"


# --------------------------------------------------------------------------
# ONE place that decides whether a self-test's output is acceptable. The
# --selftest mode drives this same function; a rule that lives in two places is
# the kind that drifts.
# --------------------------------------------------------------------------
def classify(module, tag, floor, rc, out, err, expected_skips):
    """Return a list of problems with one self-test run. Empty list = good."""
    problems = []
    if rc != 0:
        problems.append(f"{module}: exit {rc} (a documented suite must exit 0)")
    if TRACEBACK in err or TRACEBACK in out:
        first = [l for l in (err or out).splitlines() if l.strip()][-1:]
        problems.append(f"{module}: traceback — {first[0].strip() if first else '?'}")
    if tag not in out:
        problems.append(f"{module}: did not print {tag!r}")
    for line in out.splitlines():
        if line.startswith("FAIL"):
            problems.append(f"{module}: {line.strip()}")

    ran = sum(1 for l in out.splitlines() if l.startswith("OK"))
    if ran < floor:
        problems.append(f"{module}: only {ran} checks ran, expected at least "
                        f"{floor} — a suite that skipped its way to ALL PASS "
                        f"is not a passing suite")

    # Skips must match the artifact's actual contents, in BOTH directions.
    announced = {m.group(1).strip()
                 for m in re.finditer(r"^SKIP ([^:]+):", out, re.M)}
    for want in expected_skips:
        if want not in announced:
            problems.append(f"{module}: the artifact does not ship this suite's "
                            f"data, so {want!r} cannot run — but the run never "
                            f"said so. Silence is the defect; announce the skip")
    for got in announced - set(expected_skips):
        problems.append(f"{module}: skipped {got!r} although the data for it IS "
                        f"present. A skip that is not caused by a missing file "
                        f"is a check quietly not running")
    return problems


def classify_verb(module, verb, kind, needle, rc, out, err):
    """Return a list of problems with one VERB run outside a checkout."""
    what = f"{module} {verb}".strip() or module
    problems = []
    blob = out + err
    if TRACEBACK in blob:
        last = [l for l in blob.splitlines() if l.strip()][-1:]
        problems.append(f"{what}: traceback — {last[0].strip() if last else '?'}. "
                        f"A verb that cannot work off a checkout must say so, "
                        f"not crash")
        return problems                       # a traceback subsumes the rest
    if kind == RUNNABLE:
        if rc != 0:
            problems.append(f"{what}: exit {rc} — classified {RUNNABLE}, so an "
                            f"installed copy must be able to run it")
    elif kind == NOT_RUNNABLE:
        if rc == 0:
            problems.append(f"{what}: exit 0 — classified {NOT_RUNNABLE}, so it "
                            f"must refuse, and a refusal that reports success "
                            f"is the defect this table exists to catch")
        if needle and needle not in blob:
            problems.append(f"{what}: refused without saying why — the message "
                            f"must mention {needle!r}. A bare non-zero exit "
                            f"leaves the user no better off than the traceback")
    else:
        problems.append(f"{what}: unknown classification {kind!r}")
    return problems


def declared_verbs(python, cwd, module):
    """The verbs the MODULE declares, read from the artifact under test."""
    rc, out, err = run(python, ["-c", f"import {module} as m;"
                                      f"print(' '.join(getattr(m,'VERBS',())))"], cwd)
    if rc != 0:
        return None, [f"{module}: cannot read its VERBS declaration "
                      f"({(err.strip().splitlines() or [''])[-1]}) — without it "
                      f"this gate cannot know which verbs exist, and an "
                      f"unexercised verb is how `gen` shipped broken"]
    return tuple(out.split()), []


def _check_verb_inventory(module, declared, classified, problems):
    declared_set = set(declared) | {""}
    for verb in declared_set - classified:
        problems.append(
            f"{module}: verb {verb!r} is declared by the module but not "
            f"classified in VERB_TABLE. Classify it RUNNABLE or "
            f"{NOT_RUNNABLE} — a verb nobody decided about is a verb nobody "
            "runs from outside a checkout")
    for verb in classified - declared_set:
        problems.append(
            f"{module}: VERB_TABLE classifies {verb!r}, which the module no "
            "longer declares. The table is checking a verb that does not "
            "exist; delete the row or restore the verb")


def _run_module_verbs(python, verbdir, module, problems):
    for (table_module, verb), (kind, needle) in sorted(VERB_TABLE.items()):
        if table_module != module:
            continue
        rc, out, err = run(
            python, ["-m", table_module] + ([verb] if verb else []), verbdir)
        problems.extend(classify_verb(
            table_module, verb, kind, needle, rc, out, err))
    rc, out, err = run(python, ["-m", module, UNDECLARED_VERB], verbdir)
    problems.extend(classify_verb(module, UNDECLARED_VERB, NOT_RUNNABLE,
                                  UNDECLARED_VERB, rc, out, err))


def check_verbs(python, verbdir, problems):
    """Every declared verb classified, and every classified verb executed."""
    for module in MODULES:
        declared, errs = declared_verbs(python, verbdir, module)
        problems += errs
        if declared is None:
            continue
        classified = {verb for (mod, verb), _config in VERB_TABLE.items()
                      if mod == module}
        _check_verb_inventory(module, declared, classified, problems)
        _run_module_verbs(python, verbdir, module, problems)


def expected_skips(module, shipped):
    """What this module MUST announce as skipped, given what the wheel ships."""
    return [label for path, (mod, label) in CORPORA.items()
            if mod == module and path not in shipped]


# --------------------------------------------------------------------------
# The wheel is the provenance root: read it as a zip before running anything.
# --------------------------------------------------------------------------
def _version_problems(wheel_name, version):
    """The wheel's PUBLIC version must be pyproject's.

    A PEP 440 LOCAL segment (`+phase4a.<commit>`) is allowed on top of it, and
    only there: a candidate build has to be distinguishable from the published
    release of the same version, and a local segment is the one suffix PyPI
    refuses to accept, so it cannot become a release by accident. Renumbering
    the public part still fails, which is what this check was for.
    """
    declared = re.search(r'^version\s*=\s*"([^"]+)"',
                         (ROOT / "pyproject.toml").read_text(), re.M)
    if not declared:
        return []
    public, _, local = version.partition("+")
    if public != declared.group(1):
        return [f"{wheel_name}: wheel version {version} has public part "
                f"{public}, pyproject says {declared.group(1)}"]
    if local and not re.fullmatch(r"[a-z0-9]+(\.[a-z0-9]+)*", local):
        return [f"{wheel_name}: local version segment {local!r} is not a "
                f"PEP 440 local version"]
    return []


def inspect_wheel(wheel):
    problems = []
    if not wheel.is_file():
        return None, [f"no such wheel: {wheel}"]
    with zipfile.ZipFile(wheel) as z:
        names = set(z.namelist())
        meta = [n for n in names if n.endswith(".dist-info/METADATA")]
        if not meta:
            return None, [f"{wheel.name}: no dist-info/METADATA"]
        text = z.read(meta[0]).decode()
    info = {"name": None, "version": None, "files": names}
    for line in text.splitlines():
        if line.startswith("Name: "):
            info["name"] = line[6:].strip()
        elif line.startswith("Version: "):
            info["version"] = line[9:].strip()

    for m in MODULES:
        if f"{m}.py" not in names:
            problems.append(f"{wheel.name}: does not contain {m}.py — the "
                            f"distribution promises three top-level modules")

    problems += _version_problems(wheel.name, info["version"])
    dist = re.search(r'^name\s*=\s*"([^"]+)"', pyproject, re.M)
    if dist and (info["name"] or "").replace("_", "-") != dist.group(1):
        problems.append(f"{wheel.name}: wheel name {info['name']} != pyproject "
                        f"name {dist.group(1)}")
    return info, problems


def site_packages(binroot):
    venv = binroot.parent
    hits = (sorted(venv.glob("lib/python*/site-packages")) or
            sorted(venv.glob("Lib/site-packages")))
    return hits[0] if hits else None


def run(python, args, cwd, env=None):
    e = dict(os.environ)
    e.pop("PYTHONPATH", None)          # the checkout must not leak onto sys.path
    e.update(env or {})
    p = subprocess.run([python, *args], cwd=str(cwd), env=e,
                       capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


# --------------------------------------------------------------------------
# The documented snippet. QUICKSTART tells a stranger to run this and says two
# strangers get byte-identical hashes; that sentence is only true if the code
# in it exists in the artifact.
# --------------------------------------------------------------------------
SNIPPET_MARK = "sg.eval_hash"


def quickstart_snippet():
    """The fenced `python3 - <<'PY' ... PY` block from QUICKSTART.md."""
    text = (ROOT / "QUICKSTART.md").read_text()
    blocks = re.findall(r"<<'PY'\n(.*?)\nPY\n", text, re.S)
    for b in blocks:
        if SNIPPET_MARK in b:
            return b
    return None


def check_snippet(installed_python, problems):
    """Run the documented snippet. With an installed python, run it BOTH ways
    and require identical bytes; from a bare checkout there is no second copy to
    compare against, so only the documented checkout form is executed."""
    snip = quickstart_snippet()
    if snip is None:
        problems.append("QUICKSTART.md no longer contains the documented "
                        f"`{SNIPPET_MARK}` snippet — either restore it or stop "
                        "gating on it, but do not let it vanish silently")
        return
    # The checkout form needs its path insert; the installed form must NOT have
    # one, or it would be testing the checkout again.
    from_checkout = snip
    from_install = "\n".join(l for l in snip.splitlines()
                             if "sys.path.insert" not in l)
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "checkout_form.py"
        b = Path(td) / "install_form.py"
        a.write_text(from_checkout)
        b.write_text(from_install)
        rc1, out1, err1 = run(sys.executable, [str(a)], ROOT)
        if installed_python is None:
            rc2, out2, err2 = rc1, out1, err1
        else:
            rc2, out2, err2 = run(installed_python, [str(b)], td)
    if rc1 != 0:
        last = err1.strip().splitlines()[-1:] or [""]
        problems.append(f"QUICKSTART snippet fails in the checkout: {last[0]}")
        return
    if rc2 != 0:
        last = err2.strip().splitlines()[-1:] or [""]
        problems.append(f"QUICKSTART snippet fails against the installed "
                        f"package: {last[0]}")
        return
    if out1 != out2:
        problems.append("QUICKSTART snippet gives different output from the "
                        "installed package than from the checkout — "
                        f"checkout {out1.strip()!r} vs installed {out2.strip()!r}. "
                        "The page promises byte-identical results")


# --------------------------------------------------------------------------
def selftest():
    """Drive `classify` on recorded outputs, including the two real defects."""
    cases = []

    real_wave_fail = ("OK   a\nOK   b\nFAIL wave_vectors.json present run: "
                      "python3 impl/sigma_wave.py gen\n\n"
                      "WAVE: FAILURES PRESENT (13/14)\n")
    cases.append(("0.6.6 wheel, sigma_wave before the fix",
                  classify("sigma_wave", WAVE_PASS, 2, 1, real_wave_fail,
                           "", [REPLAY_SKIP]),
                  True))

    real_fed_crash = (TRACEBACK + "\n  File \"x\"\nFileNotFoundError: "
                      "vectors.json\n")
    cases.append(("0.6.6 wheel, sigma_federation before the fix",
                  classify("sigma_federation", FEDERATION_PASS, 2, 1, "",
                           real_fed_crash, [REPLAY_SKIP]),
                  True))

    good = ("OK   a\nOK   b\nSKIP recorded-vector replay: not shipped\n\n"
            "WAVE: ALL PASS (2/2) — SKIPPED: recorded-vector replay\n")
    cases.append(("fixed wheel, replay honestly skipped",
                  classify("sigma_wave", WAVE_PASS, 2, 0, good, "",
                           [REPLAY_SKIP]), False))

    cases.append(("a suite that skipped its way to ALL PASS",
                  classify("sigma_wave", WAVE_PASS, 13, 0,
                           "WAVE: ALL PASS (0/0)\n", "", []), True))

    cases.append(("a skip with no missing file behind it",
                  classify("sigma_wave", WAVE_PASS, 2, 0,
                           "OK   a\nOK   b\nSKIP recorded-vector replay: eh\n"
                           "WAVE: ALL PASS (2/2)\n", "", []), True))

    checkout_ok = "OK   a\nOK   b\n\nWAVE: ALL PASS (2/2)\n"
    cases.append(("checkout run, corpora present, nothing skipped",
                  classify("sigma_wave", WAVE_PASS, 2, 0, checkout_ok,
                           "", []), False))

    # ---- the verb matrix, driven on the REAL pre-fix behaviour ----------
    real_gen_crash = (TRACEBACK + '\n  File "sigma_wave.py", line 383\n'
                      "FileNotFoundError: [Errno 2] No such file or directory: "
                      "'.../lib/python3.14/tests/spec_conformance/"
                      "wave_vectors.json'\n")
    cases.append(("0.6.6 wheel, `sigma_wave gen` before the fix (traceback)",
                  classify_verb("sigma_wave", "gen", NOT_RUNNABLE,
                                CHECKOUT_REQUIRED, 1, "",
                                real_gen_crash), True))

    refusal = ("REFUSING: `gen` regenerates the conformance corpus at "
               "tests/spec_conformance/wave_vectors.json and requires a source "
               "checkout of sigma-glyph.\n")
    cases.append(("fixed wheel, `gen` refuses and says what it needs",
                  classify_verb("sigma_wave", "gen", NOT_RUNNABLE,
                                CHECKOUT_REQUIRED, 2, "", refusal),
                  False))

    cases.append(("a NOT_RUNNABLE verb that exits 0",
                  classify_verb("sigma_wave", "gen", NOT_RUNNABLE,
                                CHECKOUT_REQUIRED, 0, "", ""), True))

    cases.append(("a refusal that never says why",
                  classify_verb("sigma_wave", "gen", NOT_RUNNABLE,
                                CHECKOUT_REQUIRED, 2, "", "nope\n"),
                  True))

    cases.append(("a RUNNABLE verb that exits 0",
                  classify_verb("sigma_glyph", "", RUNNABLE, None, 0,
                                "ALL PASS\n", ""), False))

    # Division of labour, stated as a case: classify_verb judges the EXIT
    # STATUS and the traceback; whether the tally is honest is `classify`'s job
    # (the next case), and both run on every suite.
    cases.append(("classify_verb alone does not judge a tally",
                  classify_verb("sigma_glyph", "", RUNNABLE, None, 0,
                                "FAILURES PRESENT\n", ""), False))

    cases.append(("Book I before the fix: FAILURES PRESENT at exit 0",
                  classify("sigma_glyph", ALL_PASS, 2, 0,
                           "OK   a\nFAIL b\n\nFAILURES PRESENT\n", "", []),
                  True))

    cases.append(("a RUNNABLE verb that exits non-zero",
                  classify_verb("sigma_glyph", "", RUNNABLE, None, 1,
                                "FAILURES PRESENT\n", ""), True))

    ok = True
    for name, problems, want_problems in cases:
        good_case = bool(problems) == want_problems
        ok &= good_case
        print(("OK  " if good_case else "FAIL"), name,
              "" if good_case else f"-> {problems}")

    ship = set(CORPORA) | {"sigma_wave.py"}
    e1 = expected_skips("sigma_wave", ship)
    e2 = expected_skips("sigma_wave", {"sigma_wave.py"})
    for name, cond in (("corpora shipped -> no skip expected", e1 == []),
                       ("corpora absent -> replay skip expected",
                        e2 == [REPLAY_SKIP])):
        ok &= cond
        print(("OK  " if cond else "FAIL"), name)

    print("\nRELEASE-SURFACE-SELFTEST: " + (ALL_PASS if ok else "FAILURES"))
    return 0 if ok else 1


def _release_args():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("--wheel", help="the built wheel: the provenance root")
    ap.add_argument("--bin", help="bin/ of a venv the wheel is installed into")
    ap.add_argument("--selftest", action="store_true")
    return ap.parse_args()


def _release_scope(args, problems):
    if args.wheel:
        info, wproblems = inspect_wheel(Path(args.wheel).resolve())
        problems += wproblems
        if info is None:
            print("RELEASE SURFACE: FAIL\n")
            for problem in problems:
                print(f"  {problem}")
            return None
        return (info["files"],
                f"{info['name']} {info['version']} from {Path(args.wheel).name}")
    return set(CORPORA), "this checkout"


def _check_installed_imports(python, workdir, site, problems):
    for module in MODULES:
        rc, out, err = run(
            python, ["-c", f"import {module};print({module}.__file__)"], workdir)
        if rc != 0:
            last = (err.strip().splitlines() or [""])[-1]
            problems.append(f"{module}: not importable from the installed wheel "
                            f"({last})")
        elif site.resolve() not in Path(out.strip()).resolve().parents:
            problems.append(f"{module}: imported from {Path(out.strip()).resolve()}, "
                            f"which is not the installed package under {site} — "
                            "this run would test a checkout, not the artifact")


def _runtime_context(args, problems):
    if not args.bin:
        return sys.executable, str(ROOT)
    binroot = Path(args.bin).resolve()
    python = str(binroot / "python")
    if not Path(python).exists():
        python = str(binroot / "python3")
    site = site_packages(binroot)
    if site is None:
        print(f"RELEASE SURFACE: FAIL — no site-packages under {binroot.parent}")
        return None
    workdir = tempfile.mkdtemp(prefix="sigma-release-")
    _check_installed_imports(python, workdir, site, problems)
    return python, workdir


def _exercise_verbs(args, python, workdir, problems):
    if args.bin:
        check_verbs(python, workdir, problems)
    else:
        with tempfile.TemporaryDirectory(prefix="sigma-verbs-") as verbdir:
            for m in MODULES:
                shutil.copy(ROOT / "impl" / f"{m}.py", Path(verbdir) / f"{m}.py")
            check_verbs(python, verbdir, problems)


def _exercise_suites(args, python, workdir, shipped, problems):
    for module, tag, floor in SUITES:
        if args.bin:
            rc, out, err = run(python, ["-m", module], workdir)
        else:
            rc, out, err = run(python, [f"impl/{module}.py"], ROOT)
        problems += classify(module, tag, floor, rc, out, err,
                             expected_skips(module, shipped))
    check_snippet(python if args.bin else None, problems)


def _report_release(args, target, problems):
    if problems:
        print(f"RELEASE SURFACE: FAIL — {target} does not behave as documented "
              f"({len(problems)} problem(s)):\n")
        for p in problems:
            print(f"  {p}")
        print("\nA stranger who runs `pip install sigma-glyph` and then the "
              "documented\ncommands must not see a FAIL line or a traceback.")
        return 1
    # Say what was actually done, not what the release path does. Checkout mode
    # never imports from site-packages and has no second copy to compare the
    # snippet against; claiming otherwise here would be the same species of
    # untruth this file exists to catch.
    nverbs = len(VERB_TABLE) + len(MODULES)          # + the undeclared-verb probe
    did = (f"three modules import from site-packages, three self-tests clean "
           f"from outside the checkout, {nverbs} verb invocations behave as "
           f"classified, documented snippet reproduces byte-identically"
           if args.bin else
           f"three self-tests clean, {nverbs} verb invocations behave as "
           f"classified against a non-checkout copy of impl/, documented "
           f"snippet runs — NOT an artifact check; pass --wheel/--bin for that")
    print(f"RELEASE SURFACE: ALL PASS ({target}: {did})")
    return 0


# --------------------------------------------------------------------------
def main():
    args = _release_args()
    if args.selftest:
        return selftest()
    if args.bin and not args.wheel:
        print("RELEASE SURFACE: REFUSING — --bin without --wheel.\n\n"
              "  An installation cannot vouch for itself. Pass the wheel that\n"
              "  will be published; what ships is what decides which checks\n"
              "  are allowed to skip.", file=sys.stderr)
        return 2
    problems = []
    scope = _release_scope(args, problems)
    if scope is None:
        return 1
    shipped, target = scope
    runtime = _runtime_context(args, problems)
    if runtime is None:
        return 1
    python, workdir = runtime
    _exercise_verbs(args, python, workdir, problems)
    _exercise_suites(args, python, workdir, shipped, problems)
    return _report_release(args, target, problems)


if __name__ == "__main__":
    sys.exit(main())
