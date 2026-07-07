# Implementation-gate review: Book III federation v0.6.0-draft

Reviewer: Codex, independent adversarial implementation-gate pass

Scope: `spec/book-3-federation.md`, `impl/sigma_federation.py`,
`tests/spec_conformance/federation_vectors.json`

## Verdict

Block the v0.6.0 Book III implementation gate until the P1 items below are
resolved and pinned with vectors.

The settled ADR-006 architecture is sound: F1-strict, selection-only,
warrant-carried federation, no arithmetic assertion merge. I do not re-litigate
that. The draft's concrete spec/oracle/vector surface is not yet tight enough
for a conformance boundary. The biggest issue is not philosophical; it is a
real oracle ordering bug for allowed policies (`actor desc`) plus several
places where the prose says less or more than the oracle implements.

## Verified-vectors statement

Per `reviews/README.md`, I read the review protocol first, then ran the
required commands before reviewing the primary texts.

Command:

```bash
python3 impl/sigma_glyph.py
```

Actual output observed: all listed Book I checks printed `OK`; the command
ended with:

```text
ALL PASS
```

Command:

```bash
python3 tests/spec_conformance/run_reference.py
```

Actual output observed: all 49 listed conformance vectors printed `OK`; the
command ended with:

```text
CONFORMANCE: ALL PASS (49/49)
```

Command:

```bash
python3 tools/verify_anchors.py
```

Actual output observed:

```text
OK  spec/book-1-truth.md a98a03bd5fcc573d4850cdc9e8e80d66518fdc4888ce31c9888df1e24b48b47b
OK  spec/book-2-navigation.md dc0c42a1c28bd2fb3bf731372951e49655df86fa7787715c0e522c6907028860
OK  spec/LORE.md 9bd7977cf7b922a9a3beda60c308d77f6ad6853fa4439e5b03394fa2e79231b9
OK  spec/appendix-a-complexity.md 2df9194b15734a98b185e1f42472ddc52b03597cd6fd48a8a6fbf50799091021
OK  tests/spec_conformance/vectors.json 08116edb302a827858a95dd2a1533134a0fb90220f361085a213f5c93486fcd9
OK  tests/spec_conformance/wave_vectors.json 9ef44d0206b6ced91e25c15c8afa81e1faad5ed7db3c5f27599b2c6f00c04ccb
anchors verified
```

I also ran the Book III oracle:

```bash
python3 impl/sigma_federation.py
```

Actual output observed: all 24 federation selftests/vector replays printed
`OK`; the command ended with:

```text
FEDERATION: ALL PASS (24/24)
```

## Findings

### P1: `actor desc` selection is not the specified lexicographic order and can crash on valid JSON strings

Book III section 4 allows policy order fields `epoch`, `ts`, `warrant_id`, and
`actor`, each with `dir: "asc"|"desc"`. The oracle implements descending string
order by transforming each character with:

```python
"".join(chr(255 - ord(ch)) for ch in v)
```

That is not a sound descending lexicographic key for all strings. Prefix pairs
are enough to break it: `"a" < "aa"` in ascending lexicographic order, so
descending order should put `"aa"` first. The oracle selects `"a"`.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, W

def cand(wid, actor):
    return {
        'warrant_id': wid * 64,
        'actor': actor,
        'ts': 1,
        'assertion': {
            'annotation': ASSERTION_TAG,
            'jurisdiction': J,
            'node': 'cc' * 32,
            'epoch': 1,
            'wave': W(0, 1, 0),
        },
    }

policy = {'federation_policy': 'sigma-glyph.selection@v1',
          'order': [{'field': 'actor', 'dir': 'desc'}]}
res = select([cand('1', 'a'), cand('2', 'aa')], policy, J, 1)
print('selected_actor=', res['selected']['actor'] if res['selected'] else None)
print('selected_warrant=', res['selected']['warrant_id'] if res['selected'] else None)
print('python_desc_expected_first=', sorted(['a', 'aa'], reverse=True)[0])
PY
```

Actual output:

```text
selected_actor= a
selected_warrant= 1111111111111111111111111111111111111111111111111111111111111111
python_desc_expected_first= aa
```

The same trick is also not total for I-JSON strings. A non-ASCII actor with a
code point above 255 raises `ValueError`.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, W

def cand(wid, actor):
    return {
        'warrant_id': wid * 64,
        'actor': actor,
        'ts': 1,
        'assertion': {
            'annotation': ASSERTION_TAG,
            'jurisdiction': J,
            'node': 'cc' * 32,
            'epoch': 1,
            'wave': W(0, 1, 0),
        },
    }

policy = {'federation_policy': 'sigma-glyph.selection@v1',
          'order': [{'field': 'actor', 'dir': 'desc'}]}
try:
    print(select([cand('1', 'Ā'), cand('2', 'a')], policy, J, 1))
except Exception as e:
    print(type(e).__name__ + ': ' + str(e))
PY
```

