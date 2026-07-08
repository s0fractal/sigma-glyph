<!-- produced via tools/or_review.py | model: deepseek/deepseek-v4-pro | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-deepseek-adr007-gate.md.pass1 -->

# Review: ADR-007 Governed Anchors Design Gate

**Reviewer:** independent, with access to the full repository (PRIMARY SOURCES, pass‑1 context, prior reviews) but **no code execution**.  Observations from other reviews are explicitly attributed.

## Verdict

The governed‑anchor mechanism is sound in its core design.  Warrant v0.3 threshold policies correctly provide key‑state continuity, revocation, rotation, and collective authorization that signed git tags cannot express.  However, three **P1** defects in the specification and tooling must be fixed before adoption, and three **P2** issues (including the bootstrap honesty gap) should be resolved for a robust gate.  With these repairs the ADR will be one revision away from gate‑readiness.

**P1 findings** (must fix):

1. **Jurisdiction root missing from anchor‑set blobs** – a fork can replay the public warrant trail and present it to a fresh verifier as though it were the original chain.  Embedding the genesis WarrantID (like Book III §2) costs nothing and eliminates the confusion.
2. **Multiple adoption warrants cause verifier divergence** – the tool’s tie‑break is implementation‑defined (filesystem order).  A deterministic rule (e.g., lexicographically smallest WarrantID) must be specified.
3. **Governance verifier breaks on unrelated key‑state warrants** – `anchor_governance.py` conservatively aborts when *any* accept/supersede warrant touches key state, even if the warrant belongs to a different scope (e.g., the review trail).  The check must be scoped to the governance policy’s under‑list.

**P2 findings** (strong recommendations): bootstrap authentication (out‑of‑band pinning of genesis trust config), profile‑to‑threshold binding (profile should hash‑pin the threshold blob), conformance vectors (need pinned, deterministic test suites), trust config versioning, and explicit liveness limits of threshold rosters.

## 1. Attack the bootstrap – not ceremony

**What the governed chain stops that signed git tags do not:**

Signed git tags assert “actor X signed commit C at time T.”  They cannot express that X’s key was later **revoked** or that a **roster** of actors with a threshold must collectively authorise releases.  A verifier using only git tags would accept a later release signed by a revoked key, because the tag itself contains no revocation state.  The governed chain is a state machine over keys: adoption warrants are signed against the *current* policy’s roster, and key‑state warrants (accept, supersede, conflict) modify the effective roster.  After a supersede removes a key, any future release signed by that old key is cryptographically invalid under the new policy – **the exact attack that the governed chain stops but git tags do not**.

Arithmetic: Suppose the genesis policy requires 2 of {founder, model‑a, model‑b}.  A supersede warrant (signed by founder+model‑a) replaces the policy with a new one that omits model‑b.  A subsequent release bearing model‑b’s signature fails the threshold check because model‑b is no longer in the roster.  A git‑tag‑based verifier has no way to express “model‑b’s key is no longer authoritative” and would accept the signature, trusting a stale trust config.

**The bootstrap gap:** A fresh verifier cannot distinguish an authentic governed chain from a backdated forgery unless it obtains the genesis trust config and the first adopted anchor‑set blob hash through an out‑of‑band channel.  The ADR must explicitly require that these genesis artefacts are distributed independently of the git repository (social: cross‑posted to multiple platforms, cited in published gate reviews).  Without this, the chain is purely a ceremony – the genesis trust is a social fact, but the subsequent history is mechanically verifiable once that genesis is pinned.  The bootstrap itself is **not** automatable; it requires out‑of‑band trust.  This is a P2 gap, addressed by a concrete distribution requirement in the ADR.

**Verdict:** The mechanism provides real key‑state continuity; the bootstrap is a social trust step, but the chain beyond it is not mere ceremony.

## 2. Attack the ancestor chain across jurisdictions – P1, jurisdiction root needed

**Can a fork replay the public anchor‑set chain and present as the original to a fresh verifier?**

Yes – trivially.  The anchor‑set blobs and adoption warrants are public; the trust config is mutable.  A fork operator copies all blobs and warrants into a new `.warrants/` store, edits `ANCHORS.txt`, and distributes a `trust‑config.json` pointing to the same genesis actor keys (which are public).  A fresh verifier with no prior trust state sees an identical governed chain.  The ADR’s answer – “canonicity is a trust decision” – is philosophically correct but **mechanically insufficient** because the verifier lacks the data to distinguish jurisdictions.

**Book III §2 embeds the genesis `WarrantID` directly in assertion blobs, precisely to prevent this replay: a blob from jurisdiction A cannot be accepted in jurisdiction B.**  The ADR’s anchor‑set blob has no analogous field.  The `ancestor` field chains within a jurisdiction but does not name it.

