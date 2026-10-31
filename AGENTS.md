# Agent & contributor conduct (governance-critical)

This repository's entire purpose is **verifiable, honestly-attributed provenance**.
The git history and its commit trailers are themselves provenance. The rules below
are not style — breaking them corrupts the thing this project exists to protect.

## Hard rules

1. **Never commit to `master`.** Work on a branch. `master` advances only through
   review and the project's governance process — never a direct push/commit by an
   agent or a one-off contributor.

2. **Never assert review or roster authority in a commit.** A trailer like
   `Reviewed-by: <X> (2-of-3 roster)` is **false provenance**. Adoption is a
   signed record by the keys the repository's configuration names — **not** a
   commit message: a Warrant 3 record in `.warrant/`, under the keys and roles of
   `.warrant/v3.json`. A review is the reviewer's own signed acceptance of a
   pull request's head version, or a finding it files against it (`warrant
   review`); a commit or a comment carries none. Through v0.7.0 adoption was a
   threshold warrant in the Warrant 0.x store `.warrants/` (retired 2026-10-31,
   kept at commit `96414ab`). An agent is not a roster member and cannot
   self-grant that authority.

3. **An "independent gate" means adversarial counter-vector hunting by a fresh
   reviewer — NOT running the green test suites.** Green suites are *necessary but
   not sufficient*: in this project every real gate has been green AND still found
   new reproducible bugs the suites did not cover. Running the suites and declaring
   a gate "passed" is a rubber stamp and will be rejected.

4. **Record provenance honestly.** State exactly what was validated (which suites,
   which self-audit, which independent reviewer) *and what was not*. Do not upgrade
   "the suites are green" into "independently gated", or "self-audited" into
   "adopted".

5. **Pushing is at the agent's discretion; some actions still need the owner.**
   - **At the agent's discretion:** pushing a working branch (never `master`), and
     opening or updating a pull request.
   - **Explicit owner authorization for the specific action:** merging to
     `master`, rewriting shared history, and publishing (a release, a package,
     a DOI deposit). Approval of one such step is not approval of the next.

6. **Review is not required on every pull request.** Ordinary changes are decided
   by the full test matrix plus whatever review the change warrants. These go
   through the independent adversarial gate of rule 3, and only these:
   - normative or anchored bytes, or an adoption candidate;
   - a security or governance boundary;
   - a publication;
   - an unresolved disagreement between reviewers.

   Rule 4 still applies to every PR: say what was
   validated and what was not.

   *(Rules 5 and 6 were relaxed by the owner on 2026-10-17. Rule 5 previously
   required authorization for every push, and every pull request was treated as
   if it needed a gate.)*

## Precedent (why this file exists)

2026-07-27: an assisting agent ran the green suites, committed the WRT-001 /
ADR-008 work **directly to `master`**, and stamped
`Reviewed-by: Antigravity (2-of-3 roster)` / "independent gate passed". It was
neither an independent adversarial gate nor a governance adoption. The commits
(unpushed) were reset and re-recorded honestly on candidate branches; a genuine
adversarial gate (Kimi K3) then returned `AMEND` with 11 reproducible findings the
green suites had missed. This file exists so that does not recur.
