# Σ-GLYPH Tools

Utilities for working with the sigma-glyph specification and implementation.

## `aggregate.sh` — Complete Repository Snapshot

**Purpose:** Generate a single markdown file containing the entire repository for sharing with AI models during review.

**Usage:**
```bash
./tools/aggregate.sh
```

**Output:** `sigma-glyph-full.md` (gitignored, ~65KB)

**What's included:**
- Repository structure overview
- Core documentation (README, CHANGELOG, LICENSE)
- All specifications (Book I, Book II, LORE, ANCHORS)
- Architecture Decision Records (ADRs)
- Multi-model review history
- Reference implementation
- Tooling scripts
- CI/CD configuration

**Use case:** When working with AI models that:
- Don't have CLI access (web-only interfaces)
- Don't have GitHub access
- Work better with a single file for context
- Need complete snapshot for comprehensive review

**Regenerate:** Run the script again after any changes to refresh the snapshot.

---

## `verify_anchors.py` — Specification Anchor Verification

**Purpose:** Verify that specification anchors in `spec/ANCHORS.txt` match the actual SHA-256 hashes of specification documents.

**Usage:**
```bash
python3 tools/verify_anchors.py
```

**What it checks:**
- `book-1-truth.md` anchor matches file hash
- `book-2-navigation.md` anchor matches file hash
- `LORE.md` anchor matches file hash

**Contract:** Specification anchors are `NodeHash(LITERAL, atom = SHA-256(document_bytes))` — ensuring published specs are immutable and verifiable.

---

## `warrant_gate.py` — fail-closed consumer of the Warrant machine boundary

**Purpose:** sigma-glyph's **single machine verification boundary** for CI/tooling.
It INVOKES the real Warrant verifier's documented machine interface —
`warrant verify --store-mode --json` (`warrant.verify-report@v0`) — and consumes
**only** the normative report fields, failing closed on everything else (stderr
contamination, non-single-line / invalid / multiple JSON, an unknown report tag, a
self-inconsistent report, a counts/findings mismatch, an exit code disagreeing with
`ok`, or `ok:false`). It never branches on a finding's `message` (non-portable
prose).

**Usage:**
```bash
export WARRANT="python3 /path/to/warrant/impl/warrant.py"   # required; or a warrant-go binary
python3 tools/warrant_gate.py .warrants                       # exit 0 iff verified
python3 tools/warrant_gate.py .warrants --settlement --trust-config trust-config.json
```

**Not a re-implementation.** Sigma-Glyph no longer ships a second, partial
Warrant verifier. `warrant_gate.py` consumes the real verifier's output and
proves that the published machine contract is sufficient for an external
consumer. `$WARRANT` must name the selected pinned checkout/binary; the tool
does not guess a filesystem path. Countervectors (real + hostile) live in
`tests/warrant_gate_test.py`.

---

## `evidence_view.py` — one derived version/evidence view

**Purpose:** print, as one deterministic JSON document, which bytes carry which
version label and what stands behind each — for a cold reader who should not
have to assemble it from five files by hand.

**Usage:**
```bash
python3 tools/evidence_view.py                                      # Sigma half only
python3 tools/evidence_view.py --warrant /absolute/path/to/warrant  # both halves
```

**It owns nothing.** Every value is read from the file that owns it
(`spec/ANCHORS.txt`, `pyproject.toml`, `campaigns/phase-4a/candidate-receipt.json`,
the operand's `trust/ski-runtime-evaluators.json` and `SPEC.md` §13.1) or
recomputed from bytes on the run that prints it, and each verifier's result is
reused under that verifier's name (`verify_anchors.py`, `version_check.py`,
`anchor_governance.py status`). There is no committed artifact to go stale and
no second truth table to drift.

**What a digest proves:** identity, and nothing else. Adoption is a threshold
warrant, conformance is a verifier run, and a runtime tag is a Warrant
registration; where the view could not run the tool that decides one of those,
or could not read one answer out of it, the status is `unavailable` or the
relation is `unchecked` — never `holds`. There is no top-level pass/fail badge:
the summary counts relations. (`credit_problems` is an internal self-check that
stops such a view being printed; it is not a certificate for one already
serialized.)

**Ambiguous input is not an answer.** Every record it reads has to say one
thing: a repeated JSON member, a repeated `13.1.` heading, table or tag row, an
unreadable row of the selected runtime table, or a governance status line
printed twice or not at all yields no status at all — never the last of the
conflicting readings. The runtime table is selected by the header it declares
and every one of its rows must then read, so a table cannot be picked out by
the very rows that parse while the ones that do not go unnoticed.

**It projects the frozen receipt; it does not validate it.** The relation names
the fields it reads out of `candidate-receipt.json` and checks those for
presence and type. Members it does not read are neither projected nor rejected,
so this is not closed-schema validation; `candidate_freeze_check.py` owns the
receipt and rebuilds what it froze, and the receipt's `checks_passed` tools are
listed as a historical reference, not as fresh conformance credit.

**The Warrant operand is explicit.** Cross-repository data is read only from the
directory named by `--warrant`. With no operand the Warrant-owned half is typed
`unavailable`; the view never discovers a sibling checkout, never reads
`$WARRANT`/`$SIGMA_GLYPH`/`$SIBLING`, and passes none of them to the tools it
runs. A non-Warrant operand is refused (exit 2), not degraded. `ski@v2` stays
`reserved_no_evaluator`, and bytes bound under a reserved tag are reported as a
disagreement, never as an admission.

**Exit:** `0` printed and every checkable relation holds; `1` printed with at
least one FAILING relation (reasons on stderr); `2` refused before printing.
Controls — refusal, hostile ambient state, drift, missing, extra, widening,
ambiguity, the adoption consumer boundary and the receipt projection — live in
`tests/evidence_view_test.py`.

---

## `retirement_check.py` — controlled-forgetting records

**Purpose:** read the `RetirementRecord`s in `history/retirement-records/` as
data and refuse when an operand is not what a record says: each retired
subject's digest is recomputed from the object git holds at the before
revision; the subject must be absent from the recorded apply tree and from the
working tree; the apply commit must be the direct child of the before revision
with the recorded tree; `loss` must be non-empty for every mode; pinned
replacement operands must not have drifted; and no tracked file outside the
tombstone class (`history/`, `.warrants/`, `CHANGELOG.md`) may cite a retired
path as current. The record set must equal a closed manifest inside the
checker, so a record cannot be deleted into a pass. Each lineage also has a pinned
subject inventory (path, digest, mode); deleting a single subject cannot hide
its resurrection. The lexical scan checks full paths and paths relative to the
referring file; it is not a general Markdown or URL parser.

```bash
python3 tools/retirement_check.py               # validate + replay every record
python3 tools/retirement_check.py --surface ID  # one record's live-surface postcondition
python3 tools/retirement_check.py --selftest    # burn each refusal with a mutation
```

**What it does not assert:** that retiring was wise, that a replacement is
semantically equivalent, or anything repository-wide — `VALID` is per record.
Profile `sigma-glyph.retirement-record@v0.1` is the in-repo `APPLIED` slice of
Manifesto's `CONTROLLED-FORGETTING-0.1` form, applied locally; Manifesto's
checker is not the consumer of these records. Editing this file changes the
digest the records pin as their postcondition entrypoint, so every record must
be re-pinned in the same commit — the friction is the point.

## Adding New Tools

When adding new tools:
1. Make scripts executable: `chmod +x tools/your-script.sh`
2. Add usage documentation to this README
3. If tool generates output files, add them to `.gitignore`
4. Follow existing patterns (use `set -euo pipefail` for bash scripts)
