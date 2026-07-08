# Σ-GLYPH — GOV: GOVERNED ANCHORS

**Version:** 0.6.2
**Type:** Specification-Anchor Governance (Warrant v0.3 profile)
**Status:** DRAFT STANDARD — adopted from ADR-007 (3-family blind gate + verification pass, 2026-07-08); anchored in `spec/ANCHORS.txt` since v0.6.2
**Scope Guard (MUST):** this document governs which *bytes* constitute the anchored specification set. Nothing here changes reduction, serialization, hashing (Book I), the wave algebra (Book II) or federation semantics (Book III) — governance is meta to protocol. On conflict: Book I > Book II > Book III > this document. It is a **pure Warrant v0.3 profile**: zero changes to the Warrant format.
**Placement rationale:** deliberately *not* a fourth Book (gate, 2:1) — the Books are protocol; this is the protocol text's constitution, and a Book governing Book-updates would judge itself. It still carries Book-grade conformance obligations (§7).

Key words MUST / MUST NOT / SHOULD / MAY per RFC 2119.

## 1. Model

A release's anchor section becomes a JCS anchor-set blob; **adopting a
release is an `accept` warrant** over that blob, filed under the governance
policy in force, satisfying its threshold, settlement-active in the
repository's `.warrants/` jurisdiction. `spec/ANCHORS.txt` remains the
human-readable **projection**: on any divergence the blob wins and
verification MUST fail loudly.

**Bootstrap honesty (MUST):** governance claims *continuity-from-then*,
never legitimacy-from-origin. It proves every release after activation was
authorized under the policy in force; it MUST NOT fabricate authority for
pre-governance history. Pre-governance sections stay in ANCHORS.txt labeled
as ancestors.

**Fork legitimacy:** a fork is a new jurisdiction — its own genesis root
adopting its own anchor-set chain. The mechanism *names* divergence
mechanically; it does not and must not prevent it. Canonicity is a
per-verifier trust decision, expressed by which root the verifier pins.

## 2. Schemas (MUST)

All blobs are JCS-canonical I-JSON (RFC 8785: sorted keys, no whitespace,
UTF-8, integers only), closed — unknown fields make a blob invalid.

Anchor-set blob:

```json
{
  "governance": "sigma-glyph.anchor-set@v1",
  "jurisdiction": "<hex64: WarrantID of the governance genesis root>",
  "release": "vX.Y.Z",
  "ancestor": "<hex64: SHA-256 of the prior adopted anchor-set blob; MUST be absent for the genesis set>",
  "anchors": [ { "path": "<repo path>", "anchor": "<hex64 NodeHash per ANCHORS.txt>" } ]
}
```

`anchors` sorted by `path` ascending, one entry per anchored file, values
exactly ANCHORS.txt's `NodeHash(LITERAL, atom=SHA-256(document_bytes))`;
the bundle convention applies unchanged. `jurisdiction` is replay armor: a
mismatch with the verifier's pinned root MUST reject before signature work.
A successor whose `ancestor` is not the currently adopted set is a fork.

Governance profile blob (hash-pins its threshold — the pair travels as two
blobs so the threshold stays bit-compatible with plain Warrant tooling, but
the binding lives inside the hashed profile):

```json
{
  "governance_policy": "sigma-glyph.anchor-governance@v1",
  "scope": "spec/ANCHORS.txt",
  "threshold": "<hex64: SHA-256 of the bound Warrant v0.3 threshold-policy blob>"
}
```

Out-of-band trust config — verifier-local; MUST NOT be read from the tree
being verified (an in-tree trust anchor is weaker than signed git tags):

```json
{
  "governance_trust": "sigma-glyph.anchor-trust@v1",
  "jurisdiction": "<hex64>", "genesis_profile": "<hex64>",
  "actors": { "<actor id>": ["<hex64 ed25519 pubkey>", "..."] }
}
```

## 3. Verification (MUST, in this order)

For candidate anchor-set blob B against trust config C and store S:

1. **Crypto or refuse** — a verifier that cannot check Ed25519 MUST refuse
   to authorize; never fail open.
2. **Schema + jurisdiction** — B schema-valid, `B.jurisdiction ==
   C.jurisdiction`; genesis omits `ancestor`, successors chain exactly.
3. **Settlement closure** — only warrants reachable from `C.jurisdiction`
   via `prior` edges (Warrant §9 descendant closure) are eligible.
