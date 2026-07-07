# Review: Codex ADR-004/ADR-005 gate - 2026-07-07

## Verdict

No P0 in the shipped v0.5.0 executable core.

ADR-004: **adopt Option 2**. I do not defend the earlier Codex preference for
Option 1. Kimi's transitive-closure argument is correct on the merits: no
consensus scenario exists where two honest nodes with identical node-CAS must
agree on a blob-dependent `eval()` outcome. Blob validation is a storage-layer
contract; it must not affect Book I canonical eval results.

ADR-005: **adopt R1 with explicit partiality**. I found no navigation use where
a FALSE-containing term's wave must be non-silent. The amplitude-zero cascade is
a theorem of the v0.5 `interfere()` rule, not a Book I safety problem. The spec
must still explicitly define field-level pins, the absent base case for
uncompleted waves, and vectors for FALSE composition plus iterated decay.

## Verified vectors statement

I read `reviews/README.md` first, then ran the required commands before reading
prior reviews.

Command:

```bash
python3 impl/sigma_glyph.py
```

Actual output observed: all checks printed `OK`, including `OK   EV-LIT-FORCE`,
`OK   S(KI)(KK)-dead-missing -> K (divergence class)`, and
`OK   memory bound: size_max - 1 <= spent`, ending with:

```text
ALL PASS
```

Command:

```bash
python3 tests/spec_conformance/run_reference.py
```

Actual output observed: all 46 conformance vectors printed `OK`, including
`OK   EV-LIT-FORCE`, `OK   EV-K-DEAD-MISSING`,
`OK   EV-S-KI-KK-DEAD-Z`, and `OK   EV-TV9-REF-CHAIN`, ending with:

```text
CONFORMANCE: ALL PASS (46/46)
```

Command:

```bash
python3 tools/verify_anchors.py
```

Actual output observed:

```text
OK  spec/book-1-truth.md 0c4f39ccccca99ae2c409d64085aabc82d446a1f6ea1fa5692ad0acb09d4668d
OK  spec/book-2-navigation.md e05f789055acde32b255cb778946d92b47cd2fd0b13eb98ab749adaf60ecd5e4
OK  spec/LORE.md 9bd7977cf7b922a9a3beda60c308d77f6ad6853fa4439e5b03394fa2e79231b9
OK  spec/appendix-a-complexity.md 2df9194b15734a98b185e1f42472ddc52b03597cd6fd48a8a6fbf50799091021
OK  tests/spec_conformance/vectors.json c55c2c40989f72b77db03483a22ab38aec8c81d9fbef4e7ac8e5e1cf5cb6f6f4
OK  tests/spec_conformance/wave_vectors.json 02b5b7ffa74a219ed9769de3cfa3a75e8495f4b07ad317487f4e093f6fdbbf1b
anchors verified
```

Additional ADR-005 wave check:

```bash
python3 impl/sigma_wave.py
```

Actual output observed: all LUT and 17 wave-vector checks printed `OK`, ending
with:

```text
WAVE: ALL PASS (17/17)
```

## Primary evidence checked before prior reviews

I formed the findings below from the ADRs, Book I, Book II, the two reference
implementations, and conformance vectors before reading prior reviews in
`reviews/`.

### ADR-004 claim checks

Book I s1.1 is contradictory. The first LITERAL paragraph says the canonical
node contains a digest rather than the blob, the blob is never needed for
reduction, and blob retrieval/validation is outside Book I. The next paragraph
says normative `resolve(h)` for LITERAL fetches and validates the blob and that
`eval()` must behave like on-demand validation. These cannot both define Book I
`eval()`.

The oracle has no blob channel. `Store` has only `m`, a NodeHash-to-node-bytes
map, and `force()` returns `("lit", atom)` immediately for LITERAL nodes.

Command:

