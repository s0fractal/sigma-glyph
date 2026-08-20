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

Round 3 (a third review; it confirmed the round-2 fixes and broke what they
left uncovered — every vector below was green end-to-end on the real files):
  * **F12 — pinning STATEMENTS does not stop DEFINITIONS being gutted.**
    Deleting `Reach`'s `| step` constructor, or emptying `Reach`, or
    `def Valid (_w : Wave) : Prop := False`, leaves every pinned dump
    byte-identical and every theorem vacuous. The claimed compensating control
    (the differentials) does not cover it: two of the five bridges never
    execute Lean at all beyond the guard, and no differential can exercise a
    `Prop`-valued definition. The dependency set of each guarded statement is
    now computed from the kernel environment and pinned — values for
    definitions, constructor lists for inductives — failing closed on any
    dependency without a pin.
  * **F13 — string-literal CONTENT was not pinned.** `(strLit 64)` says only
    "a 64-character string", so `genesis_I` could be made to assert K's digest
    with every pin matching. Literals now dump as hex of their UTF-8 bytes,
    and `byte_bridge_check.py` cross-checks the genesis claims against the
    oracle so the swap also fails a differential.
  * **F14 — the registry authorized itself.** `theorem_pins.json` was hashed,
    anchored and cross-checked by nothing, so demoting a theorem to
    `unguarded` and replacing it with `: True := trivial` passed everything.
    `GUARD_CLAIMS.txt` now holds the counts, the unguarded allowlist and the
    registry's content hash as a gated claim.
  * **F15 — `open X in theorem …` on one line was invisible to coverage.**
    Declaration keywords are matched as tokens wherever a command can start.

Round 4 (a fourth review; it confirmed the round-3 mechanism where it applies
— SHA-256-pinned large dumps, pinned constructor types, the literal fix, the
genesis differential — and then went after the guard's SCOPE, which was
self-authorized. Every vector below was green end-to-end on the real files):
  * **F16 — the coverage fix was still LINE-based.** Lean separates commands
    by whitespace, not newlines, and the walk `continue`d on any line matching
    `namespace …`/`section`/`end`. `namespace Zzz theorem hidden : True :=
    trivial end Zzz` appended to a real proof file left the bridge green;
    `namespace Book1.C1 theorem sneaky : … := by native_decide end Book1.C1`
    did so while the C1 bridge printed "axiom cones are exactly within
    [propext]". The walk is now over COMMANDS across the whole file.
  * **F17 — the pin scope came from `front["build"]`, which nothing compiled
    from.** `isAudited` silently dropped every constant owned by a module
    outside that editable list — no pin required, no message — while every
    bridge hardcoded its own module tuple. Deleting one name restored already-
    closed P1s: `wave build → ["LutData"]` re-passed `Valid := False`, `size
    build → ["LutData"]` re-passed a gutted `Reach`, `bytes build →
    ["MachineBytes"]` unpinned all 12 `Sha256.*` dependencies. Now: the scope
    is the COMPLEMENT of an explicit, claimed core-Lean allowance, derived
    from the kernel environment; `build` is the one place a front's compiled
    set is spelled (bridges call `build_front`, the guard queries what it
    builds); the queried environment's module list must equal `build`; and
    `registry_guard` checks the missing direction (every strict source is a
    built module, every queried module is a built module).
  * **F18 — the claims file constrained counts, not identities.** A demotion
    masked by a fresh trivial theorem kept every count equal, so the whole
    `GUARD_CLAIMS.txt` diff was the one `pins-sha256` line `regen` rewrites
    anyway. Claims are identities now, over `build`, `modules`,
    `strict_sources`, `runner_sources`, `allowed_axioms`, `guarded`,
    `native_decide_ok`, `native_decide_sources` and `core_modules`.
  * **F19 — binder annotations and universe parameters were not pinned.**
    `(a b : Nat) (h : a ≤ b)` and `{a b : Nat} ⦃h : a ≤ b⦄` dumped
    byte-identically. Both are in the dump.
  * **F20 — a `native_decide` trust axiom was accepted on its SHAPE.** Any
    declaration could generate one for a theorem on `native_decide_ok`. The
    generating declarations are a claimed per-front list and each is queried
    and statement-pinned.

Round 5 (a cross-family review by z-ai/glm-4.7, reproduced locally before any
fix — the finding is theirs, the reproduction and this fix are ours):
  * **F21 — the file walk was not recursive, so the coverage claim was false
    for every subdirectory.** `guard_sources`, `coverage_guard` and
    `registry_guard` all enumerated `os.listdir(proofs_dir)` and dropped
    anything that was not a `.lean` file in that ONE directory, while
    README/this file claim "every `theorem`/`lemma` in proofs/*.lean is either
    guarded or explicitly registered as intentionally-unguarded" and "every
    .lean under proofs/ must be audited by some front". `proofs/Sub/Evil.lean`
    holding `axiom backdoor : False` produced ZERO problems from
    `guard_sources` and `BRIDGE: PREMISE HOLDS`, rc 0, from
    `bridge_check.py` — an unsound axiom sitting in the tree that no textual
    layer ever opened. Two consequences beyond the missed scan: the import
    allowlist was derived from the AUDITED FILE'S OWN DIRECTORY, so a
    `proofs/Sub/Lean.lean` decoy made `import Lean` legal inside
    `proofs/Sub/` (F2c, reopened by path); and `_shadows_core` was applied
    only to module names a front already registers, never to the module name a
    file's PATH implies. Enumeration is now recursive and in ONE place
    (`lean_sources`), a source's module name is derived from its path
    (`Sub/Evil.lean` → `Sub.Evil`), the import allowlist is the whole tree
    minus core-shadowing names, and an unregistered `.lean` ANYWHERE under
    proofs/ is a hard failure — auditable-but-unbuilt is not a state this
    guard has: a scan that finds nothing is indistinguishable from a scan that
    never ran.

Layers, strongest first:

* `guard_semantics()` — environment query: for every guarded theorem, the
  transitive axiom cone must sit inside that front's allowed set, the
  canonical dump of its elaborated type must equal the pinned dump, and every
  in-scope definition its meaning depends on must equal its own pin. Anything
  unobtainable (missing theorem, driver failure) is an error, never a skip.
