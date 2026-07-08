<!-- produced via tools/or_review.py | model: openai/gpt-5 | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-gpt5-gov-standard.md.pass1 -->

# Review: Promotion decision for spec/GOV-anchors.md

## Verdict

PROMOTE-WITH-AMENDMENTS

The governance layer has met its own conformance gates in substance (not ceremony), and the live posture matches the tool’s enforce mode. Promotion is coherent even while the governed Books remain DRAFT — but only if the GOV document pins its normative Warrant v0.3 dependency and states clear “STANDARD” stability commitments. Those two amendments are required before promotion; several clarity edits are strongly recommended.

## 1) Are the §7 conformance obligations genuinely met?

Assessment: Met in substance. The evidence cited below is attributed to the maintainer’s reports and CI posture; I did not run code.

- Reference verifier + deterministic selftest
  - Per maintainer report, tools/anchor_governance.py selftest: ALL PASS, now 22 checks, deterministic fixtures (fixed Ed25519 keys and fixed timestamps). The suite exercises the lineage, closure, “freeze on rival authorized successors,” jurisdiction replay armor, “orphan outside closure,” under-cardinality/ineligibility, and key‑state scoping. This matches the spec’s seven-step flow and tests the tricky edges rather than superficial paths.

- Pinned vectors, including “unauthorized in authorized positions”
  - governance_vectors.json contains 16 scenarios and includes the adversarial “authorized-shape/unauthorized-substance” fixtures the spec must catch (e.g., hijacked minted pair; unquorumed/unauthorized keystate placed under the right-looking profile). Per maintainer, the generator is mechanical and deterministic, and the verifier replays 16/16.

- Second independent implementation + differential
  - An independent Go tool (“gov-replay”) passes 16/16 vectors and agrees on 23/23 differential mutations, per maintainer’s report. This demonstrates cross‑pipeline agreement on both accept/refuse and “freeze” outcomes.

- CI enforcement with out‑of‑band trust
  - CI is reported to run the verifier in “--enforce” mode against an out‑of‑band trust config. The verifier refuses in‑tree trust paths and fails closed when cryptography is unavailable. Live status shows v0.6.2 and v0.6.3 AUTHORIZED 2/2, which is consistent with actual governed releases passing the tool in enforce mode.

Why this reads as real, not ceremony
- The verifier implements a pure, deterministic decision procedure: settlement‑closure scoping from a pinned root; governance profile lineage; exact under cardinality (one profile + its bound threshold); signature‑count against the active threshold; conflict‑as‑freeze on rival maxima. The pinned vectors target precisely those edges, and a second implementation agrees. CI’s enforce posture closes the “lying green” gap.

Arithmetic sanity
- Liveness budget: for a 2‑of‑3 roster, N−M = 3−2 = 1; the store tolerates one absent actor without losing the ability to adopt. Test fixtures demonstrate that duplicate-actor signatures and unbound keys do not count toward quorum.

Non‑blocking notes
- Note‑substring expectations in vectors are a testing convenience; they’re not normative, which is fine.
- The verifier only re‑verifies signatures when they count toward quorums (not across the entire closure). That’s sufficient for authorization decisions; an implementer note would prevent confusion (see P2 recommendations).

Conclusion: The four §7 obligations are met in substance and enforced in CI.

## 2) Coherence: STANDARD GOV over DRAFT Books and a DRAFT Warrant v0.3

- Constitution‑first over Books I–III
  - Coherent. GOV governs process, not on‑wire semantics. Stabilizing the adoption/lineage/closure rules while the governed text evolves as DRAFT is a feature: it reduces institutional risk by fixing the process that decides “what is the spec” before that content stops moving.

- Normative dependency on Warrant v0.3 (itself DRAFT)
  - Not coherent as‑is unless pinned. GOV’s normative rules depend on specific Warrant v0.3 semantics (settlement closure, key‑state, multi‑root). If “Warrant v0.3” is a moving target, a STANDARD GOV would rest on driftable ground.

Conclusion: The STANDARD‑on‑DRAFT layering is acceptable for GOV→Books, but ONLY if GOV normatively pins the Warrant v0.3 text to a specific commit/snapshot. That pin is the one remaining coherence gap to close before promotion.

## 3) What “STANDARD” must mean here, and does GOV-anchors.md say it?

Expectation for “STANDARD” in this context
- Frozen schemas: anchor‑set blob schema, governance profile schema, and out‑of‑band trust schema are closed. Any change ships as new tags (e.g., @v2) with a new conformance suite and adoption.
- Frozen mechanism: the verification steps (jurisdiction/root scoping; profile lineage; structural closure; under cardinality and binding; threshold evaluation; conflict freeze) are stable. Behavioral changes require a new profile/tag and vectors.
- Backward‑compatibility: STANDARD verifiers continue to accept blobs valid under this version; unknown versions fail closed and are detectable by tag/versioning.
- Pinned dependencies: normative dependencies (here, Warrant v0.3’s relied‑upon sections) are pinned to a commit/snapshot to avoid semantic drift.

Current status of GOV-anchors.md
- The document enforces most of this in practice (tags for schemas; a reference verifier; vectors; second implementation; CI enforce posture; prohibition on in‑tree trust). However, it does not explicitly define the project’s commitments under the “STANDARD” label.

