<!-- produced via tools/or_review.py | model: google/gemini-3.1-pro-preview | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-gemini-adr007-gate.md.pass1 -->

# Review: ADR-007 Design Gate

## Verdict

**ADR-007 is severely compromised and MUST NOT move to adoption.** While the core idea of a cryptographic specification-release anchor is sound, the reference tool contains a catastrophic fail-open signature bypass, a logic flaw allowing unilateral policy hijack, and a downgrade vulnerability. The mechanics specified in the PROPOSED document fundamentally fail to bootstrap a chain of trust stronger than self-signed Git tags.

---

## 1. Attack the bootstrap (1-of-1 self-signed)

**The attack governed chains fail to stop (The Repo-Supplied Trust Anchor):** A signed git tag operates securely primarily because the verifier (`git tag -v`) checks the signature against an out-of-band trust root (e.g., `~/.gnupg` on the user’s local machine). Under your implementation, `tools/anchor_governance.py` blindly trusts the `trust-config.json` found *inside the git repository it is evaluating*. 

If an attacker compromises the repository (e.g., via compromised credentials), they simply rewrite the in-tree `trust-config.json` to include only their own public key, delete the `.warrants/` directory, and file a 1-of-1 self-signed release warrant. Your script reads the attacker's genesis config, verifies the attacker's key, and prints `AUTHORIZED`. The chain provides exactly zero additional security over a signed git tag under these conditions.

*Conclusion:* The bootstrap is currently less secure than git tags. You must force the genesis trust anchor out-of-band or pin it in the tool’s unmodifiable runtime invocation.
*Proposal:* Add to ADR-007: *"Verifiers MUST read genesis trust configuration from an out-of-band environment source or pinned path, and MUST NOT trust a `trust-config.json` file loaded from the untrusted git tree being evaluated."*

## 2. Attack the ancestor chain across jurisdictions

**Embedded roots are unnecessary.** A fork that replays the public anchor-set blobs and signatures into its own store presents absolutely zero threat to a fresh verifier *as long as the verifier is provided the correct out-of-band genesis trust config*. 

The spec blobs and policy blobs are inert on their own. Canonicity is exclusively evaluated by walking the `prior` DAG of adoption warrants backward to the genesis root. 
* If the fork uses the original jurisdiction keys legitimately, the signatures hold, proving legitimate endorsement. 
* If the fork attempts to forge a downstream adoption using different keys without an authorized threshold succession, the cryptographic signatures fail. 

Embedding a jurisdiction ID or root inside the `anchor-set` blob itself would just break the ability of friendly downstream forks to efficiently deduplicate the specification blobs. 
*Conclusion:* "Canonicity is a trust decision" is an honest, structurally sound answer here. The blob does not need an embedded jurisdiction root.

## 3. Attack the two-blob under split

**Stateless Threshold Injection is fatal.** Yes, the two-blob split without strict bindings is completely broken. Because the `anchor-set` blob does not strictly pin the hash of the threshold policy, `tools/anchor_governance.py` evaluates authorization using the threshold policy *supplied by the `under` array inside the warrant it is currently verifying*.

**The Arithmetic of the Hijack:**
*   Legitimate Roster = `[founder, model-a, model-b]`
*   Legitimate Target `min_sigs` = 2.
*   Attacker (`model-a`) authors a forged threshold blob: `{"warrant_policy": "0.3", "threshold": {"min_sigs": 1, "actors": ["model-a@sigma-glyph"]}}`.
*   `model-a` hashes this forged blob into `.warrants/blobs/<H_forged>`.
*   `model-a` files an adoption warrant pointing to `H_forged` in its `under` array, signs it alone (1 signature), and pushes the commit.

The script reads the `under` array, parses the attacker's forged policy, and runs the arithmetic: `1 (signature provided by model-a) >= 1 (min_sigs in forged policy)`. Result: `True.` The script returns `AUTHORIZED`. Any specific legitimate minor actor can unilaterally bypass the prior threshold and hijack the chain.

*Proposal:* Add a `next_policy: <hex64>` field to the `sigma-glyph.anchor-set@v1` blob schema to tightly pin the threshold policy governing the *subsequent* release. Alternatively, mandate that verifiers MUST inherit the `under` policy of the *ancestor's* adoption warrant to validate the signatures on the current one.

## 4. Walk actor deprecation mid-policy

Let's execute the deprecation walk. 
**Roster:** `{founder, model-a, model-b}`, with `min_sigs = 2`. 
**Event:** `model-a` retires silently and throws away their keys. 
**Is the store live?** Yes. `founder` + `model-b` = 2 signatures, which perfectly satisfies `2 >= 2`.

**The recovery sequence:** Under Warrant S5.1, revoking a key requires a supersede of the *rotation warrant that introduced the key*. Because genesis keys don't originate from a key-state rotation warrant—they are hardcoded in the genesis `trust-config.json`—they *cannot* be revoked via standard S5.1 key-state supersedes. 

The only mathematically valid sequence to formally remove `model-a` from the threshold is a hard constitutional change bundled directly with the next spec release:
1. `founder` authors a new threshold blob `H_new` defining roster `[founder, model-b]` and `min_sigs = 2`.
2. `founder` and `model-b` (collecting 2 total signatures to clear the *current* `min_sigs`) author and sign the adoption warrant for the new spec release (e.g., `v0.6.2`).
3. This adoption warrant specifies `"under": [H_profile, H_new]`, thereby enforcing that all *future* adoptions utilize the `H_new` roster.