* `guard_sources()` — the cheap layer over the source text: literal-aware
  comment stripping, then sorry/admit/axiom, the import allowlist, the
  metaprogramming denylist, the coverage registry over EVERY proofs/*.lean,
  and the registry-shape guard.

What this does NOT claim: the runner files (`*Run.lean`) are I/O plumbing that
*calls* the proven model; nothing here proves a runner reports what the model
computed (it could simply print the expected answers). That faithfulness is a
review matter, and the denylist only removes the mechanical ways to decouple
compiled code from the kernel definitions.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PINS_PATH = os.path.join(HERE, "theorem_pins.json")
CLAIMS_PATH = os.path.join(HERE, "GUARD_CLAIMS.txt")

#: Module names that would shadow a core module. `regen` builds a front's
#: modules into the directory it then hands the driver as LEAN_PATH, so a pins
#: file naming a module `Lean`/`Init` would poison the guard driver's OWN
#: environment on the one path a human runs.
_CORE_MODULES = ("Lean", "Init", "Std", "Main", "Plausible")


def _shadows_core(mod):
    """True if `mod` is (or is under) a core module name."""
    return any(mod == c or mod.startswith(c + ".") for c in _CORE_MODULES)


def module_of(rel):
    """Lean module name of a proofs-relative source path: `Sub/Evil.lean` →
    `Sub.Evil`. Lean derives a module name from the path under its root, so the
    file's LOCATION is part of its identity — which is exactly what the
    directory-only walk threw away (F21)."""
    return os.path.splitext(rel)[0].replace(os.sep, "/").replace("/", ".")


def rel_of_module(mod):
    """Inverse of `module_of`: `Sub.Evil` → `Sub/Evil.lean`.

    `/` is the canonical separator for a registry entry (and is accepted by the
    filesystem APIs on every platform), so a registered source path compares
    equal to the walk's output regardless of `os.sep`.
    """
    return "/".join(mod.split(".")) + ".lean"


def lean_sources(proofs_dir=HERE):
    """`[(relative path, module name)]` for EVERY `.lean` under `proofs_dir`,
    recursively, sorted — the one enumeration every source-layer check uses.

    It was `os.listdir(proofs_dir)`, three times over, and a `.lean` in a
    subdirectory was silently skipped by all of them: the guard's stated
    coverage ("every theorem in proofs/*.lean", "every .lean under proofs/ is
    audited by some front") was false for any path with a `/` in it, so
    `proofs/Sub/Evil.lean` could carry `axiom backdoor : False` with every
    bridge green (2026-07 cross-family review by z-ai/glm-4.7, F21). This is
    the fourth instance in this stack of a *claimed coverage that does not
    cover*, so the enumeration is centralised here rather than repeated: a
    future check gets the recursive walk by construction, and a future refactor
    that moves a proof into a subdirectory keeps every textual layer.

    Nothing is filtered out — not dotfiles, not build directories. A `.lean`
    the walk cannot account for must be REFUSED loudly (registry_guard) and
    excluded, if ever, in a diff a human reads; a silent exclusion here is the
    defect this function exists to remove.
    """
    out = []
    for root, dirs, files in os.walk(proofs_dir):
        dirs.sort()
        for f in sorted(files):
            if f.endswith(".lean"):
                rel = os.path.relpath(os.path.join(root, f),
                                      proofs_dir).replace(os.sep, "/")
                out.append((rel, module_of(rel)))
    return sorted(out)

#: Axioms of the Lean 4 standard library that a clean classical proof may use.
#: Per-front allowances live in the pin registry (C1 is tightened to `propext`
#: alone, which is what proofs/README.md claims for that front).
STD_AXIOMS = ("propext", "Classical.choice", "Quot.sound")

#: Shape of the per-declaration trust axioms `native_decide` introduces
#: (Lean >= 4.x names them `<decl>._native.native_decide.ax_*`). Allowed only
#: for the theorems whose documented TCB already includes the compiler.
_NATIVE_DECIDE = re.compile(r"^([^\s]+)\._native\.native_decide\.ax[_0-9]+$")


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


def _advance_block_comment(src, index, depth):
    if src.startswith("/-", index):
        return index + 2, depth + 1
    if src.startswith("-/", index):
        return index + 2, depth - 1
    return index + 1, depth


def _string_end(src, index):
    index += 1
    while index < len(src):
        if src[index] == "\\":
            index += 2
        elif src[index] == '"':
            return index + 1
        else:
            index += 1
    return None


def _next_lean_token(src, index, depth, previous):
    if depth:
        index, depth = _advance_block_comment(src, index, depth)
        return "", index, depth, previous, None
    if src.startswith("/-", index):
        return "", index + 2, 1, previous, None
    if src.startswith("--", index):
        newline = src.find("\n", index)
        return "", len(src) if newline < 0 else newline, 0, previous, None
    raw = _RAW_OPEN.match(src, index)
    if raw:
        close = '"' + raw.group(1)
        end = src.find(close, raw.end())
        if end < 0:
            return "", index, 0, previous, "unterminated raw string literal"
        return 'r""', end + len(close), 0, '"', None
    if src[index] == '"':
        end = _string_end(src, index)
        if end is None:
            return "", index, 0, previous, "unterminated string literal"
        return '""', end, 0, '"', None
    if src[index] == "'" and not _IDENT_CH.match(previous or " "):
        char = _CHAR_LIT.match(src, index)
        if char:
            return "''", char.end(), 0, "'", None
    return src[index], index + 1, 0, src[index], None


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
        fragment, i, depth, prev, problem = _next_lean_token(
            src, i, depth, prev)
        if problem:
            return "".join(out), [problem]
        out.append(fragment)
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


#: The command keywords the coverage walk cares about, matched as TOKENS
#: wherever a command may begin — never anchored to a line. Lean separates
#: commands by whitespace, not by newlines, so `namespace X … end X` and
#: `end X theorem …` are legal on ONE line; the previous line-based walk
#: `continue`d on any line that *started* with `namespace`/`section`/`end` and
#: therefore saw nothing at all on such a line (2026-07 round-4 review, F16 —
#: `namespace Zzz theorem hidden : True := trivial end Zzz` appended to a real
#: proof file left the bridge printing ALL AGREE). Lean identifier characters
#: (including `.`, `'`, `!`, `?`) are excluded on both sides, so
#: `false_is_a_theorem` and `Foo.example` do not match.
_CMD_KW = re.compile(r"(?<![A-Za-z0-9_'!?.])"
                     r"(namespace|section|end|theorem|lemma|example)"
                     r"(?![A-Za-z0-9_'!?])")

#: The identifier following a declaration keyword (`\s*`, because a
#: declaration's name may sit on the next line) and the one following a
#: scope keyword (same line only: a bare `end` closes an anonymous section,
#: and swallowing the next line's `theorem` as its argument would be wrong).
_AFTER_DECL_KW = re.compile(r"\s*([^\s:({\[⦃⟨]*)")
_AFTER_SCOPE_KW = re.compile(r"[^\S\n]*([^\s:({\[⦃⟨]*)")

#: A command keyword can never be the *name* of the command before it.
_KEYWORDS = frozenset({"namespace", "section", "end",
                       "theorem", "lemma", "example"})


def _command_arg(body, match, keyword):
    pattern = (_AFTER_DECL_KW if keyword in ("theorem", "lemma", "example")
               else _AFTER_SCOPE_KW)
    arg = pattern.match(body, match.end()).group(1) or None
    return None if arg in _KEYWORDS else arg


def _update_scope(stack, keyword, arg):
    if keyword == "namespace":
        stack.append(("ns", arg))
        return True
    if keyword == "section":
        stack.append(("sec", arg))
        return True
    if keyword != "end":
        return False
    if stack and (arg is None or stack[-1][1] == arg):
        stack.pop()
    return True


def _qualified_decl_name(stack, name):
    if not name:
        return None
    prefix = ".".join(value for kind, value in stack
                      if kind == "ns" and value)
    return f"{prefix}.{name}" if prefix else name


def _decl_names(body):
    """[(kind, fully-qualified name or None, line)] for the declarations that
    the guard has to account for (theorem/lemma/example).

    The walk is over COMMANDS, not lines: `body` (already comment-stripped and
    literal-blanked) is scanned once for command keywords as tokens, and the
    namespace/section stack is maintained across the whole file. So a
    declaration is found wherever a command can begin, and its namespace
    prefix is correct regardless of how the file is broken into lines.
    """
    stack, out = [], []
    for m in _CMD_KW.finditer(body):
        kw = m.group(1)
        lineno = body.count("\n", 0, m.start()) + 1
        arg = _command_arg(body, m, kw)
        if not _update_scope(stack, kw, arg):
            out.append((kw, _qualified_decl_name(stack, arg), lineno))
    return out


def _denylist_problems(body, profile):
    problems = []
    rules = list(_DENY) + ([] if profile == "runner" else _RUNNER_ONLY)
    for pattern, why in rules:
        match = re.search(pattern, body)
        if match:
            problems.append(f"`{match.group(0)}` — {why}")
    return problems


def _attribute_problems(body):
    problems = []
    for match in re.finditer(r"@\[([^\]]*)\]", body):
        for entry in match.group(1).split(","):
            head = entry.strip().split(" ")[0].lstrip("-!")
            if head and head not in ALLOWED_ATTRS:
                problems.append(
                    f"attribute `@[{entry.strip()}]` is not in the allowlist "
                    f"{sorted(ALLOWED_ATTRS)} (F3: attributes are how compiled "
                    "code is decoupled from kernel definitions)")
    return problems


def _option_problems(body):
    problems = []
    for match in re.finditer(r"\bset_option\s+([^\s]+)", body):
        option = match.group(1)
        if not option.startswith("linter."):
            problems.append(f"`set_option {option}` — only `linter.*` "
                            "options are allowed (soundness flags such as "
                            "`debug.skipKernelTC` live in this namespace)")
    return problems


def _import_problems(body, root):
    problems = []
    allowed = {module for _rel, module in lean_sources(root)
               if not _shadows_core(module)}
    for line in body.splitlines():
        stripped = line.lstrip(" \t")
        if not stripped.startswith("import "):
            continue
        for module in stripped.removeprefix("import ").split():
            if module not in allowed:
                problems.append(
                    f"`import {module}` is outside the proofs/ module set "
                    f"{sorted(allowed)} — these are core-Lean-only proofs, "
                    "and `import Lean` is what makes the guard's own query "
                    "spoofable (F2b)")
    return problems


def source_guard(path, profile="strict", proofs_dir=None):
    """Problems found in one audited Lean source file (empty list = clean).

    `profile="runner"` relaxes only `partial` (the `*Run.lean` I/O loops).
    `proofs_dir` is the module ROOT the import allowlist is computed from; it
    defaults to the file's own directory, which is right for a standalone
    fixture and wrong for a file in a subdirectory — callers that scan the tree
    pass the root (F21).
    Substring/allowlist matching on purpose: a false positive on an
    exotic-but-legit spelling is the safe direction (fail closed) — the fix is
    to widen an allowlist deliberately, in a reviewed diff.
    """
    with open(path, encoding="utf-8") as source:
        src = source.read()
    body, problems = strip_lean_source(src)
    if problems:                                  # lexer disagreement: stop here
        return [f"{p} (our lexer and Lean's disagree about this file)"
                for p in problems]

    problems += _denylist_problems(body, profile)
    problems += _attribute_problems(body)
    problems += _option_problems(body)

    # The allowlist is the WHOLE proofs tree, by module name, minus anything
    # whose name shadows core Lean. It used to be the audited file's own
    # directory listing, which handed a subdirectory its own allowlist: drop a
    # decoy `proofs/Sub/Lean.lean` in beside the file and `import Lean` — the
    # import that makes the guard's query spoofable — became legal inside
    # `proofs/Sub/` (F21, reopening F2c by path). A source named after a core
    # module is refused outright by registry_guard, so it can never authorise
    # an import here either.
    root = proofs_dir or os.path.dirname(os.path.abspath(path))
    problems += _import_problems(body, root)
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

    "Every theorem in proofs/*.lean" means every `.lean` at ANY depth: the walk
    was `os.listdir`, so a subdirectory's declarations were outside a claim
    that said it covered them (F21).
    """
    pins = load_pins() if pins is None else pins
    known = set(pins.get("unguarded", {}))
    for front in pins.get("fronts", {}).values():
        known.update(front.get("guarded", []))
    problems = []
    for f, _mod in lean_sources(proofs_dir):
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


#: The per-front claim keys of GUARD_CLAIMS.txt, and the registry field each
#: one asserts. Counts used to be the whole claim, so a demotion (hide a
#: theorem, register a fresh trivial one in its place) kept every number equal
#: and showed up as a one-line `pins-sha256` diff — the single line `regen`
#: rewrites on every run, i.e. no review signal at all (2026-07 round-4
#: review, F18). Every field the guard's behaviour depends on is now claimed by
#: IDENTITY, so any change to what is guarded names the theorem in the diff.
CLAIM_FIELDS = {
    "build": "build",
    "modules": "modules",
    "strict-sources": "strict_sources",
    "runner-sources": "runner_sources",
    "axioms": "allowed_axioms",
    "guarded": "guarded",
    "native-decide-ok": "native_decide_ok",
    "native-decide-sources": "native_decide_sources",
}


def load_claims(path=CLAIMS_PATH):
    """Parse `GUARD_CLAIMS.txt` → a claims dict.

    `{"pins-sha256": hex|None, "core-modules": set|None,
      "unguarded": set, "fronts": {name: {key: set}}}`; a key absent from a
    front's dict means the claim was not made at all (which is a failure —
    an unclaimed field is an unreviewed one). A line may carry several values;
    repeated lines accumulate, so the one-name-per-line style below gives a
    diff that names the theorem.

    Raises OSError if the file is missing — an absent claims file is a
    failure, not a reason to trust the registry.
    """
    claims = {"pins-sha256": None, "core-modules": None,
              "unguarded": set(), "fronts": {}}
    with open(path) as f:
        for raw in f:
            s = raw.split("#", 1)[0].split()
            if not s:
                continue
            if s[0] == "pins-sha256" and len(s) == 2:
                claims["pins-sha256"] = s[1]
            elif s[0] == "core-modules":
                claims["core-modules"] = (claims["core-modules"] or set()) \
                    | set(s[1:])
            elif s[0] == "unguarded":
                claims["unguarded"] |= set(s[1:])
            elif s[0] == "front" and len(s) >= 3 and s[2] in CLAIM_FIELDS:
                claims["fronts"].setdefault(s[1], {}).setdefault(
                    s[2], set()).update(s[3:])
    return claims


def _claim_set_errors(cf, what, claimed, actual):
    problems = [
        f"{what}: the registry has {item!r}, which {cf} does not claim"
        for item in sorted(set(actual) - set(claimed))]
    problems += [
        f"{what}: {cf} claims {item!r}, which the registry does not have"
        for item in sorted(set(claimed) - set(actual))]
    return problems


def _core_claim_errors(pins, claims, cf):
    core = pins.get("core_modules")
    problems = []
    if not core:
        problems.append("the registry names no `core_modules` — the guard's "
                        "audit scope is the complement of that allowance, so "
                        "an empty one would put nothing in scope")
    if claims["core-modules"] is None:
        problems.append(f"{cf} makes no `core-modules` claim — the set of "
                        "modules allowed to go unpinned must be reviewed")
    else:
        problems += _claim_set_errors(
            cf, "core-modules", claims["core-modules"], core or [])
    return problems


def _one_front_claim_errors(name, front, claimed, cf):
    problems = []
    for key, field in sorted(CLAIM_FIELDS.items()):
        actual = front.get(field, [])
        if len(set(actual)) != len(actual):
            problems.append(f"front {name!r} lists a duplicate in {field}")
        if key not in claimed:
            problems.append(
                f"front {name!r} has no `{key}` claim in {cf} — every field "
                "the guard's behaviour depends on must be claimed by identity "
                "(write the bare key for an empty set)")
        else:
            problems += _claim_set_errors(
                cf, f"front {name!r} {key}", claimed[key], actual)
    return problems


def _front_claim_errors(fronts, claimed_fronts, cf):
    problems = []
    for name in sorted(set(fronts) | set(claimed_fronts)):
        if name not in fronts:
            problems.append(f"front {name!r} is claimed in {cf} but is gone "
                            "from the registry")
        elif name not in claimed_fronts:
            problems.append(f"front {name!r} has no claims at all in {cf}")
        else:
            problems += _one_front_claim_errors(
                name, fronts[name], claimed_fronts[name], cf)
    return problems


def _unguarded_claim_errors(pins, claims, cf):
    unguarded = pins.get("unguarded", {})
    problems = []
    for theorem in sorted(set(unguarded) | claims["unguarded"]):
        if theorem not in unguarded:
            problems.append(
                f"{theorem} is on the reviewed unguarded allowlist but is no "
                "longer registered as unguarded")
        elif theorem not in claims["unguarded"]:
            problems.append(
                f"{theorem} was moved to `unguarded` without being added to "
                f"the reviewed allowlist in {cf} — a theorem cannot leave the "
                "guard's reach silently")
        elif len((unguarded[theorem] or "").strip()) < 12:
            problems.append(
                f"{theorem} is unguarded with no real reason recorded")
    return problems


def _registered_module_errors(name, modules, audited, proofs_dir):
    problems = []
    for module in modules:
        if _shadows_core(module):
            problems.append(f"front {name!r} names module {module!r}, which "
                            "shadows a core Lean module")
        source = rel_of_module(module)
        if not os.path.exists(os.path.join(proofs_dir, source)):
            problems.append(f"front {name!r} builds module {module!r} with no "
                            f"{source} in proofs/")
        elif source not in audited:
            problems.append(f"front {name!r} compiles {source} but does not "
                            "audit it (strict_sources/runner_sources)")
    return problems


def _front_topology_errors(name, front, pins, proofs_dir):
    strict = set(front.get("strict_sources", []))
    runner = set(front.get("runner_sources", []))
    build = list(front.get("build", []))
    problems = _registered_module_errors(
        name, build + list(front.get("modules", [])), strict | runner,
        proofs_dir)
    for source in sorted(strict):
        if module_of(source) not in build:
            problems.append(
                f"front {name!r} audits {source} as a strict source but does "
                "not compile it (`build`) — the guard queries the environment "
                "built from `build`, so an uncompiled source is unchecked")
    for module in build:
        if rel_of_module(module) in runner:
            problems.append(f"front {name!r} builds {module}.lean and also "
                            "registers it as a runner (which relaxes the "
                            "`partial` rule) — pick one")
    for module in front.get("modules", []):
        if module not in build:
            problems.append(f"front {name!r} imports module {module!r} in the "
                            "environment query but does not build it")
    for theorem in front.get("native_decide_sources", []):
        if (theorem not in front.get("guarded", [])
                and theorem not in pins.get("unguarded", {})):
            problems.append(
                f"front {name!r} trusts native_decide axioms from {theorem}, "
                "which is neither guarded nor registered as unguarded")
    return strict | runner, problems


def _source_inventory_errors(proofs_dir, listed):
    problems = []
    for relative, module in lean_sources(proofs_dir):
        if _shadows_core(module):
            problems.append(
                f"proofs/{relative} is Lean module {module!r}, which shadows "
                "a core Lean module — building it would poison the guard "
                "driver's LEAN_PATH and its presence widens the import list")
        if relative not in listed:
            problems.append(
                f"proofs/{relative} is not audited by any front — add it to a "
                "front's strict_sources/runner_sources")
    return problems


def registry_guard(pins=None, proofs_dir=HERE, pins_path=PINS_PATH,
                   claims_path=CLAIMS_PATH):
    """`theorem_pins.json` is a claim; this is what makes it a GATED claim.

    Nothing used to hash, anchor or cross-check the registry, so moving a
    theorem from `guarded` to `unguarded` (with a plausible reason) and
    replacing it with `: True := trivial` passed every bridge — the pin and the
    axiom cone were simply never consulted for it, and the only tell was a
    count in an ungated log line (2026-07 round-3 review, F14). The registry is
    now asserted against a hand-maintained `GUARD_CLAIMS.txt` — by IDENTITY,
    not by count: every guarded theorem, every native_decide source, each
    front's build/modules/sources/axioms, the core-module allowance, the exact
    unguarded allowlist, and the pins file's content hash. Counts were not
    enough: a demotion masked by a fresh trivial theorem kept every number
    equal and left a one-line hash diff (round-4, F18).
    """
    pins = load_pins(pins_path) if pins is None else pins
    problems = []
    cf = os.path.basename(claims_path)
    try:
        claims = load_claims(claims_path)
    except OSError as e:
        return [f"the guard claims file is unreadable ({e}) — the pin registry "
                "would be self-authorizing without it"]

    with open(pins_path, "rb") as source:
        have = hashlib.sha256(source.read()).hexdigest()
    if claims["pins-sha256"] != have:
        problems.append(
            f"{os.path.basename(pins_path)} content hash {have} does not match "
            f"the {cf} claim {claims['pins-sha256']} — the registry changed "
            "without the reviewed claims file changing with it")

    fronts = pins.get("fronts", {})
    problems += _core_claim_errors(pins, claims, cf)
    problems += _front_claim_errors(fronts, claims["fronts"], cf)
    problems += _unguarded_claim_errors(pins, claims, cf)
    listed = set()
    for name, front in fronts.items():
        front_listed, front_problems = _front_topology_errors(
            name, front, pins, proofs_dir)
        listed |= front_listed
        problems += front_problems
    problems += _source_inventory_errors(proofs_dir, listed)
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

/-- String literals are dumped by CONTENT, as the hex of their UTF-8 bytes.
    They used to be dumped as `(strLit <length>)`, i.e. "some 64-character
    string" — with which `MachineBytes.genesis_I` could be made to pin K's
    digest and every pin still matched (2026-07 round-3 review, F13). Hex
    keeps the dump one whitespace-free token, so no content can collide with
    the dump's own syntax. -/
def hexDigit (k : Nat) : Char :=
  if k < 10 then Char.ofNat (48 + k) else Char.ofNat (87 + k)

def hexOfString (s : String) : String :=
  s.toUTF8.foldl (fun acc b =>
    (acc.push (hexDigit (b.toNat / 16))).push (hexDigit (b.toNat % 16))) ""

/-- Binder annotations are part of a declaration's dump. They do not change
    what a proposition MEANS, but README §2 claims the canonical dump of the
    elaborated type equals its pin, and `(w1 w2 : Wave) (h : Valid w1)` used to
    dump byte-identically to `{w1 w2 : Wave} ⦃h : Valid w1⦄` (2026-07 round-4
    review, F19). -/
def dumpBI : BinderInfo → String
  | .default => "e"
  | .implicit => "i"
  | .strictImplicit => "s"
  | .instImplicit => "c"

partial def dumpExpr : Expr → String
  | .bvar i => "#" ++ toString i
  | .fvar id => "(fvar " ++ toString id.name ++ ")"
  | .mvar _ => "(mvar)"
  | .sort u => "(sort " ++ dumpLevel u ++ ")"
  | .const n us =>
      "(const " ++ toString n ++ " [" ++ String.intercalate " " (us.map dumpLevel) ++ "])"
  | .app f a => "(app " ++ dumpExpr f ++ " " ++ dumpExpr a ++ ")"
  | .lam _ t b bi => "(lam " ++ dumpBI bi ++ " " ++ dumpExpr t ++ " " ++ dumpExpr b ++ ")"
  | .forallE _ t b bi => "(all " ++ dumpBI bi ++ " " ++ dumpExpr t ++ " " ++ dumpExpr b ++ ")"
  | .letE _ t v b _ => "(let " ++ dumpExpr t ++ " " ++ dumpExpr v ++ " " ++ dumpExpr b ++ ")"
  | .lit (.natVal n) => "(natLit " ++ toString n ++ ")"
  | .lit (.strVal s) => "(strLit " ++ toString s.length ++ " " ++ hexOfString s ++ ")"
  | .mdata _ b => dumpExpr b
  | .proj s i b => "(proj " ++ toString s ++ " " ++ toString i ++ " " ++ dumpExpr b ++ ")"

/-- The universe parameters a declaration is polymorphic in. `dumpConst` never
    emitted them, so a declaration could change its level binders with every
    pin matching (F19). -/
def dumpLevelParams (ns : List Name) : String :=
  "(lvls [" ++ String.intercalate " " (ns.map toString) ++ "])"

/-- The full structural content of one constant: its universe parameters, and
    for a definition its type AND its VALUE, for an inductive its type AND its
    constructor list. Pinning statements alone left every definition a
    theorem's meaning rests on free to be gutted (F12). -/
def dumpConst (env : Environment) (n : Name) : String :=
  match env.find? n with
  | none => "MISSING"
  | some info =>
    let lp := dumpLevelParams info.levelParams ++ " "
    match info with
    | .axiomInfo v => "axiom " ++ lp ++ dumpExpr v.type
    | .thmInfo v => "thm " ++ lp ++ dumpExpr v.type
    | .defnInfo v => "def " ++ lp ++ dumpExpr v.type ++ " := " ++ dumpExpr v.value
    | .opaqueInfo v => "opaque " ++ lp ++ dumpExpr v.type ++ " := " ++ dumpExpr v.value
    | .quotInfo _ => "quot " ++ lp
    | .ctorInfo v => "ctor " ++ lp ++ dumpExpr v.type
    | .recInfo v => "rec " ++ lp ++ dumpExpr v.type
    | .inductInfo v =>
        "ind " ++ lp ++ dumpExpr v.type ++ " ctors ["
          ++ String.intercalate " " (v.ctors.map toString) ++ "]"

/-- Is `c` inside the scope the guard must pin?

    The scope is DERIVED, not configured: everything is in scope EXCEPT the
    constants whose owning module's root is on the explicit core-Lean
    allowance (`core_modules` in the pin registry, claimed in
    GUARD_CLAIMS.txt), which the toolchain pin fixes. It used to be the
    complement — a constant counted only if its owning module was listed in
    `front["build"]`, an editable field nothing compiled from — so deleting one
    module name silently dropped every pin it owned and no message was printed
    (2026-07 round-4 review, F17: `wave build → ["LutData"]` restored the
    `Valid := False` vector, `bytes build → ["MachineBytes"]` unpinned all 12
    `Sha256.*` dependencies). A constant with no owning module is in scope —
    fail closed. -/
def inScope (env : Environment) (core : NameSet) (c : Name) : Bool :=
  match env.getModuleIdxFor? c with
  | none => true
  | some idx =>
      match env.header.moduleNames[idx.toNat]? with
      | none => true
      | some m => !core.contains m.getRoot

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

/-- The audited constants a statement's MEANING depends on: everything reachable
    from the theorem's type, then transitively through the types and VALUES of
    the definitions it mentions (a theorem reached this way contributes its type
    only — its proof is irrelevant to what anything means). Computed from the
    kernel environment, never hand-listed, so a new dependency cannot appear
    unpinned. -/
partial def collectDeps (env : Environment) (core : NameSet) (c : Name)
    : StateM NameSet Unit := do
  if (← get).contains c then return
  if !inScope env core c then return
  modify (·.insert c)
  let visit (e : Expr) : StateM NameSet Unit :=
    e.getUsedConstants.forM (collectDeps env core)
  match env.find? c with
  | none => return
  | some (.axiomInfo v) => visit v.type
  | some (.thmInfo v) => visit v.type
  | some (.defnInfo v) => visit v.type; visit v.value
  | some (.opaqueInfo v) => visit v.type; visit v.value
  | some (.quotInfo _) => return
  | some (.ctorInfo v) => visit v.type
  | some (.recInfo v) => visit v.type
  | some (.inductInfo v) => visit v.type; v.ctors.forM (collectDeps env core)

/-- `<import module>… -- <core-module root>… -- <declaration>…` -/
def splitArgs (args : List String) : List (List String) :=
  args.foldr (fun a acc =>
    if a == "--" then [] :: acc
    else match acc with
         | h :: t => (a :: h) :: t
         | [] => [[a]]) [[]]

def main (args : List String) : IO UInt32 := do
  let secs := splitArgs args
  let mods := (secs[0]?.getD []).map String.toName
  let core : NameSet := ((secs[1]?.getD []).map String.toName).foldl (·.insert ·) {}
  let decls := secs[2]?.getD []
  if core.isEmpty then
    IO.eprintln "no core-module allowance given — refusing to run"
    return 1
  initSearchPath (← findSysroot)
  let imps : Array Import := (mods.map fun m => ({ module := m } : Import)).toArray
  let env ← importModules imps {} 0
  -- Every module actually in the loaded environment, so the caller can assert
  -- that what was compiled is what it claims to compile (F17): a non-core
  -- module in here that the front does not build is a module nothing audits.
  IO.println ("MODULES " ++ String.intercalate " "
    (env.header.moduleNames.filter (fun m => !core.contains m.getRoot)
      |>.map toString |>.toList))
  let mut deps : NameSet := {}
  for d in decls do
    let n := d.toName
    match env.find? n with
    | none => IO.println ("MISSING " ++ d)
    | some info =>
      let (_, axs) := (collectName env n).run ({}, {}) |>.2
      let names := (axs.toArray.qsort Name.lt).map toString
      IO.println ("DECL " ++ d)
      IO.println ("AXIOMS " ++ String.intercalate " " names.toList)
      IO.println ("TYPE " ++ dumpLevelParams info.levelParams ++ " " ++ dumpExpr info.type)
      deps := (info.type.getUsedConstants.forM (collectDeps env core)).run deps |>.2
  for x in deps.toArray.qsort Name.lt do
    IO.println ("DEP " ++ toString x ++ " " ++ dumpConst env x)
  IO.println "DRIVER-COMPLETE"
  return 0
'''


def build_olean(lean, module, olean_dir, src_dir=HERE):
    """Compile <src_dir>/<module>.lean to <olean_dir>/<module>.olean.

    Returns an error string, or None on success. `lean` requires the input
    file under its root dir, so we run with cwd=src_dir and a relative path;
    LEAN_PATH points at olean_dir so already-built modules resolve.

    A dotted module name is a PATH (`Sub.Evil` → `Sub/Evil.lean`,
    `Sub/Evil.olean`), which is how Lean itself resolves it — so registering a
    subdirectory source is something a front can actually do, rather than a
    rule with no implementation behind it (F21).
    """
    src = rel_of_module(module)
    out = os.path.join(olean_dir, os.path.splitext(src)[0] + ".olean")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    r = subprocess.run(
        [lean, src, "-o", out],
        capture_output=True, text=True, cwd=src_dir,
        env=dict(os.environ, LEAN_PATH=olean_dir))
    if r.returncode != 0:
        return (f"{module}.lean does not compile: "
                + (r.stderr or r.stdout).strip()[:500])
    return None


#: The ONLY modules whose constants may go unpinned: core Lean, fixed by
#: `proofs/lean-toolchain`. It is a fallback — the registry's `core_modules`
#: (a claimed field of GUARD_CLAIMS.txt) is what the bridges actually use.
CORE_ALLOWANCE = ("Init", "Std", "Lean")


def build_front(lean, front, olean_dir, src_dir=HERE, runners=False):
    """Compile a front's modules, in order, into `olean_dir`.

    The ONE place a front's compiled module set is spelled. Each bridge used to
    hardcode its own tuple (`"SizeBound"`, `("Sha256", "MachineBytes",
    "BytesRun")`, …) while the guard derived its audit scope from
    `front["build"]` — two lists that nothing forced to agree, so editing
    `build` changed what was pinned without changing what was compiled
    (2026-07 round-4 review, F17). `runners=True` additionally compiles the
    front's `runner_sources` (the `*Run.lean` I/O plumbing a differential
    executes). Returns an error string or None.
    """
    mods = list(front["build"])
    if runners:
        mods += [module_of(s) for s in front.get("runner_sources", [])]
    for mod in mods:
        err = build_olean(lean, mod, olean_dir, src_dir)
        if err:
            return err
    return None


def _run_env_driver(lean, modules, decls, olean_dir, core):
    qpath = os.path.join(olean_dir, "SigmaGuardDriver.lean")
    with open(qpath, "w", encoding="utf-8") as driver:
        driver.write(GUARD_DRIVER)
    result = subprocess.run(
        [lean, "--run", qpath] + list(modules) + ["--"] + list(core)
        + ["--"] + list(decls), capture_output=True, text=True,
        cwd=olean_dir, env=dict(os.environ, LEAN_PATH=olean_dir))
    if result.returncode != 0:
        raise RuntimeError("environment query failed: "
                           + (result.stderr or result.stdout).strip()[:500])
    lines = result.stdout.splitlines()
    if "DRIVER-COMPLETE" not in lines:
        raise RuntimeError("environment query produced no completion marker: "
                           + (result.stdout + result.stderr).strip()[:500])
    return lines


def _parse_env_output(lines):
    got, deps, current, loaded = {}, {}, None, None
    for line in lines:
        kind, _, value = line.partition(" ")
        if kind == "MODULES":
            loaded = value.split()
        elif kind == "MISSING":
            raise RuntimeError(f"declaration not in the environment: {value} "
                               "(renamed or deleted?)")
        elif kind == "DECL":
            current = value
            got[current] = {"axioms": [], "type": None}
        elif kind == "AXIOMS" and current:
            got[current]["axioms"] = value.split()
        elif kind == "TYPE" and current:
            got[current]["type"] = " ".join(value.split())
        elif kind == "DEP":
            name, _, dump = value.partition(" ")
            if dump == "MISSING":
                raise RuntimeError(
                    f"dependency vanished from the environment: {name}")
            deps[name] = " ".join(dump.split())
    return got, deps, loaded


def env_query(lean, modules, decls, olean_dir, core=CORE_ALLOWANCE):
    """`({decl: {"axioms": [...], "type": dump}}, {const: dump})`.

    The second map is the DEFINITION dependency set: every constant the
    queried statements' meaning rests on that is NOT owned by a core-Lean
    module, with its full structural content (value for definitions,
    constructor list for inductives).

    `core` is the explicit, claimed allowance of module roots whose constants
    the toolchain pin fixes — the scope is the complement of that, so it cannot
    shrink by editing a per-front list. An empty allowance is refused by the
    driver.

    Raises RuntimeError on anything short of a complete answer — a missing
    (renamed/deleted) theorem, a driver crash, truncated output. The bridges
    turn that into a failure, never a skip.
    """
    if not decls:
        raise RuntimeError("no theorems to query — an empty guarded list "
                           "would pass vacuously")
    if not core:
        raise RuntimeError("no core-module allowance — refusing to query")
    got, deps, loaded = _parse_env_output(
        _run_env_driver(lean, modules, decls, olean_dir, core))
    missing = [d for d in decls if d not in got or not got[d]["type"]]
    if missing:
        raise RuntimeError("no environment answer for: " + ", ".join(missing))
    if loaded is None:
        raise RuntimeError("environment query reported no module list")
    return got, deps, loaded


#: Definition dumps longer than this are pinned by SHA-256 rather than
#: verbatim: `WaveAlgebra.lutString` is a 200 KB literal, and a pin file no one
#: can read is not a reviewable claim. The hash pins the same content — only
#: the diff's readability differs, and the definitions that carry a theorem's
#: hypotheses (`Valid`, `Wf`, `Reach`, `Step`, `Inv`) are all far below it.
PIN_INLINE_MAX = 4000


def pin_of(dump):
    """The pinned form of a structural dump (verbatim, or its SHA-256)."""
    dump = " ".join(dump.split())
    if len(dump) <= PIN_INLINE_MAX:
        return dump
    return "sha256:%s:%d" % (hashlib.sha256(dump.encode()).hexdigest(),
                             len(dump))


def strlits(dump):
    """Every string literal in a structural dump, decoded, in order.

    The dump carries literals as `(strLit <chars> <utf8-hex>)`, so a bridge can
    cross-check what a theorem's statement literally CLAIMS against the oracle
    (`byte_bridge_check.py` does this for the genesis hashes) — independently
    of whether the statement matches its pin.
    """
    out = []
    for chars, hexed in re.findall(r"\(strLit (\d+) ([0-9a-f]*)\)", dump):
        try:
            s = bytes.fromhex(hexed).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if len(s) == int(chars):
            out.append(s)
    return out


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
    front["definitions"] = pins.get("definitions", {})
    front["core_modules"] = pins.get("core_modules", list(CORE_ALLOWANCE))
    front["_pins"] = pins
    return front


def _module_scope_errors(front, loaded):
    return [
        f"the queried environment contains module {module!r}, which "
        f"front {front.get('name')!r} does not build — every non-core module "
        "in scope must be one this front compiles and audits"
        for module in sorted(set(loaded) - set(front["build"]))
    ]


def _definition_pin_errors(deps, queried, definitions):
    bad = []
    for name in sorted(set(deps) - set(queried)):
        want = definitions.get(name)
        if want is None:
            bad.append(
                f"{name} is a definition the guarded statements' meaning "
                f"depends on, but it has no pin in "
                f"{os.path.basename(PINS_PATH)} — refusing to certify a "
                "theorem whose definitions are unpinned")
            continue
        actual = pin_of(deps[name])
        if actual != " ".join(want.split()):
            bad.append(f"{name}: DEFINITION DRIFT — a definition the guarded "
                       f"theorems are stated in terms of changed.\n"
                       f"    pinned:  {want[:400]}\n"
                       f"    actual:  {actual[:400]}")
    return bad


def _theorem_axiom_errors(theorems, got, allowed, native_ok, native_sources):
    bad = []
    for theorem in theorems:
        for axiom in got[theorem]["axioms"]:
            if axiom in allowed:
                continue
            match = _NATIVE_DECIDE.match(axiom)
            if match and theorem in native_ok:
                source = match.group(1)
                if source in native_sources:
                    continue
                bad.append(
                    f"{theorem} rests on a native_decide trust axiom generated "
                    f"by {source}, which is not on this front's "
                    "`native_decide_sources` list — the compiler is trusted "
                    "only for declarations named and statement-pinned as such")
            else:
                bad.append(f"{theorem} depends on disallowed axiom: {axiom}")
    return bad


def _statement_pin_errors(queried, got, pinned):
    bad = []
    for theorem in queried:
        want = pinned.get(theorem)
        if want is None:
            bad.append(f"{theorem} has no pinned statement in "
                       f"{os.path.basename(PINS_PATH)} — refusing to certify "
                       "an unpinned theorem")
            continue
        want = " ".join(want.split())
        actual = got[theorem]["type"]
        if actual != want:
            bad.append(f"{theorem}: STATEMENT DRIFT — the theorem no longer "
                       f"says what it is pinned to say.\n    pinned:  {want}\n"
                       f"    actual:  {actual}\n"
                       f"    first difference at char {_first_diff(want, actual)}")
    return bad


def guard_semantics(lean, front, olean_dir, out=None):
    """Axiom cone, pinned statement AND pinned definitions for `front`.

    Returns an error string, or None if the front is clean. Fails closed on
    every unobtainable answer, on an empty guarded list (which would otherwise
    pass vacuously), and on any load-bearing definition without a pin.

    `out`, if given, receives the raw environment answers as
    `{"decls": …, "deps": …}` so a caller can cross-check what the statements
    and definitions literally claim (see `strlits`).
    """
    theorems = list(front.get("guarded", []))
    if not theorems:
        return (f"front {front.get('name')!r} has an empty guarded list — "
                "nothing would be checked")
    allowed = set(front.get("allowed_axioms", STD_AXIOMS))
    native_ok = set(front.get("native_decide_ok", []))
    # F20: a `native_decide` trust axiom used to be accepted on its SHAPE
    # alone, so a theorem on `native_decide_ok` could carry an axiom generated
    # by any other declaration — including an unguarded one whose statement
    # nothing pins. The generating declarations are now an explicit per-front
    # list, and each of them is queried and statement-pinned like a guarded
    # theorem (its axiom cone is not checked — it IS the compiler trust).
    native_src = list(front.get("native_decide_sources", []))
    queried = theorems + [s for s in native_src if s not in theorems]
    pinned = front["statements"]
    defs = front.get("definitions", {})
    try:
        got, deps, loaded = env_query(
            lean, front["modules"], queried, olean_dir,
            core=front.get("core_modules") or CORE_ALLOWANCE)
    except RuntimeError as e:
        return str(e)
    if out is not None:
        out["decls"], out["deps"] = got, deps
    bad = _module_scope_errors(front, loaded)
    # F17: what is COMPILED into the queried environment must be exactly what
    # the front claims to build. Anything else is a module no source-layer scan
    # and no pin covers, reached through an import chain.
    # F12: pinning statements does not stop a DEFINITION from being gutted.
    # `Reach` losing its `step` constructor, or `Valid := False`, leaves every
    # statement dump byte-identical and makes the theorems vacuous. The set
    # walked here comes from the kernel environment, so a dependency cannot be
    # silently left off a hand-written list; anything unpinned is an error.
    bad += _definition_pin_errors(deps, queried, defs)
    bad += _theorem_axiom_errors(theorems, got, allowed, native_ok, native_src)
    bad += _statement_pin_errors(queried, got, pinned)
    return "; ".join(bad) if bad else None


def _first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"{i}: pinned …{a[max(0, i - 30):i + 30]}… vs actual …{b[max(0, i - 30):i + 30]}…"
    return f"{min(len(a), len(b))}: one is a prefix of the other"


def guard_sources(front, proofs_dir=HERE):
    """The source layer for a front: EVERY proofs/*.lean, plus the registry.

    Auditing only the front's own files meant a new `proofs/Helper.lean` was
    never scanned by any bridge (it was unreachable only because the bridges
    hardcode their module tuples — a refactor reading `front["build"]` would
    have opened it). Every `.lean` in the TREE is scanned here — the walk was
    `os.listdir`, so a subdirectory file was scanned by nothing at all and
    `proofs/Sub/Evil.lean` could hold `axiom backdoor : False` with this
    function returning `[]` (F21) — under the runner profile only where a front
    explicitly registers it as a runner, by its proofs-relative path.
    """
    problems = []
    runners = set(front.get("runner_sources", []))
    for f in (front.get("_pins") or {}).get("fronts", {}).values():
        runners |= set(f.get("runner_sources", []))
    for f, _mod in lean_sources(proofs_dir):
        profile = "runner" if f in runners else "strict"
        problems += [f"{f}: {p}" for p in
                     source_guard(os.path.join(proofs_dir, f), profile,
                                  proofs_dir)]
    problems += coverage_guard(front.get("_pins"), proofs_dir)
    problems += registry_guard(front.get("_pins"), proofs_dir)
    return problems


# --------------------------------------------------------------------------
# pin regeneration (a human runs this and reviews the diff)
# --------------------------------------------------------------------------

def _regen_front(lean, name, front, core):
    bad = [module for module in front["build"] + front["modules"]
           if _shadows_core(module)]
    if bad:
        raise RuntimeError(
            f"front {name!r} names core-shadowing module(s) {bad} — regen "
            "builds them into the directory it then hands the driver as "
            "LEAN_PATH, which would poison the guard's own environment")
    queried = list(front["guarded"]) + [
        source for source in front.get("native_decide_sources", [])
        if source not in front["guarded"]]
    with tempfile.TemporaryDirectory() as temp_dir:
        error = build_front(lean, front, temp_dir)
        if error:
            raise RuntimeError(error)
        got, deps, _ = env_query(lean, front["modules"], queried, temp_dir,
                                 core=core)
    return queried, got, deps


def _refresh_statement_pins(pins, front, queried, got):
    for theorem in queried:
        old = pins["statements"].get(theorem)
        actual = got[theorem]["type"]
        pins["statements"][theorem] = actual
        state = "unchanged" if old == actual else ("NEW" if old is None else "CHANGED")
        tag = ("" if theorem in front["guarded"]
               else "  [native_decide source]")
        print(f"{state:9s} {theorem}  axioms={got[theorem]['axioms']}{tag}")


def _refresh_definition_pins(pins, queried, deps):
    for name in sorted(set(deps) - set(queried)):
        new, old = pin_of(deps[name]), pins["definitions"].get(name)
        pins["definitions"][name] = new
        if old != new:
            print(f"{'NEW' if old is None else 'CHANGED':9s} def {name}")


def _write_refreshed_pins(pins):
    with open(PINS_PATH, "w", encoding="utf-8") as target:
        json.dump(pins, target, indent=2, ensure_ascii=False)
        target.write("\n")
    with open(PINS_PATH, "rb") as source:
        digest = hashlib.sha256(source.read()).hexdigest()
    try:
        with open(CLAIMS_PATH, encoding="utf-8") as source:
            claims = source.read()
        claims = re.sub(r"(?m)^pins-sha256 .*$", "pins-sha256 " + digest, claims)
        with open(CLAIMS_PATH, "w", encoding="utf-8") as target:
            target.write(claims)
    except OSError as error:
        print(f"WARNING: could not refresh {CLAIMS_PATH}: {error}")

def regen(argv):
    """Rewrite the `statements` map from the current sources.

    This is the one operation that can make a drifted statement pass, so it is
    never invoked by a bridge or by CI: run it deliberately, then read the
    diff as you would read the theorem statements themselves.
    """
    lean = find_lean()
    if lean is None:
        print("regen needs a `lean` binary")
        return 2
    pins = load_pins()
    pins.setdefault("definitions", {})
    core = pins.get("core_modules") or list(CORE_ALLOWANCE)
    fronts = argv or list(pins["fronts"])
    for name in fronts:
        front = pins["fronts"][name]
        try:
            queried, got, deps = _regen_front(lean, name, front, core)
        except RuntimeError as error:
            print("FAIL " + str(error))
            return 1
        _refresh_statement_pins(pins, front, queried, got)
        _refresh_definition_pins(pins, queried, deps)
    _write_refreshed_pins(pins)
    print(f"wrote {PINS_PATH} — review the diff")
    print(f"refreshed the pins-sha256 line of {CLAIMS_PATH}. Nothing else "
          "there is regenerated: every identity claim (guarded theorems, "
          "native_decide sources, build/modules/sources/axioms, the "
          "core-module allowance, the unguarded allowlist) is a claim change "
          "and must be made by hand, in a diff a human reads.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "regen":
        sys.exit(regen(sys.argv[2:]))
    print(__doc__)
    print("usage: proof_guard.py regen [front ...]   (rewrite statement pins)")
    # This file is a library with ONE command (`regen`); every check it
    # implements is run by the bridges. Printing usage and exiting 0 made
    # `python3 proofs/proof_guard.py && echo guarded` print "guarded" — a
    # process that checked nothing reporting success, the same class as the
    # walk that scanned nothing above. Usage is a misuse, so it exits 2.
    sys.exit(2)
