<!-- produced via tools/or_review.py | model: moonshotai/kimi-k2.6 | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-kimi-adr007-verify.md.pass1 -->

# Review: ADR-007 rev 2 Verification Pass (Gate Round 1 Closed)

**Reviewer:** independent adversarial verification (no code execution)  
**Primary sources:** `proposals/ADR-007-governed-anchors.md` rev 2; `tools/anchor_governance.py` rev 2; gate round-1 review pack (attributed below)

## Verdict

**Blocked by one residual P1.**  
Round-1 gate findings are materially closed. The three rev-2 focus questions are answered below. However, a new P1-R—signature validation omitted from the governance-hash collector—means the tool does not deliver the key-state scoping that the maintainer response claims. Close P1-R and ADOPT.

---

## Pass-1 Findings

### Round-1 closure audit

All P1s raised by GPT-5, Gemini, and DeepSeek in gate round 1 are closed in rev 2:

- **Settlement-ignorant authorization (GPT-5 P1-A):** CLOSED. `settlement_closure(root)` computes the descendant fixpoint via prior edges; only records reachable from the pinned jurisdiction root are eligible. Orphan adoptions are ignored (selftest `adoption outside settlement closure ignored`).
- **Under cardinality (GPT-5 P1-B / Gemini Ask 3):** CLOSED. `_under_is` enforces `len(u)==2` and `set(u) == {profile_hash, threshold_hash}`. Extra blobs make the adoption ineligible (selftest `under with extra blob ineligible`).
- **Ancestor discipline (GPT-5 P1-C):** CLOSED. Genesis anchor-sets MUST omit `ancestor`; successors MUST carry the prior adopted set hash. Fork semantics are stated.
- **Fail-open crypto (Gemini P0-A):** CLOSED. Step 1 of verification requires Ed25519; missing cryptography is a hard refusal (`ERR: … refusing to authorize`).
- **Ungoverned exit-0 (Gemini P0-B):** CLOSED. `anchor_governance.py status --enforce` exits 1 when authorized state is absent.
- **Threshold-injection hijack (Gemini Ask 3):** CLOSED. A profile blob hash-pins its threshold; the current profile derives by walking authorized lineage; a minted 1-of-1 policy pair is rejected (selftest `minted 1-of-1 policy pair rejected`).
- **Jurisdiction root (DeepSeek P1-1):** CLOSED. Anchor-set blobs embed `"jurisdiction": <hex64 Genesis WarrantID>`; mismatch is rejected at schema level before signature work (selftest `foreign jurisdiction blob refused`).
- **Competing adoptions (DeepSeek P1-2):** CLOSED. Rival authorized successors freeze the chain; no deterministic winner rule exists (selftest `competing authorized successors freeze the chain`).
- **Key-state scoping (DeepSeek P1-3):** PARTIALLY CLOSED. The tool no longer bricks on *any* key-state warrant anywhere, but the shipped scoping mechanism is unsafe (see P1-R below).

---

### FOCUS 1: Can the policy-lineage walk be SPURIOUSLY frozen — a succession conflict manufactured without a quorum?

**No.** A spurious freeze is impossible; every lineage hop requires a valid quorum.

Arithmetic. Let the current governance profile be \(P_i\), bound to threshold \(T_i\) with roster \(R_i\) of size \(N\) and `min_sigs` \(M\). In `derive_current_profile`, a candidate successor profile \(P_{i+1}\) is added to the set `nxt` only if the store contains an accept warrant \(W\) whose subject is \(P_{i+1}\) and whose `under` is exactly \(\{H(P_i), H(T_i)\}\), and whose signatures satisfy:

\[
|\text{counted\_sigs}(W, H(\text{body}(W)), T_i, \text{trust\_actors})| \geq M
\]

`counted_sigs` requires each counted actor to be in \(R_i\), bound in the out-of-band trust config, and to present a valid Ed25519 signature over the body hash. An attacker controlling fewer than \(M\) distinct actors in \(R_i\) cannot produce even one valid entry in `nxt`; therefore they cannot produce two entries, and the condition `len(nxt) > 1` (succession conflict / chain frozen) is unreachable.

