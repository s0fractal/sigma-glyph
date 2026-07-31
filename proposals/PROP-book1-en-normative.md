# PROP-book1-en-normative — the English Book I as the normative citation target

**Status:** PROPOSED — **NOT ADOPTED**. No adoption warrant exists for the
v0.6.8 anchor set, no independent gate has run, and none of this is in force.
Changing which language edition is normative is a spec-governance act: it
re-hashes two anchored documents and inverts the document/oracle precedence
rule, so it can only take effect through a threshold warrant adopted by the
2-of-3 roster (GOV-anchors §3, §5) after the project's Decision Process (gate
of ≥3 model families).

**What the branch carries.** `proposal/book1-en-normative` ships the complete
candidate *in its adopted form*: `spec/book-1-truth.en.md` reads as the
normative citation target, `spec/book-1-truth.md` reads as the informative
translation, the precedence rule is inverted, and `spec/ANCHORS.txt` carries a
`== v0.6.8 ==` section whose anchor-set blob is in `.warrants/blobs/`. There
are deliberately **no `[PROPOSED — takes effect only on adoption]` markers in
the spec text**: the gate should review the bytes that would be in force, and
the fact that they are not in force yet lives here, in the commit bodies, and —
authoritatively — in the empty adoption slot the verifier reports:

```
v0.6.7     AUTHORIZED — adopted by b4dc05e307b8 (2/2 of 3)
v0.6.8     NOT AUTHORIZED — no satisfying adoption warrant in settlement closure
```

Until that second line changes, **the anchored, in-force Book I is the v0.6.7
set — the Ukrainian edition.** A branch is not the trunk and a candidate is not
a release.

**Provenance:** drafted by a Claude agent (Fable 5) on
`proposal/book1-en-normative`, 2026-07-30; re-verified and brought level with
master 2026-07-31. Self-verified only (verification record below); **no
independent gate, no review, no roster authority is claimed.**

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
3. **"Oracle wins over prose" makes the code the spec.** Ukrainian §7 said that
   on any prose/vectors discrepancy, `impl/sigma_glyph.py` wins. For a
   standards-track document this is inverted: it means no external implementer
   can ever be conformant against the *document* — only against a Python
   program. A citation target must be authoritative over its own reference
   implementation, with divergences resolved by errata, not by fiat of the code.

## Exact change list

All of the following are **on the branch** and take effect **only** on
adoption of the v0.6.8 anchor set:

| # | Change | Where | On branch |
|---|--------|-------|-----------|
| 1 | `spec/book-1-truth.en.md` becomes the **normative** Book I citation target | en header | done |
| 2 | `spec/book-1-truth.md` (Ukrainian) becomes an **informative translation** | uk header | done |
| 3 | Precedence inverted: "this document is authoritative; `impl/sigma_glyph.py` is a reference implementation, not the definition; a divergence is a defect resolved by an erratum" replaces "on any discrepancy the oracle wins" — stated in **both** editions so they cannot state opposite rules | en §7, uk §7 | done |
| 4 | Genesis constants inlined: full SHA-256("I"/"K"/"S"), full CanonicalBytes for I/K/S, full FALSE bytes — the document alone suffices to build an evaluator | en §5.1, §5.2 | done |
| 5 | The en candidate's `NOT ADOPTED` banner and the `[PROPOSED — takes effect only on adoption]` markers are removed; the clauses stay | en header, §5.1, §7 | done |
| 6 | `spec/ANCHORS.txt` gains `== v0.6.8 ==` with 11 anchors (both Book I editions + the 9 carry-overs); anchor-set blob per GOV-anchors §2, `anchors` sorted by path, `ancestor` = the adopted v0.6.7 set | ANCHORS.txt, `.warrants/blobs/` | done |
| 7 | "en is informative, not the citation target" statements flip direction | `llms.txt`, `README.md`, `QUICKSTART.md`, `tools/README.md`, `tools/repo_map.py`, `briefs/BRIEF-book1-rust.md`, `docs/index.html` | done |
| 8 | `tools/anchor_governance.py` selftest pin moves `v0.6.7`/10 anchors → `v0.6.8`/11 | selftest | done |

`tests/spec_conformance/vectors.json` stays normative and unchanged. **Nothing
in this proposal changes any byte, hash, price, or vector** — reduction,
serialization, and ATP semantics are untouched; this is a change of citation
target and precedence only. `pyproject.toml` deliberately stays at `0.6.7`:
the precedent set by `16a1355` is that the distribution version follows the
**adopted** bundle, so it moves after the warrant, not before it.

## Adoption mechanics

