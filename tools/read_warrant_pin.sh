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
# real CI reads fine (trailing ` # comment`, surrounding quotes), validates the
# single resulting value strictly, and prints it. Any violation is a hard
# error naming the actual condition — never a skip.
#
# Three further holes, found by a second fresh-context review (2026-07):
#
#   F9  a DUPLICATE pin passed when ci.yml has no final newline: `count` came
#       from `sed | wc -l`, which counts NEWLINES, so N pin lines counted as
#       N−1 and a duplicate read as "exactly one". `grep -c` counts an
#       unterminated last line, so the count is now the number of lines.
#   F10 same root cause the other way: a single VALID pin with no final
#       newline reported "has 0 WARRANT_PIN: lines" and hard-failed the whole
#       matrix with a wrong diagnosis.
#   F11 `tr -d '[:space:]'` deleted INTERNAL whitespace too, so
#       `39724276887 30e114507…` spliced into an accepted 40-hex value, and
#       `${matches%%#*}` truncated at a `#` with no preceding space — which
#       YAML keeps IN the value. Either way the local matrix would validate a
#       different commit than CI resolves. Only leading/trailing whitespace is
#       stripped now, and an inline comment must be preceded by whitespace.
#
# Usage: tools/read_warrant_pin.sh [path/to/ci.yml]
set -euo pipefail

CI_YML="${1:-.github/workflows/ci.yml}"
[ -f "$CI_YML" ] || { echo "ERR: $CI_YML not found" >&2; exit 1; }

matches="$(sed -n 's/^[[:space:]]*WARRANT_PIN:[[:space:]]*//p' "$CI_YML")"
count="$(grep -cE '^[[:space:]]*WARRANT_PIN:' "$CI_YML" || true)"

if [ "$count" -ne 1 ]; then
  echo "ERR: $CI_YML has $count WARRANT_PIN: lines — exactly one is mandated." >&2
  if [ "$count" -gt 1 ]; then
    echo "ERR: duplicate WARRANT_PIN is a forbidden ci.yml state (which pin" >&2
    echo "     would CI mean?) — remove the extra line(s); this is NOT a" >&2
    echo "     network problem." >&2
  fi
  exit 1
fi

# Tolerate exactly what real CI's YAML reader tolerates and no more: an inline
# comment only when whitespace precedes the `#` (otherwise the `#` is part of
# the value), surrounding single/double quotes, and LEADING/TRAILING whitespace
# only — internal whitespace must survive so that a spliced value fails the
# strict validation below instead of being accepted as a pin.
pin="$(printf '%s' "$matches" \
  | sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
pin="${pin%\"}"; pin="${pin#\"}"
pin="${pin%\'}"; pin="${pin#\'}"
pin="$(printf '%s' "$pin" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"

if ! printf '%s' "$pin" | grep -qxE '[0-9a-f]{40}'; then
  echo "ERR: WARRANT_PIN in $CI_YML is not a 40-hex commit id: '$pin'" >&2
  exit 1
fi

printf '%s\n' "$pin"
