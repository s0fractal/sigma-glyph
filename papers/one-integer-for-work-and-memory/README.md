# One Integer for Semantic Work and Materialization

Two versions are deposited under one concept DOI,
[10.5281/zenodo.22069650](https://doi.org/10.5281/zenodo.22069650), which
always resolves to the latest:

| | version DOI | label | source commit | date |
| --- | --- | --- | --- | --- |
| v2 (current) | [10.5281/zenodo.22646920](https://doi.org/10.5281/zenodo.22646920) | `0.7.0-paper2` | [`47cf57d`](https://github.com/s0fractal/sigma-glyph/tree/47cf57dd6ec2f671d5aaf521094420f97cf566d6) | 2026-09-07 |
| v1 | [10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651) | `0.6.7-paper1` | [`7ecba6a`](https://github.com/s0fractal/sigma-glyph/tree/7ecba6ab283c89111a76a3a1edeba57339b4443c) | 2026-08-23 |

Each deposit holds two files: `paper.pdf`, and a `git archive` of the
repository at the named commit — Lean proofs, three implementations,
specification texts and the review ledger. v2 is the paper as rewritten after
the 2026-08 reviews (Codex's implicit-store finding, Qwen's critique, the
full-system audit): the evaluator is a relation over term, budget *and* content
environment; the bound is semantic, not physical; a result hash does not carry
the exit. v1 said the first two wrongly in its summary; v2 §3.9 quotes what it
corrects. The title changed with the claim.

Deposited is not reviewed. A DOI is a permanent address and a frozen artifact;
it is not a venue, a peer review or an endorsement, and §7 of the paper says what
is still missing — chiefly an implementation of Book I by someone who has not
read this code.

| | |
| --- | --- |
| source | [`paper.md`](paper.md), bibliography in [`references.bib`](references.bib) |
| build | [`build.sh`](build.sh) — pandoc 3.10.2 with `--citeproc`, tectonic 0.17.0 |
| licence | CC BY 4.0, as recorded in the deposit |
| v2 manifest | [`DEPOSIT-v2-MANIFEST.md`](DEPOSIT-v2-MANIFEST.md) — digests, build recipe, post-publication verification |

**The v2 PDF is reproducible, and that is why its bytes are not tracked.**
`paper.md`, `references.bib` and `build.sh` on `master` are byte-identical to
`47cf57d`; with `SOURCE_DATE_EPOCH=1788134400` exported, `build.sh` produces the
deposited `paper.pdf` exactly (SHA-256 `8970a3af…c9565`, 197645 bytes) — checked
again on the day of publication. Without the epoch, tectonic stamps the build
time and the digest differs; `build.sh` prints which case it is in. `.gitignore`
excludes `papers/*/paper.pdf`; the committed artifact for v2 is the manifest.

**The v1 bytes are tracked because they are not reproducible.** v1 was built
from `paper.md` as it stood at `7ecba6a`, without a pinned epoch, so no rebuild
recovers it; the deposited files are kept under
[`v1-deposited/`](v1-deposited/) with names that cannot be mistaken for a build
output (`paper-v1-zenodo-22069651.pdf`, MD5 `f07e9c3a6301cf2be34771746d7e5c63`).

If `paper.md` is edited past `47cf57d`, a rebuild stops reproducing v2. That is
the normal state of a frozen deposit, not a defect: the commit is named above
and the bytes live at the DOI. A version worth depositing is a new version under
the same concept DOI with its own archived commit and its own manifest — the
author's decision, not a build step.

`tools/paper_claims.py` recounts every number `paper.md` states about this tree,
and `--selftest` rewrites each of them in turn to prove the recount can fail.
Both run in `tools/test-all.sh` and in CI.
