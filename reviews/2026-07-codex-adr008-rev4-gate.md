# ADR-008 rev 4 gate review

Date: 2026-07-26  
Scope: uncommitted ADR-008 proposal and its three executable probes  
Verdict: **AMEND, THEN RE-REVIEW**

Rev 4 is a real structural advance. `precedent-entry@v1` now joins the cited
decision, projection, asserted term, selected Book III assertion, and index view;
the supplied edge mutations all become `unverified` without throwing. The
normative-home split is also sound.

The gate is not closed yet. The probe demonstrates an internally consistent
*model* of the join, but the actual check remains open over two uncommitted
inputs, the object loader does not authenticate content hashes, and the selected
wave depends on policy that is absent from the view. In addition, the supposed
Warrant records are simplified metadata rather than Warrant objects or a defined
adapter from verified settlement state.

## Reproduced baseline

- `examples/resonant_precedent_probe.py`: all checks pass.
- `examples/resonant_precedent_contracts_probe.py`: all checks pass.
- `examples/resonant_precedent_join_probe.py`: happy path passes; every supplied
  edge returns `unverified`; no supplied edge raises.
- `python3 -m py_compile` over all three probes: passes.
- `tools/test-all.sh`: `TEST-ALL: ALL GREEN`.

These results establish totality for the supplied vectors, but not closure or
cross-implementation determinism of the proposed runtime.

## Findings

### [P1] C1 still has no closed, content-addressed check input

`verify_precedent_entry(entry_hash, wave_q, threshold, store)` receives
`wave_q` and `threshold` as host arguments. Neither value is present in
`precedent-entry@v1`, nor is a `wave@v1` check blob constructed or loaded.
Consequently, identical cited bytes have different verdicts:

```text
same entry, query S  -> ('pass', 'coherence=32767')
same entry, query K  -> ('fail', 'coherence=0')
```

This contradicts the ADR's statement that the runtime has a “closed check blob”
and prevents a Warrant verifier from reproducing the claim from body-level
evidence. It also makes “same view ⇒ byte-identical ranking” insufficient: the
query and threshold are part of the computation but not part of the commitment.

Define and vector a canonical `wave@v1` check object containing at least the
entry/reference set, a content-addressed query wave or query derivation proof,
the inclusive threshold, and the ruleset/runtime anchor. Make the verifier accept
only that check hash plus verified store/context. If the query is the current
Warrant itself, avoid a self-WarrantID cycle by committing to its subject,
projection, or wave evidence rather than its final WarrantID.

### [P1] `load_canonical` authenticates syntax, not the requested content hash

After lookup by `h`, the loader checks duplicate keys, JCS bytes, and schema, but
never checks `sha_hex(raw) == h`. A canonical assertion can therefore be replaced
under its old key and still be trusted:

```text
before substitution                  -> ('fail', 'coherence=0')
sha_hex(replacement) == requested key -> False
after canonical substitution         -> ('pass', 'coherence=32767')
```

The store is part of the untrusted byte domain, so dictionary-key integrity
cannot be assumed. Verify the digest before decoding/semantic use for every
loaded blob. Add a vector where canonical, schema-valid bytes are stored under
the wrong key; it must be `unverified`.

### [P1] C2 does not commit the Book III selection function

The view contains `metric` but no Book III selection/federation policy. The probe
uses the module-local hard-coded `SEL_POLICY`. The same view and active set can
select different assertion warrants under epoch-descending versus
epoch-ascending policies:

```text
same PrecedentIndexViewID, epoch-desc policy -> one WarrantID
same PrecedentIndexViewID, epoch-asc policy  -> a different WarrantID
```

Therefore `PrecedentIndexViewID` does not yet identify the effective wave whose
coherence is ranked. Add a governed `wave_selection_policy` (or the precise Book
III ruleset/federation-policy anchor) to C2, resolve it from bytes, and pass the
resolved policy to `select()`.

Related C2 fields are currently syntactic decorations rather than verified
coordinates:

- replacing `projection_profile` with an arbitrary hex64 still passes;
- replacing `sigma_ruleset` with an arbitrary hex64 still passes;
- the happy view's `jurisdiction` is not one of its `genesis_roots`, yet passes.

