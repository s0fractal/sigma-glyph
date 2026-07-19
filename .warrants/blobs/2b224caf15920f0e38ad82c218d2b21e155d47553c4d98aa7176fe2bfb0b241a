# Kimi K3 full audit-review — U+2028/U+2029 canon split (recovered)

**Model:** Kimi K3 (Kimi Code CLI, `thinkingEffort: max`), multi-agent run
`session_ccff46ce-a2b2-49fd-9e4d-adbe5556b68d`, 2026-07-18.
**Status of the source run:** *interrupted.* Kimi ran the verifications (Python
oracle `ALL PASS`, federation/governance differentials, `book1_fuzz`), read all
three Python oracles, the Rust impl, and `impl-go/main.go` in full, then traced
the consensus-critical `jcs()` paths and empirically compared Go vs Python
control-character escaping. The session was cut off **at the moment it was
building the end-to-end proof** (a probe crafting a governance record with U+2028
in a string field) — before it saw the probe's output, wrote this review, or
filed a fix. This file recovers the finding from the session wire transcript; the
confirmation and fix are in the companion `-response.md`.

## (A) VERDICT

One real, latent **cross-implementation canonicalization split**. Book I/II/III
and every existing vector are sound *because no current vector exercises the
divergent characters*. The Go reference canonicalizer `jcs()` disagrees with the
Python oracle (and with RFC 8785) on exactly two code points — U+2028 (LINE
SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR). Since `jcs()` feeds the
consensus-critical WarrantID / id-soundness / on-wire canonicality checks, a
governance record whose body carries either character would be judged **id-sound
by Python and id-unsound by Go** (or vice-versa) — a federation-consensus split
between conforming nodes.

## (B) FINDING

**P1 — Go `jcs()` over-escapes U+2028/U+2029; Python (RFC 8785) emits them raw.**

*Location:* `impl-go/main.go` `func jcs()` (`json.NewEncoder` + `SetEscapeHTML(false)`).
Go's `encoding/json` escapes U+2028 and U+2029 to the six-byte ASCII sequences
` ` / ` ` **unconditionally** — `SetEscapeHTML(false)` does *not* turn
this off. Python's `json.dumps(…, ensure_ascii=False)` emits them as raw UTF-8
(`e2 80 a8` / `e2 80 a9`), which is what RFC 8785 / JCS requires: only
U+0000..U+001F and the two mandatory characters (`"` and `\`) are escaped;
everything ≥ 0x20 is literal.

*Empirical divergence* (same object, two canonicalizers):

```
GO  : {"x":"a b"}          (bytes: … 61 5c 75 32 30 32 38 62 …)
PY  : {"x":"a<U+2028 raw>b"}    (bytes: … 61 e2 80 a8 62 …)
```

Different bytes → different SHA-256 → different WarrantID.

*Consensus-critical reach.* Go uses this `jcs()` in the id-soundness / canonicality
paths the anchored spec pins in **GOV-anchors.md §2** ("every blob and record body
read from S or C MUST be byte-identical to the canonicalization of its parsed
value") and §3 (`WarrantID == sha256(canon(body))` as a closure-reachability
precondition): `soundRecord` (`shaHex(jcs(body)) != rid`),
`keyStateUnderGovernance`, and `parseJSONBlob` (`bytes.Equal(jcs(v), b)`).
A record body with U+2028 in any string field (an actor id, a note, a prose
reason) hashes differently under the two implementations, so they disagree on
whether it is id-sound / canonical — exactly the split GOV-anchors is meant to
prevent between conforming nodes.

*Correct side.* Python is RFC-8785-conformant; **Go is the bug.** The anchored
spec text is not affected (no spec bytes change) — the fix makes the Go
implementation comply with the canonicalization the spec already mandates.

## (C) NOT bugs (checked, holds)

- Python oracle `ALL PASS`; `federation_differential 40/40`,
  `governance_differential 27/27`, `book1_fuzz` 1280 vectors across
  python-oracle + rust + warrant-go — all agree (no existing vector contains
  U+2028/U+2029, which is why the split is latent).
- Go's `\b`, `\f`, `\n`, `\r`, `\t` and control-char escaping otherwise match
  Python exactly; U+2028/U+2029 are the *only* divergence.
- Rust `evaluate` ATP width, Go `uintValue` integer paths, and the selection /
  wave / governance-replay structures match the oracle.
