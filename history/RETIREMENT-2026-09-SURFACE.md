# Surface reduction 2026-09 — three retirements from the active surface

Status: **APPLIED controlled-forgetting act**, three lineages, one transition.
Tombstone and index for what left the default tree on 2026-09-07; the
machine-readable records are `history/retirement-records/*.json`, checked in
CI by `tools/retirement_check.py`.

This changes **admission**, not truth. Nothing below was refuted, and nothing
below was erased: every byte is in git history and in the Zenodo deposit
snapshot `7ecba6a` ([10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651)).

Exact before revision: `281a12517d188e20878ab064e8deca78aaf55cb0`. The apply
commit and tree are in *Applied transition* at the end.

## Protocol, and its limit here

The form is Manifesto's `CONTROLLED-FORGETTING-0.1` §§1–10 (retirement modes,
invariants I1–I10, `RetirementRecord`), adopted there on 2026-09-03 for exactly
two combinations, of which this act uses one: `APPLIED + in-repo`. It is applied
**locally** — local records, a local consumer, local authority. Manifesto's
checker is not the consumer of these records and no authority is borrowed from
it; the local profile is `sigma-glyph.retirement-record@v0.1` so that a record
can never be mistaken for one Manifesto vouches for.

Modes used: `ARCHIVED` (excluded from default reasoning, not refuted) and
`SUPERSEDED` (a named successor holds the active role; **not** semantic
equivalence — every record names what is lost).

## Why these, and why now

The repository's adopted bundle is v0.7.0 (2026-08-30). Three things in the
default tree were competing with it for attention:

- **`reviews/` — 99 files, ~14 000 lines**, all from July 2026, all about
  v0.3.0–v0.6.6. Every finding in them was dispositioned in its paired
  `-response.md` and adjudicated in `.warrants/`; every settled point was
  extracted to `reviews/README.md`. Ten `.pass1` files were blind first passes
  of two-pass reviews — two versions of one document with different findings,
  which is the exact ambiguity §0 of the protocol names. A reader or model
  opening `reviews/` met a hundred historical documents before the three live
  ones.
- **`archive/` — 5 files, 1 386 lines**: the Era-1 0.2.12 documents and the
  v0.3.0/v0.3.1 Two Books RFCs, headed `FINAL STANDARD (SEALED)` and
  `DRAFT STANDARD`, with `MUST` clauses that later settled points supersede
  (eager materialization, LITERAL validation timing, wave-in-hash). The
  directory name said history; the bytes said standard.
- **`HANDOFF.md` and `briefs/`** — a dated hand-off from 2026-07-08 at the
  repository root and the two completed work orders it answered. Their
  acceptance surfaces are re-run by CI on every push.

`gates/`, `.warrants/`, `CHANGELOG.md` and the three August 2026 reviews are
**not** retired — see *What stays, and why*.

## Retrieval, with status

```sh
git show 281a12517d188e20878ab064e8deca78aaf55cb0:<historical-path>
```

Every retrieved subject carries this envelope, and a citation must carry it too:

```text
HISTORICAL Σ-GLYPH ARTIFACT — retired 2026-09-07, history/RETIREMENT-2026-09-SURFACE.md
retired from the default surface after 281a125
current admission: EXCLUDED; historical review allowed with this status
do not treat as current precedent without an explicit re-adoption act
```

Git availability is best-effort. The Zenodo snapshot `7ecba6a` (2026-08-23,
deposited under DOI 10.5281/zenodo.22069651) contains all 107 subjects and is
the preservation path that does not depend on this repository's remote.

---

## Lineage 1 — the July 2026 review corpus (`review-corpus-2026-07`)

**99 subjects**, all `reviews/2026-07-*` (`.md` and `.pass1`), mode `ARCHIVED`.
Relation: `extracted-from` — the extraction is `reviews/README.md` (protocol +
settled points) and this file's index below. Reviews are evidence; nothing
replaces evidence, so no subject is `SUPERSEDED`.

### Index of what was retired

Files are named by stem (`reviews/2026-07-<stem>.md`); `+r` = a paired
`-response.md`; `+p1` = a `.pass1` blind first pass.

