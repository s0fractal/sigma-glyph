# ADR-008 rev 2 re-verification: Resonant Precedent

Reviewer: Codex, second adversarial pass after the rev-1 findings were applied

Scope:

- `proposals/ADR-008-resonant-precedent.md`
- `examples/resonant_precedent_probe.py`
- Σ-GLYPH Books I–III and their reference implementations
- Warrant v0.3 `ski@v1` runtime and OAIP v0.1 bridge

## Verdict

**Rev 2 is materially better, but is not ready to close the design gate.**

The previous four P1 findings were answered in the right architectural
direction: the decision-to-term projection is now named as a required contract;
the invalid `resonance@v1` reason kind is gone; AnnotationViewID is no longer
misused as a multi-node index identity; and WarrantID ordering no longer decides
top-k inclusion. The three previous P2 findings are also corrected: coherence
is symmetric, relevance is a phase bucket rather than head identity, and the
probe measures phase buckets.

The new citation design, however, crosses a runtime boundary that `ski@v1` does
not provide. Current `ski@v1` evaluates a Book I SigmaNode graph. It cannot read
or parse a Book III JCS wave-assertion blob, invoke Book II `wave()`/`LUT_COS`,
or bind a body-level Warrant evidence item to a fact inside the term. The
projection and index-view contracts are also described as closed without yet
defining closed bytes. These are P1 gate blockers, not implementation polish.

Recommended gate state: **amend, then re-review**.

## Verified-vectors statement

I read `reviews/README.md`, ran the new probe, and then ran the repository's
complete validation matrix.

```bash
python3 examples/resonant_precedent_probe.py
tools/test-all.sh
```

Observed probe facts:

```text
metric symmetric: coh(SI,KI)=0 coh(KI,SI)=0 -> equal? True
max coherence = 32767; boundary tie-set size = 13
heads in the tie-set = ['S', 'V']
baseline I/S/K   phase_buckets= 3  full_triples= 10
extended +named phase_buckets= 9  full_triples= 67
```

The complete matrix ended with:

```text
WAVE-BRIDGE: ALL AGREE (582/582)
TEST-ALL: ALL GREEN
```

This includes Python/Go/Rust conformance, federation and governance
differentials, the live two-jurisdiction Warrant demo, anchor verification,
settlement-grade Warrant verification, and Lean byte/eval/wave bridges.

I also tested the proposed `ski@v1` seam directly. A canonical
`sigma-glyph.wave-assertion@v1` JCS blob is not a SigmaNodeV2 object. Resolving
its blob hash from a Book I REF produces Canonical Invalid Object:

```text
assertion_deserializes_as_sigma_node None
REF(assertion_blob) result ... af69b517...a4507
is_canonical_invalid True
```

Finally, I checked the proposed index identity wording. These two plausible
interpretations are not equal:

```text
SHA256(JCS)                       = fa21aa13...7fa5a
NodeHash(LITERAL, SHA256(JCS))    = 800a2656...a0136
equal? False
```

Thus "`NodeHash` of a JCS blob" needs one exact construction.

## Confirmed rev-1 fixes

1. `LUT_COS[|Δph|]` is correctly described as symmetric; the unused
   directional `interfere()` output is no longer presented as the retrieval
   primitive.
2. The probe includes the `S`/`V` shared phase and reports the complete maximum
   tie-set rather than inferring head identity from a truncated top five.
3. Retrieval resolution is now measured in the space read by the metric:
   distinct phases, 3 → 9.
4. WarrantID is acknowledged as mineable. Threshold inclusion returns the
   complete boundary tie-set, so mining an identifier cannot evict another
   equal-score candidate.
5. A per-index commitment replaces the per-node AnnotationViewID.
6. A decision-to-term projection is now explicitly recognized as the central
   OAIP↔Σ-GLYPH contract.

## Findings

### P1: `ski@v1` cannot execute the proposed wave citation

