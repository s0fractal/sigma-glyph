# ADR-004: LITERAL blob validation — inside or outside `eval()`?

**Status:** PROPOSED (2026-07-06) — needs the standard review gate before any Book I change
**Origin:** Codex post-release audit of v0.5.0 (P1), 2026-07. New evidence over the DeepSeek 2026-07 settlement: the shipped artifact cannot express the settled behavior, and Book I §1.1 contradicts itself across two adjacent paragraphs.

## Problem

Book I §1.1 currently states both:

1. *"LITERAL — інертний commitment… Для редукції blob не потрібен ніколи…
   Отримання та валідація blob — контракт сховища **поза цією Книгою**."*
2. *"Нормативна поведінка `resolve(h)` для LITERAL: fetch blob, валідувати
   `SHA-256(blob) == atom`, і якщо валідація невдала — матеріалізувати
   Canonical Invalid Object… зовнішньо спостережувана поведінка `eval()`
   MUST бути ідентичною до on-demand validation."*

These are contradictory scopings. The v0.5 reference oracle implements (1):
`Store` is a node-byte CAS with no blob channel; a LITERAL forces to normal
form in 1 ATP with no blob present (verified:
`eval(LITERAL(sha("dummy blob")))` → `normal_form`, spent 1). `EV-LIT-FORCE`
pins exactly this. Under Book I §7 supremacy (oracle/vectors win over prose),
paragraph (2) is currently a dead letter — but it is also the text that
encoded the DeepSeek 2026-07 settled point. Two implementers reading
different paragraphs build different machines: a P1 consensus-surface gap.

## Option 1 — canonize blob validation inside `eval()` (Codex's preference)

Add a BlobStore to the reference oracle and the vector format; pin at least
`EV-LIT-BLOB-OK`, `EV-LIT-BLOB-MISMATCH` (→ Canonical Invalid Object),
`EV-LIT-BLOB-MISSING` (→ pick Unresolved Reference or Invalid Object).
Preserves the DeepSeek settlement as written. Costs: `vectors.json` format
change → anchor churn → release; `eval()` results become a function of blob
availability, adding a second Unresolved-like channel for data that
reduction never demands.

## Option 2 — scope blob validation outside `eval()` (maintainer leaning)

Delete/rewrite §1.1 paragraph (2): Book I validates only SigmaNodeV2 node
bytes; a LITERAL is a normal form whose `atom` commits to external data, and
absence or mismatch of that data MUST NOT change the Book I result hash.
Blob APIs MAY report storage faults, non-canonically.

Arguments:

- A conforming blob store **cannot contain** a mismatched blob under its
  atom: the key *is* `SHA-256(blob)` by construction. Mismatch is local
  corruption, and the settled point "canonical failures ≠ local resource
  faults; the latter MUST NOT serialize as DISSONANCE" already forbids
  canonizing local corruption.
- The v0.5 lazy settlement says laziness exempts what reduction never
  demands — and reduction never demands the blob (§1.1 para 1, §3.2).
  Option 1 would make `eval()` demand data the machine provably never uses.
- Zero anchor churn on suite semantics; the oracle is already correct.

Cost: the DeepSeek settled point must be reworded (superseded-in-scope):
on-demand validation remains the normative *storage* contract at blob
retrieval, but it is not part of `eval()`. Settlement rule permits this:
the new evidence is the artifact itself.

## Decision criteria for the gate

The reviewer question to answer: is there any consensus scenario where two
honest nodes with identical node-CAS must agree on a *blob-dependent*
outcome? If yes, name it — Option 1 wins. If no such scenario exists,
Option 2 removes a dead normative branch instead of implementing one.

## Interim state (until adjudicated)

Book I §7 supremacy applies: the oracle and `EV-LIT-FORCE` are the law;
implementers MUST NOT make `eval()` results depend on blob material in
v0.5.x. This ADR exists to make the prose match whichever way the gate
decides.
