# ADR-008 rev 10 integration gate

Date: 2026-07-26  
Scope: ADR-008 rev 10, its updated probes, WRT-001, and the real Warrant verifier
refactor  
Verdict: **PRIOR LIFECYCLE COUNTEREXAMPLES ARE COVERED, BUT R0/PROBE AND
EFFECTIVE-AUTHORITY SEMANTICS ARE NOT YET SYNCHRONIZED**

Rev 10 correctly demonstrates:

- superseded assertions are removed from the probe's Book III candidate set;
- a projection replacement no longer creates effective cardinality 2;
- a resolvable borrowed check reaches the exact subject/entry binding failure;
- the §7 helper is honestly labelled obsolete;
- stored precedent is said to require R1.

The remaining problem is not the set subtraction itself but who is allowed to
cause it, plus the fact that the executable happy path still does what the new
normative text forbids.

The companion Warrant code review is:
`warrant/reviews/2026-07-codex-wrt001-refactor-gate.md`.

## Findings

### [P1] Effective-set subtraction turns any eligible supersede into censorship

`effective_active()` subtracts the target of every eligible supersede without
checking target policy, actor binding, key state, or authorization. In current
Warrant semantics, a different self-declared actor can file a well-signed
supersede and remain in `active_records`; the target is then removed from C2,
C0 cardinality, and Book III selection.

The lifecycle contract must distinguish an **authorized effective supersede**
from a merely eligible supersede. Key-state is therefore part of effective-set
derivation, not only checkpoint authorization.

Vectors must cover:

- unbound/foreign actor attempts to supersede an assertion or projection;
- wrong-policy supersede;
- authorized same-policy supersede;
- supersede of a supersede;
- competing authorized superseders;
- unrelated supersede.

### [P1] The probe's happy path violates ADR/WRT's R0 decision

The normative decision says R0 is an ephemeral query and a wave reason MUST NOT
be filed settlement-active. Yet `build()` creates a Warrant carrying an R0
reason, and the probe advertises public settlement verification of that record
as its happy path.

There is no field in the current check/view schema that allows the verifier to
distinguish R0 and R1. Therefore “MUST NOT file” is currently prose-only.

Move the R0 probe to a direct query invocation with no Warrant filing. Reserve
the reason-bearing fixture for R1, where the check explicitly names the
authorized checkpoint. Until that exists, there should be no settlement-active
wave happy path.

### [P1/P2] ADR marks the verifier refactor landed before its cross-impl gate

Python now returns one global error for missing trust, while Go returns zero
errors and exit 0. The standard agreement suite is green only because this edge
is absent. ADR-008 should call the refactor “proposed/uncommitted” until the
single-snapshot and Go differential findings are closed.

### [P2] Effective lifecycle is still correctly listed as deferred

WRT-001's deferred item 1 asks for competing and unrelated supersede vectors,
but the probe currently contains only:

- superseded cited assertion;
- superseded projection plus replacement.

Keep the feature described as a candidate derivation, not a resolved P1, until
authorization, chaining, and the named vectors exist.

## Verified baseline

- join probe passes its supplied happy path and 15 negatives;
- resolvable borrowed-check binding is now genuinely exercised;
- all three probes compile;
- Sigma `tools/test-all.sh` is fully green;
- Warrant's currently covered agreement suite is green;
- independent missing-trust differential exposes Python `(1,0)` versus Go
  `(0,0)`.

## Next move

Return to the generic Warrant patch before R1:

1. one record snapshot;
2. Go fail-closed parity;
3. version-scoped dispatcher without raw settlement authority;
4. direct Warrant hook tests.

After that, design R1 together with authorized effective lifecycle. The
checkpoint must commit the output of that authorized derivation, not raw
eligibility and not unauthenticated supersede subtraction.

