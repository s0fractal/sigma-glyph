# ADR-008 rev 7 gate review

Date: 2026-07-26  
Scope: uncommitted ADR-008 rev 7 and probes, checked against the sibling Warrant
reference implementation  
Verdict: **NEW VERSION VEHICLE ACCEPTED IN PRINCIPLE; AMEND FAIL-CLOSED DISPATCH,
SNAPSHOT POLICY, AND WARRANT §7 SEMANTICS BEFORE BUDGET**

Rev 7 successfully demonstrates four important mechanisms:

- a wave-bearing body has a distinct version string and no longer changes the
  validity of existing Warrant `"0.2"` bytes;
- the reason-bearing WarrantID is passed to the runtime;
- the happy-path index is reproduced from the citation's prior closure rather
  than supplied directly;
- runtime failures are folded into the tuple returned by the public
  `verify_store`;
- one exact ruleset hash is required;
- sorted/deduplicated set schemas and stronger negative assertions are present.

The current wrapper is still a prototype rather than a fail-closed Warrant
integration. Context-construction failure silently disables all wave checks, the
base verifier and runtime use different hidden settlement inputs, the printed
public report excludes runtime errors, and an author can omit an already
settlement-active competing assertion from `prior` and turn a Book III conflict
into a passing citation. Warrant novelty/tunnel semantics also do not know the
new runtime.

## Reproduced baseline

- All three probes pass their supplied checks.
- Rev-7 happy fixture: returned `verify_store` result is `0 errors, 5 warnings`.
- Malformed inactive fixture: bounded `3 errors`, no supplied-case crash.
- All twelve supplied citation negatives produce at least one returned error.
- `python3 -m py_compile`: passes for all three probes.
- `tools/test-all.sh`: `TEST-ALL: ALL GREEN`, including the 582/582 wave bridge.

## Findings

### [P1] Settlement-context failure disables the runtime fail-open

The wrapper catches every exception around context construction and dispatch,
then assigns `de = dw = 0`. That makes “cannot re-execute” observationally
equivalent to “all checks verified”.

With a citation whose claimed verdict is deliberately false:

```text
trust/context available:
  verify_store -> (1 error, 5 warnings)

delete the synthetic trust file:
  context builder raises FileNotFoundError
  verify_store -> (0 errors, 5 warnings)
```

The same bad active citation becomes clean precisely because verification became
impossible. This violates the ADR's `unverified -> ERR` rule and the Warrant
precedent established for settlement-active `ski@v1`.

The runtime dispatcher must be fail-closed:

- if settlement verification was requested and its context cannot be built,
  return/report a global error and do not claim a usable settlement result;
- if base verification lacks the context required by `wave@v1`, report the
  reason as `unverified` with the normatively selected base severity;
- never translate an infrastructure/runtime exception into zero findings.

Add missing/corrupt trust config, unavailable runtime, malformed settlement
context, and forced runtime-exception vectors.

### [P1] The wrapper does not use the public verifier's settlement argument

`wrapped(store, quiet, settlement)` passes `settlement` to the original verifier,
but then builds a second context through a globally captured
`_sctx_builder`. The two halves of one returned error count can therefore use
different roots, trust configs, and key state. Calling `verify_store` for a
different store still consults the fixture-global scratch trust path.

The dispatcher must execute inside the original verifier's single context, not
recompute state through a callback. Refactor Warrant so `verify_store` constructs
the context once and passes the same object to every runtime. The caller's
`settlement` argument must be the only authority for that invocation.

There is also a reporting split. For a claimed-verdict lie with
`quiet=False`, the public output says:

```text
verify: 5 records, 0 errors, 5 warnings
```

but the wrapped function returns:

```text
(1, 5)
```

The CLI exits nonzero from the tuple, but tells the human that there were zero
errors. Runtime findings must flow through the verifier's normal `out()` path and
be included in the one final summary.

### [P1] `prior` is reproducible, but it is not a complete jurisdiction snapshot

The new formula deterministically verifies the author's declared causal past:

```text
strict_prior_closure(CW) ∩ settlement_active_for(J)
```

It does not prove that the frontier contains all settlement-active records
relevant to the view. Warrant `prior` edges are chosen by the filer; absence from
`prior` does not prove that an active record was unknown, later, or ineligible.

I added a valid, signed assertion Warrant under the same trusted root. It is
settlement-active and would conflict with the cited assertion, but is not named
in `CW.prior`:

```text
omitted rival settlement-active -> True
omitted rival in CW prior       -> False
public verify_store             -> (0 errors, 6 warnings)
verify_citation                 -> pass
```

Thus a citer can intentionally omit a losing/conflicting assertion and mint a
self-consistent C2 commitment. Rev 7 closes host subset substitution but not
frontier selection.

