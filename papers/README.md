# Papers

Two write-ups about this repository, moved here 2026-08-03 from a personal
working directory outside version control.

| | words | subject |
|---|---|---|
| [`one-integer-for-work-and-memory/`](one-integer-for-work-and-memory/) | 9 346 | the engine: a content-addressed combinator machine with a single mechanized bound over work *and* memory, and what it took to make the proof artifacts trustworthy |
| [`twenty-one-ways-past-a-proof-guard/`](twenty-one-ways-past-a-proof-guard/) | 8 100 | twenty-one ways the CI apparatus around the theorem prover was bypassed while CI stayed green |

Neither is published. There is no arXiv posting, no venue, no peer review, and
nothing here should be cited as though there were.

## Why they moved

Three reasons, in ascending order of how much they matter.

They were **unversioned** — no history, no backup, no way to see what changed or
when. Seventeen thousand words in a folder.

They **describe this repository**, and a description of a thing belongs beside
the thing rather than in a drawer where drift is invisible.

And they were **outside every gate**. They assert that `proof_guard.py` is 1326
lines, that the pin registry is 175 KB holding 39 statement and 155 definition
pins, that the Lean sources total 1304 lines, that the guard's test file is 981
lines, and that there are twenty-one bypasses.

On the day they moved, **every one of those numbers was correct**. That is
exactly why the move needed a check rather than just a `git mv`: correct-by-luck
and correct-by-construction are indistinguishable until the file changes, and the
argument these papers make is that the difference is the only thing that matters.
Importing 17 000 words of unenforced claims into a repository whose discipline is
enforced claims would have been the defect the second paper is about, committed
in the act of publishing the paper about it.

So `tools/paper_claims.py` recounts them, runs in `tools/test-all.sh`, and reads
the expected value **out of the paper** rather than carrying its own copy — a
checker holding the answer only proves its two copies agree. Verified to go red:
appending one line to `proof_guard.py` fails it.

It also prints what it does **not** check, with reasons. A checker that quietly
covers half its subject reports a green worth less than it looks.

## Not anchored

These are not normative and are not listed in `spec/ANCHORS.txt`. Editing them is
an ordinary commit, not a release act — unlike the Books, where a byte change
moves an anchor and adoption is a threshold warrant.

## Standing

Written by a language model working as maintainer on this stack. Every number in
them is measured from committed refs rather than estimated, and the limitations
sections were written to be sharp rather than survivable. What none of that
supplies is independent review: this project has zero external implementers and
has never been through an independent gate, and a paper about the fragility of
one's own verification apparatus, reviewed only by its author, inherits that
problem in full. The second paper says so about itself.
