# EXP-002 — Σ-GLYPH versus a restricted WASM profile: preregistration

**Status: preregistration. No implementation exists, and none may begin until
this document is merged.** Non-normative: nothing here changes Book I, the
anchor set, or any released contract. This is an experiment about whether this
runtime should be the default choice for a task an outside consumer actually has
— and it is designed so that it can say no.

**The result is published whichever side wins.** A preregistration whose author
may withhold the outcome measures nothing.

---

## 0. The question

Warrant's `ski@v1` reasons exist so a stranger can re-execute someone else's
check safely: deterministic, bit-identical across implementations, with work and
peak memory bounded up front. A restricted WebAssembly profile claims a similar
envelope — sandboxed, portable, metered by fuel — and is a thing engineers
already have installed.

So: **on a non-trivial check that Warrant and Decision Archaeology actually need,
does Σ-GLYPH have a measurable advantage over a restricted WASM profile?**

Not "is it more elegant". Measured, against thresholds written below before
either implementation exists.

## 1. Pins

| Component | Pin |
| --- | --- |
| Σ-GLYPH evaluator | `sigma-glyph==0.6.7` (Book I v0.5 semantics), repository `master@01069d0410e6fc3b37d5dfeea1c58939e7ff6350` |
| Σ-GLYPH compiler | Profile C1 as published in `spec/book-1-truth.md` §6 — no new primitives may be added for this benchmark |
| WASM runtime | Wasmtime 48.0.0 (`wasmtime-py==48.0.0`), pinned by lockfile |
| Host | one machine, stated in the result with CPU model and OS; all timings from the same host |
| Python | 3.13.15 |

If any pin moves, the experiment is re-run under a new version number rather than
edited.

## 2. The task

> Parse raw JSON deterministically, reject duplicate keys and non-canonical
> input, evaluate a small policy over a bounded record, and return a
> standardised verdict.

This is chosen because it is what a Warrant policy check and a Decision
Archaeology case check both actually do, and because it is meaningfully harder
than arithmetic: it has parsing, rejection, and a canonicality boundary, which is
where real implementations disagree.

### Input contract (immutable once merged)

- input is **raw bytes**, supplied identically to both implementations;
- the record is bounded: at most 16 keys, nesting depth at most 3, at most 4 KiB;
- keys are ASCII; values are strings, integers within ±2⁵³, booleans, or null;
- **non-canonical input MUST be rejected**: duplicate keys, leading zeros in
  integers, non-minimal escapes, trailing content after the value, byte-order
  marks, and any whitespace outside the minimal JCS form;
- the policy is fixed: `amount_minor <= limit_minor && currency == "UAH" && !flagged`,
  where `limit_minor` is a literal in the check and every other operand comes
  from the record.

### Output contract (immutable once merged)

Exactly one of three outcomes, as a value both runtimes can produce and a
verifier can compare byte-for-byte:

| Verdict | Meaning |
| --- | --- |
| `ACCEPT` | input canonical, policy satisfied |
| `REJECT` | input canonical, policy not satisfied |
| `MALFORMED` | input not canonical, or outside the bounds |

`MALFORMED` is not an error channel. A run that crashes, hangs, or exits without
one of the three verdicts is a failure of that implementation on that vector, and
is recorded as such.

## 3. Fixtures

Written and frozen **before** either implementation, in `fixtures/`:

- 12 positive vectors (6 `ACCEPT`, 6 `REJECT`), covering both boundary sides of
  `limit_minor`;
- 18 negative vectors, at least one for each rejection cause listed above;
- 4 adversarial vectors: deepest allowed nesting, largest allowed size, a
  duplicate key at the end of a long record, and an integer at the ±2⁵³ boundary.

Both implementations receive identical bytes. A fixture may be added after the
start only if it is added to **both** sides and recorded in the change log; no
fixture may be removed.

## 4. Profiles

**Σ-GLYPH.** The current normative profile. No new primitives, no evaluator
changes, no encoding invented specially for this benchmark. If the task cannot be
expressed under the published profile, that is a result, not a reason to extend
the profile.

**WASM.** Wasmtime with a declared deterministic subset:

