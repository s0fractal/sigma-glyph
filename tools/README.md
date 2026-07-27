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
export WARRANT="python3 /path/to/warrant/impl/warrant.py"   # or a warrant-go binary
python3 tools/warrant_gate.py .warrants                       # exit 0 iff verified
python3 tools/warrant_gate.py .warrants --settlement --trust-config trust-config.json
```

**Not a re-implementation.** This is the opposite of `warrant_verify.py`:
`warrant_verify.py` is a *deliberately independent* zero-dependency re-derivation
of Warrant verification for offline auditors (no warrant checkout needed);
`warrant_gate.py` *consumes the real verifier's output* to prove the published
machine contract is sufficient for an external consumer. Countervectors (real +
hostile) live in `tests/warrant_gate_test.py`.

---

## Adding New Tools

When adding new tools:
1. Make scripts executable: `chmod +x tools/your-script.sh`
2. Add usage documentation to this README
3. If tool generates output files, add them to `.gitignore`
4. Follow existing patterns (use `set -euo pipefail` for bash scripts)
