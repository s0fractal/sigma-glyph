#!/usr/bin/env bash
# Aggregate all sigma-glyph content into a single markdown file for AI review
# Output: sigma-glyph-full.md (gitignored)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="$REPO_ROOT/sigma-glyph-full.md"

cd "$REPO_ROOT"

echo "# Σ-GLYPH — Complete Repository Snapshot" > "$OUTPUT"
echo "" >> "$OUTPUT"
echo "Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"

# Function to append a file with proper formatting
append_file() {
    local file="$1"
    local title="${2:-$file}"

    echo "" >> "$OUTPUT"
    echo "## File: \`$title\`" >> "$OUTPUT"
    echo "" >> "$OUTPUT"

    # Detect file type and use appropriate code fence
    case "$file" in
        *.md)
            echo '```markdown' >> "$OUTPUT"
            ;;
        *.py)
            echo '```python' >> "$OUTPUT"
            ;;
        *.txt)
            echo '```' >> "$OUTPUT"
            ;;
        *.sh)
            echo '```bash' >> "$OUTPUT"
            ;;
        *)
            echo '```' >> "$OUTPUT"
            ;;
    esac

    cat "$file" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo '```' >> "$OUTPUT"
    echo "" >> "$OUTPUT"
}

# Repository structure overview
echo "## Repository Structure" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo '```' >> "$OUTPUT"
tree -I '.git|__pycache__|*.pyc|.DS_Store' -L 3 2>/dev/null || find . -type f -not -path '*/\.*' | grep -v '.git' | sort
echo '```' >> "$OUTPUT"
echo "" >> "$OUTPUT"

# Core documentation
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "# Core Documentation" >> "$OUTPUT"
echo "" >> "$OUTPUT"

append_file "README.md"
append_file "CHANGELOG.md"
append_file "LICENSE"

# Specifications (The Three Books + LORE)
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "# Specifications" >> "$OUTPUT"
echo "" >> "$OUTPUT"

append_file "spec/book-1-truth.md" "spec/book-1-truth.md"
append_file "spec/book-2-navigation.md spec/book-3-federation.md" "spec/book-2-navigation.md"
append_file "spec/LORE.md" "spec/LORE.md"
append_file "spec/ANCHORS.txt" "spec/ANCHORS.txt"

# Proposals (ADRs)
if [ -d "proposals" ]; then
    echo "---" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "# Architecture Decision Records" >> "$OUTPUT"
    echo "" >> "$OUTPUT"

    for adr in proposals/*.md; do
        [ -f "$adr" ] && append_file "$adr"
    done
fi

# Reviews
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "# Multi-Model Reviews" >> "$OUTPUT"
echo "" >> "$OUTPUT"

append_file "reviews/README.md" "reviews/README.md"

for review in reviews/*.md; do
    [ -f "$review" ] && [ "$(basename "$review")" != "README.md" ] && append_file "$review"
done

# Reference implementation
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "# Reference Implementation" >> "$OUTPUT"
echo "" >> "$OUTPUT"

for impl in impl/*.py; do
    [ -f "$impl" ] && append_file "$impl"
done

# Tools
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "# Tooling" >> "$OUTPUT"
echo "" >> "$OUTPUT"

for tool in tools/*.py tools/*.sh; do
    [ -f "$tool" ] && [ "$(basename "$tool")" != "aggregate.sh" ] && append_file "$tool"
done

# GitHub workflows (if any)
if [ -d ".github/workflows" ]; then
    echo "---" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "# CI/CD Configuration" >> "$OUTPUT"
    echo "" >> "$OUTPUT"

    for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
        [ -f "$workflow" ] && append_file "$workflow"
    done
fi

# Archive (optional - can be large)
# Uncomment if you want to include archived versions
# if [ -d "archive" ]; then
#     echo "---" >> "$OUTPUT"
#     echo "" >> "$OUTPUT"
#     echo "# Archive (Historical Versions)" >> "$OUTPUT"
#     echo "" >> "$OUTPUT"
#     echo "*(Omitted from aggregate - see archive/ directory)*" >> "$OUTPUT"
# fi

echo "" >> "$OUTPUT"
echo "---" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "**End of sigma-glyph complete snapshot**" >> "$OUTPUT"

# Summary
FILE_SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
LINE_COUNT=$(wc -l < "$OUTPUT" | tr -d ' ')

echo ""
echo "✓ Aggregation complete: sigma-glyph-full.md"
echo "  Size: $FILE_SIZE bytes"
echo "  Lines: $LINE_COUNT"
echo ""
echo "Usage: Share sigma-glyph-full.md with AI models for review"
