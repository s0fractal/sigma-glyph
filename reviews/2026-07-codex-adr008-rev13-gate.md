# ADR-008 rev 13 — independent gate

Date: 2026-07-27  
Scope: raw-eligibility R0, lifecycle wording, and synchronization with the
Warrant item-0 DONE candidate  
Verdict: **R0 MECHANICS ACCEPTED; DOCUMENT SYNC STILL REQUIRED; WAIT FOR THE
WARRANT ITEM-0 PARITY FIX**

## Accepted

The executable R0 corrections pass:

- no citation Warrant is filed;
- record count remains unchanged;
- `verify_query` explicitly uses raw settlement eligibility;
- an unauthorized foreign supersede no longer removes the cited assertion;
- both the normal and foreign-supersede fixtures return
  `pass; coherence=32767`;
- the naïve effective derivation remains only in the R1-anticipating research
  path, where its censorship failure is displayed honestly.

WRT-001 §6 now also correctly says authorized effective lifecycle is R1-only
and key-state-dependent. The previous normative censorship formula is removed.

The remaining Warrant blockers are recorded in:

`warrant/reviews/2026-07-codex-wrt001-item0-done-candidate-gate.md`.

## Findings

### [P2] ADR's main summaries still collapse R0 and unresolved R1 membership

The rev-13 changelog and probe distinguish the modes correctly, but older
normative-looking summaries still say:

```text
index := effective_active_for(J) minus current citation
```

or:

```text
settlement_active_for(J) minus current citation
```

See:

- `proposals/ADR-008-resonant-precedent.md:58-80`;
- `proposals/ADR-008-resonant-precedent.md:95-107`;
- `proposals/ADR-008-resonant-precedent.md:135-145`.

State the split explicitly everywhere:

```text
R0 query: raw_active_for(J), no citation to subtract
R1 stored citation: authorized_effective_active_for(J, checkpoint)
                    minus the bound citation WarrantID
```

The R1 expression remains unresolved until key-state/checkpoint design; it
must not be paraphrased back into raw `settlement_active`.

### [P2] The deferred numbering is still stale

ADR “Remaining” calls the real single-context verifier item 1, while WRT-001
calls the generic refactor item 0 and reserves items 1–2 for authorized
lifecycle plus key-state/R1. Synchronize the list after the final item-0 parity
patch lands.

### [P2] Historical changelog claims can be mistaken for current rules

The accumulated rev-9/rev-10 entries still state the old single LIVE-HEAD /
naïve-effective contracts without a clear “superseded by rev 13” marker. Keeping
history is valuable, but mark those clauses historical so a reader cannot lift
them as the current algorithm.

## Recommendation

Accept the raw-eligibility/non-filing R0 implementation. Fix the Warrant
short-circuit and pinned-genesis parity seams, then synchronize ADR's summary
formula and numbering. After that item 0 can receive a clean DONE gate and the
joint authorized-lifecycle + key-state + R1 specification may begin.
