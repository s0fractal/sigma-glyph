---
title: "Twenty-One Ways Past a Proof Guard: The CI Apparatus Around a Theorem Prover Is the Attack Surface"
author: "Serhii Glova (independent) --- sergey.glova@gmail.com"
# Same shape as the companion paper's defect: pandoc's default LaTeX template
# renders a list of maps by its truthiness, and printed the word "true" where
# that paper's author belonged. This one has no build.sh, so it never rendered
# and the defect was latent rather than observed -- fixed here so it stays that
# way. The structured form is kept for deposit metadata, under a key the
# template does not read.
authors:
  - name: Serhii Glova
    affiliation: independent
    email: sergey.glova@gmail.com
date: 2026-07-31
keywords:
  - proof engineering
  - continuous integration
  - software supply chain
  - Lean 4
  - adversarial review
classification: cs.SE, cs.LO
bibliography: references.bib
---

# Abstract

A machine-checked theorem in a public repository makes two claims. The first is
mathematical: a kernel accepted a proof term. The second is bureaucratic: *the
thing the kernel accepted is the thing the README says it accepted.* Proof
assistants have largely solved the first. This paper is an experience report on
the second, which in our case failed twenty-one times.

We report the complete adversarial history of a proof-integrity guard for a
Lean 4 mechanization: the CI machinery that decides which theorems to ask about,
how to ask, what counts as an answer, and which files exist at all. Over one
precursor finding, six internal hardening rounds and five external reviews drawn
from four other model families, the guard was shown to accept `sorryAx`;
modifier-prefixed `axiom` declarations; a `#print axioms` syntax override
installed *by the audited module*; a string literal that blinded the comment
stripper; `@[implemented_by]` composed with `native_decide`; vacuous theorems
(`: True := trivial`); definition gutting that leaves every pinned statement
byte-identical; same-length string-literal swaps exchanging pinned hash
constants; declarations hidden behind a one-line `namespace X … end X`; an audit
whose definition-pinning scope came from a configuration field nothing compiled
from; a review-visibility control that constrained counts rather than
identities; and a file walk that was not recursive, which let a subdirectory file
containing `axiom backdoor : False` be read by nothing while CI exited 0. Every
vector was reproduced end-to-end against a green build before it was fixed. Not
one required a bug in the Lean kernel.

We argue that these are not twenty-one unrelated defects but one shape in
twenty-one spellings: **a control whose scope is chosen by the thing it
controls.** The defense that generalizes is not a longer denylist but an
inversion — derive scope from something the audited artifact cannot edit, and
make an unpinned, unregistered or unclaimed entity a failure rather than a silent
skip. Two corollaries recur: *UNRUN is not PASS*, and *a scan that finds nothing
is indistinguishable from a scan that never ran*.

We also report what the external reviews produced, because it cuts against the
method as well as for it: across five reviews, one reproducible defect, four
confident P0 claims refuted by a single command, and the sharpest critique of the
work coming from the only reviewer that executed the suites — namely, that six
rounds of hardening against hypothetical hostile proofs were misallocated effort
in a project with zero external contributors. We do not resolve that tension in
our own favour. We also state plainly the study's central weakness: the defects,
the fixes, the reviews and this paper share an author and an operator.

---

# 1. Introduction

`lean` exits 0 on a file containing `sorry`. It is a warning, not an error. So
"CI compiled the proofs" is not "CI checked the proofs", and any repository that
publishes Lean proofs and gates on compilation is gating on nothing in
particular. The standard remedy is a script: compile, then query each headline
theorem's axiom dependencies with `#print axioms`, then fail the build if
anything unexpected appears. Most repositories that take this seriously have
written some version of that script. Ours was about forty lines.

This paper is what happened to those forty lines over eight days of adversarial
review. They became 1465 lines of Python, a 179 KB pin registry, and a 981-line
regression suite asserting 122 properties — machinery that is now 2.3 times the
size of the 1404 lines of Lean it guards. Along the way the guard was defeated
twenty-one times, in twenty-one distinct ways, each demonstrated end-to-end: not
"this check has a theoretical gap" but *here is a file, here is the green CI
output, here is the falsehood it certified.*

The object under audit is a Lean 4 mechanization of a content-addressed
combinator machine, described in a companion paper [@paperA2026]; nothing here
depends on what it proves. What matters is its shape, which is the shape of a
great many verified-artifact repositories: a handful of theorem files, no
mathlib, a pinned toolchain, a README making specific claims about which
theorems hold and what they rest on, and a CI job asserting that the README is
true.

**The claim of this paper** is that the CI job is the attack surface, and that
the literature has almost nothing to say about it. Enormous care has gone into
making kernels trustworthy — the de Bruijn criterion [@barendregt2005challenge],
independent re-checkers [@lean4checker; @lean4lean], the formalized metatheory of
Lean's type theory [@carneiro2019lean]. That work is excellent and it is
orthogonal to every failure we found. A reader of a repository does not
type-check it; they read a claim and trust a green badge. Between the kernel's
verdict and that badge sits a layer of glue that nobody reviews, and we found it
to be soft in ways that surprised us repeatedly, including four rounds after we
started paying attention.

**Contributions.**

1. **A complete, reproduced taxonomy of twenty-one bypasses** of a proof-integrity
   guard (§4), each with the exact green output it produced, and the defense that
   closed it. To our knowledge no comparable catalogue exists.
2. **A structural analysis** (§6) arguing the vectors instantiate a single
   pattern — a control whose scope is chosen by the audited artifact — with the
   inversion that defeats it, and two operational corollaries.
3. **An empirical report on adversarial review by language models** (§5): five
   external reviews across four model families, what each produced, and an
   explicit account of what N = 5 does and does not support.
