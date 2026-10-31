# Σ-GLYPH — sigma-resume: resumable Book I computation

**Version:** 1.0.0-rc.1
**Status:** DRAFT STANDARD, with Book I 0.6.0. Adoption is a signed record (AGENTS.md rule 2), not this line.
**Scope:** how one Book I computation is split into budgeted segments, carried as a checkpoint, resumed by anyone,
and verified by replay. Book I governs the transition; this document adds nothing to it.

Key words MUST / MUST NOT / SHOULD / MAY are to be read as in RFC 2119. The schema strings below
(`…@draft-1`) are names of byte formats in use, not statuses: they are part of every `computation_id`, so
renaming them would change every identity this document defines.

## 1. Identities

**ComputationRoot.** `{schema, runtime_semantics_id, cost_model_id, input_term_hash, environment_id}` with
`schema = "sigma-resume.root@draft-1"`. `computation_id` MUST be the SHA-256 of the root's canonical JSON:
keys sorted, no whitespace, UTF-8. No budget is part of the root. The runtime profile is part of the root: one
term under two profiles is two computations.

**Environment.** A frozen manifest of the NodeHashes a computation may demand. `environment_id` MUST be the
SHA-256 of the canonical JSON `{schema: "sigma-resume.environment@draft-1", hashes: [sorted lowercase hex]}`.
Delivery of bytes is separate from identity: a hash outside the manifest is a semantic answer
(BLOCKED_REFERENCE), a hash in the manifest whose bytes are not delivered is a local one (EVIDENCE_UNAVAILABLE).

**MachineState.** The bytes are `"SGS1" ‖ computation_id (32 bytes) ‖ tree`, the tree in preorder: `A` for an
APPLY, then its two children; `T`, `L`, `R` or `D` followed by 32 bytes for a thunk, a LITERAL, a REF or a
DISSONANCE. `state_id` MUST be the SHA-256 of these bytes. The encoding MUST keep a thunk apart from its
materialization: a cold thunk and the node it materializes to share a term hash and MUST NOT share a `state_id`.
Bytes that are not exactly such an encoding (an unknown tag, a truncated payload, trailing bytes) MUST be refused
as INVALID_ENCODING.

**Checkpoint.** `{schema, computation_id, state_id, credit_total, spent_total, peak_semantic_size,
parent_checkpoint_id, transition_claim: {actions}}` with `schema = "sigma-resume.checkpoint@draft-1"`. A
checkpoint MUST be canonical JSON, and its integers MUST lie in 0..2^53−1; `spent_total ≤ credit_total`.
Duplicate names, floats, booleans, unknown fields and non-canonical bytes MUST be refused, never normalized.

## 2. No control state

Book I's transition derives the leftmost-outermost demanded action from the tree on every step, and which action
it picks does not depend on the remaining budget: the budget only decides whether that action is affordable. The
tree is therefore the whole operational state.

**Segmentation invariance (MUST).** Any split of the same total credit into segments MUST reach the same state,
spent and outcome as one segment with all of it.

## 3. advance(checkpoint, state, env, additional_credit)

Credit accumulates: what a segment may spend is `credit_total + additional_credit − spent_total`.

| Outcome | Kind | Meaning |
|---|---|---|
| NORMAL_FORM | kernel | no next action under the fixed semantics |
| PAUSED | kernel | the next action costs more than is available; nothing changed |
| BLOCKED_REFERENCE | kernel | the demanded hash is outside the manifest (it is named) |
| EVIDENCE_UNAVAILABLE | local | in the manifest, bytes not delivered here |
| CAS_MISMATCH | local | the bytes do not hash to their key |
| INCOMPLETE | local | an action limit or a deadline stopped the run; the last atomic state is kept |
| ADMISSION_REFUSED | local | credit or state over this host's ceiling, refused before decoding |
| RESOURCE_FAULT | local | a configured size or depth limit was breached |

**A local outcome never stands in for an answer (MUST).** Only the three kernel outcomes say anything about the
computation; a local one says what this host could or would not do.

**PAUSED changes nothing (MUST).** An action that costs more than is available is not taken: the state and
`spent_total` stay as they were, and a later grant of credit continues from them.

A non-genesis thunk needs 1 before its fetch, so at available credit 0 there is no store read.

**Integers are never wrapped (MUST).** A credit total beyond 2^53−1 MUST be refused, not wrapped or clamped.

**Admission precedes decoding (MUST).** A state larger than this host admits MUST be refused as
ADMISSION_REFUSED before it is decoded.

## 4. verify(expected_root, env, checkpoint, state)

**The verifier chooses the root and its context (MUST).** A checkpoint is verified against the root the
verifier expects, under the environment, runtime and cost model of that root; a difference in any of them is
CONTEXT_MISMATCH. Checkpoint and cycle verification share this check.

**Replay goes to the claimed `spent_total`, not the claimed credit (MUST).** `spent` strictly increases, so
exactly one state has it; a prefix taken with credit left over is therefore still verifiable.

**REPLAYED means reproduced (MUST).** A verifier MUST report REPLAYED only after it reproduced the state, the
spent and the peak itself, from the root or from a checkpoint it replayed before. The code then says what the
checkpoint is at its own credit: the kernel outcome if no further action fits, or PREFIX, a verified reachable
prefix with credit for more. PREFIX is not terminal and is never a kernel outcome.

**No signature is consulted (MUST NOT).** Whoever signed a checkpoint, one this verifier did not replay is not
REPLAYED.

| Refusal | When |
|---|---|
| INVALID_ENCODING | non-canonical bytes, or a malformed id |
| STATE_MISMATCH | the state bytes are not the ones the checkpoint names |
| UNVERIFIED_PREFIX | replay does not reach the claimed state |
| ROOT_MISMATCH | the checkpoint belongs to another computation |
| CONTEXT_MISMATCH | the environment, runtime or cost model differs |
| NOT_ASSESSED | a local limit stopped the replay |

## 5. Cycles

`verify_cycle` replays from the chosen root to exactly the entry's spent, then replays the period one action at a
time. **CYCLE_PROVEN requires all of these (MUST):** at least one priced action; the claimed cost exactly; no
terminal state on the way; the same machine state at the end, not merely the same term hash.

**A malformed witness is refused by name, before any replay (MUST).** A witness MUST have exactly the schema's
fields, valid digests and in-domain integers, and no more actions than cost; any other is INVALID_CYCLE_WITNESS.
A period costlier than this host admits is a local NOT_ASSESSED, not a verdict on the witness.

## 6. The profile

**The Book I profile is this specification's (MUST).** `runtime_semantics_id =
"sigma-book1-0.6.0/hash-thunk/leftmost-outermost"`, `cost_model_id = "atp/size-priced/adr-001+adr-003"`: the
transition and the prices are Book I's, unchanged. A root naming any other profile is another computation and
outside this document. The reference implementation carries a second, experimental profile (Y, M and W
primitives, `impl/sigma_resume.py`), which no claim of this document covers.

## 7. Implementations (informative)

`impl/sigma_resume.py` (Python) and `book1 resume` (`impl-rs`, also built for wasm32 in `impl-rs/wasm-resume`)
implement this document; `tests/resume_differential.py` holds them equal. Host persistence of checkpoints, a memo
cache and attestation by signatures are outside this document: the first two are a host's, the third is Warrant's.
