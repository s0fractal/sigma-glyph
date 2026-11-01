# Σ-GLYPH Tools

Utilities for working with the sigma-glyph specification and implementation.

The specification's integrity is held by Warrant's records (claims quoting each
normative sentence, the claims checker's acceptances) and the release tags; the
anchor registry and `verify_anchors.py` were retired on 2026-11-01
(`history/RETIREMENT-2026-11-ANCHORS.md`).

---

## Adding New Tools

When adding new tools:
1. Make scripts executable: `chmod +x tools/your-script.sh`
2. Add usage documentation to this README
3. If tool generates output files, add them to `.gitignore`
4. Follow existing patterns (use `set -euo pipefail` for bash scripts)
