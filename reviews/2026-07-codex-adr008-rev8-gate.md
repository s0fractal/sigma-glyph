# ADR-008 rev 8 consumer-profile gate

Date: 2026-07-26  
Scope: uncommitted ADR-008 rev 8 and the three precedent probes, checked against
the new Warrant-side WRT-001  
Verdict: **CROSS-PROJECT SPLIT ACCEPTED; CONSUMER STILL CONTRADICTS WRT-001 AND
THE REFERENCE PROBE DOES NOT YET IMPLEMENT ITS CLAIMED WARRANT CONTRACT**

The normative-home split is right: C1 belongs in Warrant, while ADR-008 should
own C0/C2/C3 and the join. The Book II/III anchors are now real. The remaining
issues are at the exact producer/consumer seam.

The companion Warrant review contains the full runtime analysis:
`warrant/reviews/2026-07-codex-wrt001-gate.md`.

## Findings

### [P1] The “minus wave-citations” join lets an assertion erase itself from selection

The probe treats every record carrying a `sigma-glyph.wave@v1` reason as a
citation and excludes it from C2's candidate universe. It does not require the
reason-bearing Warrant's subject to equal `check.entry`.

An active, higher-epoch rival assertion can therefore carry the happy
citation's valid check reason. Both runtime executions pass and public
`verify_store` returns `(0, 0)`, while the rival never reaches Book III
`select()`.

ADR-008 must define a citation lifecycle/role that is bound to the
`precedent-entry@v1` subject. WRT should exclude only the currently verified
citation WarrantID from its own snapshot, not every record that happens to carry
a wave reason.

### [P1] C2 currently identifies a moving live head, not a replayable view

Appending one unrelated active Warrant after the happy citation changes the
runtime-derived set and makes the existing C2 commitment fail. The original
citation changes from `(0, 0)` to `(1, 0)` without any cited blob or Warrant
changing.

If ADR-008 intends current-head retrieval, it must specify staleness and
re-indexing. If a `PrecedentIndexViewID` is intended to identify a replayable
historical ranking, it must name an authorized historical checkpoint. The
current “R0 checkpoint” does neither.

### [P1] Rev 8 contains two incompatible normative index formulas

The rev-8 changelog and C1 summary use:

```text
settlement_active_for(J) minus wave citations
```

but the verified-probe description, retained rev-7 changelog, main join
pseudocode, and design criterion 9 still use:

```text
strict_prior_closure(citation) intersect settlement_active_for(J)
```

These are adversarially different sets: the former is complete but live and the
latter is historical but filer-selectable. Implementations following different
sections will disagree on C2 and on the selected wave.

Remove the stale rev-7 formula from the normative body and state one temporal
contract. The probe docstring is stale in the same way. Also update “twelve
negatives” to the current 13.

### [P1] “Single context” and public integration are claims about a future implementation

The probe wraps `W.verify_store` externally. It builds `_settlement_context`
once, then the original verifier builds it a second time from the same
settlement inputs. Instrumentation observes two context constructions per call.

On context failure it calls the base verifier with `settlement=None`, silently
downgrading non-wave records. With the wave record removed and the trust file
missing, a settlement-requested verification returns zero errors. With
`quiet=False`, runtime errors are also absent from the printed final summary
even though they are added to the returned tuple.

The probe is useful executable design work, but ADR-008 should call it a wrapper
prototype until Warrant itself owns the dispatcher/context/reporter path.

### [P1] §7 is documented but not integrated

The standalone helper returns a tuple, but the actual Warrant
`fingerprint(reason, body, store)` returns `None` for the wave reason and
`tunnel_fingerprints()` returns an empty set. WRT-001 also does not enumerate
the exact nested closure.

Therefore rev 8 has not yet closed the rev-7 §7 finding. Say “proposed and
deferred” until Warrant recognizes it and vectors prove both fingerprint
novelty and tunnel foreclosure.

### [P1/P2] The profile anchor is neither current nor governed

The probe's Book II/III values match `spec/ANCHORS.txt`. Its profile member is a
provisional raw SHA-256 value from an older ADR revision. The current ADR hashes
to `909c7d3d...`, while the pinned value begins `a9096dd2...`; neither value is a
governed profile entry in `spec/ANCHORS.txt`.

The ruleset is exact but not yet wholly governed. Move the profile semantics and
vectors into an externally anchored artifact, then pin its governed anchor.

### [P2] The happy fixture's warning count is an artifact of quiet mode

The synthetic trust config has no actor/key binding. `quiet=True` reports zero
warnings because the current Warrant verifier skips the unbound-signature
warning branch in quiet mode. `quiet=False` reports five unbound signatures.

Keep key-state binding explicitly deferred and avoid presenting `0 warnings` as
evidence that the fixture is settlement-grade.

## Verified baseline

- all three probes compile and their supplied assertions pass;
- the join probe catches its 13 supplied negatives;
- `tools/test-all.sh` is fully green;
- Warrant's current cross-implementation suite is fully green.

These results establish that the existing Books and Warrant implementations
remain sound under their current versions. They do not cover the adversarial
role-confusion or post-citation-growth vectors above.

## Gate recommendation

Keep the WRT-001 split and the non-retroactive version. Before budget work:

1. close the citation-role binding bypass;
2. choose and specify live-head versus historical-checkpoint semantics;
3. make ADR-008 contain exactly that one index formula;
4. land the runtime in Warrant's real single-context verifier path;
5. define and test exact §7 closure and replace the provisional profile anchor.

Only then are the four proposed budget counters measuring a stable contract.