```bash
python3 - <<'PY'
import importlib.util, pathlib
root = pathlib.Path.cwd()
spec = importlib.util.spec_from_file_location("sg", root / "impl/sigma_glyph.py")
sg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sg)

st = sg.Store()
lit_b = sg.ser(sg.LITERAL, sg.F_ATOM, atom=sg.sha(b"dummy blob"))
lit_h = st.put(lit_b)
r, spent = sg.eval_hash(lit_h, 10, st)
print("store attrs", sorted(st.__dict__.keys()))
print("result_kind", r[0], "result_hash", sg.term_hash(r).hex(), "spent", spent)
print("result_is_input_hash", sg.term_hash(r) == lit_h)
PY
```

Output:

```text
store attrs ['m']
result_kind lit result_hash 18e4bb3e3e3d90536f0709bc6ae7e08c489d2fe1dd38d82578e7dd444b2e31af spent 1
result_is_input_hash True
```

`EV-LIT-FORCE` pins the same behavior: a non-genesis LITERAL forces once, costs
1 ATP, and returns the same node hash. The vector has node-CAS bytes only; no
blob input exists in the vector format.

### ADR-004 criterion answer

No consensus scenario exists where identical node-CAS forces agreement on a
blob-dependent outcome.

Reason: Book I `eval(term_hash, atp)` is defined over hash thunks, materialized
SigmaNodeV2 bytes, ATP, and the node-CAS mapping. A LITERAL's atom is part of
the canonical node bytes and therefore part of the node hash. The blob committed
by the atom is not in the node-CAS transitive closure and is never used by any
Book I reduction rule. If `eval()` were changed to fetch blob material, two
honest nodes with identical node-CAS but different blob availability would
produce different canonical outcomes from the same start state. That is the
opposite of a consensus requirement.

This directly concedes against the earlier Codex Option 1 preference. Preserving
the old settlement text is not a technical argument once the shipped v0.5 state
space is inspected. Option 1 would add an uncommitted input channel to
consensus-critical evaluation; Option 2 removes it.

### ADR-005 claim checks

Book II s6.1 pins full vectors for I/S/K. Sections s6.2-s6.4 pin only phase for
Grand Cross, Time Anchor, and Pantheon entries. Book II s2 says `Pin > Derived`
but does not define whether a partial pin overrides one field or the whole
vector. Book II s2 also defines `Derived` only for `APPLY`, so an unpinned
non-genesis LITERAL has no base-case wave.

Command:

```bash
python3 - <<'PY'
import importlib.util, pathlib
root = pathlib.Path.cwd()
spec = importlib.util.spec_from_file_location("sw", root / "impl/sigma_wave.py")
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)

I = sw.W(0, 65535, -32768)
K = sw.W(32768, 65535, -32768)
false_derived = sw.interfere(K, I)
false_r1 = dict(false_derived); false_r1["ph"] = 49152
print("interfere(K,I)", false_derived)
print("FALSE R1 field-pin", false_r1)

for idx, other in enumerate([I, K, sw.W(16384, 65535, -32768), sw.W(8192, 30000, 100)], 1):
    print("cascade left", idx, sw.interfere(false_r1, other))
    print("cascade right", idx, sw.interfere(other, false_r1))

w = sw.W(0, 49151, 0)
seq = [w["am"]]
for _ in range(6):
    w = sw.interfere(w, w)
    seq.append(w["am"])
print("decay sequence", "->".join(map(str, seq)))
PY
```

Output:

```text
interfere(K,I) {'ph': 32768, 'am': 0, 'en': -32512}
FALSE R1 field-pin {'ph': 49152, 'am': 0, 'en': -32512}
cascade left 1 {'ph': 49152, 'am': 0, 'en': -32640}
cascade right 1 {'ph': 0, 'am': 0, 'en': -32640}
cascade left 2 {'ph': 49152, 'am': 0, 'en': -32640}
cascade right 2 {'ph': 32768, 'am': 0, 'en': -32640}
cascade left 3 {'ph': 49152, 'am': 0, 'en': -32384}
cascade right 3 {'ph': 16384, 'am': 0, 'en': -32384}
cascade left 4 {'ph': 49152, 'am': 0, 'en': -16025}
cascade right 4 {'ph': 8192, 'am': 0, 'en': -16025}
decay sequence 49151->36863->20735->6560->657->7->0
```

