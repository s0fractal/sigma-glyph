# Codex independent gate: Warrant structured-report dogfood

**Date:** 2026-07-27
**Reviewer:** Codex / OpenAI
**Repository:** `sigma-glyph`
**Branch:** `feat/warrant-verify-gate`
**Base:** `master` at `b30a745571716c72c5f9988c7a9bbc7cf5e1033b`
**Candidate:** `6bbbf11ba125069038c0670dab081dd4f2dc5f31`
**Verdict:** **AMEND**

The architectural direction is correct: sigma-glyph now invokes the real pinned
Warrant verifier, consumes one structured report, does not re-derive Warrant
semantics, and rejects the ordinary malformed/no-store/contract fixtures.

The independent gate found two fail-open compositions at the consumer boundary
plus two totality/line-discipline gaps. The green hostile suite does not include
these vectors.

## P1 — Requested verification grade and trust policy are not bound to the report

`check_report()` accepts either `"base"` or `"settlement"` but does not receive
the grade requested by `verify()`. A verifier that ignores `--settlement` and
returns a valid base report is accepted as settlement verification.

### Reproduction

A producer that always prints:

```json
{"report":"warrant.verify-report@v0","grade":"base","ok":true,
 "records":0,"errors":0,"warnings":0,"findings":[]}
```

was invoked through:

```python
G.verify(
    "/missing",
    settlement=True,
    trust_config="/missing-trust",
    cmd=[python, "-c", "print(BASE_OK_REPORT)"],
)
```

Observed:

```text
(True, "verified: 0 record(s), 0 warning(s)")
```

Two option compositions also silently drop authority:

```text
warrant_gate.py .warrants --settlement
  -> VERIFIED (50 records, 4 warnings)

warrant_gate.py .warrants --trust-config /definitely/missing.json
  -> VERIFIED base (50 records, 55 warnings)
```

The first performs settlement without the intended trust source. The second
silently omits `--trust-config` from the verifier argv because `--settlement`
was absent. A caller can request a security control and receive success after
that control was ignored.

### Required closure

- Pass `expected_grade` into `check_report()` and require exact equality:
  base invocation accepts only `grade:"base"`; settlement accepts only
  `grade:"settlement"`.
- Reject `trust_config` without `settlement`; never silently discard it.
- For this sigma-glyph gate, require a trust config when settlement is requested.
  The connector exposes no alternative trusted genesis input, so settlement
  without one is not an authority-bearing gate.
- Add fake-producer vectors for base-as-settlement and settlement-as-base.
- Add CLI/API vectors for both invalid trust-option combinations.

## P1 — The hostile JSON boundary is last-wins, not strict

`json.loads()` silently accepts duplicate member names. Exact key-set validation
happens only after duplicates have collapsed, so an ambiguous report can pass.

### Reproduction

```json
{"report":"warrant.verify-report@v0","grade":"base",
 "ok":false,"ok":true,
 "records":0,"errors":0,"warnings":0,"findings":[]}
```

With return code 0:

```text
check_report(...) -> (True, "verified: 0 record(s), 0 warning(s)")
```

The same applies to duplicate `report`, `grade`, count, and finding keys. Which
semantic value wins is now a parser accident, not the closed `@v0` contract.

### Required closure

- Decode with a strict object-pairs hook that rejects duplicate members at every
  nesting level.
- Reject non-standard JSON constants (`NaN`, `Infinity`, `-Infinity`).
- Add duplicate-key vectors at the top level and inside a finding.
- Keep the existing exact top-level/finding key-set checks.

## P2 — Invalid UTF-8 crashes instead of returning a bounded rejection

`subprocess.run(..., text=True)` decodes captured output before returning.
Invalid UTF-8 raises `UnicodeDecodeError`, but `verify()` catches only
`OSError`.

Observed with a producer writing `b"\xff\n"`:

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff ...
```

The process exits nonzero in CLI use, so this is not an `ok:true` escape, but it
breaks the connector's promised `(False, reason)` totality. Capture bytes and
decode UTF-8 explicitly inside the fail-closed boundary, or catch decoding
errors. Add an invalid-UTF-8 producer vector.

## P2 — “Exactly one physical line / empty stderr” is implemented loosely

Two newline-terminated physical lines where the second is blank are accepted:

```python
check_report(GOOD_REPORT + "\n", "", 0) -> True
```

`rstrip("\n")` removes every trailing newline. Likewise `stderr.strip() == ""`
accepts whitespace-only stderr despite the stated “anything on stderr” rule.

Define one optional final LF rather than stripping an unbounded suffix, and
require `stderr == ""` if the contract is truly zero stderr. Add blank-line and
whitespace-stderr vectors.

## P2 — The two CI verdicts are not snapshot-bound

CI invokes base and settlement verification in separate processes against the
live `.warrants` directory. The two successful reports need not describe the
same byte snapshot if anything writes between calls.

Settlement verification already includes base integrity checks. Prefer one
settlement invocation for the adjudication gate and keep base behavior in the
connector test. If both public verdicts are intentionally required, run both
against one immutable copied snapshot or otherwise bind them to the same store
commitment.

This is not currently exploitable by the static checked-out GitHub job without a
concurrent writer, but it is the requested TOCTOU seam and should not be left
implicit in a “single machine boundary”.

## Cross-repository clarification

The two dogfood questions are real contract gaps, not sigma implementation bugs:

1. `errors == count(ERR findings)` and
   `warnings == count(WARN findings)` should be explicit report invariants.
2. `warrant.verify-report@v0` should be declared a closed schema; adding fields
   requires a new report tag.

The consumer's strict choices are fail-closed, so additive fields cannot change
its semantics silently. However, until Warrant documents these rules, the claim
that sigma consumes only the published contract is stronger than the published
contract itself. Land this as a separate narrow Warrant clarification, not as
part of the sigma branch.

## Evidence run

Passing on candidate `6bbbf11`:

- `tests/warrant_gate_test.py` against the real local Warrant verifier:
  `WARRANT-GATE: ALL PASS`.
- Real base connector invocation: 50 records, 0 errors.
- Real settlement connector invocation with `trust-config.json`: 50 records,
  0 errors.
- `tools/test-all.sh`: `TEST-ALL: ALL GREEN`, including 2103/2103 properties,
  Rust/Go differentials, governance replay, live federation demo, adjudication
  verification, and Lean bridges.
- `git diff --check master..HEAD` is clean.

The passing suites establish regression preservation. The countervectors above
demonstrate that the new machine boundary is not yet fully fail-closed under
mode/configuration and hostile-producer composition.
