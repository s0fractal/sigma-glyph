# PROP-book1-en-normative — the English Book I as the normative citation target

**Status:** PROPOSED — **NOT ADOPTED**. No adoption warrant exists, no gate has
run, and none of this is in force. Changing which language edition is normative
is a spec-governance act: it re-hashes anchored documents and inverts the
document/oracle precedence rule, so it can only take effect through a threshold
warrant adopted by the 2-of-3 roster (GOV-anchors §3, §5) after the project's
Decision Process (gate of ≥3 model families). This proposal ships the complete
candidate text — the rewritten [`spec/book-1-truth.en.md`] on this branch — so
the gate reviews bytes, not intentions. The Ukrainian
[`spec/book-1-truth.md`](../spec/book-1-truth.md) remains the normative,
anchored citation target, untouched by this branch.
**Provenance:** drafted by a Claude agent (Fable 5) on
`proposal/book1-en-normative`, 2026-07-30, from the maintainer's strategy
brief. Self-verified only (verification record below); **no independent gate,
no review, no roster authority is claimed.**

## Problem / Motivation

1. **External implementers cannot consume a Ukrainian citation target.** Book I
   is the consensus contract — the one document a stranger must read to build a
   node that agrees on result hashes. Standards bodies, auditors, and
   implementers overwhelmingly work in English; today the English text is
   explicitly "not the citation target" (llms.txt), so any serious external
   consumer must either read Ukrainian or trust an edition the project itself
   labels non-authoritative. That is a structural adoption blocker for a spec
   whose whole purpose is re-running a *stranger's* reason.
2. **The normative text is not self-contained.** Ukrainian §5.1 deliberately
   defers the full SHA-256("I"/"K"/"S") values to `impl/sigma_glyph.py`. An
   implementer building from the document alone cannot produce the genesis
   atoms without reading the reference implementation — which contradicts the
   claim that the document defines the consensus.
3. **"Oracle wins over prose" makes the code the spec.** Ukrainian §7 says that
   on any prose/vectors discrepancy, `impl/sigma_glyph.py` wins. For a
   standards-track document this is inverted: it means no external implementer
   can ever be conformant against the *document* — only against a Python
   program. A citation target must be authoritative over its own reference
   implementation, with divergences resolved by errata, not by fiat of the code.

## Exact change list

On adoption (and only then), all of the following in one governed release:

| # | Change | Where |
|---|--------|-------|
| 1 | `spec/book-1-truth.en.md` becomes the **normative** Book I citation target | en header; new anchor |
| 2 | `spec/book-1-truth.md` (Ukrainian) becomes an **informative translation** (header note added; body otherwise byte-identical) | uk header; new anchor |
| 3 | Precedence inverted: "This document is authoritative; `impl/sigma_glyph.py` is the reference implementation; a divergence between them is a defect in one of them, resolved by an erratum" replaces "on any discrepancy the oracle `impl/sigma_glyph.py` wins" | en §7 (drafted, marked `[PROPOSED]`) |
| 4 | Genesis constants inlined: full SHA-256("I"/"K"/"S"), full CanonicalBytes for I/K/S, full FALSE bytes — the document alone suffices to build an evaluator | en §5.1, §5.2 (drafted) |
| 5 | The en candidate's `NOT ADOPTED` banner and the two italic "until adoption the Ukrainian rule governs" sub-notes are removed; the `[PROPOSED — takes effect only on adoption]` markers are dropped (the clauses stay) | en header, §5.1, §7 |
| 6 | `spec/ANCHORS.txt` next release section adds `spec/book-1-truth.en.md` with its `NodeHash(LITERAL, atom=SHA-256(document_bytes))`, and re-anchors the retouched uk file; anchor-set blob per GOV-anchors §2, `anchors` sorted by path | ANCHORS.txt, `.warrants/` |
| 7 | `llms.txt` and any other "en is informative, not the citation target" statements flip direction | llms.txt, README if applicable |

`tests/spec_conformance/vectors.json` stays normative and unchanged. **Nothing
in this proposal changes any byte, hash, price, or vector** — reduction,
serialization, and ATP semantics are untouched; this is a change of citation
target and precedence only.

## Adoption mechanics

Per GOV-anchors (STANDARD 1.0.2) and ADR-007:

1. **Gate first.** This inverts a load-bearing precedence rule, so it is not a
   PATCH-style clarification (contrast `book3-nfc-and-spam-clarifications.md`):
   it requires the full Decision Process — a gate of ≥3 model families
   adversarially checking the clause-coverage table below and the inlined
   constants, with written adjudication.
2. **One anchor-set adoption.** The release's anchor-set blob
   (`sigma-glyph.anchor-set@v1`) includes the new en anchor and the retouched
   uk anchor; the `accept` warrant is filed under the profile/threshold pair in
   force (P1/T1, §5 of GOV-anchors), signed by ≥2 of the 3 roster actors,
   settlement-active in `.warrants/`.
