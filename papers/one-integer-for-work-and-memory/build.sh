#!/bin/sh
# Build paper.pdf from paper.md, with citations resolved from references.bib.
# Recorded so the artifact deposited at a DOI can be rebuilt from the same source.
#   pandoc 3.10.2, tectonic 0.17.0
#
# paper.pdf is NOT committed: .gitignore excludes `papers/*/paper.pdf`. The
# deposited v1 artifact (md5 f07e9c3a6301cf2be34771746d7e5c63, built at 7ecba6a)
# lives only at the DOI, and this script's earlier warning described it as the
# committed file, which no checkout has ever contained.
#
# REPRODUCIBILITY: byte-identical output requires SOURCE_DATE_EPOCH to be set.
# Without it, tectonic stamps the build time and two builds of identical bytes
# differ. Verified: with SOURCE_DATE_EPOCH=1788134400 two clean checkouts of the
# same commit both produce 16f5da1f...; without it, a third produced a different
# digest. The deposit manifest records the exact value used.
set -e
if [ -n "${SOURCE_DATE_EPOCH:-}" ]; then
  echo "build.sh: SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH (reproducible)" >&2
else
  echo "build.sh: SOURCE_DATE_EPOCH unset -- output will NOT be byte-reproducible" >&2
fi
cd "$(dirname "$0")"
pandoc paper.md -o paper.pdf \
  --citeproc --pdf-engine=tectonic \
  -V geometry:margin=1in -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -M reference-section-title=References --toc
