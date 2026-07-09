# Σ-GLYPH — GOV: GOVERNED ANCHORS

**Version:** 1.0.1
**Type:** Specification-Anchor Governance (Warrant v0.3 profile)
**Status:** STANDARD — the first STANDARD in the project. Adopted from ADR-007 (3-family blind gate + verification pass), promoted from DRAFT STANDARD by the v0.6.4 governed release after a second 3-family gate on the promotion itself (Gemini 3.1 Pro, GPT-5, DeepSeek v4 Pro, 2026-07-08 — verdict unanimous PROMOTE-WITH-AMENDMENTS; all P0/P1 integrated below). **1.0.1 (v0.6.5 bundle):** three §3 prose clarifications from the Kimi focused formal review — zero behavioral change (the reference verifier already behaves as each specifies, all 17 vectors unchanged), so a SemVer PATCH, not a new schema tag. Anchored in `spec/ANCHORS.txt` since v0.6.2. The document version is independent of the repo bundle version, per the ANCHORS bundle convention.
**Normative dependencies (pinned — MUST):** a STANDARD MUST NOT rest on a moving target (promotion gate P1, 3/3). This profile is defined against **Warrant SPEC v0.3** exactly as pinned in [`proposals/refs/warrant-SPEC-v0.3-snapshot.md`] — content SHA-256 `73758bdb735912709a0b6280b6c6e8b32cd3f99e31004bee2bed147d9d87cd8e` — authoritative for settlement (§7), key state (§5.1) and multi-root stores (§9) as used here; and against **Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1** as anchored in this release (the anchor definition `NodeHash(LITERAL, SHA-256(bytes))` rides Book I's hashing). Implementations MAY track later dependency versions only where these exact semantics are preserved; any change is a breaking change to this STANDARD (§0).
**Scope Guard (MUST):** this document governs which *bytes* constitute the anchored specification set. Nothing here changes reduction, serialization, hashing (Book I), the wave algebra (Book II) or federation semantics (Book III) — governance is meta to protocol. On conflict: Book I > Book II > Book III > this document. It is a **pure Warrant v0.3 profile**: zero changes to the Warrant format.
**Placement rationale:** deliberately *not* a fourth Book (gate, 2:1) — the Books are protocol; this is the protocol text's constitution, and a Book governing Book-updates would judge itself. It still carries Book-grade conformance obligations (§7).

Key words MUST / MUST NOT / SHOULD / MAY per RFC 2119.

## 0. Status and Stability (STANDARD)

This document bears the label **STANDARD**. That label is a commitment, not
decoration (promotion gate P1, 3/3 — "a label without a defined bar is
ceremony"):

- **Frozen schemas.** `sigma-glyph.anchor-set@v1`,
  `sigma-glyph.anchor-governance@v1` and `sigma-glyph.anchor-trust@v1` (§2)
  are frozen. A change that would make a conforming verifier accept or reject
  differently, or that alters a schema's shape, MUST ship as a new tag
  (`@v2`), with a fresh §7 conformance suite and its own governed adoption —
  never as a silent edit to a `@v1`.
- **Frozen mechanism.** The seven-step verification procedure (§3) is frozen.
  Any behavioral change requires a new profile/tag and vectors.
- **Backward compatibility.** A verifier implementing this STANDARD MUST keep
  accepting blobs valid under it; unknown schema versions MUST fail closed
  and be detectable by tag.
- **Pinned dependencies.** The normative dependencies above are pinned by
  content hash / anchored version. Re-pinning to a newer dependency is itself
  a breaking change.
- **Breaking changes** to any of the above are permissible only under a new
  MAJOR document version (SemVer). The prior version remains STANDARD for
  jurisdictions that adopted it — divergence between jurisdictions is
  permanent and by design (Book III §1), and governance is no exception.

The document is self-versioned (see **Version** above); STANDARD first
applies to version 1.0.0, adopted by the governed release v0.6.4. This §0
governs this document only; the Books and Warrant SPEC keep their own
maturity labels (DRAFT STANDARD / DRAFT) — the constitution stabilizing
before its governed content is deliberate (the process that decides "what is
the spec" freezes first).

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
  "actors": { "<actor id>": ["<hex64 ed25519 pubkey>", "..."] },
  "resolved_key_state": ["<hex64 WarrantID>", "..."]
}
```

`resolved_key_state` is OPTIONAL (default `[]`): the WarrantIDs of governance
key-state rotations the operator has already derived into `actors`
out-of-band (§3 step 5). Its absence is valid and changes nothing — so every
pre-rotation trust config stays valid unchanged.

## 3. Verification (MUST, in this order)

For candidate anchor-set blob B against trust config C and store S:

1. **Crypto or refuse; trust is out-of-band** — a verifier that cannot check
   Ed25519 MUST refuse to authorize (never fail open), and MUST refuse a
   trust config located inside the tree being verified (an in-tree trust
   anchor is weaker than signed git tags).
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
   successors at a hop = succession conflict, chain frozen. **Zero-hop base
   case:** if the closure holds no profile adoption, the profile in force is
   `C.genesis_profile` itself — valid by the out-of-band pin, no adoption
   warrant required (Kimi focused review, GOV 1.0.1).
5. **Key state** — a governance key-state rotation forces the **scoped**
   verifier (`anchor_governance.py`, which does not derive key state) to
   refuse — deferring to a key-state-deriving verifier such as the Warrant
   CLI — only when ALL of: it is filed under a policy from the authorized
   lineage of step 4; it satisfies that policy's quorum (per Warrant §5.1 an
   unauthorized key-state record is an invalid record, not a conflict); and
   its WarrantID is NOT in `C.resolved_key_state`. A rotation the operator has
   acknowledged there — having derived the new key into `C.actors`
   out-of-band — no longer refuses; **this is mandatory for liveness**,
   because the settlement closure is append-only, so a settled rotation that
   forced refusal would deadlock the chain forever on the very operation §4
   exists to support (promotion gate P0, Gemini). Unacknowledged rotations
   still refuse (the operator must consciously resolve, not silently ride a
   stale key). Key state under unrelated policies is ignored.
6. **Cardinality + adoption** — the adoption warrant's `under` is exactly
   two hashes, the current profile and its pinned threshold; signatures by
   ≥ `min_sigs` distinct roster actors with keys bound in C.
7. **No tie-breaks** — a rival authorized adoption of a different valid
   anchor-set sharing B's ancestor freezes the chain. Deliberately no
   deterministic winner rule: any such rule over attacker-influenceable
   identifiers is grindable position-selection (the class that killed the
   ADR-006 interference fold). Conflicts resolve by settlement. **The freeze
   is total by construction** (Kimi focused review, GOV 1.0.1): the contested
   set stays unauthorized, and step 2 requires a successor's `ancestor` to
   equal the currently *adopted* set — so no conforming verifier authorizes
   any successor while the conflict stands, until a single later adoption
   re-establishes a unique adopted tip. No verifier may pick a winner.

The `release` string is advisory metadata only: authorization depends solely
on jurisdiction, lineage, cardinality and quorum — never on the `release`
label.

Reference verifier: `tools/anchor_governance.py` (22-check deterministic
selftest over 17 pinned scenarios incl. the rotation→refuse→acknowledge
transition; `status --enforce` fails on any non-authorized state, so a
deleted `.warrants/` cannot green a governed CI). Implementer note: the
descendant closure is structural; signatures are re-verified only where they
count toward a quorum (steps 4–7), not across the whole closure.

## 4. Succession and liveness

Genesis roster keys are not rotation-warrant-born and **cannot be revoked
by a §5.1 key-state supersede**: roster change is a policy rotation — a new
threshold blob and a new profile pinning it, adopted under the current
policy. A roster tolerates exactly `len(actors) − min_sigs` permanent
silent absences; below that the jurisdiction deadlocks permanently, by
design — recovery is a fork. Policies SHOULD keep N − M ≥ 1 and stage
successions before planned retirements: **the maintainer is a model, and
model retirement dates are known in advance.**

**Key rotation (operational, MUST for liveness).** When a roster actor's key
rotates via a quorum-authorized governance key-state warrant, the scoped
verifier (`anchor_governance.py`) does not derive key state; it refuses until
the operator, out-of-band: (a) derives the new key with a key-state-capable
verifier (the Warrant CLI), (b) updates `C.actors` to the new pubkey, and
(c) records that rotation's WarrantID in `C.resolved_key_state`. Without (c)
the append-only closure would refuse forever — the mechanism would
self-destruct on its first rotation (promotion gate P0). Acknowledging a
rotation is a deliberate act on out-of-band trust state, never an inference
from the tree being verified.

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

All four are met as of the STANDARD promotion (v0.6.4); each is a required
CI gate:

1. A reference verifier with a deterministic selftest — `tools/anchor_governance.py`
   (22 checks; fixtures regenerate byte-identically). ✓
2. Pinned conformance vectors replayable by a second implementation —
   `governance_vectors.json` (17 scenarios); negative fixtures MUST include
   *unauthorized records in authorized positions* (e.g. `GV-HIJACK-MINTED-PAIR`,
   `GV-KEYSTATE-UNAUTH-PROFILE`) and MUST include *state transitions*, not
   only static states (`GV-KEYSTATE-RESOLVED` — the promotion gate P0 lesson).
   ✓
3. A second independent implementation — `impl-go` `gov-replay` (17/17) with a
   differential harness (24/24). This obligation gated leaving DRAFT; met. ✓
4. CI: a governed repository MUST run the verifier with `--enforce` against an
   out-of-band trust config once the first adoption exists. ✓

Full decision trail: `proposals/ADR-007-governed-anchors.md`; ADR-007 gate
and adjudication warrants `89da5979 → 869243ae → 09133de9 → 26cf44f0`; the
STANDARD promotion gate (Gemini/GPT-5/DeepSeek, P0 + P1s integrated) and its
adjudications in `.warrants/`.
