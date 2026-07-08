# HANDOFF

## Scope

- Added the independent Rust 2021 crate in `impl-rs/`.
- Implemented Book I canonical serialization, strict deserialization, node hashing,
  the intrinsic I/K/S genesis objects, FALSE, the canonical invalid object, the
  in-memory CAS, and the v0.5 hash-thunk evaluator.
- Implemented leftmost-outermost lazy left-spine reduction, one-level REF
  unwrapping, size-priced ATP accounting, intrinsic genesis lookup, unresolved
  reference handling, and invalid-object materialization.
- Added the `book1 selftest` and `book1 conformance <path>` command-line
  interfaces. Conformance validates every CAS key before replay and honors
  per-vector `store_subset`.

## Dependency Decision

The crate has no third-party dependencies. SHA-256 (FIPS 180-4) and the JSON
reader were implemented from scratch under `impl-rs/`, so the crate builds
offline without fetching `sha2`, `serde`, or `serde_json`.

## Acceptance Commands

### Release build

Command:

```sh
cd impl-rs
cargo build --release
```

Output:

```text
   Compiling sigma-glyph-book1 v0.1.0 (/Users/s0fractal/codex-rust/impl-rs)
    Finished `release` profile [optimized] target(s) in 0.88s
```

### Self-test

Command:

```sh
./impl-rs/target/release/book1 selftest
```

Output:

```text
OK  H(I) = 2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162
OK  H(K) = bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c
OK  H(S) = 887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6
OK  FALSE = 65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098
OK  Canonical Invalid Object = af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507
SELFTEST: ALL PASS
```

### Conformance

Command:

```sh
./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json
```

Output:

```text
OK  OBJ-I
OK  OBJ-K
OK  OBJ-S
OK  OBJ-FALSE
OK  OBJ-INVALID
OK  OBJ-DIS-ATP-EXHAUSTED
OK  OBJ-DIS-UNRESOLVED-REFERENCE
OK  OBJ-DIS-INVALID-OBJECT
OK  INV-EMPTY
OK  INV-SHORT
OK  INV-FLAGS-HIGH
OK  INV-OP-RESERVED
OK  INV-OP-UNKNOWN
OK  INV-FLAGS-MISMATCH
OK  INV-LEN-LONG
OK  INV-LEN-SHORT
OK  EV-GENESIS-BARE
OK  EV-LIT-FORCE
OK  EV-DIS-INERT
OK  EV-STUCK-DIS-FN
OK  EV-STUCK-LIT-FN
OK  EV-REF-COMBINATOR-FIRES
OK  EV-TV4-IK
OK  EV-TV4-IK-ATP0
OK  EV-TV4-IK-ATP2
OK  EV-TV4-IK-ATP3
OK  EV-TV5-SKKI
OK  EV-TV5-EXACT
OK  EV-TV5-UNDER
OK  EV-TV6-DUP
OK  EV-TV6-EXACT
OK  EV-TV6-UNDER
OK  EV-TV7-OMEGA
OK  EV-TV7-OMEGA-0
OK  EV-TV8-MISSING-CHILD
OK  EV-K-DEAD-MISSING
OK  EV-K-DEAD-NESTED-MISSING
OK  EV-S-KI-KK-DEAD-Z
OK  EV-REF-MISSING-ATP0
OK  EV-REF-MISSING-ATP1
OK  EV-REF-MISSING-ATP2
OK  EV-REF-MISSING-ATP3
OK  EV-REF-MISSING-ATP4
OK  EV-ROOT-MISSING
OK  EV-TV9-REF-CHAIN
OK  EV-TV9-REF-UNDER
OK  EV-GENESIS-INTRINSIC
OK  EV-BAD-BYTES-CHILD
OK  EV-TV10-C1-K

RUST-CONFORMANCE: ALL PASS (49/49)
```

## Deviations

None.