4. **A candid threats-to-validity treatment** (§7) of a study whose defects,
   fixes and reviews share an author, including the critique that the whole
   effort was misdirected — which we present as an open tension rather than
   resolve.

---

# 2. Setting

## 2.1 The artifact under audit

Ten Lean 4 [@demoura2021lean4] files, 1404 lines, core Lean only with no
mathlib, on a toolchain pinned by `lean-toolchain` (v4.31.0). The proofs are organized into five
*fronts*, each with a module set, an allowed axiom set, and a list of *guarded*
theorems whose properties CI asserts. At the commit we report, 36 theorems are
guarded and 17 more are registered as deliberately unguarded helper lemmas; the
coverage walk finds exactly 53 declarations across the 10 files, so the
registration is total with no remainder.

Two features of the artifact matter for what follows. First, the fronts have
*different* trusted bases, and the repository documents the difference: one front
permits `native_decide` — which evaluates a decision procedure using the compiled
evaluator and therefore adds the Lean compiler to the trusted base, and which
mathlib disallows for exactly that reason [@mathlib2020] — for five concrete
digest computations, another for five wave-algebra facts, and the remaining
three permit none. A guard that treats all theorems alike cannot enforce that.
Second, each front is exercised by a *differential bridge*: a Python script that
runs the compiled Lean model against a reference implementation on a fixed
corpus [@mckeeman1998differential]. The bridges are where the guard runs, so
"the guard passed" and "the differential agreed" arrive in the same green line —
a coupling that will matter in §4.

## 2.2 What the guard is supposed to enforce

Informally: that every claim the repository's prose makes about its proofs is
true of the objects the kernel actually accepted. Concretely, at maturity, six
things — and the order in which they were added is the story of §4:

1. no `sorry`, `admit` or `axiom` in the proof sources;
2. each guarded theorem's transitive axiom cone lies inside its front's allowed
   set;
3. each guarded theorem's *elaborated statement* equals a recorded pin;
4. every definition that statement transitively depends on also equals a pin;
5. every declaration in the sources is either guarded or explicitly registered as
   unguarded;
6. the registry that encodes (1)–(5) is itself constrained by a human-read claims
   file.

## 2.3 Method, and what counts as a finding

Rounds were run as fresh-context adversarial sessions: a language model was given
the repository and asked to defeat the guard, with no memory of prior rounds and
no access to the reasoning behind the current design. The project's governing
rule, adopted before the data reported here and vindicated by it, is that **a
finding is a reproduction, not a sentence.** A claimed bypass counts only if the
reviewer produces the file, runs CI, and shows the green output. Symmetrically,
every fix carries a regression test confirmed *red before the fix* — a discipline
borrowed from mutation testing's insight that a test suite which cannot fail on a
seeded defect measures nothing [@demillo1978hints; @jia2011mutation].

This rule did substantial work. As §5 shows, most externally claimed defects did
not survive it.

---

# 3. Why the obvious defenses are not enough

Before the taxonomy, it is worth stating why the two natural answers do not
close the problem, since a reader's first reaction is reasonably that this is a
solved problem.

**"Use an independent checker."** `lean4checker` and `lean4lean`
[@lean4checker; @lean4lean] re-verify a compiled environment against an
independent implementation of the kernel. They are valuable and they raise
assurance about claim one. They do not address claim two at all: they will
happily certify that the environment contains a perfectly valid proof of
`True`, or of a theorem whose statement was silently changed, or of a theorem
about an inductive type from which a constructor has been deleted. Nine of our
twenty-one vectors produce environments an independent checker accepts without
complaint, because the proofs really are valid — of the wrong proposition.

**"Just read the diff."** This is the actual last line of defense, and we do not
dispute it. But it degrades predictably: three of our vectors are four-line
diffs, one is a single line, and one — the vector we consider the most instructive
in the set — produces a diff of *one insertion and one deletion* in a file whose
entire purpose is to make such changes visible. The interesting question is not
whether a sufficiently attentive reviewer would catch a given vector, but which
vectors survive a reviewer of realistic attentiveness, and what a tool can do to
shrink that set.

---

# 4. The taxonomy

We present the vectors in the order they were found, because the ordering is
itself the finding: each round's fix created the surface the next round attacked.
Commit hashes are given so each can be read against the diff that closed it.

## 4.1 Precursor: the file CI never checked

At commit `c537f78` one proof file was reachable in CI only through
`lean proofs/SizeBound.lean`, with no guard at all — making it the one file a
`sorry` would have passed straight through. This is the null case, and it is
worth stating because it is where most repositories are.

## 4.2 Round 1 (`2490b37`): the regex layer

The guard was a textual check: reject `\b(sorry|admit)\b` and a line-leading
`axiom`.

**V1 — `sorryAx`.** `theorem memory_bound … := sorryAx _ true`. The word boundary
in `\bsorry\b` does not match `sorryAx`, because `A` is a word character.
`sorryAx` is what `sorry` *elaborates to*: the desugared form defeated a check
aimed at the sugar.

**V2 — modifier-prefixed axiom.** `private axiom oops : False`, with
`memory_bound := oops.elim`. The `^\s*axiom` anchor is defeated by any modifier
or attribute.

*Defense.* Match `sorry`/`admit` as substrings — deliberately without word
boundaries — and `axiom` as an unanchored keyword. More importantly, demote text
to a secondary layer and add a semantic one: query each theorem's transitive
axiom cone and require it inside the front's allowed set. The round-1 write-up
then claimed this "closes any unsoundness route however spelled". We quote that
sentence because round 2 refuted it with four vectors, and because writing it was
the actual mistake.

