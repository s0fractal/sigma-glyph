<!--
family: deepseek
model_requested: deepseek/deepseek-v4-pro-0813
model_answered: deepseek/deepseek-v4-pro-0813
requested_utc: 2026-08-29T17:06:33+00:00
answered_utc: 2026-08-29T17:16:34+00:00
finish_reason: stop
prompt_sha256: 7b7cb164bbb90151e61bcef8fd0cf92362d57432ef157767ce447251f1682ddb
system_sha256: a87d162d7a1c13ce15756bcf1565daf55701b91fd7e47ed432dfae4d3a819d2a
frozen_commit: 1e91131c891dcc8f8b02ee27957330ab2251e2b6
response_sha256: 59f8954596826d8339fdf681be3f1de01d83ed83f3e1ee3437fb4378e9b9775f
verdict: REJECT
-->

The candidate is not adoptable in this shape. I reviewed the supplied normative bytes; I did not rely on CI, prior gates, or author assertions of fixed findings.

### P0 — §3.5 contradicts itself and permits two conforming engines to disagree

§3.5 contains two irreconcilable requirements:

- “запис, якого виконання не вимагало, не впливає на результат” / “an entry the evaluation never demanded does not affect the result.”
- “Ширша перевірка (наприклад, валідація всього середовища на вході) дозволена … її наслідком MUST бути та сама локальна відмова” / “a wider check … is permitted … its consequence MUST be that same local refusal.”

For a poisoned entry that is never demanded, the first clause says the entry must not affect the result; the second says an implementation that validates the whole environment on admission must locally refuse. That is a direct contradiction in the same paragraph.

Concrete executable counterexample:

- `term_hash = H(I) = 2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162`
- `atp = 10`
- `env1 = {}`
- `env2 = { 0000000000000000000000000000000000000000000000000000000000000000 : 0001a83dd0ccbffe39d071cc317ddf6e97f5c6b1c87af91919271f9fa140b0508c6c }`

The value is canonical `I` bytes, which hash to `H(I)`, not to the zero key. The zero key is never demanded when evaluating `H(I)`.

- Implementation A, which checks the CAS property only for hashes actually resolved, returns `Receipt{ normal_form, H(I), 0 }` on `env2`.
- Implementation B, which performs the permitted whole-environment validation on admission, detects the mismatched undemanded entry and locally refuses, returning no `Receipt`.

Both behaviors are explicitly permitted by §3.5. This also violates the immediately following “Розширення середовища (MUST)” stable-extension clause: moving from `env1` to `env2` preserves answers to all already-demanded hashes (there are none), yet a conforming whole-env validator does not return the same `Receipt`. The round 1 “fix” did not close this; it still permits the wider check and still mandates local refusal.

### P0 — The bundle is inconsistent with its own governance STANDARD, deliberately unresolved

The candidate changes the anchored Books to Book I v0.6.0, Book II v0.7.0, Book III v0.7.0, but leaves `spec/GOV-anchors.md` unchanged. That document remains pinned:

> **Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1** as anchored in this release

and §0 says changing a pinned dependency is itself a breaking change requiring a new MAJOR document version.

Concrete document state:

- Proposed `v0.7.0` anchor-set contains `spec/book-1-truth.md` with `Version: 0.6.0`, and Books II/III with `Version: 0.7.0`.
- It still contains `spec/GOV-anchors.md` `Version: 1.0.2` with the old pins above.

Two conforming governance verifiers can disagree:

- Verifier A treats the normative-dependency preamble and §0 as binding, sees the pinned dependency versions have been replaced without a GOV MAJOR, and refuses to authorize the candidate.
- Verifier B follows only the seven-step §3 procedure, which states authorization depends solely on jurisdiction, lineage, cardinality and quorum, and authorizes the same candidate.

This is exactly the divergence ADR-010 records as unresolved. An unresolved P0 at the governance layer is still a P0 in the candidate.

### P1 — `NodeHash(bytes)` is undefined for §4.1-invalid bytes, leaving the CAS check ambiguous against §4.2

§3.5 requires `NodeHash(bytes) = key` for each resolved content-environment entry. §3.5 also retains the old failure mode:

> байти не проходять валідацію §4.1 → матеріалізується Canonical Invalid Object (§4.2)

For bytes that fail §4.1, there is no valid SigmaNodeV2, so `NodeHash(bytes)` per §2 is not defined. Two conforming readings result:

Concrete counterexample:

- `b = 0x03 0x01` (opcode `0x03`, invalid under §1.2/§4.1)
- `k = SHA-256(b)`
- `term_hash = H(REF(k)) = SHA-256(01 01 || k)`
- `atp = 10`
- `env = { k : b }`

Reading 1: `NodeHash(bytes)` means raw `SHA-256(bytes)`. The CAS property passes because `SHA-256(b) = k`; `force(k)` then reads invalid bytes, applies §4.1/§4.2, and returns a canonical `Receipt` with `result_hash = af69b517…ba4507` and `atp_spent = 4`.

Reading 2: since `b` is not a valid SigmaNodeV2, `NodeHash(bytes)` is undefined; the CAS property cannot hold for the resolved key, and per §3.5 the implementation locally refuses rather than returning a canonical `Receipt`.

The candidate needs to say explicitly whether the CAS property is checked over raw byte hashes or over valid-node hashes, and what happens when an invalid buffer raw-hashes to the key.

Therefore:

VERDICT: REJECT