3. **Version.** Suggested: both editions bump Book I to **0.5.3** with a
   CHANGELOG entry "editorial/governance: normative language switched to
   English; zero semantic change; all 49 vectors byte-identical" — final call
   is the maintainer's (open question 1).
4. **Continuity honesty.** Prior anchors of the uk edition remain the normative
   ancestors of their eras; this adoption claims continuity-from-then, not a
   retroactive re-labeling of history (GOV-anchors §1, bootstrap honesty).

## Honest risks

- **Translation drift.** Two texts now exist and future edits could diverge.
  Mitigations: (a) only one edition is normative at any time — uk flips to
  informative, so there is never a bilingual tie to adjudicate; (b) the
  clause-coverage table below lets a reviewer audit completeness mechanically;
  (c) the RFC 2119 keyword census is identical per section in both editions
  (verified below) and any future Book I edit should re-run that census.
- **Inverting oracle-wins makes prose bugs normative.** Today a prose error is
  harmless (the oracle wins); after adoption an undiscovered prose error *is*
  the spec until an erratum passes governance. Mitigations: the 49-vector
  anchored conformance suite and three independent implementations
  (Python/Rust/Go) bound the blast radius to whatever the vectors do not pin;
  the erratum path is the same governed release process, so a divergence is
  fixed loudly, not silently.
- **Inlining constants creates a duplication surface.** The doc and the impl
  now both state SHA-256("I"/"K"/"S") etc.; a typo in the adopted doc would be
  normative and wrong. Mitigations: every inlined value was recomputed
  independently (hashlib, from the §2 byte layout) and matches the impl's
  pinned assertions; recommend a CI check hashing the doc's stated constants
  against the impl before the adopting release (open question 2).
- **Author conflict.** This proposal was drafted by an agent of the same model
  family as a roster actor. The gate must include reviewers outside that
  family; the draft claims no review authority.

## Clause-coverage table (uk → en)

Audit key: **F** = faithful translation (verbatim hashes/keywords, no semantic
change); **D** = deliberate, marked deviation (takes effect only on adoption);
**+** = marked *(computed)* addition — derivable values absent from uk,
included for self-containment. RFC 2119 keyword counts (MUST excl. MUST NOT /
MUST NOT / SHOULD / MAY) were machine-counted per section and are **identical
in both editions** for every row: totals 19/12/1/7 per edition (the SHOULD and
one each of MUST/MUST NOT/MAY are the keyword-declaration line itself).

| # | uk section | Normative content | en section | Keywords | Status |
|---|-----------|-------------------|-----------|----------|--------|
| 1 | Header + Scope + RFC 2119 line | scope isolation MUST NOT; keyword decl | Header + Scope | 1/2/1/1 | F (+ NOT-ADOPTED banner, D by necessity: status marker only) |
| 2 | §1.1 SigmaNodeV2 | opcode enum; Flags table (MUST equal); mask MUST-zero; blob contract MUST; ADR-004 MUST NOT ×2, MAY | §1.1 | 3/2/0/1 | F |
| 3 | §1.2 invalid opcodes | unknown bytes → Canonical Invalid Object MUST | §1.2 | 1/0/0/0 | F |
| 4 | §2 serialization | layout; field order; NodeHash = SHA-256 | §2 | 0/0/0/0 | F |
| 5 | §3.1 rules | R-I/R-K/R-S/R-R; one-level R-R MUST; 3n ATP chain; EV-TV9 | §3.1 | 1/0/0/0 | F |
| 6 | §3.2 recognition | identity by hash MUST | §3.2 | 1/0/0/0 | F |
| 7 | §3.3 machine | step() pseudocode; divergence class MUST NOT; two examples | §3.3 | 1/1/0/0 | F |
| 8 | §3.4 ATP | size model; 5 price rules; eval signature + 3 canonical outcomes; uint32 MAY; exhaustion-precedes; totality MUST NOT; memory-bound theorem + guard MUST; tree accounting MUST/MAY | §3.4 | 3/1/0/2 | F |
| 9 | §3.5 resolution | failure modes (a)/(b); lazy materialization; 0.4.x breaking-change note | §3.5 | 1/0/0/0 | F |
| 10 | §3.6 faults | implementation fault MUST NOT be DISSONANCE | §3.6 | 1/1/0/0 | F |
| 11 | §3.7 tooling | trace_eval MAY; MUST NOT change eval | §3.7 | 0/1/0/2 | F |
| 12 | §4.1 deserialization | 4-step validation MUST | §4.1 | 1/0/0/0 | F |
| 13 | §4.2 invalid object | exact bytes + hash | §4.2 | 1/0/0/0 | F |
| 14 | §5.1 axioms table | I/K/S bytes + NodeHash | §5.1 | — | F, **+** full atom values and full CanonicalBytes inlined |
| 15 | §5.1 note "full values in impl, deliberately not duplicated" | (anti-duplication rationale) | §5.1 `[PROPOSED]` paragraph | — | **D1**: note replaced — the doc becomes the single source, impl cross-checks |
| 16 | §5.1 genesis intrinsic | intrinsic resolve MUST; UNRES MUST NOT; FALSE-is-theorem | §5.1 | 2/1/0/0 | F |
| 17 | §5.2 FALSE | bytes formula + hash | §5.2 | — | F, **+** full bytes hex |
| 18 | §5.3 reason hashes | 3 reason hashes MUST; Signal Damped reserved MUST NOT | §5.3 | 1/1/0/0 | F |
| 19 | §6 C1 compiler | FV def MUST NOT capture; C1/A rules; order strict; η MUST NOT; determinism; no extensional canonicity; frontends MAY | §6 | 0/2/0/1 | F |
| 20 | §7 preamble + TV-1..TV-3 | MUST PASS; vectors.json normative; **oracle-wins precedence** | §7 | 1/0/0/0 | **D2**: precedence inverted, marked `[PROPOSED]`, current rule quoted alongside |
| 21 | §7 TV-4..TV-12 + negatives | 9 vectors, exact hashes + ATP counts; negative class | §7 | — | F, **+** TV-9 r1/r2 hashes, TV-11 ghost hash *(computed)* |
| 22 | §8 SpecAnchor | anchor formula; detached publication; fork-with-ancestor | §8 | — | F |
| 23 | Epigraph | — | Epigraph | — | F |

