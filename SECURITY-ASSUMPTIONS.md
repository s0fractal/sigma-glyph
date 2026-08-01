# Security assumptions and non-goals

**Status: informative, not adopted.** Adoption is a threshold warrant signed by
roster keys (`AGENTS.md` rule 2) and has not happened for this document. Where
this file and a Book or `spec/GOV-anchors.md` disagree, the specification is
normative and this file is the defect.

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
copied; the Books state limits inline where they are normative; `reviews/` holds
findings never promoted to either. A limit stated somewhere else and absent here
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

> Given a term hash and a budget, any two conforming implementations compute the
> same result hash or the same deterministic budget-exhaustion outcome —
> integer-only, total, with work **and peak memory** bounded in advance, and with
> no float, clock or network anywhere in the reduction.

## Scoped assumptions

### SA-1. Part of the Lean chain assumes the compiler, not only the kernel

`native_decide` is in the trusted base for part of the mechanized chain, so those
theorems trust the Lean **compiler** as well as the kernel. `C1Compiler.lean`
does not use it.

The assumption is discharged nowhere and cannot be: that is what `native_decide`
means. It is named per-front in `proofs/README.md`, which also lists the
`native_decide` sources whose *statements* are pinned while what they *rest on*
is not re-checked.

### SA-2. Most proof fronts reach CI through differential bridges, not kernel checks

CI checks `SizeBound.lean` directly; the rest of the proofs reach CI through the
differential bridges rather than as kernel checks of their own.

What a bridge can and cannot establish is enumerated in `proofs/README.md`, and
that enumeration is the source of truth for it — three of the four differentials
run the compiled Lean model, two do not run Lean beyond the guard, and no
differential can exercise a `Prop`-valued definition, which is exactly where each
theorem's hypotheses live. Definition drift is caught by pins, not by
differentials.

### SA-3. The pinned auditor disagrees with the live CLI on signature severity

`tools/warrant_verify.py` is pinned to a governed Warrant v0.1/v0.2 snapshot in
which any bad signature is fatal; SPEC v0.3 §6(3) makes it a warning and excludes
the signature. Demonstrated: one store, one forged co-signature — this tool says
`errors=1`, the live CLI says `0 errors, 56 warnings`. The tool prints the
divergence on the line where it fires.

A re-pin belongs to a §7 gate, so the divergence is a stated assumption rather
than a bug: a reader of this repository's own `.warrants/` audit is reading the
older, stricter rule, deliberately.

### SA-4. Book III admits a JCS-equivalent but non-canonical assertion blob

`sigma_federation.py` does not compare raw bytes against `canon(parsed)`. The
v0.6.6 governance fix (GOV 1.0.2 byte-canonicality) covered the **governance**
verifier only.

Deferred to the settlement-integration layer, which is the layer now being built.
Until then, a Book III consumer must not infer byte-canonicality from acceptance.

### SA-5. A threshold assumes independent custody; this one has not had it

Governance is 2-of-3 (`spec/GOV-anchors.md` §5). Counted rather than
characterised:

