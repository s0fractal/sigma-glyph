# Σ-GLYPH

**A portable check engine: send a computation by hash, get the same answer on any
machine, with work and memory bounded up front.**

```
result_hash = eval(term_hash, atp)     // deterministic, integer-only, total
```

Two independent machines given the same `term_hash` and the same budget return
the same `result_hash` — bit for bit, with no shared runtime, no float, no clock,
no network. If the budget runs out, that outcome is deterministic too. No input
hangs it, and no input makes one implementation disagree with another.

**Why anyone needs that.** It is what lets you re-run a *stranger's* reason.
[Warrant](https://github.com/s0fractal/warrant) records why an AI agent was
allowed to do something; a reason there can be a Σ-GLYPH term, so a reviewer
re-executes it on their own laptop and gets the same verdict — instead of
trusting the log of whoever wrote it. Bounding work *and* memory up front is what
makes running a stranger's computation safe by construction.

That claim is about the *semantics*: a term's canonical result and its ATP cost
are bounded and deterministic. It is not a promise that any given binary is
immune to its own resource limits — Book I §3.6 keeps local faults deliberately
outside the canonical outcomes, and each implementation still has to refuse
cleanly rather than fall over. Until v0.6.7 the Rust binary did not: hostile
input aborted it with a stack overflow. It now fences and refuses; see
`tests/book1_resource_fence.py`.

Three independent implementations agree on **all 49** conformance vectors —
Python, Rust and [`warrant-go`](https://github.com/s0fractal/warrant), across
serialization, byte-rejection and evaluation alike — and the evaluator's
determinism, totality and memory bound are machine-checked theorems in Lean 4
([`proofs/`](proofs/)), not prose. A randomized differential fuzzer runs all
three against each other on every push, and `tools/x1_cross_repo.sh` runs this
repo against warrant's HEAD rather than a pinned snapshot.

```bash
python3 impl/sigma_glyph.py                        # Book I -> ALL PASS
python3 tests/spec_conformance/run_reference.py    # 49/49 vectors
```

---

### Current: v0.6.6

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

## The Three Books

| Document | Status | Contract between |
|---|---|---|
| [`spec/book-1-truth.md`](spec/book-1-truth.md) (informative [EN](spec/book-1-truth.en.md)) | Normative | **nodes** — everything two independent nodes need to agree on a result hash: canonical bytes, SHA-256 identity, SKI normal-order reduction, ATP totalization, resolution contract, canonical compiler profile C1 |
| [`spec/book-2-navigation.md`](spec/book-2-navigation.md) | Normative | **nodes** (annotation layer) — WaveVectorQ as detached annotation, pinned LUT (SHA-256 arbitrated), `interfere()` with the Law of Left Dominance, coordinate pins, Mass, CP-24 |
| [`spec/book-3-federation.md`](spec/book-3-federation.md) | Normative | **jurisdictions** — annotation assertions as Warrant v0.3 records, machine-readable selection policies, ConflictSets that clients never merge, AnnotationViewID + assertion-set commitments, ten conformance criteria |
| [`spec/LORE.md`](spec/LORE.md) | Non-normative | **humans & agents** — why the glyphs are named, why FALSE sits at 270°, why the wave left the hash, and what deliberately isn't here yet |
| [`spec/GOV-anchors.md`](spec/GOV-anchors.md) | Normative (meta) | **the spec itself** — releases as anchor-set blobs adopted by threshold warrants (2-of-3), policy lineage, succession for model actors, fork legitimacy; deliberately not a Book: the constitution must not judge itself |

Core invariants, in one breath: **hash is identity; phase is a coordinate; wave is a view; aggregate is never a field; ATP prices work AND memory (size − 1 ≤ spent); dead branches are never fetched; canonical failures are deterministic, local faults are not canonical.**

## Reference implementation

`impl/sigma_glyph.py` — Book I: serialization, validation, CAS, the v0.5 hash-thunk evaluator (lazy left-spine, size-priced ATP, genesis intrinsic), C1 λ→SKI compiler. `impl/sigma_wave.py` — Book II: arbiter-checked LUT, interfere() with entropy–coherence coupling. `impl/sigma_federation.py` + `impl-go/` — Book III (Python oracle + independent Go). `impl-rs/` — a third, independent **Rust** implementation of Book I (from-scratch SHA-256 + evaluator, no external crates) that replays the same oracle-generated vectors byte-exact.

```bash
python3 impl/sigma_glyph.py         # expected: ALL PASS (Book I)
python3 impl/sigma_wave.py          # expected: WAVE: ALL PASS (Book II)
python3 impl/sigma_federation.py    # expected: FEDERATION: ALL PASS (Book III)
(cd impl-rs && cargo build --release) && \
  ./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json  # RUST-CONFORMANCE: ALL PASS (49/49)
```

Book I now has three independent implementations that agree on every vector — the Python oracle, warrant-go's native evaluator (via `ski@v1`), and Rust — plus a Lean 4 mechanization of the evaluator's determinism/totality and memory bound (`proofs/EvalMachine.lean`). `impl-go` in *this* repo implements Books II and III only; its Book I "vector" is an echoed constant and says so out loud (`VACUOUS FV-BOOK-I-UNREACHABLE`).

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