The verifier must bind the entry's C0 profile to `view.projection_profile`,
validate the expected governed Sigma anchor, and define/verify the relation
between jurisdiction and genesis roots. Otherwise distinct implementations can
honestly interpret the same ViewID differently.

### [P1] The “Warrant join” does not yet consume Warrant semantics

The probe's records are local dictionaries such as:

```python
{"kind": "decision", "subject": S, "under": P}
```

They are not Warrant bodies (`subject.hash`, `under` cardinality, decision,
actor/signature data, and settlement interpretation differ), and `active` is a
caller-provided set. Thus the test uses the real Book III `select()` but not a
real Warrant schema, verification result, or settlement closure. A second
implementation cannot derive this adapter from the ADR.

Specify the exact verified-context interface, including how an accepted active
record exposes WarrantID, `body.subject.hash`, `body.under`, actor, time/epoch,
jurisdiction, and decision. Prefer a fixture produced by the real Warrant
verifier/store. At minimum, make the adapter normative and vector its mapping
from canonical Warrant bytes and settlement output.

### [P1] C0 cardinality is stated but not enforced

The ADR requires at most one active projection per
`(source_warrant, profile)`, with multiples becoming a conflict. The verifier
only checks the named projection Warrant. Adding a second active projection for
the same key, updating the active-set commitment, and leaving the cited one
unchanged still returns:

```text
two active projections, same (source_warrant, profile)
-> ('pass', 'coherence=32767')
```

Enumerate active projection accepts in the verified view and require exactly one
eligible winner for that key, or delegate to a specified settlement selection
whose conflict result is checked. Add both duplicate-identical and
different-projection conflict vectors.

### [P2] Direct-assertion R0 needs an explicit eligibility boundary

The join currently indexes only a directly selected assertion over the C0 term.
Book II/III `wave(term)` can also obtain a wave from canonical pins or structural
derivation. This is acceptable as an R0 restriction only if the profile says
that such terms are deliberately ineligible until they have a direct selected
assertion. Otherwise the probe is narrower than the metric named by the ADR.

Add vectors showing pin-only and structurally-derived terms abstain under R0.
If `wave_fed` is intended instead, the committed selection/ruleset context must
cover the derivation and all dependencies.

### [P2] Remaining closed-schema edges

- `wave_q` validates only `ph`; `am` and `en` may have arbitrary types despite
  the object being called a WaveVectorQ. Either validate all three coordinates or
  define the query input as phase-only.
- C0's `vocabulary` is accepted as an arbitrary hex64 and never resolved or
  checked against the governed projection profile.
- The noncanonical test stores pretty bytes under the *canonical* digest. Keep
  that corruption test, but also hash the actual noncanonical bytes to isolate
  the JCS rejection from the missing digest check.
- The earlier contracts probe still exposes a partial kernel with an `invalid`
  result. Deprecate it or make its non-normative role unmistakable now that the
  ADR specifies Warrant `pass`/`fail` plus verifier-level `unverified`.
- The “losing/stale” vector proves losing selection, not a staleness rule; the
  hard-coded policy has no `max_age`. Rename it or add a real stale case under
  the committed policy.

## Normative-home decision

Keep the split introduced in rev 4:

- C0 projection payload and projection governance: OAIP / explicit OAIP-to-Sigma
  profile.
- C1 `wave@v1` and its failure/version semantics: Warrant runtime registry.
- Coherence metric and anchor: Book II.
- Effective-wave selection: Book III.
- C2/C3 composition and precedent entry/query/result formats: ADR-008 profile.

The whole ADR should not be moved into OAIP. Its core value is precisely the
cross-project composition boundary.

## Next gate

The smallest honest next vector is a canonical `wave@v1` check blob evaluated
against a real Warrant verified/settled fixture. It should mutate, one at a time:

1. query evidence or threshold without changing the check hash;
2. canonical bytes under an incorrect content hash;
3. the committed Book III selection policy;
4. C0 profile, vocabulary, Sigma ruleset, jurisdiction/root relation;
5. a second active projection for the same cardinality key;
6. real Warrant acceptance/activity/subject/under fields;
7. direct-only versus derived/pinned wave eligibility.

Once Python and one independent implementation agree on that vector, the
remaining projection DSL question is genuinely semantic research. At rev 4,
there are still structural seams before that boundary.