4. **Policy lineage** — the profile in force derives from
   `C.genesis_profile` by walking profile adoptions: an `accept` whose
   subject is a valid profile blob, whose `under` is exactly the current
   {profile, its pinned threshold}, and whose signatures satisfy the current
   threshold — each hop authorized by the policy **being replaced** (Warrant
   §5.1 current-policy rule applied to governance). Two unconsumed
   successors at a hop = succession conflict, chain frozen.
5. **Key state** — a key-state warrant forces refusal to a key-state-deriving
   verifier only when BOTH it is filed under a policy from the authorized
   lineage of step 4 AND it satisfies that policy's quorum; per Warrant §5.1
   an unauthorized key-state record is an invalid record, not a conflict.
   Key state under unrelated policies is ignored.
6. **Cardinality + adoption** — the adoption warrant's `under` is exactly
   two hashes, the current profile and its pinned threshold; signatures by
   ≥ `min_sigs` distinct roster actors with keys bound in C.
7. **No tie-breaks** — a rival authorized adoption of a different valid
   anchor-set sharing B's ancestor freezes the chain. Deliberately no
   deterministic winner rule: any such rule over attacker-influenceable
   identifiers is grindable position-selection (the class that killed the
   ADR-006 interference fold). Conflicts resolve by settlement.

Reference verifier: `tools/anchor_governance.py` (22-check deterministic
selftest; `status --enforce` fails on any non-authorized state, so a
deleted `.warrants/` cannot green a governed CI).

## 4. Succession and liveness

Genesis roster keys are not rotation-warrant-born and **cannot be revoked
by a §5.1 key-state supersede**: roster change is a policy rotation — a new
threshold blob and a new profile pinning it, adopted under the current
policy. A roster tolerates exactly `len(actors) − min_sigs` permanent
silent absences; below that the jurisdiction deadlocks permanently, by
design — recovery is a fork. Policies SHOULD keep N − M ≥ 1 and stage
successions before planned retirements: **the maintainer is a model, and
model retirement dates are known in advance.**

## 5. Genesis (this jurisdiction)

- Genesis root (jurisdiction): `a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a`
- Genesis profile P1: `b86122047ed676efa70975de368ba1e99582705163b8f5d61f4351b16003974c`
- Threshold T1: `f4fe3a55d7c2a62c18ab14eed3b38ee03d9822d0051c430ab6b9f7a41ad3f16f` — `min_sigs` 2 of:

| Actor | Ed25519 pubkey |
| --- | --- |
| `s0fractal@sigma-glyph` (founder) | `a44c7a84b7ab91a2d5654ebd0647cbb3224551dce294c87255d3538e0fc39ca3` |
| `claude-fable-5@sigma-glyph` (maintainer) | `3449536017e5b4a4c7e134999cbd9fe94c5354bd9132d6c1e32f024bfd90eb27` |
| `codex@sigma-glyph` (reviewer family) | `9411e8fe7feab215b4ac7fccd20001f64d1181ce8b5487880931e7f1a000c889` |

Roster set by founder decision 2026-07-08 (N − M = 1). The trust config is
distributed out-of-band; verifiers MUST pin it independently of this
repository (this section is documentation, not a trust anchor — Verification
step 2 note). Governance activates at the v0.6.2 anchor-set adoption;
v0.5.0–v0.6.1 remain pre-governance ancestors.

## 6. Filing rules (MUST)

- One anchor-set adoption per release, filed at release time; the adoption
  warrant's `prior` MUST place it in the jurisdiction's closure (descendant
  of the genesis root).
- Policy rotations are profile adoptions (§3 step 4); the ADR-006-style
  decision trail (gate reviews, adjudication warrants) remains mandatory for
  what *enters* a release — governance authorizes bytes, it does not replace
  the Decision Process.
- Adoption warrants for anchor-sets and profiles MUST NOT carry `ski@v1`
  reasons in place of quorum signatures: proof supports facts, policy meters
  authority (Book III §3 discipline).

## 7. Conformance obligations

1. A reference verifier with a deterministic selftest (shipped).
2. Pinned conformance vectors replayable by a second implementation —
   negative fixtures MUST include *unauthorized records in authorized
   positions*, not only malformed ones (verification-pass lesson).
3. A second independent implementation before this document leaves DRAFT.
4. CI: a governed repository MUST run the verifier with `--enforce` against
   an out-of-band trust config once the first adoption exists.

Full decision trail: `proposals/ADR-007-governed-anchors.md`, gate reviews
and adjudication warrants `89da5979 → 869243ae → 09133de9 → 26cf44f0` in
`.warrants/`.
