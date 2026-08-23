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
| status | **draft prepared, not published** — publishing is the author's action |
| DOI | not yet assigned |
| contents | `report.pdf`, `results.json`, and a snapshot of the repository |
| build | [`build.sh`](build.sh) — pandoc 3.10.2, tectonic 0.17.0 |
| licence | CC BY 4.0, matching the paper |
| relation | supplement to the paper's concept DOI 10.5281/zenodo.22069650 |

`report.pdf` is a cover page followed by two documents reproduced **unedited**:
the preregistration as committed at `d3eea63`, before any reducer existed, and
the result with its three rounds of corrections intact. The cover explains why
both are printed and what the record does not claim.

Once the record is published, its DOI belongs here and in
`experiments/exp-004/RESULT.md`.
