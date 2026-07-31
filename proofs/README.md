# Mechanized proofs

The assurance stack for Book I's normative memory bound
(`materialized_size − 1 ≤ spent`, §3.4) has three layers:

1. **Checked algebra** — `SizeBound.lean` (Lean 4 core, no mathlib):
   the seven-row accounting model of §3.4 entails the invariant by
   induction over traces, plus the preflight corollary
   (`size ≤ budget + 1`). Run: `lean proofs/SizeBound.lean`.
2. **Checked premise on live traces** — `bridge_check.py` drives the
   reference oracle step-by-step over adversarial terms (duplication
   towers, Ω, deep REF chains, dead branches, TV fixtures) and asserts
   every observed action satisfies the step-level premise the Lean
   proof consumes (`Δsize ≤ cost − 1`). Run: `python3 proofs/bridge_check.py`.
   NB (scope): the bridge does NOT prove row-by-row correspondence between
   runtime steps and the seven Lean constructors — it checks the weaker,
   theorem-sufficient inequality. Exact per-rule costs remain covered by the
   conformance vectors; a step-tag classifier is a possible future upgrade.
3. **Pinned end results** — the conformance vectors and property P7
   (`tests/spec_conformance/`).

## Book II wave algebra (`WaveAlgebra.lean`)

The §5 `interfere()` integer algebra is mechanized against the generated
LUT (`LutData.lean`, written by `gen_lut_lean.py`, which imports the
oracle's table and therefore inherits the Book II §4 SHA-256 arbiter
fail-fast; encoded as a string literal because a 32769-element array
literal elaborates quadratically). Theorems:

- `interfere_valid` — **range closure**: valid operands give valid results
  (the §3 width guarantee behind the int64 implementer note);
- `zero_amp_cascade` — §6.2's "the zero-amplitude cascade is a theorem",
  now literally one;
- `left_dominance_ph` — §5.2 Law of Left Dominance;
- `crystallization` — §5.1 Resonance Identity: the unique non-zero fixed
  point of self-interference is `{am = 65535, en = −32768}` (phase free);
- `fold_not_associative` / `not_commutative` — the ADR-006 fold killer and
  Left Dominance as machine-checked witnesses (FV-FOLD-UNSOUND operands).

**Bridge** — `wave_bridge_check.py`: (a) `LutData.lean` regenerates
byte-identically; (b) no `sorry`/`axiom` sneaks past `lean`'s exit code;
(c) the Lean `interfere` (executed via `WaveRun.lean`) agrees with the
live oracle on a 582-case deterministic boundary grid incl. the
crystallization point, the FV-FOLD-UNSOUND triple and negative-tie
parities. Run: `python3 proofs/wave_bridge_check.py`.

TCB honesty (sharpened by the Kimi v0.6.4 focused review): the base LUT
facts (`lut_range`, `lut_zero`, `lut_size`), the 65536-case amplitude
fixed-point scan (`am_fixed_scan`) and the concrete `divRoundHalfUp`
witnesses use `native_decide`, which adds the Lean compiler to the trusted
base. The interference theorems are *reasoning*-symbolic but not
TCB-independent: `interfere_valid` consumes `lut_range`, `zero_amp_cascade`
and `crystallization` consume `lut_zero`/`native_decide` witnesses — so
their soundness transitively rests on the compiler too. Only the pure
integer lemmas of this file (the `divRoundHalfUp` bounds, `clamp_range`,
`prod01_bounds`, `af_bounds`) and `left_dominance_ph` (via
`Int.emod_eq_of_lt`) are fully kernel-checked with no `native_decide` in
their dependency cone. (`size_pos` is the evaluator's size lemma and lives in
`EvalMachine.lean`, not here — this list named it by mistake until a 2026-07
review checked the attribution.) The differential bridge is the empirical check
that the Lean `interfere` is the oracle's, independent of the TCB question.

## Book I byte-level machine correspondence (`MachineBytes.lean` + `Sha256.lean`)

