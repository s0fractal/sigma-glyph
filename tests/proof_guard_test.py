#!/usr/bin/env python3
"""Regression: the bridge soundness guard rejects every proven bypass vector.

Round 1 (2026-07 fresh-context review) — both compiled clean under `lean`
(exit 0) and passed the then-current textual regexes:

  1. `theorem ... := sorryAx _ true`   — word boundary defeated by the `A`;
  2. `private axiom oops : False` + `:= oops.elim` — line-start anchor
     defeated by the modifier (any of private/protected/noncomputable/@[...]).

Round 2 (a second fresh-context review, which broke the round-1 fix):

  F1  `theorem memory_bound : True := trivial` — the guard checked axiom cones
      but never the STATEMENT, so a vacuous theorem was certified "std axioms
      only" and the bridge printed PREMISE HOLDS. This test's CLEAN fixture
      used to be `(1 : Nat) = 1 := rfl` asserted as ACCEPTED — the fixture
      enshrined the hole. It is now a real statement, pinned, and the vacuous
      / weakened-hypothesis / changed-conclusion variants must all be
      rejected against that pin.
  F2a `def blind : String := "/-"` opened a block comment for the STRIPPER,
      hiding a bare `axiom oops : False` from the textual layer.
  F2b the query file `import`ed the audited module, so the audited module
      could override `#print axioms` syntax and dictate the guard's input.
      The query now loads the module as DATA; this test proves the override
      no longer changes the answer.
  F2c `import Lean` in an audited proof file (what makes F2b spellable) is
      itself a hard failure — these are core-Lean-only proofs.
  F3  `@[implemented_by]` + `native_decide` proves arbitrary falsehoods, and
      `@[implemented_by]`/`@[extern]` decouple `lean --run` (the differential
      harnesses) from the kernel definition. The vector compiles clean, so the
      attribute allowlist is the line of defense.
  P3  a hand-written `axiom fake._native.native_decide.ax_1_1 : False` is
      accepted by the axiom layer alone (it mimics the allowed shape) — the
      two layers are not independent, so the source layer must catch it even
      when the stripper is under attack (F2a).

Round 3 (a third fresh-context review, which confirmed the round-2 fixes and
then broke what they left uncovered — all four vectors below were GREEN,
end-to-end, against the real proof files):

  F12 pinning STATEMENTS does not stop DEFINITIONS from being gutted. Deleting
      `Reach`'s `| step` constructor (4 lines) or emptying `Reach` altogether
      left every pinned dump byte-identical and `BRIDGE: PREMISE HOLDS` on a
      theorem covering one state / nothing; `def Valid (_w : Wave) : Prop :=
      False` made three wave theorems vacuous with `WAVE-BRIDGE: ALL AGREE
      (582/582)`. The claimed compensating control did not exist: no
      differential runs Lean over a Prop-valued definition. Every definition a
      guarded statement's meaning depends on is now pinned too — value for
      definitions, constructor list for inductives — over a dependency set
      computed from the kernel environment.
  F13 string-literal CONTENT was not pinned: the dump said `(strLit 64)`, "a
      64-character string". Swapping `hIT`/`hKT`'s bodies and the two pinned
      hex strings kept every theorem true, every pin matched, and
      `BYTE-BRIDGE: ALL AGREE (334/334)` — with TV-1 `genesis_I` asserting K's
      hash. Literals now dump by content, and `byte_bridge_check.py`
      cross-checks the genesis claims against the oracle.
  F14 `theorem_pins.json` was self-authorizing: moving a theorem to
      `unguarded` with a plausible reason and replacing it with
      `: True := trivial` passed everything. Its shape is now asserted against
      the reviewed `proofs/GUARD_CLAIMS.txt`.
  F15 `open X in theorem …` / `set_option … in theorem …` on ONE line hid a
      declaration from the coverage registry entirely (the matcher was
      line-anchored), defeating both README §7 claims.

Round 4 (a fourth fresh-context review; it confirmed round 3 where it applies
— the SHA-256-pinned large dumps, the pinned constructor TYPES, the literal
fix and the genesis differential all held — and then attacked the guard's
SCOPE, which was self-authorized. Every vector below was GREEN end-to-end):

  F16 the round-3 coverage fix was still LINE-based: the walk `continue`d on
      any line matching `namespace …`/`section`/`end`, and Lean separates
      commands by whitespace, not newlines. `namespace Zzz theorem
      hidden_by_ns : True := trivial end Zzz` appended to WaveAlgebra.lean →
      `WAVE-BRIDGE: ALL AGREE`, rc 0; `end Sec1 theorem hidden_by_end …` and
      `namespace Zzz2 example …` likewise; and `namespace Book1.C1 theorem
      sneaky_native : (2:Nat)^10 = 1024 := by native_decide end Book1.C1`
      appended to C1Compiler.lean printed "axiom cones are exactly within
      [propext]" with an unqueried native_decide theorem in the file. The walk
      is now over COMMANDS across the whole file.
  F17 the definition-pin scope came from `front["build"]`, a field nothing
      compiled from: the driver silently dropped every constant owned by a
      module outside it. `wave build → ["LutData"]` restored the round-3
      `Valid := False` vector (ALL AGREE 582/582); `size build → ["LutData"]`
      restored the gutted `Reach` (PREMISE HOLDS); `bytes build →
      ["MachineBytes"]` unpinned all 12 `Sha256.*` dependencies (31 → 19)
      with ALL AGREE. The scope is now the COMPLEMENT of a claimed core-Lean
      allowance, derived from the kernel environment, and `build` is the one
      place a front's compiled set is spelled — bridges and guard read it.
  F18 GUARD_CLAIMS.txt constrained COUNTS, not identities, so a demotion was a
      one-line `pins-sha256` diff — the single line `regen` rewrites anyway.
      The claims are identities now, over every field the guard consults.
  F19 binder annotations and universe parameters were dropped from the dump,
      so `(a b : Nat) (h : a ≤ b)` and `{a b : Nat} ⦃h : a ≤ b⦄` pinned
      identically. Both are in the dump now.
  F20 a `native_decide` trust axiom was accepted on its SHAPE alone, so a
      theorem on `native_decide_ok` could carry one generated by any other
      declaration, guarded or not. The generating declarations are an explicit
      claimed list, and each is statement-pinned.

Round 5 (a cross-family review by z-ai/glm-4.7 — this one found the defect,
we reproduced it before fixing it):

  F21 the file walk was not recursive. `guard_sources`, `coverage_guard` and
      `registry_guard` each did `os.listdir(proofs_dir)`, so a `.lean` in a
      SUBDIRECTORY was invisible to every textual check while the guard
      claimed to cover "every theorem in proofs/*.lean" and "every .lean under
      proofs/". Reproduced on the real tree: `proofs/Sub/Evil.lean` holding
      `axiom backdoor : False` gave `guard_sources(...) == []` and
      `proofs/bridge_check.py` → `BRIDGE: PREMISE HOLDS ON ALL OBSERVED
      STEPS`, rc 0. Two by-products, both closed here: the import allowlist
      came from the audited file's OWN directory, so a decoy
      `proofs/Sub/Lean.lean` made `import Lean` legal inside `proofs/Sub/`
      (F2c by path); and `_shadows_core` was never applied to the module name
      a file's PATH implies (`proofs/Lean/Foo.lean` → `Lean.Foo`).
  F22 (found by the sibling exit-code audit, handed over) `proof_guard.py`
      with no arguments printed its docstring and exited 0, so
      `python3 proofs/proof_guard.py && echo guarded` printed "guarded" — a
      process that ran no check at all reporting success. Usage now exits 2.

Also asserted: coverage (an unregistered theorem, and an anonymous `example`,
are errors), an empty guarded list is an error, an unpinned theorem or
definition is an error, a lexer disagreement (unterminated literal) is an
error, an unaudited `proofs/*.lean` is an error, and no false positive on the
real proofs/*.lean.

All Lean scratch files live in a temp dir — nothing touches proofs/.
Needs `lean` for the semantic layer; exit 2 if unavailable (like the bridges).
Run: python3 tests/proof_guard_test.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "proofs"))
import proof_guard  # noqa: E402

# ---- round-1 vectors (must stay dead) ------------------------------------
VECTOR_SORRYAX = (
    "theorem memory_bound : (1 : Nat) = 2 := sorryAx _ true\n")
VECTOR_PRIV_AXIOM = (
    "private axiom oops : False\n"
    "theorem memory_bound : (1 : Nat) = 2 := oops.elim\n")
VECTOR_ATTR_AXIOM = (
    "@[simp] axiom oops2 : (2 : Nat) = 3\n"
    "theorem memory_bound : (2 : Nat) = 3 := oops2\n")

# ---- the honest article: a real statement, provable, std axioms ----------
CLEAN = (
    "-- a comment mentioning sorry, admit and axiom must not trip the guard\n"
    "/- nor a block comment: private axiom -/\n"
    "theorem memory_bound (size spent : Nat) (h : size ≤ spent) :\n"
    "    size ≤ spent + 1 := Nat.le_succ_of_le h\n")

# ---- F1: statement attacks that keep the axiom cone clean ---------------
VECTOR_VACUOUS = "theorem memory_bound : True := trivial\n"
VECTOR_WEAK_HYP = (
    "theorem memory_bound (size spent : Nat) (h : size + 1 ≤ spent) :\n"
    "    size ≤ spent + 1 := by omega\n")
VECTOR_CHANGED_CONCL = (
    "theorem memory_bound (size spent : Nat) (h : size ≤ spent) :\n"
    "    size ≤ spent + 2 := by omega\n")

# ---- F2a / P3: the stripper is blinded by a string literal --------------
VECTOR_BLINDED_AXIOM = (
    'def blind : String := "/-"\n'
    "axiom oops : False\n"
    "theorem memory_bound : (1 : Nat) = 2 := oops.elim\n")
VECTOR_BLINDED_FAKE_NATIVE = (
    'def blind : String := "/-"\n'
    "axiom memory_bound._native.native_decide.ax_1_1 : False\n"
    "theorem memory_bound : (1 : Nat) = 2 :=\n"
    "  (memory_bound._native.native_decide.ax_1_1).elim\n")

# ---- F2b / F2c: the audited file dictating the guard's input ------------
VECTOR_SYNTAX_OVERRIDE = (
    "import Lean\n"
    "open Lean Elab Command\n"
    'def blind : String := "/-"\n'
    "axiom oops : False\n"
    'syntax (name := fk) (priority := high) "#print" &"axioms" ident : command\n'
    "@[command_elab fk] def elabFk : CommandElab := fun stx => do\n"
    "  logInfo m!\"'{stx[2].getId}' depends on axioms: [propext, Quot.sound]\"\n"
    "theorem memory_bound : (1 : Nat) = 2 := oops.elim\n")

# ---- F3: implemented_by + native_decide --------------------------------
VECTOR_IMPLEMENTED_BY = (
    "def evilImpl : Bool := true\n"
    "@[implemented_by evilImpl] def evilFlag : Bool := false\n"
    "theorem memory_bound : (1 : Nat) = 2 := by\n"
    "  have h1 : evilFlag = true := by native_decide\n"
    "  have h2 : evilFlag = false := rfl\n"
    "  simp [h1] at h2\n")
VECTOR_EXTERN = (
    '@[extern "lean_nat_add"] opaque wat : Nat → Nat\n'
    "theorem memory_bound : (1 : Nat) = 1 := rfl\n")
VECTOR_SKIP_KERNEL = (
    "set_option debug.skipKernelTC true in\n"
    "theorem memory_bound : (1 : Nat) = 1 := rfl\n")

# ---- lexer honesty ------------------------------------------------------
VECTOR_UNTERMINATED = 'def s : String := "oops\n'

# ---- F12: the STATEMENT is pinned, the DEFINITIONS it means were not ----
# `memory_bound`'s elaborated type is `∀ {a}, Reach a → 1 ≤ a` in all three of
# these. Deleting `Reach`'s recursive constructor shrinks the theorem to the
# single state `1`; emptying `Reach` makes it about nothing at all. Neither
# touches the pinned statement dump, and no differential can ever exercise a
# Prop-valued definition, so nothing else in the stack sees it.
IND_CLEAN = (
    "inductive Reach : Nat → Prop where\n"
    "  | init : Reach 1\n"
    "  | step {a : Nat} : Reach a → Reach (a + 1)\n"
    "theorem memory_bound {a : Nat} (r : Reach a) : 1 ≤ a := by\n"
    "  induction r with\n"
    "  | init => omega\n"
    "  | step _ ih => omega\n")
IND_GUTTED = (
    "inductive Reach : Nat → Prop where\n"
    "  | init : Reach 1\n"
    "theorem memory_bound {a : Nat} (r : Reach a) : 1 ≤ a := by\n"
    "  cases r; omega\n")
IND_EMPTY = (
    "inductive Reach : Nat → Prop where\n"
    "theorem memory_bound {a : Nat} (r : Reach a) : 1 ≤ a := by\n"
    "  nomatch r\n")

# `Valid := False` makes every Valid-hypothesis theorem vacuous while the
# statements stay byte-identical (the reviewer's WaveAlgebra vector).
PROP_CLEAN = (
    "def Valid (n : Nat) : Prop := 1 ≤ n\n"
    "theorem memory_bound (n : Nat) (h : Valid n) : 0 < n := h\n")
PROP_VACUOUS = (
    "def Valid (_n : Nat) : Prop := False\n"
    "theorem memory_bound (n : Nat) (h : Valid n) : 0 < n := h.elim\n")

# ---- F13: string-literal CONTENT was not pinned -------------------------
# The dump rendered a literal as `(strLit <length>)`, i.e. "a 1-character
# string" / "a 64-character string". Swapping the atoms kept every theorem
# true, every statement pin matched, and the genesis hash pins were free.
STR_I = ('def tag : String := "I"\n'
         'theorem memory_bound : tag = "I" := rfl\n')
STR_K = ('def tag : String := "K"\n'
         'theorem memory_bound : tag = "K" := rfl\n')

# ---- F15: a same-line prefix hid a declaration from coverage ------------
VECTOR_PREFIXED_DECLS = (
    "open Nat in theorem hidden_by_open : (1 : Nat) = 1 := rfl\n"
    "set_option linter.unusedVariables false in "
    "theorem hidden_by_setoption : (1 : Nat) = 1 := rfl\n"
    "open Nat in private theorem hidden_by_private : (1 : Nat) = 1 := rfl\n"
    "open Nat in example : (1 : Nat) = 1 := rfl\n")

# ---- F16: a scope command on the SAME LINE as the declaration -----------
# Lean separates commands by whitespace, not newlines. The round-3 walk was
# still line-based and `continue`d on any line starting with a scope keyword,
# so everything below was invisible to coverage — each of these appended to a
# real proof file left its bridge printing ALL AGREE, rc 0.
VECTOR_ONELINE_NS = (
    "namespace Zzz theorem hidden_by_ns : True := trivial end Zzz\n")
VECTOR_ONELINE_END = (
    "section Sec1\nend Sec1 theorem hidden_by_end : True := trivial\n")
VECTOR_ONELINE_EXAMPLE = (
    "namespace Zzz2 example : True := trivial end Zzz2\n")
#: The escalation the reviewer ran against the real C1Compiler.lean: an
#: unqueried `native_decide` theorem inside the guarded front's own namespace,
#: while the bridge prints "axiom cones are exactly within [propext]".
VECTOR_ONELINE_ESCALATION = (
    "namespace Book1.C1 theorem sneaky_native : (2:Nat)^10 = 1024 := by "
    "native_decide end Book1.C1\n")
#: `namespace X … end X` on one line used to push without popping, so the NEXT
#: declaration got a doubled prefix (`WaveAlgebra.WaveAlgebra.fold_…`) and was
#: "unregistered" for the wrong reason.
VECTOR_ONELINE_BALANCED = (
    "namespace Ns1 theorem inside_ns : True := trivial end Ns1\n"
    "theorem outside_ns : True := trivial\n")
#: A bare `end` closes an anonymous section; the next line's `theorem` must not
#: be swallowed as its argument.
VECTOR_BARE_END = (
    "section\nend\ntheorem after_bare_end : True := trivial\n")

# ---- F19: binder annotations and universe params were not pinned ---------
BINDER_EXPLICIT = ("theorem memory_bound (a b : Nat) (h : a ≤ b) : "
                   "a ≤ b + 1 := Nat.le_succ_of_le h\n")
BINDER_IMPLICIT = ("theorem memory_bound {a b : Nat} ⦃h : a ≤ b⦄ : "
                   "a ≤ b + 1 := Nat.le_succ_of_le h\n")

# ---- F17: a dependency in a module the front does not name ---------------
# `Base` owns the Prop the theorem's hypothesis is about; `Top` states it.
# With the scope taken from an editable per-front list, naming only `Top` made
# `Base.Valid` vanish from the pinned set with no message at all.
BASE_CLEAN = ("namespace Base\ndef Valid (n : Nat) : Prop := 1 ≤ n\n"
              "end Base\n")
BASE_VACUOUS = ("namespace Base\ndef Valid (_n : Nat) : Prop := False\n"
                "end Base\n")
TOP_SRC = ("import Base\n"
           "theorem memory_bound (n : Nat) (h : Base.Valid n) : 0 < n := h\n")
TOP_SRC_VACUOUS = ("import Base\n"
                   "theorem memory_bound (n : Nat) (h : Base.Valid n) : "
                   "0 < n := h.elim\n")

# ---- F20: a native_decide trust axiom from ANOTHER declaration -----------
NATIVE_BORROWED = (
    "theorem helper_scan : (2 : Nat) ^ 10 = 1024 := by native_decide\n"
    "theorem memory_bound (a b : Nat) (h : a ≤ b) : a ≤ b + 1 := by\n"
    "  have := helper_scan\n"
    "  exact Nat.le_succ_of_le h\n")

failures = []


def check(name, ok, detail=""):
    print(("ok    " if ok else "FAIL  ") + name
          + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def write(td, body, name="GuardCase.lean"):
    p = os.path.join(td, name)
    with open(p, "w") as f:
        f.write(body)
    return p


def front(guarded, statements, definitions=None, **kw):
    """A minimal front for the fixtures (the registry shape guard_semantics
    and guard_sources consume)."""
    f = {"name": "test", "modules": ["GuardCase"], "build": ["GuardCase"],
         "guarded": guarded, "statements": statements,
         "definitions": definitions if definitions is not None else {},
         "allowed_axioms": list(proof_guard.STD_AXIOMS),
         "native_decide_ok": [], "native_decide_sources": [],
         "core_modules": list(proof_guard.CORE_ALLOWANCE),
         "strict_sources": ["GuardCase.lean"],
         "runner_sources": [], "_pins": {"fronts": {}, "unguarded": {}}}
    f.update(kw)
    return f


def pin_fixture(lean, body, decls=("memory_bound",)):
    """Compile `body` and return (statement pins, definition pins)."""
    with tempfile.TemporaryDirectory() as td:
        write(td, body)
        err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        if err:
            raise RuntimeError(err)
        got, deps, _ = proof_guard.env_query(lean, ["GuardCase"], list(decls), td)
    return ({d: got[d]["type"] for d in decls},
            {k: proof_guard.pin_of(v) for k, v in deps.items()})


def semantics_of(lean, body, stmts, defs, decls=("memory_bound",), **kw):
    """Run the full semantic layer over `body` against the given pins."""
    with tempfile.TemporaryDirectory() as td:
        write(td, body)
        return (proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
                or proof_guard.guard_semantics(
                    lean, front(list(decls), stmts, defs, **kw), td))


def main():
    lean = proof_guard.find_lean()
    if lean is None:
        print("proof_guard test needs `lean` for the environment-query layer; "
              "exit 2")
        return 2

    # --- source layer -----------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        for name, body, want_reject in [
                ("source rejects sorryAx vector", VECTOR_SORRYAX, True),
                ("source rejects private-axiom vector", VECTOR_PRIV_AXIOM, True),
                ("source rejects attribute-axiom vector", VECTOR_ATTR_AXIOM, True),
                ("F2a source rejects axiom hidden behind a \"/-\" string literal",
                 VECTOR_BLINDED_AXIOM, True),
                ("P3 source rejects a hand-written native_decide-shaped axiom "
                 "behind the same blinding string", VECTOR_BLINDED_FAKE_NATIVE, True),
                ("F2c source rejects `import Lean` (+ syntax override)",
                 VECTOR_SYNTAX_OVERRIDE, True),
                ("F3 source rejects @[implemented_by]", VECTOR_IMPLEMENTED_BY, True),
                ("F3 source rejects @[extern]/opaque", VECTOR_EXTERN, True),
                ("F3 source rejects non-linter set_option (debug.skipKernelTC)",
                 VECTOR_SKIP_KERNEL, True),
                ("lexer disagreement (unterminated string) is a problem",
                 VECTOR_UNTERMINATED, True),
                ("source accepts clean file (comments mentioning the words)",
                 CLEAN, False),
                ("source accepts the vacuous theorem (it is the STATEMENT "
                 "layer's job, not this one)", VECTOR_VACUOUS, False)]:
            probs = proof_guard.source_guard(write(td, body))
            check(name, bool(probs) == want_reject,
                  f"problems={probs}")

    # the real proof files must stay clean (no false-positive regression).
    # Enumerated with the guard's OWN recursive walk, so this loop covers a
    # subdirectory source the day one appears (F21).
    proofs_dir = os.path.join(REPO, "proofs")
    for rel, _mod in proof_guard.lean_sources(proofs_dir):
        profile = "runner" if rel.endswith("Run.lean") else "strict"
        probs = proof_guard.source_guard(os.path.join(proofs_dir, rel),
                                         profile, proofs_dir)
        check(f"source guard quiet on proofs/{rel} ({profile})", not probs,
              str(probs))

    # --- coverage ---------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        write(td, "theorem brand_new_one : True := trivial\n"
                  "example : (1 : Nat) = 1 := rfl\n", "Cover.lean")
        pins = {"fronts": {"x": {"guarded": ["other"]}}, "unguarded": {}}
        probs = proof_guard.coverage_guard(pins, td)
        check("coverage flags an unregistered theorem",
              any("brand_new_one" in p for p in probs), str(probs))
        check("coverage rejects an anonymous `example`",
              any("example" in p for p in probs), str(probs))
        pins2 = {"fronts": {"x": {"guarded": ["brand_new_one"]}}, "unguarded": {}}
        write(td, "theorem brand_new_one : True := trivial\n", "Cover.lean")
        check("coverage quiet once the theorem is guarded",
              not proof_guard.coverage_guard(pins2, td))

    # F15: a declaration hidden behind a same-line prefix
    with tempfile.TemporaryDirectory() as td:
        write(td, VECTOR_PREFIXED_DECLS, "Cover.lean")
        probs = proof_guard.coverage_guard(
            {"fronts": {}, "unguarded": {}}, td)
        for what in ("hidden_by_open", "hidden_by_setoption",
                     "hidden_by_private"):
            check(f"F15 coverage sees `{what}` behind a same-line prefix",
                  any(what in p for p in probs), str(probs))
        check("F15 coverage still rejects `open … in example`",
              any("example" in p for p in probs), str(probs))

    # F16: a scope command on the SAME LINE as a declaration
    def covers(body, name="Cover.lean"):
        with tempfile.TemporaryDirectory() as td:
            write(td, body, name)
            return proof_guard.coverage_guard({"fronts": {}, "unguarded": {}}, td)

    for label, body, want in [
            ("`namespace Zzz theorem … end Zzz` on one line",
             VECTOR_ONELINE_NS, "Zzz.hidden_by_ns"),
            ("`end Sec1 theorem …` on one line",
             VECTOR_ONELINE_END, "hidden_by_end"),
            ("a declaration after a bare `end`",
             VECTOR_BARE_END, "after_bare_end"),
            ("`namespace Book1.C1 theorem … native_decide … end` (the "
             "escalation into a guarded front's own namespace)",
             VECTOR_ONELINE_ESCALATION, "Book1.C1.sneaky_native")]:
        probs = covers(body)
        check(f"F16 coverage sees a theorem hidden by {label}",
              any(want in p for p in probs), str(probs))
    probs = covers(VECTOR_ONELINE_EXAMPLE)
    check("F16 coverage rejects `namespace Zzz2 example … end Zzz2` on one line",
          any("example" in p for p in probs), str(probs))
    probs = covers(VECTOR_ONELINE_BALANCED)
    check("F16 a one-line namespace POPS: the next declaration is not "
          "double-prefixed",
          any("`Ns1.inside_ns`" in p for p in probs)
          and any("`outside_ns`" in p for p in probs), str(probs))

    # the real registry accounts for every theorem in proofs/*.lean
    check("coverage quiet on the real proofs/ tree with the real registry",
          not proof_guard.coverage_guard(),
          str(proof_guard.coverage_guard()))

    # --- F14: the pin registry is not self-authorizing ---------------------
    real = proof_guard.load_pins()
    check("registry guard quiet on the real registry + claims file",
          not proof_guard.registry_guard(), str(proof_guard.registry_guard()))

    def demoted():
        p = json.loads(json.dumps(real))
        t = p["fronts"]["wave"]["guarded"].pop()
        p["unguarded"][t] = "covered by the differential (a plausible reason)"
        return p, t

    p, t = demoted()
    probs = proof_guard.registry_guard(p)
    check("F14/F18 demoting a guarded theorem NAMES it in the diff",
          any(f"claims '{t}'" in x and "guarded" in x for x in probs),
          str(probs))
    check("F14 the demoted theorem is not on the reviewed unguarded allowlist",
          any(t in x and "allowlist" in x for x in probs), str(probs))

    # F18: counts were the whole claim, so a demotion could be masked by adding
    # a fresh trivial theorem in the victim's place — every number stayed equal
    # and the entire GUARD_CLAIMS.txt diff was the machine-written
    # `pins-sha256` line. Identity claims name both halves of the swap.
    p = json.loads(json.dumps(real))
    victim = "WaveAlgebra.crystallization"
    p["fronts"]["wave"]["guarded"] = [
        x for x in p["fronts"]["wave"]["guarded"] if x != victim
    ] + ["WaveAlgebra.placeholder_bound"]
    p["fronts"]["wave"]["native_decide_ok"] = [
        x for x in p["fronts"]["wave"]["native_decide_ok"] if x != victim]
    probs = proof_guard.registry_guard(p)
    check("F18 a count-preserving demotion names the DROPPED theorem",
          any(f"claims '{victim}'" in x and "guarded" in x for x in probs),
          str(probs))
    check("F18 a count-preserving demotion names the ADDED theorem",
          any("WaveAlgebra.placeholder_bound" in x and "does not claim" in x
              for x in probs), str(probs))
    check("F18 it also names the dropped native-decide-ok entry",
          any(f"claims '{victim}'" in x and "native-decide-ok" in x
              for x in probs), str(probs))

    # F18: the fields that had no claim at all
    for field, key, mutate in [
            ("build", "build",
             lambda f: f.__setitem__("build", ["WaveAlgebra"])),
            ("modules", "modules",
             lambda f: f.__setitem__("modules", ["LutData"])),
            ("allowed_axioms", "axioms",
             lambda f: f["allowed_axioms"].append("Sneaky.axiom")),
            ("native_decide_ok", "native-decide-ok",
             lambda f: f["native_decide_ok"].append("WaveAlgebra.lut_size")),
            ("native_decide_sources", "native-decide-sources",
             lambda f: f["native_decide_sources"].append("WaveAlgebra.lut_size")),
            ("strict_sources", "strict-sources",
             lambda f: f.__setitem__("strict_sources", ["WaveAlgebra.lean"])),
            ("runner_sources", "runner-sources",
             lambda f: f.__setitem__("runner_sources", []))]:
        p = json.loads(json.dumps(real))
        mutate(p["fronts"]["wave"])
        probs = proof_guard.registry_guard(p)
        check(f"F18 an edit to `{field}` produces a named claim failure",
              any(f"wave' {key}" in x for x in probs), str(probs))

    p = json.loads(json.dumps(real))
    p["core_modules"] = p["core_modules"] + ["Mathlib"]
    check("F18 widening the core-module allowance is a named claim failure",
          any("core-modules" in x and "Mathlib" in x
              for x in proof_guard.registry_guard(p)), "")
    p = json.loads(json.dumps(real))
    p["core_modules"] = []
    check("F17 an EMPTY core-module allowance is refused (it would put "
          "nothing in scope)",
          any("core_modules" in x for x in proof_guard.registry_guard(p)), "")

    with tempfile.TemporaryDirectory() as td:
        claims = os.path.join(td, "CLAIMS.txt")
        with open(claims, "w") as f:
            f.write("pins-sha256 " + "0" * 64 + "\n")
        probs = proof_guard.registry_guard(real, claims_path=claims)
        check("F14 a wrong pins-sha256 is a failure",
              any("content hash" in x for x in probs), str(probs))
        check("F18 a claims file that makes no per-front claim fails closed",
              any("no claims at all" in x for x in probs), str(probs))
        probs = proof_guard.registry_guard(
            real, claims_path=os.path.join(td, "absent.txt"))
        check("F14 a MISSING claims file fails closed",
              any("self-authorizing" in x for x in probs), str(probs))
        p = json.loads(json.dumps(real))
        p["unguarded"]["SigmaGlyph.step_preserves"] = ""
        check("F14 an unguarded entry with no reason is a failure",
              any("no real reason" in x
                  for x in proof_guard.registry_guard(p)), "")
        p = json.loads(json.dumps(real))
        p["fronts"]["size"]["build"] = ["Init", "SizeBound"]
        probs = proof_guard.registry_guard(p)
        check("F14/latent a core-shadowing module name is rejected",
              any("shadows a core Lean module" in x for x in probs), str(probs))

    # F17: registry_guard only ever checked build ⊆ audited-sources. Each of the
    # reviewer's three restorations began by SHRINKING `build`, which the
    # missing direction (compiled ⊆ build, and modules ⊆ build) now catches
    # even before the derived scope does.
    for name, shrunk in [("wave", ["LutData"]),
                         ("bytes", ["MachineBytes"]),
                         ("size", ["LutData"])]:
        p = json.loads(json.dumps(real))
        p["fronts"][name]["build"] = shrunk
        if name == "size":                      # the reviewer's exact shape
            p["fronts"][name]["strict_sources"] = ["SizeBound.lean",
                                                   "LutData.lean"]
        probs = proof_guard.registry_guard(p)
        check(f"F17 shrinking front {name!r}'s `build` is a hard failure "
              "(a strict source that is never compiled)",
              any("does not compile it" in x and f"{name}'" in x
                  for x in probs), str(probs))

    # latent: an unlisted proofs/*.lean is audited by nobody
    helper = os.path.join(REPO, "proofs", "Helper.lean")
    try:
        with open(helper, "w") as f:
            f.write("namespace Helper\nend Helper\n")
        probs = proof_guard.registry_guard()
        check("latent: a new proofs/*.lean that no front audits is a failure",
              any("Helper.lean" in x for x in probs), str(probs))
    finally:
        os.remove(helper)

    # --- F21: the walk was not recursive -----------------------------------
    # The reviewer's vector, on the REAL tree (same pattern as Helper.lean
    # above, one directory deeper). Before the fix all three of these were
    # empty and `python3 proofs/bridge_check.py` printed `BRIDGE: PREMISE
    # HOLDS ON ALL OBSERVED STEPS` and exited 0 with this file in place.
    sub = os.path.join(REPO, "proofs", "Sub")
    evil = os.path.join(sub, "Evil.lean")
    try:
        os.makedirs(sub, exist_ok=True)
        with open(evil, "w") as f:
            f.write("axiom backdoor : False\n"
                    "theorem secret_sauce : (1:Nat) = 1 := rfl\n")
        pins = proof_guard.load_pins()
        fr = dict(pins["fronts"]["size"])
        fr["_pins"] = pins
        probs = proof_guard.guard_sources(fr, os.path.join(REPO, "proofs"))
        check("F21 guard_sources reads a .lean in a SUBDIRECTORY at all "
              "(the axiom is seen)",
              any("Sub/Evil.lean" in x and "axiom" in x for x in probs),
              str(probs))
        cov = proof_guard.coverage_guard(pins, os.path.join(REPO, "proofs"))
        check("F21 coverage accounts for a subdirectory theorem",
              any("secret_sauce" in x for x in cov), str(cov))
        reg = proof_guard.registry_guard(pins, os.path.join(REPO, "proofs"))
        check("F21 an unregistered subdirectory .lean is a HARD failure, not "
              "merely a scanned file",
              any("Sub/Evil.lean" in x and "not audited" in x for x in reg),
              str(reg))
    finally:
        if os.path.exists(evil):
            os.remove(evil)
        if os.path.isdir(sub):
            os.rmdir(sub)
    check("F21 the fixture cleaned up after itself (no debris under proofs/)",
          not os.path.exists(sub) and not proof_guard.registry_guard()
          and not proof_guard.coverage_guard(), "")

    # F21 by-product 1: the import allowlist used to be the audited file's own
    # DIRECTORY listing, so a decoy module beside it authorised `import Lean` —
    # the import that makes the guard's query spoofable (F2c), reopened by path.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "Sub"))
        write(td, "namespace Lean\nend Lean\n", os.path.join("Sub", "Lean.lean"))
        p = write(td, "import Lean\ntheorem t : True := trivial\n",
                  os.path.join("Sub", "X.lean"))
        probs = proof_guard.source_guard(p, "strict", td)
        check("F21 a decoy `Sub/Lean.lean` no longer authorises `import Lean` "
              "for its neighbours",
              any("import Lean" in x for x in probs), str(probs))
        check("F21 the allowlist is the whole tree by MODULE name "
              "(`Sub.Lean`, not `Lean`)",
              any("'Sub.Lean'" in x for x in probs), str(probs))

    # F21 by-product 2: `_shadows_core` was applied to registered module names
    # only, never to the module a file's PATH implies.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "Lean"))
        write(td, "theorem t : True := trivial\n",
              os.path.join("Lean", "Foo.lean"))
        claims = os.path.join(td, "CLAIMS.txt")
        with open(claims, "w") as f:
            f.write("pins-sha256 " + "0" * 64 + "\n")
        probs = proof_guard.registry_guard(
            {"core_modules": ["Init"], "fronts": {}, "unguarded": {}},
            td, pins_path=os.path.join(REPO, "proofs", "theorem_pins.json"),
            claims_path=claims)
        check("F21 a source whose PATH implies a core module name "
              "(`proofs/Lean/Foo.lean` → `Lean.Foo`) is refused",
              any("shadows a core Lean module" in x and "Lean/Foo.lean" in x
                  for x in probs), str(probs))

    # F21, the other direction: a subdirectory source that IS registered by its
    # path is accepted — the rule is "registered or refused", and registration
    # has to be a real, expressible state, not a rule with nothing behind it.
    def _subdir_registry(td, strict_src):
        pins = {"core_modules": ["Init", "Lean", "Std"], "unguarded": {},
                "statements": {}, "definitions": {},
                "fronts": {"sub": {
                    "build": ["Sub.Ok"], "modules": ["Sub.Ok"],
                    "strict_sources": [strict_src], "runner_sources": [],
                    "allowed_axioms": ["propext"], "guarded": ["sub_ok"],
                    "native_decide_ok": [], "native_decide_sources": []}}}
        pins_path = os.path.join(td, "pins.json")
        with open(pins_path, "w") as f:
            json.dump(pins, f)
        digest = hashlib.sha256(open(pins_path, "rb").read()).hexdigest()
        claims = os.path.join(td, "CLAIMS.txt")
        with open(claims, "w") as f:
            f.write(f"pins-sha256 {digest}\ncore-modules Init Lean Std\n"
                    "front sub build Sub.Ok\nfront sub modules Sub.Ok\n"
                    f"front sub strict-sources {strict_src}\n"
                    "front sub runner-sources\nfront sub axioms propext\n"
                    "front sub guarded sub_ok\nfront sub native-decide-ok\n"
                    "front sub native-decide-sources\n")
        return pins, pins_path, claims

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "Sub"))
        write(td, "theorem sub_ok : True := trivial\n",
              os.path.join("Sub", "Ok.lean"))
        pins, pins_path, claims = _subdir_registry(td, "Sub/Ok.lean")
        probs = proof_guard.registry_guard(pins, td, pins_path, claims)
        check("F21 a subdirectory source registered by its PATH is accepted",
              not probs, str(probs))
        check("F21 coverage is quiet once the subdirectory theorem is guarded",
              not proof_guard.coverage_guard(pins, td),
              str(proof_guard.coverage_guard(pins, td)))
        # registering it by BASENAME must not work: `Ok.lean` is a different
        # file from `Sub/Ok.lean`, and accepting it would let a registry entry
        # cover a file that does not exist while the real one goes unaudited.
        pins2, pins_path2, claims2 = _subdir_registry(td, "Ok.lean")
        probs = proof_guard.registry_guard(pins2, td, pins_path2, claims2)
        check("F21 registering a subdirectory source by BASENAME does not "
              "cover it", any("Sub/Ok.lean" in x and "not audited" in x
                              for x in probs), str(probs))

    # F21: "registered" has to mean something the toolchain can carry out — a
    # dotted module name is a PATH to Lean, so a subdirectory module must
    # compile and answer the environment query like any other.
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "Sub"))
        write(td, CLEAN, os.path.join("Sub", "Deep.lean"))
        e = proof_guard.build_olean(lean, "Sub.Deep", td, src_dir=td)
        check("F21 build_olean compiles module `Sub.Deep` from Sub/Deep.lean",
              not e, str(e))
        got, _d, loaded = proof_guard.env_query(
            lean, ["Sub.Deep"], ["memory_bound"], td)
        check("F21 the environment query answers for a subdirectory module",
              bool(got["memory_bound"]["type"]) and loaded == ["Sub.Deep"],
              str(loaded))

    # --- F22: the module's own exit status ---------------------------------
    # Found by the sibling exit-code audit and handed over rather than edited
    # across agents. `proof_guard.py` with no arguments printed its docstring
    # and exited 0, so `python3 proofs/proof_guard.py && echo guarded` printed
    # "guarded": a process that ran no check reporting success. Same class as
    # F21 above — UNRUN is not PASS — so usage is exit 2, and only `regen`
    # (which a human runs deliberately) may return 0.
    gp = os.path.join(REPO, "proofs", "proof_guard.py")
    for label, argv in [("no arguments", []), ("an unknown subcommand",
                                               ["bogus"])]:
        r = subprocess.run([sys.executable, gp] + argv,
                           capture_output=True, text=True)
        check(f"F22 `proof_guard.py` with {label} exits nonzero "
              "(usage is not a passed check)", r.returncode == 2,
              f"rc={r.returncode}")
        check(f"F22 …and still prints the usage line ({label})",
              "usage: proof_guard.py regen" in r.stdout, r.stdout[-120:])

    # --- semantic layer: pin the CLEAN statement, then attack it ----------
    with tempfile.TemporaryDirectory() as td:
        write(td, CLEAN)
        err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        check("clean fixture compiles", not err, str(err))
        got, _deps, _mods = proof_guard.env_query(
            lean, ["GuardCase"], ["memory_bound"], td)
        PIN = got["memory_bound"]["type"]
        check("clean fixture's axioms are within the std set",
              set(got["memory_bound"]["axioms"]) <= set(proof_guard.STD_AXIOMS),
              str(got["memory_bound"]["axioms"]))
        check("a pinned statement is a non-trivial dump",
              "SigmaGlyph" not in PIN and len(PIN) > 80, PIN)

    cases = [
        ("guard accepts the clean, pinned proof", CLEAN, False),
        ("round-1 sorryAx vector rejected", VECTOR_SORRYAX, True),
        ("round-1 private-axiom vector rejected", VECTOR_PRIV_AXIOM, True),
        ("F1 vacuous `: True := trivial` rejected (statement pin)",
         VECTOR_VACUOUS, True),
        ("F1 weakened hypothesis rejected (statement pin)", VECTOR_WEAK_HYP, True),
        ("F1 changed conclusion rejected (statement pin)",
         VECTOR_CHANGED_CONCL, True),
        ("F2b syntax-override vector rejected — the data-only query reports "
         "the REAL axioms", VECTOR_SYNTAX_OVERRIDE, True),
    ]
    for name, body, want_reject in cases:
        with tempfile.TemporaryDirectory() as td:
            write(td, body)
            err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td) \
                or proof_guard.guard_semantics(
                    lean, front(["memory_bound"], {"memory_bound": PIN}), td)
            check(name, bool(err) == want_reject, str(err))
            if err and want_reject:
                print(f"      (guard said: {err.splitlines()[0][:120]})")

    # --- F12: the definitions the statement is ABOUT ----------------------
    stmts, defs = pin_fixture(lean, IND_CLEAN)
    check("F12 the pinned dependency set is computed, not hand-listed "
          "(the inductive and its constructors are in it)",
          {"Reach", "Reach.init", "Reach.step"} <= set(defs), str(sorted(defs)))
    check("F12 an inductive is pinned WITH its constructor list",
          "ctors [Reach.init Reach.step]" in defs["Reach"], defs["Reach"])
    err = semantics_of(lean, IND_CLEAN, stmts, defs)
    check("F12 the clean fixture passes the definition pins", not err, str(err))
    for name, body in [("F12 gutting an inductive (deleting the recursive "
                        "constructor) is rejected — the STATEMENT is "
                        "unchanged", IND_GUTTED),
                       ("F12 an EMPTY inductive (theorem about nothing) is "
                        "rejected", IND_EMPTY)]:
        st2, _ = pin_fixture(lean, body)
        check(name + " [statement really is byte-identical]",
              st2["memory_bound"] == stmts["memory_bound"], "statement moved")
        err = semantics_of(lean, body, stmts, defs)
        check(name, bool(err), str(err))
        if err:
            print(f"      (guard said: {err.splitlines()[0][:120]})")

    stmts, defs = pin_fixture(lean, PROP_CLEAN)
    st2, _ = pin_fixture(lean, PROP_VACUOUS)
    check("F12 `Valid := False` leaves the statement byte-identical",
          st2["memory_bound"] == stmts["memory_bound"], "statement moved")
    err = semantics_of(lean, PROP_VACUOUS, stmts, defs)
    check("F12 a Prop-valued definition replaced by False is rejected",
          bool(err), str(err))
    err = semantics_of(lean, IND_CLEAN, stmts, {})
    check("F12 an UNPINNED definition fails closed", bool(err), str(err))

    # --- F17: the audit scope is DERIVED, not configured -------------------
    # Two modules, the guarded statement in `Top`, the Prop it is about in
    # `Base`. Naming only `Top` used to make `Base.Valid` invisible to the pin
    # layer — no pin required, no message, and `Valid := False` passed.
    with tempfile.TemporaryDirectory() as td:
        write(td, BASE_CLEAN, "Base.lean")
        write(td, TOP_SRC, "Top.lean")
        for m in ("Base", "Top"):
            e = proof_guard.build_olean(lean, m, td, src_dir=td)
            check(f"F17 two-module fixture: {m} compiles", not e, str(e))
        got, deps, loaded = proof_guard.env_query(
            lean, ["Top"], ["memory_bound"], td)
        check("F17 the dependency set spans BOTH modules with no per-front "
              "list saying so", "Base.Valid" in deps, str(sorted(deps)))
        check("F17 the query reports every non-core module it loaded",
              sorted(loaded) == ["Base", "Top"], str(loaded))
        stmts = {"memory_bound": got["memory_bound"]["type"]}
        defs = {k: proof_guard.pin_of(v) for k, v in deps.items()}
        f_ok = front(["memory_bound"], stmts, defs, modules=["Top"],
                     build=["Base", "Top"], strict_sources=["Base.lean",
                                                            "Top.lean"])
        check("F17 the clean two-module fixture passes",
              not proof_guard.guard_semantics(lean, f_ok, td), "")
        f_narrow = front(["memory_bound"], stmts, defs, modules=["Top"],
                         build=["Top"], strict_sources=["Top.lean"])
        err = proof_guard.guard_semantics(lean, f_narrow, td)
        check("F17 a front that does not build a module in its own queried "
              "environment is refused", bool(err) and "Base" in str(err),
              str(err))
        if err:
            print(f"      (guard said: {err.splitlines()[0][:140]})")

    with tempfile.TemporaryDirectory() as td:
        write(td, BASE_VACUOUS, "Base.lean")
        write(td, TOP_SRC_VACUOUS, "Top.lean")
        for m in ("Base", "Top"):
            proof_guard.build_olean(lean, m, td, src_dir=td)
        got2, _d, _l = proof_guard.env_query(
            lean, ["Top"], ["memory_bound"], td)
        check("F17 `Base.Valid := False` leaves the statement byte-identical",
              got2["memory_bound"]["type"] == stmts["memory_bound"],
              "statement moved")
        err = proof_guard.guard_semantics(lean, f_ok, td)
        check("F17 gutting a definition in the SECOND module is rejected "
              "(the restored round-3 vector)", bool(err), str(err))
        if err:
            print(f"      (guard said: {err.splitlines()[0][:140]})")

    # --- F19: binder annotations and universe parameters --------------------
    stmts_e, defs_e = pin_fixture(lean, BINDER_EXPLICIT)
    stmts_i, _ = pin_fixture(lean, BINDER_IMPLICIT)
    check("F19 explicit and implicit binders no longer dump identically",
          stmts_e["memory_bound"] != stmts_i["memory_bound"],
          stmts_e["memory_bound"][:120])
    err = semantics_of(lean, BINDER_IMPLICIT, stmts_e, defs_e)
    check("F19 changing `(a b : Nat) (h : …)` to `{a b : Nat} ⦃h : …⦄` is "
          "rejected against the pin", bool(err), str(err))
    check("F19 the dump carries universe parameters",
          "(lvls [" in proof_guard.pin_of(list(defs_e.values())[0])
          if defs_e else True, str(list(defs_e.items())[:1]))

    # --- F20: a native_decide trust axiom from ANOTHER declaration ----------
    stmts_n, defs_n = pin_fixture(lean, NATIVE_BORROWED)
    err = semantics_of(lean, NATIVE_BORROWED, stmts_n, defs_n,
                       native_decide_ok=["memory_bound"])
    check("F20 a trust axiom generated by an unlisted declaration is rejected "
          "even when the consuming theorem is on native_decide_ok",
          bool(err) and "helper_scan" in str(err), str(err))
    if err:
        print(f"      (guard said: {err.splitlines()[0][:140]})")
    stmts_n2, defs_n2 = pin_fixture(lean, NATIVE_BORROWED,
                                    decls=("memory_bound", "helper_scan"))
    err = semantics_of(lean, NATIVE_BORROWED, stmts_n2, defs_n2,
                       native_decide_ok=["memory_bound"],
                       native_decide_sources=["helper_scan"])
    check("F20 the same axiom passes once its generator is named AND "
          "statement-pinned", not err, str(err))
    err = semantics_of(lean, NATIVE_BORROWED, stmts_n, defs_n2,
                       native_decide_ok=["memory_bound"],
                       native_decide_sources=["helper_scan"])
    check("F20 a named native_decide source with NO pinned statement fails "
          "closed", bool(err), str(err))

    # --- F13: string-literal CONTENT ---------------------------------------
    stmts_i, defs_i = pin_fixture(lean, STR_I)
    stmts_k, _ = pin_fixture(lean, STR_K)
    check("F13 two same-length string literals no longer dump identically",
          stmts_i["memory_bound"] != stmts_k["memory_bound"],
          stmts_i["memory_bound"])
    check("F13 a literal's content is recoverable from the dump",
          proof_guard.strlits(stmts_i["memory_bound"]) == ["I"],
          str(proof_guard.strlits(stmts_i["memory_bound"])))
    err = semantics_of(lean, STR_K, stmts_i, defs_i)
    check("F13 swapping a string literal for another of the SAME LENGTH is "
          "rejected (the genesis hash pins)", bool(err), str(err))
    if err:
        print(f"      (guard said: {err.splitlines()[0][:120]})")

    # F3, stated honestly. Two applications of the same trick:
    #  (a) falsify a PIN (the reviewer rewrote MachineBytes.genesis_I to claim
    #      a different hash) — the statement pin now catches that, because the
    #      claim itself changed;
    #  (b) keep the statement EXACTLY as pinned and prove it through the evil
    #      route. The cone then holds only allowed axioms and the statement
    #      matches, so the semantic layer accepts: the attribute denylist is
    #      the only thing that stops (b). That is what "the layers are not
    #      independent" means, and it is why the denylist is not optional.
    evil = (
        "def evilImpl : Bool := true\n"
        "@[implemented_by evilImpl] def evilFlag : Bool := false\n"
        "theorem memory_bound (size spent : Nat) (h : size ≤ spent) :\n"
        "    size ≤ spent + 1 := by\n"
        "  have h1 : evilFlag = true := by native_decide\n"
        "  have h2 : evilFlag = false := rfl\n"
        "  simp [h1] at h2\n")
    with tempfile.TemporaryDirectory() as td:
        write(td, VECTOR_IMPLEMENTED_BY)
        err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        check("F3 implemented_by+native_decide vector really does compile "
              "(so `lean` exiting 0 proves nothing)", not err, str(err))
        sem = proof_guard.guard_semantics(
            lean, front(["memory_bound"], {"memory_bound": PIN},
                        native_decide_ok=["memory_bound"],
                        native_decide_sources=["memory_bound"]), td)
        check("F3 (a) a FALSIFIED claim is caught by the statement pin",
              bool(sem), str(sem))
    with tempfile.TemporaryDirectory() as td:
        p = write(td, evil)
        err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        check("F3 (b) statement-preserving evil proof compiles", not err, str(err))
        sem = proof_guard.guard_semantics(
            lean, front(["memory_bound"], {"memory_bound": PIN},
                        native_decide_ok=["memory_bound"],
                        native_decide_sources=["memory_bound"]), td)
        check("F3 (b) the semantic layer alone does NOT catch it (documented, "
              "not fixed there)", sem is None, str(sem))
        check("F3 (b) the source denylist DOES catch it",
              any("implemented_by" in x for x in proof_guard.source_guard(p)),
              str(proof_guard.source_guard(p)))

    # --- fail-closed cases ------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        write(td, CLEAN)
        proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        err = proof_guard.guard_semantics(
            lean, front(["memory_bound", "gone_theorem"],
                        {"memory_bound": PIN, "gone_theorem": PIN}), td)
        check("a deleted/renamed guarded theorem fails, not skips", bool(err),
              str(err))
        err = proof_guard.guard_semantics(
            lean, front(["memory_bound"], {}), td)
        check("an UNPINNED guarded theorem fails closed", bool(err), str(err))
        err = proof_guard.guard_semantics(lean, front([], {}), td)
        check("an EMPTY guarded list is an error, not a vacuous pass",
              bool(err), str(err))
        err = proof_guard.guard_semantics(
            lean, front(["memory_bound"], {"memory_bound": PIN},
                        modules=["NoSuchModule"]), td)
        check("an unloadable module fails closed", bool(err), str(err))

    if failures:
        print(f"\nPROOF-GUARD: {len(failures)} FAILED")
        return 1
    print("\nPROOF-GUARD: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
