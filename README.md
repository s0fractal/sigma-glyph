# Σ-GLYPH

**A claim with an executable check is worth exactly as much as your ability to
run the check yourself. Usually you cannot safely run a stranger's program.**

Σ-GLYPH makes a check a content-addressed object rather than mutable code you
must trust. Evaluation is deterministic, integer-only and total over its
canonical outcomes; one ATP budget prices both semantic work and peak semantic
materialization.

```text
Receipt = eval(term_hash, atp: uint32, content_environment)
```

Two machines given the same term hash, budget and valid demanded content return
the same exit, result hash and ATP spent. Missing demanded content is an explicit
input and yields `Unresolved Reference`; local process/resource faults stay
outside canonical outcomes. Implementations must apply local admission limits
before reading untrusted terms or stores.

The three-input form above is normative in Book I 0.6.0. Earlier README text
incorrectly omitted the content environment even though the Lean model, Python
implementation and unresolved-reference semantics already depended on it. The
defect was found in external review and resolved in v0.7.0 through ADR-010; the
dated finding remains at
[`reviews/2026-08-codex-store-parameter.md`](reviews/2026-08-codex-store-parameter.md).

## What it establishes

Σ-GLYPH owns deterministic reduction, content addressing and bounded replay.
[Warrant](https://github.com/s0fractal/warrant) owns decision records,
provenance, authority and settlement. A Warrant `ski@v1` reason uses the frozen
Book I v0.5 evaluator bytes; Sigma-Glyph HEAD is a differential target, not a
silent replacement for that runtime.

Three implementations from one author/model lineage agree on all 49 Book I
conformance vectors: the Python reference, Warrant's native Go evaluator and a
from-scratch Rust implementation. Lean 4 checks determinism, totality, the
semantic-size bound and valid-store monotonicity. This is strong internal
conformance evidence, not independent custody, outside adoption, semantic truth
or immunity of a binary to local faults.

The cheapest attacks have repeatedly targeted the apparatus around the kernel:
hidden theorem scope, weakened statements, omitted files and guards that stopped
observing their subjects. [`proofs/README.md`](proofs/README.md) separates what
the Lean kernel checks from what bridges, registries and generated inputs must
still be trusted to supply.

## Run it

From a checkout:

```bash
python3 impl/sigma_glyph.py                     # Book I
python3 tests/spec_conformance/run_reference.py # 49/49 vectors
python3 impl/sigma_wave.py                      # Book II
python3 impl/sigma_federation.py                # Book III
tools/test-all.sh                               # full repository suite
```

From PyPI, where `0.6.7` is the current distribution release:

```bash
pip install sigma-glyph
python -m sigma_glyph
python -m sigma_wave
python -m sigma_federation
```

The wheel contains the three Python modules, not the replay corpora. Installed
Book II/III self-tests therefore report recorded-vector replay as `SKIP` while
still running their property checks. Full re-derivation needs a checkout. The
artifact boundary and release procedure are in [`PUBLISHING.md`](PUBLISHING.md).

### Current: v0.7.0

**v0.7.0** (2026-08-30) is the adopted repository bundle. PyPI remains at
**0.6.7** until a separate distribution release. Its governed anchor set is
`abf10f2a…adf59`, authorised by threshold warrant `0e634c17…46e1` with two
distinct roster signatures. Book I is 0.6.0; Books II and III are 0.7.0.

The bundle makes the content environment and receipt explicit, removes
reference-oracle precedence, anchors all three suite schemas and admits at most
one Pin per NodeHash in the annotation profile. Adoption records this project's
own governance act; it does not claim outside review, custody or use.

### Previous: v0.6.7

**v0.6.7** (2026-07-31) is both the previous adopted bundle and the current PyPI
release. Release history and exact changed anchors belong to
[`CHANGELOG.md`](CHANGELOG.md), [`spec/ANCHORS.txt`](spec/ANCHORS.txt) and
[`spec/VERSIONS.md`](spec/VERSIONS.md). `SECURITY-ASSUMPTIONS.md` records the
single-host custody limits of earlier threshold acts.

## The Three Books

| Document | Status | Owns |
|---|---|---|
| [`Book I — Truth`](spec/book-1-truth.md) ([EN](spec/book-1-truth.en.md)) | Normative | canonical bytes, SHA-256 identity, SKI normal-order reduction, ATP totalization, content resolution, C1 compiler profile |
| [`Book II — Navigation`](spec/book-2-navigation.md) | Normative | detached WaveVectorQ annotations, pinned LUT, interference and coordinate rules; never identity |
| [`Book III — Federation`](spec/book-3-federation.md) | Normative | Warrant-backed annotation assertions, selection policies and permanent jurisdictional divergence |
| [`GOV anchors`](spec/GOV-anchors.md) | Normative meta | adopted anchor sets, threshold warrants, succession and fork legitimacy |

The wave layer is an optional view over identity. Ignore Books II and III and
Book I still holds. [`spec/GLOSSARY.md`](spec/GLOSSARY.md) fixes the local meaning
of work, size, memory and materialization;
[`WHY-THESE-THREE.md`](WHY-THESE-THREE.md) explains why determinism, addressing
and one semantic bound are combined; [`spec/LORE.md`](spec/LORE.md) is explicitly
non-normative.

## Implement and verify

`impl/sigma_glyph.py` is the Book I Python reference. `impl/sigma_wave.py` is
Book II. Book III has Python and Go implementations. `impl-rs/` independently
implements Book I within the same author/model lineage; `impl-go/` in this repo
implements Books II and III only.

```bash
(cd impl-rs && cargo build --release)
./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json
python3 proofs/proof_guard.py
python3 tools/spec_audit.py
python3 tools/version_check.py
```

Implementation guidance is in [`spec/IMPLEMENTING.md`](spec/IMPLEMENTING.md).
Every adopted specification byte set is detached in
[`spec/ANCHORS.txt`](spec/ANCHORS.txt); a specification update is an explicit
fork, not a mutable page edit.

For AI or human review, read [`reviews/README.md`](reviews/README.md), run the
reference suite first, and attack one exact claim/operand boundary. Green tests
are baseline evidence, not an independent gate or governance adoption.

## Published evidence

- *One Integer for Work and Memory* —
  [Zenodo 10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651),
  deposited with repository snapshot `7ecba6a`; deposited, not peer reviewed.
- *Does One Integer Still Price Work and Memory in Parallel?* —
  [Zenodo 10.5281/zenodo.22073568](https://doi.org/10.5281/zenodo.22073568), a
  preregistered experiment: the aggregate bound survived the measured parallel
  reducer while per-redex refusal did not. See [`experiments/exp-004/`](experiments/exp-004/).

`archive/` preserves prior eras and their historical hashes. Current provenance
does not erase superseded semantics; current admission does not reactivate them.

MIT for implementations; CC BY 4.0 for specification texts.
