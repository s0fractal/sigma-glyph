# Adjudication — gemini-3.1-flash-lite on the oaip Ed25519 verifier (2026-07-30)

Raw review: [`2026-07-gemini31flashlite-ed25519.md`](2026-07-gemini31flashlite-ed25519.md)
(google/gemini-3.1-flash-lite via OpenRouter, **no execution**; sent *function slices* of
`oaip/impl/oaip.py` **without the file header** — an operator packaging error that directly
produced finding 2).

**Cross-repository note.** The subject is `oaip/impl/oaip.py`. Filed here for the same reason as
the sibling glm-4.7 Ed25519 review: `reviews/` is this stack's inbox, and the verifier under
review is the construction Σ-GLYPH's `tools/warrant_verify.py` and `tools/anchor_governance.py`
also implement.

**This was not an independent gate.** Same operator, same task framing as the other four
reviews in this round; see [`README.md`](README.md) § *Cross-family round, 2026-07-30/31*.

Note the severities: this reviewer filed **P1 and P2**, no P0. It is the only non-executing
reviewer in the round that did not overstate.

## Dispositions

| gemini-3.1-flash-lite claim | Verification | Verdict |
|---|---|---|
| **P1** `_ed_decompress` passes `sign = y >> 255`, which is "the parity of *y*", while RFC 8032 requires the parity of *x*; `_ed_recover_x` compares it against `x & 1`, so ~50% of valid signatures pick the wrong root and are wrongly rejected | Refuted twice over. **By reading:** in RFC 8032 §5.1.2 a point encoding is `y` in the low 255 bits with bit 255 set to the **least significant bit of x**. At `oaip.py:216` `y = int.from_bytes(b, "little")` is still the **whole 32-byte encoding**, so `y >> 255` at `:217` extracts exactly that x-parity bit; only on that same line is `y` then masked to 255 bits. The reviewer read the variable one line later than it acquires its meaning. **By reproduction:** 200 freshly generated RFC 8032 public keys, encode → `_ed_decompress` → re-affinise → compare: **200/200 round-trip exactly, 0 wrong roots**. A 50% root-selection error would not have survived the existing differential batteries either — it would fail immediately, not subtly | **REFUTED** |
| **P2** `hashlib` is used but "the import is missing from the provided code snippet"; recommends adding `import hashlib` and `import shutil` | `oaip/impl/oaip.py:43` `import hashlib`, `:47` `import shutil`. Both present. The model hedged correctly ("if `hashlib` is not explicitly imported in the actual file") — it was reporting the truth about the bytes it was handed | **ARTIFACT OF THE OPERATOR'S PROMPT, not a defect** |
| "What I checked" — small-order/non-canonical inputs, `S >= L` malleability, extended-coordinate addition, the `SIG_DECIDE_CAP` / `id(s)` memoised gate logic, the Legendre-symbol branch, `int.from_bytes` safety | Each matches the code as shipped | **AGREED** |

## The finding that is ours, not the model's

Finding 2 is a **process defect in how this round was run**: reviewers were sent function slices
without file headers, so a correctly-reasoning model reported a missing import that exists. The
same packaging is the proximate cause of the glm-4.7 Ed25519 false P0 in this round, where the
model could not re-read a hex literal it had already flagged itself as possibly mis-copying.

Two corrections adopted for future rounds:

1. Send **whole files**, or state explicitly and in-band that the header is elided.
2. Ask non-agentic reviewers to label a claim they could not reproduce as a **hypothesis**, so
   confidence levels do not blend.

## Commands run for this disposition

```
grep -n '^import' oaip/impl/oaip.py                    -> hashlib :43, shutil :47
python3 -c "<200 RFC 8032 keys, encode -> _ed_decompress -> compare>"   -> ok/bad = 200 0
python3 oaip/tests/signature_gate.py                   -> SIGNATURE-GATE: ALL PASS
```

## Outcome

**Zero code changes.** One claim refuted by reading plus reproduction, one caused by our own
packaging. No independent gate ran; nothing adopted.