Actual output:

```text
ValueError: chr() arg not in range(0x110000)
```

This is a P1 because two implementations can both accept the policy and
candidates but derive different selected assertions depending on whether they
follow the prose's "strict lexicographic order" or the oracle's current key
hack. It is not P0 because Book III waves do not affect Book I hashes.

Concrete code proposal:

```python
from functools import cmp_to_key

def _cmp_scalar(a, b):
    if isinstance(a, str) and isinstance(b, str):
        # Or replace this with UTF-8 byte lexicographic comparison, but specify
        # that exact collation in Book III.
        return (a > b) - (a < b)
    return (a > b) - (a < b)

def cmp_candidates(a, b):
    for k in policy["order"]:
        av = a["assertion"]["epoch"] if k["field"] == "epoch" else a[k["field"]]
        bv = b["assertion"]["epoch"] if k["field"] == "epoch" else b[k["field"]]
        c = _cmp_scalar(av, bv)
        if c:
            return -c if k["dir"] == "desc" else c
    return 0

live.sort(key=cmp_to_key(cmp_candidates))
top = [c for c in live if cmp_candidates(c, live[0]) == 0]
```

Concrete text proposal:

```text
For string order fields, lexicographic order is over Unicode scalar-value
sequences as represented in the JCS string value. Implementations MUST compare
strings directly and invert the comparison result for `dir: "desc"`; they MUST
NOT implement descending order by character-complement transforms. A later
revision MAY instead define UTF-8 byte lexicographic order, but the chosen
collation MUST be explicit and vector-pinned.
```

Concrete vector proposal:

```json
{
  "id": "FV-SELECT-ACTOR-DESC-PREFIX",
  "kind": "select",
  "policy": {
    "federation_policy": "sigma-glyph.selection@v1",
    "order": [{"field": "actor", "dir": "desc"}]
  },
  "candidates": [
    {"warrant_id": "1111...", "actor": "a", "...": "..."},
    {"warrant_id": "2222...", "actor": "aa", "...": "..."}
  ],
  "expected": {
    "status": "selected",
    "selected_warrant": "2222...",
    "conflict_set": []
  }
}
```

Add a second vector with a non-ASCII actor or explicitly restrict actor strings
to a smaller grammar before allowing `actor` as an order key.

### P1: `select()` is not node-bound although section 4 defines candidates for `(node, jurisdiction)`

Book III section 4 says candidates are accepted active assertions for
`(node, jurisdiction)`. The oracle signature is:

```python
select(candidates, policy, jurisdiction, epoch)
```

It has no `node` argument and does not filter `assertion["node"]`. If callers
do not pre-filter perfectly, the oracle can select an assertion for a different
node.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, W

def cand(wid, node, epoch, amp):
    return {
        'warrant_id': wid * 64,
        'actor': 'actor',
        'ts': 1,
        'assertion': {
            'annotation': ASSERTION_TAG,
            'jurisdiction': J,
            'node': node,
            'epoch': epoch,
            'wave': W(0, amp, 0),
        },
    }

policy = {'federation_policy': 'sigma-glyph.selection@v1',
          'order': [{'field': 'epoch', 'dir': 'desc'}]}
node_a = 'aa' * 32
node_b = 'bb' * 32
res = select([cand('1', node_a, 1, 1), cand('2', node_b, 2, 2)], policy, J, 2)
print('selected_node=', res['selected']['assertion']['node'] if res['selected'] else None)
print('selected_warrant=', res['selected']['warrant_id'] if res['selected'] else None)
print('note= select() has no node argument; caller must have prefiltered for the node')
PY
```

Actual output:

```text
selected_node= bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
selected_warrant= 2222222222222222222222222222222222222222222222222222222222222222
note= select() has no node argument; caller must have prefiltered for the node
```

This can be repaired either by making the precondition normative or by making
the oracle enforce the spec. The latter is safer for a reference oracle.

Concrete code proposal:

```python
def select(candidates, policy, jurisdiction, node, epoch):
    ...
    if a["node"] != node:
        continue
