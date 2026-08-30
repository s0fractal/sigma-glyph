# v0.7.0 candidate — frozen bytes, round 4

Round 3 completed at its third delivery attempt: **ADOPT** (Gemini), **REJECT**
(DeepSeek), **NO VERDICT** (Moonshot, three attempts, never a reply). DeepSeek's
review carried one observation that changes normative bytes, so under the rule in
force — any defect that moves the bytes voids the round — this is a new subject
and all three families are asked again.

**Nothing here is adopted.** The `v0.7.0` section of `spec/ANCHORS.txt` is marked
CANDIDATE, `tools/anchor_governance.py status` does not list it, and the anchor
set below carries no signature.

## Revision

| | |
| --- | --- |
| branch | `spec/book1-v0.7.0-candidate` (draft PR #35) |
| adopted release this descends from | `v0.6.7` at `16a1355` |
| `master` at freeze time | `f07edad` |

## The anchor set

`round-4/anchor-set.json` — JCS-canonical, no trailing newline.

    SHA-256  91b4182c9332c0e7a64acb5faba6354bbf3f64a0e997837ee32329817c9015b1

Reproduced byte-for-byte by:

    python3 tools/anchor_governance.py make-blob \
      --jurisdiction a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a \
      --ancestor d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5 \
      --release v0.7.0 --candidate > anchor-set.json

## Raw SHA-256 of the frozen source files

    aa583a558772263f0aefc8a6d2d6e653c1ee27681b1a5458a4a59a8d725de79e  spec/book-1-truth.md
    c10129ef069f2e03896672dae9f46fbefad3b43e501493877a2565e12cf807eb  spec/book-1-truth.en.md
    7ef8f91b45854828a46b6f503f41211bdbe455836a1870b22e7ee5298ce902d6  spec/book-2-navigation.md
    c0c5d48b27aa58eba9f02ddb22e1d7e6b115f871620f8e5bd327b574074a654a  spec/book-3-federation.md
    4a3240d244160e755377fc16aa1df1ce53436dee948d8dddc796afe83ee804b3  tests/spec_conformance/vectors.json
    0928cba4103784588c3b3f00b0eddc5576a3cd5bc4054a55df6df5cd3e458381  tests/spec_conformance/wave_vectors.json
    a6ade79884808c88b951567425b2ec012cee496e6b043740eec4771f923fc07b  tests/spec_conformance/federation_vectors.json
    68f96177d1975cf0e9a2f7881330173d71734f8b17a844449f22b7eeec50475b  tests/spec_conformance/governance_vectors.json
    f7ca204b3773ea1b6b5e288fa59240c24e9b14f49fa3cb6ba8db1a405b5ae8c3  spec/GOV-anchors.md
    07ddd994c397ee253065cf62636f51a99ba638afa18344da43afbf842f1fe4ec  spec/LORE.md
    9e35f22bffe40d0442b20ed98e8a9f7880de96bc325373d47e3f6c00865e94f1  spec/appendix-a-complexity.md

## What round 4 changed against round 3

One defect, in Book I §7, of the same class as rounds 1 and 2 — a clause the
candidate added and a neighbouring clause it did not revisit.

TV-7 read `∀n: eval(Ω,n) = DISSONANCE(ATP Exhausted)`, and TV-12 read
`eval(H(I), n) = ⟨I⟩, 0 ATP`, both quantifying over every `n` whatsoever. §3.6,
which this candidate adds, refuses a budget outside `uint32` **before**
evaluation and forbids that refusal from being a canonical exit. So the
unbounded quantifiers claimed a canonical outcome for inputs the same Book says
must be locally refused. Both are now bounded to `n : uint32`, with the reason
stated in TV-7.

`tools/spec_audit.py`'s hand-written declarations for those two statements were
re-keyed to the new sentences, which is the mechanism working as intended: the
declarations are keyed by the statement itself, so editing one invalidates its
declaration and forces a fresh look rather than silently carrying over.

`vectors.json` moved in its `book1_anchor` pin and nowhere else.

## The reviewer set changed, and why

| Family | Round 3 | Round 4 |
| --- | --- | --- |
| Google | `google/gemini-3.1-pro-preview` | unchanged |
| DeepSeek | `deepseek/deepseek-v4-pro-0813` | unchanged |
| third | `moonshotai/kimi-k3`, then `kimi-k2.6` | **`qwen/qwen3-235b-a22b-2507`** |

Moonshot never delivered a review on this subject. `kimi-k3` returned nothing in
every round it was asked; `kimi-k2.6`, tried as its replacement, produced 147 315
and then 83 414 characters of reasoning trace and no reply, at a 40 000- and then
a 24 000-token budget. The traces are kept beside the records as
`*.reasoning-trace.txt` — they are evidence about the reviewer and about this
tool's settings, and they are not reviews.

Not OpenAI either, though GPT-5 sat on the original ADR-007 gate: `codex@
sigma-glyph` is a roster signer and this round's instructions came through it, so
putting the same vendor on the gate would concentrate the instructing, the
signing and a third of the reviewing in one place. Qwen is outside both.

**This is a change to the gate's own composition and it weakens comparability
across rounds.** Round 4's three families are not round 1's three families. It is
recorded here rather than absorbed silently.

## Decided, not open: GOV-anchors

The owner's disposition is in ADR-010: the candidate preserves the exact
anchor-hashing semantics GOV-anchors 1.0.2 consumes, and a dependency-minimizing
GOV 2.0 is separate governed work, not part of this adoption. DeepSeek held this
at P0 in rounds 2 and 3 and its dissent stands in the record; the owner deciding
it does not convert the disagreement into consensus.

Round 4's reviewers see that disposition, because the prompt carries ADR-010.
They are therefore not blind to it — the same partial-independence limit the
earlier rounds carry, stated again because it now touches the one question the
gate has split on throughout.

## Release artifacts

None.