*Proposal:* Add a designated S5.1 limitation note to ADR-007: *"Genesis keys cannot be revoked via key-state supersedes. Roster changes to genesis actors MUST occur via a bundled rotation of the threshold policy during a release adoption."*

## 5. Placement

**It must be a standing GOV document (e.g., `spec/GOV-anchors.md`).**
Books I, II, and III are operational protocol documents. They define how anonymous network nodes resolve content, bytes, and assertions. ADR-007, conversely, achieves human/mechanical consensus over *which exact text file constitutes the protocol at a given moment in a specific repository*. 

Placing this in Book III conflates network-level subjective annotation federation with repository-level objective specification maintenance. Furthermore, injecting human governance into *any* of the three Books invites a bootstrap evaluation paradox: does an update to Book III legitimately update the exact rules by which the update to Book III itself is meant to be judged by the governance script? Separating this into a fourth standalone GOV document dissolves the paradox.

---

## Other Attacks and Spec Defects

### Vulnerability A: Catastrophic Fail-Open Cryptography (P0)
If `anchor_governance.py` runs in a minimal environment where the script's `cryptography` library dependencies are not installed, it will silently validate invalid signatures. Look at this pseudo-block from the drafted approach:
```python
            if HAVE_ED25519:
                try: ... except Exception: continue
            counted.add(actor)
```
**Arithmetic:** If `HAVE_ED25519` evaluates to `False`, the `try/catch` verification block is bypassed entirely. Execution proceeds immediately to `counted.add(actor)`. Unverified garbage hex mapped to `sig` fields now incorrectly increments the authorized signature count toward `min_sigs`. 
*Fix:* `if not HAVE_ED25519: return False, ["ERR: Python 'cryptography' library missing, cannot verify signatures"]`

### Vulnerability B: Downgrade to Exit-0 (P0)
Currently, if no valid blobs are resolved, the tool gracefully assumes governance has not populated yet and exits with `0` (success):
```python
    if all(v.startswith("UNGOVERNED") for _, v in verdicts):
        print("\nGOVERNANCE: not active...")
        return 0
```
An average attacker with standard repository write access who wants to bypass governance and push an arbitrary unauthorized spec update simply deletes the `.warrants/` directory. The CI runner will execute `anchor_governance.py`, observe zero governance state, gracefully exit 0, and report a green pipeline.
*Fix:* Introduce an `--enforce` CLI flag that causes `UNGOVERNED` empty states to explicitly `exit 1`. Require this flag in the CI yaml immediately.

### Vulnerability C: Key-State Bricks the Pure Function (P1)
```python
    if store_has_key_state_warrants(recs, bdir):
        return False, ["ERR: key-state warrants present — verify with the warrant CLI"]
```
Design Criterion 2 demands a pure function returning a clear exit code. By preemptively tossing its hands up and throwing a fatal error the instant any key-state rotation happens, `anchor_governance.py` guarantees it will permanently paralyze the project's CI/CD pipeline on the very first succession/rotation event. 
*Fix:* Remove this manual throw limit. Import the warrant CLI dynamically as a module and use its native key-state resolution.

---

## Relation to Prior Reviews

*Note: As an adversarial text reviewer, I cannot execute code. Therefore, any specific test output values, CI failure simulations, and command strings cited below from earlier system states are strictly attributed to the prior execution runs documented by reviewers Codex and Qwen.*

**What is NEW in this audit:**
The entirety of the ADR-007 surface area, vulnerabilities A/B/C, the stateless threshold injection hijack, and the bootstrap bypass are entirely novel findings not covered by the `v0.6.0` pedantic audit (Codex) or the holistic review (Qwen). ADR-007 represents an entirely new boundary of the system that neither previous iteration touched.

**Agreement with Codex (v0.6.0 Pedantic Audit):**
I strongly agree with Codex regarding the critical hazard of "lying green" states in infrastructure. Codex's P1 finding mathematically demonstrated that GitHub Actions' lack of default `pipefail` silently masked standard exits from `false | tail -1` (Codex executed: `bash -c 'false | tail -1'; echo "exit=$?" -> 0`). My Vulnerability B (Downgrade to Exit-0) operates on the exact same philosophical frequency: tools guarding specification protocol must enforce strict bounding logic. If `anchor_governance.py` fails open to exit-0 when `.warrants/` vanishes, it is executing an identical "lying green" mask on CI. 

**Agreement with Qwen (Holistic Analysis):**
I concur with Qwen's holistic critique (G6/S4) concerning the limits of Python dependency as a consensus standard, though for security rather than multi-platform float precision reasons. The maintainer's response to Qwen defended the Python reference as optimizing for "auditability" over universal speed. However, my Vulnerability A explicitly weaponizes Pythonic `try/except` runtime dynamism inside this governance environment: a dynamically un-imported module (`HAVE_ED25519 == False`) allows the script to silently hop its own verification logic and rubber-stamp attacker sigs. The choice of Python inherently requires strict exit guarantees, which this ADR-007 reference tool currently violates.

**Disagreement with maintainer integration strategy (Re Qwen response):**
The maintainer response to Qwen claims that Σ-GLYPH and Warrant are deliberately separated, defending the two CLI outputs because "Warrant must verify decisions about *anything* without importing a compute spec". However, the design of `anchor_governance.py` in ADR-007 represents a deeply flawed integration between the two. As highlighted in my Vulnerability C, the tool arbitrarily crashes rather than executing key-state analysis (`ERR: key-state warrants present...`). If Warrant's true strength is its portable, settlement-grade verification (as praised in Qwen's review), then ADR-007 immediately subverts that strength by building an incomplete Python wrapper that refuses to resolve those verifications programmatically.
