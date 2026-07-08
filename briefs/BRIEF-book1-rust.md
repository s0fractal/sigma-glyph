# BRIEF: Rust implementation of Σ-GLYPH Book I (third independent impl)

Build an independent Rust implementation of Σ-GLYPH **Book I** (TRUTH) that
replays the machine-readable conformance suite byte-exact. The Python
reference is `impl/sigma_glyph.py` and the normative text is
`spec/book-1-truth.md`; you MAY read both to resolve ambiguity, but your
implementation must be your own logic, not a transliteration. Passing the
oracle-generated vectors IS the differential test against the oracle.

## Deliverable

A crate under `impl-rs/` (edition 2021), buildable **offline** — no network
crates that need fetching if avoidable. You MAY depend on the `sha2` crate
for SHA-256 (it is the standard choice and models a production impl); if the
sandbox cannot fetch it, implement SHA-256 (FIPS 180-4) from scratch in the
crate instead — decide based on whether `cargo build` can fetch. `serde_json`
is convenient for parsing vectors.json; if it cannot be fetched, write a tiny
hand JSON reader (the file is simple: objects is a flat string→string map;
vectors is an array of objects with string/int fields). State which path you
took in HANDOFF.

A binary `book1` (or `cargo run --bin book1 -- conformance <path>`) with a
`conformance` subcommand that reads `tests/spec_conformance/vectors.json`,
replays every vector, and prints per-vector `OK`/`FAIL` lines then exactly:
`RUST-CONFORMANCE: ALL PASS (49/49)` (or a nonzero exit with FAIL lines).
Also a `selftest` subcommand printing the genesis hashes and
`SELFTEST: ALL PASS` when H(I)/H(K)/H(S)/FALSE match the constants below.

## Normative rules to implement (from Book I; do not deviate)

**§1.1 OpCodes / Flags (u8):** `LITERAL=0x00, REF=0x01, APPLY=0x02,
RESERVED=0x03, DISSONANCE=0xFF`. Flags: `F_ATOM=0x01, F_LEFT=0x02,
F_RIGHT=0x04`. Required flags per opcode: LITERAL→F_ATOM, REF→F_ATOM,
APPLY→F_LEFT|F_RIGHT (0x06), DISSONANCE→F_ATOM.

**§2 canonical serialization:** `[Op:1][Flags:1][Atom?:32][Left?:32][Right?:32]`,
optional fields strictly in order Atom, Left, Right, present iff their flag
bit is set. **NodeHash = SHA-256(canonical bytes)**, 32 raw bytes; hex is
presentation only.

**§4.1 deserialization/validation (a buffer is valid iff ALL hold):**
1. len ≥ 2; read `op=buf[0]`, `flags=buf[1]`.
2. `flags & ~0x07 == 0`; `op` is in the table (0x03 and any other value →
   invalid); `flags` **exactly equals** the opcode's required value.
3. `expected_len = 2 + 32 * popcount(flags & 0x07)`; `len == expected_len`.
Invalid bytes → materialize the **Canonical Invalid Object** (§4.2):
`DISSONANCE` node whose atom is `SHA-256("Invalid Object")`.

**Reason hashes:** `R_INVALID=SHA-256("Invalid Object")`,
`R_ATP=SHA-256("ATP Exhausted")`, `R_UNRES=SHA-256("Unresolved Reference")`.

**§5.1 genesis (intrinsic):** `I/K/S` are LITERAL nodes with atoms
`SHA-256("I")`, `SHA-256("K")`, `SHA-256("S")`. Their NodeHashes are
recognized WITHOUT any store lookup. FALSE = `APPLY(⟨K⟩,⟨I⟩)` is a theorem,
constructed from H(K),H(I), no store. Expected constants (verify these):
- H(I) = `2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162`
- H(K) = `bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c`
- H(S) = `887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6`
- FALSE = `65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098`
- Canonical Invalid Object hash = `af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507`

**§3.3/§3.4 the v0.5 hash-thunk evaluator (this is the crux — match it exactly):**
Terms are graphs of materialized nodes over unresolved hashes (thunks). A
thunk holds a 32-byte hash. Node kinds: thunk, lit(atom), ref(target),
dis(reason), app(left, right) — where app children may themselves be thunks.

- **size** (hash-leaf model): `app → 1 + size(l) + size(r)`; `ref → 2`;
  thunk/lit/dis → `1`.