If the attacker controls \(\geq M\) actors, they are, by definition, an authorized quorum of the current policy. Two authorized successors under the same policy constitute a *constitutional disagreement*, not a spurious attack. The mechanism is designed to freeze exactly in this case. No attacker outside the quorum can manufacture the freeze.

**Drafting position:** The code correctly enforces the current-policy rule from Warrant §5.1. Verdict: **FOCUS 1 is answered negatively.**

---

### FOCUS 2: Does settlement-closure scoping + embedded jurisdiction root close the replay surface completely against a verifier with a CORRECT out-of-band trust config, or name the residual confusion attack?

**Replay surface: fully closed. Residual confusion attack: named below.**

**Why replay is closed.**  
Settlement closure (`settlement_closure`) computes the descendant fixpoint of the `prior` DAG starting from the pinned root. Any record not reachable from that root is invisible to the verifier. The anchor-set blob carries an embedded `"jurisdiction"` field equal to the genesis WarrantID. `verify_adoption` rejects, at schema level, any blob whose jurisdiction does not match the verifier’s out-of-band trust config. Therefore:

- A fork cannot replay the original chain into a different store and present it to a verifier with the correct root: the original root is either different (blob rejected at jurisdiction match) or identical (records are part of the same jurisdiction and must obey its policy).
- A replayed record from a foreign root is excluded because it is not in the descendant closure of the pinned root.

**Residual confusion attack: unauthorized governance-hash pollution bricks the verifier via `key_state_under_governance`.**

`governance_blob_hashes` builds the set of hashes that trigger the key-state refusal. It iterates `_accepts_of(recs, closure, bdir)` and adds the subject hash of every record whose decision is `accept` and whose subject parses as a valid profile blob. `_accepts_of` verifies body-to-record-id integrity (`sha256(canon(body)) == rid`) but **does not verify signatures**.

Because the `.warrants` store is content-addressed and the tool loads every `.json` file present, an attacker with write access to the store can:

1. Create a valid profile blob \(P_x\) (schema-correct: `governance_profile`, `scope`, `threshold` fields).
2. Compute \(H(P_x)\), store the blob, and store a record \(R_x\) with `decision="accept"`, `subject.hash = H(P_x)`, `prior = [root]` (placing it inside the settlement closure), and arbitrary or invalid signatures.
3. Because `_accepts_of` ignores signatures, `governance_blob_hashes` adds \(H(P_x)\) to `gov`.
4. The attacker then stores a key-state warrant \(R_k\) (subject `{"actor":"A","key":"K"}`) with `under = [H(P_x)]` and `prior = [root]`.
5. `key_state_under_governance` scans the closure, sees `under` intersects `gov`, and returns `True`.
6. `verify_adoption` refuses with `ERR: key-state warrants under governance policy blob...`, even though \(P_x\) was **never authorized by a quorum**.

The verifier with a correct trust config is thereby *confused* into treating an unauthorized profile blob as a governance policy and spuriously refusing legitimate anchor-set adoptions. This is a liveness-breaking confusion attack, not a safety violation, but it is reachable without a quorum and without a valid signature.

**Verdict:** Replay is closed; the residual confusion attack survives because the governance-hash collector omits signature verification. **FOCUS 2 names the residual attack.**

---

### FOCUS 3: Attack `tools/anchor_governance.py` rev 2 directly — its 20-check selftest is the claim surface; find the case it missed.

**The missed case: unauthorized profile adoption expands the key-state refusal scope.**

The selftest covers:
- settlement-closure exclusion,
- under-cardinality enforcement,
- foreign-jurisdiction rejection,
- profile/threshold binding,
- lineage succession under rotated policy,
- competing-authorized-successor freeze,
- key-state under governance refused,
- key-state under unrelated policy ignored,
- 1-of-1 hijack rejected,
- and several canonical JSON / schema checks.

The selftest does **not** exercise `governance_blob_hashes` with an *unauthorized* profile adoption. Specifically, it does not create a profile-shaped accept record that:

- passes `sha256(canon(body)) == rid` and `decision == "accept"`,
- passes `valid_profile(doc)`,
- is placed inside the settlement closure via a `prior` edge to the root,
- **carries no valid signatures** (or carries signatures from keys not bound in the trust config),

and then verify that this unauthorized hash is **excluded** from the governance set used by `key_state_under_governance`.