## 4.3 Round 2 (`ddefce1`): statement, stripper, and query

**V3 — the vacuous theorem.** Replace the *statement*:
`theorem memory_bound : True := trivial`. The axiom cone is clean — `trivial`
needs no axioms — so the guard printed "OK `#print axioms` clean (std axioms
only)" and the bridge printed `PREMISE HOLDS ON ALL OBSERVED STEPS`, exit 0. **An
axiom check verifies how something was proven, never what.** The same hole admits
a weakened hypothesis or an altered conclusion. Worse, the guard's own "clean"
fixture was `theorem memory_bound : (1 : Nat) = 1 := rfl`, asserted as ACCEPTED:
the regression suite had enshrined the hole.

**V4 — comment-stripper blinding.** `def blind : String := "/-"`. The stripper
was not literal-aware, read `"/-"` as opening a block comment, and dropped the
rest of the file — including a bare `axiom oops : False` placed after it. The
textual layer reported no problems on a file whose visible content was an axiom
of `False`.

**V5 — `#print axioms` override by the audited module.** The axiom query wrote a
`.lean` file that `import`ed the audited module and ran `#print axioms`.
Elaboration therefore happened in an environment the audited module controls.
With `import Lean`, a `@[command_elab]` handler replacing the `#print axioms`
syntax, the model deleted, `axiom oops : False`, and `memory_bound := oops.elim`:
`lean` exited 0, the guard reported "clean", the bridge printed `PREMISE HOLDS`,
exit 0. **The audited artifact was answering the audit's questions.**

**V6 — `@[implemented_by]` with `native_decide`.** For any theorem permitted
`native_decide`, `@[implemented_by]` replaces the compiled code whose results the
kernel is trusting, so arbitrary falsehoods become provable. The reviewer rewrote
a genesis-hash theorem to assert a different digest; the guard reported "axioms
clean for 12 byte-level theorems" and the bridge printed
`BYTE-BRIDGE: ALL AGREE (334/334)`.

Three structural weaknesses arrived with them: a hand-written
`axiom pin._native.native_decide.ax_1_1 : False` mimics the *shape* the allowlist
accepts; coverage was a hardcoded theorem list, so a new poisoned theorem in an
already-guarded file was never queried; and two pinned test vectors were
anonymous `example`s — an anonymous declaration has no name, so no query can
reach it, and a falsified pin passed.

*Defenses.* (i) **Statement pins**: the canonical dump of each guarded theorem's
elaborated type must equal a recorded pin, drift being a hard failure with a
diff. The dump is structural — binder names and `mdata` dropped, constants by
full name, never pretty-printed — so notation cannot make the displayed statement
differ from the elaborated one. This is a Pollack-consistency concern
[@wiedijk2012pollack] moved from the prover's pretty-printer into CI.
(ii) A **literal-aware stripper** in which a literal or comment still open at EOF
is a failure, on the grounds that our lexer and Lean's then disagree about the
file. (iii) A **data-only environment query**: load the audited module's `.olean`
through `Lean.Environment.importModules` and walk the kernel environment, so the
audited module is data, never elaborated code, and cannot install syntax.
(iv) Import and attribute allowlists plus a metaprogramming denylist
(`implemented_by`, `extern`, `csimp`, `initialize`, `run_cmd`, `elab`, `macro`,
`syntax`, `notation`, `unsafe`, `opaque`, `attribute`, `#`-commands, and any
non-`linter.*` `set_option` — which is where `debug.skipKernelTC` lives).
(v) A **coverage registry** rejecting anonymous `example`s outright.

## 4.4 Round 3 (`577f411`, `1ff139d`): the definitions and the registry

Round 3's two findings share a form: *the pinned thing is not the thing that
matters.*

**V7 — definition gutting.** Pinning a statement does not stop the definitions it
is *about* from being hollowed out beneath it. Deleting one constructor from an
inductive reachability relation — a four-line diff — shrinks a memory-bound
theorem to a claim about a single state. Emptying the relation makes it a theorem
about nothing. `def Valid (_w : Wave) : Prop := False` makes three separate
theorems simultaneously vacuous. In every case **every pinned statement dump
stayed byte-identical** and every bridge stayed green, including
`WAVE-BRIDGE: ALL AGREE (582/582)`.

**V8 — lossy string-literal pins.** The structural dump rendered a string literal
as `(strLit 64)` — "some 64-character string" — so the *contents* of every pinned
hex constant were unprotected. Swapping two atom definitions and the two
corresponding pinned digests left every theorem true, every pin matching, and the
bridge green, with the test vector for `I` asserting `K`'s hash.

**V9 — same-line declaration prefixes.** The scanner matched keywords only at the
start of a stripped line, so `open Nat in theorem hidden : …` and
`set_option linter.unusedVariables false in theorem hidden2 : …` were invisible
to the coverage registry.

**V10 — the registry authorized itself.** Nothing hashed or cross-checked the pin
file. Moving a theorem from a front's `guarded` list to `unguarded` — with an
entirely plausible reason — and replacing it with `: True := trivial` passed
every bridge: the pin and the axiom cone were simply never consulted for it. The
only tell was "5 wave theorems" instead of 6, inside a log line no gate greps.

**V11 — unaudited files and core-shadowing modules.** A new `proofs/Helper.lean`
carrying `axiom oops : False` was scanned by nobody, because each front scanned
only its own file set. And a front whose module list named `Init` or `Lean` would
poison the guard driver's own `LEAN_PATH`.

