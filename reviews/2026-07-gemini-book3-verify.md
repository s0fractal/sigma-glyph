# Implementation-gate verification: Book III federation v0.6.0-draft

Reviewer: Gemini 3.1 Pro (High), independent adversarial implementation-gate verification pass

Scope: `spec/book-3-federation.md`, `impl/sigma_federation.py`, `tests/spec_conformance/federation_vectors.json`

## Verdict

The draft is ready to ANCHOR at v0.6.0. The fixes for Codex's round 1 implementation-gate findings are robust, and no new blocking defects were found in the revised mechanics. There is one minor P2 finding regarding whitespace in actor strings, but it is not a conformance blocker.

## Verified-vectors statement

Per `reviews/README.md`, I ran the required commands before reviewing the primary texts.

Command:
```bash
python3 impl/sigma_glyph.py
```
Actual output observed:
```text
ALL PASS
```

Command:
```bash
python3 tests/spec_conformance/run_reference.py
```
Actual output observed:
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

I also checked the federation vectors replay byte-exactly and that regenerating them is a no-diff operation.

Command:
```bash
python3 impl/sigma_federation.py gen && git diff tests/spec_conformance/federation_vectors.json
```
Actual output:
```text
wrote federation_vectors.json: 21 vectors
```
The diff output was empty, confirming regeneration is a no-diff operation.

## Own Findings and New Code Paths Attack

Before reading the prior Codex review, I audited the code against the prose.

### Attack 1: `cmp_to_key` mixed-type fields and stability
The use of `functools.cmp_to_key` combined with `_cmp_order` handles string ordering strictly by Unicode scalar values as Python's native string comparison operations `<`/`>` perform lexicographic collation. Because candidate selection metadata types are strictly pre-filtered by `_valid_metadata` and `validate_assertion`, there is no risk of `TypeError` from mixed-type comparisons (e.g. `int` vs `str`) inside `_cmp_order`. Sorting is completely stable due to the final `warrant_id asc` tie-breaker. This code path is sound.

### Attack 2: `quota_per_actor_epoch` tie_order grouping
The quota logic groups by `(actor, assertion.epoch)` and limits each group to `Q` elements. By applying `tie_order` to the `g.sort()` call before taking the slice `[:quota]`, it correctly ensures that the quota survivors are those highest-ranked by the final policy itself (since `tie_order = order + [{"field": "warrant_id", "dir": "asc"}]`).

### Attack 3: Metadata validation edge cases
I checked whether the `ts` field would evaluate as malformed when `ts=0` (due to falsy truth values). The oracle delegates to `_is_uint`, which correctly passes `0`.

Command:
```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'impl')
from sigma_federation import select, ASSERTION_TAG, J, W

def cand(wid, ts):
    return {
        'warrant_id': wid * 64,
        'actor': 'actor',
        'ts': ts,
        'assertion': {
            'annotation': ASSERTION_TAG,
            'jurisdiction': J,
            'node': 'cc' * 32,
            'epoch': 1,
            'wave': W(0, 1, 0),
        },
    }

policy = {'federation_policy': 'sigma-glyph.selection@v1',
          'order': [{'field': 'ts', 'dir': 'desc'}]}
res = select([cand('1', 0)], policy, J, 'cc'*32, 1)
print('selected_warrant_ts0=', res['selected']['warrant_id'] if res['selected'] else res['status'])
PY
```
Actual Output:
```text
selected_warrant_ts0= 1111111111111111111111111111111111111111111111111111111111111111
```

I also checked whether an actor name consisting only of whitespace is considered valid by the oracle:

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
res = select([cand('1', '   ')], policy, J, 'cc'*32, 1)
print('selected_warrant_whitespace=', res['selected']['warrant_id'] if res['selected'] else res['status'])
PY
```
Actual Output:
```text
selected_warrant_whitespace= 1111111111111111111111111111111111111111111111111111111111111111
```

The string `"   "` evaluates to Truthy under `_valid_metadata`, making it a valid "non-empty" string. Book III only specifies "непорожній Warrant-рядок актора" (non-empty Warrant-string). See the minor P2 finding below regarding whether this should be more strictly defined.

### Audit of Spec s4 Derivation Order (Steps 1-6)
I verified the reference oracle (`select()`) step-by-step against the 6 steps outlined in Section 4.

1. **Discard malformed metadata and invalid assertions**: Handled precisely via `_valid_metadata` and `validate_assertion`.
2. **Discard by `node` filter**: Handled explicitly by `if a["node"] != node: continue`.
3. **Discard by `jurisdiction` check**: Handled by `if a["jurisdiction"] != jurisdiction: continue`.
4. **Future not live & Staleness**: Handled exactly via `if a["epoch"] > epoch:` before checking `max_age_epochs`.
5. **Quota**: Grouped by `(actor, assertion.epoch)`, sorted by `tie_order`, and clamped by `quota`.
6. **Tie-break and ConflictSet**: Determined by finding all elements matching `live[0]` under the base `order`.

The code matches the 6 steps seamlessly. There is no divergence.

## Relative to Prior Codex Review

I have confirmed that all P1 and P2 findings from Codex's round 1 implementation-gate pass (`reviews/2026-07-codex-book3-gate.md`) have been soundly fixed:

1. **`actor desc` prefix pair / non-ASCII**: Confirmed fixed. Replaced `chr(255 - ord(c))` with lexicographic `cmp_to_key` comparator which handles prefix inversions and non-ASCII characters natively and cleanly.
2. **Node-bound selection**: Confirmed fixed. `node` is now an explicit parameter of `select()` and filtered internally.
3. **Future-epoch exclusion**: Confirmed fixed. Prose and oracle both explicitly evaluate `epoch > view_epoch`.
4. **`quota_per_actor_epoch` semantics**: Confirmed fixed. Semantics explicitly defined to use the *same* `order` as the policy with `warrant_id asc` tie-breaker.
5. **Peer-root policy rejection**: Confirmed fixed. The prose defers peer-root inclusion to a future version, and the code asserts strict equality with the current genesis root.
6. **P2 documentation and coverage**: Confirmed all vectors were added (`FV-BOOK-I-UNREACHABLE`, `FV-WAVE-APPLY-ASSERTION-OVERRIDES-STRUCTURAL` -> `FV-WAVE-APPLY-ASSERTION-OVERRIDES`, etc.).

I agree with Codex's original findings, and I agree with the maintainer's implemented fixes in the current branch.

## New Findings

### P2: "Non-empty" actor strings include whitespace-only strings

The spec states: `actor — непорожній Warrant-рядок актора` (non-empty Warrant-string). The oracle's implementation `isinstance(c.get("actor"), str) and c["actor"]` rejects zero-length strings (`""`), but accepts whitespace-only strings (`"   "`). If the intent is that whitespace-only actor identifiers should also be rejected, the prose and oracle should explicitly demand stripping or pattern matching. However, as it stands, it follows JSON string constraints properly and is not a conformance blocker.

**Concrete text proposal**:
If you wish to enforce that actor strings cannot be purely whitespace, update Book III §4:
```text
actor — непорожній Warrant-рядок актора (який містить принаймні один непробільний символ)
```
And the implementation:
```python
and isinstance(c.get("actor"), str) and c["actor"].strip()
```
Otherwise, leave it as is; this is not a blocker.