The §1.1/§2/§4.1 serialization layer is mechanized: `Node`, canonical
`serialize` (`[Op][Flags][Atom?][Left?][Right?]` with the normative
per-opcode flags), `deserialize` (§4.1 validation), and
`nodeHash = SHA-256 ∘ serialize` over a from-scratch FIPS 180-4 SHA-256
in core Lean (`Sha256.lean`, total — no `partial`/`unsafe`). Theorems:

- `serialize_injective` — distinct well-formed nodes never share canonical
  bytes (identity is injective; the hash layer above adds only CP-24);
- `deser_serialize` / `serialize_deser` — round-trip AND **canonicity**:
  a valid buffer is the unique serialization of its parse (no second byte
  form for any node);
- `deser_wf`, `valid_lengths` (§4.1 rule 3: valid buffers are 34 or 66
  bytes), `reserved_opcode_invalid` (§1.2: opcode `0x03` never parses);
- `lit_bytes_disjoint` — the byte-0 discrimination under `glyph_eq`'s O(1)
  redex recognition;
- **genesis pins** — `H(I)/H(K)/H(S)` (TV-1), the §4.2 Canonical Invalid
  Object, and `false_is_a_theorem` (§5.2: `H(APPLY(⟨K⟩,⟨I⟩))`) recomputed
  end-to-end (`serialize ∘ sha256`) and pinned to the spec constants — so
  "FALSE is a theorem, not an axiom" is now a `native_decide` fact.

**Bridge** — `byte_bridge_check.py`: no-`sorry` guard; FIPS 180-4 digest
vectors; and the executed Lean pipeline (`BytesRun.lean`) matched against
the live oracle on **334 buffers** — every conformance CAS object (incl.
the deliberately malformed Era-1 `0x03` one), the genesis bytes, and ~250
adversarial mutations (truncation, out-of-mask flags, wrong-in-mask flags,
reserved opcode, op/flag swap): CAS keys, §4.1 verdicts and round-trips
all agree. Run: `python3 proofs/byte_bridge_check.py`.

TCB honesty: the SHA-256 correctness and the genesis pins rest on
`native_decide` (Lean compiler in the trusted base) plus the FIPS/oracle
differential; the structural theorems (injectivity, round-trip,
canonicity, validation totality) are symbolic.

## Book I evaluator (`EvalMachine.lean`)

The v0.5 hash-thunk machine itself — the beating heart of Book I — is
modeled faithfully (mirrors `step5`/`eval_hash`): leftmost-outermost
reduction with lazy left-spine resolution and size-priced ATP, redex
recognition by hash (§3.1/§3.2), genesis I/K/S intrinsic (§5.1). It is
built on `MachineBytes`, so redex recognition uses the *proven*
serialization/hash layer, not a re-axiomatized one.

- **Totality is definitional** — `step` is well-founded on `sizeOf t`, `eval`
  is fuel-indexed structural recursion: `evalHash` is a *total function*, no
  partial/unsafe.
- **Determinism is definitional** — it is a function.
- `step_bounds` (via `fun_induction`) ⇒ `step_cost_le` (a fired action costs
  ≤ the remaining budget) and `step_cost_pos` (≥ 1: the §3.4 "minimum cost 1",
  so reduction cannot stall at zero cost).
- `eval_spent_le` / `evalHash_spent_le` — **`spent ≤ atp`**: the evaluator
  never overspends its budget, for ALL terms and budgets, now a theorem and
  not just a per-vector observation.
- `size_step` / `eval_size_bound` / `evalHash_size_bound` — the **ADR-001
  memory bound `size ≤ spent + 1`, proven directly on this concrete
  evaluator**. `size_step` is the exact §3.4 per-step accounting
  (`size t' + 1 ≤ size t + c` — every action grows the term by ≤ `cost − 1`;
  R-S, the only growing rule, holds *unconditionally*: the discarded ⟨S⟩ head
  is pure slack). This is the row-by-row step↔cost correspondence that
  `SizeBound.lean` assumed abstractly and `bridge_check.py` samples on live
  traces — here it is a theorem about the evaluator itself, no classifier.