*Defenses.* **Definition pins over a kernel-computed dependency set**: for each
guarded statement, collect the constants in its type, then transitively through
the types *and values* of the definitions those mention; pin every member — a
definition by type and value, an inductive by type and constructor list including
the constructors' own types. Dumps too long to read in a diff are pinned by
SHA-256 of the same dump. An unpinned dependency is a hard failure, so a *new*
dependency cannot appear silently. String literals are dumped by content, as hex
of their UTF-8 bytes. Declaration keywords are matched as tokens wherever a
command can start. The registry becomes a gated claim in a separate
`GUARD_CLAIMS.txt`. And the pinned digests gain a cross-check against an
independent oracle implementation, so V8 now fails a differential even if the
pins were regenerated to match.

## 4.5 Round 4 (`c760f57`): commands are not lines

Round 3's fix matched keywords as tokens — but line by line, `continue`ing on any
line matching `namespace\s+\S+`, `section\b` or `end\b`. **Lean separates commands
by whitespace, not newlines.**

**V12 — one-line scopes.** All three were invisible to the coverage walk:

```lean
namespace Zzz theorem hidden_by_ns : True := trivial end Zzz
-- … end Sec1 theorem hidden_by_end : True := trivial
namespace Zzz2 example : True := trivial end Zzz2
```

The third also defeats round 2's "anonymous examples are rejected" claim.
Appended to a real proof file, the first returned coverage `[]` and
`WAVE-BRIDGE: ALL AGREE (582/582)`, rc 0. A side effect: `namespace X … end X` on
one line pushed the scope stack without popping it, so the *next* declaration
acquired a doubled prefix (`WaveAlgebra.WaveAlgebra.fold_not_associative`) — a
name no query would ever match.

**V13 — an unqueried `native_decide` inside a guarded front.** The escalation
appended, to the one front documented as having no compiler in its trusted base:

```lean
namespace Book1.C1 theorem sneaky_native : (2:Nat)^10 = 1024 := by native_decide end Book1.C1
```

The bridge printed `C1-BRIDGE: ALL AGREE`, rc 0, *while printing* "axiom cones
are exactly within [propext]" — a theorem carrying a compiler trust axiom, inside
the guarded front's own namespace, with the front's documented invariant
contradicted in the front's own output.

*Defense.* Walk **commands, not lines**: scan the stripped, literal-blanked body
once for `namespace|section|end|theorem|lemma|example` as tokens and carry the
scope stack across the whole file. A scope keyword takes its argument on the same
line only; a declaration keyword may take its name across a newline; no command
keyword can be another's argument.

## 4.6 Round 5 (`bfff9e4`): the audit chose its own scope

This is the round that generalizes furthest, and the reason §6 exists.

**V14 — the definition-pin scope came from a field nothing compiled from.** The
guard passed `audit = front["build"] or front["modules"]` to the driver, whose
`isAudited` predicate **silently dropped** every constant owned by a module
outside that set: no pin required, no message. Nothing actually compiled from
`build` — each bridge hardcoded its own module tuple — and the registry check only
ever verified `build ⊆ audited-sources`, never the converse. So deleting one
module name from a configuration field disabled the entire definition-pinning
control for a front, restoring two already-closed P1s:

| Mutation | Result |
|---|---|
| wave `build: [LutData, WaveAlgebra] → [LutData]` + `Valid := False` | `WAVE-BRIDGE: ALL AGREE (582/582)`, rc 0, *while printing* "every definition they are stated in terms of matches its pin" |
| size `build → [LutData]` + inductive loses a constructor | `BRIDGE: PREMISE HOLDS`, rc 0, printing "Step/Reach/Acc … match theirs" |
| bytes `build → [MachineBytes]` | pinned dependencies fall 31 → 19, all twelve SHA-256 pins silently gone, `BYTE-BRIDGE: ALL AGREE (334/334)` |

**V15 — the claims file constrained counts, not identities.** Round 3's
`GUARD_CLAIMS.txt` recorded *how many* theorems each front guards. Hiding a
theorem via V12, replacing it with `: True := trivial`, dropping it from
`guarded`, and registering a fresh trivial `placeholder_bound` kept every count
equal. After regeneration the bridge was green and
`git diff --stat GUARD_CLAIMS.txt` showed **one insertion, one deletion** — the
content-hash line that regeneration rewrites on every run. *Zero review signal,
from the control whose entire purpose was review signal.*

**V16 — binder information was not dumped.** `BinderInfo` and `levelParams` were
omitted, so `(a b : Nat) (h : a ≤ b)` and `{a b : Nat} ⦃h : a ≤ b⦄` dumped
byte-identically. Logically the same proposition, so not a soundness hole — but
the documentation said the canonical dump equals the pin, and it did not.

**V17 — trust axioms accepted on shape alone.** The `native_decide` allowlist
matched the axiom's name *pattern*, so a trust axiom generated by any declaration
was accepted for any theorem permitted to have one. The obvious tightening —
require the generator to be the theorem itself — would have been wrong, because
legitimate theorems consume trust axioms generated by helper lemmas.

*Defenses.* **Scope is derived, not configured**: the driver takes an explicit
core-Lean allowance (a fixed, separately claimed list) and puts *everything else*
in scope, walking the kernel environment; an unpinned dependency fails whoever
owns it, and scope cannot shrink by editing a per-front list. `build` becomes the
single place a front's module set is written, and every bridge calls one function
to build it, so the guard queries exactly what the bridge built. The registry
gains the missing direction: every strict source must be a built module, every
queried module must be a built module, no built module may be registered as a
runner. Re-running the three reproductions *with the claims file fully
regenerated to match* — handing the attacker an updated claims file — all three
now fail at the source layer. `GUARD_CLAIMS.txt` claims **identities**, one
theorem per line, across every field the guard's behaviour depends on, and an
unclaimed field is itself a failure. Binder info is dumped. And the *generators*
of trust axioms become an explicit, identity-claimed list, each one queried and
statement-pinned like a guarded theorem — so a trust axiom's meaning is pinned
even where its cone is not re-checked. This is why the registry pins 39
statements while 36 theorems are guarded.

