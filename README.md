# Σ-GLYPH

**A claim that arrives with a check attached is worth exactly as much as your
ability to run the check yourself. Usually you can't.**

Re-executing someone else's check means running their code, on your machine, for
an unknown length of time — so in practice people read the verdict instead of
reproducing it. And a check whose author can quietly change what it covers is
indistinguishable, from the outside, from one whose scope is fixed. Σ-GLYPH makes
a check an *object* rather than a program you have to trust: a computation is
addressed by the hash of itself, so what was checked is pinned by its own identity
and cannot be re-scoped afterwards, and evaluating it is deterministic,
integer-only and total, with work and **peak semantic materialization** priced up
front.

```
(result_term, atp_spent) = eval_hash(term_hash, atp, content_store)
```

Two machines given the same `term_hash`, the same uint32 budget and the same
valid content for every demanded hash return the same result term and spend — bit
for bit, with no float, clock or network in reduction. Missing content is itself
an input and yields `Unresolved Reference`; local resource faults remain outside
the canonical result. The current API does not return the exit kind separately,
so a result hash alone cannot distinguish a normal form equal to the
ATP-exhausted term from an actual exhausted exit.

> **Resolved in v0.7.0 (adopted 2026-08-30 by warrant `0e634c17…`).** Book I 0.6.0 §3.4 now
> states `eval(term_hash, atp: uint32, env) → Receipt` in normative, anchored bytes, and the
> Receipt carries the exit. The paragraphs below are kept as the record of the defect as it
> stood on 2026-08-27; the sentence in them about the two-argument form being still anchored
> was true then and is superseded by the section "Current: v0.7.0" further down.
>
> **Correction (2026-08-27).** This line used to read `eval(term_hash, atp)`, and
> the paragraph under it promised that the budget and the term hash were enough.
> They are not: the evaluator has a third input. A node that holds the referenced
> bytes reaches a normal form where a node that does not reaches
> `DISSONANCE(Unresolved Reference)` — same term, same budget, two conforming
> implementations, two different canonical results. Availability had become part
> of the semantics without being written down, and the genesis intrinsics of
> Book I §5.1 are the one island carved out of it.
>
> This is a defect in the claim, not a discovery about the machine: the Lean
> model has always been `evalHash (h) (atp) (st)`, the Python oracle has always
> been `eval_hash(h, atp, store, …)`, and Book I §3.5 has always made an
> unresolved demand a canonical result. What was missing is the third argument in
> the sentence people read.
>
> Found by an external review of the deposited paper
> ([`reviews/2026-08-codex-store-parameter.md`](reviews/2026-08-codex-store-parameter.md)),
> registered without disposition. **Book I §3.4 at that date still printed the two-argument
> form in normative, anchored bytes**; changing it was a specification edit with
> its own candidate and gate (ADR-010, `gates/v0.7.0-candidate/`), which has since happened. The resulting
> `evalHash_mono` / `evalHash_stable` theorems are now guarded on
> `master`: under a valid store extension, only an `Unresolved` outcome may
> change; a normal form or exhaustion is stable. Their live-oracle bridge grows
> and shrinks every evaluation fixture rather than treating the Lean model as
> sufficient evidence about the Python implementation.

