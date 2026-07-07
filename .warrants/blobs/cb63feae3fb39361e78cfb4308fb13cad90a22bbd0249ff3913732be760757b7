# ADR-006 design-gate review: annotation federation

Reviewer: Codex, independent adversarial pass
Scope: `proposals/ADR-006-annotation-federation.md`, with normative dependency `proposals/refs/warrant-SPEC-v0.3-snapshot.md`

## Verdict

**Do not adopt F3 as proposed. Adopt F1 as the v0.6 normative core, with an explicit extension point for non-settlement ranking/aggregate views.**

F3's attractive claim is that Warrant can carry identity while Book II `interfere()` supplies native wave arithmetic. That claim fails at the fold boundary: `interfere()` is intentionally order-dependent by Left Dominance, and every deterministic canonical order available to a warrant store becomes either grindable or an arbitrary policy selector. At that point the ordering policy, not the algebra, determines the effective phase.

F2 is also rejected: it does not solve identity, jurisdiction, key state, settlement, or spam, and it imports a non-commutative operator into a convergence problem. F1 is sufficient for v0.6 federation because ADR-006's consensus-grade requirement is not "average all opinions"; it is "let two verifiers mechanically name the same jurisdictional annotation view." Warrant v0.3 already gives that.

I concede the review-gate F1 question: **selection-only merge is sufficient for the protocol layer.** Useful arithmetic cases exist, such as local discovery ranking from many weak endorsements, freshness scoring, or sector Mass dashboards, but those do not require a normative `WaveVectorQ` effective wave. They can be local/query profiles over accepted warrants. ADR-006 does not name a protocol use case where two implementations must arithmetically merge independent assertions into one canonical wave rather than select, supersede, or display multiple settled assertions.

## Verified vectors statement

I read `reviews/README.md` first, then ran the required checks:

```bash
python3 impl/sigma_glyph.py
python3 tests/spec_conformance/run_reference.py
python3 tools/verify_anchors.py
```

Actual outputs observed:

- `python3 impl/sigma_glyph.py` ended with `ALL PASS`.
- `python3 tests/spec_conformance/run_reference.py` ended with `CONFORMANCE: ALL PASS (49/49)`.
- `python3 tools/verify_anchors.py` printed the expected spec/vector anchor hashes and ended with `anchors verified`.

I also verified the Book II algebra claims relied on below:

```bash
python3 impl/sigma_wave.py
```

Actual output ended with `WAVE: ALL PASS (30/30)`.

For the specific ADR-006 fold risks, I ran:

```bash
python3 - <<'PY'
from impl.sigma_wave import W, interfere, iterate_am
pairs = [
    (W(8192,30000,100), W(40960,20000,-100)),
    (W(0,50000,0), W(16384,40000,0)),
]
for a,b in pairs:
    print('A then B =', interfere(a,b))
    print('B then A =', interfere(b,a))
print('decay from 49151 =', iterate_am(W(0,49151,0)))
print('fixed point =', interfere(W(12345,65535,-32768), W(12345,65535,-32768)))
print('max self from en 0 =', interfere(W(12345,65535,0), W(12345,65535,0)))
PY
```

Actual output:

```text
A then B = {'ph': 8192, 'am': 0, 'en': 256}
B then A = {'ph': 40960, 'am': 0, 'en': 256}
A then B = {'ph': 0, 'am': 15259, 'en': 0}
B then A = {'ph': 16384, 'am': 15259, 'en': 0}
decay from 49151 = [49151, 36863, 20735, 6560, 657, 7, 0]
fixed point = {'ph': 12345, 'am': 65535, 'en': -32768}
max self from en 0 = {'ph': 12345, 'am': 65535, 'en': -256}
```

These runs confirm the relevant Book II facts: Left Dominance makes phase order-dependent, partial self-interference decays quadratically to zero, and `{am=65535,en=-32768}` is the non-zero crystallized fixed point for a pinned phase.

## Review-gate asks

### 1. Fold-position grinding under Left Dominance

Yes, an asserter can choose fold position if the canonical order uses any attacker-influenced hash or metadata. A WarrantID commits to the body, including fields such as `ts`, `prior`, `because`, `evidence`, and the assertion subject hash. Even if the intended annotation payload is fixed, the actor can vary admissible non-semantic or weakly semantic material until the WarrantID lands where desired. If assertion blob hashes are used instead, a payload format with any nonce, evidence choice, note, epoch, or equivalent entropy has the same problem.

This is not a small bias. A left fold of `interfere()` inherits the phase of the first folded assertion forever. The command above shows identical inputs in different order preserve amplitude/entropy but flip final phase from `8192` to `40960`, or from `0` to `16384`. With hash-order folding, "lowest hash wins phase" is the real rule.

Sorting by `(ph, hash)` does not fix this; it deterministically privileges the lowest phase bucket, so the attacker chooses phase power by choosing `ph`, not by winning trust. Sorting by DAG order or timestamp is worse: Warrant section 5.1 explicitly rejects wall-clock trust for key state, and Warrant section 9 scopes settlement by roots rather than imposing a total order over actors.