## 4.7 External finding (`a4e7de1`, `5e75e9b`): the walk that was not a walk

The artifact was then given to reviewers from three model families other than the
one that had written it. One finding survived.

**V18 — the file walk was not recursive.** Three separate checks each enumerated
`os.listdir(proofs_dir)` and dropped anything that was not a `.lean` in that *one*
directory — while the documentation claimed every theorem in the proof sources is
guarded or registered, and every `.lean` is audited by some front. Both claims
were false for any path containing a `/`. Reproduced on the real tree:
`proofs/Sub/Evil.lean` containing `axiom backdoor : False` produced zero problems
from every textual layer, and the bridge printed
`PREMISE HOLDS ON ALL OBSERVED STEPS` and exited 0.

Chasing it surfaced two holes the reviewer had not named, the first of which the
project's own write-up calls the most dangerous bypass of the entire series:

**V19 — the import allowlist was built from the audited file's own directory
listing.** A decoy `proofs/Sub/Lean.lean` therefore made `import Lean` legal for
its neighbours — **reopening by filesystem path the exact route (V5) by which an
audited module once overrode the guard's own axiom query**, four rounds after V5
was closed.

**V20 — the core-shadowing check never saw the module a file's path implies**, so
`proofs/Lean/Foo.lean` was unreachable to it.

**V21 — usage exited 0.** Invoking the guard module with no arguments printed its
docstring and exited 0, so `python3 proofs/proof_guard.py && echo guarded`
printed `guarded`. Every check the module implements runs from the bridges, so
that exit status asserted a check that had not run.

*Defenses.* One recursive enumeration feeds every source-layer check, so a future
check inherits the walk instead of repeating the bug; a source's module name is
derived from its path, and that identity is used by the registry, the import
allowlist, the core-shadow check and the build alike. A `.lean` at any depth must
be registered by its path or it is a hard failure. Two weaker alternatives were
considered and rejected in writing: "auditable but unbuilt" — because a second,
weaker tier is exactly where an unsound axiom would legally live — and "scan it
but do not require registration", because *a scan that finds nothing is
indistinguishable from a scan that never ran; only refusal is observable*. Usage
now exits 2.

## 4.8 The same shape outside the guard

Two further defects, found by a different external reviewer with reproductions,
sit outside the proof guard and inside the same family. We include them because
they show the pattern is not an artifact of Lean.

**A signed record naming a runtime that did not run.** A sibling tool executed a
validation check via `shell=True` on the host while recording a runtime tag that
the governing specification defines as *execution in an isolated container* — a
signed record promising an execution profile that had not occurred. In the
reproduction the check also created a file in the observed workspace *after* the
post-state snapshot was taken, so the signed decision reported zero effects while
the workspace had changed. The reviewer noted correctly that this is not a
shell-injection defect: the check is user-supplied, and the defect is in
provenance semantics. The fix registered an honest tag and closed the observation
window — and discovered that the project's own demo documented a check that
writes `__pycache__` into the observed workspace. *The first real instance of the
defect was living in its own documentation.*

**A compiler emitting artifacts its own verifier rejects.** A policy frontend
accepted any integer for a budget flag; negative values produced terms the
verifier fails, and values above $2^{32}-1$ produced blobs the verifier rejects
outright. The frontend's contract is to refuse what it cannot compile; instead
the refusal happened in someone else's verifier. The existing round-trip check
validated the *term* but not the field of the blob actually written — *a check
that measures something adjacent to the thing being proved.*

**And one found the day this paper was written.** A release gate greps its
verifier's output for `AUTHORIZED` to decide whether the specification anchor set
in force has been adopted. `grep -q "AUTHORIZED"` matches `NOT AUTHORIZED`. The
gate passed on a store containing no adoption warrant at all, and failed only
because `pipefail` happened to catch an exit status; removing that line greens an
unauthorized set silently. It was found not by review but by an agent preparing
the next release, which noticed the shared gate would not have caught *its own*
not-yet-adopted state. The negative control was run rather than argued: with the
adoption warrant deleted, the old form passes and the new form fails.

---

# 5. What the external reviews produced

Five external reviews were run across four model families other than the one that
wrote the artifact and the guard. We report the outcome in full, including the
parts unflattering to the method.

| Reviewer | Executed the suites? | Confirmed defects | Claims refuted |
|---|---|---|---|
| deepseek-v3.2 | no | 0 | 3 P0 + 1 P1 (three refutable by a single `grep`) |
| gemini-3.1-flash-lite | no | 0 | 2 |
| Antigravity (agentic) | **yes** | 0 | — |
| glm-4.7 | no | **1** (V18) | 1 P0 (refuted empirically) |
| Codex | **yes** | **2 P1 + 2 P2** (§4.8) | — |

**The one guard defect came from a reviewer that could not run anything.**
glm-4.7 read the code and observed that the file walk was not recursive. Six
internal rounds had not seen it — not because it was deep, but because every
internal attack silently assumed the proof files were where they currently are.
The finding cost under one cent of inference. This is the strongest argument for
cross-family review we have, and it is ours rather than borrowed: a reviewer who
does not share your unexamined assumptions can see past them, and the assumptions
you cannot see are precisely the ones your own adversarial rounds will not
attack. The mechanism is visible in the finding itself, which is what makes it
more than an anecdote — the vector is not cleverer than the ones we found
internally, it is *shallower*, and its shallowness is the point.

