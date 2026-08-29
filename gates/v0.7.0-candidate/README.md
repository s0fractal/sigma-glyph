# The v0.7.0 candidate, and what has been done to it

Each round is self-contained: the bytes it froze, the anchor set built from them,
the exact prompt every reviewer saw, and each reviewer's raw response with its
model id, prompt digest and timestamps. Nothing in a round directory is edited
after the round; a round whose findings are answered is superseded, not amended.

| Round | Bytes | Verdicts |
| --- | --- | --- |
| [round 1](round-1/) | anchor set `0bac2605…` | REJECT / REJECT / REJECT |
| [round 2](round-2/) | anchor set `79bf939a…` | ADOPT / REJECT / NO VERDICT |
| [round 3](round-3/) | anchor set `4c93717a…` | ADOPT / NO VERDICT / NO VERDICT — **incomplete** |

Reviewers, in that column order: `google/gemini-3.1-pro-preview`,
`deepseek/deepseek-v4-pro-0813`, `moonshotai/kimi-k3`. The third has since been
changed to `moonshotai/kimi-k2.6` for future rounds: k3 usually returns nothing,
and a reviewer that returns nothing costs the whole round rather than a third of
it. The rounds recorded here name the model that actually answered them, which is
the point of recording it.

Round 1's central finding was one the candidate had introduced: §3.6 was added
saying an out-of-domain budget MUST be refused, and §3.4 was left saying it MAY
be clamped. Three families found it independently and two produced the same
counterexample. That is what a gate is for, and it is the reason a round's
verdicts do not carry across a byte change — round 1's REJECTs are a true record
of a revision nobody is proposing any more.

Dispositions for every round-1 finding, including the one left unresolved, are in
[`proposals/ADR-010`](../../proposals/ADR-010-three-inputs-and-a-receipt.md).

Run a round with:

    python3 tools/candidate_gate.py gates/v0.7.0-candidate/round-N

It verifies every frozen digest before sending anything, gives each reviewer a
fresh context and the same prompt, shows no reviewer another's answer, and writes
NO VERDICT with a reason rather than leaving a gap when one does not answer.

## What each round found, in one line

Round 1's central finding and round 2's were both defects the candidate had
introduced in the immediately preceding step — §3.6 added without amending §3.4,
then §3.5's repair contradicting itself. Neither was reachable by any test in
this repository, and a green CI accompanied both.

Round 3 did not complete: the OpenRouter account ran out of credit after the
first reviewer, and the two families whose round-2 findings produced round 3's
edits never saw them. One ADOPT is not a gate, and it is not recorded as one.

Round 2's NO VERDICT was a truncated reply, not a silent reviewer. It is recorded
as NO VERDICT with the reason, and the reply budget is now an argument that every
review records.

**Independence is partial from round 2 onward.** The prompt carries the
candidate's ADR and the ADR carries earlier dispositions, so a later round can
inherit an earlier round's argument — one family reversed a P0 that way. Count
independent judgments, not verdicts. `ADR-010` states this at length.

## One defect in this tooling, found while cleaning it

`build_prompt` diffed the Books between the adopted tag and **`HEAD`**, not the
working tree. The freeze verifies the files on disk, so the prompt depended on
which commit happened to be checked out rather than on the bytes being gated:
re-running the tool after any later commit produced a different prompt for the
same frozen bytes, and wrote it over the record of what that round's reviewers
had actually seen. It diffs the working tree now, and `prompt.txt` is refused
rather than overwritten when it already records something different.

The evidence of a round is what its reviewers were shown. A tool that can quietly
replace that is the same defect class as everything else in this repository's
history: a check whose subject can be changed by the thing being checked.
