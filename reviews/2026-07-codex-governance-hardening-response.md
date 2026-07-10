# Response: Codex governance-layer hardening audit — 2026-07-10

Interim maintainer adjudication (drafted in-session; **pending roster co-sign** —
the vector/mechanism changes below are a governed release, not yet adopted).

Codex ran adversarial probes *outside* the published matrix and reported 3 P0,
2 P1, 2 P2 against the governance layer. Books I/II/III oracles, all conformance
suites, differentials, anchors and Lean bridges were green before and remain
green after — the findings live entirely in the ADR-007 anchor-governance
verifier and its Go twin. Each was reproduced against the actual repo before
acting.

Disposition summary:

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 1 | P0 | First policy rotation invalidates all prior history (liveness) | **Accepted — open.** MAJOR (@v2) redesign; design below. Not implemented. |
| 2 | P0 | Python vs Go build settlement closure differently (malformed bridge) | **Fixed.** |
| 3 | P0 | Go accepts trailing JSON that Python rejects | **Fixed.** |
| 4 | P1 | JCS canonicality claimed but not checked | **Fixed** (anchor layer); Book III noted below. |
| 5 | P1 | Book III not end-to-end at Warrant level | **Accepted — open** (already honestly open in ROADMAP); design below. |
| 6 | P2 | Local "complete matrix" ≠ CI | **Fixed.** |
| 7 | P2 | Documentation drift | **Fixed.** |

All reproductions used the fixed-seed fixtures already in
`tools/anchor_governance.py`.

---

## Fixed this round (F2, F3, F4, F6, F7)

### F2 — settlement closure now id-gated (P0)

`settlement_closure()` in `tools/anchor_governance.py` added any JSON record
whose `body.prior` touched the closure **without** checking that the filename
WarrantID equals `sha256(canon(body))`. A forged intermediate record therefore
made an otherwise-unreachable foreign adoption reachable in Python, while Go
(which gates every hop on `soundRecord()`) refused it. Probe:
`malformed record in Python closure: True`.

Fix: a new `_sound_body(env, rid)` helper gates both the root and every hop —
an id-unsound record is litter, not a graph node. This brings Python to Go
parity. All 17 legitimate vectors regenerate byte-identically (the real chain
uses only sound records); locked by new vector **`GV-MALFORMED-BRIDGE-IGNORED`**.

### F3 — Go decoder now requires EOF (P0)

`parseJSONBlob()` in `impl-go/main.go` called `Decode()` once and ignored
trailing bytes, so `<object> true` authorized in Go but not in Python. Fix: a
second `Decode` into `json.RawMessage` must return `io.EOF`. Locked by new
vector **`GV-TRAILING-JSON-REJECTED`** (Python already rejected via
`json.loads`; the vector guards the Go side against regression).

### F4 — JCS canonicality now enforced on the wire (P1)

Both `parse_json_blob()` (Python) and `parseJSONBlob()` (Go) validated the
*parsed* value, never comparing raw bytes to `canon(doc)`. A pretty-printed
(non-JCS) anchor-set blob authorized cleanly. Probe:
`pretty-printed anchor-set authorized: True`. Fix: both implementations now
require the raw blob bytes to equal the re-canonicalization of the parsed
value, which also rejects duplicate-key and non-minimal encodings. Locked by
new vector **`GV-NONCANONICAL-BLOB-REJECTED`**. Scoped to store blobs only —
the out-of-band trust config is human-edited and is **not** subject to this
check.

> **Book III residue (F4, second half):** `validate_assertion()` /
> `validate_policy()` in `impl/sigma_federation.py` are pure functions over
> already-parsed dicts by construction (the oracle takes no raw bytes — Warrant
> owns ingestion). Enforcing canonicality there belongs to the settlement
> integration layer (F5), not the selection oracle. Tracked under F5, not
> patched in the oracle.

### F6 — one matrix, called by both CI and the local wrapper (P2)

`tools/test-all.sh` claimed "complete validation matrix" but omitted four CI
surfaces. Added: vector-regeneration freshness (implemented as the stronger,
commit-state-independent "regeneration is a no-op on the working tree"), the
Book III two-jurisdictions live demo, and network-gated blocks for
`status --enforce` (out-of-band anchor trust) and the settlement-grade Warrant
CLI — the latter two skip cleanly offline so the local matrix stays runnable
without network, and run for full CI parity when reachable.