**Three of five produced confident P0 claims that a single command refutes.** One
asserted that `opaque` was absent from the metaprogramming denylist; it is on a
line in the file the reviewer was given. One asserted a signature-verification
defect which, had it been real, could not have survived the 270 347 differential
cases already in the suite — a 50% failure rate does not hide. In two cases the
reviewer's own visible reasoning shows it was working from a truncated copy of
the file it was judging; in one of those the truncation was the operator's
packaging error rather than the model's, which is itself a finding about how to
run these reviews. The project rule that a finding is a reproduction was adopted
before this data. Without it we would have spent the day "fixing" a non-existent
defect in a cryptographic blocklist, and plausibly broken something real in the
process — the cost of a false positive in this setting is not zero, it is a
change to working security code.

**Execution correlates with not filing false positives.** The two reviewers that
ran the suites filed zero refuted claims between them; the three that only read
filed six. We note the correlation and decline to make it a law: with five data
points it is equally consistent with the agentic tools simply being more capable
overall. What we can say without inference is procedural — the reviewers that
could execute produced findings we could act on immediately, and the reviewers
that could not produced claims that cost us triage time roughly proportional to
their confidence.

**The only reviewer that executed and found nothing attacked the premise
instead.** Its critique — that six rounds of guard hardening were the streetlight
fallacy in a project with zero external contributors — is treated in §7.2. We
consider it the most valuable single output of the external round, which is an
uncomfortable thing for a paper about the bypasses to have to report, and we
report it in the same section as the successes rather than quarantining it in a
limitations paragraph.

**What N = 5 supports, and what it does not.** It supports an existence claim:
cross-family review found a real, reproduced defect that same-family adversarial
review had missed six consecutive times, and the causal mechanism — an assumption
shared by the artifact and its attackers — is legible in the finding. It supports
a cost observation: the marginal cost of an additional reviewer family was
negligible relative to the cost of one internal round, by roughly three orders of
magnitude in wall-clock and inference spend. It does **not** support any rate. One
confirmed defect in five reviews is not a yield estimate: the reviews were not
independently sampled, the prompts differed between them, two reviewers received
truncated inputs through operator error, the artifact changed between reviews,
and "model family" is not a controlled variable when training corpora overlap
substantially. It does not support the stronger claim that cross-family review
outperforms same-family review in general — same-family rounds found seventeen
vectors and cross-family found one, and on raw count the internal rounds win
decisively. The defensible statement is narrower and still worth acting on:
**the two methods find different things, and the cross-family finding lay in a
blind spot that repeated same-family effort was structurally unable to reach.**
A project that can afford only one should not read this table as a reason to drop
the internal rounds; a project already doing internal rounds should read it as a
reason to add one cheap external pass, and to require a reproduction from it.

# 6. Analysis: one shape, twenty-one spellings

The vectors are not a list of unrelated bugs. Read in sequence, they instantiate
a single pattern:

> **A control whose scope is chosen by the thing it controls.**

- The **axiom cone** is chosen by the theorem's own proof (V3): prove `True` and
  the cone is trivially clean.
- The **axiom answer** is chosen by the audited module (V5): install syntax and
  the audit asks its question of the defendant. This is Thompson's observation
  [@thompson1984trust] relocated from compilers to audits — if your integrity
  check runs code in an environment the audited artifact defines, the artifact
  can answer for itself. That V19 reopened this route *by filesystem path*, four
  rounds after V5 was closed, is why we present the vectors as a taxonomy rather
  than a list.
- The **stripper's view of the file** is chosen by a string literal inside the
  file (V4).
- The **set of declarations** is chosen by their own line breaks (V9, V12).
- The **set of pinned definitions** is chosen by a configuration field the same
  commit edits (V14).
- The **review signal** is chosen by a count whose editor also controls the
  numerator (V15).
- The **trust-axiom allowlist** is satisfied by an axiom's shape, which the
  audited file writes (V17, and the forged-shape weakness of round 2).
- The **set of files** is chosen by which directory the files sit in (V18).
- The **import allowlist** is chosen by a decoy file's own neighbours (V19).
- Outside the guard: the **runtime profile** is chosen by the record that claims
  it (§4.8), and the **adoption verdict** is chosen by a substring of the word
  that denies it (§4.8).

Stated this way, the defense is not a longer denylist. It is an inversion:
**derive the scope from something the audited artifact cannot edit, and make
absence a failure rather than a skip.** Concretely, in our final design, that
means (a) the audit scope is the *complement* of a small, separately declared
allowance rather than an enumerated inclusion list; (b) the answer comes from the
compiled environment loaded as data, never from elaborating code the artifact can
influence; (c) enumeration of files happens once, recursively, in a function
every check calls, so a future check inherits the walk rather than reimplementing
the bug; (d) an entity that is unpinned, unregistered or unclaimed is a hard
failure; and (e) the human-read claims file states *identities*, not counts, so
that any change to what is guarded is a diff line naming a theorem.

This is the least-privilege and complete-mediation discipline
[@saltzer1975protection] applied to an audit rather than to a reference monitor,
and the failure mode is the familiar one: mediation that is incomplete because
the mediator's notion of "everything" was supplied by the subject.

Two operational corollaries recur often enough to be worth stating as rules:

**UNRUN is not PASS.** V21 is the pure case — a module printing usage and exiting
0 — but the pattern appears throughout: the harness that printed `ALL GREEN` and
exited 0 after skipping surfaces it could not check; the bridge that printed "ALL
AGREE" with the Lean half never run because `lean` was absent; the gate whose
grep matched the negation of its own predicate. A check that cannot run must be
louder than a check that failed, because a failure gets investigated and a skip
gets shipped.