```

Concrete text proposal:

```text
Selection inputs are the complete accepted assertion set visible to the
jurisdiction. The selection derivation MUST first discard any assertion whose
`node` is not the queried NodeHash and any assertion whose `jurisdiction` is
not accepted for the queried jurisdiction. The reference oracle's `select`
function takes the queried `node` as an explicit parameter.
```

Concrete vector proposal: add `FV-SELECT-NODE-FILTER` with one higher-ranked
foreign-node assertion and one lower-ranked queried-node assertion; expected
selection is the queried-node assertion.

### P1: Future-epoch exclusion is oracle law but not normative prose or vector-pinned

The oracle excludes assertions whose `assertion.epoch > current epoch`:

```python
if a["epoch"] > epoch:
    continue
```

That is the right rule, but Book III section 2 only says jurisdiction policy
defines epoch semantics and section 4 names accepted, active, non-stale
candidates. It does not explicitly say that assertions from the future are
inactive. An implementation that only applies `max_age_epochs` staleness could
select a future assertion under `epoch desc`.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, W

def cand(wid, epoch):
    return {
        'warrant_id': wid * 64,
        'actor': 'actor',
        'ts': 1,
        'assertion': {
            'annotation': ASSERTION_TAG,
            'jurisdiction': J,
            'node': 'cc' * 32,
            'epoch': epoch,
            'wave': W(0, epoch, 0),
        },
    }

policy = {'federation_policy': 'sigma-glyph.selection@v1',
          'order': [{'field': 'epoch', 'dir': 'desc'}]}
res = select([cand('1', 8), cand('2', 9)], policy, J, 8)
print('selected_epoch=', res['selected']['assertion']['epoch'] if res['selected'] else None)
print('selected_warrant=', res['selected']['warrant_id'] if res['selected'] else None)
print('note= oracle excludes epoch > current_epoch before ordering')
PY
```

Actual output:

```text
selected_epoch= 8
selected_warrant= 1111111111111111111111111111111111111111111111111111111111111111
note= oracle excludes epoch > current_epoch before ordering
```

Concrete text proposal:

```text
For a view at epoch E, an assertion with `assertion.epoch > E` is not live and
MUST be excluded before ordering. `max_age_epochs`, when present, is applied
after this future-epoch exclusion: an assertion is stale iff
`E - assertion.epoch > max_age_epochs`.
```

Concrete vector proposal: add `FV-SELECT-FUTURE-EXCLUDED`, with candidates at
epochs `8` and `9`, view epoch `8`, order `epoch desc`, expected selected
warrant = the epoch-8 assertion.

### P1: `quota_per_actor_epoch` is in the schema but its semantics are underspecified and surprising

Book III section 4 includes optional `quota_per_actor_epoch`, but the prose
does not define when it is applied, how candidates are grouped, or which
assertions survive the quota. The oracle applies quota before policy ordering,
groups by `(actor, assertion.epoch)`, sorts each live set globally by
`warrant_id`, and keeps the first `quota` items per group.

That choice is deterministic, but it is not derivable from the prose and it can
discard the assertion that the declared policy order would otherwise prefer.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, W

def cand(wid, actor, ts, epoch, amp):
    return {
        'warrant_id': wid * 64,
        'actor': actor,
        'ts': ts,
        'assertion': {
            'annotation': ASSERTION_TAG,
            'jurisdiction': J,
            'node': 'cc' * 32,
            'epoch': epoch,
            'wave': W(0, amp, 0),
        },
    }