- **force(h, store):** genesis I/K/S synthesize their lit node without the
  store; else look up `store[h]` (store keyed by SHA-256 of bytes); missing →
  Unresolved; bytes failing §4.1 → the Canonical Invalid Object dis node;
  else deserialize (a fresh APPLY materializes with thunk children).
- **glyph recognition (§3.2, Identity by Hash):** a term is ⟨I⟩/⟨K⟩/⟨S⟩ iff
  its NodeHash equals H(I)/H(K)/H(S). For a thunk, compare its hash directly
  (no force); for a lit, hash it; app/ref/dis are never a glyph.
- **one priced step (leftmost-outermost, lazy left-spine):**
  - thunk h: if h ∈ {H(I),H(K),H(S)} → normal form (no cost); else if
    remaining < 1 → ATP Exhausted; else force → node v, cost = size(v)
    (1/2/3); if cost > remaining → ATP Exhausted (fetched bytes discarded);
    else step to v spending cost.
  - ref h: cost 1 → thunk h (R-R unwraps exactly ONE level).
  - lit/dis: normal form.
  - app(f,a): if f is ⟨I⟩ → a, cost 1 (R-I). Else if f=app(f1,f2) and f1 is
    ⟨K⟩ → f2, cost 1 (R-K; a/arg never forced). Else if f=app(app(f11,f12),f2)
    and f11 is ⟨S⟩ → app(app(f12,a),app(f2,a)), cost = **1 + size(a)** (R-S;
    the thunk leaves in `a` count 1 and are never forced). Else descend: take
    one step of f (with the same remaining); if it stepped, rebuild
    app(f',a); else f is normal, take one step of a → app(f,a'); else the app
    is normal form. **Exhaustion is checked BEFORE each action** (a cost
    `c > remaining` yields ATP Exhausted with `spent` unchanged; min action
    cost is 1, so `eval(REF(missing),0)` = ATP Exhausted decided before any
    fetch). A failed force (Unresolved) is NOT charged.
- **eval(term_hash, atp):** start from thunk(term_hash), loop stepping while
  affordable; the three canonical outcomes are: the step-normal term (its
  NodeHash is the result), `DISSONANCE(ATP Exhausted)` (atom R_ATP), or
  `DISSONANCE(Unresolved Reference)` (atom R_UNRES). Return
  `(result_node_hash, atp_spent)`. `eval` is TOTAL: no panic, no overflow —
  `spent` never exceeds `atp`. (You do NOT need resource-limit faults; the
  vectors don't exercise ResourceFault, and the memory bound `size ≤ spent+1`
  keeps growth bounded by the budget.)

## Vector replay (`tests/spec_conformance/vectors.json`, format_version 2)

- `objects`: map `hash_hex → bytes_hex`. Load each into the CAS; the key MUST
  equal SHA-256(bytes) — verify on load. One object is deliberately malformed
  (won't deserialize) — a CAS stores bytes, validity is decided at force.
- `kind:"object"`: `expected.hash` MUST equal SHA-256(bytes).
- `kind:"deserialize"`: `expected.valid` is `false` for all — the bytes MUST
  fail §4.1 validation.
- `kind:"eval"`: fields `term` (hash hex), `atp` (int), optional
  `store_subset` (list of object-hash keys: if present, eval against a store
  containing ONLY those objects). `expected.result_hash` and
  `expected.atp_spent` MUST both match your `eval(term, atp)`.

## Constraints

- Do NOT modify anything outside `impl-rs/` and `HANDOFF.md` — not `spec/`,
  `impl/`, `tests/`, `.warrants/`, `.github/`, `proofs/`, `examples/`,
  `tools/`, `proposals/`, `reviews/`.
- Build with `cargo build --release` inside `impl-rs/`; if offline vendoring
  is needed, `cargo build --offline` after `cargo fetch`, or vendor. Set
  `CARGO_HOME` under `impl-rs/` if the default is unwritable.
- The binary must run from the repo root as
  `./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json`.

## Report

Overwrite `HANDOFF.md` with: scope, dependency decision (sha2/serde vs
from-scratch and why), every reproducible command with full output (build,
selftest, conformance — all 49/49), and a Deviations section. An empty
Deviations section is a claim and will be adversarially checked against the
diff and against a fresh `cargo build` + conformance run by the maintainer.
