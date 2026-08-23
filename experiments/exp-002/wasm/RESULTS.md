# EXP-002, WASM side — result

Authoring clock: **2026-08-23T01:53:01Z → 01:56:19Z** for the implementation,
plus a correction pass after review. Agent wall-clock, recorded so both sides are
measured the same way; it is not comparable to the three-working-day human budget
the preregistration allows.

## The load path, and why it is what it is

Σ-GLYPH names a term by the hash of itself, and a verifier who wants to run *that*
term must be told the hash out of band — the hash does not live inside the bytes.
WASM has no such rule, so this profile adds one: `artifact.json` pins the
expected SHA-256, `profile_load.py` compares the bytes against it, and only a
matching module reaches Wasmtime.

Without that, the two sides would not be comparable: one would have been judged
on an identity check the other was never given. With it, the difference that
remains is **where the check lives** — normative in Book I, a profile wrapper
here — which belongs in the trusted-computing-base metrics (9–12), not in a kill
criterion.

## Numbers

Thirty-four vectors, five runs each, on one host: **Apple M4 Pro**, macOS, under
the interpreter and runtime the preregistration pins — Python 3.13.15 and
Wasmtime 48.0.0. The runner **refuses to produce a result** under anything else,
and checks the installed package rather than repeating a version string from a
manifest: run under Python 3.14.7 it prints `REFUSED: python 3.14.7, the
preregistration pins 3.13.15` and exits 1.

| Measure | Value |
| --- | --- |
| vectors agreeing with the frozen verdicts | **34 / 34** |
| fuel | min 16,489 · median 21,401 · max 247,886 |
| per-vector median wall time | 12.6 µs (slowest vector 30.7 µs) |
| per-vector IQR | median 0.88 µs |
| peak linear memory | 17 pages = 1,088 KiB, limiter at 2,048 KiB |
| OS peak RSS, fresh process | 37,680 KiB — the Python and Wasmtime process, not the module |
| cold start, fresh process | 16.6 ms, including importing the runtime |
| artifact | 4,190 bytes, `sha256 e16eaa31e4bb0670…` |
| determinism | five runs per vector in-process, plus **all thirty-four replayed in a freshly started process**, every id and verdict compared |

Host, OS, Python, Wasmtime, rustc and the artifact digest are recorded in
`results.json` beside every per-vector number.

## Controls, which are gates

Both refuse, and a failure exits non-zero:

- **a corrupted artifact** is rejected before execution, by digest, under the
  hash the verifier was given: `REFUSED before execution: artifact is
  da76bd4e…, expected e16eaa31…`. Verified by flipping a byte of the committed
  file and observing exit status 1;
- **a zero fuel budget** traps instead of answering;
- **a freshly started process** must reach the same verdict for every vector.
  Comparing one fixture and trusting the rest was the earlier version's mistake:
  a subprocess that failed produced zeros and a green run. Now a skipped vector,
  an unknown vector, a differing verdict, a wrong interpreter or a non-zero exit
  each turn the gate red — checked by making the subprocess answer `ACCEPT`
  everywhere, which produced 25 failures and exit status 1.

## An observation that is not a control

Separately from the profile, and with **no digest check at all**, single-byte
flips were handed straight to Wasmtime to see what the runtime alone catches.
Over **114 offsets sampled at a fixed step of 37 bytes** through this particular
4,190-byte module:

| outcome | count |
| --- | --- |
| rejected at load | 98 |
| trapped at run time | 3 |
| same verdict as the intact module | 7 |
| different verdict, no objection | 6 |

That is a survey of one sample of one artifact, not a probability of arbitrary
corruption, and it says nothing about whether WASM "can" pass a control — with
the digest check it does. What it does show is what the runtime notices on its
own, which is a different question from what the profile notices, and the answer
is: most of a module is structural, and some of it is not.

## The first attempt, kept

`src/lib.rs.attempt-1` got `neg-nonminimal-escape` wrong: it accepted any
`\u00xx` escape, and compared the currency by scanning the raw bytes for
`"currency":"UAH"`. Both mistakes were the same shape — checking the
neighbourhood of a value instead of the value. The correction binds the parsed
string's byte range and refuses an escape for any character a canonical document
would write literally.

## What this does not say

No comparison. The Σ-GLYPH side has not been written, no threshold has been
evaluated, and none of K1–K6 has been triggered or ruled out.
