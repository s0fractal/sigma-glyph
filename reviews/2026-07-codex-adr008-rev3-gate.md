# ADR-008 rev 3 gate: the citation is still not a precedent proof

Reviewer: Codex, third adversarial pass

Scope:

- `proposals/ADR-008-resonant-precedent.md` rev 3
- `examples/resonant_precedent_probe.py`
- `examples/resonant_precedent_contracts_probe.py`
- Σ-GLYPH Books I–III, Warrant v0.3, and OAIP v0.1

## Verdict

**Amend, then re-review.**

Rev 3 correctly withdraws the impossible `ski@v1` reuse and chooses the honest
shape: a new Warrant check runtime. C2's content-hash construction and C3's
inclusive score buckets are also sound directions.

The new C1 probe proves a narrower claim than the ADR needs, however. It proves
that a verdict changes when one *wave-assertion blob hash* is replaced by
another. It does not prove that the blob belongs to the cited decision, is
settlement-active or selected in the named index view, matches the C0 projected
term, or even belongs to the view's jurisdiction. `index_view` is accepted and
then ignored. Consequently `wave@v1` can return `pass` for an arbitrary valid
but inactive/cross-jurisdiction assertion while the prose calls the result an
admissible precedent citation.

The reference verifier also is not total over its proposed input schema:
malformed field types and malformed JSON crash it, while non-JCS assertion
bytes are accepted. These are executable P1 counterexamples at the new seam,
not objections to the phase metric.

The structural core is now close. The missing object is a **verifiable
precedent entry** joining:

```text
decision Warrant
  → accepted C0 projection
  → projected term
  → effective Book III wave in C2 view
  → C1 coherence claim
```

Until that join is executable, C0, C1, and C2 remain three individually
content-addressed objects rather than one proof.

## Verified-vectors statement

I ran both ADR probes before reviewing the prose:

```bash
python3 examples/resonant_precedent_probe.py
python3 examples/resonant_precedent_contracts_probe.py
```

Observed happy-path results:

```text
metric symmetric ... equal? True
phase_buckets=3
phase_buckets=9
swapping the cited blob flips the verdict: True
same active set shuffled ... order-independent? True
settlement +w4 ... changed by new active? True
canonical bytes ... re-run identical: True
```

I then ran:

```bash
python3 -m py_compile \
  examples/resonant_precedent_probe.py \
  examples/resonant_precedent_contracts_probe.py
tools/test-all.sh
```

The complete repository matrix ended with:

```text
WAVE-BRIDGE: ALL AGREE (582/582)
TEST-ALL: ALL GREEN
```

I additionally called the C1/C2/C3 functions with adversarial inputs. Relevant
observations:

```text
threshold='30000'     CRASH TypeError
threshold=None        CRASH TypeError
query=list            CRASH TypeError
malformed-json        CRASH JSONDecodeError
noncanonical-json     pass
bad-index-view        pass
cross-jurisdiction    pass
duplicate root changes logical-set view? True
duplicate active id changes logical-set view? True
duplicate index entries ... same WarrantID appears twice
C0 validator exists? False
```

The normal suite is green because the new profile is not part of the anchored
suite yet. The adversarial calls target exactly the proposed new contract.

## Findings

### P1: C1 binds two blobs, not a cited precedent in C2

The C1 schema calls `query` and `cited` "wave-assertion blob" hashes. The
admissibility rule later says "`cited` is settlement-active in J", but
settlement-active identity is a WarrantID, not a subject-blob hash. The check
contains no cited decision WarrantID and no wave-assertion WarrantID, so the
runtime cannot evaluate that rule.

The verifier also never reads `index_view`. Replacing it with
`"not-hex-or-resolvable"` still returns `pass`. Supplying a syntactically valid
assertion from a different jurisdiction also returns `pass`. A valid but
inactive, superseded, conflict-losing, stale, or foreign assertion therefore
works as citation evidence as long as its phase is favorable.

There is a second disconnected edge: C0 projects a decision to a term, but C1
does not resolve a C0 blob, compare `assertion.node` to `projection.term`, or
derive `wave(term)` under Book III selection. It reads the complete vector from
an arbitrary direct assertion instead. The probe uses the same `node` for query
and cited assertions and does not involve C0 at all.

Thus the current check proves only:

```text
two syntactically valid assertion blobs contain phases whose cosine score
meets a threshold
```

It does not prove:

```text
this settlement-active decision, projected by C0 in this C2 view, has this
effective wave and coheres with the query
```

Concrete correction: define a closed `precedent-entry@v1` proof object, or put
equivalent fields directly in the `wave@v1` check:

```json
{
  "entry": "sigma-glyph.precedent-entry@v1",
  "decision_warrant": "<hex64 settlement-active WarrantID>",
  "projection_warrant": "<hex64 WarrantID accepting the C0 blob>",
  "projection": "<hex64 C0 blob>",
  "wave_assertion_warrant": "<hex64 selected assertion WarrantID>",
  "wave_assertion": "<hex64 assertion blob>",
  "index_view": "<hex64 C2 view>"
}
```

For a deliberately narrow R0, the runtime can require a direct selected
assertion and verify:

1. the decision Warrant is active in the C2 active set;
2. its `subject.hash` equals C0 `source_subject`;
3. the projection Warrant is active and filed under the declared profile;
4. C0 `term` equals the assertion's `node`;
5. the assertion Warrant is active, has that assertion as its subject, embeds
   the view jurisdiction, and wins Book III selection at the view epoch;
6. the C2 view object hashes to `index_view`.

If structurally derived waves are in scope, step 5 must instead run
`wave_fed(term, resolve_selection)` over the view's active assertion set. That
is a larger runtime. The ADR must choose direct-assertion R0 or full derivation;
the current code silently chooses neither.

### P1: `wave_v1_verify` is not a total closed-schema verifier

The function checks the key set and two tag strings, but does not validate:

- `query`, `cited`, and `index_view` as lowercase hex64;
- `threshold` as an `int16` excluding booleans;
- JCS canonical bytes for the check or assertion blobs;
- duplicate JSON member names;
- the metric's pinned Sigma/Book-II ruleset;
- query/cited jurisdiction and node/view relationships.

This produces both crashes and invalid acceptance:

- string/`null` thresholds crash at integer comparison;
- an unhashable query value crashes dictionary lookup;
- malformed JSON crashes parsing;
- pretty-printed non-JCS assertion JSON returns `pass`;
- `true` is accepted as threshold `1`;
- out-of-int16 thresholds are accepted;
- cross-jurisdiction assertions return `pass`.

Book III requires JCS-canonical assertion bytes. Parsing to a dict and then
calling `validate_assertion` cannot detect duplicate keys or prove that the
stored bytes were canonical. The runtime must validate raw bytes before
semantic validation.

The proposed third outcome, `"invalid"`, also needs Warrant semantics. A
Warrant check reason claims only `pass` or `fail`. Existing `ski@v1` treats a
malformed/unexecutable check as **unverified**, escalated to ERR for a
settlement-active record; it does not expose `"invalid"` as a reason verdict.
The new Warrant runtime version must specify the same distinction.

Required negative vectors should include:

```text
unknown/missing field
wrong scalar type (including bool-as-int)
threshold -32769 and 32768
non-hex and uppercase hash
missing blob
malformed JSON
non-JCS JSON
duplicate JSON key
invalid assertion schema
foreign jurisdiction
wrong node for projection
inactive/losing assertion Warrant
wrong/unresolvable index_view
ruleset mismatch
```

No input in the runtime's byte domain may raise an implementation exception.

The runtime tag must either normatively mean one anchored Book II ruleset
(analogous to `ski@v1` naming Book I v0.5), or the check blob must carry and
validate the ruleset/anchor-set hash. C2 pinning a ruleset does not help while
C1 ignores C2.

### P1: C0 is a schema sketch without an executable Warrant join

Rev 3 says the previous projection P1 is closed by executable code, but the
contracts probe implements only C1, C2, and C3; there is no C0 validator.

The five-field JSON shape is a useful R0 payload, but the lifecycle is still
undefined:

- Is the C0 blob the `subject.hash` of a separate projection-accept Warrant, or
  evidence on the decision Warrant?
- Which WarrantID is the indexed decision?
- How is `source_subject` checked against that decision's `subject.hash`?
- Must the accepting Warrant's `under` contain exactly `profile`?
- Is the C0 Warrant required to be active in the same C2 view?
- What is the closed vocabulary-set blob schema, and what does validation of
  `term` against it mean?