- no imports at all beyond the memory and the entry point — no clock, no random,
  no network, no environment, no filesystem, no WASI preview interfaces;
- fuel metering enabled, with a fixed fuel budget per run;
- a separate memory limiter, with a fixed maximum;
- `memory.grow` disallowed beyond the declared maximum;
- SIMD, threads, and reference types disabled;
- **fuel is not claimed to bound peak memory.** Fuel bounds work. Memory is
  bounded by the limiter, and the two are reported separately, because
  conflating them is the exact claim Σ-GLYPH's proven bound exists to make
  honestly.

Determinism is checked, not assumed: each WASM vector is run 3 times on the host
and once more in a fresh process, and the outputs must be byte-identical.

## 5. Metrics

Reported per implementation, per vector where applicable:

1. correctness on the 30 positive/negative vectors;
2. behaviour on the 4 adversarial vectors;
3. artifact size (term bytes / `.wasm` bytes, both content-addressed);
4. execution cost in the runtime's own unit (ATP / fuel);
5. wall time, median of 5 runs, plus the interquartile range;
6. peak memory, measured by the runtime's limiter and by the OS;
7. cold-start cost (first run in a fresh process);
8. authoring effort — wall-clock and lines, recorded honestly, including failed
   attempts;
9. trusted computing base — what a verifier must trust to believe the result, in
   components and approximate size;
10. portability — what else must be installed to re-run it;
11. difficulty of independent reconstruction — could a second implementer produce
    a byte-identical artifact from the published description alone;
12. number of special assumptions each side needed.

Metrics 9–12 are judgements and are reported as prose with their reasoning, not
as numbers pretending to be measurements.

## 6. Negative controls

- a vector that must be `MALFORMED` and is instead accepted fails that
  implementation, not the fixture;
- a deliberately corrupted artifact (one byte flipped) must not produce a valid
  verdict on either side;
- a fuel budget of zero and an ATP budget of zero must both refuse rather than
  answer;
- an implementation that produces the right verdict for the wrong reason —
  detected by the corrupted-artifact and zero-budget controls — is recorded as
  failing.

## 7. Kill criteria (numeric, fixed now)

| # | Condition | Consequence |
| --- | --- | --- |
| K1 | Σ-GLYPH cannot express the task under the published profile, or needs more than **50,000,000 ATP** on any single vector | Σ-GLYPH is not a general default runtime for this class of check |
| K2 | Σ-GLYPH's median wall time exceeds **50×** the WASM profile's on the same host, without demonstrating a property an outside consumer needs | status changes to **optional specialised runtime** |
| K3 | Σ-GLYPH's artifact exceeds **100×** the `.wasm` artifact and nothing in metrics 9–12 offsets it | same as K2 |
| K4 | WASM fails byte-identical determinism across the repeat runs, or exceeds its declared memory bound | the WASM profile is not called a drop-in replacement |
| K5 | either side fails any negative control | that side's numbers are reported as unverified, not as results |
| K6 | authoring effort for Σ-GLYPH exceeds **10×** the WASM side | recorded as a finding about the authoring surface, not as a kill on its own |

Thresholds may not be edited after a result is known. A different threshold means
**EXP-003**, with this document left intact and cited.

## 8. Allowed and forbidden changes after the start

**Allowed:** adding a fixture to both sides with a change-log entry; fixing a bug
in the harness, recorded and re-run for both; clarifying prose that does not move
a threshold or a contract.

**Forbidden:** changing the input or output contract, adding a Σ-GLYPH primitive
or a WASM import, removing a fixture, adjusting a kill threshold, changing the
host between measurements, or reporting a partial result while the rest is still
running.

## 9. What the result cannot say

- It cannot say Σ-GLYPH's proven bound is wrong; the bound is a theorem about
  semantics, and no benchmark reaches it.
- It cannot say WASM is unsafe; the restricted profile is a real envelope with a
  different trust base.
- It cannot generalise past this task. One check is one check, and the
  preregistration exists so that a single measurement is not read as a verdict on
  a runtime's whole reason to exist.

## 10. Change log

| Date | Change | Result already known? |
| --- | --- | --- |
| 2026-08-22 | initial preregistration | no |
