# Σ-GLYPH Tools

Utilities for working with the sigma-glyph specification and implementation.

## `verify_anchors.py` — Specification Anchor Verification

**Purpose:** Verify that specification anchors in `spec/ANCHORS.txt` match the actual SHA-256 hashes of specification documents.

**Usage:**
```bash
python3 tools/verify_anchors.py
```

**What it checks:** every file of the current (topmost) section of
`spec/ANCHORS.txt` hashes to its anchor. A file retired on 2026-10-31 (Books II
and III, GOV-anchors, LORE and their suites) is read at the commit it was
retired from, so the adopted bytes stay verifiable; the check needs that
history (CI unshallows first).

**Contract:** Specification anchors are `NodeHash(LITERAL, atom = SHA-256(document_bytes))` — ensuring published specs are immutable and verifiable.

---

## Adding New Tools

When adding new tools:
1. Make scripts executable: `chmod +x tools/your-script.sh`
2. Add usage documentation to this README
3. If tool generates output files, add them to `.gitignore`
4. Follow existing patterns (use `set -euo pipefail` for bash scripts)