**Coverage: 23/23 uk units mapped; 0 gaps; 2 deliberate deviations (D1, D2),
both marked `[PROPOSED — takes effect only on adoption]` in the candidate
text; 4 marked *(computed)* additions, all machine-derivable from §2 and
re-verified against the reference implementation.**

## Verification record (what was and was not verified)

Performed 2026-07-30 on this branch, worktree of `master` @ `f9ec499`:

- **Constants recomputed independently** (Python `hashlib` directly from the
  §2 byte layout, not via the impl): SHA-256("I"/"K"/"S"); NodeHash H(I), H(K),
  H(S); FALSE bytes and hash; Canonical Invalid Object bytes and hash; TV-3
  bytes and hash; reason hashes for "Invalid Object", "ATP Exhausted",
  "Unresolved Reference", "Signal Damped". **All match** the pinned assertions
  in `impl/sigma_glyph.py` and every hex string in both spec editions.
- **Vectors re-run** through the reference evaluator (`eval_hash`): TV-4 (4
  ATP, and the 0/2/3-budget exhaustion cases via the suite), TV-5 (12 ATP),
  TV-6 (21 ATP, NF `APPLY(K,K)`), TV-7 (ATP Exhausted), TV-8 (spent 4), TV-9
  (6 ATP; budget-1 case via suite), TV-10 (20 ATP → ⟨S⟩), TV-11 (7 and 20
  ATP), TV-12 (3 ATP on empty store; bare thunk 0 ATP) — every hash and ATP
  count quoted in the candidate text reproduced exactly.
- **Suites:** `python3 impl/sigma_glyph.py` → **ALL PASS (35 checks)**;
  `python3 tests/spec_conformance/run_reference.py` → **CONFORMANCE: ALL PASS
  (49/49)**. Both unchanged by this branch (no code touched).
- **Keyword census:** per-section RFC 2119 counts machine-compared between the
  uk source and the en candidate — identical for all 16 keyword-bearing
  sections.
- **Not verified / not claimed:** no independent adversarial gate; no roster
  review; no adoption; no warrant filed; the translation's prose fidelity was
  self-checked clause-by-clause by the drafting agent only. Green suites are
  necessary, not sufficient (AGENTS.md rule 3).

## Non-goals

Changing any reduction, serialization, pricing, or vector semantics;
re-anchoring history; retroactive legitimization; deprecating the Ukrainian
text (it remains published, anchored, and maintained as the informative
translation); machine translation of Books II/III (a separate proposal once
this pattern is judged).

## Open questions for the maintainer

1. **Version bump on adoption** — 0.5.3 for both editions, or keep 0.5.2 with
   the change carried by the release bundle version only?
2. **Constants CI check** — add a small tool that extracts every hex constant
   from the normative doc and re-derives it (hashlib), run in `test-all.sh`,
   before the adopting release?
3. ***(computed)* additions** — keep the convenience values (TV-9 r1/r2, TV-11
   ghost, FALSE full bytes) in the adopted text, or strip them for strict
   verbatim parity with the uk source?
4. **Scope of the uk retouch** — is the informative-translation header note on
   the uk file part of this same warrant (one release, two re-anchored files),
   or a follow-up?
5. **Gate composition** — given the drafting agent's family sits on the
   roster, which ≥3 families run the gate, and should the clause-coverage
   audit be a required gate deliverable?
