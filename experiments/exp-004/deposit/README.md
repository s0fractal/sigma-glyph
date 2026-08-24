# EXP-004 deposit

A Zenodo record for the interaction-net experiment, kept separate from the
paper's record ([10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651))
rather than folded into a second version of it.

The reason is the distinction the preregistration exists to protect. The paper
proves a theorem about a sequential machine; this experiment *measures* what
happens in a setting the paper does not claim, and part of what it found limits
the paper's discipline rather than extending it. Printing them as one document
would blur which sentences were proved and which were observed.

| | |
| --- | --- |
| status | published 2026-08-24 by the author |
| DOI | [10.5281/zenodo.22073568](https://doi.org/10.5281/zenodo.22073568) |
| concept DOI | [10.5281/zenodo.22073567](https://doi.org/10.5281/zenodo.22073567) — always the latest version |
| archived commit | [`3b1dcab`](https://github.com/s0fractal/sigma-glyph/tree/3b1dcab18e28088edf1ab8f9f0881fba6b655dc6) |
| contents | `report.pdf`, `results.json`, and a snapshot of the repository |
| build | [`build.sh`](build.sh) — pandoc 3.10.2, tectonic 0.17.0 |
| licence | CC BY 4.0, matching the paper |
| relation | supplement to the paper's concept DOI 10.5281/zenodo.22069650 |

`report.pdf` is a cover page followed by two documents reproduced **unedited**:
the preregistration as committed at `d3eea63`, before any reducer existed, and
the result with its three rounds of corrections intact. The cover explains why
both are printed and what the record does not claim.

## The committed PDF and the sources will drift, on purpose

`report.pdf` as committed **is** the deposited artifact, built from the sources as
they stood at `3b1dcab`. Recording the DOI in `RESULT.md` changed one of those
sources, so `build.sh` now produces a document that differs from the deposited one
by exactly that line — and will differ by more if the result is ever corrected
again.

That is the normal state and not a defect: a deposit is frozen at a commit, and
the commit is named above. What must not happen is rebuilding `report.pdf` and
committing the result as though it were what carries the DOI. If the result
changes enough to be worth depositing again, that is a new version of the record,
with its own version DOI under the same concept DOI, and its own archived commit.