- Are multiple active projections for one decision a conflict, separate views,
  or multiple entries?

`source_subject` alone cannot identify a sealed decision: multiple Warrants can
decide the same subject with different actors, policies, outcomes, and prior
history. Precedent identity is the decision WarrantID.

Smallest correction:

1. add `source_warrant` to C0;
2. make the C0 blob the subject of an active projection-accept Warrant;
3. require `source_warrant.body.subject.hash == source_subject`;
4. require the projection Warrant to be filed under the `profile` policy;
5. define conflict/cardinality rules for projections per
   `(source_warrant, profile)`;
6. ship `validate_projection` plus negative vectors.

This remains an explicit-term bridge; it does not require the deferred semantic
DSL.

### P2: C2 hashes lists that are described as sets

The probe sorts `genesis_roots` and `active_warrant_ids` but does not reject or
remove duplicates. `[A]` and `[A,A]` therefore produce different IDs despite
representing the same logical set. `assertion_set_root` is sound when its caller
already supplies a mathematical set; the new public helper does not enforce
that precondition.

Require uniqueness and either reject duplicates or canonicalize from a set
before hashing. Add vectors for duplicate roots/active IDs.

The `sigma_ruleset` field is also described as one "Book I/II anchor", while the
repository has separate Book anchors. Index derivation crosses Book I term
identity, Book II wave math, Book III selection, and Warrant active-set rules.
Use the governed Sigma anchor-set identity, or list the exact required anchors
and Warrant profile explicitly. A stand-in hash of `"book1-v0.5"` does not
exercise this seam.

### P2: C3 needs an input-set contract

C3 canonicalizes a well-formed list but neither validates nor normalizes the
index. Duplicate entries with the same WarrantID survive into the result twice.
Malformed waves, hashes, or thresholds can also raise exceptions.

Define the index as a set keyed by a precise identity—probably
`(decision_warrant, projection_profile)`—and reject duplicates before scoring.
Validate `tau` as int16 excluding bool, every WarrantID as lowercase hex64, and
every effective wave as WaveVectorQ. Sorting within a tie remains bytes-only and
is not a semantic grind surface.

### P3: the contract count and labels are inconsistent

The Problem section says "three contracts" but lists C0, an unlabeled citation
runtime, C2, and C3: four contracts. The next heading also says "three bridge
contracts", while rev 3 relies on C0–C3. Label the citation as C1 in the Problem
sentence and call them four contracts. The probe should either add C0 or stop
claiming all P1 closures are executable.

## Normative-home answer

Do **not** move the whole ADR into OAIP as one unit.

- **C0 belongs in OAIP or an explicit OAIP↔Σ projection profile.** It maps an
  observed/decided subject into a Sigma term and governs semantic vocabulary.
- **C1 belongs to Warrant's runtime specification/registry.** Adding
  `wave@v1` changes which `because.kind=check` records are schema-valid and how
  settlement-grade verification treats execution failure. OAIP may author the
  check, but it cannot unilaterally define a Warrant runtime tag.
- **Book II owns the coherence algorithm and its anchor.**
- **Book III owns effective-wave selection and jurisdictional assertion
  validity.**
- **C2/C3 belong in the precedent profile**, which composes the above contracts.

So ADR-008 is indeed not a Book II ADR. It is a cross-project
OAIP/Warrant precedent profile over Books II–III. The clean split is:

```text
OAIP profile:       C0 projection payload and governance
Warrant extension:  C1 wave@v1 runtime and failure/version semantics
Sigma Books II/III: wave metric + effective-wave derivation
ADR-008 profile:    C2 view identity + C3 query/result contract
```

## Gate recommendation

Keep C2's direct content hash and C3's inclusive bucket representation. For the
next revision, focus on one end-to-end negative-capable vector:

```text
active decision Warrant
  + active C0 projection Warrant
  + selected Book III assertion Warrant
  + C2 view
  + C1 check
  → pass
```

Then flip each edge independently:

```text
inactive decision
wrong source_subject
projection under wrong policy
assertion for wrong node
foreign jurisdiction
losing/stale assertion
wrong index view
noncanonical blob
```

Each must deterministically become runtime-unverified/invalid according to the
new Warrant version, never `pass` and never a host exception. Once that vector
exists in two implementations, the remaining projection question is genuinely
semantic research rather than an unclosed structural seam.