| Round | Subject | Files (stems) | What it produced |
| --- | --- | --- | --- |
| v0.3.0–v0.4.1 first reviews | Two Books RFC | `claude`, `codex`, `kimi`, `qwen`, `deepseek` | scores 7.8–8.5/10; LORE split out of the spec; TV-9 / TV-6 pinned; the first settled points |
| v0.4.2 | Book I text | `claude-sonnet` +r | §3.5 `resolve()` branches made explicit; Decision Process added to ROADMAP; JSON conformance suite queued (later shipped) |
| v0.4.4 | conformance follow-up | `codex-v0.4.4-followup` +r | `eval` raised a raw `Unresolved` (totality bug) — fixed; `EV-REF-MISSING-ATP*` vectors |
| v0.5 ADR gate (3/3) | ADR-001/002/003 | `codex-v0.5-adr-gate` +r, `gemini-adr-gate` +r, `deepseek-adr-gate` +r | no ADR adopted as written; all three amended; hash-leaf size model chosen; adopted v0.5.0 |
| v0.5.0 post-release | shipped core | `codex-v0.5.0-audit` +r, `kimi-v0.5.0-audit` +r +p1, `opus48-v0.5.1-review` +r, `claude-v0.5-lazy-edges` +r | no P0; LITERAL prose/oracle split → ADR-004; dangling-hash rule → `tools/check_lazy_edges.py` |
| ADR-004/005 gate | blob scope, wave totality | `codex-adr45-gate` +r, `gemini-adr45-gate` +r, `deepseek-adr45-gate` +r +p1 | ADR-004 4/≥3 zero dissent; ADR-005 2:1 R1; adopted v0.5.1 |
| ADR-006 gate (3/3) | annotation federation | `codex-adr006-gate` +r, `gemini-adr006-gate` +r, `kimi-adr006-gate` +r +p1 | F1-strict selection-only federation; interference fold rejected (non-associativity) |
| Book III implementation gate | federation v0.6.0 | `codex-book3-gate` +r, `gemini-book3-verify` +r | block-until-P1s → fixed → ready to anchor; v0.6.0 |
| ADR-007 gate (3/3 + verify) | governed anchors | `gpt5-adr007-gate` +r +p1, `gemini-adr007-gate` +r +p1, `deepseek-adr007-gate` +r +p1, `kimi-adr007-verify` +r +p1 | `spec/GOV-anchors.md`; roster 2-of-3 since v0.6.2 |
| GOV STANDARD promotion gate | GOV-anchors DRAFT→STANDARD | `gpt5-gov-standard` +r +p1, `gemini-gov-standard` +r +p1, `deepseek-gov-standard` +r +p1 | unanimous PROMOTE-WITH-AMENDMENTS; Gemini's P0 liveness self-destruct fixed with `resolved_key_state`; v0.6.4 |
| v0.6.x audits | release surface, runtime | `codex-v0.6.0-pedantic-audit` +r, `codex-governance-hardening` (response only), `codex-v0.6.4-hardening-audit` +r, `kimi-v0.6.4-holistic` +r +p1, `kimi-v0.6.4-formal-focused` +r, `qwen-web-holistic` +r, `web-sonnet-reverification` (response only) | v0.6.1 hygiene; `GV-TRAILING-JSON-REJECTED` / `GV-NONCANONICAL-BLOB-REJECTED`; `tools/test-all.sh`; the four Lean fronts (ROADMAP) |
| v0.6.6 | GOV 1.0.2 patch, proofs | `v0.6.6-independent-gate`, `fable5-v0.6.6` (self-conducted), `gemini31pro-agy-audit` +r, `gptoss120b-agy-audit` +r, `antigravity-deep-review` +r, `kimi-full-audit` +r | torsion encodings added as defense-in-depth, refuted P0s recorded; C1 Lean mechanization judged sound; U+2028/2029 canon split closed |
| Warrant verify gate | `feat/warrant-verify-gate` | `codex-warrant-verify-gate`, `codex-warrant-verify-gate-regate` | APPROVE; the tool it gated was itself retired — `history/WARRANT-VERIFIER-REDUCTION-2026-09.md` |
| Cross-family round 2026-07-30/31 | guard, Ed25519, cross-repo | `antigravity-cross-family-audit` +r, `glm47-guard-coverage` +r, `glm47-ed25519` +r, `deepseekv32-guard` +r, `gemini31flashlite-ed25519` +r, `codex-cross-repo-runtime` (transcription) | one confirmed defect (non-recursive guard walk, `a4e7de1`); five P0/P1 refuted by one line each; two cross-repo P1s fixed |

