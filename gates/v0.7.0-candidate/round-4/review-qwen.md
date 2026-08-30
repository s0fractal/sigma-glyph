<!--
family: qwen
model_requested: qwen/qwen3-235b-a22b-2507
model_answered: qwen/qwen3-235b-a22b-2507
requested_utc: 2026-08-29T19:11:14+00:00
answered_utc: 2026-08-29T19:11:41+00:00
finish_reason: stop
attempt: 1
max_tokens: 24000
prompt_sha256: 7711812198a43d715082c7fd1671d6558dd8a7c79d38aa7f86932f95780e2248
system_sha256: a87d162d7a1c13ce15756bcf1565daf55701b91fd7e47ed432dfae4d3a819d2a
frozen_commit: e2b4f1eb2a0a7cff0fc2f42b39541c42873118a0
response_sha256: 4cd5ad7562ab06f637c8ac461fab620a64222b503eecbb9434c3a2de8139b021
verdict: ADOPT
-->

The candidate revision introduces significant changes to the normative specification, particularly in Book I, with ripple effects across Books II and III. The anchor section is marked CANDIDATE and carries no signature, so it is not adopted. The review focuses on the normative text of the three Books at the candidate revision, assessing for P0 and P1 issues.

### P0: Two conforming implementations can disagree on a result

**Finding: None.**

The candidate addresses prior defects identified in the gate rounds, including the contradiction between clamping and refusing out-of-domain budgets, the handling of foreign-key mismatches, and the quantification over `uint32` in test vectors. All identified P0 issues from the gate rounds were fixed before this review.

For example, the contradiction in Book I §3.4 between allowing clamping of `ATP > 2³²−1` and §3.6 requiring refusal was resolved by amending §3.4 to explicitly forbid clamping and require refusal per §3.6. The quantifiers in TV-7 and TV-12 were bounded to `n : uint32`, aligning with §3.6's treatment of non-`uint32` inputs as local refusals, not canonical exits.

The machine-readable test vectors are now normative and must agree with the prose. The candidate regenerated all vector files using their generators, ensuring consistency. The anchor set for the candidate was recorded, and the exact command to reproduce it byte-for-byte is available.

No P0 issue remains that would allow two conforming implementations to disagree on a result.

### P1: The text is silent where an implementer must guess, or a normative requirement is unenforceable as written

**Finding: None.**

The candidate clarifies several previously ambiguous points:

1. **Interface and Receipt:** The `eval` interface now explicitly takes three inputs: `term_hash`, `atp`, and `env`. The `Receipt` structure with `exit`, `result_hash`, and `atp_spent` is clearly defined. The fact that `result_hash` alone does not determine `exit` is explicitly stated.

2. **Content Environment:** The `env` is defined as a partial map from NodeHash to bytes with the property `SHA-256(bytes) = key`. The check is performed on the raw buffer before validation, and the distinction between "is this a valid node" and "do these bytes belong under this key" is made clear.

3. **Determinism and Environment Extension:** Determinism is defined over the **demanded** environment. Extending the environment can only change an `unresolved_reference` exit, not a settled one (`normal_form` or `atp_exhausted`).

4. **Admission vs. Canonical Exit:** The distinction between admission (a local refusal before evaluation) and canonical exits is clear. Admission MUST NOT be serialized as a DISSONANCE.

5. **Input Domain:** Inputs outside the declared domain (`atp` not `uint32`, `term_hash` not 32 bytes) MUST be refused locally, before consulting the environment, and not as a canonical exit.

6. **Suite Normativity:** The machine-readable test vector suites for all three Books are now normative parts of the edition. Prose and records MUST be mutually consistent. An edition with a discrepancy is non-conformant. No implementation, including the reference, has precedence.

The candidate also corrects the attribution in Books II and III, replacing the reference to "the discipline of Book I §7" with the actual rule about suite normativity, mapped to each suite's own schema.

All normative requirements are now enforceable. The implementer knows what to do in every case.

### P2: Clarity, naming, structure

**Finding: Minor issues.**

- The typo `преф лайт` was corrected to `префлайт` (preflight) in Book I §3.4.
- The English rendering is informative and is checked against the Ukrainian text for consistency in hashes, keywords, and code blocks. This is sufficient.
- The candidate's argument (ADR-010) is clear and correctly describes the changes.

### P3: Future work

- The owner's disposition on `spec/GOV-anchors.md` leaving the dependency pin unchanged is recorded. The pin refers to "Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1 as anchored in this release." The candidate changes the Books to v0.6.0 and v0.7.0, but the anchor definition `NodeHash(LITERAL, SHA-256(bytes))` and the hashing semantics are unchanged. The owner's decision is that this is correct because the consumed semantics (NodeHash, serialization, validation) are unchanged. Re-pinning the version strings is a breaking change requiring its own MAJOR version and governed adoption. This is a valid governance decision, not a defect in the specification text.

VERDICT: ADOPT