The fold would need order-insensitivity by construction to be safe. But Book II `interfere()` cannot provide that without giving up Left Dominance for federation. A commutative aggregation would have to compute phase by some separate policy, histogram, vector sum, or winner selection, and then aggregate amplitude/entropy independently. That may be useful, but it is no longer "reuse `interfere()` as the merge operator"; it is a new federation algebra.

### 2. `ski@v1`-priced amplitude and amortization

`ski@v1` proves that a deterministic check reduces within a bounded ATP budget. It does not prove that the actor burned a scarce resource per annotation. A prover can cite one expensive check across many annotation warrants, or file many warrants whose checks are byte-identical or outcome-identical. Warrant section 7 even defines outcome fingerprints so syntactically different checks with the same consequence can be recognized; that helps settlement novelty, but it does not meter weight.

Therefore "budget bounds claimable `am`" is not enforceable as stated. ATP is verifier replay cost and peak-memory bound, not spend. Treating it as spend turns public proof into reusable money.

### 3. Is selection-only F1 sufficient?

Yes for v0.6. The federation layer needs identity, authorization, settlement, explicit jurisdiction, re-litigation, and deterministic view naming. F1 supplies those by delegating to Warrant v0.3. The protocol does not need to turn multiple accepted assertions into one arithmetic wave unless ADR-006 first specifies a consensus-grade consumer that cannot operate on a selected assertion set.

A real arithmetic use case is "rank nodes by accumulated independent endorsements while decaying stale endorsements." But that is a local navigation or discovery score. It can be computed by clients from the warrant set and named as a score profile. It does not need to be the jurisdiction's canonical `wave(h)`.

## Findings

### P1: F3's canonical `interfere()` fold is not consensus-safe

Two conforming implementations can agree on warrant bytes and still inherit an arbitrary, attacker-influenced phase winner from the canonical ordering rule. Because Left Dominance makes the first folded phase final, order selection becomes semantic selection. Hash order is grindable; timestamp order is forgeable; DAG order is partial and policy-dependent; `(ph, hash)` order bakes in phase priority.

Concrete text proposal:

```text
ADR-006 v0.6 core MUST NOT define the jurisdictional effective wave by
folding multiple independent annotation assertions with Book II interfere().
Within a jurisdiction, wave(h) is selected by settlement policy from active
annotation warrants, or is absent/ambiguous if policy selects no unique
assertion. Any aggregate computed from multiple active assertions MUST be
named as a derived score profile, not as the canonical WaveVectorQ, unless a
future ADR defines a commutative, order-insensitive federation algebra with
machine vectors.
```

If F3 is revisited later, the fold definition must not be a total order over actor-controlled records. It must either be commutative/associative or explicitly be a policy winner-take-one selector.

### P1: Criterion 4 is unenforceable if `ski@v1` ATP is treated as spend

`ski@v1` is strong evidence, not scarce weight. A single expensive proof can be amortized across unlimited assertions unless the policy separately limits reuse. Even binding a check to `{node,wave,actor,epoch}` only proves a per-subject computation was replayable; it still does not stop an actor from producing many subjects with the same underlying expensive evidence unless the jurisdiction imposes quotas, thresholds, stake, or reputation caps.

Concrete text proposal:

```text
Weight costs something: an assertion's amplitude MUST be bounded by a
jurisdiction policy over scarce or slashable authority, not by the ATP budget
of a reusable proof alone. ski@v1 MAY support the factual claim behind an
annotation, but MUST NOT by itself mint amplitude. If a policy uses check
budgets in a weight formula, it MUST define the uniqueness domain
(actor, node, wave, epoch, check outcome fingerprint) and MUST cap or reject
reuse across assertions.
```

### P1: "Fold-and-forget" conflicts with Warrant settlement and with non-commutative folds

Criterion 5 says a node must hold a jurisdiction's effective view in `O(annotated nodes)`, not `O(all assertions ever)`, and that "fold-and-forget must be sound despite non-commutativity." That is not sound for F3. A later key-state warrant, supersede, re-litigation, policy change, or newly resolved settlement-critical blob can change which assertions are active. Warrant section 7 settlement and section 9 jurisdiction also require tunnel and root context to decide foreclosure, novelty, and active roots. Discarding the assertion history leaves no way to recompute or audit the view.

Concrete text proposal:

```text
State is bounded for query caches, not for authoritative verification:
implementations MAY cache the current effective view in O(annotated nodes),
but the authoritative federation state is the settlement-active warrant DAG
and referenced blobs, or a compact authenticated proof sufficient to
reconstruct the active assertion set. No normative rule may require
fold-and-forget over a non-commutative merge.
```

Under the recommended F1 architecture, this becomes easy: cache selected `wave(h)` per jurisdiction, but retain the Warrant store or a verifiable projection for audit.