**A scan that finds nothing is indistinguishable from a scan that never ran.**
This is why the design refuses unregistered files rather than merely scanning
them. Silence is not evidence; only refusal is observable. It is also why the
regression suite asserts, for every one of the twenty-one vectors, both that the
guard rejects the vector *and* that the guard does not fire on the genuine
sources — a positive and a negative control for each, which is the discipline
mutation testing formalizes [@demillo1978hints; @jia2011mutation] and which
coverage metrics alone do not provide [@ivankovic2019coverage].

Finally, the asymmetry that motivated this paper. Every vector type-checked. Not
one required a kernel bug, and not one is a claim about Lean; the kernel and its
axiom accounting behaved correctly throughout. Substantial community effort has
gone into trustworthy kernels — independent re-checkers, formalized metatheory,
the de Bruijn criterion [@lean4checker; @lean4lean; @carneiro2019lean;
@barendregt2005challenge] — and almost none into trustworthy *audits* of what
those kernels accepted. A reader of a repository depends on the latter. Supply
chain frameworks [@torresarias2019intoto; @slsa; @sigstore] attest that a build
happened as claimed, which is orthogonal: all twenty-one of our vectors are
faithfully built, correctly attested artifacts that certify a falsehood about
themselves.

---

# 7. Threats to validity

## 7.1 The study and its subject share an author

This is the central weakness and it deserves the plainest possible statement. The
proofs, the defects, the guard, the fixes, the regression suite, the prompts that
elicited the adversarial reviews, and this paper were produced by the same
operator working with language models — in most cases models of the same family
that wrote the code being attacked. A paper arguing that self-authorized controls
fail is itself a self-authorized control. The reader should weigh it accordingly,
and we would rather say so here than in a closing disclaimer.

Three partial mitigations, none sufficient. Every vector is a reproduction with
its command output preserved in a commit message, so the *existence* claims are
checkable by anyone with the repository and a Lean toolchain, independent of who
wrote them. Every fix carries a regression test asserted red before the fix, so
the *closure* claims are falsifiable the same way. And the external reviews of §5
were run by models from other families — though still prompted by the same
operator with the same framing, which is precisely why the project declines to
call them an independent gate. No independent adversarial gate has run against
any of this work, and none of the guard commits carries the project's own
governance adoption.

A specific consequence: the round-to-round narrative may be flattered by
selection. We report the vectors that were found. We cannot report the vectors
that six rounds of the same family were structurally unable to see — and V18,
which was exactly such a vector and needed an outsider, is direct evidence that
the unreported set is non-empty.

## 7.2 The work may have been misallocated

The agentic external reviewer, the only one that executed the suites, found no
bypass and instead argued that the entire effort was the streetlight fallacy.
Hardening a guard against adversarial Lean proofs is defence against hostile
third-party contributions, and this project has had zero external contributors.
Six rounds were therefore spent defending against hypothetical pull requests from
oneself, while the friction a first real user would meet — policies authored by
hand in SKI combinators — went unaddressed. The critique is sharp and we think it
is largely correct.

We decline to resolve the tension in our own favour, because both sides hold.
Against the work: the effort was chosen because it was legible and tractable, not
because a threat model demanded it; the guard is now 2.3× the size of the proofs
it protects, up from 1.8× before the final three rounds, and that ratio is a cost
someone pays in review attention forever. For the work: the taxonomy transfers to
projects that *do* accept external proofs, and its value does not depend on this
project having users; V14 and V18 are defects of *claimed coverage*, which would
have silently falsified the repository's README for any reader, contributors or
none; and the same shape kept appearing outside the guard, in a signed provenance
record and in a release gate (§4.8), where the threat model is not hypothetical.
The honest summary is that the *findings* generalize better than the *effort
allocation* did.

## 7.3 Construct and external validity

The guard's maturity is measured by the vectors it now rejects, which is
circular: the suite was built from the vectors we found. We have no estimate of
the residual, and the round-4 and round-5 vectors are evidence that our estimate
would have been wrong at every prior point. The vectors are also Lean-specific in
their spelling — `sorryAx`, `native_decide`, `@[implemented_by]` — though §6
argues the shapes are not. Whether the same taxonomy holds for Coq, Isabelle or
Agda repositories is untested, and we make no claim about it; the mechanism (an
audit script deciding what to ask a prover) is common to all of them, but the
specific escape hatches are not.

Finally, single-artifact experience reports do not support frequency claims. We
report what happened to one guard over eight days, and the value we claim for it
is the catalogue and the structural argument, not a base rate.

---

# 8. Related work

**Trustworthiness of the checker.** The de Bruijn criterion — that a proof
assistant should emit certificates checkable by a small independent kernel
[@barendregt2005challenge] — is realized for Lean 4 by `lean4checker` and
`lean4lean` [@lean4checker; @lean4lean], resting on formalized metatheory
[@carneiro2019lean]. Pollack-inconsistency [@wiedijk2012pollack] asks whether
what a system *displays* faithfully denotes what it *means*; our statement pins
are that concern relocated from a pretty-printer to a JSON file whose reader is
CI, and V8 (`(strLit 64)`) is a textbook instance. All of this work concerns
claim one. We are not aware of prior work cataloguing attacks on the CI
apparatus that asserts claim two, which is the gap this paper addresses.

**Proof engineering.** Surveys of engineering large verified systems
[@ringer2019qed] and the experience of seL4 and CompCert
[@klein2009sel4; @leroy2009compcert] treat proof maintenance, refactoring and
proof-to-code correspondence at scale. The concerns are adjacent — how a proof
artifact stays true as it evolves — but the failure mode studied there is honest
drift, not an adversary editing the audit's own scope.