Because the selftest only uses fully authorized fixtures, the signature-validation gap in `governance_blob_hashes` is never exercised. An attacker-injected profile-shaped blob would pass all tests that the selftest runs, yet would expand the refusal surface and brick the verifier.

**Fix:** `governance_blob_hashes` must derive its set from the **authorized** profile lineage only. Since `derive_current_profile` already walks the quorum-authorized succession and rejects unsigned hops, the simplest safe source of governance hashes is the sequence `{genesis_profile} ∪ {profiles consumed in the lineage walk} ∪ {their bound thresholds}`. Alternatively, `governance_blob_hashes` must independently verify that each profile adoption it counts carries a valid quorum under the threshold current at that hop.

**Verdict:** The selftest’s claim surface is 20/20 for the scenarios it covers, but it misses the **unsigned governance-hash pollution** vector. **FOCUS 3 identifies the gap.**

---

### P1-R: Signature validation gap in `governance_blob_hashes` (new, not in round-1)

**Severity:** P1 — spec silent where implementers must guess; tool under-delivers claimed scoping.

**Description:** As demonstrated in FOCUS 2 and FOCUS 3, `governance_blob_hashes` treats every profile-shaped accept in the closure as a governance policy, regardless of whether its adoption warrant was authorized. The maintainer response to DeepSeek P1-3 claims: *"Refusal now scoped to key-state warrants filed under a governance policy blob; rotations in the review trail no longer brick anchor verification."* The code does **not** deliver this claim, because any attacker can manufacture a "governance policy blob" without a quorum.

**Concrete fix:** Replace the broad `_accepts_of` scan in `governance_blob_hashes` with a derivation tied to the authorized lineage. After `derive_current_profile` succeeds, emit the set:

\[
\text{gov} = \{\text{genesis\_profile}\} \cup \{\text{genesis\_threshold}\} \cup \bigcup_{k=1}^{n} \{H(P_k), H(T_k)\}
\]

where \(P_1 \dots P_n\) are the profiles consumed in the walk. Any key-state warrant filed under a hash outside this authorized set is irrelevant to anchor governance.

**Verdict:** Blocker until closed.

---

## Relation to prior reviews

**GPT-5 (gate round 1):**  
*Agree* on the lineage-binding arithmetic (profile pins threshold, under exact cardinality, current-policy walk) and on the settlement-closure requirement. My FOCUS 1 confirms that the adopted lineage walk correctly prevents spurious freeze without quorum. My FOCUS 2 confirms the replay-closure value of embedded jurisdiction + descendant fixpoint, but names a residual attack not identified in the gate.

**Gemini (gate round 1):**  
*Agree* on the hijack arithmetic (threshold-injection) and on the out-of-band trust requirement. The fail-open crypto and exit-0 P0s are verified closed in rev 2. My FOCUS 3 finds a new gap not caught by Gemini’s vulnerability analysis or by the rev 2 selftest expansion from 14 to 20 checks.

**DeepSeek (gate round 1):**  
*Agree* on jurisdiction embedding (2:1) and on the intent of key-state scoping. *Disagree* with the maintainer disposition that claims P1-3 is fully fixed. DeepSeek’s requested scoping—ignore key-state warrants not under the governance threshold—is correct in principle, but the rev 2 implementation under-delivers because it omits signature validation from the governance-hash collector. The maintainer response states the selftest covers both directions of scoping; the selftest does not, in fact, cover the unauthorized-profile-injection direction. This is a new finding.

**Codex (v0.6.0 pedantic audit):**  
*Not applicable* to ADR-007 surface area; Codex did not evaluate governed anchors. Codex’s CI-hygiene lesson (pipefail / “lying green”) is noted as general infrastructure culture, but no direct bearing on the mechanism.

**Attribution note:** I did not run the selftest or any tool commands. Observations about selftest coverage, code paths, and maintainer dispositions are drawn from reading `tools/anchor_governance.py` rev 2 and the text of `proposals/ADR-007-governed-anchors.md` rev 2. Statements about prior reviews’ content are taken from the review files in `reviews/2026-07-{gpt5,gemini,deepseek,codex}-adr007-gate.md` and their corresponding maintainer responses.
