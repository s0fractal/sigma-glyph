# ADR-008 rev 14 — item-0 final gate

Date: 2026-07-27  
Scope: R0/R1 document synchronization and dependency on the Warrant item-0 gate  
Verdict: **R0 EXECUTION ACCEPTED; REV 14 IS STILL INTERNALLY MIXED; WAIT FOR
WARRANT ITEM 0**

## Accepted

The executable R0 contract remains correct:

- it is a non-filing query;
- it uses raw settlement eligibility;
- it subtracts neither a citation nor supersede targets;
- an unauthorized foreign supersede does not change the result;
- the naïve effective derivation is isolated as a failing R1 research vector.

The main pseudocode at lines 70–86 now cleanly separates implemented R0 from
unresolved R1.

## Findings

### [P2] Two normative-looking summaries still restate the superseded LIVE-HEAD formula

The C1 summary at lines 117–121 and design criterion 9 at lines 156–158 still
say the runtime universe is:

```text
settlement_active_for(J) minus the current citation
```

That is neither current R0 (raw eligibility, no citation subtraction) nor the
unresolved R1 contract (authorized effective set from a checkpoint, minus the
bound citation WID). Replace both with the explicit two-mode split already used
at lines 70–86, or point to WRT-001 without paraphrasing it.

### [P2] “Remaining” still uses the obsolete pre-item-0 numbering

Lines 166–174 list “real single-context verifier” as item 1 and key-state/R1 as
item 2. WRT-001 now marks the generic verifier work as item 0 and makes
authorized lifecycle plus key-state the inseparable items 1–2. Synchronize the
list instead of preserving an older ordering under normative-looking
“Remaining”.

## Dependency

The Warrant final gate still reproduces strict-parser, genesis-totality, and
public-summary parity blockers. See:

`warrant/reviews/2026-07-codex-wrt001-item0-final-gate.md`.

After those local fixes and the two editorial replacements above, item 0 can
receive a clean DONE verdict and joint authorized-lifecycle + key-state + R1
design may begin.
