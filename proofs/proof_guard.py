#!/usr/bin/env python3
"""Shared soundness guard for the Lean proof bridges (proofs/*_bridge_check.py).

Why this exists: a 2026-07 fresh-context adversarial review demonstrated two
vectors that compiled clean under `lean` (exit 0) AND passed every bridge's
old textual guard:

  1. `:= sorryAx _ true` — the old `\\b(sorry|admit)\\b` regex needs a word
     boundary, and `sorryAx` (what `sorry` desugars to) has none after "sorry".
  2. `private axiom oops : False` — the old `^\\s*axiom` regex is anchored to
     line start, so any modifier or attribute (`private`, `protected`,
     `noncomputable`, `@[...]`) before the keyword defeats it.

Two layers, strongest first:

* `axiom_guard()` — the semantic check: `#print axioms <thm>` for every
  load-bearing theorem, asserted against an allowed set (the standard axioms
  `propext`, `Classical.choice`, `Quot.sound`, plus per-theorem `native_decide`
  trust axioms only where the documented TCB already includes the compiler).
  The kernel tracks the transitive axiom dependencies of the actual proof
  term, so this catches ANY unsoundness route — `sorryAx`, prefixed axioms,
  custom tactics — regardless of how the source text is spelled.
* `textual_guard()` — the cheap second layer: comments stripped, then any
  `sorry`/`admit` SUBSTRING (catches `sorryAx`) or `axiom` keyword anywhere
  in the code (catches `private axiom`) fails.
"""
import os
import re
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

#: Axioms of the Lean 4 standard library that a clean classical proof may use.
STD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

#: Shape of the per-declaration trust axioms `native_decide` introduces
#: (Lean >= 4.x names them `<decl>._native.native_decide.ax_*`). Declaring an
#: axiom that mimics this shape requires the `axiom` keyword, which
#: `textual_guard` rejects.
_NATIVE_DECIDE = re.compile(r"^[A-Za-z0-9_.']+\._native\.native_decide\.ax[_0-9]+$")


def find_lean():
    """Absolute path to a `lean` binary, honoring $LEAN; None if unavailable."""
    cand = os.environ.get("LEAN")
    if cand:
        return cand if os.path.sep in cand and os.path.exists(cand) \
            else shutil.which(cand)
    found = shutil.which("lean")
    if found:
        return found
    elan = os.path.join(os.path.expanduser("~"), ".elan", "bin", "lean")
    return elan if os.path.exists(elan) else None


def strip_lean_comments(src):
    """Remove `--` line comments and (nested) `/- ... -/` block comments."""
    out, i, n, depth = [], 0, len(src), 0
    while i < n:
        if src.startswith("/-", i):
            depth += 1
            i += 2
        elif depth and src.startswith("-/", i):
            depth -= 1
            i += 2
        elif depth:
            i += 1
        elif src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def textual_guard(path):
    """List of problems found in the comment-stripped source (empty = clean).

    Substring matching on purpose: `sorryAx` must fail, and a false positive
    on an exotic-but-legit identifier is the safe direction (fail closed).
    """
    body = strip_lean_comments(open(path).read())
    problems = []
    if "sorry" in body:
        problems.append("`sorry` substring (catches sorryAx too)")
    if "admit" in body:
        problems.append("`admit` substring")
    if re.search(r"\baxiom\b", body):
        problems.append("`axiom` keyword (any position, incl. `private axiom`)")
    return problems


def build_olean(lean, module, olean_dir, src_dir=HERE):
    """Compile proofs/<module>.lean to <olean_dir>/<module>.olean.

    Returns an error string, or None on success. `lean` requires the input
    file under its root dir, so we run with cwd=src_dir and a relative path;
    LEAN_PATH points at olean_dir so already-built modules resolve.
    """
    r = subprocess.run(
        [lean, module + ".lean", "-o", os.path.join(olean_dir, module + ".olean")],
        capture_output=True, text=True, cwd=src_dir,
        env=dict(os.environ, LEAN_PATH=olean_dir))
    if r.returncode != 0:
        return (f"{module}.lean does not compile: "
                + (r.stderr or r.stdout).strip()[:500])
    return None


def print_axioms(lean, imports, theorems, olean_dir):
    """Run `#print axioms` for each theorem; return {theorem: [axiom, ...]}.

    Raises RuntimeError if lean fails (e.g. a theorem name no longer exists —
    a renamed/deleted load-bearing theorem must fail the bridge, not skip).
    """
    src = ("".join(f"import {m}\n" for m in imports)
           + "".join(f"#print axioms {t}\n" for t in theorems))
    qpath = os.path.join(olean_dir, "AxiomQuery.lean")
    with open(qpath, "w") as f:
        f.write(src)
    r = subprocess.run([lean, "AxiomQuery.lean"], capture_output=True, text=True,
                       cwd=olean_dir, env=dict(os.environ, LEAN_PATH=olean_dir))
    if r.returncode != 0:
        raise RuntimeError("#print axioms query failed (missing theorem?): "
                           + (r.stderr or r.stdout).strip()[:500])
    text = re.sub(r"\n\s+", " ", r.stdout)       # unwrap wrapped axiom lists
    got = {}
    for name, axs in re.findall(r"'([^']+)' depends on axioms: \[([^\]]*)\]", text):
        got[name] = [a.strip() for a in axs.split(",") if a.strip()]
    for name in re.findall(r"'([^']+)' does not depend on any axioms", text):
        got.setdefault(name, [])
    return got


def axiom_guard(lean, imports, theorems, olean_dir, native_decide_ok=frozenset()):
    """Assert every theorem's axiom set is within the allowed TCB.

    `native_decide_ok`: theorem names (as passed) additionally allowed to
    depend on `native_decide` trust axioms — ONLY the fronts whose documented
    TCB already includes the Lean compiler (see proofs/README.md).
    Returns an error string, or None if all theorems are clean.
    """
    try:
        got = print_axioms(lean, imports, theorems, olean_dir)
    except RuntimeError as e:
        return str(e)
    bad = []
    for t in theorems:
        if t not in got:
            bad.append(f"{t}: no #print axioms output (theorem missing?)")
            continue
        for ax in got[t]:
            if ax in STD_AXIOMS:
                continue
            if t in native_decide_ok and _NATIVE_DECIDE.match(ax):
                continue
            bad.append(f"{t} depends on disallowed axiom: {ax}")
    return "; ".join(bad) if bad else None