policy = {
    'federation_policy': 'sigma-glyph.selection@v1',
    'order': [{'field': 'ts', 'dir': 'desc'}],
    'quota_per_actor_epoch': 1,
}
res = select([
    cand('1', 'same-actor', 100, 5, 100),
    cand('2', 'same-actor', 200, 5, 200),
], policy, J, 5)
print('selected_ts=', res['selected']['ts'] if res['selected'] else None)
print('selected_warrant=', res['selected']['warrant_id'] if res['selected'] else None)
print('note= quota keeps lower warrant_id before policy order, so later ts is discarded')
PY
```

Actual output:

```text
selected_ts= 100
selected_warrant= 1111111111111111111111111111111111111111111111111111111111111111
note= quota keeps lower warrant_id before policy order, so later ts is discarded
```

Concrete text proposal, if the current oracle behavior is intended:

```text
If `quota_per_actor_epoch = Q` is present, the selection derivation groups live
candidates by `(actor, assertion.epoch)`, sorts each group by `warrant_id`
ascending, keeps at most the first Q candidates from each group, and discards
the rest before applying the policy `order`. This quota is an anti-spam
pre-filter, not a trust ranking.
```

Concrete text proposal, if policy order should decide quota survivors:

```text
If `quota_per_actor_epoch = Q` is present, the selection derivation groups live
candidates by `(actor, assertion.epoch)`, sorts each group by the same
lexicographic `order` used for final selection with `warrant_id asc` appended
as a deterministic tiebreaker, keeps at most the first Q candidates from each
group, and discards the rest before final selection.
```

Pick one. The second is less surprising for policies that order by `ts desc` or
other freshness fields.

Concrete vector proposal: add `FV-QUOTA-ACTOR-EPOCH` with two same-actor,
same-epoch assertions and an order that would distinguish them. The expected
survivor must make the chosen quota semantics executable.

### P1: Section 2 allows authorized federated-peer roots, but the policy schema cannot express them and the oracle always rejects them

Section 2 says the selection policy must reject assertions whose embedded
`jurisdiction` does not equal the current genesis root "or an authorized
federated-peer root by policy." The policy schema has no such field, and
`validate_policy()` rejects unknown fields.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import validate_policy, J2

policy = {
    'federation_policy': 'sigma-glyph.selection@v1',
    'order': [{'field': 'epoch', 'dir': 'desc'}],
    'federated_peer_roots': [J2],
}
print('validate_policy=', validate_policy(policy))
PY
```

Actual output:

```text
validate_policy= policy has unknown fields
```

And the oracle rejects a foreign assertion outright:

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, J2, W

cand = {
    'warrant_id': '1' * 64,
    'actor': 'peer',
    'ts': 1,
    'assertion': {
        'annotation': ASSERTION_TAG,
        'jurisdiction': J2,
        'node': 'cc' * 32,
        'epoch': 1,
        'wave': W(0, 1, 0),
    },
}
policy = {'federation_policy': 'sigma-glyph.selection@v1',
          'order': [{'field': 'epoch', 'dir': 'desc'}]}
print(select([cand], policy, J, 1))
PY
```

Actual output:

```text
{'status': 'absent', 'selected': None, 'conflict_set': []}
```

This is a direct spec/oracle mismatch.

Concrete text proposal for v0.6 F1-strict:

```text
Selection policy MUST reject assertions whose `jurisdiction` does not equal
the genesis root of the current jurisdiction. Federated-peer root acceptance is
not part of the v0.6.0 policy schema and MUST be introduced, if needed, by a
future versioned policy tag with vectors.
```

Alternative concrete schema proposal:

```json
{
  "federation_policy": "sigma-glyph.selection@v1",
  "order": [...],
  "authorized_jurisdictions": ["<hex64 current root>", "<hex64 peer root>", ...]
}
```

If the alternative is chosen, `validate_policy()` must require a nonempty
array of unique lowercase hex64 roots and `select()` must accept assertions
whose embedded `jurisdiction` is a member of that array. Add both positive and
negative vectors.

## P2 findings and coverage gaps

### P2: `assertion_set_root` is an unsalted set commitment, not a privacy boundary that "reveals nothing"

Section 6 says `assertion_set_root` reveals nothing to parties that have not
independently obtained the warrants. The implemented root is:

```python
SHA-256(JCS(sorted(warrant_ids)))
```

That hides the literal list, but it is deterministic and unsalted. If the
candidate universe is small or guessable, a third party can enumerate subsets
and recover the active set.

Command:

```bash
python3 - <<'PY'
import itertools, sys
sys.path.insert(0, 'impl')
from sigma_federation import assertion_set_root

universe = ['1' * 64, '2' * 64, '3' * 64]
secret = ['1' * 64, '3' * 64]
root = assertion_set_root(secret)
print('root=', root)
for r in range(len(universe) + 1):
    for subset in itertools.combinations(universe, r):
        if assertion_set_root(list(subset)) == root:
            print('recovered_subset=', list(subset))
