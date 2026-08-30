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

`paper.pdf` as committed **is** the deposited artifact, byte for byte: its MD5,
`f07e9c3a6301cf2be34771746d7e5c63`, is the one Zenodo publishes for the record's
`paper.pdf`. It was built from `paper.md` as that file stood at `7ecba6a`.

`paper.md` has since been rewritten past it. The two corrections the deposited
version carried as appended notes are now in the text itself — §7's reason for
the missing independent implementation, and the summary line that named two
arguments where the evaluator takes three — and the paper has gained the title,
the abstract framing, §3.6–§3.9 (three inputs, the receipt, admission, and where
the specification stands), V22 in the limitations, and a §6 re-measured at the
frozen v0.7.0 candidate. Its counts moved with the tree.

So a rebuild no longer reproduces the deposited PDF. That is the normal state of
a frozen deposit and not a defect — the commit is named above, and the artifact
stays here unchanged. **Do not overwrite `paper.pdf` with a rebuild.** `build.sh`
writes to that name, so build it somewhere else when checking the rendering; the
current source is deliberately not deposited, and a version worth depositing is a
new version under the same concept DOI, with its own archived commit, which is
the author's decision and not a build step.

`tools/paper_claims.py` recounts every number `paper.md` states about this tree,
and `--selftest` rewrites each of them in turn to prove the recount can fail.
Both run in `tools/test-all.sh` and in CI.