This requires an explicit contract choice:

1. **Author-relative causal view.** Keep the current rule, rename it accordingly,
   and admit “frontier capture” as an adversarial surface. A pass means “selected
   within this filer-declared causal past”, not “effective for the jurisdiction”.
   It must not be used for admissibility language that implies a complete
   jurisdiction view.
2. **Jurisdiction snapshot.** Reference a settlement-authorized checkpoint or
   frontier object that commits the complete active set for J. The citation can
   exclude itself by evaluating the checkpoint it cites, avoiding a cycle. This
   is required if `pass` is supposed to prove the effective Book III wave of the
   jurisdiction.

Given ADR-008's claim of an admissible jurisdictional precedent, I recommend the
second. A raw Warrant prior closure is not a settlement checkpoint.

### [P1] Warrant §7 does not recognize `wave@v1`

The new runtime is added to body validation and store verification, but Warrant's
`fingerprint()` still handles only `cmd@v1` and `ski@v1`:

```text
fingerprint(wave_reason)       -> None
tunnel_fingerprints(citation)  -> empty set
```

Consequently, a wave check cannot count as a new outcome under Warrant §7 and
does not participate in foreclosure/novelty as the other check runtimes do. The
generic tunnel includes the check blob, but does not recursively include the
entry, view, assertions, policies, vocabulary, selection policy, and ruleset that
the runtime actually depends on.

The Warrant runtime ADR must define:

- the `wave@v1` outcome fingerprint;
- which nested references belong to its runtime-specific tunnel;
- behavior when any nested reference is unavailable;
- whether semantically equivalent checks with different view/check hashes share
  a fingerprint;
- the interaction between claimed verdict, computed coherence, threshold, view,
  and ruleset in novelty.

Until this is specified, the citation is verification-carried but not fully
settlement-integrated.

### [P1/P2] The pinned ruleset is still made from symbolic labels

Exact comparison with `WAVE_RULESET` correctly rejects a differently shaped or
newly minted ruleset. However its members are:

```python
H("book-II-coherence@v0.6")
H("book-III-selection@v0.6")
H("adr008-profile@v1")
```

These are hashes of labels, not governed spec/profile bytes or adopted anchor-set
objects. They do not change when the implementation, Book text, vectors, or ADR
semantics change. Direct comparison with the current files confirms none equals
the corresponding content hash.

Replace the placeholders with the repository's actual governed anchor
construction. The runtime registry should pin:

- the adopted Book II anchor;
- the adopted Book III anchor;
- an externally anchored ADR-008 profile artifact and conformance vectors;
- the Warrant runtime/version specification.

Avoid putting the ADR's own changing hash directly inside itself; use the normal
external governance/anchor-set mechanism.

### [P2] Version vehicle recommendation

A dedicated new Warrant body version is the safer choice. `wave@v1` changes more
than an allowed string: it adds re-execution, settlement severity, nested tunnel
references, novelty fingerprints, context requirements, and later a cost model.
A generic extension field would need to version and gate all of those semantics
anyway, while adding downgrade and unknown-extension rules.

`0.2+sigma-wave.1` is acceptable as an experimental namespaced tag, but the final
identifier belongs in a Warrant runtime/version ADR. If Warrant prefers sequential
format versions, use the next body-format version rather than semver-like `+`
syntax whose meaning could be mistaken for ignorable build metadata.

The clean-verifier property to preserve is correct:

- old verifier: unknown version -> invalid record;
- new verifier: exact new version + exact runtime semantics -> valid;
- no reinterpretation of `"0.2"`.

### [P2] Deferred items remain correctly deferred

The deterministic cost model, key-state-bound fixture, R0 abstention vectors, and
Go/Rust parity remain necessary. They are not yet the immediate gate because the
dispatcher and snapshot semantics still determine what work is being metered.

Once the P1s above are fixed, the proposed four budget counters are a sound
starting point:

- canonical bytes read;
- WarrantIDs examined;
- assertion candidates passed to `select`;
- schema/digest operations.

## Recommended next move

This is the right point to move from a Sigma-side monkey-patch into a real
**Warrant runtime ADR**, but not yet to request production signatures or port the
fixture:

1. choose the new Warrant body/runtime version;
2. integrate a single fail-closed runtime dispatcher and settlement context into
   `verify_store`;
3. decide author-relative causal view versus settlement-authorized checkpoint;
4. define `wave@v1` fingerprint and tunnel expansion;
5. replace symbolic ruleset members with governed anchors;
6. then add budget and bound-key vectors;
7. freeze bytes and port to Go/Rust;
8. only after the Warrant gate passes, adopt/sign the runtime version.

Rev 7 has reached the genuine Warrant specification boundary. The next work
belongs there rather than in another local wrapper revision.
