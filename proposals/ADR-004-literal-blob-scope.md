# ADR-004: LITERAL blob validation — inside or outside `eval()`?

**Status:** REVIEW GATE CLOSED for **Option 2** (2026-07-07, 4/≥3, zero dissent) — awaiting adoption release (Book I §1.1 prose rewrite + EV-LIT-FORCE note; oracle already conforms)
**Gate reviews:** 4 — every review answers the decision criterion in the negative and verdicts Option 2. Kimi k2.6 and Gemini 3.1 Pro below; Codex (2026-07-07) **conceded its own audit-time Option 1 preference** on the merits ("historical continuity cannot justify making a canonical result depend on blob state absent from node-CAS") and contributed the no-blob-vectors rule; DeepSeek v4 Pro (2026-07-07) supplied the textual base for the §1.1 rewrite (keep paragraph 1, delete paragraph 2) and confirmed no new vector is needed.
- Kimi k2.6 (2026-07-07): `eval()` is a pure function over the node-CAS transitive closure; the blob is never in that closure, so identical node-CAS can never force agreement on a blob-dependent outcome, and Option 1 would let blob-CAS state (possession/absence/corruption) split canonical results between honest nodes — a P0-class divergence surface. (reviews/2026-07-kimi-v0.5.0-audit.md §1)
- Gemini 3.1 Pro (2026-07-07): concurs — Option 1 "bridges off-chain state into the deterministic eval() pure function"; explicitly rejects Codex's Option 1 as prioritizing legacy prose over content-addressed determinism. Contributes the candidate §1.1 replacement text (blob absence/corruption is a local storage event, MUST NOT change `eval()` results or generate DISSONANCE). (reviews/2026-07-gemini-adr45-gate.md §1)
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