ADR-008 says the `ski@v1` term reads two
`sigma-glyph.wave-assertion@v1` evidence blobs and computes
`coherence(wave_q, wave_cited)`. That is not a capability of Warrant
`ski@v1`.

The runtime's complete input is:

```json
{"ski":1,"term":"<NodeHash>","atp":0,"expect":"<NodeHash>"}
```

Warrant calls `eval_hash(term, atp, BlobCAS)`. The CAS adapter returns bytes only
when Book I forces a NodeHash. Book I then validates those bytes as
SigmaNodeV2. A wave assertion is JCS JSON, not SigmaNodeV2, so forcing it yields
Canonical Invalid Object; there is no byte parser, JSON parser, field access,
integer primitive, Book II `wave()` call, or LUT opcode in Book I.

The body-level `evidence` array is not passed to `run_ski_check` either.
Warrant's existing `ski_policy` library states the honest boundary explicitly:
fact values are baked into the term, and evidence/signatures must establish
whether those facts are true. Swapping the cited wave evidence does not alter a
precompiled term's verdict.

This means the proposed reason can at most prove a Boolean over *claimed phase
values baked into the term*. It does not prove that those phases came from the
two cited assertion blobs or the named index view.

Concrete options:

1. Define a new deterministic check runtime, for example `wave@v1`, whose closed
   check blob names the query assertion, cited assertion, metric, threshold, and
   index view. Its verifier resolves and validates the JCS assertions and then
   executes the pinned Book II integer algorithm. This keeps the Warrant reason
   kind as `check`, but it does require a Warrant format/runtime version change.
2. Use `cmd@v1` for an illustrative profile and withdraw the
   "re-runnable without trust" claim.
3. Supply a real compiler and conformance vectors that encode the assertion
   bytes, their hashes, JCS validation, integer coherence computation, and the
   threshold predicate into Book I terms. Merely baking precomputed phase facts
   into a Boolean term is insufficient.

The first option is the smallest honest contract.

Suggested replacement:

```text
A resonant citation remains a Warrant check reason, but current ski@v1 cannot
bind Book III JCS wave assertions to a Book II coherence computation. ADR-008
therefore requires either (a) a future deterministic wave@v1 check runtime with
a closed check schema and cross-implementation vectors, or (b) a non-portable
cmd@v1 profile. Until that runtime exists, resonance citations are profile
evidence, not Warrant's trustless ski@v1 reasons.
```

### P1: `projection@v1` is named but not yet defined

The ADR calls `projection@v1` a "normative, closed" schema, but supplies neither
an object schema nor an executable mapping. The prose says that the profile
"names exactly which record fields are read, in what order, [and] how they
encode", while open question 3 still asks what the minimal schema is. A content
hash makes bytes immutable; it does not give unknown bytes shared semantics.
Two implementations can resolve the same profile hash and still have no rule
for parsing or executing it.

The gate needs either:

- one actual closed projection DSL with field domains, ordering,
  failure/absence behavior, vocabulary identity, compiler semantics, and
  vectors; or
- a deliberately narrow R0 bridge that does not infer semantics from OAIP
  prose.

The narrow bridge is enough to validate the rest of the ADR:

```json
{
  "projection": "sigma-glyph.precedent-projection@v1",
  "source_subject": "<hex64 OAIP/Warrant subject blob>",
  "profile": "<hex64 governed projection-policy blob>",
  "term": "<hex64 Sigma NodeHash>",
  "vocabulary": "<hex64 governed vocabulary-set blob>"
}
```

Unknown fields are invalid; every hash is lowercase hex64; the blob is accepted
under the jurisdiction's projection policy. This makes the mapping explicit
and settlement-governed without pretending that OAIP's free-form predicate has
already acquired a canonical semantic compiler. A later ADR can replace the
explicit `term` assertion with a genuinely executable projection DSL.

### P1: `PrecedentIndexViewID` does not yet have deterministic bytes