**What that is for.** Re-running a *stranger's* reason.
[Warrant](https://github.com/s0fractal/warrant) records why an AI agent was
allowed to do something; a reason there can be a Σ-GLYPH term, so a reviewer
re-executes it on their own laptop and gets the same verdict — instead of
trusting the log of whoever wrote it. The ATP theorem bounds semantic work and
materialized-node count; affordability additionally requires the verifier to
apply its own admission limit before reading the term or store.

That claim is about the *semantics*: a term's canonical result and its ATP cost
are bounded and deterministic. It is not a promise that any given binary is
immune to its own resource limits — Book I §3.6 keeps local faults deliberately
outside the canonical outcomes, and each implementation still has to refuse
cleanly rather than fall over. Until v0.6.7 the Rust binary did not: hostile
input aborted it with a stack overflow. It now fences and refuses; see
`tests/book1_resource_fence.py`.

Three implementations from one author/model lineage agree on **all 49**
conformance vectors — Python, Rust and
[`warrant-go`](https://github.com/s0fractal/warrant), across
serialization, byte-rejection and evaluation alike — and the evaluator's
determinism, totality and semantic-size bound are machine-checked theorems in Lean 4
([`proofs/`](proofs/)), not prose. A randomized differential fuzzer runs all
three against each other on every push, and `tools/x1_cross_repo.sh` runs this
repo against warrant's HEAD rather than a pinned snapshot.

How this repo relates to its siblings — which links are CI-gated contracts and
which are only proposals — is indexed in the
[ecosystem relationship map](https://github.com/s0fractal/protocol-ecosystem).

**Paper:** *One Integer for Work and Memory* — Zenodo DOI
[10.5281/zenodo.22069651](https://doi.org/10.5281/zenodo.22069651), archived with a snapshot of this
repository at commit [`7ecba6a`](https://github.com/s0fractal/sigma-glyph/tree/7ecba6ab283c89111a76a3a1edeba57339b4443c).
Deposited, not peer reviewed: see [`papers/`](papers/) for what that does and does
not mean.

**Experiment:** *Does One Integer Still Price Work and Memory in Parallel?* — Zenodo
DOI [10.5281/zenodo.22073568](https://doi.org/10.5281/zenodo.22073568). A
preregistered measurement of whether the paper's bound survives confluent parallel
reduction: it does, while Book I's per-redex refusal discipline does not, so a
parallel machine must choose the granularity of refusal explicitly. The
preregistration was committed before the reducer existed and is deposited unedited
alongside the result. See [`experiments/exp-004/`](experiments/exp-004/).

**Where the failures have actually been.** Not in the mathematics. Every vector
`tests/proof_guard_test.py` now rejects is an attack on the *guard* rather than on
the kernel — a theorem hidden from the registry by a one-line `namespace`, a scope
read from a field the guard itself edits, a subdirectory file that no textual layer
ever opened, a statement weakened while its name stayed the same. The Lean kernel
was never the thing under attack, because it never had to be: the cheaper target
was always the apparatus deciding what the proofs were taken to cover. Whether that
generalises past this repository is not something one codebase can settle;
[`proofs/README.md`](proofs/README.md) states, front by front, what is
kernel-checked and what is merely trusted.

```bash
python3 impl/sigma_glyph.py                        # Book I -> ALL PASS
python3 tests/spec_conformance/run_reference.py    # 49/49 vectors
```

Or from PyPI, where **0.6.7** is the current release:

```bash
pip install sigma-glyph
python -m sigma_glyph        # Book I   -> ALL PASS
python -m sigma_wave         # Book II  -> WAVE: ALL PASS … SKIPPED: recorded-vector replay
python -m sigma_federation   # Book III -> FEDERATION: ALL PASS … SKIPPED: …
```

The wheel ships the three modules and not the corpora, so an installed copy
announces the recorded-vector replays as an explicit `SKIP` with the reason.
The property checks run either way; **full re-derivation still needs the
checkout** and `tools/test-all.sh`. See [PUBLISHING.md](PUBLISHING.md) for what
the release gate does and does not prove.

---

### Current: v0.7.0

**v0.7.0** (2026-08-30) is the adopted repository bundle. PyPI remains at
**0.6.7** until a separate distribution release. The governed anchor set is
`abf10f2a…adf59`, authorised by threshold warrant `0e634c17…46e1` with two
distinct roster signatures. Book I is 0.6.0; Books II and III are 0.7.0. The
release makes evaluation explicitly a relation over a term hash, a uint32 budget
and a content environment; returns a receipt carrying exit, result hash and ATP
spent; removes reference-oracle precedence; anchors all three suite schemas; and
enforces one Pin per NodeHash at annotation-profile admission.

### Previous: v0.6.7

**v0.6.7** (2026-07-31) is the adopted bundle and the version on PyPI. *Adopted*
means this project's own governance ran — a 2-of-3 threshold warrant signed by its
own roster — and nothing about anyone outside it; `SECURITY-ASSUMPTIONS.md` SA-5
records that of the five thresholds exercised so far, three were signed from a
single host, which is one custody rather than a quorum. Against
v0.6.6 exactly one anchored file changed —
`tests/spec_conformance/governance_vectors.json`, re-signed under Warrant SPEC
v0.4's domain-separated message (`"warrant-sig-v1:" || WarrantID_raw`), which
this repository's governance verifier now requires. Books I–III, `LORE.md`,
`appendix-a-complexity.md` and `GOV-anchors.md` are byte-identical to their
v0.6.6 anchors. Everything else in the release is tooling: one signing path
instead of eight, resource fences in the Rust binary, and self-tests that no
longer exit 0 after printing failures.

Three Books (DRAFT STANDARD) + a constitution now at **STANDARD**. Hash-thunk
evaluation with size-priced ATP (Book I), field-level wave pins with absent-wave
semantics (Book II), selection-only annotation federation as a Warrant v0.3
profile (Book III: jurisdictions, machine-readable selection policies, permanent
divergence by design), and **governed Specification Anchors**
([`spec/GOV-anchors.md`](spec/GOV-anchors.md) v1.0.2, STANDARD: releases adopted
by 2-of-3 threshold warrants, ADR-007; promoted DRAFT→STANDARD through a second
3-family gate). Machine-readable conformance suites for all Books
([`tests/spec_conformance/`](tests/spec_conformance/)).

Beyond the compute core there is a second, **optional** layer: a wave/coordinate
navigation view for finding related terms. It is strictly a *view over* identity
and never part of it — ignore it entirely and Book I still holds. The names, the
cosmology, and why FALSE sits at 270° live in [`spec/LORE.md`](spec/LORE.md):
non-normative, and deliberately unhurried.


**Why these three properties together** — determinism, content addressing, and a
single Lean-proven bound over work and semantic materialization — is in
[`WHY-THESE-THREE.md`](WHY-THESE-THREE.md). Short version: they are what makes it
possible to bound a proof sent by a stranger. Local admission, a valid content
store and ordinary implementation fences remain required.

## The Three Books

| Document | Status | Contract between |
|---|---|---|
| [`spec/book-1-truth.md`](spec/book-1-truth.md) (informative [EN](spec/book-1-truth.en.md)) | Normative | **nodes** — everything two independent nodes need to agree on a result hash: canonical bytes, SHA-256 identity, SKI normal-order reduction, ATP totalization, resolution contract, canonical compiler profile C1 |
| [`spec/book-2-navigation.md`](spec/book-2-navigation.md) | Normative | **nodes** (annotation layer) — WaveVectorQ as detached annotation, pinned LUT (SHA-256 arbitrated), `interfere()` with the Law of Left Dominance, coordinate pins, Mass, CP-24 |
| [`spec/book-3-federation.md`](spec/book-3-federation.md) | Normative | **jurisdictions** — annotation assertions as Warrant v0.3 records, machine-readable selection policies, ConflictSets that clients never merge, AnnotationViewID + assertion-set commitments, ten conformance criteria |
| [`spec/GLOSSARY.md`](spec/GLOSSARY.md) | Non-normative | **readers of the papers** — one name per thing: what `size`, ATP, "work", "memory" and "materialization" mean here, what they do not mean, and the refinement gap between the proved semantic quantity and a process's actual resource use |
| [`spec/VERSIONS.md`](spec/VERSIONS.md) | Non-normative | **anyone reading a version number** — six numbers in three schemes, what each governs, why a Book at 0.5.2 inside a v0.6.x bundle is correct, and two suite versions that do not agree and are governed to fix. Checked by `tools/version_check.py` |
| [`spec/IMPLEMENTING.md`](spec/IMPLEMENTING.md) | Non-normative | **implementers** — that Book I is implementable from Book I: derive the genesis atoms yourself in three lines, settle the one convention the text leaves to inference, and see the two places the Book still points at our code. Checked by `tools/spec_audit.py` on every CI run |
| [`spec/LORE.md`](spec/LORE.md) | Non-normative | **humans & agents** — why the glyphs are named, why FALSE sits at 270°, why the wave left the hash, and what deliberately isn't here yet |
| [`spec/GOV-anchors.md`](spec/GOV-anchors.md) | Normative (meta) | **the spec itself** — releases as anchor-set blobs adopted by threshold warrants (2-of-3), policy lineage, succession for model actors, fork legitimacy; deliberately not a Book: the constitution must not judge itself |

Core invariants, in one breath: **hash is identity; phase is a coordinate; wave is a view; aggregate is never a field; ATP prices work AND semantic materialized size (`size − 1 ≤ spent`); dead branches are never fetched; canonical failures are deterministic, local faults are not canonical.**

## Reference implementation

`impl/sigma_glyph.py` — Book I: serialization, validation, CAS, the v0.5 hash-thunk evaluator (lazy left-spine, size-priced ATP, genesis intrinsic), C1 λ→SKI compiler. `impl/sigma_wave.py` — Book II: arbiter-checked LUT, interfere() with entropy–coherence coupling. `impl/sigma_federation.py` + `impl-go/` — Book III (Python and Go implementations). `impl-rs/` — a from-scratch **Rust** implementation of Book I (including SHA-256, no external crates) that replays the same oracle-generated vectors byte-exact. All were produced within one author/model lineage.

```bash
python3 impl/sigma_glyph.py         # expected: ALL PASS (Book I)
python3 impl/sigma_wave.py          # expected: WAVE: ALL PASS (Book II)
python3 impl/sigma_federation.py    # expected: FEDERATION: ALL PASS (Book III)
(cd impl-rs && cargo build --release) && \
  ./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json  # RUST-CONFORMANCE: ALL PASS (49/49)
```

Book I now has three implementations from one author/model lineage that agree on every vector — the Python oracle, warrant-go's native evaluator (via `ski@v1`), and Rust — plus a Lean 4 mechanization of the evaluator's determinism/totality, semantic-size bound and valid-store monotonicity (`proofs/EvalMachine.lean`). `impl-go` in *this* repo implements Books II and III only; its Book I "vector" is an echoed constant and says so out loud (`VACUOUS FV-BOOK-I-UNREACHABLE`). No external implementation exists yet.

## For AI reviewers

This repository is deliberately structured for multi-model review. If you are a model asked to critique this spec, read [`reviews/README.md`](reviews/README.md) first — it defines the protocol, and `reviews/` contains prior reviews (Claude, Codex, Kimi) so you don't rediscover settled points.

Fastest way to be useful: **run the reference implementation before critiquing the prose.** Two of three prior reviewers filed "ambiguities" that were already resolved by executable test vectors.

## Specification Anchors

Every published spec version is a citizen of its own system:
`SpecAnchor = NodeHash(LITERAL, atom = SHA-256(document_bytes))` — published detached in [`spec/ANCHORS.txt`](spec/ANCHORS.txt). A spec update is formally a fork with an explicit ancestor.

## Provenance

`archive/` preserves prior eras verbatim, including Era-1 (v0.2.12 "Titanium Monolith"), whose genesis forge method was reconstructed by brute force in 2026. Old hashes remain valid artifacts of their era. Dirty history is provenance, not shame.

## License

MIT for the implementation; CC-BY-4.0 for the specification texts.

---
*Part of the s0fractal mycelium federation (trinity / myc.md / OMEGA / liquid).*
