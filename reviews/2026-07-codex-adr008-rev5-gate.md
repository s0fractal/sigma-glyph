# ADR-008 rev 5 gate review

Date: 2026-07-26  
Scope: uncommitted ADR-008 rev 5 and its executable probes, with the sibling
`warrant` reference implementation as the claimed integration boundary  
Verdict: **STRUCTURAL KERNEL PASSES; WARRANT INTEGRATION GATE DOES NOT**

Rev 5 correctly closes the rev-4 local-contract defects:

- `wave@v1` now has a canonical, content-addressed check object;
- query and threshold changes mint different check hashes;
- every Sigma-side blob load authenticates its digest;
- the Book III selection policy is committed and resolved;
- view/profile/ruleset equality and projection cardinality are exercised;
- the probe reads genuine Warrant body shapes and WarrantIDs rather than mock
  record dictionaries.

Those are material improvements. The remaining gap is no longer the arithmetic
or the cited-side join. It is the boundary the ADR now calls
`VerifiedContext`: the happy vector is not emitted by settlement verification,
cannot be active under the roots named by its own view, and does not put the
`wave@v1` check inside any Warrant. Targeted tests also show that an active
`reject` can currently serve as the projection or assertion accept and still
produce `pass`.

## Reproduced baseline

- All three ADR probes pass their stated checks.
- `python3 -m py_compile` passes for all three probes.
- `examples/resonant_precedent_join_probe.py` reports happy `pass`, fifteen
  supplied edges as `unverified`, and no exception for its four adversarial
  check objects.
- `tools/test-all.sh`: `TEST-ALL: ALL GREEN`, including the 582/582 Lean wave
  bridge.

The regression suite therefore remains healthy. The findings below are new
contract/integration findings, not regressions in Books I–III.

## Findings

### [P1] There is still no Warrant carrying or executing the `wave@v1` reason

The builder creates three Warrants, all with an empty `because` array. It then
creates the `wave@v1` check blob separately, but no Warrant body references that
hash. Direct inspection gives:

```text
check referenced by a Warrant -> False
all active Warrant because    -> []
```

The current Warrant schema also rejects the reason the ADR describes:

```text
Warrant version 0.2
validate_body(
  because=[{kind:"check", runtime:"sigma-glyph.wave@v1", ...}]
)
-> runtime must be one of ('cmd@v1', 'ski@v1')
```

Thus the probe proves `verify_citation()` as a standalone function, not a
Warrant runtime or end-to-end citation. No Warrant verifier invokes it, compares
its result with a claimed verdict, escalates `unverified` on an active record,
or defines its settlement novelty fingerprint.

The next fixture must contain an actual Warrant reason using the new runtime and
must be accepted/re-executed by the Warrant verifier. The Warrant-side change
needs to specify:

1. the body version/runtime registry entry that permits the reason;
2. the exact reason fields and claimed-verdict comparison;
3. base versus settlement-grade handling of `unverified`;
4. the §7 outcome fingerprint/novelty semantics;
5. deterministic resource limits for re-execution.

Until that exists, “real Warrant store” is true only for the three supporting
records, not for the citation itself.

### [P1] The happy `VerifiedContext` cannot be derived under its own C2 view

`VerifiedContext` receives a caller-supplied set. All three supplied records have
`prior: []`, so they are three independent Warrant roots. The view, meanwhile,
names two different fabricated hashes as `genesis_roots`; none is a Warrant root
in the store:

```text
all supplied active records are independent roots -> True (3)
view roots ∩ actual Warrant roots                 -> {}
settlement active records under view roots        -> 0
verify_citation with supplied context              -> pass
```

The decision subject blob is also unresolved in the happy store. Base Warrant
verification reports `0 errors, 4 warnings`, not a clean verified fixture.

This is more than the acknowledged absence of thresholds/key-state. The active
set used to obtain `pass` is impossible under the jurisdiction/root coordinates
committed by the same view.

Build a hermetic settlement fixture as one real lineage:

- store the decision subject bytes;
- make one actual Warrant root the Book III jurisdiction;
- link projection, assertion, and citation records into that root's `prior`
  closure;
- pin the fixture actor/key and root in a test trust config;
- derive `active_records` from settlement verification;
- set `view.jurisdiction` and `genesis_roots` from that result;
- prove the derived active-set commitment equals C2.

This can use the existing deterministic fixture seed. It does not need or
justify touching the user's mac-mini production keys.

The adapter also needs jurisdictional provenance, not only a union of active
WarrantIDs. In a multi-root store, a global settlement-active union lets a
decision or projection from another root satisfy this join. The interface should
expose `active_for(jurisdiction)` or the verified root lineage for every record.

### [P1] Settlement-active does not mean “accepted”

