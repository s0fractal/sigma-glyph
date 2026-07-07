# ADR-006: Annotation federation — the v0.6 front

**Status:** PROPOSED, rev 1 (2026-07-08) — design-stage; opens the v0.6 cycle. Needs the standard adversarial gate (≥3 model families) on the architecture choice before any Book III / protocol text is drafted.
**Origin:** Book II has promised this since v0.3.0: *"Розбіжність анотацій одного вузла між нодами — не форк обчислення; це предмет федеративного узгодження (протокол — окремий майбутній документ)."* This ADR is that document's design gate. The enabling event is external: **Warrant v0.3** now provides settlement-active jurisdictions, executable re-litigation, and key-state — trust machinery Book III would otherwise have to invent. (Pinned snapshot for reviewers: `proposals/refs/warrant-SPEC-v0.3-snapshot.md`.)

## Problem

Two nodes annotate the same NodeHash with different waves. Book II's axiom
says this is not a compute fork (wave ∉ hash — settled v0.3.0), but says
nothing about what a *federation* of annotators converges to, or whether it
converges at all. Concretely undefined today:

1. **Identity of an assertion.** Who said `wave(h) = {ph, am, en}`, under
   what authority, and how does a stranger verify that without trusting
   the transport?
2. **Merge.** Node A holds `{ph=8192, am=40000, en=-100}` for `h`, node B
   holds `{ph=8192, am=20000, en=+50}`. What does a node that hears both
   store? Is merge deterministic, order-independent, bounded?
3. **Staleness.** Annotations age. Book II §5.1 already gives partial
   amplitude a quadratic decay under self-interference — is decay also
   the aging law, or do annotations live forever once asserted?
4. **Spam and weight.** Amplitude is mass is visibility (Gravity).
   Unpriced assertions of `am=65535` are free visibility. What makes
   asserting weight *cost* something?
5. **Jurisdiction.** Must all federants agree? (No — that would be
   consensus, which Book I owns for results and nothing else needs.)
   Then what bounds the subjectivity so two verifiers can at least name
   *which* view they disagree about?

## Candidate architectures

### F1 — Warrant-carried assertions (lean on v0.3 wholesale)

An annotation assertion is a warrant `accept` whose subject is a
JCS blob `{"node": "<hex64>", "wave": {"ph":…, "am":…, "en":…}}`, filed
under an annotation policy, signed by a bound key. Federation = syncing
warrant stores. Then every open question above maps onto machinery that
already survived a three-family gate:

- identity/verification → WarrantID + Ed25519 + key state (§5.1);
- jurisdiction → settlement-active roots (§9): an annotation *view* IS a
  jurisdiction; two verifiers with different genesis sets disagree
  explicitly, not silently;
- disagreement → not a fork, a re-litigation surface: a competing
  assertion must carry new evidence or a new outcome fingerprint;
- spam → policy thresholds + the §7 flooding note; assertions are
  signed, attributable, and refusable at filing.

Cost: heavyweight per-assertion (a warrant per wave update); merge is
*selection* (which assertion does my jurisdiction accept), not
arithmetic — the wave algebra of Book II §5 is unused at the federation
layer.

### F2 — Interference as the merge operator (algebra-native)

Merging two assertions for the same node = `interfere(w1, w2)` — the
federation layer reuses the one operator Book II already pins to 17+
vectors. Decay is aging (unrefreshed annotations self-interfere toward
silence); crystallized `{am=65535, en=−32768}` is exactly the state that
survives merging with itself — *standing waves persist, noise cools*.

Cost: `interfere` is deliberately non-commutative (Left Dominance,
§5.2) — merge order changes results, so convergence needs a canonical
ordering (e.g. by assertion hash), and then the ordering, not the
algebra, is doing the real work. Identity/spam/jurisdiction all remain
unsolved and would need inventing — precisely what F1 gets for free.

### F3 — Hybrid: warrants carry, interference weighs (leaning)

Assertions travel as warrants (F1: identity, jurisdiction, settlement,
spam). Within a jurisdiction, the *effective* wave of a node with
multiple accepted assertions is derived by folding them with
`interfere` in canonical order (F2: aging, weighting, crystallization),
never stored as truth — recomputable, like every Book II view. Book I
untouched by construction; Book II untouched except a new §7
(Federation) defining the fold; the protocol document becomes mostly a
profile of Warrant v0.3.

## Design criteria for the gate

1. **Book I MUST be unreachable** from any federation state — no
   annotation, however adversarial, may influence `eval()`. (Inherited
   axiom; restated because federation is the first outward-facing
   surface.)
2. **Determinism per jurisdiction:** two verifiers with the same
   genesis set and the same warrant store MUST derive identical
   effective waves — byte-exact, differential-testable across
   implementations, like everything else in both projects.
3. **Divergence is explicit:** two jurisdictions may disagree forever,
   but naming the disagreement (which roots, which assertions) MUST be
   mechanical.
4. **Weight costs something:** an assertion's amplitude MUST be bounded
   by something the asserter provably spent or risked — candidates:
   ATP-priced check (`ski@v1` whose budget bounds claimable `am`),
   threshold co-signatures, stake-by-reputation-in-jurisdiction. The
   gate should attack each.
5. **State is bounded:** a node MUST be able to hold a jurisdiction's
   effective view in O(annotated nodes), not O(all assertions ever) —
   fold-and-forget must be sound despite non-commutativity.

## Review gate asks (rev 1)

1. Attack F3's canonical fold order: any deterministic order (hash
   order, DAG order, ts order) — can an asserter *choose their position
   in the fold* (Left Dominance means position = phase power) by
   grinding assertion hashes? Does the fold need to be
   order-insensitive by construction (e.g. sort by (ph, hash) then fold),
   and what does that cost the algebra?
2. Attack criterion 4's ski@v1-priced amplitude: does "budget bounds
   claimable am" survive a prover who amortizes one expensive check
   across many assertions?
3. Is F1-without-F2 actually sufficient (selection-only merge), making
   the interference fold complexity unnecessary? Name the use case that
   *requires* arithmetic merge, or concede F1.

## Non-goals

Global consensus on annotations (explicitly rejected — Book I owns the
only consensus this system has); real-time transport (gossip cadence is
an implementation profile); incentive tokens of any kind.