Per GOV-anchors (STANDARD 1.0.2) and ADR-007:

1. **Gate first.** This inverts a load-bearing precedence rule, so it is not a
   PATCH-style clarification (contrast `book3-nfc-and-spam-clarifications.md`):
   it requires the full Decision Process — a gate of ≥3 model families
   adversarially checking the clause-coverage table below and the inlined
   constants, with written adjudication.
2. **One anchor-set adoption.** The v0.6.8 anchor-set blob is already built and
   stored at the address the verifier computes:

   ```
   blob      c4eddcc1211d6c2a11398bbd12ed53fe9ed207bf1394e5aeffcc79660279cd86
   ancestor  d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5  (v0.6.7, adopted)
   release   v0.6.8      anchors 11, sorted by path
   ```

   The `accept` warrant is filed under the profile/threshold pair in force
   (P1/T1, §5 of GOV-anchors), signed by ≥2 of the 3 roster actors,
   settlement-active in `.warrants/`. The runbook with the exact commands is
   `strategy-2026-07/ADOPT-v0.6.8.md`.
3. **Version.** Both editions stay at Book I document version **0.5.2** — see
   open question 1, now answered.
4. **Continuity honesty.** Prior anchors of the uk edition remain the normative
   ancestors of their eras; this adoption claims continuity-from-then, not a
   retroactive re-labeling of history (GOV-anchors §1, bootstrap honesty). The
   `spec/ANCHORS.txt` header says so in the file itself.

## Honest risks

- **Translation drift.** Two texts now exist and future edits could diverge.
  Mitigations: (a) only one edition is normative at any time — uk flips to
  informative, so there is never a bilingual tie to adjudicate; (b) the
  clause-coverage check below is mechanical and re-runnable; (c) the RFC 2119
  keyword census is identical per section in both editions (re-verified below)
  and any future Book I edit should re-run that census. **Not mitigated:**
  nothing in `test-all.sh` re-runs the census automatically, so drift would be
  caught by review, not by a gate. See open question 2.
- **Inverting oracle-wins makes prose bugs normative.** Today a prose error is
  harmless (the oracle wins); after adoption an undiscovered prose error *is*
  the spec until an erratum passes governance. Mitigations: the 49-vector
  anchored conformance suite and three independent implementations
  (Python/Rust/Go) bound the blast radius to whatever the vectors do not pin;
  the erratum path is the same governed release process, so a divergence is
  fixed loudly, not silently.
- **Inlining constants creates a duplication surface.** The doc and the impl
  now both state SHA-256("I"/"K"/"S") etc.; a typo in the adopted doc would be
  normative and wrong. Mitigations: **every** 64-hex-or-longer literal in the
  English document was recomputed from the §2 byte layout with `hashlib`
  alone — 27 values, zero unexplained (see the verification record) — and each
  matches the implementation. Recommend making that a CI check before the
  adopting release (open question 2).
- **Author conflict.** This proposal was drafted by an agent of the same model
  family as a roster actor. The gate must include reviewers outside that
  family; the draft claims no review authority.

## Clause coverage (uk → en)

Re-derived mechanically on 2026-07-31 from the two files as they stand on this
branch (headings → sections, longest-first RFC 2119 keyword count per section):

- **23 of 23 sections present in both editions; 0 gaps in either direction.**
- **Per-section RFC 2119 census identical in every section**; totals
  **19 MUST / 12 MUST NOT / 1 SHOULD / 7 MAY** in each edition. (Counting
  convention: keywords in heading lines are attributed to the heading, not the
  body — applied identically to both files.)
- **Every ADR reference in uk appears in en** (ADR-001, ADR-003, ADR-004); none
  extra.
- **Every rule/vector identifier in uk appears in en** (R-I/R-K/R-S/R-R,
  TV-1…TV-12, EV-TV9, C1/A); none extra.
- **Every hex literal in uk appears in en.** en carries **9 additional** hex
  literals — the self-containment values: `SHA-256("I"/"K"/"S")`,
  `CanonicalBytes(K)`, `CanonicalBytes(S)`, the full FALSE bytes, TV-9's `r1`
  and `r2`, and the TV-11 ghost hash. Each is marked *(computed)* where the uk
  edition leaves it implicit, and each was independently recomputed.

Two deliberate deviations, both now unmarked because the branch is the adopted
form: **D1** — uk §5.1's "the full values live in the implementation,
deliberately not duplicated" note is replaced by the inlined constants plus the
statement that the document is the single source and the implementation
cross-checks it. **D2** — the precedence inversion in §7, mirrored into uk §7
so the two editions do not state opposite rules.