**What the cross-family round was not** — kept with the table because a paper
cites it: those were cross-family reviews run by the same operator on the same
task framing, not independent gates in `AGENTS.md` §3's sense; no roster
threshold was met, no warrant records them, nothing in the round was adopted,
and two reviewers received truncated inputs through an operator packaging
error. `codex-cross-repo-runtime` is a transcription reconstructed from commit
bodies and must not be cited as the reviewer's text. The round established that
cross-family and same-family review find different things; it did not establish
a rate.

### Carried forward — findings not closed in the tree

The short active list Codex asked for. Each item names where it lives now.

- **Book III end-to-end at Warrant settlement level** — transport profile beyond
  file-copy, and settlement-grade candidate extraction in
  `examples/two-jurisdictions/`. Open in `ROADMAP.md` (v0.6 "Still open").
  Source: `codex-governance-hardening-response` #5.
- **Multi-scope anchor governance** — scope definitions deferred to a future
  ADR. Source: `deepseek-adr007-gate-response`, P1-2. Not tracked elsewhere.
- **Lean runner profile residual** — `BytesRun` / `EvalRun` / `WaveRun` run under
  `profile="runner"`, which relaxes `partial`; a hostile edit there could print
  hardcoded answers. Mitigated by the bridge differentials, not closed. Source:
  `antigravity-cross-family-audit-response`. **Not in
  `SECURITY-ASSUMPTIONS.md`**, which by its own rule makes that a defect in that
  file; listed here so it is not lost with the review.
- **Governance failure-mode analytics** (Kimi, P3) — filed as issues on
  `s0fractal/warrant`, not here.

### Known loss

- the full text of every finding, refutation and reproduction command — the
  index above keeps outcomes, not arguments;
- the reviewer-by-reviewer reasoning behind each settled point;
- the blind-pass provenance (`.pass1`) readable without `git show`;
- the July critiques as a browsable directory on GitHub — `docs/index.html`
  now points at this ledger instead;
- `experiments/exp-001/probe.py` measures `reviews/` at HEAD, so its §3 counts
  no longer reproduce `FINDINGS.md` from the working tree; reproduce at the
  before revision.

---

## Lineage 2 — the pre-Two-Books archive (`archive-eras`)

**5 subjects.** `archive/v0.3.0-two-books.md`, `archive/v0.3.1-two-books.md`,
`archive/era-1/v1.4-genesis-complete.md`,
`archive/era-1/v1.9.1-enlightened-extension.md` — `SUPERSEDED`;
`archive/era-1/README.md` — `ARCHIVED`.

Relation: `replaced-by` — the active role "the specification of Σ-GLYPH" is
held by the anchored Books, indexed by `spec/ANCHORS.txt`; the Era-1 forge
method and the four Era-1 hashes (`I=83948a41…`, `S=89723554…`,
`K=9a91a8ba…`, `FALSE=a0a0b559…`) are carried by `spec/LORE.md`.

The historical bytes remain CC BY 4.0, as `LICENSE` said when they were in the
tree; the retirement does not change their licence.

### Known loss

- the v0.3.0 Appendix A migration table (Era-1 → 0.3.0 hashes) — only in the
  retired document;
- the Era-1 test vectors TV-N1..N6 and their 2026 re-verification note;
- the Ukrainian prose of the first Two Books RFC, which `spec/LORE.md`
  summarizes but does not reproduce;
- reading superseded `MUST` clauses side by side with current ones without git.

---

## Lineage 3 — completed work orders (`work-orders-2026-07`)

