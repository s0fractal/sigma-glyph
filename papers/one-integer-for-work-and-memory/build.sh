#!/bin/sh
# Build paper.pdf from paper.md, with citations resolved from references.bib.
# Recorded so the artifact deposited at a DOI can be rebuilt from the same source.
#   pandoc 3.10.2, tectonic 0.17.0
#
# WARNING: the committed paper.pdf IS the deposited artifact (md5
# f07e9c3a6301cf2be34771746d7e5c63, built at 7ecba6a) and paper.md has moved
# past it. Running this in the working tree overwrites it. To check rendering,
# copy this directory elsewhere and build there -- see README.md.
set -e
cd "$(dirname "$0")"
pandoc paper.md -o paper.pdf \
  --citeproc --pdf-engine=tectonic \
  -V geometry:margin=1in -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -M reference-section-title=References --toc
