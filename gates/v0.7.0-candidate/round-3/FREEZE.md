# v0.7.0 candidate — frozen bytes, round 3

Round 2: one ADOPT, one REJECT, one NO VERDICT. The REJECT's first finding was
again one the previous round's fix had introduced, and it is fixed here. The
NO VERDICT was a fact about the reply budget, not about the candidate: the
reviewer was cut off mid-reasoning at 24 000 tokens, so `tools/candidate_gate.py`
now takes `--max-tokens` and records it.

**Nothing here is adopted.** The `v0.7.0` section of `spec/ANCHORS.txt` is marked
CANDIDATE, `tools/anchor_governance.py status` does not list it, and the anchor
set below carries no signature. Adoption is a threshold warrant, not a file.

## Revision

| | |
| --- | --- |
| branch | `spec/book1-v0.7.0-candidate` (draft PR #35) |
| adopted release this descends from | `v0.6.7` at `16a1355` |
| `master` at freeze time | `f07edad` |

The gate re-hashes every file listed below immediately before sending anything
and refuses if one has moved. The digests, not a commit, are what a verdict
attaches to.

## The anchor set

`round-3/anchor-set.json` — JCS-canonical, no trailing newline.

    SHA-256  4c93717a7007ef8af179ae39ee62492a59594e23be8fdc4a4eef5e04a98f3ae9

Reproduced byte-for-byte by:

    python3 tools/anchor_governance.py make-blob \
      --jurisdiction a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a \
      --ancestor d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5 \
      --release v0.7.0 --candidate > anchor-set.json

## Raw SHA-256 of the frozen source files

    7948b2b58ddbf3fbd7b08a16487e23c1c521f838ad1bffd8f913f54215e2cb70  spec/book-1-truth.md
    2d55f4d8b0619ca061eacb72a691edd3df86e0e852b31bed2c7ab4a99525df53  spec/book-1-truth.en.md
    7ef8f91b45854828a46b6f503f41211bdbe455836a1870b22e7ee5298ce902d6  spec/book-2-navigation.md
    c0c5d48b27aa58eba9f02ddb22e1d7e6b115f871620f8e5bd327b574074a654a  spec/book-3-federation.md
    bda72b13dbe9edd1448b63b665c73af7b29be8110c643ec39d8953c6a7409196  tests/spec_conformance/vectors.json
    0928cba4103784588c3b3f00b0eddc5576a3cd5bc4054a55df6df5cd3e458381  tests/spec_conformance/wave_vectors.json
    a6ade79884808c88b951567425b2ec012cee496e6b043740eec4771f923fc07b  tests/spec_conformance/federation_vectors.json
    68f96177d1975cf0e9a2f7881330173d71734f8b17a844449f22b7eeec50475b  tests/spec_conformance/governance_vectors.json
    f7ca204b3773ea1b6b5e288fa59240c24e9b14f49fa3cb6ba8db1a405b5ae8c3  spec/GOV-anchors.md
    07ddd994c397ee253065cf62636f51a99ba638afa18344da43afbf842f1fe4ec  spec/LORE.md
    9e35f22bffe40d0442b20ed98e8a9f7880de96bc325373d47e3f6c00865e94f1  spec/appendix-a-complexity.md

`spec/book-1-truth.en.md` is listed because the gate reads it, not because it is
anchored.

## What round 3 changed against round 2

Both in Book I §3.5, and only there.

- **The paragraph round 2 added contradicted itself.** It said an undemanded
  entry "does not affect the result" and, in the next sentence, that a permitted
  wider check MUST end in a local refusal — so a poisoned entry nobody demands
  both must not and may change the outcome. DeepSeek produced the counterexample:
  `H(I)`, `atp = 10`, an environment holding canonical `I` bytes under the zero
  key. The confusion was mine, between *the result* and *whether a verifier
  agrees to compute at all*. Now stated as the only thing that can actually
  diverge: an undemanded entry MUST NOT change any canonical `Receipt`, and a
  verifier that declines such an environment is exercising admission (§3.6),
  which produces no `Receipt` and therefore has nothing to disagree about.
- **`NodeHash(bytes) = key` was undefined for buffers that fail §4.1.** There is
  no node, so there is no NodeHash, yet failure mode (b) prices materializing the
  Canonical Invalid Object — which is only reachable if the key check passed. The
  property is now `SHA-256(bytes) = key` over the raw buffer, checked before
  validation, with the two questions named as different: whether a buffer is a
  valid node has a canonical answer, whether bytes belong under a key has none.
  This matches what the reference oracle has always done (`node_hash(b) != h`
  before `deser(b)`), so no vector changes.

`vectors.json` moved only in its hand-declared `book1_anchor` pin.

## Still open, and deliberately not resolved here

`spec/GOV-anchors.md` pins Book versions this candidate makes stale. Round 1:
P0, P0, P3. Round 2: Gemini reversed to "not a P0" citing Kimi's round-1
reasoning, DeepSeek held it at P0. **Count the independent judgments rather than
the verdicts**: Gemini's reversal rests on an argument it read in the ADR, so on
this point there is one line of reasoning with two subscribers, not two
independent findings. It is not resolved by the author, for the reason ADR-010
gives, and it is the decision this candidate most needs from the roster.

## Release artifacts

None.

## Round 3's outcome: incomplete, for a reason that is not about the candidate

| Reviewer | Verdict | |
| --- | --- | --- |
| `google/gemini-3.1-pro-preview` | **ADOPT** | full review recorded |
| `deepseek/deepseek-v4-pro-0813` | **NO VERDICT** | `HTTP Error 402: Payment Required` |
| `moonshotai/kimi-k3` | **NO VERDICT** | `HTTP Error 402: Payment Required` |

The OpenRouter account ran out of credit partway through the round: three rounds
of a 130 KB prompt across three models spent it. DeepSeek was retried at a
12 000-token reply budget rather than 40 000 and returned 402 again; the balance
at that point was $0.168.

**This is one verdict, not a gate.** Two of three families have not seen these
bytes. The correct reading is that the round did not happen, not that it went
one-nil: an ADOPT standing alone says only that one reviewer found nothing, and
the two whose round-2 findings produced these very edits were not asked whether
the edits close them. In particular DeepSeek, whose P0 and P1 this round answers,
has not seen the answer.

Nothing here is substituted for. A cheaper model from the same family would have
changed the reviewer set mid-gate, and choosing to spend more is the account
holder's decision, not the reviewer-runner's.

## The prepared adoption warrant

Unsigned, in this directory as `adoption-warrant.unsigned.json`, outside
`.warrants/`.

| | |
| --- | --- |
| subject (anchor-set blob) | `4c93717a7007ef8af179ae39ee62492a59594e23be8fdc4a4eef5e04a98f3ae9` |
| ancestor | `d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5` (adopted v0.6.7) |
| prior warrant | `b4dc05e307b81e7415536a2e2442ff5db41d29ea5b392423735e1892236e095c` |
| threshold | 2-of-3 — `claude-fable-5@sigma-glyph`, `codex@sigma-glyph`, `s0fractal@sigma-glyph` |
| WarrantID **if** filed by `s0fractal@sigma-glyph` at `ts = 1788000000` | `e9dd72bccb56444b64fb4faf475bf56e6926c39c41607cea3e1bc6aa79cbc5da` |

The WarrantID is conditional on those two values because both are inside the
body and therefore inside the hash. A different filer or a different timestamp is
a different warrant. Regenerate with:

    python3 tools/prepare_adoption.py gates/v0.7.0-candidate/round-3 \
      --actor <roster actor> --ts <filing time>

which prints the ID and the exact `cosign.py` and settlement-verification
commands. It holds no keys and cannot sign.