The ADR-005 arithmetic is correct. The one caveat is that `interfere(K,I)` gives
`ph=32768`, and R1 then applies the FALSE phase pin to get `ph=49152` while
leaving `am=0,en=-32512`.

### ADR-005 criterion answer

I found no use where a FALSE-containing term's wave must be non-silent for
navigation to work.

Federation queries and local navigation can still address FALSE by NodeHash,
structural index, or phase coordinate. Mass-style ranking already depends on
amplitude; a FALSE-containing composite contributing zero mass is coherent with
the math and does not affect Book I. LORE gravity language is non-normative and
cannot justify defaulting missing amplitudes to maximum strength.

R2 would invent maximal amplitude and minimum entropy for entities whose fields
were never computed. That is larger and less defensible than accepting the
derived silence where derivation exists and making absent fields explicit where
derivation does not exist.

## Findings by severity

### P1 - ADR-004: Book I LITERAL blob scoping is consensus-significant prose drift

The shipped law is oracle plus vectors: `eval()` does not read blobs. Book I
s1.1 still contains normative prose requiring blob validation inside LITERAL
`resolve(h)`. That text is not merely unimplemented; if implemented as canonical
`eval()` behavior, it creates a divergence surface because blob-CAS state is not
fixed by identical node-CAS.

Concrete normative text proposal for Book I s1.1:

```text
LITERAL is an inert commitment. The canonical node contains `atom`, a 32-byte
digest, not the committed blob. For Book I reduction the blob is never demanded:
LITERAL is a normal form, and combinators are recognized only by NodeHash
(s3.2).

Book I validates SigmaNodeV2 node bytes only. Absence, availability, or
corruption of external blob material committed by `atom` MUST NOT change the
canonical result hash, canonical failure kind, or ATP spent reported by
`eval()`. Blob retrieval APIs MAY validate `SHA-256(blob) == atom` and report
storage-layer faults, but those faults are outside Book I and MUST NOT serialize
as Book I DISSONANCE.
```

Concrete conformance-vector proposal:

```text
Keep EV-LIT-FORCE, but strengthen its note:
"non-genesis LITERAL: one force (1 ATP), then NF. No blob material is supplied;
Book I eval MUST depend only on the LITERAL node bytes and MUST NOT fetch or
validate the committed blob."

Add a format note:
"Eval vectors do not contain blob-store inputs. Implementations MUST NOT make
kind=eval results depend on external blob material."
```

Do not add `EV-LIT-BLOB-OK`, `EV-LIT-BLOB-MISMATCH`, or
`EV-LIT-BLOB-MISSING` to Book I conformance if Option 2 is adopted. Those would
reintroduce the external channel.

### P1 - ADR-005: Book II partial pins and absent wave base cases are underspecified

R1 should be adopted, but it needs sharper type text. The current
`WaveAnnotation: NodeHash -> WaveVectorQ` implies total full vectors for
annotated nodes, while the tables contain phase-only pin records. Under R1,
unlisted fields derive only where derivation is defined; otherwise the full wave
is absent.

Concrete normative text proposal for Book II s1-s2:

```text
struct WaveVectorQ { ph: uint16; am: uint16; en: int16; }
struct WavePin { ph?: uint16; am?: uint16; en?: int16; }

Pin tables in s6 define WavePin records. A pin overrides exactly the fields it
lists. Unlisted fields are completed by Derived only when the node is APPLY and
the corresponding child waves are present. If any field cannot be completed,
`wave_full(node)` is absent for that node.

Derived:
  wave_full(APPLY(f,a)) = complete(interfere(wave_full(f), wave_full(a)),
                                   pin(APPLY(f,a)))
  where the pin, if present, overrides only listed fields.

Base case:
  A non-genesis, non-pinned LITERAL has no derived wave. Its `wave_full` is
  absent unless a full pin or external WaveAnnotation supplies all fields.
  Interference with an absent operand is absent.

Pins and absent waves are Book II annotation facts only. They MUST NOT affect
Book I serialization, hashing, or eval.
```

Concrete normative text proposal for Book II s6.2 FALSE:

```text
FALSE has a phase pin only: `pin(FALSE).ph = 49152`. Under R1, its unlisted
fields are derived from `interfere(wave_full(K), wave_full(I))`, so:
`wave_full(FALSE) = {ph=49152, am=0, en=-32512}`.
Consequently, any APPLY whose derived subtree contains FALSE has `am=0` unless
an explicit pin overrides amplitude at or above that node.
```

Concrete conformance-vector proposals:

```text
WV-FALSE-R1:
  rule: field-level pin completion
  term: FALSE = APPLY(K,I)
  pins: I={0,65535,-32768}, K={32768,65535,-32768}, FALSE.ph=49152
  expected: {ph=49152, am=0, en=-32512}

WV-FALSE-ANCESTOR-SILENT:
  rule: derived APPLY with FALSE child
  term: APPLY(FALSE,I)
  expected: {ph=49152, am=0, en=-32640}

WV-PH-ONLY-LITERAL-ABSENT:
  rule: phase-only LITERAL pin without derivable Am/En
  term: SATOSHI or TESLA
  expected: wave_full absent; phase pin remains available as a coordinate pin
            but the node is excluded from Mass until a full annotation exists.

WV-UNPINNED-LITERAL-ABSENT:
  rule: base case
  term: LITERAL(SHA-256("dummy blob")) with no pin
  expected: wave_full absent

WV-SELF-PARTIAL-ITERATED:
  rule: repeated self-interference
  start: {ph=0, am=49151, en=0}
  expected amplitude sequence: 49151->36863->20735->6560->657->7->0
```

The existing `wave_vectors.json` format only covers raw `interfere(w1,w2)`.
Adopting ADR-005 should either extend the format with `kind` fields for
pin-completion and absent-wave cases, or add a second `wave_terms.json` suite.

## Engagement with standing positions

Codex prior position on ADR-004: I previously preferred Option 1 because it
preserved the v0.4.2 settlement text. I now concede. The transitive-closure
argument defeats that preference: historical continuity cannot justify making a
canonical result depend on blob state absent from node-CAS.

Kimi on ADR-004: I agree with the Option 2 conclusion and with the stronger
claim that Option 1 would be P0-class if adopted. My independent code check
reproduced the core premise: the store has only node bytes, and LITERAL eval
returns the input node hash without blob material.

Maintainer on ADR-004: I agree with the Option 2 leaning. The prose should be
rewritten to scope validation outside `eval()` rather than making the oracle
grow a BlobStore.

Maintainer undecided R1-vs-R2 on ADR-005: I recommend R1. R2 is attractive only
because it makes full vectors easier to consume, but it silently assigns maximum
amplitude to phase-only entities. R1 plus explicit absent-wave semantics is
smaller, matches `interfere()`, and preserves the ability to add full pins later
with explicit evidence.

Kimi on ADR-005: I agree with the confirmed P1s: partial-pin semantics,
FALSE-derived zero amplitude, missing LITERAL base case, and the unpinned decay
chain. I also preserve the maintainer correction: the decay sequence is not a
contradiction of Book II's crystallization narrative; it is the stated
"partial commitment decays quadratically" behavior and needs vector coverage.

## New relative to prior reviews

New only in the sense of gate disposition, not discovery: this review gives a
direct Codex concession on ADR-004 Option 1 after checking Kimi's argument
against the code and vectors.

For ADR-005, the additional sharpening is that R1 requires an explicit partial
pin type or equivalent prose. Without that, phase-only SATOSHI/TESLA/Pantheon
entries remain awkward: they are normative phase coordinates, but not full
`WaveVectorQ` annotations unless Am/En are completed by derivation or later
explicit full annotations.

## Closing

ADR-004 should close as Option 2 with no Book I blob vectors. ADR-005 should
close as R1 with partial wave semantics and a release because
`wave_vectors.json` is anchored. The concrete vector gap to prioritize is
`FALSE = APPLY(K,I) -> {ph=49152, am=0, en=-32512}` plus one FALSE-ancestor
silence vector; those pin the controversial consequence directly.
