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

`paper.pdf` as committed **is** the deposited artifact, built from `paper.md` as
it stood at `7ecba6a`. `paper.md` has since gained two marked corrections: §7's
reason for the missing independent implementation was wrong, and the summary line
named two arguments where the evaluator takes three — the store is an input, and
availability is inside the semantics. Its counts of Lean lines and pin-registry
entries have also moved, because the store-monotonicity theorems that answer that
correction are new code in the tree the paper counts.
A rebuild therefore no longer reproduces the deposited PDF, which is the normal
state of a frozen deposit and not a defect — the commit is named above. What must
not happen is rebuilding the PDF and committing it as though it carried the DOI.
A correction worth depositing is a new version under the same concept DOI, with
its own archived commit, and that is the author's decision.
