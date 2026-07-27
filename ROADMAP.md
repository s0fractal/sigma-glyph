# Σ-GLYPH Roadmap

This document consolidates all planned breaking changes, milestones, and major open fronts. Sigma-glyph follows specification-first development: ADRs (Architecture Decision Records) in `proposals/` are debated, then adopted into normative Books with a version bump and new Specification Anchors.

---

## Decision Process

How an ADR moves from PROPOSED to adopted (and how disputes end):

1. **Multi-model adversarial review.** An ADR needs reviews from at least 3 independent models. Every P0/P1 finding must be closed (spec text fixed, or finding rebutted in writing) before adoption; an ADR with an open P1 stays PROPOSED. Silence is not consent.
2. **Reference implementation gate.** The candidate rule is implemented and `ALL PASS` on the updated vectors is a **precondition** for adoption, not a follow-up task.
3. **Maintainer decision.** An interim AI maintainer designated by the project founder (currently Claude) accepts or rejects, with written rationale filed in `reviews/`. Rejections are as binding as acceptances and equally documented.
4. **Planned transition.** Interim maintainership is temporary; the target is collective governance over Specification Anchors (see Multi-Signature / Threshold Governance, v0.6+). Until then, the maintainer-of-record is accountable for every accepted change.

---

## Milestone: v0.5.0 (Breaking release, shipped 2026-07-05)

> Current repo bundle is **v0.6.6** (see README and `spec/ANCHORS.txt`); the
> v0.5.0 entry below is retained as milestone history. Its "Known limitations"
> were closed by the v0.6 Federation + Governance releases (see below).

**Status:** DRAFT STANDARD (superseded by the v0.6.x line).

**Scope:**
- Book I (TRUTH) — bit-exact computational core: **hash-thunk machine** (lazy left-spine, ADR-003) with **size-priced ATP** under the hash-leaf model (ADR-001), genesis intrinsic I/K/S
- Book II (NAVIGATION) — wave layer with **entropy–coherence coupling** (ADR-002); Resonance Identity rewritten (crystallization to `{am=65535, en=−32768}`)
- LORE — non-normative cultural context

**Reference implementations:** `impl/sigma_glyph.py` (Book I) + `impl/sigma_wave.py` (Book II) — ALL PASS; conformance `vectors.json` (46) + `wave_vectors.json` (9); property suite incl. the memory-bound invariant.

**Adoption trail:** three ADRs, three dedicated reviews (Codex/OpenAI, Gemini/Google, DeepSeek — Decision Process quota), five adjudication warrants, adoption warrants in `.warrants/`. Serialization and NodeHashes unchanged from v0.4.x — only evaluation semantics and ATP accounting changed (migration guide in CHANGELOG).

**Settled additionally in v0.5:**
- Memory bound as a normative invariant: `materialized size − 1 ≤ spent`
- Divergence class: undemanded unresolved subtrees never affect results
- Genesis axioms intrinsic (FALSE is a theorem, needs no intrinsic status)
- `div_round_half_up` = round-half-away-from-zero (Book II §3; negative-tie wave vector pins it)

**Known limitations (both closed in v0.6):**
- ~~No federation/gossip protocol (wave sync is future work)~~ → Book III shipped (v0.6.0)
- ~~Wave annotation trust/reputation undefined~~ → selection policies + key-state via Warrant v0.3 (Book III)

---

## Shipped: v0.5.0 gate history (2026-07-05)

Reviews 3/3 (Codex, Gemini, DeepSeek) confirmed: Hash-Leaf Size Model as the ADR-001×003 composition (option-2 broken by the `(S K K) T` attack; option-3 proof audited), Genesis Intrinsic Rule, ADR-002 with the §5.1 supersession. Implementation gate passed same day: hash-thunk oracle, 46 Book I vectors + 9 wave vectors, property suite with the memory bound. Full trail: `reviews/2026-07-*-adr-gate*.md` + `.warrants/`.

### ADR-001: Size-Priced ATP

**Motivation:** Current ATP accounting is step-count only. R-S doubles term size per step → O(2^ATP) memory explosion. Size-priced ATP couples work *and* memory into a single bound.

