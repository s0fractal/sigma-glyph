# v0.7.0 candidate — frozen bytes, round 5

Round 4 returned **ADOPT / ADOPT-WITH-AMENDMENTS / ADOPT** with **no P0 from any
family**. DeepSeek's remaining P1 moves normative bytes, so under the rule in
force this is a new subject and all three families are asked again.

**Nothing here is adopted.** The `v0.7.0` section of `spec/ANCHORS.txt` is marked
CANDIDATE, `tools/anchor_governance.py status` does not list it, and the anchor
set below carries no signature.

## Revision

| | |
| --- | --- |
| branch | `spec/book1-v0.7.0-candidate` (draft PR #35) |
| adopted release this descends from | `v0.6.7` at `16a1355` |
| `master` at freeze time | `f07edad` |

All seven pull-request checks are green on the head this freezes, and the two new
ones were confirmed to have run as real steps rather than an empty job:
*"Every normative suite matches its anchored schema"* and *"The conformance
runner checks four observables, not two"*.

## The anchor set — now 13 entries, was 10

`round-5/anchor-set.json` — JCS-canonical, no trailing newline.

    SHA-256  edc0ede59b5907512b4b4578f162ff19ffdb5707502e5e3964aab164d4ae54b9

    python3 tools/anchor_governance.py make-blob \
      --jurisdiction a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a \
      --ancestor d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5 \
      --release v0.7.0 --candidate > anchor-set.json

The three new entries are the suite schemas. A specification that calls a JSON
file normative has to say what shape that file has, and a shape cannot be
declared by a version number — so the shape is bytes, and the bytes are anchored
next to the artifact they describe.

## Raw SHA-256 of the frozen source files

    f5aadc405c1c7d9f4d2e1f0431c91f40027e6b4037b43c2cbf6b278f4093ac6a  spec/book-1-truth.md
    4af7441e7da441d47d7f2e9e807da16a1dc057afc9de2071d101b37a982aa6d3  spec/book-1-truth.en.md
    cc8b133b999869616523239079504896e320d3fe5e34d581063cc6fb57a844c0  spec/book-2-navigation.md
    5c881f313eb036607003c69f5522a2f5c66dac111c2a94eded8bf741a5a1c51a  spec/book-3-federation.md
    d7e7fa8394e359519eb95b0cea4c351f1646e82eaf0e48a53fbc6669431d26ff  spec/schemas/book1-conformance.schema.json
    9c7fca4ad8fa4f57f94a1347ae7f6aaaa3069d4c3c2c2ce2de54087b9c49b0c3  spec/schemas/book2-wave-conformance.schema.json
    3987c6b1e55c3b06f8afd3e7457de0e913950e4de8d8e6a2784c707714ad7579  spec/schemas/book3-federation-conformance.schema.json
    8ea03000e5f352f8f87234b68806d554dfbeb7ed0d0b33c2da28dca2eda399f2  tests/spec_conformance/vectors.json
    0928cba4103784588c3b3f00b0eddc5576a3cd5bc4054a55df6df5cd3e458381  tests/spec_conformance/wave_vectors.json
    a6ade79884808c88b951567425b2ec012cee496e6b043740eec4771f923fc07b  tests/spec_conformance/federation_vectors.json
    68f96177d1975cf0e9a2f7881330173d71734f8b17a844449f22b7eeec50475b  tests/spec_conformance/governance_vectors.json
    f7ca204b3773ea1b6b5e288fa59240c24e9b14f49fa3cb6ba8db1a405b5ae8c3  spec/GOV-anchors.md
    07ddd994c397ee253065cf62636f51a99ba638afa18344da43afbf842f1fe4ec  spec/LORE.md
    9e35f22bffe40d0442b20ed98e8a9f7880de96bc325373d47e3f6c00865e94f1  spec/appendix-a-complexity.md

`spec/book-1-truth.en.md` is listed because the gate reads it, not because it is
anchored.

## What round 5 changed against round 4

DeepSeek's P1 was schematic: the Books declare a JSON artifact normative without
defining its shape. Checking it found the instance, and the instance was worse
than the argument.

**§3.4 enumerates three exits. The normative suite carried a fourth value.**
`EV-BAD-BYTES-CHILD` records `expected.outcome: "invalid_object"`, while the
reference oracle's receipt for that vector reads `exit = normal_form,
atp_spent = 5` — and §7 called `expected.outcome` "the canonical exit". Book,
suite and engine disagreed about one field, which is exactly what §7 says makes
an edition non-conformant.

- **Two levels, two fields.** `expected.exit` is `Receipt.exit`, closed enum of
  three. `expected.outcome` is a suite-level classification and keeps
  `invalid_object`, which names a `normal_form` exit whose result is the
  Canonical Invalid Object — **not a fourth exit**. Book I states that deriving
  either from the other checks neither.
- **The schema is an anchored file, not a version number.** `format_version`
  named a version and defined nothing: no required fields, no closed-world
  policy, no enums, no nested shapes. Three closed-world schemas now do, anchored
  beside their suites. `tools/suite_schema.py` validates them in the standard
  library — a validator that runs only where `jsonschema` is installed is a check
  whose subject can quietly go empty — and its selftest breaks ten rules per
  suite.
- **The runner checks four observables, not two.** It called the two-value
  `eval_hash`; it reads a `Receipt` now. 49 checks became 148.
- **The classification no longer self-confirms.** `generate.py` derived
  `outcome` from the oracle and never passed it to the hand-declared check.
  `exit` and `outcome` are now declared by hand for all 31 declared eval vectors,
  from the spec statement each cites. The old derivation was wrong in a way worth
  naming: it classified by the *result term*, so a run settling on
  `DISSONANCE(ATP Exhausted)` would have been labelled `atp_exhausted` while its
  exit is `normal_form`.
- **A second engine agrees on the exit.** `impl-rs` hard-required
  `format_version == 2` and would have refused the file. It carries an `Exit`
  enum now — it always knew the exit at each return site and discarded it — and
  checks the exit and the classification. `tests/book1_fuzz.py` carries them
  across thousands of generated vectors per run.
- **Negative controls mutate exit and outcome independently**, requiring each to
  fail alone: the exit mutation where the two agree, the outcome mutation on the
  one vector where they differ.
- `tests/spec_conformance/README.md` said `outcome` was informative while the
  candidate declared it normative. Corrected, with the date it was wrong.

Suite format **v3**, suite package **0.6.0**.

## Carried into this round unfixed, and named

- **`warrant-go` checks two observables of four.** The third Book I engine reads
  `result_hash` and `atp_spent` only. It lives in a repository under a feature
  freeze, so the exit is agreed by **two engines of three**, not three.
- **DeepSeek's round-4 P2s are left as written**: the interaction between the
  content-environment CAS check and §5.1's intrinsic synthesis is derivable but
  not stated; §3.5's "the second question has no canonical answer at all" is
  terse; "eval is total" sits uneasily beside implementation faults; and §3.4's
  `guard MUST міряти фактичний size(t)` is a normative constraint on an optional
  internal fence. None changes a verdict for a documented state.

## Decided, not open: GOV-anchors

The owner's disposition is in ADR-010. DeepSeek downgraded its own standing P0 to
P1 in round 4 on its own reasoning, and Qwen recorded the same conclusion
independently as P3. Round 5's reviewers see the disposition, because the prompt
carries the ADR; they are therefore not blind to it.

## Release artifacts

None.