**Fix:** Add a `jurisdiction` field to the anchor‑set blob that contains the genesis adoption warrant’s `WarrantID`.  A conformant verifier must reject any blob whose `jurisdiction` does not match the genesis root in its local trust config.  This is a single‑field change that instantly gives the verifier the ability to say “this blob claims to be from jurisdiction X, but I trust Y – mismatch.”

**Severity: P1.**  Without this, a fork can silently masquerade as the original, and a fresh verifier has no mechanical way to reject it.

## 3. Attack the two‑blob under split – profile should pin threshold hash (P1/P2)

The ADR proposes that adoption warrants file `under` **two** blobs: a pure Warrant v0.3 threshold‑policy blob, and a sigma‑glyph governance profile blob.  The threshold blob is bit‑compatible with any warrant implementation; the profile scopes it to anchor adoption.

**Can a satisfied threshold blob be replayed to authorise unrelated subjects?**

If a warrant for a different purpose (e.g., a key rotation) omits the profile blob and files only under the same threshold policy, a verifier that does not check for the profile may accept it.  However, the reference verifier `anchor_governance.py` **requires both** blobs in `under`; a warrant lacking either is rejected.  Thus, in the default implementation, the replay vector is closed.

The **actual risk** is implementer confusion: the profile blob and threshold blob are semantically linked but syntactically independent.  An implementer could mistakenly accept a warrant with only one of the two.  The defence against this is to make the binding explicit inside the profile blob.

**Recommendation:** The profile blob **should** include a `threshold_policy` field containing the SHA‑256 hash of the bound threshold policy blob.  Then:

- The binding is inside the hashed profile, not just an array adjacency.
- A verifier can validate “profile P binds threshold T” with a single hash check.
- Changing the threshold (i.e., superseding the profile) requires a new profile blob, whose hash changes, preventing accidental mismatch.

This is a one‑field change that eliminates ambiguity.

**Severity: P1/P2 boundary.**  Current design works correctly but invites footguns.  The hash‑pin should be adopted.

## 4. Walk actor deprecation mid‑policy concretely

**Setup:** roster = {founder, model‑a, model‑b}, `min_sigs` = 2.  Model‑A retires silently (no revocation, no supersede).  **Is the store live?**  Yes – founder and model‑b together form a quorum (2 of 3).  The threshold is still 2, and two distinct keys are available.  The store is fully live.

**Exact sequence to recover (i.e., remove model‑A from the roster):**

1. Founder and model‑B sign an `accept` warrant whose subject is a **new threshold policy blob** with roster {founder, model‑b, model‑c} and `min_sigs: 2`, filed `under` the current threshold policy.  This warrant requires 2 signatures from the old roster – satisfied.
2. The new policy is adopted.  Model‑A’s key is no longer in the roster; no revocation is needed.
3. All future adoption warrants are signed against the new roster.

**Arithmetic:** N = 3, M = 2 → N‑M = 1.  The quorum can tolerate one permanent absence.  If model‑B disappears simultaneously with model‑A, only the founder remains (1 signature < 2), and the store **deadlocks permanently** – no supersede warrant can be authorised because no quorum exists.  Warrant §5.1’s emergency conflict‑reduction rule does **not** trigger for non‑conflicted actors.  The deadlock is by design; recovery is a jurisdiction fork (new genesis root) or a social trust‑override.

**Severity: P2 – design constraint.**  The ADR should explicitly document the N‑M tolerance and the permanent‑freeze failure mode.  The mechanism is correct; the failure mode is a feature, not a bug.

## 5. Placement – Book IV

**Recommendation: Book IV: GOVERNANCE, a normative Book with conformance obligations.**

Anchor governance is mechanically verifiable (`anchor_governance.py` produces an exit code from a warrant store, analogous to the Book III oracle’s `ALL PASS`).  It defines a jurisdiction over spec bytes, with a threshold selection policy, replay‑resistant anchor‑set blobs, and fork legitimacy – structurally identical to Book III’s jurisdiction over annotation assertions.  Placing it inside Book III would bloat a document whose subject is wave‑annotation federation, confusing readers.  A standing `GOVERNANCE.md` outside the Books risks being treated as advisory and would not carry the requirement for machine vectors and differential second implementations.

Book IV inherits the conventions of the other Books: its own anchor in `ANCHORS.txt`, a reference implementation, conformance vectors, and a “second implementation” differential gate.  This signals that governance is a consensus‑critical component of the specification.