**Software supply chain.** in-toto [@torresarias2019intoto], SLSA [@slsa] and
Sigstore [@sigstore] establish that an artifact was built by the expected process
from the expected inputs; empirical catalogues of package-ecosystem attacks
[@ohm2020backstabber] motivate them. These are complementary and orthogonal:
every vector here yields a faithfully built, correctly attested artifact whose
*content* certifies something false about itself. Provenance answers "did this
come from where it says"; it does not answer "does the badge mean what it says".

**Testing methodology.** Differential testing [@mckeeman1998differential;
@yang2011csmith] is the empirical control tying our Lean model to a reference
implementation, and §4 shows its limit: no differential can exercise a
`Prop`-valued definition, which is exactly where each theorem's hypotheses live,
so V7 was invisible to every bridge. Mutation testing
[@demillo1978hints; @jia2011mutation] is the closest methodological relative of
what the adversarial rounds actually did — seed a defect, check the suite goes
red — and our red-before-fix rule is that discipline applied by hand to a
security control rather than to a program.

**Language models as authors and reviewers.** Evaluations of code-generating
models [@chen2021codex] and studies of the security of their output
[@pearce2022asleep; @perry2023users] establish that model-written code carries
characteristic defects. Our data is a small point in the adjacent space of
model-written *review*: five reviews, one reproducible finding, four confident
false positives, and a strong correlation between "could execute the suite" and
"did not file a false positive". We are not aware of a systematic study of
cross-family model review as a QA method, and we do not claim to provide one.

---

# 9. Conclusion

A guard whose entire job was "no `sorry` reaches CI" was defeated twenty-one
ways. It was defeated by the desugared spelling of the token it looked for; by a
string literal that blinded its lexer; by the audited module answering the
audit's own question; by theorems whose statements had been replaced with `True`;
by definitions hollowed out beneath statements that still matched their pins
byte-for-byte; by a one-line `namespace X … end X`; by a scope taken from a
configuration field nothing compiled from; by a review control that counted
instead of naming; and — six adversarial rounds in, by an outsider, in minutes —
by the plain fact that its file walk never entered a subdirectory. Every one was
a green build certifying a falsehood. Not one was a bug in Lean.

The narrow lesson is that a machine-checked proof in a repository is two claims,
that proof assistants have solved the first, and that the second is currently
defended by scripts nobody reviews. The broader one is that the failures share a
shape — *a control whose scope is chosen by the thing it controls* — and that
naming the shape is more useful than extending any denylist, because the shape
kept reappearing in new spellings, in a provenance record and in a release gate,
after we had named it.

We are aware of the recursion. This paper is a self-authored control arguing that
self-authored controls fail, its defects and its fixes share a family, and its
reviewers share an operator. The one finding that mattered most came from a
reviewer that did not share our assumptions and could not run our code, and cost
less than a cent. That is the recommendation we would actually make to another
project: whatever you have hardened six times, hand to someone whose blind spots
are not yours, and require a reproduction rather than an opinion from both of
you.

---

# 10. Artifact availability

Everything reported here is in one public repository:

> **https://github.com/s0fractal/sigma-glyph** [@sigmaglyph2026]
> commit `8d6b8234959a97be564a0301ca0b3d130c8c8c2f`, `master`

MIT for the implementation, CC-BY-4.0 for the specification texts. All figures
were measured at `35d8aea`, three commits earlier; `proofs/` and
`tests/proof_guard_test.py` are byte-identical between the two, which we verified
with `git diff`.

**The guard and its regression suite** are `proofs/proof_guard.py` (1465 lines),
`proofs/theorem_pins.json` (179 KB; 44 statement pins, 156 definition pins),
`proofs/GUARD_CLAIMS.txt`, and `tests/proof_guard_test.py` (981 lines). Every
vector in §4 is a fixture in the last of these. Each round's commit message
contains the reproduction and its verbatim green output; the hashes are given in
the §4 headings.

**Reproducing the guard and the vectors** requires Python 3.10+ and `elan` for
the pinned toolchain (`leanprover/lean4:v4.31.0`, from `proofs/lean-toolchain`).
No mathlib and no network.

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
git checkout 8d6b8234959a97be564a0301ca0b3d130c8c8c2f
python3 tests/proof_guard_test.py     # PROOF-GUARD: ALL PASS (122 checks)
```

We measured 122 checks and 0 failures in 38.9 s on an Apple-silicon macOS host
(arm64-darwin 24.6.0). Run it on a clean tree: several vectors write and then
remove real files under `proofs/`, including a subdirectory, as part of testing
the unaudited-file and non-recursive-walk cases. The five differential bridges,
each of which runs the guard before anything else and fails closed if `lean` is
absent, complete in 42.3 s cold:

```bash
for b in bridge byte_bridge eval_bridge wave_bridge c1_bridge; do
  python3 proofs/${b}_check.py; done
```

The mechanization these guard is described in the companion paper
[@paperA2026]. The stack's three Python packages are published on PyPI
(`sigma-glyph` 0.6.7, `warrant-verify` 0.6.0, `oaip` 0.3.0, all uploaded
2026-07-31 via OIDC Trusted Publishing, which we verified against the PyPI JSON
API); they are not needed to reproduce anything in this paper, for which the
repository checkout is the artifact.

---

# Acknowledgements

The adversarial rounds of §4 were conducted by fresh-context language-model
sessions prompted by the author; the external reviews of §5 were run against
models from other families through OpenRouter, at a total inference cost of under
one cent. Neither process constitutes an independent audit, and §7 says so at
length. The critique recorded in §7.2 is the reviewer's, reproduced because it is
the sharpest thing anyone said about this work.