**Bridge** — `eval_bridge_check.py`: no-`sorry` guard, compile (theorems check
on compile), and the executed Lean evaluator (`EvalRun.lean`) matched against
the live oracle on **all 33 eval conformance vectors** — result NodeHash AND
`atp_spent`, byte-exact — including Omega divergence (500 ATP → ATP
Exhausted), R-S size-pricing, genesis-intrinsic, store-isolation and stuck
forms. This is the empirical determinism/totality check: the total,
budget-respecting Lean function IS the oracle on the whole pinned surface.

## Book I §6 C1 compiler (`C1Compiler.lean`)

The canonical λ→SKI compiler (Profile C1) is mechanized: `Lam`/`Ski` terms, the
§6 bracket-abstraction `abstr` (A-1/A-2/A-3 **in order** — A-2 `x∉FV M → K M`
before A-3), and `c1`. Theorems:

- `mem_skiFv_abstr` — `A(x,·)` removes exactly `x` from the free variables;
- `mem_skiFv_c1` — **C1 preserves free variables exactly**;
- `c1_closed` — **a closed λ-term compiles to a variable-free SKI term**: the
  reference's runtime "free variable escapes abstraction" guard can never fire
  on closed input — a theorem, not a check. Determinism is definitional (`c1`
  is a total pure function).
- `tv10_id` / `tv10_const` — §6/TV-10 pinned by `rfl` (`C1[λx.x]=⟨I⟩`,
  `C1[λx.λy.x]=S(KK)I`). These were anonymous `example`s until a 2026-07
  round-2 review showed a falsified pin passed the bridge: an anonymous
  declaration has no name, so no axiom/statement query can ever reach it. They
  are named and guarded now.

TCB: these are **fully kernel-checked** — every one of the five depends on
`propext` alone, and the guard's allowed-axiom set for this front is exactly
`{propext}` (not the broader standard set), so the documented claim and the
enforced claim are the same sentence. The compiler behind the `Sha256`/wave
`native_decide` facts is NOT in this front's trusted base.

**Bridge** — `c1_bridge_check.py`: source + environment guard (hard exit 2 if
`lean` is missing — it used to print "skip lean check" and then
"C1-BRIDGE: ALL AGREE", so `proofs.yml`, which gates on that string, went
green with the Lean half never run), then a
faithful transcription of the Lean `abstr`/`c1` is diffed against the oracle's
`sigma_glyph.c1` on **3000 random closed λ-terms**, NodeHash-exact. (This bridge
already earned its keep: it caught an A-2/A-3 ordering bug in the first draft of
the Lean model — the oracle checks `x∉FV → K M` before the `S` rule for
applications too, and the model didn't.) Run: `python3 proofs/c1_bridge_check.py`.

## Mechanization status

The three ROADMAP formal-verification targets are covered — the Book I
memory bound (`SizeBound`), the Book II wave algebra (`WaveAlgebra`), Book I
byte-level correspondence (`MachineBytes`/`Sha256`) — plus a fourth: the
**Book I evaluator** (`EvalMachine`), giving Qwen's requested
determinism/totality (definitional) with the budget bound as a theorem and a
33-vector oracle differential. The Lean reduction relation *contains* redex
recognition (built on the proven byte layer), rather than deferring it to
vectors, and `EvalMachine.evalHash_size_bound` re-proves the ADR-001 memory
bound directly on the concrete evaluator — so the step-tag / row-by-row
correspondence that `SizeBound` assumed abstractly is now a theorem, not a
future classifier. The four fronts are *layered*, not independent:
`EvalMachine` is built on `MachineBytes`, which is built on `Sha256` — each
front stands on the proven one below it.

Not mechanized: `bridge_check.py` still samples the SizeBound premise on the
*Python oracle's* traces (a useful independent cross-check, since the Lean
proof is about the Lean model and the differential is what ties the two); a
Rust production implementation remains the last non-Lean Qwen item.

