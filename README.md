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
defect was found in external review and resolved in v0.7.0 through ADR-010.

## What it establishes

Σ-GLYPH owns two things: **Book I** (deterministic reduction, content addressing,
one ATP budget for work and memory) and **sigma-resume** (budgeted segments,
checkpoints, resume and verification by replay). Everything else this
repository once carried (Books II and III, the GOV-anchors governance, the
Warrant 0.x apparatus, gate and review material) was retired on 2026-10-31;
[`history/RETIREMENT-2026-10-ECHO.md`](history/RETIREMENT-2026-10-ECHO.md) says
what left, why and where its bytes are.

Two implementations agree on all 49 Book I conformance vectors and on generated
terms: the Python reference and a from-scratch Rust implementation, from one
author/model lineage (a third, Warrant 0.x's Go evaluator, left with Warrant
0.x). Lean 4 checks determinism, totality, the semantic-size bound and
valid-store monotonicity. This is strong internal conformance evidence, not
independent custody, outside adoption, semantic truth or immunity of a binary to
local faults.

The cheapest attacks have repeatedly targeted the apparatus around the kernel:
hidden theorem scope, weakened statements, omitted files and guards that stopped
observing their subjects. [`proofs/README.md`](proofs/README.md) separates what
the Lean kernel checks from what bridges, registries and generated inputs must
still be trusted to supply.

## Run it

From a checkout:

```bash
python3 impl/sigma_glyph.py                     # Book I
python3 tests/spec_conformance/run_reference.py # the conformance vectors
python3 tests/resume_test.py                    # sigma-resume
tools/test-all.sh                               # full repository suite
```

From PyPI (latest release 0.8.0; see "Status by surface" below):

```bash
pip install sigma-glyph
python -m sigma_glyph
```

The wheel contains the Python modules, not the replay corpora; full
re-derivation needs a checkout. The artifact boundary and release procedure are
in [`PUBLISHING.md`](PUBLISHING.md). The published 0.7.0 and 0.8.0 still ship
`sigma_wave` and `sigma_federation`; the next distribution will not.

### The resume provider, installed

`sigma_provider` is the consumer surface of the DRAFT resumable kernel
(`impl/sigma_resume.py`, `spec/drafts/sigma-resume-draft-1.md`): build a
computation from a term, run a budgeted segment (PAUSED or a normal form or an
explicit local refusal), resume from a checkpoint, verify a receipt by replay,
verify a cycle witness. It is not normative Book I. It ships from 0.8.0
(`pip install sigma-glyph==0.8.0`), or build the wheel from a commit and install
that file.

```bash
pip wheel --no-deps -w wheelhouse "git+https://github.com/s0fractal/sigma-glyph@<commit>"
pip install wheelhouse/sigma_glyph-*.whl
python -m sigma_provider                          # self-test
echo '{"sigma_provider":1,"op":"term","args":{"expr":"S K K (K I)"}}' | python -m sigma_provider serve
```

The library and the one-request-per-process protocol are documented in the
module's docstring. To continue someone else's checkpoint, use `resume`, which
replays it from your own root first; raw `advance` trusts its checkpoint. A consumer decides which provider bytes it accepts:
`sigma_provider.identity_of(...)` names them, and a provider reporting its own
identity grants nothing.

## Status by surface

Several things move separately here, and their labels are not interchangeable.
Each paragraph names its authoritative source; when this section and that
source disagree, the source is right. `tools/version_check.py` checks the two
version headings below against `spec/ANCHORS.txt` and `pyproject.toml`.

### Adopted bundle: v0.7.0

**v0.7.0** (2026-08-30) is the newest adopted anchor set in
[`spec/ANCHORS.txt`](spec/ANCHORS.txt): Book I 0.6.0, Books II and III 0.7.0,
GOV-anchors 1.0.2. It was adopted by threshold warrant `0e634c17…46e1` (2-of-3,
two distinct roster keys) over anchor set `abf10f2a…adf59`, recorded in the
Warrant 0.x store `.warrants/`, retired 2026-10-31 and kept at commit `96414ab`.
The retired documents of the bundle are verified there by
`tools/verify_anchors.py`. The bundle makes the content environment and receipt explicit,
removes reference-oracle precedence, anchors all three suite schemas and admits
at most one Pin per NodeHash in the annotation profile. Adoption records this
project's own governance act; it does not claim outside review, custody or use.
`SECURITY-ASSUMPTIONS.md` SA-5 records what custody each threshold act has
actually had.

