# The v0.7.0 candidate, and what has been done to it

Each round is self-contained: the bytes it froze, the anchor set built from them,
the exact prompt every reviewer saw, and each reviewer's raw response with its
model id, prompt digest and timestamps. Nothing in a round directory is edited
after the round; a round whose findings are answered is superseded, not amended.

| Round | Bytes | Verdicts |
| --- | --- | --- |
| [round 1](round-1/) | anchor set `0bac2605…` | REJECT / REJECT / REJECT — Gemini 3.1 Pro, DeepSeek v4 Pro, Kimi k3 |
| [round 2](round-2/) | anchor set `79bf939a…` | pending |

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
