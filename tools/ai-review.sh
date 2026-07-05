#!/bin/sh
# ai-review.sh — run an external AI reviewer over a DISPOSABLE clone of this repo.
#
#   tools/ai-review.sh agy   2026-07-gemini-adr-gate.md  "focus text..."
#   tools/ai-review.sh codex 2026-07-codex-foo.md        "focus text..."
#
# The reviewer works in a throwaway clone (never the live checkout); the ONLY
# artifact copied back is reviews/<outfile>. The maintainer then verifies the
# review's claims independently and adjudicates (response doc + warrant).
# Model override: AGY_MODEL env (default "Gemini 3.1 Pro (High)").
set -eu
CLI=${1:?usage: ai-review.sh <agy|codex> <outfile.md> [focus...]}
OUT=${2:?missing output review filename}
shift 2
FOCUS=${*:-"Full adversarial spec review."}
REPO=$(git rev-parse --show-toplevel)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
git clone -q "$REPO" "$T/repo"
cd "$T/repo"

PROMPT="You are an independent adversarial reviewer of this repository.

PROTOCOL (binding): read reviews/README.md first. Run first, read second:
  python3 impl/sigma_glyph.py                       # must print ALL PASS
  python3 tests/spec_conformance/run_reference.py   # must print ALL PASS
  python3 tools/verify_anchors.py                   # must verify
Include a verified-vectors statement with the actual outputs you saw.

FOCUS: $FOCUS

RULES:
- Severity ladder P0/P1/P2/P3 per reviews/README.md. Settled points are listed
  there; re-litigation requires genuinely new evidence.
- Form your own findings from the primary texts BEFORE reading prior reviews in
  reviews/; then add a section stating where you agree, disagree, and what is
  new relative to them.
- Every claim that can be checked by running code: check it by running code,
  and show the command.
- Give concrete text proposals for every P1/P2.
- Write the COMPLETE review to reviews/$OUT and nothing else: do not modify any
  other file, do not commit, do not push.
"

case "$CLI" in
  agy)
    agy --add-dir . --dangerously-skip-permissions \
        --model "${AGY_MODEL:-Gemini 3.1 Pro (High)}" \
        --print-timeout 45m -p "$PROMPT"
    ;;
  codex)
    codex exec --sandbox workspace-write "$PROMPT"
    ;;
  *)
    echo "unknown reviewer CLI: $CLI" >&2; exit 2
    ;;
esac

test -s "reviews/$OUT" || { echo "reviewer did not write reviews/$OUT" >&2; exit 1; }
cp "reviews/$OUT" "$REPO/reviews/$OUT"
echo "review delivered: reviews/$OUT"
