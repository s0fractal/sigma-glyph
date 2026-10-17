# sigma-resume, draft 1: the resumable Book I kernel as implemented (DRAFT, not reviewed)

**Status:** DRAFT. This describes `impl/sigma_resume.py` and `book1 resume`
(impl-rs) on the local branch `resume/p1-p2-reference`. Book I, its vectors, and
`eval_receipt`/`eval_hash` are unchanged and remain the specification. Nothing
here is adopted. Adoption is a threshold warrant signed by roster keys
(AGENTS.md), and this text has had no independent gate.

## 1. Identities

- **ComputationRoot** = `{schema, runtime_semantics_id, cost_model_id,
  input_term_hash, environment_id}`.
  - `computation_id` is the SHA-256 of its canonical JSON.
  - No budget is part of it.
  - The runtime profile is part of it: one term under two profiles is two
    computations.
- **Environment** = a frozen manifest of NodeHashes. `environment_id` is the
  digest of the sorted manifest. Delivery is separate from identity.
- **MachineState** bytes are `b"SGS1" ‖ computation_id(32) ‖ tree`. The tree is
  written in preorder: `A` for APPLY, then `T`/`L`/`R`/`D` plus 32 bytes for
  thunk / literal / ref / dissonance. `state_id = SHA-256(bytes)`. The codec
  keeps a thunk apart from its materialization, and it does not depend on
  physical sharing.
- **Checkpoint** = `{schema, computation_id, state_id, credit_total,
  spent_total, peak_semantic_size, parent_checkpoint_id, transition_claim
  {actions}}`.
  - It must be strict canonical JSON.
  - Integers must lie in 0..2^53−1.
  - `spent ≤ credit`.
  - Duplicates, floats, bools and unknown fields are refused.

## 2. No control state

Book I's `step5` derives the leftmost-outermost demanded action from the tree on
every call. Which action it picks does not depend on the remaining budget. The
budget only decides whether the action is affordable. This was measured over
20,114 (state, budget) pairs, and over 60,729 for the rich profile.

So the tree is the whole operational state. **Segmentation invariance** follows
from determinism plus pre-checked, atomic charging: any split of the same total
credit reaches the same state, spent and outcome. Measured: 12,649 partitions.

## 3. advance(checkpoint, state, env, additional_credit[, max_actions])

Credit accumulates: `available = credit_total − spent_total`.

| Outcome | Kind | Meaning |
|---|---|---|
| NORMAL_FORM | kernel | no next action under the fixed semantics (not "TRUE") |
| PAUSED | kernel | the next action costs more than is available; nothing changed |
| BLOCKED_REFERENCE | kernel | the demanded hash is outside the manifest (it is named) |
| EVIDENCE_UNAVAILABLE | local | in the manifest, bytes not delivered here |
| CAS_MISMATCH | local | the bytes do not hash to their key |
| INCOMPLETE | local | an action limit / deadline stopped the run; the last atomic state is kept |
| ADMISSION_REFUSED | local | credit or state over this host's ceiling, refused before decoding |
| RESOURCE_FAULT | local | a configured size/depth limit was breached |

A local outcome never stands in for an answer. Normal-form detection costs
nothing. A non-genesis thunk needs 1 before its fetch, so at credit 0 there is no
store read.

## 4. verify(expected_root, env, checkpoint, state[, cache])

**The verifier chooses the root and its context.** CONTEXT_MISMATCH covers the
environment, runtime and cost model. Checkpoint verification and cycle
verification share this check (PR #62 review, R1).

**Replay goes to the claimed `spent_total`, not the claimed credit.** `spent`
strictly increases, so exactly one state has it. An atomic prefix taken with
credit left over (an action limit or a deadline) is therefore still verifiable,
from the root or from a parent this verifier replayed before (R2). The cache is
keyed by verifier identity.

**REPLAYED** means this verifier reproduced the state, spent and peak. The code
then says what the checkpoint is at its own credit:
- the kernel outcome, if no further action fits that credit;
- **PREFIX**, if it is a verified reachable prefix with credit for more. PREFIX
  is not terminal and is never a kernel outcome.

`transition_claim.actions` is segment-local and informational. Reachability does
not rest on it.

| Refusal | When |
|---|---|
| INVALID_ENCODING | non-canonical bytes, or a malformed id: `computation_id` and `state_id` must be 64 lowercase hex, parent null or 64 lowercase hex (R3). Never a host exception, with or without a cache. |
| UNVERIFIED_PREFIX | replay does not reach the claimed state |
| ROOT_MISMATCH | the checkpoint belongs to another computation |
| CONTEXT_MISMATCH | the environment, runtime or cost model differs |
| NOT_ASSESSED | a local limit stopped the replay |

No signature is consulted.

## 5. Cycles

`verify_cycle` replays from the chosen root to exactly the entry's spent (spent
strictly increases, so that state is unique), then replays the period one action
at a time. CYCLE_PROVEN requires all of these:
- at least one priced action;
- the claimed cost exactly;
- no terminal state on the way;
- the same machine state at the end, not merely the same term_hash.

Under the Book I profile, no Sigma term with a state cycle is known: 0 among all
3.1M SKI terms of ≤ 8 leaves. The rich profile (Y, M, W primitives; another
session, `f371005`) has real ones: `Y I` (period 2), `M M` (period 1).

Before any replay, the witness must have exactly the schema's fields, valid digests,
in-domain integers, and no more actions than cost. Any other witness is
INVALID_CYCLE_WITNESS (re-review N2). The period's cost is admitted against the
same per-call `max_atp` that `advance` applies. A costlier period is a **local**
`NOT_ASSESSED: ADMISSION_REFUSED`, not a verdict on the witness (re-review N1).

## 6. Second engine: `book1 resume <request.json>`

- **Request:** `{available, state (hex), manifest [hex], delivered {hex: hex},
  max_actions?}`.
- **Response:** `{outcome, state, spent, actions, peak, missing}`.
- **Sharing:** one `step` serves both the Book I conformance path and resume mode,
  through a fetch callback. Book I conformance stays 49/49.
- **WASM:** `impl-rs/wasm-resume` builds the same `main.rs` for wasm32, and
  `resume_worker.mjs` runs one request per disposable worker with a deadline
  (DEADLINE is local).
- **Agreement:** `tests/resume_differential.py` holds Python = Rust on 2268 Book I
  runs covering all six reachable outcomes, and on 1548 rich-profile runs
  (R-N69; `runtime` field in the request, `897f1e7`). wasm = native on 60. Four
  broken engines are caught (`resume_differential_controls.sh`).

## 7. Matrix

`tests/resume_test.py`: N01–N37, N61/N62, the rich-profile cases and the PR #62
review regressions (R1–R3, SG04, N1, N2), **46 PASS, 0 FAIL, 3 UNRUN**:
- N05: host persistence;
- N15: no memo;
- N27: attestation is Warrant's.

`tests/resume_mutants.py`: 22 mutants, each killed by its own case (6 undo review
fixes). All four suites now run in CI (`.github/workflows/ci.yml`).
