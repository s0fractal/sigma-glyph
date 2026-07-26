# ADR-008 rev 12 — independent gate

Date: 2026-07-26  
Scope: ADR-008 rev 12, the revised non-filing R0 probe, and WRT-001 §6  
Verdict: **NON-FILING R0 IS REAL, BUT THE EFFECTIVE-SET ROLLBACK IS NOT
COMPLETE; DO NOT START R1**

The previous fake-R0 finding is closed: `build(no_file_cw=True)` files no
citation Warrant, `CW is None`, and the record count remains `4/4` across
`verify_query`. This is a materially better separation between a query and a
stored R1 citation.

The Warrant item-0 blockers are separately recorded in:

`warrant/reviews/2026-07-codex-wrt001-item0-recheck-2.md`.

## Findings

### [P1] The executable R0 still uses the rejected censorship derivation

`verify_query` delegates to `verify_citation(..., cw_wid=None)`, which still
does:

```python
eff = effective_active(sctx)
index = {w for w in eff ...}
```

`effective_active` is the naïve “active minus every active supersede target”
candidate. A foreign self-signed actor can therefore remove another actor's
assertion from the supposedly genuine R0 result. Reproduced:

```text
non-filing R0, normal store:
  pass

non-filing R0, foreign actor supersedes cited assertion:
  unverified: cited assertion inactive/out of snapshot
```

The probe describes the naïve derivation as only an explicitly failing research
vector, but it remains the execution path for the happy R0 query itself.

If authorized effective lifecycle is truly R1-only/unresolved, R0 must not
silently use it. Either:

- define R0 explicitly over raw settlement eligibility, accepting that it is a
  non-authoritative research view with historical/superseded records; or
- defer the full precedent join until R1 and keep R0 to the coherence/query
  kernel that does not claim an authorized effective set.

Add a non-filing foreign-supersede vector and assert the chosen semantics.

### [P1] WRT-001 §6 still normatively mandates the censorship primitive

ADR rev 12 says the main algorithm no longer contains the insecure formula, but
WRT-001—the stated normative home—still says:

```text
The runtime MUST derive:
active_records minus every record targeted by an active supersede
```

See `warrant/proposals/WRT-001-wave-v1-runtime.md:95-106`.

That directly contradicts WRT deferred items 1–2, which correctly say authorized
effective lifecycle is unresolved and inseparable from key-state. It also
contradicts ADR rev 12's claim that the formula is no longer normative.

Replace §6 with the unresolved
`authorized_effective_active_for(J, checkpoint)` contract for R1. Put the naïve
formula only in a non-normative rejected-candidate note.

### [P2] ADR rev 12 still restates the old LIVE-HEAD contract in several normative summaries

Although the main algorithm now mentions the unresolved authorized set, the C1
summary and design criterion 9 still say the universe is
`settlement_active_for(J) minus current citation`:

- `proposals/ADR-008-resonant-precedent.md:91-103`;
- `proposals/ADR-008-resonant-precedent.md:128-140`.

The “Remaining” list also still calls “real single-context verifier” item 1,
while WRT calls the generic refactor item 0 and the authorized lifecycle/key
state items 1–2:

- `proposals/ADR-008-resonant-precedent.md:144-156`.

Synchronize these only after the Warrant item-0 gate passes. Until authorized
lifecycle exists, do not let summaries reconstruct the superseded formula that
the main section tried to remove.

### [P2] WRT's R0 API prose still names the old function

WRT-001 says the non-filing call is `verify_citation(...)` directly, while the
probe now correctly introduces a distinct `verify_query(...)` wrapper with
`cw_wid=None`. Update the normative API distinction:

- R0: non-filing `verify_query`, no citation identity/role binding/subtraction;
- R1: stored `verify_citation`, checkpoint-bound citation Warrant.

This distinction was the substance of the previous gate and should not remain
only in prototype code.

## Recommendation

Accept the **non-filing mechanics** of R0, but not its current membership
semantics. First finish Warrant item 0. Then decide whether R0 uses raw
eligibility or stops before the effective-set join. After that, specify
authorized lifecycle + key-state + R1 as one contract. No signatures or runtime
registration yet.