"`NodeHash` of a JCS blob committing `{...}`" is not an exact identity rule.
Book I NodeHash is SHA-256 of canonical SigmaNodeV2 bytes, whereas Warrant/OAIP
blob identity is SHA-256 of blob bytes. At minimum the ADR must choose between:

```text
PrecedentIndexViewID = SHA-256(JCS(view_object))
```

and:

```text
PrecedentIndexViewID =
  NodeHash(LITERAL, atom = SHA-256(JCS(view_object)))
```

The view object is also not closed yet: it has no version tag, field domains,
array ordering, exact `active_warrant_set_commit` algorithm, definition of
which active records enter that set, Sigma/Book-II ruleset anchor, federation
selection-policy identity, or epoch. `metric_id` is named but not bound to
bytes or an anchored ruleset.

A sufficient construction should define a tagged closed JCS object, sort all
set-valued arrays lexicographically, pin the exact set-commit algorithm, and
include every ruleset needed to derive an entry. If `NodeHash` is desired, wrap
that content hash as a LITERAL exactly as Book I §8 does.

### P1: the query returns a set while the criteria require byte-identical rankings

`precedent(wave_q, index, τ)` now correctly avoids top-k boundary eviction, but
it returns "every entry" above a threshold and leaves all further ordering to
settlement policy. The design criteria nevertheless require two implementations
to derive byte-identical *rankings*, and the text still says resonance "orders"
candidates. No canonical result representation is defined.

WarrantID can safely be used for serialization inside a coherence tie as long
as that order has no inclusion, authority, or rank semantics. One exact result
shape would be:

```json
[
  {"coherence": 32767, "entries": ["<WarrantID>", "..."]},
  {"coherence": 30273, "entries": ["<WarrantID>", "..."]}
]
```

Buckets are ordered by descending signed coherence; IDs inside each bucket are
sorted lexicographically solely for canonical bytes; all entries at the
inclusive `int16` threshold are retained. This preserves the anti-grinding fix
while making "byte-identical ranking" testable.

### P2: the phase-capture paragraph conflates two attack surfaces

ADR-006's hash-grinding attack chose an assertion's *position in a fold* so
Left Dominance selected its phase. ADR-008 no longer folds or orders by
WarrantID, so that exact attack is closed. In ADR-008, an actor does not grind a
hash to land on a phase: it chooses or manipulates source fields so the
projection emits a term with the desired pinned left head. That is projection
gaming/head capture, governed by candidate admissibility and projection policy.

The paragraph also alternates between injecting a candidate precedent and
putting cost/uniqueness on the *query* side. Those are different adversaries and
need separate controls.

Suggested terminology:

```text
Projection capture: an actor may shape a decision's projected term so its left
head occupies a desirable phase bucket. Candidate-side mitigation is
settlement-active admissibility plus projection-policy validation. Query-side
gaming is separate: a querier may choose a query term to surface a preferred
bucket, but this cannot add authority to any returned warrant.
```

### P2: the probe docstring still says 63 full triples

The executable output and ADR prose correctly report 67 distinct full triples
for the extended corpus. The module docstring says 63. This does not affect the
phase-bucket conclusion, but it breaks the claim that every number in the probe
description is recomputed rather than hand-written.

## Gate recommendation

Keep the corrected metric/query core:

1. phase-only symmetric coherence;
2. inclusive threshold buckets, never top-k truncation through ties;
3. no identifier-based semantic tie-break;
4. settlement-active admissibility;
5. explicit phase-not-identity behavior.

Before the next gate, reduce the bridge to three executable contracts:

1. an actual projection blob/schema (the explicit-term R0 is sufficient);
2. an exact index-view identity and canonical result encoding;
3. a citation verifier that can really bind the cited JCS assertions to the
   coherence claim (`wave@v1`, or an equivalently specified runtime).

Once those have vectors, ADR-008 becomes a coherent OAIP/Warrant profile over
Book II rather than a promise that `ski@v1` already crosses the Book I/II
boundary.