**Text proposal:**  
> Book IV: GOVERNANCE defines the mechanism by which the Three Books’ anchor‑sets are adopted, superseded, and forked.  It is a Warrant v0.3 profile structurally analogous to Book III’s annotation federation: a jurisdiction over spec bytes, with a threshold selection policy, replay‑resistant anchor‑set blobs, and permanent fork legitimacy.  Book IV carries the same conformance obligations as Books I–III.

## Additional Attacks on ADR-007 and `anchor_governance.py`

### 6.1 Multiple adoption warrants for the same blob cause verifier divergence (P1)

The `ancestor` field chains releases, but a malicious quorum can simultaneously file two `accept` warrants for the same release (e.g., two distinct anchor‑set blobs) with the same ancestor.  Both are valid; Warrant §5.1’s conflict rule does not cover subject‑adoption warrants.  The current tool sorts warrants by filesystem order (implementation‑defined) and picks the first it finds – two verifiers with different directory listings can disagree on which adoption is authoritative.  
**Fix:** Specify a tie‑break rule: “If multiple settlement‑active adoption warrants exist for the same anchor‑set blob hash, the warrant with the lexicographically smallest WarrantID is authoritative.”  This mirrors Book III’s selection‑policy tie‑break and costs nothing to specify.

### 6.2 Scope as a bare string – fragile but acceptable for now (P2)

The governance profile blob uses `"scope": "spec/ANCHORS.txt"`, a free‑text string.  If the file is renamed, the blob’s bytes are unchanged but the scope becomes wrong.  Conversely, a fork changing scope must change the string (and thus the blob hash), forcing all adoption warrants to be re‑filed.  This is fine for a single‑jurisdiction use, but a future multi‑scope governance would benefit from a content‑addressed scope definition (hash of a scope blob).  Acceptable for v0.6.x.

### 6.3 No deterministic conformance vectors (P2)

`anchor_governance.py`’s self‑test generates fresh Ed25519 keys every run, so its outputs are non‑deterministic.  Unlike Book III’s `federation_vectors.json` with 21 pinned vectors, the governance tool has no replayable conformance suite.  **Before adoption, the ADR must commit to producing a set of pinned vectors** (known keys, known stores, expected outcomes) that can be used by an independent implementation.

### 6.4 Trust config is unversioned and unsigned (P2)

`trust‑config.json` contains raw actor key mappings with no schema version, no self‑hash, no signature.  A corrupted or maliciously edited file silently changes the verifier’s root of trust.  **Recommendation:** add a `governance_trust` property with a versioned schema (e.g., `"sigma‑glyph.trust‑config@v1"`) and a `jurisdiction` field matching the genesis root.  Also recommend distributing the trust config with a detached signature or hash pin.

### 6.5 Governance verifier breaks on unrelated key‑state warrants (P1)

`anchor_governance.py`’s `store_has_key_state_warrants()` function immediately bails out if **any** accept or supersede warrant’s subject parses as a key‑state object, regardless of which policy it files under.  This means the governance verifier cannot coexist with the review‑trail warrant store if a future key rotation for the review trail is filed there.  The check must be narrowed: only key‑state warrants that file `under` the governance threshold policy blob (or governance profile blob) should trigger a refusal.  Key‑state warrants under unrelated policies are irrelevant to anchor governance and must be ignored.

**Severity: P1 – architectural conflict between the governance and review‑trail uses of the same warrant store.**

## Relation to Prior Reviews

The two prior reviews available – **Codex pedantic full‑state audit (v0.6.0)** and **Qwen holistic analysis** – did not evaluate ADR‑007.  My findings are therefore complementary and do not conflict with their conclusions.

- **Codex pedantic audit** focused on the v0.6.0 release surface (CI masking bug, stale references, proof bridge pedantry, etc.).  Its thoroughness exposed a pattern of “hygiene defects” that is consistent with my own P2 findings (e.g., missing conformance vectors, unversioned trust config).  I agree with the Codex assessment that the project benefits from strict version/documentation hygiene, and my review independently echoes that principle.
- **Qwen holistic review** offered a broad critique of Σ‑GLYPH and Warrant, with some claims refuted by existing vectors (observer paradox, floats).  Its strengths section gave a fair outside summary of the three‑Book architecture.  The review did not touch anchor governance, so its Warrant‑side criticisms (e.g., key revocation mechanisms) do not directly affect my analysis; the governed‑anchor design already uses key‑state warrants within a policy, which addresses the “lifelong keys” concern in that context.

Both prior reviews and the maintainer responses align with my overall judgement that the specification and tooling culture is rigorous but that every new mechanism needs the same “vectors, differential, precise scoping” discipline – which is exactly what my P1 findings demand for ADR‑007.  My verdicts are my own, drawn from the ADR text and tool code; the prior reviews provide useful context but do not alter the specific defects uncovered here.