### P2: ADR-006 needs an exact annotation assertion blob schema

F1 says the warrant subject is a JCS blob containing `{"node":"<hex64>","wave":...}`. The Warrant body itself only has `subject: {"hash": <hex64>, "note": ...}`. For cross-implementation determinism, the ADR must define the blob bytes exactly: allowed keys, integer ranges, version tag, unknown-field handling, and whether partial waves are legal.

Concrete text proposal:

```text
Annotation assertion subject blob v1 is JCS-canonical I-JSON with exactly:
{
  "annotation": "sigma-glyph.wave-assertion@v1",
  "node": "<lowercase hex64 NodeHash>",
  "wave": { "ph": <uint16>, "am": <uint16>, "en": <int16> }
}
Unknown fields are invalid. Numbers are JSON integers only. The blob hash is
the Warrant subject.hash. Partial pins are Book II/spec data only; federation
assertions carry complete WaveVectorQ values unless a later profile defines
partial assertion semantics.
```

### P2: Criteria 2 and 3 need a canonical view identity

"Same genesis set and same warrant store" is close, but not enough for portable disagreement names. A view also depends on the Sigma spec anchor, Warrant spec/profile, annotation policy hashes, active root set, settlement-active record set, and the exact assertion-selection rule. Without a canonical `ViewID`, two nodes can explain disagreement in prose but not mechanically compare what they derived.

Concrete text proposal:

```text
AnnotationViewID = SHA-256(JCS({
  "view": "sigma-glyph.annotation-view@v1",
  "sigma_spec_anchor": "<hex64>",
  "warrant_profile": "warrant-v0.3",
  "roots": ["<WarrantID>", ... sorted lexicographically],
  "policies": ["<hex64>", ... sorted lexicographically],
  "active_assertions": ["<WarrantID>", ... sorted lexicographically],
  "selection_rule": "<policy-defined rule id>"
}))
```

The exact fields can change, but the ADR needs this class of object. It is the mechanical name for explicit divergence.

## Attack on the five design criteria

1. **Book I unreachable:** correct and enforceable if the protocol adds tests proving arbitrary annotation stores do not affect `eval()`, serialization, or NodeHash. This criterion is necessary and complete for the Book I boundary.

2. **Determinism per jurisdiction:** necessary, but incomplete until the input set and `ViewID` are canonical. "Same warrant store" must define treatment of inactive roots, unresolved blobs, settlement-inactive records, key-state conflicts, and policy versions.

3. **Divergence explicit:** correct direction, but under-specified. Warrant roots identify jurisdictions, but ADR-006 still needs a portable view identifier and a standard way to list selected/active assertions for a node.

4. **Weight costs something:** necessary but currently unenforceable. `ski@v1` ATP is not spend; threshold signatures and reputation are policy authority, not algebraic cost; stake is out of scope unless a jurisdiction defines slashing. The criterion should require policy-defined scarcity/caps and forbid reusable proofs from directly minting amplitude.

5. **State bounded:** valid as a cache/query goal, invalid as an authoritative storage rule. Warrant settlement is historical and DAG-based. F1 can expose `O(annotated nodes)` projections; it cannot safely erase the evidence needed to verify those projections. F3 fold-and-forget is especially unsafe because non-commutative order prevents later deletion/supersession without replay.

Missing criterion:

```text
Auditability/projection: every effective annotation returned by a node MUST be
traceable to the WarrantID(s), policy hash(es), root set, and selection rule
that produced it. Cached projections MAY be served, but clients MUST be able
to request the proof material or an authenticated projection hash.
```

## Architecture recommendation

Adopt **F1.5**:

1. Warrant-carried complete wave assertions are the only normative federation object in v0.6.
2. A jurisdiction's policy selects zero or one current effective assertion per `NodeHash`, or returns an explicit conflict set.
3. Multiple assertions are not folded into a canonical `WaveVectorQ`.
4. Arithmetic aggregation is allowed only as a named, non-settlement profile over the selected/active assertion set, with its own conformance vectors if it becomes normative later.
5. `ski@v1` is accepted as portable evidence for claims, not as direct amplitude spend.

This preserves Book I, uses Warrant v0.3 for the machinery it actually specifies, and avoids pretending that a non-commutative application operator is a federation CRDT.

## Relative to prior reviews

Per the required ordering, I formed the findings above before reading prior reviews. Afterward I searched:

```bash
rg -n "ADR-006|annotation federation|Warrant-carried|interference weighs|canonical fold|priced amplitude|F1|F2|F3" reviews
```

I found no prior ADR-006 gate review in `reviews/`; the only ADR-006 hit is `reviews/README.md`, which lists ADR-006 as an open proposal. Therefore there is no prior ADR-006 finding to agree or disagree with. New relative to the existing review inbox: this review rejects F3-as-proposed, recommends F1.5, and supplies concrete amendments for fold safety, priced amplitude, state boundedness, assertion schema, and view identity.
