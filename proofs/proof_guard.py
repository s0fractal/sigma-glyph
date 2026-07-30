#!/usr/bin/env python3
"""Shared soundness guard for the Lean proof bridges (proofs/*_bridge_check.py).

Why this exists: `lean` exits 0 on a file whose proofs are `sorry`ed (it is a
warning), so "CI compiled the proofs" is not "CI checked the proofs". Two
successive fresh-context adversarial reviews (2026-07) each broke the
then-current guard; what follows is the third iteration, and its scope is
stated honestly — it enforces *specific* properties, it is not a proof that no
unsoundness route exists.

Round 1 (killed by the previous iteration, still covered by the regressions):
  * `:= sorryAx _ true` — a `\\b(sorry|admit)\\b` regex needs a word boundary
    and `sorryAx` has none after "sorry";
  * `private axiom oops : False` — a `^\\s*axiom` regex is anchored to line
    start, so any modifier/attribute before the keyword defeats it.

Round 2 (what this file now closes):
  * **F1 — vacuous theorems.** The guard checked axiom cones but never the
    theorem STATEMENT, so `theorem memory_bound : True := trivial` passed with
    "std axioms only". Every guarded theorem's elaborated type is now pinned
    (`proofs/theorem_pins.json`) and compared against the environment.
  * **F2a — the stripper was blindable.** `def blind : String := "/-"` opened a
    block comment *for the stripper*, hiding an `axiom oops : False` from the
    textual layer. The lexer below is string/char/raw-string aware and blanks
    literal contents instead of parsing them.
  * **F2b — the query was spoofable by the audited file.** The old query wrote
    a `.lean` file that `import`ed the audited module and ran `#print axioms`,
    so the audited module could override that syntax and dictate the guard's
    input. Axioms and statements now come from a driver that loads the audited
    module's `.olean` as DATA (`Lean.Environment.importModules`) and walks the
    kernel environment itself — no elaboration of the audited module's syntax,
    no reliance on its precomputed axiom table.
  * **F2c — `import Lean`.** These are core-Lean-only proofs; an import outside
    the proofs/ module set is a hard failure (it is what made F2b spellable).
  * **F3 — compiler-override metaprogramming.** `@[implemented_by]` +
    `native_decide` proves arbitrary falsehoods, and `@[implemented_by]`/
    `@[extern]` decouple `lean --run` (the differential harnesses) from the
    kernel definition. Attributes are allowlisted and the metaprogramming
    commands (`macro`/`syntax`/`elab`/`initialize`/`run_cmd`/`unsafe`/
    `attribute`/non-linter `set_option`/`#`-commands …) are denied outright.
  * **Coverage.** A hardcoded theorem list never queries a NEW poisoned
    theorem; every `theorem`/`lemma` in proofs/*.lean must now be either
    guarded or explicitly registered as intentionally-unguarded, and an
    anonymous `example` (which can never be axiom-checked) is an error.

Layers, strongest first:

* `guard_semantics()` — environment query: for every guarded theorem, the
  transitive axiom cone must sit inside that front's allowed set, and the
  canonical dump of its elaborated type must equal the pinned dump. Anything
  unobtainable (missing theorem, driver failure) is an error, never a skip.
* `guard_sources()` — the cheap layer over the source text: literal-aware
  comment stripping, then sorry/admit/axiom, the import allowlist, the
  metaprogramming denylist, and the coverage registry.

What this does NOT claim: the runner files (`*Run.lean`) are I/O plumbing that
*calls* the proven model; nothing here proves a runner reports what the model
computed (it could simply print the expected answers). That faithfulness is a
review matter, and the denylist only removes the mechanical ways to decouple
compiled code from the kernel definitions.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PINS_PATH = os.path.join(HERE, "theorem_pins.json")

#: Axioms of the Lean 4 standard library that a clean classical proof may use.
#: Per-front allowances live in the pin registry (C1 is tightened to `propext`
#: alone, which is what proofs/README.md claims for that front).
STD_AXIOMS = ("propext", "Classical.choice", "Quot.sound")

#: Shape of the per-declaration trust axioms `native_decide` introduces
#: (Lean >= 4.x names them `<decl>._native.native_decide.ax_*`). Allowed only
#: for the theorems whose documented TCB already includes the compiler.
_NATIVE_DECIDE = re.compile(r"^[^\s]+\._native\.native_decide\.ax[_0-9]+$")


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


# --------------------------------------------------------------------------
# layer 2: the source text
# --------------------------------------------------------------------------

_IDENT_CH = re.compile(r"[A-Za-z0-9_'!?ⁿ¹²³₀-₉α-ωΑ-Ω.]")
_CHAR_LIT = re.compile(r"'(?:[^'\\\n]|\\(?:x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|.))'")
_RAW_OPEN = re.compile(r'r(#*)"')


def strip_lean_source(src):
    """Comment-strip `src` and BLANK every literal's contents.

    Returns `(body, problems)`. Literal awareness is the point: the previous
    stripper parsed `"/-"` inside a string literal as a block-comment opener
    and silently dropped the rest of the file, so an `axiom oops : False`
    after it was invisible to the textual layer (F2a). Literal *contents*
    cannot smuggle unsoundness, so they are replaced with an empty literal
    rather than scanned. A literal or comment still open at EOF means our
    lexer and Lean's disagree about the file — that is reported, not ignored
    (fail closed).
    """
    out, i, n, depth, prev = [], 0, len(src), 0, ""
    while i < n:
        if depth:
            if src.startswith("/-", i):
                depth += 1
                i += 2
            elif src.startswith("-/", i):
                depth -= 1
                i += 2
            else:
                i += 1
            continue
        if src.startswith("/-", i):
            depth += 1
            i += 2
            continue
        if src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        m = _RAW_OPEN.match(src, i)
        if m:
            close = '"' + m.group(1)
            j = src.find(close, m.end())
            if j < 0:
                return "".join(out), ["unterminated raw string literal"]
            out.append('r""')
            prev, i = '"', j + len(close)
            continue
        if src[i] == '"':
            j, closed = i + 1, False
            while j < n:
                if src[j] == "\\":
                    j += 2
                elif src[j] == '"':
                    closed = True
                    j += 1
                    break
                else:
                    j += 1
            if not closed:
                return "".join(out), ["unterminated string literal"]
            out.append('""')
            prev, i = '"', j
            continue
        if src[i] == "'" and not _IDENT_CH.match(prev or " "):
            m = _CHAR_LIT.match(src, i)
            if m:
                out.append("''")
                prev, i = "'", m.end()
                continue
        out.append(src[i])
        prev, i = src[i], i + 1
    if depth:
        return "".join(out), ["unterminated block comment"]
    return "".join(out), []


def strip_lean_comments(src):
    """Back-compat wrapper: the stripped body only (see strip_lean_source)."""
    return strip_lean_source(src)[0]


#: Attributes an audited proof file may carry. Everything else is denied,
#: which is how `@[implemented_by …]`, `@[extern …]`, `@[csimp]`,
#: `@[command_elab …]` and `@[app_unexpander …]` are refused (F3): an
#: allowlist cannot be defeated by a spelling we failed to imagine.
#: `inline` (Sha256.lean) is a compiler hint that cannot change a definition's
#: meaning; `simp`/`reducible` only steer elaboration.
ALLOWED_ATTRS = frozenset({"inline", "simp", "reducible"})

#: Commands/modifiers that let a file reach outside the "core Lean, kernel
#: definitions only" contract these proofs claim. Reason strings are printed.
_DENY = [
    (r"\bimplemented_by\b", "`implemented_by` replaces compiled code, so "
     "`native_decide`/`lean --run` stop matching the kernel definition"),
    (r"\bextern\b", "`extern` binds a declaration to foreign code"),
    (r"\bcsimp\b", "`csimp` rewrites compiled code"),
    (r"\b(?:builtin_)?initialize\b", "`initialize` runs code at import time"),
    (r"\brun_cmd\b", "`run_cmd` runs arbitrary metaprogram at elaboration"),
    (r"\bunsafe\b", "`unsafe` bypasses the kernel"),
    (r"\bmacro(?:_rules)?\b", "macros can redefine the meaning of any syntax"),
    (r"\bsyntax\b", "new syntax can shadow commands the guard depends on"),
    (r"\belab(?:_rules)?\b", "custom elaborators can produce unchecked terms"),
    (r"\bnotation\b|\binfix[lr]?\b|\bprefix\b|\bpostfix\b",
     "notation can make the printed form disagree with the term"),
    (r"\bopaque\b", "`opaque` hides a definition from the kernel while the "
     "compiler still runs a body"),
    (r"\battribute\b", "`attribute` can apply a denied attribute out of line"),
    (r"#[A-Za-z_][A-Za-z0-9_]*", "`#`-commands (`#eval`, `#check`, …) run at "
     "elaboration time and can modify the environment"),
    (r"sorry", "`sorry` substring — no word boundary, so `sorryAx` (what "
     "`sorry` desugars to) is caught as well"),
    (r"admit", "`admit` substring"),
    (r"\baxiom\b", "`axiom` keyword (any position, incl. `private axiom`)"),
]

#: `partial def` makes the kernel see an opaque constant while the compiler
#: runs a body — the same decoupling as `implemented_by`. Legitimate in the
#: `*Run.lean` I/O loops (which prove nothing), denied in the model files.
_RUNNER_ONLY = [(r"\bpartial\b", "`partial` leaves the kernel without a "
                 "definition while compiled code has one")]


def _decl_names(body):
    """[(kind, fully-qualified name or None, line)] for the declarations that
    the guard has to account for (theorem/lemma/example)."""
    stack, out = [], []
    for lineno, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        m = re.match(r"namespace\s+([^\s]+)", s)
        if m:
            stack.append(("ns", m.group(1)))
            continue
        if re.match(r"section\b", s):
            stack.append(("sec", re.sub(r"^section\s*", "", s) or None))
            continue
        m = re.match(r"end\b\s*([^\s]*)", s)
        if m:
            want = m.group(1) or None
            if stack and (want is None or stack[-1][1] == want):
                stack.pop()
            continue
        m = re.match(r"(?:@\[[^\]]*\]\s*)*"
                     r"(?:(?:private|protected|noncomputable|nonrec|scoped)\s+)*"
                     r"(theorem|lemma|example)\b[ \t]*([^\s:({\[⦃⟨]*)", s)
        if not m:
            continue
        kind, name = m.group(1), m.group(2) or None
        if name:
            prefix = ".".join(n for k, n in stack if k == "ns")
            name = f"{prefix}.{name}" if prefix else name
        out.append((kind, name, lineno))
    return out


def source_guard(path, profile="strict"):
    """Problems found in one audited Lean source file (empty list = clean).

    `profile="runner"` relaxes only `partial` (the `*Run.lean` I/O loops).
    Substring/allowlist matching on purpose: a false positive on an
    exotic-but-legit spelling is the safe direction (fail closed) — the fix is
    to widen an allowlist deliberately, in a reviewed diff.
    """
    src = open(path).read()
    body, problems = strip_lean_source(src)
    if problems:                                  # lexer disagreement: stop here
        return [f"{p} (our lexer and Lean's disagree about this file)"
                for p in problems]

    rules = list(_DENY) + ([] if profile == "runner" else _RUNNER_ONLY)
    for pat, why in rules:
        m = re.search(pat, body)
        if m:
            problems.append(f"`{m.group(0)}` — {why}")

    for m in re.finditer(r"@\[([^\]]*)\]", body):
        for entry in m.group(1).split(","):
            head = entry.strip().split(" ")[0].lstrip("-!")
            if head and head not in ALLOWED_ATTRS:
                problems.append(
                    f"attribute `@[{entry.strip()}]` is not in the allowlist "
                    f"{sorted(ALLOWED_ATTRS)} (F3: attributes are how compiled "
                    "code is decoupled from kernel definitions)")

    for m in re.finditer(r"\bset_option\s+([^\s]+)", body):
        if not m.group(1).startswith("linter."):
            problems.append(f"`set_option {m.group(1)}` — only `linter.*` "
                            "options are allowed (soundness flags such as "
                            "`debug.skipKernelTC` live in this namespace)")

    allowed_imports = {os.path.splitext(f)[0]
                       for f in os.listdir(os.path.dirname(os.path.abspath(path)))
                       if f.endswith(".lean")}
    for m in re.finditer(r"^[ \t]*import[ \t]+(.+)$", body, re.M):
        for mod in m.group(1).split():
            if mod not in allowed_imports:
                problems.append(
                    f"`import {mod}` is outside the proofs/ module set "
                    f"{sorted(allowed_imports)} — these are core-Lean-only "
                    "proofs, and `import Lean` is what makes the guard's own "
                    "query spoofable (F2b)")
    return problems


def textual_guard(path):
    """Back-compat name for `source_guard(path)` (strict profile)."""
    return source_guard(path)


def coverage_guard(pins=None, proofs_dir=HERE):
    """Every theorem in proofs/*.lean is guarded or registered as unguarded.

    A hardcoded theorem list means a NEW theorem is never queried: a poisoned
    one could be added to a guarded FILE and no bridge would look at it. This
    makes an unaccounted-for declaration a hard failure, and rejects anonymous
    `example`s outright — they have no name, so `#print axioms` / the
    environment query can never reach them (the C1 §6/TV-10 pins used to be
    `example`s and a falsified pin passed).
    """
    pins = load_pins() if pins is None else pins
    known = set(pins.get("unguarded", {}))
    for front in pins.get("fronts", {}).values():
        known.update(front.get("guarded", []))
    problems = []
    for f in sorted(os.listdir(proofs_dir)):
        if not f.endswith(".lean"):
            continue
        body, lex = strip_lean_source(open(os.path.join(proofs_dir, f)).read())
        if lex:
            problems.append(f"{f}: {lex[0]}")
            continue
        for kind, name, lineno in _decl_names(body):
            if kind == "example":
                problems.append(
                    f"{f}:{lineno}: anonymous `example` cannot be reached by "
                    "the environment query — give it a name and register it")
            elif name not in known:
                problems.append(
                    f"{f}:{lineno}: `{name}` is in neither a front's guarded "
                    "list nor `unguarded` in theorem_pins.json (a new theorem "
                    "must be classified deliberately)")
    return problems


# --------------------------------------------------------------------------
# layer 1: the environment query (axioms + statements)
# --------------------------------------------------------------------------

#: The driver. It imports `Lean` (it is a metaprogram, not an audited proof),
#: loads the audited modules' `.olean`s as DATA, and walks the kernel
#: environment itself. The audited module is never elaborated here, so it
#: cannot override syntax, run `initialize` code, or otherwise choose what the
#: guard sees (F2b). Axioms are collected from constant bodies rather than
#: read out of the module's precomputed `collectAxioms` table. Types are
#: dumped structurally — binder names and `mdata` dropped, so the dump is
#: alpha-invariant — instead of pretty-printed, so no notation/delaborator can
#: make the printed statement differ from the elaborated one.
GUARD_DRIVER = r'''
import Lean
open Lean

partial def dumpLevel : Level → String
  | .zero => "0"
  | .succ l => "(s " ++ dumpLevel l ++ ")"
  | .max a b => "(max " ++ dumpLevel a ++ " " ++ dumpLevel b ++ ")"
  | .imax a b => "(imax " ++ dumpLevel a ++ " " ++ dumpLevel b ++ ")"
  | .param n => "(p " ++ toString n ++ ")"
  | .mvar _ => "(lmvar)"

partial def dumpExpr : Expr → String
  | .bvar i => "#" ++ toString i
  | .fvar id => "(fvar " ++ toString id.name ++ ")"
  | .mvar _ => "(mvar)"
  | .sort u => "(sort " ++ dumpLevel u ++ ")"
  | .const n us =>
      "(const " ++ toString n ++ " [" ++ String.intercalate " " (us.map dumpLevel) ++ "])"
  | .app f a => "(app " ++ dumpExpr f ++ " " ++ dumpExpr a ++ ")"
  | .lam _ t b _ => "(lam " ++ dumpExpr t ++ " " ++ dumpExpr b ++ ")"
  | .forallE _ t b _ => "(all " ++ dumpExpr t ++ " " ++ dumpExpr b ++ ")"
  | .letE _ t v b _ => "(let " ++ dumpExpr t ++ " " ++ dumpExpr v ++ " " ++ dumpExpr b ++ ")"
  | .lit (.natVal n) => "(natLit " ++ toString n ++ ")"
  | .lit (.strVal s) => "(strLit " ++ toString s.length ++ ")"
  | .mdata _ b => dumpExpr b
  | .proj s i b => "(proj " ++ toString s ++ " " ++ toString i ++ " " ++ dumpExpr b ++ ")"

abbrev CM := StateM (NameSet × NameSet)

/-- Transitive axiom cone of `c`, walked over the kernel environment. -/
partial def collectName (env : Environment) (c : Name) : CM Unit := do
  if (← get).1.contains c then return
  modify fun (s, a) => (s.insert c, a)
  let visit (e : Expr) : CM Unit := e.getUsedConstants.forM (collectName env)
  match env.find? c with
  | none => return
  | some (.axiomInfo v) => modify (fun (s, a) => (s, a.insert c)); visit v.type
  | some (.defnInfo v) => visit v.type; visit v.value
  | some (.thmInfo v) => visit v.type; visit v.value
  | some (.opaqueInfo v) => visit v.type; visit v.value
  | some (.quotInfo _) => return
  | some (.ctorInfo v) => visit v.type
  | some (.recInfo v) => visit v.type
  | some (.inductInfo v) => visit v.type; v.ctors.forM (collectName env)

def main (args : List String) : IO UInt32 := do
  let mods := (args.takeWhile (· != "--")).map String.toName
  let decls := (args.dropWhile (· != "--")).drop 1
  initSearchPath (← findSysroot)
  let imps : Array Import := (mods.map fun m => ({ module := m } : Import)).toArray
  let env ← importModules imps {} 0
  for d in decls do
    let n := d.toName
    match env.find? n with
    | none => IO.println ("MISSING " ++ d)
    | some info =>
      let (_, axs) := (collectName env n).run ({}, {}) |>.2
      let names := (axs.toArray.qsort Name.lt).map toString
      IO.println ("DECL " ++ d)
      IO.println ("AXIOMS " ++ String.intercalate " " names.toList)
      IO.println ("TYPE " ++ dumpExpr info.type)
  IO.println "DRIVER-COMPLETE"
  return 0
'''


def build_olean(lean, module, olean_dir, src_dir=HERE):
    """Compile <src_dir>/<module>.lean to <olean_dir>/<module>.olean.

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


def env_query(lean, modules, decls, olean_dir):
    """{decl: {"axioms": [...], "type": "<canonical dump>"}} for every decl.

    Raises RuntimeError on anything short of a complete answer — a missing
    (renamed/deleted) theorem, a driver crash, truncated output. The bridges
    turn that into a failure, never a skip.
    """
    if not decls:
        raise RuntimeError("no theorems to query — an empty guarded list "
                           "would pass vacuously")
    qpath = os.path.join(olean_dir, "SigmaGuardDriver.lean")
    with open(qpath, "w") as f:
        f.write(GUARD_DRIVER)
    r = subprocess.run([lean, "--run", qpath] + list(modules) + ["--"]
                       + list(decls), capture_output=True, text=True,
                       cwd=olean_dir, env=dict(os.environ, LEAN_PATH=olean_dir))
    if r.returncode != 0:
        raise RuntimeError("environment query failed: "
                           + (r.stderr or r.stdout).strip()[:500])
    lines = r.stdout.splitlines()
    if "DRIVER-COMPLETE" not in lines:
        raise RuntimeError("environment query produced no completion marker: "
                           + (r.stdout + r.stderr).strip()[:500])
    got, cur = {}, None
    for line in lines:
        if line.startswith("MISSING "):
            raise RuntimeError(f"declaration not in the environment: "
                               f"{line[8:]} (renamed or deleted?)")
        if line.startswith("DECL "):
            cur = line[5:]
            got[cur] = {"axioms": [], "type": None}
        elif line.startswith("AXIOMS ") and cur:
            got[cur]["axioms"] = line[7:].split()
        elif line.startswith("TYPE ") and cur:
            got[cur]["type"] = " ".join(line[5:].split())
    missing = [d for d in decls if d not in got or not got[d]["type"]]
    if missing:
        raise RuntimeError("no environment answer for: " + ", ".join(missing))
    return got


def load_pins(path=PINS_PATH):
    """The pin registry. A missing/unreadable registry is an error, not a skip."""
    with open(path) as f:
        return json.load(f)


def load_front(name, path=PINS_PATH):
    """One front's guard configuration, with the shared maps attached."""
    pins = load_pins(path)
    front = dict(pins["fronts"][name])
    front["name"] = name
    front["statements"] = pins["statements"]
    front["_pins"] = pins
    return front


def guard_semantics(lean, front, olean_dir):
    """Axiom cone AND pinned statement for every guarded theorem of `front`.

    Returns an error string, or None if the front is clean. Fails closed on
    every unobtainable answer, and on an empty guarded list (which would
    otherwise pass vacuously).
    """
    theorems = list(front.get("guarded", []))
    if not theorems:
        return (f"front {front.get('name')!r} has an empty guarded list — "
                "nothing would be checked")
    allowed = set(front.get("allowed_axioms", STD_AXIOMS))
    native_ok = set(front.get("native_decide_ok", []))
    pinned = front["statements"]
    try:
        got = env_query(lean, front["modules"], theorems, olean_dir)
    except RuntimeError as e:
        return str(e)
    bad = []
    for t in theorems:
        for ax in got[t]["axioms"]:
            if ax in allowed:
                continue
            if t in native_ok and _NATIVE_DECIDE.match(ax):
                continue
            bad.append(f"{t} depends on disallowed axiom: {ax}")
        want = pinned.get(t)
        if want is None:
            bad.append(f"{t} has no pinned statement in "
                       f"{os.path.basename(PINS_PATH)} — refusing to certify "
                       "an unpinned theorem")
            continue
        want = " ".join(want.split())
        if got[t]["type"] != want:
            bad.append(f"{t}: STATEMENT DRIFT — the theorem no longer says "
                       f"what it is pinned to say.\n    pinned:  {want}\n"
                       f"    actual:  {got[t]['type']}\n"
                       f"    first difference at char {_first_diff(want, got[t]['type'])}")
    return "; ".join(bad) if bad else None


def _first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"{i}: pinned …{a[max(0, i - 30):i + 30]}… vs actual …{b[max(0, i - 30):i + 30]}…"
    return f"{min(len(a), len(b))}: one is a prefix of the other"


def guard_sources(front, proofs_dir=HERE):
    """The source layer for a front: its own files, plus repo-wide coverage."""
    problems = []
    for f in front.get("strict_sources", []):
        problems += [f"{f}: {p}" for p in
                     source_guard(os.path.join(proofs_dir, f), "strict")]
    for f in front.get("runner_sources", []):
        problems += [f"{f}: {p}" for p in
                     source_guard(os.path.join(proofs_dir, f), "runner")]
    problems += coverage_guard(front.get("_pins"), proofs_dir)
    return problems


# --------------------------------------------------------------------------
# pin regeneration (a human runs this and reviews the diff)
# --------------------------------------------------------------------------

def regen(argv):
    """Rewrite the `statements` map from the current sources.

    This is the one operation that can make a drifted statement pass, so it is
    never invoked by a bridge or by CI: run it deliberately, then read the
    diff as you would read the theorem statements themselves.
    """
    import tempfile
    lean = find_lean()
    if lean is None:
        print("regen needs a `lean` binary")
        return 2
    pins = load_pins()
    fronts = argv or list(pins["fronts"])
    for name in fronts:
        front = pins["fronts"][name]
        with tempfile.TemporaryDirectory() as td:
            for mod in front["build"]:
                err = build_olean(lean, mod, td)
                if err:
                    print("FAIL " + err)
                    return 1
            got = env_query(lean, front["modules"], front["guarded"], td)
        for t in front["guarded"]:
            old = pins["statements"].get(t)
            pins["statements"][t] = got[t]["type"]
            state = "unchanged" if old == got[t]["type"] else \
                    ("NEW" if old is None else "CHANGED")
            print(f"{state:9s} {t}  axioms={got[t]['axioms']}")
    with open(PINS_PATH, "w") as f:
        json.dump(pins, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {PINS_PATH} — review the diff")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "regen":
        sys.exit(regen(sys.argv[2:]))
    print(__doc__)
    print("usage: proof_guard.py regen [front ...]   (rewrite statement pins)")