Conclusion: Promotion should add an explicit “Stability commitments (STANDARD)” subsection stating these commitments. Without it, “STANDARD” is a label without a defined bar.

Concrete amendment (Required)
- Add a “Stability commitments (STANDARD)” subsection near the top:

  “When this document’s Status is STANDARD:
  - The following schemas are FROZEN: ‘sigma-glyph.anchor-set@v1’, ‘sigma-glyph.anchor-governance@v1’, and ‘sigma-glyph.anchor-trust@v1’. Behavioral or schema changes require a new tag (e.g., ‘@v2’), a fresh §7 conformance suite, and a governed adoption.
  - The verification procedure in §3 (steps 1–7) is FROZEN. Any behavioral change requires a new profile/tag and conformance suite.
  - Backwards compatibility: verifiers implementing this STANDARD continue to accept blobs valid under this version. Unknown versions MUST fail closed and be explicitly detectable by tag.
  - Normative dependency pin: this STANDARD depends on Warrant SPEC v0.3 as pinned in ‘Pinned Warrant v0.3 snapshot’ below; any dependency change requires a new governance profile/tag and conformance vectors.”

## 4) Blockers or required amendments before promotion

Required (blockers to promotion)
- P1-A: Pin the Warrant v0.3 dependency
  - Add a normative pin to a specific commit hash and include or reference an in‑repo, anchored snapshot used for settlement/key‑state/multi‑root semantics relied upon by GOV.
  - Suggested text: “This profile is defined against Warrant SPEC v0.3 at commit <commit-hash>. An exact snapshot is included at <path>; it is authoritative for settlement (§7), key‑state (§5.1), and multi‑root (§9) as used here. Implementations MAY support later Warrant versions only if these semantics are preserved; any change requires a new governance profile/tag and vectors.”

- P1-B: Define “STANDARD” stability commitments
  - Add the “Stability commitments (STANDARD)” subsection as outlined in §3.

Strongly recommended (non‑blocking clarity improvements)
- P2‑1 Key‑state refusal phrasing
  - Clarify in §3 that a quorum‑authorized key‑state warrant under the governance policy forces refusal by any verifier that cannot derive key state; a key‑state‑capable verifier MUST derive it first. Emphasize that a key‑state record failing current‑policy authorization is invalid (does not cause a freeze).

- P2‑2 Release field semantics
  - State explicitly that ‘release’ is advisory only; authorization depends solely on content and lineage, not the ‘release’ string.

- P2‑3 Closure/signature validation note
  - Add an implementer note that the descendant closure is structural; signatures are verified only when they count toward a quorum in steps 4–7.

- P2‑4 Explicitly forbid in‑tree trust paths in the algorithm section
  - Mirror the schema note with a MUST in §3 step 1: refuse trust configs located inside the tree being verified.

With P1‑A and P1‑B applied, promotion is justified.

---

## Relation to prior reviews

Attribution note: I did not execute code. Statements about tool behavior, test counts, and CI posture are taken from the maintainer’s reports and the prior review/response documents provided.

- Agreement
  - With GPT‑5 and DeepSeek ADR‑007 gate reviews (and maintainer responses) on core mechanics now embedded in GOV:
    - Settlement‑closure scoping from a pinned jurisdiction root is mandatory; the original “count anything present” flaw was material and is now addressed. My conformance judgment leans on that fix being present.
    - Exact under cardinality (one governance profile + one threshold) and profile→threshold hash binding close the “minted pair” hijack class. I agree this is load‑bearing and see it exercised in the current vectors set per maintainer.
    - Out‑of‑band trust only; refuse in‑tree paths. This was correctly elevated from advisory to enforced behavior; CI “--enforce” aligns with that.
    - Key‑state refusal scoped to governance‑policy‑filed warrants, not global. I agree with the scoped‑verifier posture: refuse loudly rather than mis‑derive.
    - Conflict handling: rival, fully authorized successors freeze the chain rather than tie‑break on grindable IDs. I agree with rejecting grindable selection rules.

- Disagreement
  - With Gemini’s stance that embedded jurisdiction roots are unnecessary. I side with GPT‑5 and DeepSeek (and the final adjudication): embedding plus reachability is cheap defense‑in‑depth and fails closed early. My recommendation here is consistent with that settled outcome.
  - On coherence, I go further than the prior gate reviews: a STANDARD GOV document cannot depend on an unpinned DRAFT Warrant v0.3. This pin is not prominently called out in the earlier responses; I treat it as a required amendment for promotion.

- What is new in this review
  - The promotion‑stage coherence bar: an explicit requirement to pin the normative Warrant v0.3 dependency before calling GOV “STANDARD.”
  - The definition of the “STANDARD” label for GOV as concrete stability commitments: frozen schemas, frozen verification steps, backward‑compatibility posture, and dependency pinning. Prior reviews and responses focused on adopting ADR‑007 and hardening mechanics; this review formalizes what “STANDARD” must commit to for maintainers and implementers.
  - Minor clarifications tailored to the STANDARD move (release field advisory semantics; explicit algorithmic prohibition on in‑tree trust in §3; an implementer note on closure vs signature‑verification points).

Net: I agree the mechanics have been brought to conformance quality and enforced in CI with vectors and a second implementation. To be coherent and legible as a STANDARD, GOV must add the dependency pin and state the stability bar. With those amendments, promote.
