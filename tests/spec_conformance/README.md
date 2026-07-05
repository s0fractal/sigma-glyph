# Σ-GLYPH Specification Conformance Suite

Machine-readable test vectors for Book I (TRUTH). Purpose: an implementation
in any language can claim Book I conformance by passing `vectors.json` —
without reading the Python reference implementation.

## Files

| File | Role |
|------|------|
| `vectors.json` | The vectors. **Generated, never hand-edited.** |
| `generate.py` | Regenerates `vectors.json` from the oracle (`impl/sigma_glyph.py`). |
| `run_reference.py` | Replays the vectors against the oracle; also executable documentation of runner semantics. |
| `test_properties.py` | Seeded property tests (determinism, ATP exactness, canonicity round-trip, C1 purity). Stdlib-only. |

## vectors.json format (`format_version: 1`)

Top level:

```jsonc
{
  "format": "sigma-glyph-conformance",
  "format_version": 1,
  "spec_version": "0.4.5",        // Book I DOCUMENT version the vectors conform to
  "suite_version": "0.4.5",       // conformance-suite PACKAGE (release) version
  "book1_anchor": "6ca303f3…",    // Specification Anchor of that Book I
  "objects": { "<node-hash-hex>": "<canonical-bytes-hex>", … },
  "vectors": [ … ]
}
```

`spec_version` and `suite_version` can differ: the suite may grow vectors in a
release that does not touch Book I text. A conformance claim cites both plus
`book1_anchor` — the anchor is the unambiguous one.

**Setup:** insert every entry of `objects` into your CAS. Keys are the SHA-256
NodeHash of the bytes — verify this while loading. One object is deliberately
*malformed* (Era-1 `0x03` opcode): a CAS stores bytes, not judgments; its
validity is decided at `resolve()` time (Book I §3.5b, §4.1).

**Vector kinds:**

- `kind: "object"` — serialization/hash conformance.
  Hashing `bytes` MUST yield `expected.hash`.

- `kind: "deserialize"` — negative validation.
  `bytes` MUST fail §4.1 validation (⇒ materialize the Canonical Invalid
  Object, §4.2). `expected.valid` is always `false` in v1.

- `kind: "eval"` — the core contract.
  `eval(term, atp)` MUST produce a node whose NodeHash is
  `expected.result_hash`, spending exactly `expected.atp_spent` ATP under
  **tree semantics** (Book I §3.4, TV-6). `expected.outcome`
  (`normal_form` | `atp_exhausted` | `unresolved_reference` | `invalid_object`)
  is informative; the normative observables are `result_hash` and `atp_spent`.

Dissonance outcomes need no special casing: `DISSONANCE(ATP Exhausted)` and
`DISSONANCE(Unresolved Reference)` are canonical nodes with fixed hashes, so
comparing `result_hash` covers them uniformly.

## Claiming conformance

1. Load `objects`, verifying CAS keys.
2. Pass all `vectors` (39 in this release).
3. State the `spec_version`, `suite_version` and `book1_anchor` you tested against.

Passing this suite demonstrates conformance on the covered surface; it does
not replace reading Book I. The suite grows — new findings become new vectors
(review protocol: `reviews/README.md`).

## Regenerating

```
python3 tests/spec_conformance/generate.py     # rewrites vectors.json from the oracle
python3 tests/spec_conformance/run_reference.py
python3 tests/spec_conformance/test_properties.py
```

Regeneration is deterministic: same oracle → byte-identical JSON. CI enforces
that a stale `vectors.json` (one that no longer matches the oracle) fails.