### F7 — documentation drift (P2)

- `README.md`: GOV-anchors.md `v1.0.0` → **`v1.0.1`** (matches the document).
- `ROADMAP.md`: stale `## Current: v0.5.0` retitled to a milestone entry with a
  pointer to the current **v0.6.5** bundle; its two "Known limitations" marked
  closed by the v0.6 Federation + Governance releases.
- `tools/anchor_governance.py` docstring: `PROPOSED, rev 2` → **ACTIVE**
  (GOV-anchors.md 1.0.1), which is the true state since v0.6.2.

---

## Accepted but NOT implemented (need a roster/version decision)

### F1 — policy rotation invalidates history (P0, liveness) → **MAJOR (@v2)**

Root cause (confirmed): `verify_adoption()` calls `derive_current_profile()`,
which walks to the single **terminal** profile of the whole store, then
`cmd_status` re-verifies *every* live release and demands each historical
adoption's `under` cite that terminal `(profile, threshold)` pair
(`anchor_governance.py` ~L374/L406). After one legitimate rotation, every
pre-rotation release fails `_under_is`. Probe:

```
old/genesis set after policy rotation: False
new/successor set after policy rotation: True
```

So `status --enforce` can never again re-verify the full chain across a
rotation — the mechanism self-limits to one policy epoch.

**Why not patched here:** the fix changes the frozen `@v1` verification
semantics — it is a MAJOR change requiring a new schema epoch, a second
3-family gate (per the Decision Process), and roster re-adoption. Proposed
design, for the ADR:

1. **Causal-past policy resolution.** Resolve the governing `(profile,
   threshold)` for a release-adoption `W` from *W's own causal past* (the
   latest authorized profile-adoption reachable through `W.prior`), not from
   the store's terminal profile. An adoption stays valid under the policy that
   was in force when it was filed.
2. **Explicit dependency.** Require a release-adoption to depend, via `prior`,
   on the profile-adoption it is filed under, so the causal link is a store
   fact, not an inference.
3. **Full-chain transition vector.** Add a governance vector that rotates the
   policy *and then* re-verifies the whole live chain (old + new releases both
   AUTHORIZED) — the regression the current suite structurally cannot express,
   because no scenario re-verifies a historical release post-rotation.

This preserves every existing single-epoch guarantee (competing-successor
freeze, lineage authorization, key-state refusal) while making the chain
re-verifiable across arbitrarily many rotations.

### F5 — Book III not end-to-end at the Warrant level (P1) → **integration layer**

`select()` operates only over a caller-supplied accepted set
(`sigma_federation.py` L116); `examples/two-jurisdictions/demo.py` takes every
well-formed `accept` as live with no threshold / key-state / supersede /
settlement filtering (L109). So the Book III criteria on *revocation soundness*
and *O(Δ warrants) incremental verification* are exercised by neither
implementation. This is **already honestly open** in `ROADMAP.md` ("settlement-
grade candidate extraction in the demo") — Codex is right that the promised
integration vector has not landed.

Proposed design, for the ADR / roadmap item (not this round):

- A settlement-active candidate extractor that derives the live assertion set
  from a real Warrant store: quorum over the citing policy, current key-state,
  supersede/revocation, and settlement-closure scoping — mirroring what the
  anchor-governance verifier already does for anchors, then feeding `select()`.
- A Go/Python differential over that extractor, plus a revocation-soundness
  vector and an incremental-verification (Δ-warrants) vector.
- Canonicality enforcement (F4) applied at this ingestion boundary, where raw
  bytes first enter.

---

## Release note — re-anchoring required

The three added adversarial vectors change the **anchored**
`tests/spec_conformance/governance_vectors.json` (17 → 20 vectors). Its pin in
`spec/ANCHORS.txt` (`4957a77d…`) therefore no longer matches, so
`verify_anchors.py` and `status --enforce` fail by design until the roster mints
a new anchored release. New content hash:

```
2ab354b4ede71cc4d9a28429649761073c973a3a7ee0725e9e1f20c3315c2a30  tests/spec_conformance/governance_vectors.json
```

Every other surface is green with the changes in place: Book I/II/III oracles,
49/49 Rust, federation-GO 21/21, governance-GO **20/20**, federation-diff 40/40,
governance-diff **27/27**, Book III live demo, 46 adjudication warrants, Lean
bridges. Working tree left **uncommitted** for the co-sign / re-adopt / version
step.
