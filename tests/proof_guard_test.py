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

Also asserted: coverage (an unregistered theorem, and an anonymous `example`,
are errors), an empty guarded list is an error, an unpinned theorem or
definition is an error, a lexer disagreement (unterminated literal) is an
error, an unaudited `proofs/*.lean` is an error, and no false positive on the
real proofs/*.lean.

All Lean scratch files live in a temp dir — nothing touches proofs/.
Needs `lean` for the semantic layer; exit 2 if unavailable (like the bridges).
Run: python3 tests/proof_guard_test.py
"""
import json
import os
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
         "native_decide_ok": [], "strict_sources": ["GuardCase.lean"],
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
        got, deps = proof_guard.env_query(lean, ["GuardCase"], list(decls), td)
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

    # the real proof files must stay clean (no false-positive regression)
    for f in sorted(os.listdir(os.path.join(REPO, "proofs"))):
        if f.endswith(".lean"):
            profile = "runner" if f.endswith("Run.lean") else "strict"
            probs = proof_guard.source_guard(os.path.join(REPO, "proofs", f),
                                             profile)
            check(f"source guard quiet on proofs/{f} ({profile})", not probs,
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
    check("F14 demoting a guarded theorem trips the per-front count",
          any("guards 5 theorems" in x for x in probs), str(probs))
    check("F14 the demoted theorem is not on the reviewed unguarded allowlist",
          any(t in x and "allowlist" in x for x in probs), str(probs))

    with tempfile.TemporaryDirectory() as td:
        claims = os.path.join(td, "CLAIMS.txt")
        with open(claims, "w") as f:
            f.write("pins-sha256 " + "0" * 64 + "\n")
        probs = proof_guard.registry_guard(real, claims_path=claims)
        check("F14 a wrong pins-sha256 is a failure",
              any("content hash" in x for x in probs), str(probs))
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

    # --- semantic layer: pin the CLEAN statement, then attack it ----------
    with tempfile.TemporaryDirectory() as td:
        write(td, CLEAN)
        err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        check("clean fixture compiles", not err, str(err))
        got, _deps = proof_guard.env_query(
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
                        native_decide_ok=["memory_bound"]), td)
        check("F3 (a) a FALSIFIED claim is caught by the statement pin",
              bool(sem), str(sem))
    with tempfile.TemporaryDirectory() as td:
        p = write(td, evil)
        err = proof_guard.build_olean(lean, "GuardCase", td, src_dir=td)
        check("F3 (b) statement-preserving evil proof compiles", not err, str(err))
        sem = proof_guard.guard_semantics(
            lean, front(["memory_bound"], {"memory_bound": PIN},
                        native_decide_ok=["memory_bound"]), td)
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
