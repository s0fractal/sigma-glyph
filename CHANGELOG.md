# Changelog

## v0.6.6 — GOV 1.0.2 (2026-07)

Conformance-hardening **PATCH** from an external Codex adversarial audit of the anchor-governance verifier — three cross-implementation defects where a §2/Warrant-§3-conforming verifier should already have refused, but the reference implementations under-enforced. `spec/GOV-anchors.md` → v1.0.2 (§3 steps 2–3 spell out the invariants). **Not** a new schema `@v2` tag — all 17 prior governance vectors are byte-identical; only inputs the spec already forbade change verdict. Independently gated: **DeepSeek v4 Pro + Gemini 3.1 Pro, both APPROVE-PATCH** (§0 conformance-not-mechanism-change reasoning; codex CLI was unavailable — blocked by its vendor's cybersecurity content filter on the repo's own security-testing vocabulary).

- **F2 (P0):** Python `settlement_closure()` admitted records reachable via `body.prior` without checking id-soundness (`sha256(canon(body)) == filename WarrantID`); Go already gated on `soundRecord()`. A malformed intermediate record could bridge a foreign adoption into the closure in Python only. Fixed with `_sound_body()` gating root + every hop → Go parity. Locked by `GV-MALFORMED-BRIDGE-IGNORED`.
- **F3 (P0):** Go `parseJSONBlob()` decoded once and ignored trailing bytes (`<object> true` parsed in Go, rejected by Python's `json.loads`). Now requires `io.EOF` after the value. Locked by `GV-TRAILING-JSON-REJECTED`.
- **F4 (P1):** neither implementation compared raw blob bytes to `canon(parsed)`, so a pretty-printed (non-JCS) blob authorized. Both now enforce byte-canonicality (also rejects duplicate-key / non-minimal encodings). Locked by `GV-NONCANONICAL-BLOB-REJECTED`. Book III (`sigma_federation.py`) canonicality is deferred to the settlement-integration layer (ROADMAP), since that oracle takes no raw bytes.
- `governance_vectors.json` 17 → 20 scenarios; Go `gov-replay` 20/20; governance differential 27/27; all 17 originals byte-identical.
- Tooling/docs (non-anchored): `tools/test-all.sh` reaches CI parity (freshness regen, Book III live demo, network-gated `status --enforce` + settlement Warrant CLI); README/ROADMAP drift corrected; `reviews/2026-07-codex-governance-hardening-response.md` (+ independent gate reviews). 
- Governed adoption warrant, 2-of-3 signatures. Anchor set: `spec/GOV-anchors.md` and `tests/spec_conformance/governance_vectors.json` change; all other anchors carry over from v0.6.5.

## v0.6.5 — GOV 1.0.1 (2026-07)

First **PATCH** through the governed-anchor process: `spec/GOV-anchors.md` → v1.0.1, three §3 prose clarifications from the Kimi focused formal review, **zero behavioral change** (the reference verifier already behaves as each specifies; all 17 governance vectors byte-identical) — a SemVer patch, not a new schema `@v2` tag. Proves the constitution's maintenance path handles routine clarity work, not only landmark releases.

- §3 step 4: the zero-hop lineage base case (profile in force = `genesis_profile` when the closure holds no adoption) stated explicitly.
- §3 step 5: reworded so the subject of the key-state refusal is unambiguous — the **scoped** verifier refuses and defers to a key-state-deriving verifier.
- §3 step 7: the competing-adoption freeze stated as **total by construction** (an unauthorized set is not a valid ancestor, so no verifier advances the chain; none may pick a winner).
- Also: `proofs/README` TCB note sharpened (the interference theorems transitively consume `native_decide` LUT lemmas — the compiler is in their cone; only the pure integer lemmas + `left_dominance_ph` are fully kernel-checked); `EvalMachine.lean` gains a `grind` tactic-transparency comment. `or_review` now briefs reviewers on the full gate surface (all four proof bridges + governance replay/differential + Rust).
- Governed adoption warrant, 2-of-3 signatures. Anchor set: only `spec/GOV-anchors.md` changes; all other anchors carry over from v0.6.4.

## v0.6.4 — "Standing Constitution" (2026-07)

`spec/GOV-anchors.md` leaves DRAFT: **the project's first STANDARD** (document version 1.0.0, independent of this v0.6.4 bundle). Promoted through the process it defines — a second 3-family gate on the promotion itself (Gemini 3.1 Pro, GPT-5, DeepSeek v4 Pro; unanimous PROMOTE-WITH-AMENDMENTS) — not by maintainer fiat.

- **P0 fixed (Gemini, found by 1 of 3): the suicide verifier.** `key_state_under_governance` refused on the *presence* of a settled governance key-state warrant; the settlement closure is append-only, so the first roster rotation — the very operation §4 exists to support — would deadlock the chain **forever**, even after the operator derived the new key. The static vector `GV-KEYSTATE-QUORUM-REFUSED` had enshrined that refusal. Fixed with an OPTIONAL `resolved_key_state: [WarrantID]` in `sigma-glyph.anchor-trust@v1`: an acknowledged rotation (derived into `actors` out-of-band) no longer refuses; unacknowledged ones still do. New transition vector `GV-KEYSTATE-RESOLVED` (rotate→refuse→acknowledge→proceed); §7 now MUST include state-transition fixtures, not only static states. Fixed in both implementations (Python + Go), differential 24/24. This bug shipped in v0.6.3; the fix is warranted regardless of promotion.
- **P1 (3/3): define STANDARD + pin dependencies.** New §0 Status and Stability: frozen schemas (`@v2` for any breaking change), frozen §3 mechanism, backward-compat/fail-closed, SemVer. Normative dependencies pinned — Warrant v0.3 by content SHA-256 of the vendored snapshot (`73758bdb…`), Books I-III by anchored version — so a STANDARD never rests on a moving DRAFT target. Coherence resolved: the constitution stabilizing before its governed content is deliberate (the process that decides "what is the spec" freezes first).
- **P2 (GPT-5):** §3 step 1 MUST-refuses in-tree trust configs; `release` is advisory metadata; implementer note on closure-vs-signature scope.
- Reference verifier `anchor_governance.py` (22 checks) + `governance_vectors.json` (16→17) + Go `gov-replay` (17/17) all updated; CI gates green. Governed adoption warrant carries 2-of-3 signatures.
- Decision trail: `reviews/2026-07-{gemini,gpt5,deepseek}-gov-standard*.md` + adjudication warrants in `.warrants/`. **Published Book vectors: no changes** (Books I/II/III untouched).

## v0.6.3 — "Second Signature" (2026-07)

The constitution meets its own conformance obligations, and the third roster actor becomes real:

- **`tests/spec_conformance/governance_vectors.json`** (GOV obligation 2): 16 pinned full-store adoption scenarios — every gate attack as a deterministic fixture (minted-pair hijack, closure orphans, jurisdiction replay, rival freeze, both P1-R directions). Generated by `tools/anchor_governance.py gen` (refuses if the oracle disagrees with a declared expectation), replayed by `replay`; regen byte-deterministic; anchored.
- **Go second implementation** (GOV obligation 3, codex zero-relay): `impl-go` gains `gov-replay` (16/16) — an independent §3 verification pipeline; `tests/governance_differential.py` — 7 adversarial mutation kinds, Python and Go agree on all 23 cases. Adjudication warrant `631ad4a3`.
- **This release's adoption warrant carries the first `codex@sigma-glyph` signature**, filed from a codex session after its own verification run — the 2-of-3 roster is now three real actors, not two and a placeholder.
- CI: governance replay + differential as required gates. GOV-anchors.md stays DRAFT STANDARD (status change is a future release decision; its stated preconditions are now met).
- **Published vectors: no changes** to Book I/II/III suites; `governance_vectors.json` is new and now anchored.

## v0.6.2 — "Governed Anchors" (2026-07)

Adopts **ADR-007** (3-family blind gate: GPT-5, Gemini 3.1 Pro, DeepSeek v4 Pro — all P0/P1 closed in rev 2; verification pass: Kimi k2.6 — residual P1-R closed in rev 3, "close P1-R and ADOPT"). The interim single-maintainer trust point starts retiring on a schedule: **Specification Anchors are now warrant-governed.**

- **New: `spec/GOV-anchors.md`** (normative, meta; deliberately not a Book — the constitution must not judge itself, gate 2:1). Releases become JCS anchor-set blobs (jurisdiction-embedded, ancestor-chained) adopted by `accept` warrants under a threshold policy; ANCHORS.txt is the human projection, the blob wins on divergence. Policy lineage per Warrant §5.1 (each profile adoption authorized under the policy being replaced); rival successors freeze the chain — no tie-breaks (grindable, the ADR-006 fold lesson); genesis keys retire by policy rotation, N−M liveness arithmetic stated; forks are legitimate jurisdictions.
- **Governance genesis filed:** root `a30bd202…`, roster 2-of-3 {s0fractal (founder), claude-fable-5 (maintainer), codex (reviewer family)} — founder decision 2026-07-08. Continuity-from-then: v0.5.0–v0.6.1 are labeled pre-governance ancestors in ANCHORS.txt; governance authorizes v0.6.2 forward and claims nothing about history.
- `tools/anchor_governance.py` — reference verifier (settlement-closure scoping, fail-closed crypto, out-of-band trust config with in-tree refusal, `--enforce`); deterministic 22-check selftest.
- `examples/two-jurisdictions/` — first live Book III exercise (two real warrant stores, file-copy gossip, divergent sovereign views, ConflictSet, replay resistance observed live); in CI.
- Decision trail: ADR-007 (3 revisions), 7 reviews/responses in `reviews/`, adjudication warrants `89da5979 → 869243ae → 09133de9 → 26cf44f0`, governance genesis `a30bd202…`, adoption warrant over the v0.6.2 anchor-set — all in `.warrants/`.
- **Published vectors: no changes** (all Book I/II/III vectors byte-identical; Book anchors carried over per the bundle convention).

## v0.6.1 (2026-07)

Hygiene release adjudicating the Codex pedantic full-state audit (P2/P3 pedantry explicitly invited — and earned). No behavior changes anywhere; one real CI bug and a stale-reference sweep:

- **P1 (CI):** the federation second-implementation step piped through `tail -1`, which masks failures (Actions runs without pipefail) — the one gate guarding the Book III two-implementation claim could go green on a failed replay. Now `set -euo pipefail` + `grep -q` like every other step.
- Anchored prose: Book II §1 no longer promises a "future document" that shipped (points at §10/Book III); Book III criterion 10 said "Merkle root" after §6 was corrected to a set commitment; three typos (Піни/subject/повторної верифікації). Book II/III headers → 0.6.1.
- ANCHORS gains the **bundle convention** note: an untouched file keeps its bytes, per-document version and anchor from the last release that changed it (Book I ships in v0.6.x at its own 0.5.2 — intentional, now explicit).
- CHANGELOG v0.6.0 said Book II §7 where the file says §10; README's "Two Books" header and table now know all three Books; implementation docstrings state oracle-vs-bundle versions; `tests/spec_conformance/README` updated from v1/39 to v2/49; "Warrant v0.1 format" wording made precise in reviews/README and warrant_verify; proofs/README states plainly that the bridge checks the theorem-sufficient premise, not row-by-row constructor correspondence.
- Review tooling briefs the current surface: or_review primary sources/gates now include Book III, proofs, federation differential; ai-review protocol mandates all three oracles; aggregate.sh ships Three Books.


## v0.6.0 — "Sovereign Views" (2026-07)

Adopts ADR-006 (annotation federation, gate 3/3: Gemini, Codex, Kimi k2.6 — architecture **F1-strict**, selection-only, warrant-carried). **Book III: FEDERATION is born and anchored.** No Book I changes of any kind; Book II gains one normative section (§10 Федерація) and nothing else.

**Book III (new, anchored):** annotation assertions are Warrant v0.3 records; a jurisdiction's machine-readable selection policy picks zero-or-one assertion per node (ties surface as ConflictSets that clients MUST NOT merge — automated systems treat conflicted nodes as unannotated); `interfere()` is structural-only — the interference fold died at the design gate to verified non-associativity (grouping alone doubles amplitude); replay resistance via jurisdiction roots embedded in assertion blobs; `AnnotationViewID` (a coordinate) + `assertion_set_root` (a set commitment — honestly not zero-knowledge) name views and projections mechanically; proof supports facts, policy meters weight (ski@v1 never mints amplitude); protocol-level aggregation profiles are forbidden (MUST NOT) — the governance-backdoor lesson.

**Book II (0.5.2 → 0.6.0):** new §10 — waves are per-jurisdiction, per-policy derived coordinates, not global attributes; divergence between jurisdictions is permanent and by design; §6 pins are the null jurisdiction's defaults.

**Implementations and vectors:**
- `impl/sigma_federation.py` — pure-function reference oracle (validation, six-step selection derivation, `wave_fed`, ViewID, set root). Survived a blocking implementation-gate round: a real ordering bug (character-complement descending trick failed on prefix pairs and crashed on non-ASCII) was found by review and fixed with a direct-comparison comparator; collation is now normative.
- `impl-go/` — second, independent Go implementation (stdlib-only, own LUT generation against the Book II arbiter), replaying the same vectors.
- `tests/spec_conformance/federation_vectors.json` — 21 vectors / 37 oracle checks, including `FV-FOLD-UNSOUND` (why merging is forbidden), `FV-BOOK-I-UNREACHABLE` (the Book I boundary as an executable vector, not a promise), and the full adversarial selection surface (prefix/non-ASCII actors, node binding, future epochs, quota semantics, malformed metadata).
- `tests/federation_differential.py` — both implementations must agree on every outcome (40/40, incl. astral-plane actors, quota collisions, whitespace metadata).

The full decision trail — design gate, blocking implementation review, fix adjudications — is signed warrants in `.warrants/`.

## v0.5.2 — "Honest Fences" (2026-07)

Hygiene release adjudicating the Opus 4.8 (1M) adversarial review of v0.5.1 — the review attacked consensus safety and found none broken; everything below is fence/discipline repair. **No canonical eval result changes** (all 46 prior vectors byte-identical in expectations; 3 new).

- **M1 (fixed in 129a828, adjudicated here):** the reference's memory fence guarded on `spent` — an UPPER bound on size, not a proxy — so `eval(Ω, n)` faulted instead of returning canonical ATP Exhausted for `n ≥ max_materialized_nodes`, violating TV-7's `∀n`. Guard now measures actual `size(t)`/depth; §3.4 prose corrected: the bound gives a preflight memory estimate, never a live fault trigger.
- **m1:** Book I/II version headers now match their anchor section (the v0.5.1 bytes were filed under stale 0.5.0 headers).
- **m3 (also sharpens Kimi §3):** §3.4 explicitly defines `materialized_size(t)` = the section's Розмір over the materialized graph, synthetic nodes included — no "exclusion lemma" needed since every rule's growth < its cost.
- **m2:** the "phase coordinate stays visible" guarantee is now modeled: `coordinate(name)` accessor over the Ph-only pin tables + `kind=coordinate` wave vectors (`WV-COORD-SATOSHI/V/FALSE`).
- **N1:** Book II §4 no longer demands ≥80-bit LUT generation; the arbiter hash is authoritative and 64-bit is provably sufficient (no entry within 0.5 ULP of a tie).
- **N2:** three new eval vectors pin previously-untested behavior: `EV-STUCK-DIS-FN`, `EV-STUCK-LIT-FN` (non-combinator in function position → stuck normal form, spent 4), `EV-REF-COMBINATOR-FIRES` (REF target enabling a redex). Suite: 46 → 49.
- **N3:** implementer note on §3 fixed widths in `interfere()` (int64/uint64 intermediates mandatory in ports).


## v0.5.1 — "Scoped Silence" (2026-07)

Adopts ADR-004 (Option 2, review gate 4/≥3 with zero dissent — including a Codex concession of its own audit-time Option 1) and ADR-005 (R1, gate 2:1 over R2). **No Book I behavior changes: every v0.5.0 eval result, hash and cost is unchanged.** This release aligns prose with the oracle and makes Book II's wave layer total-by-declaration.

**Book I (0.5.0 → 0.5.1), prose-only:**
- §1.1: the LITERAL blob-validation paragraph that contradicted both its neighbor and the oracle is replaced — Book I validates node bytes only; blob absence/availability/corruption MUST NOT change `eval()` results and MUST NOT serialize as Book I DISSONANCE. (ADR-004; DeepSeek's textual base merged with Codex's MUST-NOT clauses.)

**Book II (0.5.0 → 0.5.1):**
- §2: **Pin > Derived is field-level** — `WavePin {ph?, am?, en?}` overrides exactly the fields it lists; the rest derive via `complete(interfere(...), pin)`. (ADR-005, R1.)
- §2.1 (new): **wave() is a partial function** — non-APPLY nodes without pins have no wave; interfere with an absent operand is absent; absence is legitimate and never touches Book I.
- §6.2: normative FALSE row — `{ph=49152 (pin), am=0, en=−32512 (derived)}`. The zero-amplitude cascade is a theorem: any APPLY whose derived subtree contains FALSE has `am=0` unless an explicit pin overrides amplitude at or above that node. Phase coordinates stay visible.

**Vectors and implementations:**
- `wave_vectors.json` format v2 (14 vectors): `kind=term` (pin completion, absent-wave semantics; `expected=null` = absent) and `kind=iterate` (`WV-ITER-DECAY`: 49151→36863→20735→6560→657→7→0). New: `WV-FALSE-DERIVED`, `WV-FALSE-ANCESTOR-SILENT`, `WV-PH-ONLY-ABSENT`, `WV-UNPINNED-LITERAL-ABSENT`.
- `impl/sigma_wave.py`: pin table + `wave()` over symbolic terms with R1 completion (selftest 27 checks).
- `vectors.json`: notes strengthened per ADR-004 — eval vectors carry no blob-store inputs and results MUST NOT depend on blob material (`EV-LIT-FORCE` note states this explicitly). No behavioral change.
- Post-release audit cycle recorded in `reviews/` (peer-Claude, Codex, Kimi k2.6 + the three-way ADR gate), all adjudicated as warrants in `.warrants/`; `tools/warrant_verify.py` ships for local verification.

## v0.5.0 — "Priced Reality" (2026-07) — BREAKING

Adopts ADR-001 + ADR-003 (composed via the Hash-Leaf Size Model) and ADR-002, after 3/3 dedicated model reviews (Codex, Gemini, DeepSeek) and 5 adjudication warrants. **Serialization, validation, NodeHashes and C1 are unchanged — every v0.4 hash remains valid.** What changed is evaluation semantics and ATP accounting.

**Book I (0.4.5 → 0.5.0):**
- §3.3: the **hash-thunk machine** — terms are graphs of materialized nodes over unresolved hashes (thunks); redex patterns compare hashes without forcing; leftmost-outermost search forces only what it demands; genesis thunks are normal-form leaves. Divergence class normative: undemanded unresolved subtrees never affect results.
- §3.4: **size-priced ATP, hash-leaf model** — force costs 1/2/3 (atom/REF/APPLY), R-I/R-K/R-R cost 1, R-S costs `1 + size(z)` with thunks counting 1 and never forced. New normative invariant: `materialized size − 1 ≤ spent` (the memory bound). Exhaustion decided before every action; min-cost 1 check precedes even the fetch.
- §3.5: **lazy left-spine materialization normative** (eager was 0.4.x); §3.6 updated (size guard now free via the bound).
- §5.1: **Genesis Intrinsic** — I/K/S resolve without a store; FALSE is a theorem, constructible.
- §7: TV costs re-pinned (TV-4: 4 ATP; TV-5: 12; TV-6: 21; TV-9: 6; TV-10: 20); new TV-11 (divergence class) and TV-12 (genesis intrinsic).

**Book II (0.4.2 → 0.5.0):**
- §5: **entropy–coherence coupling** — `delta_en = div_round_half_up(−r, 128)`; constructive interference creates order, destructive creates disorder.
- §5.1: **Resonance Identity rewritten** — entropy drifts −256 per constructive self-application; the unique non-zero full-WaveVector fixed point is `{am=65535, en=−32768}` (crystallization; the Gravity mechanism).

**Vectors and implementations:**
- `vectors.json` format v2 (46 vectors): all eval expectations re-pinned; `store_subset` field for isolation vectors; flips vs v0.4: `EV-K-DEAD-MISSING` → I (was Unresolved), `EV-REF-MISSING-ATP1` → Exhausted (force priced). ghost bytes pinned: SHA-256("this node was never stored").
- **New `impl/sigma_wave.py`** (Book II oracle: LUT arbiter-checked, interfere with coupling) + `wave_vectors.json` (9 vectors incl. `WV-NEG-TIE` — catches floor-rounding implementations: `avg(−1,−2)` MUST be −2, away-from-zero per Book II §3).
- Property suite: +P7 memory bound (2103 checks); appendix A rewritten (time O(spent²), memory O(spent), "you pay to look").

**Migration from v0.4.x:**
1. Hashes, stores and blobs need no migration — identity layer untouched.
2. Re-budget every eval call: costs are ~2–4× step counts for small terms (materialization is priced). Rule of thumb: `3×(nodes to touch) + old step count + size of duplicated args`.
3. Terms relying on eager verification ("whole closure must exist") now reduce past dead missing branches — if you depended on Unresolved Reference as an availability check, check availability explicitly instead.
4. Wave annotations: recompute entropies; self-resonant structures drift to en=−32768 by design.
5. Anchors: Book I `0c4f39cc…`, Book II re-anchored; v0.4.6 anchors remain valid ancestors.

## v0.4.6 (2026-07)
- **New: `spec/appendix-a-complexity.md`** (NON-NORMATIVE) — per-rule size deltas (only R-S/R-R grow, each by < the duplicated size), O(2^ATP) worst-case envelope with the honest empirical note that Omega grows *linearly* (~1 node / 8 steps; the exponential bound needs crafted duplication towers), time/space bounds for v0.4.x vs ADR-001, fetch accounting. Closes Sonnet 4.5 P3.1 — the last deferred finding from that review.
- **New: `tools/complexity_metrics.py`** — regenerates the appendix table; integer-deterministic, machine-independent. Table vs tool: tool wins.
- **Oracle robustness (self-found, P1-class):** a term of depth 1500 — well within the promised `max_node_depth=4096` — crashed `eval` with a raw `RecursionError` (Python stack ceiling ~1000; same leak class as the Codex P1-A totality bug). Fixed: `eval_hash` scopes the interpreter recursion limit to the configured depth and maps residual `RecursionError` → `ResourceFault` (§3.6 local fault). Two new oracle tests: depth-1500 within limits → canonical outcome; depth-4500 beyond limits → ResourceFault, never a raw crash.
- ANCHORS.txt: v0.4.6 section; appendix anchored alongside the Books. Book I/II, LORE and vectors.json unchanged — anchors carry over (published vectors: **no changes**).

**Impact:** Additive doc + local-fault robustness fix. No spec text changes, no vector changes, no consensus-observable changes.

## v0.4.5 (2026-07)
- **Oracle bug fix (Codex follow-up P1):** `eval` could (a) leak a raw `Unresolved` exception through the post-step lookahead — violating the §3.4 totalization MUST — and (b) report `atp_spent > atp` by firing a rule it could not pay for. New loop: exhaustion is decided **before** any resolve of the next step; `spent` never exceeds `atp`; failed firings are not charged; `eval` is total.
- Book I §3.4: new normative bullet pinning the above (budget check precedes firing; `eval(REF(missing),0)` = ATP Exhausted, not Unresolved).
- Book I §3.5: **eager materialization normative in 0.4.x** — APPLY children resolve before redex recognition; a missing dead argument yields Unresolved Reference, not reduction past it (Codex follow-up P1: the gap was divergence-grade). Lazy left-spine resolution filed as **ADR-003** (v0.5 candidate; composes with ADR-001).
- Conformance suite: +5 vectors (39 total) — `EV-K-DEAD-MISSING`, `EV-REF-MISSING-ATP0/1`, `EV-I-REF-MISSING-ATP1/2` pin the new semantics and the exhaustion-vs-unresolved precedence.
- **Corrected published vectors:** `EV-TV4-IK-ATP0`, `EV-TV7-OMEGA-0` — `atp_spent` 1 → 0. These values were produced by the buggy loop and contradicted §3.4; a defective vector is corrected, not grandfathered (rationale in `reviews/2026-07-codex-v0.4.4-followup-response.md`). Outcome hashes unchanged.
- Version metadata (Codex P2): README "Current" line fixed (was stale at v0.4.0); `vectors.json` gains `suite_version` alongside `spec_version`; conformance claims must cite both plus `book1_anchor`.
- Release checklist extended: README version line + "did published vectors change" statement are now release gates.

**Impact:** Book I text clarified (2 additions), oracle semantics corrected on previously-unpinned edges, two published vector values corrected with rationale. No outcome-hash changes for any previously published vector.

## v0.4.4 (2026-07)
- **New: `tests/spec_conformance/`** — machine-readable conformance suite (Sonnet 4.5 P3.2, the highest-priority deferred item).
  - `vectors.json` (format v1): 23 CAS objects + 34 vectors — genesis/serialization, 8 negative validation cases, eval vectors covering TV-4…TV-10 with exact-budget and under-budget boundaries, root-missing, bad-bytes-child (§3.5b), inert stored DISSONANCE. Normative observables: `result_hash` + `atp_spent` (tree semantics); dissonance outcomes compare uniformly via canonical DISSONANCE hashes.
  - `generate.py` — vectors are **computed from the oracle** (`impl/sigma_glyph.py`), never hand-written; regeneration is deterministic (byte-identical JSON).
  - `run_reference.py` — replays vectors against the oracle; doubles as runner-semantics documentation for Rust/Zig/other implementations.
  - `test_properties.py` — seeded stdlib-only property tests (1929 checks): serialization canonicity round-trip, deser totality under fuzz, eval determinism, ATP exactness (budget = spent reaches NF; spent−1 exhausts), normal forms are 0-ATP fixed points, C1 output purity + determinism.
- CI: regen-freshness gate (`generate.py` must produce no diff), conformance replay, property suite — all required on every push/PR.
- ANCHORS.txt: v0.4.4 section; `vectors.json` is now anchored alongside the Books (executable law gets an anchor too). Books unchanged — their anchors carry over from v0.4.3, and per the LORE precedent document versions bump only when the document changes.

**Impact:** Additive only. No spec text changes. No breaking changes. Multi-language implementations can now claim Book I conformance by passing `vectors.json`.

## v0.4.3 (2026-07)
- Book I §3.4: ATP budget width made normative — `uint32` canonical; ATP > 2³²−1 implementation-defined (MAY reject/clamp); only the three canonical outcomes are consensus-critical. Closes P1 (Claude Sonnet 4.5 finding).
- Book I §3.5: `resolve(h)` failure modes made explicit — missing hash → DISSONANCE(Unresolved Reference); bytes failing §4.1 → Canonical Invalid Object. (Sonnet P2.1.)
- Book I §5.1: truncated-hash footnote replaced with explicit pointer to `impl/sigma_glyph.py` TV-1 — one source of truth. (Sonnet P2.2.)
- ADR-001: retitled "node-count semantics"; `size(t)` definition moved into the header block. (Sonnet P2.4.)
- ROADMAP.md: new "Decision Process" section — multi-model review → impl gate → maintainer decision with written rationale → planned collective governance. (Sonnet P2.5.)
- **Anchor drift fixed:** v0.4.2 shipped without refreshing ANCHORS.txt (`verify_anchors.py` was failing). v0.4.2 anchors reconstructed retroactively and filed as ancestors; v0.4.3 anchors forged; `verify_anchors.py` now checks only the current section and green verification is a release gate.
- reviews/: Claude Sonnet 4.5 review filed (9.5/10); maintainer response with per-finding disposition (incl. one factual rejection: LORE is versioned since v0.4.1); settled points updated.

**Impact:** Clarifications only. No breaking changes. Reference impl unchanged. v0.4.3 is drop-in compatible with v0.4.2.

## v0.4.2 (2026-07)
- Book I §1.1: LITERAL validation timing clarified — normalize on on-demand validation at `resolve(h)`, eager validation is MAY. Closes P1 spec gap (DeepSeek finding).
- Book I §5.3: RESERVED hash bridge sentence — "reason hash, not opcode; doesn't affect deserialization."
- Book I §6: Explicit FV() definition for C1 compiler — normative annex now self-contained.
- Book II §4: LUT_COS range notation clarified — `d ∈ {0, 1, ..., 32768}` (integer inclusive).
- ROADMAP.md: Consolidated all pending breaking changes (ADR-001, ADR-002), v0.5 milestone, release discipline.
- reviews/: DeepSeek review filed (9.2/10); settled points updated.

**Impact:** Clarifications only. No breaking changes. Reference impl unchanged. v0.4.2 is drop-in compatible with v0.4.1.

## v0.4.1 (2026-07)
- Book I: "Signal Damped" demoted to Reserved (Era-1 legacy) — dead normative hash found by Qwen.
- Book II: Resonance Identity (self-application = quadratic amplitude map; MAX is the unique non-zero fixed point); 65534 range explanation.
- LORE: standing waves & self-reflection; Pantheon cultural-fork note.
- proposals/: ADR-001 (size-priced ATP, with computed vectors and memory bound), ADR-002 (entropy–coherence coupling, with worked integer examples).
- reviews/: Qwen review filed; settled points updated.

## v0.4.0 — "Cold Books" (2026-07)
- Restructured into three documents: Book I (Truth, hermetic core), Book II (Navigation, pure math), LORE (non-normative warmth). Per Kimi review.
- Canonical λ→SKI compiler profile C1 (normative annex; implemented, TV-10).
- Explicit R-R one-level-per-step rule + TV-9 (REF chain, 2 ATP).
- Mass formula; CP-24 collision warning; 65535 unit-scale rationale; RESERVED de-nostalgized; blob guards moved to implementation notes.
- Specification Anchor protocol; detached ANCHORS.txt for all three documents.

## v0.3.1 — "Sealed Contour" (2026-07)
- Resolution contract (§3.5): any resolve failure → DISSONANCE(Unresolved Reference), incl. APPLY children.
- Resource faults ≠ canonical dissonance (§3.6).
- LITERAL as inert commitment; BlobStore contract externalized.
- Pin > Derived annotation precedence (resolves FALSE 270° vs left-dominance 180°).
- Stress vectors: TV-6 duplication (tree=5 ATP vs sharing=4), TV-7 Omega, TV-8 unresolved child.
- SKI-only consensus hardened.
- Reference implementation (Book I, Milestone 1): ALL PASS.

## v0.3.0 — "Two Books" (2026-07)
- Wave removed from canonical bytes: WaveVectorQ is a view addressed by NodeHash, never part of identity.
- SKI rewriting as normative reduction semantics (normal order, ATP totalization). LAMBDA removed; binding dissolved.
- FALSE becomes structural: APPLY(K,I). Trinity = nominal axioms; everything else = structural theorems.
- LUT pinned: normative generation formula + SHA-256 arbiter.
- Law of Left Dominance (phase non-commutativity) made normative.
- Genesis re-forged (V2 waveless hashes); Era-1 preserved in migration appendix.

## v0.2.12 — Era-1 "Titanium Monolith" (2025)
- See archive/era-1/. Verified test vectors; genesis forge reconstructed post-hoc.