PY
```

Actual output:

```text
root= d1646bbd02652e2f23b2d2f0c70c6ff97415e504f7886694c9db81292d3094d5
recovered_subset= ['1111111111111111111111111111111111111111111111111111111111111111', '3333333333333333333333333333333333333333333333333333333333333333']
```

This is P2 because it is a security/privacy overclaim, not a selection
divergence.

Concrete text proposal:

```text
`assertion_set_root` is a deterministic set commitment:
SHA-256(JCS(array of active WarrantIDs sorted lexicographically by lowercase
hex)). It omits the plaintext `active_assertions` list from projection
metadata, but it is not a zero-knowledge privacy boundary: observers who know
or can guess a small candidate universe can test subsets offline. Jurisdictions
requiring stronger privacy MUST use encrypted subject blobs and/or a future
private-set-commitment profile; such profiles are outside v0.6.0.
```

Also stop calling the current construction a Merkle root unless it is changed
to a real Merkle tree. "Set commitment" is accurate.

### P2: ViewID is a coordinate, not a content identity; same ViewID can have different active sets within an epoch

`AnnotationViewID` includes jurisdiction, node, policy hash, and epoch. It
intentionally excludes active assertions. That is good for avoiding plaintext
graph leakage, but the prose should not imply that the ViewID alone identifies
the full derived content. Within the same epoch, newly settled, superseded, or
revoked assertions can change `wave_fed` and `assertion_set_root` while the
ViewID remains the same.

Concrete text proposal:

```text
AnnotationViewID names the jurisdiction/policy/node/epoch coordinate of a
view. It is not by itself a content hash of the active assertion set. A
verifiable projection is identified by `(AnnotationViewID, assertion_set_root)`
plus the policy hash and proof material needed to audit selection. Clients that
cache effective waves MUST invalidate or revalidate the cached value whenever
the settlement-active assertion set for that coordinate changes.
```

Epoch granularity is sufficient only if this distinction is explicit.

### P2: Direct assertion on an APPLY node is implemented but not vector-pinned

Section 5 says a direct assertion on `APPLY(f,a)` overrides structural
derivation. The oracle implements this by checking `resolve_selection(term)`
before recursing, but the vector file only pins leaf assertion-over-pin and
structural fallback.

Command:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import wave_fed, ASSERTION_TAG, J, W

term = ['APPLY', 'K', 'I']
sel = {'status': 'selected', 'selected': {'assertion': {
    'annotation': ASSERTION_TAG,
    'jurisdiction': J,
    'node': 'cc' * 32,
    'epoch': 1,
    'wave': W(1, 2, 3),
}}, 'conflict_set': []}
print(wave_fed(term, lambda t: sel if t == term else None))
print('structural_without_assertion=', wave_fed(term, lambda t: None))
PY
```

Actual output:

```text
{'ph': 1, 'am': 2, 'en': 3}
structural_without_assertion= {'ph': 32768, 'am': 0, 'en': -32512}
```

Concrete vector proposal: add `FV-WAVE-APPLY-ASSERTION-OVERRIDES-STRUCTURAL`,
with direct selected assertion wave `{ph:1, am:2, en:3}` on `["APPLY","K","I"]`
and expected effective wave equal to that assertion, not Book II FALSE
derivation.

### P2: The conformance suite does not yet satisfy Book III's own "MUST contain" coverage

Book III section 7 criterion 1 says the suite MUST contain a vector proving an
arbitrary annotation store does not change any Book I eval result. The current
federation vector set contains validation, selection, wave, ViewID,
set-root, and fold-unsound vectors, but no eval-with-annotation-store vector.

Concrete vector proposal:

```json
{
  "id": "FV-BOOK-I-UNREACHABLE",
  "kind": "eval_ignores_annotation_store",
  "term": "<same fixture as EV-TV4-IK or EV-TV5-SKKI>",
  "annotation_store": [
    {"node": "<term node>", "wave": {"ph": 1, "am": 2, "en": 3}},
    {"node": "<child node>", "wave": {"ph": 4, "am": 5, "en": 6}}
  ],
  "expected_eval": "<exact Book I result/disposition/spent from existing vector>"
}
```

If the Book I reference runner will never accept annotation-store inputs, the
vector can be a harness assertion that runs the same Book I vector before and
after constructing arbitrary federation candidates and compares byte-identical
eval outputs.

### P2: Field domains for candidate metadata should be closed when a policy can sort on them

Assertion blobs are closed and range-checked. Policy blobs are closed and
range-checked. Candidate metadata consumed by policy order (`warrant_id`,
`actor`, `ts`) is not validated by the oracle. It assumes Warrant has already
supplied well-formed fields, but Book III is the document that makes them
selection inputs. At minimum, Book III should state the imported Warrant field
domains:

```text
Before ordering, implementations MUST reject or ignore candidates whose
selection metadata is malformed: `warrant_id` is lowercase hex64, `actor` is
the exact Warrant actor string after Warrant validation, and `ts` is a JSON
uint64. Candidate records with missing or ill-typed order fields are not live
for Book III selection.
```