## Bridge soundness guard (`proof_guard.py` + `theorem_pins.json`)

`lean` exits 0 on `sorry` (warning only), so "CI compiled the proofs" is not
"CI checked the proofs" and every bridge carries its own guard. Three
successive fresh-context adversarial reviews (2026-07) each broke the
then-current guard; this is the fourth iteration. **What it enforces is listed
below; it is not a proof that no unsoundness route exists** — an earlier
version of this section claimed the axiom check "catches any unsoundness route
regardless of spelling", and the second review refuted that claim with four
vectors.

Enforced, per front, for the theorem lists above (front configuration,
allowed axioms and pinned statements: `theorem_pins.json`; the reviewed claim
about that file: [`GUARD_CLAIMS.txt`](GUARD_CLAIMS.txt)):

1. **Axiom cone** — the transitive axiom dependencies of each guarded theorem
   must lie inside that front's allowed set: the standard axioms (`propext`,
   `Classical.choice`, `Quot.sound`) — `{propext}` alone for C1 — plus
   `native_decide` trust axioms only for the theorems whose documented TCB
   already includes the compiler (the wave theorems, the byte-level genesis
   pins) **and only when the axiom was generated by a declaration on that
   front's claimed `native_decide_sources` list**, each of which is itself
   queried and statement-pinned. A trust axiom used to be accepted on its
   *shape* alone, so a permitted theorem could carry one generated by any
   declaration in the file, pinned or not.
2. **Statement** — the canonical dump of each guarded theorem's *elaborated
   type* must equal its pin. Axiom-cone checking alone certified
   `theorem memory_bound : True := trivial` as "std axioms only" and the
   bridge printed PREMISE HOLDS; a weakened hypothesis or an altered
   conclusion was equally invisible. Drift is a hard failure with a diff.
   The dump is structural (binder *names* and `mdata` dropped, binder
   *annotations* and universe parameters kept, constants by full name), never
   pretty-printed, so notation cannot make the printed statement differ from
   the elaborated one. String literals are dumped **by content** (hex of their
   UTF-8 bytes): the dump used to say `(strLit 64)`, "some 64-character
   string", which left every genesis hash pin unprotected. Binder annotations
   are in the dump because they were not: `(w1 w2 : Wave) (h : Valid w1)` and
   `{w1 w2 : Wave} ⦃h : Valid w1⦄` used to pin identically. (That one is a
   presentation change, not a soundness hole — the proposition is the same —
   but the sentence above says the dump equals the pin, so it now does.)
