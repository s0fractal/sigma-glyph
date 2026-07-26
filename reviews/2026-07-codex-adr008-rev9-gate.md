# ADR-008 rev 9 consumer-profile gate

Date: 2026-07-26  
Scope: ADR-008 rev 9 and its updated precedent probes against WRT-001 rev 2 and
the current Warrant settlement implementation  
Verdict: **ROLE BINDING ACCEPTED; DEFINE EFFECTIVE LIFECYCLE AND REPLACE THE
NON-CONVERGENT R0 WORKFLOW BEFORE CALLING THE PROFILE SETTLEMENT-CARRIED**

Rev 9 is substantially more honest and internally consistent:

- there is one index formula;
- LIVE-HEAD and historical checkpoint are no longer conflated;
- only the current role-bound citation is excluded;
- the wrapper, §7, key binding, and profile anchor limitations are named;
- the broken-context global error is executable.

The remaining structural seam is now the meaning of the set being committed.
The companion detailed runtime review is:
`warrant/reviews/2026-07-codex-wrt001-rev2-gate.md`.

## Findings

### [P1] R0 supports at most one clean head citation, not a growing citation corpus

A correctly re-indexed second citation passes, but its insertion stales the first
active citation. Because stale currently means active `unverified` → ERR, public
verification remains nonzero:

```text
before citation 2     (0 errors)
citation 1            stale/unverified
citation 2            pass
after citation 2      (1 error)
```

Repeating re-citation only moves the passing head and accumulates stale active
errors. The profile's stated re-index/re-cite workflow therefore cannot
converge. R0 may be useful as an ephemeral research query, but it is not a usable
settlement-carried multi-citation representation under current Warrant severity
and active-set semantics.

Require R1 for stored citations, or specify a trustworthy effective
supersession/stale lifecycle before enabling R0 records.

### [P1] The join confuses settlement eligibility with effective lifecycle

Warrant's `active_records` does not remove a record targeted by `supersede`.
The profile nevertheless treats membership as “currently active”:

- a superseded assertion remains an `accept` candidate and can still be cited as
  the selected effective wave;
- a superseded projection remains in cardinality, so its valid replacement
  produces cardinality 2.

Executable reproduction:

```text
cited assertion active-record eligible    true
valid supersede active-record eligible     true
new current-view citation                  pass
```

C2/R1 must commit a precisely derived effective set, and the join must use that
same effective lifecycle for projection cardinality and Book III selection.
This is separate from key binding: authorized signers can authorize a
checkpoint that still contains the wrong lifecycle set.

### [P2] The advertised binding vector uses an unresolved check

The rival remains in selection, so the original bypass is genuinely closed.
However the rival carries `H("borrowed")`, not a resolvable borrowed check. Its
own runtime error is “unresolved reference”, not the subject/entry binding
failure claimed in the handoff.

Add a resolvable-check mismatch vector and assert the exact reason. Keep the
existing vector as the reason-presence/no-exclusion test.

### [P2] Executable §7 output contradicts the new deferral

The main probe still prints that wave has a recomputable outcome fingerprint,
while its helper uses the claimed verdict and the real Warrant fingerprint is
`None`. Relabel or remove that supplied check until WRT-001's executable
recomputed fingerprint exists.

### [P3] Remaining prose cleanup

- change “one governed ruleset/anchor-set” to “one exact provisional ruleset”
  until the profile artifact is governed;
- update budget references from item 1 to item 5;
- update the probe docstring's deferred order and rev number;
- replace stale “checkpoint/wave citations” comments in the LIVE-HEAD builder.

## Verified baseline

- join happy path and all 14 supplied negatives pass their harness;
- missing trust on a non-wave store returns a global error;
- all three probes compile;
- Sigma `tools/test-all.sh` is fully green;
- Warrant's full current cross-implementation agreement suite is green.

## Next move

The real single-context/one-reporter refactor is safe to start **as generic
Warrant plumbing only**. Do not register the wave version in production during
that patch. First specify and vector effective supersession plus R1 membership;
then connect the runtime to the prepared dispatcher.

