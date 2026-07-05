# Σ-GLYPH

**Topological Compute Engine / Decentralized Wave Resonator**
Current: **v0.4.6** — DRAFT STANDARD, verified test vectors, reference implementation, machine-readable conformance suite ([`tests/spec_conformance/`](tests/spec_conformance/)).

Content-addressed SKI computation core with a bit-exact determinism guarantee, plus a wave/coordinate navigation layer that is strictly a *view* over identity — never part of it.

```
result_hash = eval(term_hash, atp)     // deterministic, integer-only, total
```

## The Two Books

| Document | Status | Contract between |
|---|---|---|
| [`spec/book-1-truth.md`](spec/book-1-truth.md) | Normative | **nodes** — everything two independent nodes need to agree on a result hash: canonical bytes, SHA-256 identity, SKI normal-order reduction, ATP totalization, resolution contract, canonical compiler profile C1 |
| [`spec/book-2-navigation.md`](spec/book-2-navigation.md) | Normative | **nodes** (annotation layer) — WaveVectorQ as detached annotation, pinned LUT (SHA-256 arbitrated), `interfere()` with the Law of Left Dominance, coordinate pins, Mass, CP-24 |
| [`spec/LORE.md`](spec/LORE.md) | Non-normative | **humans & agents** — why the glyphs are named, why FALSE sits at 270°, why the wave left the hash, and what deliberately isn't here yet |

Core invariants, in one breath: **hash is identity; phase is a coordinate; wave is a view; aggregate is never a field; ATP prices work, not memory; canonical failures are deterministic, local faults are not canonical.**

## Reference implementation

`impl/sigma_glyph.py` — Book I, Milestone 1: serialization, validation, CAS, normal-order evaluator with ATP accounting, C1 λ→SKI compiler, full conformance suite (TV-1…TV-10 + negatives).

```bash
python3 impl/sigma_glyph.py    # expected: ALL PASS
```

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
