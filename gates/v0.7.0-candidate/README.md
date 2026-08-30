# The v0.7.0 candidate, and what has been done to it

Each round is self-contained: the bytes it froze, the anchor set built from them,
the exact prompt every reviewer saw, and each reviewer's raw response with its
model id, prompt digest and timestamps. Nothing in a round directory is edited
after the round; a round whose findings are answered is superseded, not amended.

| Round | Bytes | Verdicts |
| --- | --- | --- |
| [round 1](round-1/) | anchor set `0bac2605…` | REJECT / REJECT / REJECT |
| [round 2](round-2/) | anchor set `79bf939a…` | ADOPT / REJECT / NO VERDICT |
| [round 3](round-3/) | anchor set `4c93717a…` | ADOPT / REJECT / NO VERDICT — completed on the third delivery attempt |
| [round 4](round-4/) | anchor set `91b4182c…` | ADOPT / ADOPT-WITH-AMENDMENTS / ADOPT — no P0 from any family |
| [round 5](round-5/) | anchor set `edc0ede5…` | REJECT / NO VERDICT / REJECT |
| [round 6](round-6/) | anchor set `c826eaf5…` | ADOPT / NO VERDICT / REJECT — **final multifamily gate**; see [AMENDMENT.md](round-6/AMENDMENT.md) |

Reviewers, in that column order: Google, DeepSeek, and a third family. The third
was `moonshotai/kimi-k3` in rounds 1–3 and `moonshotai/kimi-k2.6` for round 3's
last two attempts; neither ever delivered a review. From round 4 it is
`qwen/qwen3-235b-a22b-2507`. Each record names the model that actually answered
it, which is the point of recording it — and the change means round 4's three
families are not round 1's three families, which `round-4/FREEZE.md` states
rather than absorbs.

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

Round 3 took three delivery attempts. Attempt 1 was `HTTP 402` — the account was
out of credit. Attempt 2, after a top-up, returned reasoning traces and no reply
from both reviewers at a 40 000-token budget. Attempt 3 at 24 000 got DeepSeek's
review; Moonshot never produced one under either model tried. Every attempt is
filed beside the last, never over it, and the retries were delivered from the
**recorded** prompt file rather than a rebuilt one, so all three families were
asked the same question.

Round 4 was the first with no P0 from anyone — DeepSeek downgraded its own
standing GOV-anchors P0 on its own reasoning. Its remaining P1 was that the
Books declare a JSON artifact normative without defining its shape; checking it
found the instance, which was worse than the argument: §3.4 enumerates three
exits and the normative suite carried a fourth value for the field §7 called
"the canonical exit". Round 5 splits the two levels into `expected.exit` and
`expected.outcome`, anchors a closed schema per suite, and makes the runner check
four observables instead of two.

Round 3's REJECT rested on GOV-anchors, which the owner has since dispositioned.
What moved the bytes was an observation beside it: §7's test vectors quantified
over every budget `n` while §3.6 — added by this same candidate — refuses a
budget outside `uint32` before evaluation. The third instance of one pattern: a
clause added, its neighbour not revisited.

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

## Findings refuted by the frozen bytes

Kept, not deleted. A reviewer's mistake about the subject is evidence about the
**gate**, and deleting it would leave the gate looking better than it is.

| Round | Family | Finding | Status |
| --- | --- | --- | --- |
| 5 | qwen | §3.4 still permits clamping an out-of-domain `atp`, contradicting §3.6 | `REFUTED_BY_FROZEN_BYTES` |
| 6 | qwen | `wave(APPLY(K,I))` yields `Ph=32768`, diverging from `wave(FALSE)` | `REFUTED_BY_FROZEN_BYTES` — that is the pre-fix behaviour; both engines and the suite return 49152 |

The quoted string occurs in the round-5 prompt exactly once, on line 36, prefixed
`-` — a deletion. The frozen bytes contain zero occurrences in either language.
The reviewer read a removed diff line as current text.

That is a defect in how the subject was presented, not in the reviewer: a raw
unified diff invites reading `-` lines as the specification. From round 6 the
prompt carries the current normative bytes and no raw diff as the source of
truth, and asks for the verdict at the head of the response as well as the tail
so that a reviewer which reasons past its budget still delivers one.

## What the final gate produced, named honestly

Round 6 was **not** a clean three-family pass, and calling it one would be the
kind of claim this directory exists to prevent. It produced **one adoption, one
delivery failure, one refuted rejection, and one subsequently confirmed narrower
P1** — the last found by auditing the refuted rejection rather than by the
ensemble.

The P1 was repaired without a Round 7, by explicit owner disposition:
[`round-6/AMENDMENT.md`](round-6/AMENDMENT.md) states what changed, why another
round of this ensemble would produce no new independent signal, and the narrow
limit of that exception. Adoption remains a threshold warrant filed by the
roster; no model verdict substitutes for it.

`REVIEW-POLICY.md` governs when a multifamily gate runs at all from here.