Add `FV-SELECT-BAD-METADATA-REJECTED` or explicitly declare this validation to
be a Warrant-layer precondition outside the oracle.

## Vector coverage checklist

Currently pinned:

- Assertion closed schema: yes.
- Complete wave only: yes.
- Policy closed schema and bad order field: yes.
- Latest epoch and warrant-id tiebreak: yes.
- Foreign jurisdiction rejected: yes, but only for the no-peer-root model.
- ConflictSet tie: yes.
- Staleness by `max_age_epochs`: yes.
- Leaf assertion overrides Book II pin: yes.
- Structural Book II fallback: yes.
- ViewID deterministic formula: yes.
- Assertion set root order-insensitive: yes.
- `interfere()` fold unsoundness: yes.

Missing or insufficient:

- `actor desc` prefix ordering and Unicode/non-ASCII behavior.
- Node filtering in selection.
- Future-epoch exclusion.
- `quota_per_actor_epoch` survivor semantics.
- Direct assertion on APPLY-node override.
- Book I unreachable under arbitrary annotation store.
- Foreign federated-peer roots, unless the phrase is removed from v0.6.
- Candidate metadata type/domain failures.
- ViewID plus changed `assertion_set_root` within same epoch.
- Superseded settlement-active warrant exclusion, likely as a Warrant-layer
  integration vector rather than a pure `sigma_federation.py` vector.

## Determinism criteria

With the P1 fixes above, the deterministic core can be made adequate. As
written, two conforming implementations can disagree on vector-class outcomes
in these ways:

- A prose-following implementation may compare `actor desc` directly and select
  `"aa"` over `"a"`; the oracle selects `"a"`.
- A Unicode-capable implementation may handle actor strings beyond U+00FF; the
  oracle raises.
- An implementation may select future assertions because future exclusion is
  not a normative MUST.
- An implementation may apply `quota_per_actor_epoch` after policy ordering,
  before policy ordering, by `ts`, by `warrant_id`, or per `(actor,node,epoch)`;
  the prose does not decide.
- An implementation may accept authorized federated peer roots because section
  2 says they exist; the oracle and schema cannot.
- An implementation may assume `select()` receives a full warrant store and
  filters by node; the oracle assumes pre-filtered candidates.

JCS itself is not the immediate problem for the current vectors. The larger
determinism risk is that candidate metadata collation, quota preprocessing,
future liveliness, and node scope are not all normatively pinned.

## Relative to prior reviews

I formed the findings above from `reviews/README.md`, the required command
runs, and the primary Book III/oracle/vector texts before reading prior
reviews. After that, I searched and opened the ADR-006 gate reviews.

Commands:

```bash
rg --files reviews
rg -n "Book III|book-3|federation|quota_per_actor_epoch|federated-peer|assertion_set_root|actor.*desc|chr\\(255|ViewID|future" reviews
sed -n '1,260p' reviews/2026-07-codex-adr006-gate.md
sed -n '1,260p' reviews/2026-07-gemini-adr006-gate.md
sed -n '1,260p' reviews/2026-07-kimi-adr006-gate.md
```

Agreement:

- I agree with Gemini, prior Codex, and Kimi that F1 selection-only is the
  correct settlement-grade architecture and that `interfere()` must not merge
  independent assertions.
- I agree with Kimi that `active_assertions` must not appear directly in
  ViewID/plain projection metadata and that policy must be machine-readable,
  not a string rule id.
- I agree with the ADR-006 settlement recorded in `reviews/README.md`:
  F1-strict, no protocol-level arithmetic score profiles.

Disagreement or refinement:

- Kimi's privacy direction is right, but Book III's current phrase that
  `assertion_set_root` reveals nothing is too strong. The current deterministic
  unsalted set commitment is enumerable for small candidate universes.
- Prior ADR-006 reviews were conceptual. This gate needs to treat the oracle as
  executable law. The `actor desc` prefix case is a concrete oracle bug, not a
  conceptual objection to federation.

New relative to prior reviews:

- Concrete counterexample for `select()` descending string order.
- Concrete totality failure for non-ASCII actor strings above U+00FF.
- Concrete `select()` node-scope mismatch.
- Concrete future-epoch prose/oracle gap.
- Concrete `quota_per_actor_epoch` semantics gap with observable selected
  assertion change.
- Concrete federated-peer-root prose/schema mismatch.
- Concrete `assertion_set_root` rainbow example.
- A vector coverage checklist for the implementation gate.

