# v0.7.0 candidate — frozen bytes

This records exactly which bytes the blind gate in `REVIEWS.md` was run over, so
that a reader can tell whether a verdict applies to the thing in front of them.
If any byte named here changes, the gate does not carry over and this file says
so in one place rather than in a reader's inference.

**Nothing here is adopted.** The `v0.7.0` section of `spec/ANCHORS.txt` is marked
CANDIDATE, `tools/anchor_governance.py status` does not list it, and the anchor
set below carries no signature. Adoption is a threshold warrant, not a file.

## Revision

| | |
| --- | --- |
| branch | `spec/book1-v0.7.0-candidate` (draft PR #35) |
| frozen commit | `1c2b6ca42cb95cdc035fc887cd0587a5758862d7` |
| adopted release this descends from | `v0.6.7` at `16a1355` |
| `master` at freeze time | `f07edad` |

The frozen commit is where the candidate bytes were written, and they have not
moved since: every commit after it on this branch leaves every anchored file
byte-identical, which `git diff 1c2b6ca HEAD -- spec tests` reports as empty.
Later commits carry the two papers, this directory, `tools/paper_claims.py`,
`tools/candidate_gate.py`, `tools/anchor_governance.py`, `tools/test-all.sh` and
`.github/workflows/ci.yml` — none of them anchored, none of them shown to a
reviewer as normative.

The gate itself re-hashes every file listed below immediately before sending
anything, and refuses if one has moved (`tools/candidate_gate.py`). The digests,
not the commit, are what a verdict is attached to.

## The anchor set

`gates/v0.7.0-candidate/anchor-set.json` — 1410 bytes, JCS-canonical, no trailing
newline.

    SHA-256  0bac2605fd46f0b7fdadf7b06cce7738445d75f713632754fe2e718e4935726e

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

| Path | v0.6.7 (adopted) | v0.7.0 (candidate) |
| --- | --- | --- |
| `spec/book-1-truth.md` | `a98a03bd…` | **`a97fc637…`** |
| `spec/book-2-navigation.md` | `7733dfb0…` | **`8b704112…`** |
| `spec/book-3-federation.md` | `e7bdbac8…` | **`0db4007d…`** |
| `tests/spec_conformance/vectors.json` | `08116edb…` | **`55abdc42…`** |
| `tests/spec_conformance/wave_vectors.json` | `9ef44d02…` | **`904395f2…`** |
| `tests/spec_conformance/federation_vectors.json` | `310296a8…` | **`392f74ef…`** |
| `tests/spec_conformance/governance_vectors.json` | `14ead59a…` | `14ead59a…` |
| `spec/GOV-anchors.md` | `59bbb117…` | `59bbb117…` |
| `spec/LORE.md` | `9bd7977c…` | `9bd7977c…` |
| `spec/appendix-a-complexity.md` | `2df9194b…` | `2df9194b…` |

Six of ten move. Full values are in `spec/ANCHORS.txt` and in the blob;
`python3 tools/verify_anchors.py` checks them against the files.

## Raw SHA-256 of the frozen source files

The anchors above are NodeHashes, not file digests; these are the file digests, so
a reader with the files and no Book I implementation can still check them.

    3a0a6e56fea9f6542cefda206e6bb366ef46f328da5ee69ca9bfba154f1196c1  spec/book-1-truth.md
    bc9f87912689342e606621c1fa7bcc3510aba276b7d475e250f6e442ce0caf4c  spec/book-1-truth.en.md
    251e5465baad3c2cf70a2b116bd26018c9a7bb49abe73b1fc86962e52fadfb97  spec/book-2-navigation.md
    9bafd3dc3b79c6c54bb4dff7b6683d357e4ea77f0d852f0d130a9605d5d77007  spec/book-3-federation.md
    e35954f7b0a982e0af3e84a8d9f1dad02f3ffbbb61c2e2c7549adb1813bac9b2  tests/spec_conformance/vectors.json
    0928cba4103784588c3b3f00b0eddc5576a3cd5bc4054a55df6df5cd3e458381  tests/spec_conformance/wave_vectors.json
    a6ade79884808c88b951567425b2ec012cee496e6b043740eec4771f923fc07b  tests/spec_conformance/federation_vectors.json
    68f96177d1975cf0e9a2f7881330173d71734f8b17a844449f22b7eeec50475b  tests/spec_conformance/governance_vectors.json
    f7ca204b3773ea1b6b5e288fa59240c24e9b14f49fa3cb6ba8db1a405b5ae8c3  spec/GOV-anchors.md
    07ddd994c397ee253065cf62636f51a99ba638afa18344da43afbf842f1fe4ec  spec/LORE.md
    9e35f22bffe40d0442b20ed98e8a9f7880de96bc325373d47e3f6c00865e94f1  spec/appendix-a-complexity.md

`spec/book-1-truth.en.md` is listed because the gate reads it, not because it is
anchored: the English rendering is informative, and Book I §7 says the Ukrainian
text and the vector suite decide.

## What changed against the adopted release

`git diff v0.6.7 4969fbc -- spec tests/spec_conformance` is 473 insertions and 29
deletions across twelve files. Anchored, and therefore normative:

- **`spec/book-1-truth.md` 0.5.2 → 0.6.0** (+30/-8) — §3.4 the interface over
  three inputs, the receipt and the named two-value compatibility profile; §3.4
  size as a semantic measure and what the bound is not; §3.5 the content
  environment as a CAS (`NodeHash(bytes) = key`, foreign-key bytes MUST NOT
  execute), determinism over the demanded environment, and extension bounded to
  the unresolved outcome; §3.6 admission as a required deployment boundary and
  out-of-domain input; §5.1 the ASCII-byte convention stated rather than implied;
  §7 one arbiter and the five normative record fields.
- **`spec/book-2-navigation.md` and `spec/book-3-federation.md` 0.6.1 → 0.7.0**
  (+4/-4 each) — "the oracle wins" replaced by the one arbitration rule all three
  Books now share, and Book III's attribution of that rule to Book I §7 removed,
  because §7 of this edition says something else.
- **The four vector suites** — regenerated by their generators, not hand-edited;
  `spec_version` set to the Book each conforms to, which closes the two
  discrepancies `tools/version_check.py` carried by name.

Unanchored and therefore informative, but in the same diff: `spec/ANCHORS.txt`
(the CANDIDATE section itself), `spec/GLOSSARY.md`, `spec/IMPLEMENTING.md`,
`spec/VERSIONS.md`, `spec/book-1-truth.en.md` and
`tests/spec_conformance/generate.py`.

## Known open question, carried into the gate

`spec/GOV-anchors.md` pins its normative dependencies as "Book I v0.5.2 / Book II
v0.6.1 / Book III v0.6.1 as anchored in this release". Its own bytes do not move
in this candidate, so after adoption an unchanged GOV-anchors would name Book
versions that are no longer current. GOV-anchors depends on the Books only for
`NodeHash`, which this candidate does not touch, so the pinned *semantics* hold —
but the sentence goes stale, and §0 makes re-pinning a dependency a breaking
change to a STANDARD. This candidate deliberately does not edit it: a governance
document editing itself alongside the content it governs is the shape this
project refuses elsewhere. It is put in front of the gate as a question, not
resolved by the author.

## Release artifacts

None. No tag, no GitHub release, no PyPI upload, no Zenodo deposit, and no
rebuild of the deposited `paper.pdf`. The paper source at this commit is
`papers/one-integer-for-work-and-memory/paper.md`,
SHA-256 `dbaed29319cfdc9c3dae9ab04f517183831136cff2dfe7a305c3761f7978bc36`;
the committed `paper.pdf` remains the deposited artifact of the *previous*
version (MD5 `f07e9c3a6301cf2be34771746d7e5c63`, DOI 10.5281/zenodo.22069651)
and is untouched.