**Status:** Proposal with worked integer examples, candidate test vectors.

**Impact:**
- Breaking: ATP costs change for all non-trivial terms
- Breaking: New test vectors TV-11+ replace TV-6, TV-7
- Breaking: Specification Anchors for Book I bump

**Adoption criteria:**
- Multi-model review (Claude, Codex, Kimi, Qwen, DeepSeek done; GPT/Gemini pending)
- Reference impl update + ALL PASS
- Community consensus (issue/PR feedback)

---

### ADR-002: Entropy-Coherence Coupling

**Motivation:** Wave interference is currently blind to term structure. Entropy-coherence coupling makes phase sensitive to term "order" (reduction depth or other structural measure).

**Status:** Proposal with worked integer examples.

**Impact:**
- Breaking: Wave vector computation changes (Book II)
- Breaking: Specification Anchor for Book II bumps
- Non-breaking for Book I (hash unaffected)

**Adoption criteria:**
- Clear use case demonstration (what does this enable?)
- Multi-model review
- Reference impl update (wave layer is separate module)

---

### Combined v0.5.0 Scope

If both ADRs adopted:
- Book I anchor bumps (ATP semantics)
- Book II anchor bumps (wave semantics)
- Test vectors TV-1…TV-10 replaced/extended
- CHANGELOG notes breaking changes clearly
- Migration guide for existing implementations

**Timeline:** When ready. No rush. Spec quality > speed.

---

## v0.6: Federation (SHIPPED v0.6.0 "Sovereign Views"; hygiene v0.6.1)

### Book III: FEDERATION — selection-only annotation federation

**Architecture decided** (ADR-006, gate 3/3 closed 2026-07-08, F1-strict):
annotation assertions travel as Warrant v0.3 records; a jurisdiction's
selection policy picks zero-or-one assertion per node (ties surface as
ConflictSets that clients MUST NOT merge); `interfere()` is structural-only —
the interference fold died at the gate to verified non-associativity.
Trust/reputation = Warrant key state + policy thresholds; conflict
resolution = settlement, not arithmetic.

**Shipped:** `spec/book-3-federation.md` anchored; implementation gate passed
(Codex blocked→fixed, Gemini verified); Book II §10; two implementations
(`impl/sigma_federation.py` + `impl-go/`, differential-tested); 21 vectors.
**Landed post-release:** `examples/two-jurisdictions/` — first live exercise
(two real warrant stores, file-copy gossip, divergent sovereign views,
ConflictSet, replay resistance; in CI). **Still open:** transport profile
guidance beyond file-copy (cadence/peering stay an implementation profile,
not spec); settlement-grade candidate extraction in the demo (threshold +
key-state via the warrant CLI).

---

## Long-horizon North Star: exchange experience, not state

The ecosystem should eventually let one digital entity receive an **episode of
another entity's experience** rather than merely copy its terminal state,
weights, cache, or verdict.

Here, “experience” is an operational term, not a claim about phenomenal
consciousness. It means a content-addressed, authority-aware decision episode
whose relevant perspective can be reconstructed:

- what was observed and what was not available;
- the historical view, jurisdiction, policies, key-state, and resource bounds;
- the alternatives that were considered or remained reachable;
- the action or decision, its reasons and evidence;
- the resulting observations, later challenges, and settlement history.

The receiving machine does not become the source machine and does not obtain
privileged access to an unknowable first-person interior. The target is
**perspective-preserving third-person replay**: an observer can re-execute the
source's declared transformation under the source's committed context, inspect
why that path was available, and distinguish that reconstruction from its own
interpretation.

Two operations must remain separate and equally first-class:

1. **Historical re-experiencing** — replay the episode under the exact committed
   context that existed then. The original must never be silently repaired by
   later knowledge.
2. **Contemporary reinterpretation** — replay the same immutable episode under a
   new view, policy, or body of evidence. The new result is a new,
   content-addressed interpretation, not a rewrite of the old experience.

This direction composes the ecosystem rather than assigning the whole problem
to one repository:

- **Warrant** carries provenance, authority, lifecycle, key-state, checkpoints,
  reasons, and the right to treat an episode as admissible.