## Verification record (what was and was not verified)

Performed **2026-07-31** on this branch after merging master (`16a1355`),
independently of the 2026-07-30 run — nothing from that run was trusted:

- **Constants recomputed independently.** A script using `hashlib` only,
  building nodes from the §2 layout (`[Op][Flags][Atom?][Left?][Right?]`) and
  never importing `impl/sigma_glyph.py`, derived 27 values: SHA-256("I"/"K"/"S");
  CanonicalBytes and NodeHash for I/K/S; FALSE bytes and hash; the Canonical
  Invalid Object bytes and hash; the four reason hashes; TV-3 bytes and hash;
  TV-4/5/6/7 hashes; TV-9 `r1`/`r2`; TV-10's `C1[λx.λy.x]`; the TV-11 ghost.
  It then scanned the English document for **every** run of ≥16 hex characters
  and matched each against the derived set: **27 matched, 0 unexplained.** The
  document contains no constant that cannot be re-derived from its own rules.
- **Vectors re-executed against the current reference implementation.** 34
  assertions, all passing: TV-1/2/3 identities and the Invalid Object hash;
  TV-4 with its 4-ATP result and all three exhaustion cases (budgets 0, 2, 3
  with `spent` 0, 0, 3); TV-5 (12 ATP); TV-6 (normal form `APPLY(⟨K⟩,⟨K⟩)`,
  exactly 21 ATP); TV-7 (ATP Exhausted at every budget sampled); TV-8
  (Unresolved Reference, spent 4); TV-9 (6 ATP, and budget-1 → spent 0);
  TV-10 (`C1[λx.x] = ⟨I⟩`, the compiled hash, 20 ATP → ⟨S⟩); TV-11 (7 and 20
  ATP); TV-12 (3 ATP on an empty store, bare thunk 0 ATP); the §3.3
  divergence-class example; and the four §4.1 negatives. Every hash and every
  ATP count quoted in the candidate reproduced exactly.
- **Clause coverage / keyword census re-derived** — the section above.
- **The Ukrainian source did not move.** `spec/book-1-truth.md` is byte-identical
  between the branch point (`f9ec499`) and master (`16a1355`); its anchor
  `a98a03bd…` has been unchanged since v0.5.2. The English candidate was
  therefore already level with the normative text; no back-porting was needed.
- **Anchor bundle verified in an isolated copy first.** The v0.6.8 blob address
  was computed with the same expression `anchor_governance.status` uses —
  `sha256(canon(anchor_set_blob(...)))` — not by hashing `make-blob`'s stdout
  (which appends a newline and yields a different, useless address). Written
  into a throwaway copy of the tree, `status --enforce` moved from
  "no anchor-set blob in store" to "no satisfying adoption warrant in
  settlement closure"; only then was the same blob written to the real store.
- **Suites.** `tools/test-all.sh` runs green up to and including the anchors
  and governance surfaces; the enforce gate is the intended stopping point
  while v0.6.8 is unadopted.
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

1. **Version bump on adoption** — *answered on this branch: no bump.* Both
   editions stay at 0.5.2. Bumping to 0.5.3 cascades: `SPEC_VERSION` in
   `tests/spec_conformance/generate.py` → `spec_version` in `vectors.json` →
   that file's anchor → a wider bundle; and `spec/GOV-anchors.md` §0 pins
   "Book I v0.5.2" as a normative dependency, so a bump edits a STANDARD. The
   semantics are unchanged, so the cheaper and more honest reading is that the
   *bundle* version (v0.6.8) records the change and the document version
   records the text's semantic era. Reversible — say the word and it becomes a
   three-file bundle instead of a two-file one.
2. **Constants CI check** — still open, and now the largest residual risk.
   Add a tool that extracts every hex constant from the normative doc and
   re-derives it (the verification script above is a working prototype), plus
   the uk↔en keyword census, and run both in `test-all.sh`?
3. ***(computed)* additions** — *answered on this branch: kept.* Stripping them
   would re-open motivation 2 (self-containment), which is half the point.
4. **Scope of the uk retouch** — *answered on this branch: same warrant.* One
   release, two re-anchored files. The uk edit is two things: the
   informative-translation header note, and the §7 precedence inversion so the
   two editions do not state opposite rules. Leaving the old "the oracle wins"
   sentence in an informative edition would be a stale contradiction of exactly
   the kind this repository keeps finding.
5. **Gate composition** — given the drafting agent's family sits on the
   roster, which ≥3 families run the gate, and should the clause-coverage
   audit be a required gate deliverable?