The normative adapter exposes subject, under, actor, and time, but omits
`body.decision`. The verifier consequently never checks that the projection
Warrant or assertion Warrant is an `accept`.

Using genuine schema-valid, correctly signed `reject` bodies, and trusting their
roots so they are settlement-active, produced:

```text
projection Warrant decision = reject
settlement-active            = True
verify_citation              = ('pass', 'coherence=32767')
Warrant verify               = (0 errors, 5 warnings)

assertion Warrant decision   = reject
settlement-active            = True
verify_citation              = ('pass', 'coherence=32767')
Warrant verify               = (0 errors, 5 warnings)
```

That contradicts the ADR's “accepted C0 projection” language. Add `decision` to
`VerifiedContext` and require at least:

- projection Warrant: `decision == "accept"`;
- cited assertion Warrant: `decision == "accept"`.

Whether the source decision may be either `accept` or `reject` is a profile
choice and should be stated explicitly. Add negative vectors for every
disallowed decision value.

### [P1] `ruleset` and `vocabulary` are compared as names but not resolved

The code resolves the projection-policy blob, but its vocabulary hash is never
loaded. The check/view ruleset hashes are only compared for equality and are
never resolved or validated as a governed Sigma anchor-set.

The happy fixture itself demonstrates both missing references:

```text
ruleset blob resolves   -> False
vocabulary blob resolves -> False
```

More decisively, replacing both `check.ruleset` and `view.sigma_ruleset` with the
same arbitrary, unresolved hex64 still gives:

```text
matched arbitrary ruleset, blob exists=False
-> ('pass', 'coherence=32767')
```

Equality closes substitution between check and view, but it does not establish
the semantics of `LUT_COS`, the assertion schema, or the vocabulary. Resolve and
digest-authenticate both objects, validate closed schemas, and connect the
ruleset/profile to their governed/adopted anchors. Otherwise two implementations
can agree on a meaningless hash while executing different bundled semantics.

### [P1/P2] The query is committed but not a “querying decision”

Rev 5 correctly commits the query assertion, so verdict determinism is fixed.
However, only `query.wave` participates in verification. Its node, jurisdiction,
epoch, Warrant lifecycle, and relation to a querying decision are unchecked. A
canonical assertion with an unrelated node, foreign jurisdiction, and
`epoch = 2^64 - 1`, but the same phase, still returns `pass`.

This is one of two valid contracts, but the ADR must choose:

- **Free query vector:** the query is user-chosen retrieval input. Rename it
  accordingly and remove “of the querying decision”; arbitrary query-side
  selection is then an explicit feature/threat.
- **Decision citation:** add a query-side projection/Warrant join analogous to
  the cited side, including active selection in the view.

The current prose promises the second while the code implements the first. Since
ranking position may affect what evidence humans or agents inspect, “no standing”
does not by itself make this mismatch harmless.

### [P2] Runtime work is deterministic but not bounded

`wave@v1` is proposed as a re-executable stranger-supplied Warrant runtime. The
verifier reads blobs without a specified byte limit and scans the full active set
for projection cardinality and again for assertion candidates. No maximum active
set, blob size, candidate count, or metered cost is committed by the check.

This does not break byte equality, but it creates a verification-availability
surface absent from the budget-bounded `ski@v1` design. The Warrant runtime entry
should define hard portable limits or a deterministic cost budget and specify
`unverified` on exhaustion. Cross-implementation vectors must cover exact-limit
and one-over-limit cases.

### [P2] Direct-assertion R0 remains prose-only at the boundary

The ADR now states that pin-only and structurally derived terms are ineligible
under R0, which is a coherent first version. The join probe still has no explicit
pin-only or derived-wave abstention vector. Add both so a later implementation
cannot silently call `wave_fed()` while another requires a direct assertion.

Also clarify whether projection filing requires `under == [profile]` or merely
`profile in under`. The implementation currently permits extra policies, which
can make one projection participate in multiple policy domains.

## Gate recommendation

Do **not** start with Go/Rust translation of the current fixture. That would
cross-implement the supplied-context model rather than the intended settlement
contract.

The smallest honest next gate is:

1. add the `sigma-glyph.wave@v1` reason/runtime to a Warrant branch or explicit
   experimental registry;
2. create one deterministic Warrant lineage and synthetic trust config;
3. export a public verified context scoped to one jurisdiction;
4. put an actual citation Warrant carrying the check into that lineage;
5. resolve ruleset and vocabulary anchors;
6. run the positive vector plus reject/foreign-root/unresolved-anchor negatives;
7. only then replay the identical bytes and derived context in Go or Rust.

At that point, cross-implementation agreement is the correct final structural
gate. The projection DSL can remain the isolated semantic research question.
