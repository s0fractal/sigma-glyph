# One Integer for Work and Memory

Published: **Zenodo DOI [10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651)**,
archived at commit [`7ecba6a`](https://github.com/s0fractal/sigma-glyph/tree/7ecba6ab283c89111a76a3a1edeba57339b4443c).
The concept DOI [10.5281/zenodo.22069650](https://doi.org/10.5281/zenodo.22069650) always resolves to
the latest version.

The deposit holds two files: `paper.pdf`, and a snapshot of this repository at
that commit — Lean proofs, three implementations, specification texts and the
review ledger. On that commit `lake env lean SizeBound.lean`,
`python3 proofs/bridge_check.py` and `python3 tests/spec_conformance/run_reference.py`
were all green, and `proofs/` contained no `sorry`.

Deposited is not reviewed. A DOI is a permanent address and a frozen artifact; it
is not a venue, a peer review or an endorsement, and §7 of the paper says what is
still missing — chiefly an implementation of Book I by someone who has not read
this code.

| | |
| --- | --- |
| source | [`paper.md`](paper.md), bibliography in [`references.bib`](references.bib) |
| build | [`build.sh`](build.sh) — pandoc 3.10.2 with `--citeproc`, tectonic 0.17.0 |
| licence | CC BY 4.0, as recorded in the deposit |
