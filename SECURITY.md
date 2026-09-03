# Security

## Reporting a vulnerability

Use GitHub's private reporting: **Security → Report a vulnerability** on
<https://github.com/s0fractal/sigma-glyph>. That opens a channel visible only to the
maintainers, which is the right place for anything you would not want in a public
issue.

If that is unavailable to you, open a public issue saying only that you have a
security report and asking for a channel. Do not put the details in it.

## What you can expect, honestly

This project is maintained by one person, with a model actor holding a bounded,
revocable delegation for day-to-day work. Accountability sits with the person;
the model is a delegate, not a maintainer of record (see
`SECURITY-ASSUMPTIONS.md` SA-6). There is no security team, no on-call rotation,
and no paid triage.

- **Acknowledgement:** best effort, usually within a few days. If a week passes
  with no reply, assume the message was missed and say so publicly without
  details — that is not a breach of coordination, it is the only remedy you have.
- **Fix timeline:** none is promised, because none could be kept. What is
  promised is that a confirmed report gets a reproduction, a regression test, and
  a commit that says plainly what was wrong.
- **Credit:** named in the fixing commit unless you ask otherwise.
- **Embargo:** as long as you need to coordinate, and no longer. If a fix ships
  before you are ready, the commit will say the reporter asked for a delay.

No bounty. No CVE-issuing authority here; if a report warrants a CVE, request one
through GitHub's advisory flow, which this repository supports.

## What is in scope

The things this project asks you to trust:

- **Two nodes disagreeing on a result hash.** `eval(term_hash, atp)` is the whole
  promise; any input on which two conforming implementations differ is the
  highest-severity finding here.
- **Non-determinism, non-totality, or an escaped budget.** An input that hangs,
  that consumes more than `atp` allows, or that violates
  `materialized size − 1 ≤ spent`.
- **The wave layer deciding identity.** Book II is a view over identity and never
  part of it. Anything that lets a wave, a coordinate or an annotation change a
  NodeHash or a verification outcome breaks the invariant the whole stack rests
  on, and is a P0 regardless of how narrow it looks.
- **Canonical bytes.** Two distinct byte sequences accepted as the same object, or
  a canonical object rejected; non-canonical blobs admitted where the text
  requires rejection.
- **Governance (GOV-anchors).** A release adopted without its threshold, a roster
  member removed unilaterally, a jurisdiction deadlocked with no recovery, or an
  anchor chain that accepts a forged ancestor.
- **The Lean chain.** A theorem whose statement does not mean what the prose says
  it means, or a bridge that compares the model against something other than the
  oracle.

## What is out of scope

Not because it does not matter, but because it is a **stated boundary of the
threat model** rather than a defect. The boundary is defined in one place —
[SECURITY-ASSUMPTIONS.md](SECURITY-ASSUMPTIONS.md) — as ten scoped assumptions
(`SA-1` … `SA-10`) and seven explicit non-goals (`NG-1` … `NG-7`), each with its
reasoning. That document is where they live; this list points at the ones a
reporter hits most often:

- **`native_decide` is in the trusted base** for part of the Lean chain, which
  puts the compiler there too. `C1Compiler.lean` does not use it. (SA-1)
- **Warrant verification is an external machine boundary.** A source-only
  checkout needs a pinned Warrant checkout or binary; `tools/warrant_gate.py`
  fails closed rather than re-deriving Warrant semantics locally. (SA-3)
- **Book III accepts a JCS-equivalent non-canonical assertion blob**; the v0.6.6
  fix narrowed this to the governance verifier only. Deferred and stated. (SA-4)
- **LORE.md is non-normative.** Disagreeing with the naming or the cosmology is
  welcome and is not a specification defect. (NG-7)
- Local resource faults are not canonical failures — that distinction is
  specified, not a bug (see Book I on `DISSONANCE` versus `ResourceFault`). (NG-6)
- **Governance declines to decide some things on purpose**: it will not pick a
  winner between rival adoptions (the chain freezes), will not prevent a fork,
  and will not recover a jurisdiction that has deadlocked below quorum.
  (NG-1, NG-3, NG-4)

A report showing that any of these is *worse than stated* is in scope and is the
most valuable thing this project receives; one restating it is not.

## Severity, as this project ranks it

The ladder used in `reviews/` and in the gate policy:

- **P0** — two conforming nodes can disagree on a result hash; or the wave layer
  affects identity; or something forged reads as verified.
- **P1** — the specification is silent where an implementer must guess.
- **P2** — clarity, structure, misleading output.
- **P3** — roadmap.

## A finding is a reproduction

Not a rule for you, an offer: a report that runs is acted on immediately, and a
report that does not has to be re-derived before anything can happen. If you can
send a script that exits non-zero on the defect and zero once it is fixed, it
becomes a permanent regression test with your name on it.

Every fix in this repository's history carries a negative control — the fix is
removed and the attack is shown to come back — so a reproduction is what the
process is built to consume.

## Verify anything first

```bash
tools/test-all.sh          # the full matrix; a skipped surface exits 2, not ALL GREEN
```

If a document and a command disagree, the command is right. Several reports
against this project have been artefacts of reading a feature branch, an archived
evidence blob, or truncated output rather than the thing itself; `MAP.md` says
which ref holds what, `reviews/README.md` lists settled points, and
`SECURITY-ASSUMPTIONS.md` states the known boundaries so you do not spend a pass
rediscovering them.
