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

## Adding New Tools

When adding new tools:
1. Make scripts executable: `chmod +x tools/your-script.sh`
2. Add usage documentation to this README
3. If tool generates output files, add them to `.gitignore`
4. Follow existing patterns (use `set -euo pipefail` for bash scripts)
