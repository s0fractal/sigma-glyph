# Security assumptions and non-goals

**Status: informative, not adopted.** Where this file and Book I disagree, Book I
is normative and this file is the defect.

## What this document is

What Σ-GLYPH assumes of its environment, and what it deliberately does not do.
This is where those statements live: `llms.txt` and `SECURITY.md` point here
instead of carrying their own copies, so the same item is not maintained in three
places and cannot drift between them.

Scope of that claim, stated because "a document claims closure where the fix only
narrowed" is a recurring defect class in this stack and `llms.txt` has been
caught at it four times: this file covers the residuals those two files used to
list, plus the repository-level statement of the proof-chain assumptions. It is
**not** a claim that every limit of Σ-GLYPH is enumerated here. `proofs/README.md`
remains the source of truth for per-front proof detail and is deliberately not
copied; Book I states limits inline where they are normative; the retirement
ledgers in `history/` hold findings never promoted to either. A limit stated somewhere else and absent here
is a defect in this file.

Read it the way a standards reader reads a security-considerations section. Every
item is one of two things:

- a **scoped assumption** (`SA-n`) — a condition the guarantees require and that
  Σ-GLYPH does not itself establish. Stating it is what makes the guarantee
  precise; omitting it would make the guarantee false.
- an **explicit non-goal** (`NG-n`) — a property deliberately not provided, with
  the reason it is out of scope rather than merely absent.

Together they draw the boundary of the threat model. Inside it, a failure is a
**defect** and is in scope for a report. An item stated below is **not** a
defect — but a demonstration that reality is *worse than the item states* is, and
is the most valuable report this project receives. Several of these exist
because a reviewer did exactly that.

## What Σ-GLYPH claims

One sentence, because everything below bounds it:

> Given the same term hash, uint32 budget and valid partial content store, two
> conforming implementations compute the same result term and reported spend —
> integer-only and total, with no float, clock or network in reduction. ATP
> bounds priced work and peak **semantic materialized-node count**. It does not
> bound process memory, and the verifier must apply a local admission policy.
>
> sigma-resume adds: the same computation run in budgeted segments and resumed
> from checkpoints reaches the same kernel outcome as one straight run, and a
> receipt is verified by replaying it from the verifier's own root.

## Scoped assumptions

**Retired 2026-10-31** with Books II and III, GOV-anchors, the Warrant 0.x apparatus and LORE (history/RETIREMENT-2026-10-ECHO.md): SA-3, SA-4, SA-5, SA-5b, SA-7, NG-1, NG-2, NG-3, NG-4, NG-7. Their text is at commit `96414ab`; the identifiers are not reused.


### SA-1. Part of the Lean chain assumes the compiler, not only the kernel

`native_decide` is in the trusted base for part of the mechanized chain, so those
theorems trust the Lean **compiler** as well as the kernel. `C1Compiler.lean`
does not use it.

The assumption is discharged nowhere and cannot be: that is what `native_decide`
means. The five theorems that use it are the `MachineBytes` genesis and
invalid-object pins; `proofs/README.md` names them per front. Their statements
are pinned and their axiom cones guarded; what the cones rest on is the
compiler.

### SA-2. Most proof fronts reach CI through differential bridges, not kernel checks

CI checks `SizeBound.lean` directly; the rest of the proofs reach CI through the
differential bridges rather than as kernel checks of their own.

What a bridge can and cannot establish is enumerated in `proofs/README.md`, and
that enumeration is the source of truth for it — three of the four differentials
run the compiled Lean model, two do not run Lean beyond the guard, and no
differential can exercise a `Prop`-valued definition, which is exactly where each
theorem's hypotheses live. Definition drift is caught by pins, not by
differentials.

### SA-6. Model actors here are delegates, not maintainers of record

Authority originates with a human. A model actor holds a written, bounded,
revocable delegation, and its signature attests **that a delegated process ran
under a policy a human signed** — not that a model decided something in its own
right. Non-repudiation rests with the accountable human entity and does not move.

