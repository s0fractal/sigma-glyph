# v0.7.0 candidate — frozen bytes, round 6 (final multifamily gate)

Round 5 returned REJECT / NO VERDICT / REJECT. One REJECT was a real P0, older
than this candidate; one was refuted by the frozen bytes and is kept as
`REFUTED_BY_FROZEN_BYTES`; the NO VERDICT was a truncated reasoning trace.

**This is the last multifamily round for this candidate**, per `REVIEW-POLICY.md`.
Its outcome does not adopt anything: adoption is a threshold warrant filed by the
roster, and a model verdict is adversarial evidence, not authority.

## Revision

| | |
| --- | --- |
| branch | `spec/book1-v0.7.0-candidate` (draft PR #35) |
| bytes committed at | `5ffbfea` — all seven pull-request checks green on that head |
| adopted release this descends from | `v0.6.7` at `16a1355` |
| `master` | `f07edad`, carrying no normative byte of this candidate |

The two new CI steps were confirmed to have run as real steps on that head, not
as an empty job: *"Every normative suite matches its anchored schema"*, *"One
node, one wave — identity by hash, admission at load"*, and the Go gate, whose
`GO-TEST-GATE-SELFTEST: ALL PASS` and `GO-TEST-GATE: ALL PASS` appear in the CI
log — the first execution of Go's tests in CI at all.

## The anchor set — 13 entries

    SHA-256  c826eaf59c5e8979ed8f1554f3ed2fd9d8cb7c03c0be5e08932bfe9b178ffa49

    python3 tools/anchor_governance.py make-blob \
      --jurisdiction a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a \
      --ancestor d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5 \
      --release v0.7.0 --candidate > anchor-set.json

## Raw SHA-256 of the frozen source files

    f5aadc405c1c7d9f4d2e1f0431c91f40027e6b4037b43c2cbf6b278f4093ac6a  spec/book-1-truth.md
    4af7441e7da441d47d7f2e9e807da16a1dc057afc9de2071d101b37a982aa6d3  spec/book-1-truth.en.md
    cc8b133b999869616523239079504896e320d3fe5e34d581063cc6fb57a844c0  spec/book-2-navigation.md
    9018f215fc077dcdbcb233249101f3c87f8ba7b77fe8632da310a2c70b98a98e  spec/book-3-federation.md
    d7e7fa8394e359519eb95b0cea4c351f1646e82eaf0e48a53fbc6669431d26ff  spec/schemas/book1-conformance.schema.json
    9c7fca4ad8fa4f57f94a1347ae7f6aaaa3069d4c3c2c2ce2de54087b9c49b0c3  spec/schemas/book2-wave-conformance.schema.json
    3987c6b1e55c3b06f8afd3e7457de0e913950e4de8d8e6a2784c707714ad7579  spec/schemas/book3-federation-conformance.schema.json
    8ea03000e5f352f8f87234b68806d554dfbeb7ed0d0b33c2da28dca2eda399f2  tests/spec_conformance/vectors.json
    0928cba4103784588c3b3f00b0eddc5576a3cd5bc4054a55df6df5cd3e458381  tests/spec_conformance/wave_vectors.json
    686a9d0309c18148ed0178273908481dea6038e5306d82f069359f9a629c0998  tests/spec_conformance/federation_vectors.json
    68f96177d1975cf0e9a2f7881330173d71734f8b17a844449f22b7eeec50475b  tests/spec_conformance/governance_vectors.json
    f7ca204b3773ea1b6b5e288fa59240c24e9b14f49fa3cb6ba8db1a405b5ae8c3  spec/GOV-anchors.md
    07ddd994c397ee253065cf62636f51a99ba638afa18344da43afbf842f1fe4ec  spec/LORE.md
    9e35f22bffe40d0442b20ed98e8a9f7880de96bc325373d47e3f6c00865e94f1  spec/appendix-a-complexity.md

## What round 6 changed against round 5

One defect, Book II's and Book III's, found by Gemini and older than the
candidate: `wave(["APPLY","K","I"])` answered `ph 32768` while `wave("FALSE")`
answered `ph 49152` for the same NodeHash, because the Pin was reachable only
through a table keyed by NAME. Identity by Hash failing, not a wrong vector.

- Pins keyed by **NodeHash** across `sigma_wave`, `sigma_federation` and Go.
- Book III §5's fallback carries `complete(…, pin(APPLY(f,a)))`, with a new MUST:
  two different Pins for one NodeHash is a contradictory profile, refused at
  **load/admission**, never by write order — an **annotation-profile** refusal,
  not a `Receipt.exit` and not a DISSONANCE.
- The profile is accepted whole or does not exist: validated at import in Python,
  in `requireAnnotationProfile()` before dispatch in Go; no lookup builds it.
- Go's `nodeHashOf` bound to Book I's printed digests, nested cases included.

**Blast radius, measured after regeneration:** `wave_vectors.json`
byte-identical; `federation_vectors.json` changed in exactly one value,
`FV-WAVE-STRUCTURAL.ph 32768 → 49152`.

## Two changes to the gate itself

1. **No raw unified diff.** Round 5 put one at the top of the prompt and a
   reviewer read a line prefixed `-` — a deletion — as the current specification,
   raising a P0 about a sentence absent from the bytes. The prompt now presents
   the current normative text and says plainly that where the ADR and the Book
   disagree, the Book is the specification.
2. **The verdict is asked for first and last.** Two families have spent whole
   reply budgets on reasoning traces and delivered nothing. A truncated review
   with a verdict at the top is worth more than a complete one nobody receives.
   Each record now carries `verdict_first_stated`, `verdict_last_stated` and
   `changed_mind_while_reasoning`, so a reviewer that reasons its way to a
   different conclusion is recorded as having done so.

## Carried in unfixed, and named

`warrant-go` checks `result_hash` and `atp_spent` only. The honest phrasing is
**two full-receipt implementations and one compatibility-profile verifier**, and
that is what the record says until a separate non-normative PR fixes it.

DeepSeek's round-4 P2s stand as written: the intrinsic/CAS interaction is
derivable but unstated; §3.5's "the second question has no canonical answer at
all" is terse; "eval is total" sits uneasily beside implementation faults; §3.4's
`guard MUST міряти фактичний size(t)` constrains an optional internal fence.

## Release artifacts

None.
