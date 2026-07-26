# ADR-008 rev 11 — independent cross-repository gate

Date: 2026-07-26  
Scope: ADR-008 rev 11 and `resonant_precedent_join_probe.py`, checked against
the current uncommitted Warrant refactor  
Verdict: **NOT READY FOR R1; FIX THE WARRANT PLUMBING AND THE R0 CONTRACT FIRST**

The full Sigma suite and all supplied join-probe assertions are green. The
effective-lifecycle censorship gap is now honestly named, and coupling it to
key-state before R1 is the right architectural correction. Two remaining
cross-repository claims are nevertheless executable contradictions.

The Warrant-side commit blockers—double-read/schema-invalid trust, mutable
handler state, missing runtime CAS resolver, and vacuous hook coverage—are
documented in:

`warrant/reviews/2026-07-codex-wrt001-refactor-recheck.md`.

## Findings

### [P1] The alleged non-filing R0 query still files and depends on a wave Warrant

The probe prints:

```text
R0 is a DIRECT ephemeral query (no Warrant filed)
```

but `build()` unconditionally creates `CW` with a `wave@v1` check reason and
stores it:

- `examples/resonant_precedent_join_probe.py:408-430`
- `examples/resonant_precedent_join_probe.py:528-532`

The direct demonstration then passes that filed WarrantID to
`verify_citation`:

- `examples/resonant_precedent_join_probe.py:551-554`

This is not merely fixture residue. The function contract itself requires
`cw_wid` so it can enforce `citation.subject == check.entry` and subtract the
current citation from the live-head universe. A query with no citation Warrant
has no such WarrantID. Therefore the currently implemented R0 cannot satisfy
WRT-001's “creates no Warrant reason” decision.

Define a genuinely separate ephemeral-query contract. For example, its closed
query object can carry entry/query/threshold/ruleset directly, derive the
candidate universe without subtracting a nonexistent citation, and return a
non-settlement result. Add a fixture mode that never calls `put_record` for
`CW`, assert the record count before/after is identical, and prove the result
does not depend on a synthetic citation identity. Keep the role-bound
`cw_wid` path exclusively for R1 stored citations.

### [P1] ADR-008 still presents the known censorship primitive as the profile algorithm

The rev-11 changelog correctly says naïve “active minus supersede targets” is
only a candidate and lets any self-signed actor censor another record. But the
main algorithm still normatively defines:

```text
EFFECTIVE = active minus active-supersede targets
```

and uses it for the index, C0 cardinality, and selection:

- `proposals/ADR-008-resonant-precedent.md:49-67`

That contradicts both the changelog and the opening promise that ADR-008 defers
effective lifecycle to WRT-001 “and never restates a competing formula”.

Until authorized lifecycle/key-state is specified, the main algorithm must say
that `authorized_effective_active_for(J, checkpoint)` is unresolved/R1-only,
without embedding the insecure candidate formula. The prototype may retain the
naïve derivation only as an explicitly failing research vector.

### [P2] The deferred list and completed-plumbing claim disagree inside rev 11

The changelog says the generic Warrant refactor is completed, while “Remaining”
still lists “real single-context verifier” as item 1:

- `proposals/ADR-008-resonant-precedent.md:5-8`
- `proposals/ADR-008-resonant-precedent.md:135-147`

WRT-001 now numbers the generic refactor as item 0 and separates authorized
effective lifecycle from key-state as inseparable items 1–2. Synchronize the ADR
only after the Warrant recheck findings are fixed. Until then item 0 should be
`IN PROGRESS`, not `DONE`.

### [P2] The supplied green probe does not exercise the new Warrant registry

The probe still monkey-patches `W.verify_store` with a wrapper and explicitly
does not register through the new generic handler path. Consequently its
happy/negative results cannot validate the new registry's context identity,
reporter folding, fail-closed behavior, or ability to resolve blobs. The WRT
document acknowledges this, but ADR's “Verified probes” language makes the
integration evidence sound stronger than it is.

Keep the current probe as a semantic model. Add a separate Warrant-local
end-to-end vector only after the runtime execution context has an immutable
snapshot and authenticated CAS accessor.

## Recommendation

Do not start R1 or collect governance signatures. The next gate is still the
generic Warrant verifier boundary, followed by a genuinely non-filing R0 vector.
Then specify authorized effective lifecycle + key-state + R1 together. The
current research ordering is sound; the claimed completion state is not.
