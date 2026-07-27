# Codex re-gate: `feat/warrant-verify-gate`

Date: 2026-07-27
Candidate: `8843fb38924865ca1a0c9358870673ee3e26d26a`
Verdict: **APPROVE**

## Scope

Adversarial re-gate of the Warrant verification connector after the previous
AMEND, including the companion `warrant.verify-report@v0` clarification at
Warrant candidate `8febf8c148db6a2658dc5d3f4325d3725a60516d`.

## Closure

All prior findings are closed:

- the requested verification grade is carried across the process boundary and
  must equal the report grade;
- duplicate JSON members are rejected recursively;
- settlement/trust-config option mismatches are rejected before execution;
- invalid UTF-8 and contaminated output streams fail closed without traceback;
- CI performs one settlement-grade adjudication, which subsumes base integrity.

Independent countervectors covered grade downgrade in both directions,
top-level and nested duplicate members, extra newlines, whitespace-only stderr,
invalid UTF-8, hostile scalar values, and invalid option combinations. None
produced a false `VERIFIED`.

The connector is a strict consumer of the documented closed `@v0` schema. It
does not reimplement Warrant semantics and branches only on the documented
machine-contract fields.

## Verification

- `tests/warrant_gate_test.py`: **29/29 PASS**
- `tools/test-all.sh`: **TEST-ALL: ALL GREEN**
- real settlement gate against the local Warrant candidate: **VERIFIED**

## Integration note

Land the Warrant contract clarification before, or atomically with, updating
consumers to rely on its closed-schema guarantee. The companion Warrant review
has one non-blocking-for-this-code but merge-blocking-for-that-doc-branch P2:
the producer repository should permanently assert the newly documented
schema/count invariants in its own report suite.
