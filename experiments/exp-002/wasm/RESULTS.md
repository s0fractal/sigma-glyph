# EXP-002, WASM side — result

Authoring clock: **2026-08-23T01:53:01Z → 01:56:19Z**, one attempt plus one
correction. That is agent wall-clock, not a human working day: it is recorded so
the two sides are compared on the same measure, and it is not comparable to the
three-working-day human budget the preregistration allows.

## What was built

`src/lib.rs`, `no_std` Rust compiled to `wasm32-unknown-unknown`. **No imports at
all** — checked at load, not assumed. Two exports beyond memory: `input_ptr` for
the host to write into, and `verdict(len) -> 0|1|2`.

Canonicality is not checked by re-serialising, because there is no allocator
here. It is enforced by accepting only the canonical form during the single
parsing pass: no whitespace, members strictly increasing, minimal escapes, no
leading zeros. A document that would serialise differently does not parse.

## Numbers

| Measure | Value |
| --- | --- |
| fixtures agreeing with the frozen verdicts | **34 / 34** |
| fuel | min 16,491 · median 21,403 · max 247,888 |
| wall time per fixture | median 12 µs · max 29 µs |
| peak memory | 17 pages = 1,088 KiB, limiter set at 2,048 KiB |
| artifact | 4,190 bytes |
| determinism | three runs in-process and a fourth in a fresh process, identical |

## Negative controls

**Zero fuel refuses.** The call traps rather than answering, as required.

**A corrupted artifact does not refuse, and cannot.** The preregistration asks
that a one-byte corruption must not produce a valid verdict. Measured over 114
single-byte flips, one at a time:

| outcome | count |
| --- | --- |
| rejected at load | 98 (86%) |
| trapped at run time | 3 (3%) |
| same verdict as the intact module | 7 (6%) |
| **different verdict, no objection** | **6 (5%)** |

So the control fails on this side, and the honest reading is not that the
implementation is careless. A `.wasm` module carries slack the runtime never
reads, and nothing in the format binds the artifact to its own identity: a
verifier who wants to know they ran *the* module must carry a digest **out of
band**. That is a property of the format, not of Wasmtime, and it is exactly the
place where a content-addressed artifact does not need the extra channel.

The 5% that answer differently without any objection are the sharp end: those
flips change the verdict silently.

## The first attempt, kept

`src/lib.rs.attempt-1` is the version that got one fixture wrong
(`neg-nonminimal-escape`). It accepted any `\u00xx` escape and compared the
currency by scanning the raw bytes for `"currency":"UAH"`. Both mistakes had the
same shape: checking the neighbourhood of a value instead of the value. The
correction binds the parsed string's byte range and refuses an escape for any
character a canonical document would write literally.

## What this does not say

Nothing here is a comparison. The Σ-GLYPH side has not been written, no
threshold has been evaluated, and none of K1–K6 has been triggered or ruled out.
