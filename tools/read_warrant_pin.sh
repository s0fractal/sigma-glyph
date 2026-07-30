#!/usr/bin/env bash
# Extract THE WARRANT_PIN from .github/workflows/ci.yml — fail closed.
#
# tools/test-all.sh used to do this inline with `sed -n '...p'`, which prints
# EVERY matching line: two WARRANT_PIN: lines produced a two-line value, the
# per-line `grep -qE '^[0-9a-f]{40}$'` validator still matched, and the
# malformed URL then made both network parity checks fall into their "skip:
# not reachable" branch — a forbidden ci.yml state (duplicate pin) was
# misdiagnosed as a network problem (2026-07 adversarial review, P1).
#
# This helper asserts EXACTLY ONE pin line exists, tolerates the YAML forms
# real CI reads fine (trailing `# comment`, surrounding quotes), validates the
# single resulting value strictly, and prints it. Any violation is a hard
# error naming the actual condition — never a skip.
#
# Usage: tools/read_warrant_pin.sh [path/to/ci.yml]
set -euo pipefail

CI_YML="${1:-.github/workflows/ci.yml}"
[ -f "$CI_YML" ] || { echo "ERR: $CI_YML not found" >&2; exit 1; }

matches="$(sed -n 's/^[[:space:]]*WARRANT_PIN:[[:space:]]*//p' "$CI_YML")"
count="$(sed -n 's/^[[:space:]]*WARRANT_PIN:[[:space:]]*//p' "$CI_YML" | wc -l | tr -d ' ')"

if [ "$count" -ne 1 ]; then
  echo "ERR: $CI_YML has $count WARRANT_PIN: lines — exactly one is mandated." >&2
  if [ "$count" -gt 1 ]; then
    echo "ERR: duplicate WARRANT_PIN is a forbidden ci.yml state (which pin" >&2
    echo "     would CI mean?) — remove the extra line(s); this is NOT a" >&2
    echo "     network problem." >&2
  fi
  exit 1
fi

# Tolerate what real CI's YAML reader tolerates: strip a trailing comment,
# surrounding single/double quotes, and whitespace — then validate strictly.
pin="${matches%%#*}"
pin="$(printf '%s' "$pin" | tr -d '[:space:]')"
pin="${pin%\"}"; pin="${pin#\"}"
pin="${pin%\'}"; pin="${pin#\'}"

if ! printf '%s' "$pin" | grep -qxE '[0-9a-f]{40}'; then
  echo "ERR: WARRANT_PIN in $CI_YML is not a 40-hex commit id: '$pin'" >&2
  exit 1
fi

printf '%s\n' "$pin"