In this repository that is mechanical. Every actor that signs a record has a key
bound to a role in `.warrant/v3.json` (an owner-path file): the author files a
pull request's head, the reviewer (`pr/acceptor`) accepts it or files findings,
the claims checker (`claim/verifier`) accepts a claim only after replaying its
witnesses and mutants, and the review replayer re-runs a finding's test. None of
them merges: the owner does (AGENTS.md rule 5), and branch protection makes a
merge go through a pull request with the required checks green (SA-12).

What a key binding does **not** establish: that the model behind a key decided
anything in its own right, or that two keys stand for independent parties. Both
reviewers and authors are delegates of the same human, and the positioning in
the sibling repository
([`warrant/MODEL-ACTORS.md`](https://github.com/s0fractal/warrant/blob/master/MODEL-ACTORS.md))
still applies. The previous text of this item flagged a `(maintainer)`
annotation in `spec/GOV-anchors.md`; that document was retired on 2026-10-31,
and with it the place where the mechanism and the positioning disagreed.

### SA-8. The publish path has run four times, on one runner, read back by the releaser

`.github/workflows/publish.yml` has published four releases to PyPI through
Trusted Publishing with no stored token: **0.6.6.post1** (2026-07-30), **0.6.7**
(2026-07-31), **0.7.0** (2026-09-17) and **0.8.0** (2026-10-19). The token
exchange, the `pypi` environment gate and PyPI's acceptance of this repository's
workflow identity have worked for those tags on GitHub's hosted runner, with the
action SHAs pinned in that file. For 0.7.0 the served digests were compared with
the release run's own artifacts and matched; `PUBLISHING.md` records what was
checked for each release.

What that does **not** establish:

- **Four runs are not a track record.** Nothing has exercised the path after a
  rotated publisher, a renamed workflow or environment, or from another runner.
  A configuration that quietly stops matching fails at upload, after the gate.
- **The TestPyPI dry run has never been performed.** All four publishes went
  straight to PyPI.
- **Only this project has installed the result.** Every read-back was done on
  one host by the party that cut the release. No outside party is known to have
  installed any version or reproduced an upload.
- **A green publish is not a gate.** `tools/check_release_surface.py` measures
  the artifact against this repository's own documentation and says nothing
  about whether either is correct.

### SA-9. Review is by a second model family, not by an independent party

A pull request is reviewed by the actor `.warrant/v3.json` names as
`pr/acceptor` (Codex), whose acceptance or findings are signed records in
`.warrant/records.jsonl`, and CI re-executes the review replays and claims
acceptances new since the base. That is a different model family looking at the
change with the means to run it, which in this project has repeatedly found
reproducible defects the suites did not cover (`AGENTS.md` rule 3).

It is not an independent gate: the reviewer is a delegate of the same human who
owns the repository (SA-6), and no party outside this project has reviewed any
revision. Nothing here is stated as validated without naming by what.

### SA-10. The proof-guard registry assumes review, not verification, at two points

`proofs/proof_guard.py regen` can make any drift pass by construction; it is
never run by a bridge or by CI, and the pin file is the claim.
`GUARD_CLAIMS.txt` is a **review-visibility** control, not an authority — whoever
can edit the registry can edit it too, and no bridge consumes it as authority.
The core-module allowance (constants owned by `Init`/`Lean`/`Std` are unpinned,
fixed only by `lean-toolchain`) is likewise trust rather than verification.

`proofs/README.md` is the source of truth for the per-front detail of all three.

## Explicit non-goals

### SA-11. Totality is not affordability, and the caller picks the budget

`eval` is total: a stranger's term always terminates. That is a real guarantee and
it is not the same as being safe to run. A 32-bit ATP admits up to
**4,294,967,295** priced actions, and because the memory bound is `size ≤ atp + 1`
the budget a stranger chooses is also their licence over the evaluator's semantic
materialized size. The
party supplying the term therefore decides how much a verifier spends discovering
that it terminates.

The reference implementation's other limits — depth, materialized nodes, store
fetches — are all breached *during* evaluation, after the work that breached them
has been done. Nothing refused before starting.

`impl/sigma_glyph.py` now has `admit()` and a `VERIFIER_LIMITS` preset carrying
`max_atp`. It raises `AdmissionRefused` before any allocation or store read, and
that refusal is deliberately not a `ResourceFault` and not a DISSONANCE: it says
the verifier declined, not what the term evaluates to. `DEFAULT_LIMITS` leaves
`max_atp` unset, because this module is also the conformance oracle and must
answer for any budget the Book permits.

**What remains assumed.** A verifier has to actually choose `VERIFIER_LIMITS`;
nothing forces it. Book I says nothing about admission and should not — this is
local policy, and §3.6 already keeps local faults outside the canonical outcomes.
Consumers of Σ-GLYPH reasons elsewhere in the ecosystem have not been changed, so
today the assumption is: *every verifier applies its own cap, and none is known to.*


### SA-12. The guard lives in the artifact it guards — narrowed, not closed

An external review named this **V22, "Edit the Cop"**: `proof_guard.py`,
`theorem_pins.json`, `GUARD_CLAIMS.txt`, the regression suite and the workflow
that runs them all sit in the repository they police. `GUARD_CLAIMS.txt` already
said as much — whoever can change the registry can change the claims; it is
visibility control, not authority.

The reviewer marked it a threat-model candidate rather than a reproduced exploit,
because they could not read this repository's protection settings. Those settings
were then read, and the condition held: **rulesets empty, `master` unprotected**.
Anyone with push could move the branch directly, guard and all.

**What was done.** `master` requires a pull request and four checks —
`test`, `lean`, `SonarCloud Code Analysis`, `GitGuardian Security Checks` (read
from the branch protection on 2026-11-01; `cross-repo` left with Warrant 0.x) —
with force-pushes and deletions refused and **admin enforcement on**. That last
part was tested rather than assumed: with `enforce_admins` off, a direct push by
an admin succeeded and was reverted by a forward commit, not a rewrite; with it
on, the same push is rejected with `protected branch hook declined`.

**What is still open, and it is the interesting half.** A *pull request* can still
change a theorem, the guard, the tests and the workflow together, and the required
checks are the ones that pull request defines. GitHub requires no approving
review; the reviewer's acceptance is a record (SA-9), and `.github/` and
`.warrant/v3.json` are owner paths, which the owner merges. The recursion is
narrowed to one door, not closed:

    proof ← guard ← tests ← workflow ← all editable in the same change

Closing it needs a verifier that does not live in the candidate revision — a
reusable workflow pinned to a protected ref, a separate verifier repository, or a
governance commitment over the verifier's hash. None of those exist yet, so no
claim of an independent guard should be made on the strength of branch protection
alone.


### NG-5. Serving as its own trust anchor

`.warrant/v3.json` is this repository's statement of whose keys it accepts for
which role, and CI assesses the records under it. That is a declaration by the
tree under review, not a trust anchor: a verifier outside this project brings
its own trust and reads the records under it (Warrant 3 assesses records under
the receiver's profile). Distributing trust is out of scope of this repository
and stays out of it.

### NG-6. Treating a local resource fault as a canonical failure

A `ResourceFault` is a property of the machine that ran the reduction;
`DISSONANCE` is a property of the term. Collapsing the two would make a result
hash depend on the host, which is the one thing the whole stack exists to
prevent. Specified in Book I, and not a bug.

## Severity, and how to report

`SECURITY.md` is the process. Its ladder in one line: **P0** two conforming nodes
can disagree on a result hash, or a resumed computation disagrees with a straight
run, or something forged reads as verified; **P1** the specification is silent where an implementer
must guess; **P2** clarity; **P3** roadmap.

A finding is a reproduction. A script that exits non-zero on the defect and zero
once fixed becomes a permanent regression test — and every fix in this
repository's history carries a **negative control**: the fix is removed and the
attack is shown to come back.

Verify before reporting:

```bash
tools/test-all.sh          # the full matrix; a skipped surface exits 2, not ALL GREEN
```