- **OAIP** projects heterogeneous observations and decisions into an explicit
  shared semantic interface without pretending that the projection is the
  source itself.
- **Σ-GLYPH** supplies bounded executable structure, wave/navigation semantics,
  sovereign views, explicit divergence, and eventually resonant precedent:
  discovering which prior experience is relevant to the present context.

### Invariants for every step toward this North Star

- **No verdict laundering.** A copied answer without its executable context is
  evidence at most, never transferred experience.
- **No retrospective identity.** Replaying a perspective is not becoming its
  author; similarity of outcome is not identity of subject.
- **No silent context merge.** Historical and contemporary views, and distinct
  jurisdictions, stay separately named even when they agree.
- **Causal legibility before narrative plausibility.** Every claimed dependency
  must bind to authenticated bytes or be explicitly marked unavailable,
  projected, or inferred.
- **Bounded stranger re-execution.** An episode received from an untrusted peer
  must be total and deterministically resource-bounded before it is safe to
  “re-live”.
- **Authority and privacy survive transfer.** Replayability does not imply that
  every observation may be disclosed; selective revelation and revocation
  boundaries are part of the experience contract.
- **Counterfactuals do not rewrite history.** Alternative replays branch from a
  committed episode and remain distinguishable from what actually settled.

### Research progression

1. Define a minimal cross-project **experience/decision-episode profile** and
   identify which context dependencies must be committed versus explicitly
   absent.
2. Produce one hermetic historical episode that replays byte-identically in two
   independent implementations.
3. Reinterpret that same episode under a new governed view and emit a canonical
   explanation of what changed, while preserving the historical result.
4. Exchange episodes between sovereign peers and demonstrate useful learning
   from precedent without sharing model state or collapsing jurisdictions.
5. Add selective-disclosure or proof-carrying profiles so a peer can verify the
   relevant causal structure without receiving every private observation.

The decisive gate is not “did the second machine copy the first machine's
answer?” It is: **did it acquire a portable, inspectable episode that it can
faithfully replay in the old context, honestly reinterpret in a new one, and
cite without erasing either perspective?**

### Relation to the near-term wedge (so this stays tethered)

This North Star is **not a pivot away from** the near-term product — it is the
same object seen at full extension. The immediate, fundable capability is
*action provenance for regulated agents*: a verifiable record of what an agent
decided, under whose authority, on what evidence, that a third party can
re-check. A "decision episode that replays under its committed context" **is**
that provenance record — just with its context made complete enough to replay,
not only to audit. So every step earns its keep at the wedge first: the
episode/decision profile is a richer Warrant reason; historical replay is
settlement re-verification; selective disclosure is the privacy story
compliance already asks for. If a North-Star step does not also strengthen the
verifier-first wedge, it waits. The mission constrains the roadmap; it does not
license scope that the near-term product cannot justify.

**Status:** philosophical and architectural direction, NON-NORMATIVE. Every
wire format, runtime, authority rule, privacy rule, and use of the word
“causal” still requires its own ADR, adversarial countervectors, reference
implementation, and governance adoption.

Method note: [Compositional Countervectors — from metaphor to engineering
method](docs/compositional-countervectors.md).

---

### Provable Computation Layer (ZK / SNARK)

**Motivation:** `eval(h, ATP)` is deterministic → amenable to SNARKs. A ZK-friendly circuit for SKI reduction would enable verifiable compute.

**Scope:**
- Circuit design for R-I/R-K/R-S/R-R
- Proof of ATP bound compliance
- Possibly integration with existing zkVM (RISC Zero, SP1, etc.)

**Status:** Research. No concrete proposal.

---

### Multi-Signature / Threshold Governance

**Motivation:** LORE mentions "Pantheon" (cultural fork). If sigma-glyph governance moves on-chain or multi-sig, the spec itself could become a governed artifact. Concretely: the anchor trail and the warrant trail run parallel and unlinked; the interim maintainer is one actor with one key; the maintainer is a model, and models retire on a schedule.