3. **Definitions** — pinning a statement does not stop the definitions it is
   *about* from being gutted underneath it. Deleting the `| step` constructor
   of `SizeBound`'s `Reach` (a 4-line diff) shrinks `memory_bound` to the
   single state `⟨1,0⟩`; emptying `Reach` makes it a theorem about nothing;
   `def Valid (_w : Wave) : Prop := False` makes `interfere_valid`,
   `left_dominance_ph` and `crystallization` vacuous. In all of these every
   pinned statement dump stayed byte-identical and every bridge stayed green.
   So each queried statement's **dependency set** is computed from the
   kernel environment — the constants in its type, then transitively through
   the types and *values* of the definitions those mention — and every member
   is pinned: a definition by its type AND value, an inductive by its type AND
   constructor list (with the constructors' own types). Dumps too long to read
   in a diff (the 200 KB `lutString`, `Sha256.sha256`) are pinned by SHA-256 of
   the same dump. A dependency with no pin is a hard failure, so a *new*
   dependency cannot appear silently, and the compiler-generated auxiliaries
   the eval statements are phrased in terms of (`EvalMachine.step.match_3`)
   are pinned like any other definition.
4. **Scope — derived, not configured.** What (3) covers used to be "constants
   owned by a module listed in `front["build"]`", a field no bridge compiled
   from (each hardcoded its own module tuple) and no claim covered. Deleting
   one name silently dropped every pin that module owned — no message — and
   restored three already-closed findings: `wave build → ["LutData"]` re-passed
   `Valid := False` (ALL AGREE 582/582), `size build → ["LutData"]` re-passed
   a gutted `Reach` (PREMISE HOLDS), `bytes build → ["MachineBytes"]` unpinned
   all 12 `Sha256.*` dependencies (31 → 19). Now: the scope is the
   **complement** of an explicit `core_modules` allowance (`Init`, `Lean`,
   `Std` — fixed by `lean-toolchain`, and itself a claimed line in
   `GUARD_CLAIMS.txt`), computed over the kernel environment, so an unpinned
   dependency is a hard failure whoever owns it. `build` is the single place a
   front's compiled module set is spelled: the bridges compile it
   (`proof_guard.build_front`) and the guard queries what they built. The
   driver reports every non-core module in the loaded environment and the
   guard refuses any the front does not build, and `registry_guard` checks the
   direction that was missing — every strict source must be a built module and
   every queried module must be a built module, not only the converse.
5. **Where the answer comes from** — a driver that loads the audited module's
   `.olean` as *data* (`Lean.Environment.importModules`) and walks the kernel
   environment. The previous query wrote a `.lean` file that `import`ed the
   audited module and ran `#print axioms`, so the audited module could
   override that syntax and hand the guard a fabricated axiom list; the
   end-to-end vector had `axiom oops : False`, `memory_bound := oops.elim`,
   and a green bridge.
6. **Imports** — an `import` naming anything outside the `proofs/` module set
   is a hard failure. These are core-Lean-only proofs, and `import Lean` in an
   audited file is what made (5) spellable. The module set is the whole tree by
   module name (`Sub/Ok.lean` → `Sub.Ok`), minus any name that shadows core
   Lean. It used to be the audited file's OWN directory listing, so a decoy
   `proofs/Sub/Lean.lean` made `import Lean` legal for everything beside it.
7. **Metaprogramming / compiler override** — attributes are allowlisted
   (`inline`, `simp`, `reducible`) and `implemented_by`, `extern`, `csimp`,
   `initialize`, `run_cmd`, `elab`, `macro`, `syntax`, `notation`, `unsafe`,
   `opaque`, `attribute`, `#`-commands and any non-`linter.*` `set_option`
   (which is where `debug.skipKernelTC` lives) are rejected. `@[implemented_by]`
   plus `native_decide` proves arbitrary falsehoods — the review used it to
   make `MachineBytes.genesis_I` claim a different hash with the bridge still
   printing ALL AGREE — and `@[implemented_by]`/`@[extern]` also decouple
   `lean --run` (the differential harnesses) from the kernel definitions.
   `partial` is allowed only in the `*Run.lean` I/O plumbing, which proves
   nothing.
8. **Text** — literal-aware comment stripping, then `sorry`/`admit` as
   substrings (catching `sorryAx`) and the `axiom` keyword in any position
   (catching `private axiom`). The stripper is literal-aware because
   `def blind : String := "/-"` opened a block comment *for the stripper* and
   hid everything after it, including a bare `axiom oops : False`. A literal
   or comment still open at EOF means our lexer and Lean's disagree about the
   file: that is a failure, not a shrug.
9. **Coverage** — every `theorem`/`lemma` in `proofs/*.lean` must be either in
   a front's guarded list or registered in `unguarded` with a reason, so a new
   theorem in an already-guarded file cannot slip in unqueried. Anonymous
   `example`s are rejected outright: nothing can query them. The scan walks
   **commands, not lines**: the file is scanned once for command keywords as
   tokens and the namespace/section stack is maintained across the whole file,
   so a declaration is found wherever a command can begin and its prefix is
   right regardless of newlines. Two rounds of review lived in this paragraph:
   `open Nat in theorem …` on one line defeated a line-anchored matcher, and
   then `namespace Zzz theorem hidden : True := trivial end Zzz` — one line,
   legal Lean — defeated its line-based replacement, including
   `namespace Book1.C1 theorem sneaky : … := by native_decide end Book1.C1`
   appended to `C1Compiler.lean` while the bridge printed "axiom cones are
   exactly within [propext]". Every `.lean` file in `proofs/` is scanned by
   every bridge, not only the files its own front lists — and "every" means
   **at any depth**: the walk was `os.listdir`, one directory, so
   `proofs/Sub/Evil.lean` carrying `axiom backdoor : False` was opened by no
   textual layer at all and `bridge_check.py` printed `PREMISE HOLDS`, rc 0
   (2026-07 cross-family review by z-ai/glm-4.7). One recursive enumeration
   (`proof_guard.lean_sources`) now feeds every source-layer check.
10. **The registry itself** — nothing used to hash, anchor or cross-check
   `theorem_pins.json`, so it authorized itself: moving a theorem from
   `guarded` to `unguarded` with a plausible reason and replacing it with
   `: True := trivial` passed every bridge, the pin and the axiom cone never
   consulted. Its shape is now a gated claim held in
   [`GUARD_CLAIMS.txt`](GUARD_CLAIMS.txt), and that claim is made by
   **identity, not by count**: every guarded theorem, every native_decide
   source, each front's `build`/`modules`/`strict_sources`/`runner_sources`/
   `allowed_axioms`, the `core_modules` allowance, the exact `unguarded`
   allowlist, and the pin file's content hash. Counts were not enough — hiding
   `crystallization` from coverage, replacing it with `: True := trivial` and
   registering a fresh trivial `placeholder_bound` in its place kept every
   number equal, and the entire diff of the claims file was the one
   `pins-sha256` line `regen` rewrites on every run. A demotion now produces
   diff lines that NAME the theorem. Also enforced there: every front audits
   every module it compiles *and* compiles every strict source it audits,
   every `.lean` in `proofs/` — at any depth, registered by its
   proofs-relative path (`Sub/Ok.lean`, module `Sub.Ok`) — is audited by some
   front, no front names a module that shadows core Lean (which would poison
   the driver's own `LEAN_PATH` under `regen`) and neither does any module
   name a source's own PATH implies (`proofs/Lean/Foo.lean` → `Lean.Foo`), no
   built module is registered as a runner, and an `unguarded` entry carries a
   real reason. There is deliberately no auditable-but-unbuilt tier for a
   subdirectory file: an unregistered `.lean` anywhere under `proofs/` is a
   hard failure, because a file that is merely scanned is indistinguishable
   from one nothing scanned.
11. **Fail closed** — a missing/renamed theorem, an unpinned theorem, an
   unpinned definition in a queried statement's dependency set, a non-core
   module in the environment the front does not build, an empty guarded list,
   an empty core-module allowance, an unclaimed registry field, a missing
   claims file, a driver failure or a missing `lean` binary is an error in
   every bridge (exit 2 for the last), never a skip.

Scoped assumptions of this front, stated rather than papered over. This is the
source of truth for the per-front detail; `SECURITY-ASSUMPTIONS.md` states the
repository-level consequences (SA-1, SA-2, SA-10) and points back here rather
than copying any of it.

* **Which fronts have a Lean-executing differential, precisely.** An earlier
  version of this section named the four differentials as the control for
  definition drift. Three of the four do run the compiled Lean model:
  `byte_bridge_check.py` (334 buffers through `BytesRun.lean`),
  `eval_bridge_check.py` (33 vectors through `EvalRun.lean`) and
  `wave_bridge_check.py` (582 cases through `WaveRun.lean`). The other two do
  **not** run Lean beyond the guard: `bridge_check.py`'s 861 steps drive
  `impl/sigma_glyph.py` against the SizeBound *premise* (a cross-check of the
  Python oracle, not of the Lean file), and `c1_bridge_check.py`'s 3000 λ-terms
  compare `lean_c1` — a hand-written Python transcription of the Lean source —
  against the oracle. And *no* differential can ever exercise a `Prop`-valued
  definition (`Valid`, `Wf`, `Reach`, `Step`, `Inv`), which is exactly where
  each theorem's hypotheses live. That is why definition drift is caught by the
  pins in (3), not by the differentials.
* **The genesis pins have a differential now, and only because one was added.**
  "Compiling IS the check" only says the hex in the file is the digest of
  whatever `hIT`/`hKT`/`hST` happen to be. `byte_bridge_check.py` now compares
  the five genesis/FALSE/invalid-object statements — and the atom definitions
  they are stated over — against `impl/sigma_glyph.py`, so a swap fails the
  differential even if the pins were regenerated to match.
* The `*Run.lean` runners are I/O plumbing; nothing proves a runner reports
  what the model computed rather than printing expected answers. The denylist
  removes the mechanical decoupling routes, not the need to read the file.
* Regeneration (`python3 proofs/proof_guard.py regen`) can make any drift pass
  by construction. It is never run by a bridge or by CI; the pin file is the
  claim, and its diff deserves the same reading as the theorem statements.
  `regen` refreshes only the `pins-sha256` line of `GUARD_CLAIMS.txt`; every
  identity claim there is hand-written, and a registry edit not mirrored in
  them fails.
* `GUARD_CLAIMS.txt` is a **review-visibility** control, not an authority:
  whoever can edit the registry can edit it too, and no bridge consumes it as
  authority. What it buys is that the edit is loud and NAMES what changed,
  instead of hiding inside a 30 000-line pin file — which is exactly what the
  earlier count-only version did not buy. It is not part of `spec/ANCHORS.txt`
  — adding a file to a governed release bundle is a roster action, not an
  agent's.
* **`native_decide` sources whose statements are pinned but not axiom-cone
  checked.** `WaveAlgebra.lut_range`, `lut_zero` and `am_fixed_scan` generate
  trust axioms the guarded wave theorems consume. They are named in
  `native_decide_sources`, and their statements are pinned and claimed — but
  they stay on the `unguarded` list, i.e. what they SAY is pinned while what
  they REST ON is not re-checked. Their TCB is the Lean compiler by
  construction (that is what `native_decide` means), which is why this front's
  TCB paragraph above says so.
* **The core-module allowance is trust, not verification.** Constants owned by
  `Init`/`Lean`/`Std` are unpinned; the toolchain pin (`lean-toolchain`) is
  what fixes them. The allowance is an explicit, claimed line rather than an
  implicit consequence of a per-front list, which is the whole of the
  improvement — it is not a check on core Lean.

Regression: `tests/proof_guard_test.py` asserts every vector above is
rejected — both round-1 bypasses, the vacuous/weakened/altered statements, the
string-literal blinding, the `#print axioms` override, `import Lean`,
`@[implemented_by]`, `@[extern]`, `debug.skipKernelTC`, the fake
`native_decide`-shaped axiom, the gutted and emptied inductive, the
`Prop := False` definition, the same-length string-literal swap, the
prefixed-declaration coverage escapes, the one-line
`namespace`/`section`/`end` coverage escapes (including the
`native_decide` escalation into a guarded front's own namespace), the
build-shrink scope escapes, a dependency gutted in a second module, the
binder-annotation swap, a borrowed `native_decide` trust axiom, the registry
demotion (named, and with counts preserved), the subdirectory file that no
textual layer opened (with its two by-products: the directory-local import
allowlist and the core-shadowing path), and each fail-closed path — and that
none of them fires on the real `proofs/` tree.

Toolchain: `curl …elan-init.sh | sh` (Lean pinned by `lean-toolchain`).