**3 subjects**, mode `ARCHIVED`: `HANDOFF.md`, `briefs/BRIEF-book1-rust.md`,
`briefs/BRIEF-governance-go.md`. Relation: `none` — the deliverables
(`impl-rs/`, the Go `gov-replay` verifier) are in the tree and CI re-runs the
acceptance the hand-off recorded (`Book I third implementation (Rust)`,
`Governance second implementation (Go) + differential`).

### Known loss

- the exact task framing each second implementer was given, including what it
  was and was not allowed to read — the evidence of the "own logic, not a
  transliteration" rule; the Warrant records `631ad4a3…` and `835114b7…` still
  describe the zero-relay cycle;
- the 2026-07-08 acceptance transcript (49/49) as text rather than as a live
  CI step.

---

## What stays, and why

- **`gates/v0.7.0-candidate/`** — the frozen evidence of the currently adopted
  bundle (threshold warrant `0e634c17…46e1`). `tools/paper_claims.py` counts its
  rounds. Its README now says the candidate was adopted; nothing in a round
  directory was touched.
- **`.warrants/`** — signed, content-addressed records and blobs. Several cite
  retired review paths; they are immutable historical records and the citations
  carry the status above. Editing them would corrupt the store.
- **`reviews/2026-08-*`** — three live items: a registered review whose headline
  finding was resolved by ADR-010 but has no `-response.md`; a registered,
  undispositioned critique of the deposited paper; the pre-deposit full-system
  audit whose release order is partly done. `reviews/README.md` lists them.
- **`CHANGELOG.md`** — a dated log; its July entries cite July reviews as
  history, which is what a changelog is for.

## Reference transitions

Active files that cited a retired subject as current were rewritten in the
apply commit: `README.md`, `ARCHITECT.md`, `ROADMAP.md`, `LICENSE`,
`llms.txt`, `docs/index.html`, `SECURITY-ASSUMPTIONS.md`, `reviews/README.md`,
`tools/or_review.py` (its hard-coded prior-review list is now a glob over the
live inbox), `gates/v0.7.0-candidate/README.md` and `REPORT.md` (a status line
each). `MAP.md` was regenerated only if `tools/repo_map.py --check-map` asked.

Excluded from the zombie-reference scan as tombstone or immutable-history
class: `history/`, `.warrants/`, `CHANGELOG.md`. Nothing else is excluded.

`reviews/README.md` also lost two sections that were not about retired subjects
but were stale — "Open proposals" (every ADR it listed is adopted; ROADMAP owns
proposal status) and "Open fronts" (a copy of ROADMAP's) — and its adjudication
section named `tools/warrant_verify.py`, retired on 2026-09-03; it names
`tools/warrant_gate.py` now.

## Executable postconditions

`tools/retirement_check.py` (CI, `tools/test-all.sh`) reads the three records
as data and refuses, per record, when:

- a subject's digest at the before revision differs from the record, or the
  subject is still present in the apply tree or the working tree;
- the apply commit is not the direct child of the before revision, or its tree
  is not the recorded one;
- `loss` is empty for any record, or a `replaced-by` / `extracted-from`
  replacement operand's digest has drifted;
- any tracked file outside the excluded classes cites a retired path
  (`ZOMBIE_REFERENCE`);
- a record is missing from, or absent in, the checker's closed manifest — so a
  fixture cannot be deleted into a pass.

`--selftest` burns each of those with a mutation and requires the named
refusal. `VALID` means the record's operands bound and its postconditions
replayed green; it says nothing about whether retiring was wise.

## Re-adoption

Restoring bytes from git is not re-adoption. Returning any subject to the
default surface needs a new record that names the evidence for doing so; it
does not rewrite this one.

## Applied transition

- before revision: `281a12517d188e20878ab064e8deca78aaf55cb0`
- apply commit: recorded in `history/retirement-records/*.json` (`applied`)
- authority: repository owner instruction in the working session of
  2026-09-07, with Codex concurring as co-developer on scope and modes; the
  record addresses the act, it does not prove it was within anyone's power
- changed scope: the 107 subjects, this ledger, the reference transitions
  above; the receipt commit adds the records, the checker and its CI step
