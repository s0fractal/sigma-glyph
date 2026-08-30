# v0.7.0 candidate — frozen bytes, round 2

Round 1 returned three REJECTs from three families. Four of its findings are
fixed and one is recorded unresolved; the dispositions are in
[`proposals/ADR-010`](../../../proposals/ADR-010-three-inputs-and-a-receipt.md).
The bytes therefore moved, and round 1's verdicts do not carry: they are a record
of a revision that is no longer proposed. This file freezes what round 2 is run
over.

**Nothing here is adopted.** The `v0.7.0` section of `spec/ANCHORS.txt` is marked
CANDIDATE, `tools/anchor_governance.py status` does not list it, and the anchor
set below carries no signature. Adoption is a threshold warrant, not a file.

## Revision

| | |
| --- | --- |
| branch | `spec/book1-v0.7.0-candidate` (draft PR #35) |
| candidate bytes, round 1 | `1c2b6ca42cb95cdc035fc887cd0587a5758862d7` |
| adopted release this descends from | `v0.6.7` at `16a1355` |
| `master` at freeze time | `f07edad` |

The gate re-hashes every file listed below immediately before sending anything
and refuses if one has moved (`tools/candidate_gate.py`). The digests, not a
commit, are what a verdict attaches to — which is why this table names the branch
and not a hash that the act of recording it would invalidate.

## The anchor set

`round-2/anchor-set.json` — 1410 bytes, JCS-canonical, no trailing newline.

    SHA-256  79bf939a737e88d310a029150facb7ba77e9e9483e622e868deeca57f628e9b5

Reproduced byte-for-byte by:

    python3 tools/anchor_governance.py make-blob \
      --jurisdiction a30bd20205cb482588e436d8a4eb6fa72cdfefe2f4b35572e292d3814d198a0a \
      --ancestor d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5 \
      --release v0.7.0 --candidate > anchor-set.json

`--candidate` is required and is the point: without it the command refuses,
because serializing an annotated section by accident is how the wrong bytes get
put in front of a signer. The jurisdiction is the governance genesis root; the
ancestor is the adopted `v0.6.7` anchor-set blob.

## Anchors (`NodeHash(LITERAL, atom=SHA-256(bytes))`)

| Path | v0.6.7 (adopted) | round 1 | round 2 (current) |
| --- | --- | --- | --- |
| `spec/book-1-truth.md` | `a98a03bd…` | `a97fc637…` | **`eff52cdb…`** |
| `spec/book-2-navigation.md` | `7733dfb0…` | `8b704112…` | **`c88d78f7…`** |
| `spec/book-3-federation.md` | `e7bdbac8…` | `0db4007d…` | **`f9f6b1f7…`** |
| `tests/spec_conformance/vectors.json` | `08116edb…` | `55abdc42…` | **`fe89e80d…`** |
| `tests/spec_conformance/wave_vectors.json` | `9ef44d02…` | `904395f2…` | `904395f2…` |
| `tests/spec_conformance/federation_vectors.json` | `310296a8…` | `392f74ef…` | `392f74ef…` |
| `tests/spec_conformance/governance_vectors.json` | `14ead59a…` | `14ead59a…` | `14ead59a…` |
| `spec/GOV-anchors.md` | `59bbb117…` | `59bbb117…` | `59bbb117…` |
| `spec/LORE.md` | `9bd7977c…` | `9bd7977c…` | `9bd7977c…` |
| `spec/appendix-a-complexity.md` | `2df9194b…` | `2df9194b…` | `2df9194b…` |

Six of ten move against the adopted release; four of those moved again in round
2. The two vector suites whose Books changed in round 2 did **not** move, because
Books II and III gained a mapping clause and no vector: their prose now says
which record fields carry a prose claim, and the records were already those
fields. Full values are in `spec/ANCHORS.txt`; `python3 tools/verify_anchors.py`
checks them against the files.

## Raw SHA-256 of the frozen source files

The anchors above are NodeHashes, not file digests; these are the file digests, so
a reader with the files and no Book I implementation can still check them.

    128b1a90cecf4aa57faf08eb39ae121e20641e011a0b6d6ff6c53240a61e7d26  spec/book-1-truth.md
    c89aeb39625d98b6862245dbf3a0988d672cce4b7322821907ae22b6ac7be7f5  spec/book-1-truth.en.md
    7ef8f91b45854828a46b6f503f41211bdbe455836a1870b22e7ee5298ce902d6  spec/book-2-navigation.md
    c0c5d48b27aa58eba9f02ddb22e1d7e6b115f871620f8e5bd327b574074a654a  spec/book-3-federation.md
    06ef8926ffc2f584eeb0e0de1fb5767ee9bc025d81c7159be00780516ff466cc  tests/spec_conformance/vectors.json
    0928cba4103784588c3b3f00b0eddc5576a3cd5bc4054a55df6df5cd3e458381  tests/spec_conformance/wave_vectors.json
    a6ade79884808c88b951567425b2ec012cee496e6b043740eec4771f923fc07b  tests/spec_conformance/federation_vectors.json
    68f96177d1975cf0e9a2f7881330173d71734f8b17a844449f22b7eeec50475b  tests/spec_conformance/governance_vectors.json
    f7ca204b3773ea1b6b5e288fa59240c24e9b14f49fa3cb6ba8db1a405b5ae8c3  spec/GOV-anchors.md
    07ddd994c397ee253065cf62636f51a99ba638afa18344da43afbf842f1fe4ec  spec/LORE.md
    9e35f22bffe40d0442b20ed98e8a9f7880de96bc325373d47e3f6c00865e94f1  spec/appendix-a-complexity.md

`spec/book-1-truth.en.md` is listed because the gate reads it, not because it is
anchored: the English rendering is informative, and Book I §7 says the Ukrainian
text and the vector suite decide.

## What round 2 changed against round 1

- **Book I §3.4** — the out-of-domain budget clause. Round 1's bytes said
  "implementation-defined (MAY reject/clamp)" for `ATP > 2³²−1` in §3.4 and
  "MUST be refused" for a non-`uint32` `atp` in §3.6. All three reviewers found
  it; two produced the same counterexample. §3.4 now refuses by reference to
  §3.6 and forbids clamping by name.
- **Book I §3.5** — when the CAS property is checked. Now: for every hash the
  evaluation actually resolves; an undemanded entry does not affect the result;
  a wider local check MUST end in the same local refusal, never a different
  canonical exit.
- **Book I §7** — a notation clause. `eval(·, atp)` is shorthand for evaluation
  over the edition's own vector-suite environment, `= ⟨X⟩` asserts
  `normal_form` with that result hash, and the shorthand adds no requirement.
- **Books II and III** — how Book I §7's rule maps onto their schemas: the input
  fields and `expected` carry the prose claim, `id` and `note` do not, and Book
  I's field list is not transported literally.
- **A typo**, `преф лайт` → `префлайт` (§3.4), pre-existing.

The vector suites were regenerated by their generators, and `vectors.json` moved
only in its `book1_anchor` pin, which is hand-declared in
`tests/spec_conformance/generate.py` on purpose: a pin the generator computed
from the file it pins would assert nothing.

## Still open, and deliberately not resolved here

`spec/GOV-anchors.md` pins its normative dependencies as "Book I v0.5.2 / Book II
v0.6.1 / Book III v0.6.1 as anchored in this release", and this candidate makes
that sentence name versions the bundle no longer carries. Two reviewers called
this P0; one called it P3 and argued that leaving it unedited is correct. Both
readings are in ADR-010. It is not resolved by the author, because a document
that governs which bytes are the specification should not be amended by the
author of the bytes it is being asked to govern.

## Release artifacts

None. No tag, no GitHub release, no PyPI upload, no Zenodo deposit, and no
rebuild of the deposited `paper.pdf`.
