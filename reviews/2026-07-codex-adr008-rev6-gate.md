# ADR-008 rev 6 gate review

Date: 2026-07-26  
Scope: uncommitted ADR-008 rev 6, its executable probes, and the sibling Warrant
reference implementation used by the integration fixture  
Verdict: **CITED-SIDE JOIN PASSES; AMEND WARRANT DISPATCH AND SNAPSHOT BINDING
BEFORE BUDGET OR CROSS-IMPLEMENTATION**

Rev 6 closes the concrete record-shape and lineage defects from rev 5:

- the decision subject resolves;
- the projection and assertion records are real, signed descendants of one root;
- their activity is obtained from Warrant settlement rather than record presence;
- projection and assertion roles require `decision == "accept"`;
- the citation Warrant genuinely contains a `sigma-glyph.wave@v1` reason;
- the ruleset and vocabulary objects are at least resolved and schema-checked;
- projection filing is exactly `under == [profile]`;
- all twelve supplied negatives are caught and the full repository suite remains
  green.

The remaining blockers are not the proposed budget or Go/Rust parity yet.
`wave@v1` is still installed by retroactively mutating the meaning of Warrant
`"0.2"`, its hook is outside `verify_store`, and the historical index context is
still a caller input whose completeness is not derived or verified by the hook.
There is also no semantic binding between `check.ruleset` and the local Book
II/III implementation that actually executes.

## Reproduced baseline

- Metric probe: all stated properties hold.
- Contract probe: C1/C2/C3 supplied checks hold.
- Rev-6 join probe:
  - settlement active records: 5;
  - pre-citation index records: 4;
  - `verify_citation`: `pass`, coherence 32767;
  - custom reason hook: `OK`, claimed `pass`;
  - twelve supplied negatives caught; no supplied-case crash.
- `python3 -m py_compile`: passes for all three probes.
- `tools/test-all.sh`: `TEST-ALL: ALL GREEN`, including 582/582 Lean wave
  differential cases.

## Findings

### [P1] Registering the runtime retroactively changes Warrant `"0.2"`

The fixture appends `sigma-glyph.wave@v1` to `W.RUNTIMES["0.2"]` at process
runtime. This is not the runtime-version change promised by the ADR. It changes
the validity of already-versioned bytes without changing their WarrantID:

```text
clean Warrant 0.2 validator:
  runtime must be one of ('cmd@v1', 'ski@v1')

after register_wave_runtime():
  same body -> schema valid
  same WarrantID -> True
```

Two honest Warrant 0.2 implementations therefore disagree on whether the same
record exists in the valid domain. This violates Warrant's version rule and
prevents cross-implementation agreement before `wave@v1` even runs.

Adopt one of these normatively in Warrant:

- a new body-format version whose allowed-runtime set includes
  `sigma-glyph.wave@v1`; or
- a versioned runtime-extension mechanism that is itself committed by the body
  and has identical validation rules across implementations.

Do not extend the meaning of `"0.2"` through mutable process state. The
experimental prototype may monkey-patch for exploration, but the ADR must not
call the resulting record conformant Warrant 0.2.

### [P1] The hook is not part of Warrant verification

`verify_wave_reasons()` scans real Warrant reasons, which is progress, but
`W.verify_store()` never calls it and never includes its errors in its return
value. A claimed-verdict lie demonstrates the split:

```text
W.verify_store(store) -> (0 errors, 5 warnings)
custom wave hook      -> ERR: pass; claimed fail
```

Thus “the Warrant verifier re-executes it” is not yet true. A caller that invokes
the public Warrant verifier and trusts its zero-error result never sees the
`wave@v1` failure.

Implement a Warrant runtime dispatcher used by `verify_store`, with the same
observable report/error count semantics as `ski@v1`. The runtime must receive the
reason-bearing WarrantID and the settlement context, because both are needed to
derive the correct historical view. The fixture should assert the combined
public verifier result, not a separately printed hook list.

### [P1] The experimental hook regresses Warrant's store-wide totality

The hook iterates every parsed record and calls `r.get(...)` without verifying
that `because` is a list of objects. A single inactive schema-invalid record with
`because: ["not-an-object"]` produces:

```text
verify_wave_reasons -> AttributeError: 'str' object has no attribute 'get'
W.verify_store      -> bounded (2 errors, 7 warnings), no crash
```

This is exactly the store-wide availability class the Warrant verifier has
already hardened against. “No byte-domain input raises” is therefore false for
the integrated surface.

The dispatcher must only execute reasons from shape-validated records, remain
defensive over inactive malformed records, and convert every runtime exception
to a stable `unverified` reason class. Add malformed-envelope, scalar-body,
non-list-`because`, scalar-reason, missing-field, and deeply nested blob vectors.

### [P1] C2 authenticates a supplied subset, not a settlement-derived snapshot

The fixture derives `index_active` correctly while building the check. During
verification, however, `verify_wave_reasons(store, settlement_ctx, index_ctx)`
accepts that precomputed context as a host argument. The hook does not derive it
from the reason-bearing Warrant, and `verify_citation` only checks that the
supplied subset hashes to the view's commitment.

