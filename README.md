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

The three-input form above is normative since Book I 0.6.0.

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
author/model lineage. Lean 4 checks determinism, totality, the semantic-size
bound and valid-store monotonicity of Book I, and for sigma-resume segmentation
invariance, one state per spent and what an accepted cycle witness establishes. This is strong internal conformance evidence, not
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
python3 tests/book1_claims_test.py              # the claims' witnesses
tools/test-all.sh                               # full repository suite
```

From PyPI (latest release 0.8.0; see "Status by surface" below):

```bash
pip install sigma-glyph
python -m sigma_glyph
```

The wheel contains the Python modules, not the replay corpora; full
re-derivation needs a checkout. The artifact boundary and release procedure are
in [`PUBLISHING.md`](PUBLISHING.md).

### The resume provider, installed

`sigma_provider` is the consumer surface of the resumable kernel
(`impl/sigma_resume.py`, specified by `spec/sigma-resume.md`): build a
computation from a term, run a budgeted segment (PAUSED or a normal form or an
explicit local refusal), resume from a checkpoint, verify a receipt by replay,
verify a cycle witness. It ships from 0.8.0
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

Each paragraph names its authoritative source; when this section and that
source disagree, the source is right. `tools/version_check.py` checks the
distribution heading below against `pyproject.toml`, and the conformance
suite's `spec_version` against Book I's.

### Specification

**Book I 1.0.0** and **sigma-resume 1.0.0**, both STANDARD, the semantics of
Book I 0.6.0 unchanged. A version is the bytes at its release tag, and its
identity Book I §8's SpecAnchor of those bytes; it is adopted when the roadmap
goal "sigma-glyph 1.0" is met, a signed record (AGENTS.md rule 2), not a
heading. The detached registry `spec/ANCHORS.txt` and its bundle headings were
retired on 2026-11-01 ([`history/RETIREMENT-2026-11-ANCHORS.md`](history/RETIREMENT-2026-11-ANCHORS.md)):
Warrant's records and the release tags hold what it held.

### Distribution: 1.0.1

`pyproject.toml` carries **1.0.1**: Book I (`sigma_glyph`) and the resume kernel
and provider (`sigma_resume`, `sigma_provider`), without the retired Book II and
III modules, implementing Book I 1.0.0 and sigma-resume 1.0.0. 1.0.0 is on PyPI
since 2026-11-01, cut from tag `v1.0.0` once goal G1's obligations were accepted
(AGENTS.md rule 5 says by whom and on what evidence). Its provider did not
conform to sigma-resume §5: it normalized a non-canonical cycle witness and
replayed it (Codex's challenge on G1). 1.0.1 refuses those bytes before replay;
the documents are unchanged.
Releases and what was checked about each are in [`PUBLISHING.md`](PUBLISHING.md)
and [`CHANGELOG.md`](CHANGELOG.md); PyPI is right about what it holds.

## The specification

| Document | Status | Owns |
|---|---|---|
| [`Book I — Truth`](spec/book-1-truth.md) ([EN](spec/book-1-truth.en.md)) | Normative | canonical bytes, SHA-256 identity, SKI normal-order reduction, ATP totalization, content resolution, C1 compiler profile |
| [`sigma-resume`](spec/sigma-resume.md) | Normative (draft standard) | budgeted segments, checkpoints, resume, receipts verified by replay, cycle witnesses |

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
A released version is the bytes at its tag, and its identity the SpecAnchor of
those bytes; a specification update is an explicit fork, not a mutable page edit
(Book I §8).

For AI or human review, run the reference suite first and attack one exact
claim/operand boundary. Green tests are baseline evidence, not an independent
gate or governance adoption.

Every RFC 2119 keyword of Book I and sigma-resume (MUST, SHALL, REQUIRED) lies
in some claim's sentence, and `warrant claims check` refuses one that does not
(`coverage`): `.warrant/claims.json` names both documents, the witness files
(`tests/book1_claims_test.py`, `tests/resume_claims_test.py`) and the mutant
harness (`tests/claims_mutants.py`); each claim@1 record quotes one sentence verbatim and
cites the cases that witness it and the mutants that must break them, or says
why it is unbacked. `warrant claims check` refuses a sentence its document no
longer holds, a witness nobody prints or a mutant off its claim; `warrant claims
view` prints them. A backed claim is accepted by the claims checker
(`claim/verifier`), a key bound in `.warrant/v3.json` whose acceptance is a replay
of the witnesses and mutants at one commit; CI re-executes every new acceptance.

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
  reducer while per-redex refusal did not. Its harness is in the deposit and at
  commit `96414ab`.

Prior eras and their historical hashes are preserved in git history and in the
deposited snapshot, not in the default tree: `history/` holds the retirement
ledgers that say what left the surface, why, what was lost and how to retrieve
it with status. Current provenance does not erase superseded semantics; current
admission does not reactivate them.

MIT for implementations; CC BY 4.0 for specification texts.
