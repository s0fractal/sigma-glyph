# ADR-007: Governed anchors — Specification Anchors as warrant-settled artifacts

**Status:** PROPOSED (gate 0 of ≥3) — drafted 2026-07-08; mechanism implemented and self-tested (`tools/anchor_governance.py`), no adoption warrants exist yet and none may exist before this gate closes.
**Origin:** ROADMAP has promised "Multi-Signature / Threshold Governance" over Specification Anchors since v0.4.3, filed as *cultural, no technical proposal yet*. The enabling event is the same one that unblocked Book III: **Warrant v0.3** ships threshold policies, key state, and settlement-active jurisdictions (§5.1, §7, §9). This ADR is the technical proposal: it makes the ROADMAP's own Decision Process — which today is enforced socially — mechanically checkable, and it retires the interim single-maintainer trust point on a schedule instead of an accident.
**Normative dependency:** [Warrant SPEC v0.3](https://github.com/s0fractal/warrant) (pinned snapshot for reviewers: `proposals/refs/warrant-SPEC-v0.3-snapshot.md`). This ADR is a **pure Warrant v0.3 profile**: like Book III, it requires zero changes to the Warrant format.

## Problem

Every release since v0.4.0 anchors its documents in `spec/ANCHORS.txt`, and every
adoption since v0.5.1 files its adjudications as signed warrants in `.warrants/`.
The two trails run parallel and **nothing links them**:

1. **ANCHORS.txt is ungoverned text.** A release section is a git commit. Nothing
   machine-checks that the section was authorized by anyone — the adjudication
   warrants sit next to it, unreferenced. "Was v0.6.1 legitimately adopted?" is
   archaeology (read reviews/, correlate timestamps), not a verification.
2. **One actor, one key.** The entire warrant trail's authority is a single
   Ed25519 seed held by the interim maintainer (`claude-fable-5@sigma-glyph`).
   Key loss orphans the trail; key compromise rewrites it forward. There is no
   rotation path because there is no policy under which rotation warrants could
   be authorized.
3. **The maintainer is a model, and models retire on a schedule.** The interim
   maintainer is an AI actor. Model deprecation is not a tail risk to insure
   against — it is a *certainty with a date*. Succession must be a warrant
   authorized under a standing policy, not a `trust-config.json` edit by
   whoever holds the repo keys that day. (The ROADMAP already promises this
   transition; today it has no mechanism.)
4. **The Decision Process is not self-hosting.** The project's own rule — gate
   of ≥3 model families, implementation precondition, written adjudication —
   governs everything *except itself*. A release could skip the gate and the
   only witness would be prose.

## Candidate architectures

### G1 — Anchor-set warrants under threshold policy (lean on Warrant v0.3 wholesale)

A release's anchor section becomes a JCS-canonical I-JSON blob
(`sigma-glyph.anchor-set@v1`, §schema below). Adoption of a release = an
`accept` warrant whose `subject.hash` is the anchor-set blob, filed `under`
(a) a Warrant v0.3 threshold-policy blob and (b) an anchor-governance profile
blob, carrying signatures that satisfy the threshold, settlement-active in the
repository's `.warrants/` jurisdiction. `spec/ANCHORS.txt` remains the
human-readable **projection**; on any divergence the blob wins and the verifier
errors. Key continuity and succession are Warrant §5.1 verbatim: rotation is a
warrant, revocation is a warrant, conflicted keys are excluded, emergency
replacement is quorum-without-the-outgoing-key.

- Mechanical decidability → `tools/anchor_governance.py` answers "is this
  release authorized" with an exit code, from the store alone.
- Succession → policy roster with `min_sigs < len(actors)` survives any single
  actor's retirement; replacing an actor is a policy supersede authorized under
  the policy in force.
- Fork legitimacy → ANCHORS.txt already declares "a spec update is formally a
  fork with an explicit ancestor"; under G1 a hostile or friendly fork is a new
  jurisdiction (its own genesis root adopting its own anchor-set chain) — named
  mechanically, exactly like Book III jurisdictions. Canonicity is a
  per-verifier trust decision, by design, not a protocol claim.

Cost: bootstrap is self-signed (see gate ask 1); every release gains one
mandatory warrant-filing step.

### G2 — On-chain / DAO governance (the ROADMAP's original sketch)

Move anchor adoption to a smart contract or multisig chain. Rejected in
drafting: it imports an external consensus layer into a system whose explicit
axiom is that **Book I owns the only consensus** and everything else is
jurisdictional; it adds a token/gas dependency to a spec that runs on stdlib;
and it solves nothing G1 doesn't — a chain would still need the same threshold
semantics, now with a bridge. The gate may resurrect it with a use case.

### G3 — Status quo plus linking (single maintainer, anchors cite warrants)

Keep 1-of-1 governance but add the anchor-set blob and adoption warrant, i.e.
G1 with `min_sigs: 1` frozen. Honest about today, changes nothing structural.
Rejected as an *end state* (the single key remains the trail's single point of
failure and succession stays undefined) but **adopted as the bootstrap stage**
of G1: the first governed release is necessarily self-adopted by the incumbent
under a 1-of-1 policy, and the roster upgrade to M-of-N is itself the first
exercise of the policy-supersede path.

## Schemas (drafting base, G1)

Anchor-set blob — JCS-canonical I-JSON, closed (unknown fields invalid):

```json
{
  "governance": "sigma-glyph.anchor-set@v1",
  "release": "v0.6.1",
  "ancestor": "<hex64: SHA-256 of the prior adopted anchor-set blob, or absent for the genesis set>",
  "anchors": [
    { "path": "spec/book-1-truth.md", "anchor": "<hex64 NodeHash per ANCHORS.txt convention>" }
  ]
}
```

- `anchors` MUST be sorted by `path` ascending (byte order), one entry per
  anchored file, values exactly the `NodeHash(LITERAL, atom=SHA-256(bytes))`
  ANCHORS.txt already defines. The bundle convention (v0.6.1) applies
  unchanged: untouched files carry their old anchors.
- `ancestor` makes adopted releases a hash chain independent of git. A release
  whose `ancestor` is not the currently adopted set is a **fork**, not an
  upgrade — verifiers in the original jurisdiction MUST NOT treat it as the
  next release.

Governance profile blob — JCS-canonical I-JSON, closed:

```json
{
  "governance_policy": "sigma-glyph.anchor-governance@v1",
  "scope": "spec/ANCHORS.txt"
}
```

The adoption warrant's `under` MUST list **both** the profile blob and a
Warrant v0.3 threshold-policy blob (exact §5 grammar, no extra fields — the
two-blob split keeps the threshold blob bit-compatible with warrant
implementations that know nothing about sigma-glyph). Changing either blob is
constitutional change: the superseding adoption MUST satisfy the threshold of
the policy **being replaced** (Warrant §5.1 current-policy rule, applied to
governance itself).

## Design criteria for the gate

1. **Book I MUST be unreachable** from governance state — anchors govern which
   *bytes* are the spec, never what any term evaluates to. (Inherited axiom.)
2. **Mechanical decidability:** "release R is authorized under policy P" MUST
   be a pure function of (store, trust config) with an exit code — no prose,
   no timestamps-as-authority, no git archaeology.
3. **Succession is a liveness requirement:** the mechanism MUST survive the
   scheduled retirement of any single actor (model deprecation is certain),
   via Warrant §5.1 paths only. A roster that can deadlock on one absent
   actor fails this criterion.
4. **Bootstrap honesty:** the first governed release is self-adopted by the
   incumbent. The ADR claims **continuity-from-then**, not
   legitimacy-from-origin: governance proves that every release *after*
   activation was authorized under the policy in force — it MUST NOT fabricate
   authority for history. Pre-governance sections stay in ANCHORS.txt labeled
   as ancestors, exactly like the v0.4.2 retroactive-anchor precedent.
5. **No parallel truth:** on ANCHORS.txt ↔ blob divergence, the blob wins and
   verification fails loudly. One projection, one source.
6. **Fork legitimacy preserved:** a fork with its own genesis root and its own
   anchor-set chain MUST be *nameable and verifiable* in its own jurisdiction,
   and MUST NOT be confusable with the original chain by a verifier holding
   the original trust config.

## Review gate asks (rev 1)

1. **Attack the bootstrap.** A chain that begins with a 1-of-1 self-signed
   adoption: is its continuity claim worth more than git history alone
   provides? Name the exact attack the governed chain stops that signed git
   tags do not, or concede the mechanism is ceremony. (Drafting position: key
   state + threshold succession is the difference — git tags cannot express
   "this key may no longer sign releases" — but the gate should try to break
   this.)
2. **Attack the ancestor chain across jurisdictions.** Can a fork replay the
   original anchor-set chain (public blobs, public warrants) into its own
   store and present as the original to a *fresh* verifier with no trust
   config? Is "canonicity is a trust decision" an honest answer or an evasion —
   does the mechanism need first-use pinning guidance (à la Book III's
   embedded jurisdiction root) in the anchor-set blob itself?
3. **Attack the two-blob `under` split.** The threshold blob is pure Warrant
   grammar; the profile blob binds it to anchors. Can a threshold blob
   satisfied for anchor governance be replayed to authorize something else
   (key rotation, unrelated settlements) because the binding lives in a
   *sibling* blob rather than inside the policy? Does the profile need to name
   the threshold blob's hash explicitly?
4. **Attack criterion 3 concretely.** Walk actor deprecation mid-policy under
   Warrant §5.1: roster {founder, model-A, model-B}, `min_sigs: 2`, model-A
   retires with no successor and no revocation warrant. Is the store live? Is
   there a quorum path that does not degenerate to founder-plus-one-model =
   effectively 1-of-1 with ceremony?
5. **Placement.** Is this Book III material (governance as a federation
   jurisdiction over spec bytes), a fourth Book, or a standing GOV document
   outside the Books? The Books are protocol; this governs the protocol's
   *text*. Wrong placement either bloats Book III or hides the constitution.

## Non-goals

On-chain anything, tokens, DAO tooling (G2 rejected pending a use case);
global consensus on the spec (forks are legitimate jurisdictions — the
mechanism *names* divergence, it does not prevent it); retroactive
legitimization of pre-governance releases; governance of anything other than
the anchored byte-sets (code, CI, and reviews remain git-governed — extending
scope is a future ADR with its own gate).