- The threshold has been exercised **six times** — the v0.6.2 – v0.6.7
  anchor-set adoptions — and nothing else among the store's 52 records carries a
  second signature. (This paragraph read "five times" and "50 records" for two
  days after the v0.6.7 adoption landed; an external review caught it. A count
  nobody recounts is the defect this file exists to name, and it was this file's.)
- **Three of the six** pair `claude-fable-5` with `codex`. Those two keys sat in
  one directory on one host as of 2026-07-28 (warrant's
  `policies/gate-settlement.json`, `custody`), so any process there could sign as
  both. **Two signatures from one host are one custody**, and a report calling
  them a 2-of-3 quorum makes a false claim.
- The other three pair `claude-fable-5` with the founder actor key
  `s0fractal@sigma-glyph`. What the store establishes is exactly that: an
  envelope carrying a valid signature under that actor id. It does not establish
  who held the key, whether a human was present, or whether the act was
  deliberate.

  (A previous revision of this bullet said the v0.6.7 co-signer was "the human
  principal acting deliberately rather than a second key on the same machine".
  Nothing in the store supports either half. It was written into the section
  headed *Counted rather than characterised*, which exists to forbid precisely
  that substitution — and written while correcting a different overstatement in
  the same paragraph. Left visible instead of deleted: this file's subject is
  the gap between what a signature proves and what a reader assumes it proves,
  and the shortest illustration available is that its own author closed that gap
  by assumption on the first try. A custody or intent claim needs attributable
  evidence from the principal, not an inference from an actor id.)

So where a document describes "2-of-3 governance", the correct reading is: a
2-of-3 policy, satisfied six times, three times by two distinct parties and three
times by one. The machinery is correct as specified; what it has actually
witnessed is smaller than the specification suggests.

### SA-6. Model actors here are delegates, not maintainers of record

Authority originates with a human. A model actor holds a written, bounded,
revocable delegation, and its signature attests **that a delegated process ran
under a policy a human signed** — not that a model decided something in its own
right. Non-repudiation rests with the accountable human entity and does not move.

The full positioning, including four places where the current mechanism does not
yet match it, is in the sibling repository:
[`warrant/MODEL-ACTORS.md`](https://github.com/s0fractal/warrant/blob/master/MODEL-ACTORS.md)
and `warrant/MAINTAINER-LEASE.md`.

One of those four is here. `spec/GOV-anchors.md` §5 annotates
`claude-fable-5@sigma-glyph` as `(maintainer)` and §4 states "the maintainer is a
model". That document is a STANDARD, anchored in `spec/ANCHORS.txt` by the
SHA-256 of its exact bytes, and its anchor-set has been adopted by threshold
warrant — re-wording it changes the anchor and requires a governed adoption, so
it stands as written and is flagged here instead.

Read under the delegation framing, §4's sentence is an argument about **delegated
actors expiring on a published schedule**, and that is the strongest thing in it:
a delegate whose deprecation date is announced in advance by the party operating
it is a liveness fault a policy can be *designed against* rather than merely
survive, which is why §4 requires successions staged before planned retirements
and `N − M ≥ 1`.

### SA-7. ADR-008 is on a branch, and its gate rounds came from one family

ADR-008 is **not on `master`** and not in `spec/ANCHORS.txt`. It lives on
`adr-008-rev15-candidate`, is cited from `warrant`, and all fifteen of its gate
rounds came from one reviewer family. Present is not adopted (`MAP.md` says which
ref holds what); and depth from a single family is measured in this project to
find that family's blind spots slowly, if at all.

### SA-8. The publish path has now run, twice, for two releases on one runner

This item used to say that nothing had ever been published and that the first
release would also be the first test of the OIDC path. That stopped being true
on 2026-07-30, and an assumption that overstates a limitation misleads exactly
as much as one that understates it — so it is rewritten rather than deleted.

`.github/workflows/publish.yml` has executed end to end **twice**: `sigma-glyph`
**0.6.6.post1** (2026-07-30) and **0.6.7** (2026-07-31) are on PyPI, uploaded
through Trusted Publishing with no stored token. The token exchange, the `pypi`
environment gate, and PyPI's acceptance of this repository's workflow identity
are no longer unexercised — they worked, for those two tags, on GitHub's hosted
runner, with the action SHAs pinned in that file.

What that does **not** establish, which is the part still worth reading as an
assumption:

- **Two runs are not a track record.** Nothing has exercised the path after a
  rotated publisher, a renamed workflow, a changed environment name, or from a
  runner other than the hosted one. A Trusted Publishing configuration that
  quietly stops matching fails at upload — after the gate has already passed.
- **The TestPyPI dry run has still never been performed.** `PUBLISHING.md`
  describes it and the `testpypi` job has never run; both real publishes went
  straight to PyPI.
- **Only the maintainer has installed the result.** `pip install sigma-glyph`
  into a clean venv, followed by the three self-tests, was done by the
  maintainer on one host. No one else is known to have installed it, and no
  second party has reproduced the upload.
- **A green publish is not a gate.** `tools/check_release_surface.py` measures
  the artifact against this repository's own documentation and says nothing
  about whether either is correct. SA-9 is unaffected.

### SA-9. No independent gate is currently affordable

Work lands with the attestation described in warrant's
`policies/gate-settlement.json` rather than with a passed gate. Green suites are
necessary and not sufficient: in this project every real gate has been green and
still found new reproducible bugs the suites did not cover (`AGENTS.md` rule 3).

Nothing in this document has passed an independent gate, and this item is the
reason no claim in it is stated as validated without naming by what.

### SA-10. The proof-guard registry assumes review, not verification, at two points

`proofs/proof_guard.py regen` can make any drift pass by construction; it is
never run by a bridge or by CI, and the pin file is the claim.
`GUARD_CLAIMS.txt` is a **review-visibility** control, not an authority — whoever
can edit the registry can edit it too, and no bridge consumes it as authority.
The core-module allowance (constants owned by `Init`/`Lean`/`Std` are unpinned,
fixed only by `lean-toolchain`) is likewise trust rather than verification.

`proofs/README.md` is the source of truth for the per-front detail of all three.

## Explicit non-goals

### NG-1. Preventing a fork

A fork is a new jurisdiction with its own genesis root adopting its own
anchor-set chain. The mechanism **names** divergence mechanically; it does not
and must not prevent it (`GOV-anchors.md` §1). Canonicity is a per-verifier trust
decision, expressed by which root a verifier pins. Jurisdictions diverge
permanently by design (Book III §1), and governance is no exception.

### NG-2. Legitimacy-from-origin

Governance claims *continuity-from-then*, never legitimacy-from-origin. It proves
every release after activation was authorized under the policy in force, and it
MUST NOT fabricate authority for pre-governance history; pre-governance sections
stay in `ANCHORS.txt` labeled as ancestors (`GOV-anchors.md` §1). A reader
wanting a story about the beginning will not get one, deliberately.

### NG-3. Deciding a governance conflict

Two rival authorized adoptions of different valid anchor-sets sharing an ancestor
**freeze the chain**, totally, with no deterministic winner rule (`GOV-anchors.md`
§3 step 7). This is not an omission: any such rule over attacker-influenceable
identifiers is grindable position-selection — the class that killed the ADR-006
interference fold. Conflicts resolve by settlement; no verifier may pick a winner.

### NG-4. Recovering a deadlocked jurisdiction

A roster tolerates exactly `len(actors) − min_sigs` permanent silent absences;
below that the jurisdiction deadlocks **permanently, by design**, and recovery is
a fork (`GOV-anchors.md` §4). The alternative — an escape hatch — is a standing
bypass of the quorum it exists to protect. SA-6's staged succession is the
intended answer, and it must happen before the absence, not after.

### NG-5. Serving as its own trust anchor

A verifier MUST refuse a trust config located inside the tree being verified: an
in-tree trust anchor is weaker than signed git tags (`GOV-anchors.md` §3 step 1).
`spec/GOV-anchors.md` §5 is documentation, not a trust anchor. Distributing trust
is out of scope of this repository and stays out of it.

### NG-6. Treating a local resource fault as a canonical failure

A `ResourceFault` is a property of the machine that ran the reduction;
`DISSONANCE` is a property of the term. Collapsing the two would make a result
hash depend on the host, which is the one thing the whole stack exists to
prevent. Specified in Book I, and not a bug.

### NG-7. Aesthetic agreement about `spec/LORE.md`

`LORE.md` is non-normative. Disagreement with the naming or the cosmology is
welcome and is not a specification defect.

## Severity, and how to report

`SECURITY.md` is the process. Its ladder in one line: **P0** two conforming nodes
can disagree on a result hash, or the wave layer affects identity, or something
forged reads as verified; **P1** the specification is silent where an implementer
must guess; **P2** clarity; **P3** roadmap.

A finding is a reproduction. A script that exits non-zero on the defect and zero
once fixed becomes a permanent regression test — and every fix in this
repository's history carries a **negative control**: the fix is removed and the
attack is shown to come back.

Verify before reporting:

```bash
tools/test-all.sh          # the full matrix; a skipped surface exits 2, not ALL GREEN
```