A bundle heading is a governance label, not a git tag and not a release. They
coincide here only because the 0.7.0 distribution was cut from this bundle: the
`v0.7.0` tag, GitHub release and PyPI upload are release acts of 2026-09-17,
not the adoption of 2026-08-30. Release history and exact changed anchors
belong to [`CHANGELOG.md`](CHANGELOG.md), `spec/ANCHORS.txt` and
[`spec/VERSIONS.md`](spec/VERSIONS.md).

### Distribution: 0.9.0.dev0

`pyproject.toml` carries **0.9.0.dev0**: the next distribution ships Book I
(`sigma_glyph`) and the resume kernel and provider (`sigma_resume`,
`sigma_provider`), without the retired Book II and III modules. Nothing is
published until a GitHub Release runs `.github/workflows/publish.yml`.

`sigma-glyph` **0.8.0** is the latest PyPI release: the first that ships
`sigma_resume` and `sigma_provider` (the checked `resume`), next to the three
Books' modules. PyPI is right about what it holds.

`sigma-glyph` **0.7.0** (2026-09-17), the release before it, was built from git
tag `v0.7.0` (commit `9d10bbc…`) by `.github/workflows/publish.yml`. It packages the adopted v0.7.0 bundle
(Book I 0.6.0, Books II and III 0.7.0), so an installed copy is no longer one
bundle behind — the first release for which that is true since the bundle was
adopted. The published wheel is `c9ee4768…6276a` and the sdist `5ad36077…bcf8`;
both are byte-identical to the artifacts the release run built, and the three
installed modules are byte-identical to `impl/` at the tag.
[`PUBLISHING.md`](PUBLISHING.md) owns the release procedure; if it and PyPI
disagree, PyPI is right.

## The specification

| Document | Status | Owns |
|---|---|---|
| [`Book I — Truth`](spec/book-1-truth.md) ([EN](spec/book-1-truth.en.md)) | Normative | canonical bytes, SHA-256 identity, SKI normal-order reduction, ATP totalization, content resolution, C1 compiler profile |
| [`sigma-resume`](spec/drafts/sigma-resume-draft-1.md) | Draft | budgeted segments, checkpoints, resume, receipts verified by replay, cycle witnesses |

[`spec/GLOSSARY.md`](spec/GLOSSARY.md) fixes the local meaning of work, size,
memory and materialization; [`WHY-THESE-THREE.md`](WHY-THESE-THREE.md) explains
why determinism, addressing and one semantic bound are combined.

## Implement and verify

`impl/sigma_glyph.py` is the Book I Python reference and `impl/sigma_resume.py`
the resumable kernel. `impl-rs/` independently implements Book I (and
`impl-rs/wasm-resume/` the resume kernel) within the same author/model lineage.

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

For AI or human review, run the reference suite first and attack one exact
claim/operand boundary. Green tests are baseline evidence, not an independent
gate or governance adoption.

Reviews are records, not prose: `.warrant/` is this repository's Warrant 3
store (`warrant-graph`, pinned in `.github/warrant-requirements.txt`). A pull
request's head is a `pr-head@1` version; the reviewer named by
`.warrant/v3.json` (`pr/acceptor`) accepts it or files `finding@1` challenges
against it, signed with its own key. `warrant status` and `warrant review view`
read them. The owner merges (AGENTS.md rule 5).

## Published evidence

- *One Integer for Semantic Work and Materialization* —
  [Zenodo 10.5281/zenodo.22646920](https://doi.org/10.5281/zenodo.22646920)
  (v2, 2026-09-07, repository snapshot `47cf57d`; concept DOI
  [10.5281/zenodo.22069650](https://doi.org/10.5281/zenodo.22069650)); v1 is
  [10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651) (snapshot
  `7ecba6a`). Deposited, not peer reviewed.
- *Does One Integer Still Price Work and Memory in Parallel?* —
  [Zenodo 10.5281/zenodo.22073568](https://doi.org/10.5281/zenodo.22073568), a
  preregistered experiment: the aggregate bound survived the measured parallel
  reducer while per-redex refusal did not. Its harness (`experiments/exp-004/`)
  is kept at commit `96414ab` and in the deposit.

Prior eras and their historical hashes are preserved in git history and in the
deposited snapshot, not in the default tree: `history/` holds the retirement
ledgers that say what left the surface, why, what was lost and how to retrieve
it with status. Current provenance does not erase superseded semantics; current
admission does not reactivate them.

MIT for implementations; CC BY 4.0 for specification texts.
