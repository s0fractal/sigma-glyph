# Adjudication — Kimi K3 full audit: U+2028/U+2029 canon split (2026-07-18)

Raw: [`2026-07-kimi-full-audit.md`](2026-07-kimi-full-audit.md). Kimi's multi-agent
run was interrupted while building the end-to-end proof (it had confirmed the
Go-vs-Python byte divergence but never saw its probe's output, wrote no review,
filed no fix). The finding was recovered from the session wire transcript,
**re-confirmed independently**, and fixed here.

## Disposition

- **P1 — Go `jcs()` over-escapes U+2028/U+2029.** CONFIRMED. Reproduced at the
  byte level: for `{"x": "a b"}`, Go emitted `{"x":"a b"}` (the escape
  as six ASCII bytes) while Python emitted the raw `e2 80 a8`. These are the
  consensus-critical canon bytes (`shaHex(jcs(body))` in `soundRecord` /
  `keyStateUnderGovernance`; `bytes.Equal(jcs(v), b)` in `parseJSONBlob`), so the
  two implementations would compute different WarrantIDs and disagree on
  id-soundness / on-wire canonicality — the split **GOV-anchors.md §2/§3** exists
  to forbid. Python is RFC-8785-correct; **Go was non-conformant.**

  **Fixed** in `impl-go/main.go`: `jcs()` now post-processes the encoder output
  through `unescapeLineSeparators`, which rewrites the ` `/` ` escapes
  back to raw UTF-8. Escape sequences are consumed **atomically** so a literal
  ` ` (an escaped backslash followed by the text `u2028`, i.e. `\\u2028` on
  the wire) is never mis-rewritten; control characters U+0000..U+001F stay
  escaped per RFC 8785; a fast path (`bytes.Contains(b, "\u202")`) makes the
  common no-separator case a single scan with no allocation.

  This is an **implementation** fix — **no anchored spec byte changes.** The Go
  impl is brought into compliance with the JCS canonicalization the spec already
  mandates.

## Verification

- New unit test `impl-go/jcs_test.go` (`go test ./...` → `ok`):
  - `jcs` of bodies containing U+2028, U+2029, and both emits raw UTF-8
    byte-identical to Python `json.dumps(ensure_ascii=False)`;
  - **confirmed the test fails without the fix** (temporarily bypassing
    `unescapeLineSeparators` → `got "  "` vs `want` raw → FAIL);
  - `\t` / `\b` and other control chars stay escaped (RFC 8785);
  - the escaped-backslash case `\\u2028` is preserved, not corrupted;
  - a body with no separators is byte-identical through the pass (fast path),
    so no existing vector shifts.
- No regression: Python oracle `ALL PASS`; `federation_differential 40/40`,
  `governance_differential 27/27`, `book1_fuzz` (1280 vectors,
  python-oracle + rust + warrant-go) all still agree.

## Files

- `impl-go/main.go` — `jcs()` routes through new `unescapeLineSeparators`.
- `impl-go/jcs_test.go` — new; byte-exact U+2028/U+2029 canon regression + the
  atomic-escape and fast-path guards.

## Note for a future governed release

This fix needs no vector change to land (it makes latent-divergent inputs
*agree*). But the natural belt-and-braces follow-up — adding a governance
conformance vector whose record body carries U+2028 in a string field, so the
differential harness exercises the split directly — touches the **anchored**
vector set and therefore belongs to a 2-of-3 governed release, alongside the
already-queued Book III NFC/spam clarifications. Queued, not shipped here.