Consequently, a caller can remove a settlement-active record, mint a view/check
committing the smaller subset, and still pass. Removing the active jurisdiction
root itself gave:

```text
settlement-derived pre-citation index size -> 4
caller-supplied subset size                -> 3
settlement-active root omitted             -> True
verify_citation                            -> ('pass', 'coherence=32767')
```

The root does not affect the arithmetic, so self-consistency is mistaken for
snapshot completeness. More importantly, an omitted competitor could change
which assertion wins.

Excluding the citation Warrant is the right way to avoid a self-WarrantID cycle,
but the exclusion needs a normative causal rule. The cleanest option is:

```text
index_context(CW, J) =
  settlement_active_for(J)
  ∩ strict_prior_closure(CW)
```

The reason-bearing WarrantID is known to the dispatcher. Require the citation's
`prior` frontier to cover every record in the intended view, derive the context
inside the verifier, and compare its exact set commitment with C2. For the
competitor/cardinality vectors, the rival records must therefore be included in
that frontier.

An alternative is a settled snapshot/frontier object plus a content-addressed
canonical WarrantID-list blob. A bare set hash is insufficient to reconstruct
or prove completeness of a historical view. Whichever rule is chosen, remove
`index_ctx` as a free hook argument.

### [P1] A well-shaped `ruleset` does not select the semantics being executed

Rev 6 resolves the anchor-set object, but accepts any object matching:

```json
{"anchor_set":"sigma-glyph.anchor-set@v1","books":["<hex64>", "..."]}
```

The referenced Book hashes are not resolved, governed, or compared with an
allowed runtime anchor. The evaluator still unconditionally calls the locally
imported `sw.LUT_COS` and `sf.select`.

Replacing the happy ruleset with a newly minted, well-shaped anchor containing
two nonexistent “evil book” hashes produced:

```text
both Book anchors resolve -> [False, False]
verify_citation           -> ('pass', 'coherence=32767')
```

Therefore `check.ruleset` still does not determine runtime behavior. Make the
Warrant runtime registry map `sigma-glyph.wave@v1` to one exact supported
ruleset hash, or implement governed dispatch where every accepted ruleset hash
selects a precisely anchored implementation.

The actual dependency scope should also be corrected:

- Book II: coherence/LUT semantics;
- Book III: assertion schema and `select()` semantics;
- ADR-008 profile: C0/C1/C2 schemas and join algorithm;
- Warrant: context/settlement/runtime failure semantics.

Book I evaluation is explicitly unreachable, so pinning Book I while omitting
Book III is backwards. If NodeHash identity is intended as a Book I dependency,
name that narrow dependency separately; the runtime unquestionably executes
Book III.

### [P2] The acknowledged remaining items are real

The ADR correctly keeps these open:

- portable resource bounds and `unverified` on exhaustion;
- bound fixture key state;
- explicit direct-only R0 abstention vectors;
- independent implementation parity.

They should remain open, but they are not the immediate next step. A budget
cannot be normatively enforced until the actual Warrant dispatcher owns the
runtime invocation and historical context construction.

For the budget, prefer a simple deterministic cost model over reusing Book I ATP
verbatim. `wave@v1` work is object resolution plus set/candidate scans, not graph
reduction. Suggested charged units:

- canonical bytes read;
- WarrantIDs examined for snapshot/cardinality;
- assertion candidates passed to `select`;
- fixed cost for each schema/digest check.

Commit the budget in the check or runtime version and vector exact-limit plus
one-over-limit behavior. Book I's size-priced philosophy is reusable; its ATP
unit is not automatically the right unit.

### [P2] Set schemas need canonical set rules

`anchor_set.books` and `vocabulary.leaves` currently accept duplicates and
arbitrary ordering. If these are sets, enforce sorted, duplicate-free arrays so
semantically identical sets cannot mint multiple anchor/profile hashes. If order
has semantics, rename the fields and define it.

### [P3] The negative harness assertion is weaker than its heading

For ordinary negatives, the harness marks a case successful when
`verify_citation == unverified` even if the active citation hook did not emit
`ERR`. The current twelve happen to show `hookERR=True`, but the assertion should
require it for every active-citation negative. Otherwise a future regression in
settlement escalation can still print the overall success line.

## Gate order

The recommended order is:

1. introduce a non-retroactive Warrant version/extension for `wave@v1`;
2. integrate a total runtime dispatcher into public `verify_store`;
3. derive the exact pre-citation jurisdictional snapshot from the
   reason-bearing Warrant rather than a host `index_ctx`;
4. bind the runtime to an exact Book II/III/profile ruleset;
5. add deterministic resource accounting and key-state binding;
6. add the direct-R0 abstention vectors;
7. only then freeze the fixture bytes and port the vector to Go or Rust.

Rev 6 proves the cited-side join and shows the intended Warrant topology. It
does not yet prove a conforming Warrant implementation will execute the same
runtime over the same settlement snapshot. That remains a structural boundary,
not merely strictness.
