#!/bin/sh
# Build report.pdf: the cover, then the preregistration and the result verbatim.
# Recorded so the artifact deposited at a DOI can be rebuilt from the same source.
#   pandoc 3.10.2, tectonic 0.17.0
#
# The two source files are concatenated rather than rewritten. Editing either to
# read better in print would defeat what this document is for.
#
# FONTS. Latin Modern, which tectonic uses by default, has no glyph for the very
# characters this report is about: the first build dropped every `<=`, `>=`, and
# every Greek agent name, so the central formula printed without its inequality
# and nothing said so. Palatino and Menlo cover them. Both are macOS system
# fonts; on Linux substitute URW Palladio L and DejaVu Sans Mono, which have the
# same coverage.
#
# The check below is the point: a missing glyph makes this script fail rather
# than quietly ship a PDF whose formulas are wrong.
set -e
cd "$(dirname "$0")"

printf '\n\\newpage\n\n# Part II — The result\n\n*Written after the measurement, corrected three times in review. Reproduced here unedited.*\n\n' > divider.md

pandoc cover.md \
       ../../EXP-004-parallel-bound-preregistration.md \
       divider.md \
       ../RESULT.md \
       -o report.pdf \
  --pdf-engine=tectonic \
  -V mainfont="Palatino" -V monofont="Menlo" \
  -V geometry:margin=1in -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  --toc 2> build.log

rm -f divider.md
if grep -q "could not represent" build.log; then
  echo "REFUSED: the build dropped characters this report is about:" >&2
  grep "could not represent" build.log | sort -u >&2
  rm -f report.pdf
  exit 1
fi
rm -f build.log
echo "built report.pdf"