**Status: SHIPPED — `spec/GOV-anchors.md` is STANDARD (v1.0.0), the project's first.** ADR-007 adopted (gate 3/3 blind: GPT-5, Gemini, DeepSeek + Kimi verification), governed since v0.6.2 (roster 2-of-3 {s0fractal, claude-fable-5, codex}), promoted DRAFT→STANDARD at v0.6.4 through a *second* 3-family gate on the promotion itself (unanimous PROMOTE-WITH-AMENDMENTS). That gate earned its keep: Gemini alone found a P0 liveness self-destruct (the scoped key-state refusal deadlocks the append-only chain on its first roster rotation) — fixed with `resolved_key_state` acknowledgment + a transition vector, in both implementations. STANDARD now means a defined bar (§0: frozen schemas/mechanism, pinned dependencies, SemVer). The interim single-maintainer trust point is retiring on schedule: releases need 2-of-3 warrant signatures, no single key — including the maintainer's — can bless one. On-chain/DAO (G2) rejected — Book I owns the only consensus this system has.

---

## Release Discipline

**Version scheme:**
- `v0.x.y` — draft standard (breaking changes allowed with clear notice)
- `v1.0.0` — first stable release (breaking changes require major bump)

**Specification Anchors:**
- Every spec version gets a `NodeHash(LITERAL, atom = SHA-256(document_bytes))`
- Anchors published in `spec/ANCHORS.txt`
- A spec update is formally a fork with an explicit ancestor

**Breaking change protocol:**
1. File ADR in `proposals/`
2. Solicit multi-model review
3. Update reference impl
4. Bump version, update CHANGELOG
5. Generate new Specification Anchors
6. Announce breaking change window (e.g., "v0.5 adopts ADR-001 in 2 weeks")

---

## How to Contribute

**For implementers:**
- Run `python3 impl/sigma_glyph.py` — if it passes, you're consensus-compatible
- File issues for spec ambiguities (Book I) or navigation questions (Book II)
- Propose ADRs for missing features

**For reviewers:**
- Read `reviews/README.md` first (settled points, no redundant feedback)
- Run the impl before reading prose ("run first, read second")
- File reviews in `reviews/YYYY-MM-model.md`

**For users:**
- v0.4.x is stable for early experiments
- v0.5 will be breaking — plan migration window
- Subscribe to repo releases for announcements

---

*Roadmap is living. Check back after each release.*

## Formal verification (from the Qwen web review, 2026-07)

**Four targets mechanized (Lean 4 core, no mathlib; `proofs/`):**
- ADR-001 **memory bound** — `SizeBound.lean` (§3.4 accounting ⇒ `size ≤ spent + 1`) + `bridge_check.py` (step premise on live traces).
- Book II **wave algebra** — `WaveAlgebra.lean` (interfere range closure, zero-amplitude cascade, Left Dominance, the §5.1 crystallization fixed point, fold non-associativity) + `wave_bridge_check.py` (582-case Lean-vs-oracle differential).
- Book I **byte-level correspondence** — `MachineBytes.lean` + a from-scratch FIPS 180-4 `Sha256.lean` (serialize injectivity/round-trip/canonicity, §4.1 validation totality, reserved-opcode rejection, genesis + FALSE + Invalid-Object hash pins) + `byte_bridge_check.py` (334-buffer differential incl. every conformance CAS key).
- Book I **evaluator determinism/totality + memory bound** — `EvalMachine.lean`: a faithful hash-thunk machine (built on `MachineBytes`, so redex recognition rides the proven byte layer) that is total by construction (fuel-indexed) and deterministic (a function), with `spent ≤ atp` proven for all terms (`eval_spent_le`), step cost ∈ `[1, remaining]` (`step_cost_le`/`step_cost_pos`), and the **ADR-001 memory bound `size ≤ spent + 1` re-proven directly on the concrete evaluator** (`size_step`/`evalHash_size_bound` — the step↔cost row correspondence, now a theorem not a classifier) + `eval_bridge_check.py` (33-vector Lean-vs-oracle differential on result hash AND atp_spent, incl. Omega divergence).

The four Lean fronts are layered — `EvalMachine` → `MachineBytes` → `Sha256` — each standing on the proven one below.

**Remaining:** a Rust production implementation (the last non-Lean Qwen item; would be a third independent Book I). Vectors remain the contract.
