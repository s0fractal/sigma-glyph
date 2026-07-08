# HANDOFF

## Scope

- Implemented the `gov-replay` subcommand in `impl-go/main.go`.
- Added an independent in-memory Go verifier for `spec/GOV-anchors.md` section 3:
  - closed schema validation for anchor-set blobs, governance profiles, trust configs, and Warrant v0.3 threshold policies;
  - canonical record-id integrity checks before accepting records into replay;
  - settlement closure from the pinned jurisdiction root through `prior` edges;
  - authorized profile lineage walking from the pinned genesis profile;
  - Ed25519 quorum verification over raw WarrantID bytes with distinct roster actors only;
  - governance-scoped key-state refusal;
  - exact current `{profile, threshold}` adoption checking;
  - rival authorized successor detection with chain-freeze refusal.
- Added `tests/governance_differential.py`, a black-box differential harness over all pinned governance vectors plus adversarial mutations:
  - tamper one signature byte;
  - strip all signatures from an adoption;
  - remove a lineage record;
  - replace `under` with a minted 1-of-1 profile/threshold pair;
  - flip the candidate blob jurisdiction;
  - orphan the adoption's `prior`;
  - duplicate the adoption under a rival valid anchor-set blob.

## Commands Run

### Build

Command:

```sh
cd impl-go && GOCACHE=$PWD/.gocache go build
```

Output:

```text
```

### Go Governance Replay

Command:

```sh
cd impl-go && ./sigma-federation-go gov-replay ../tests/spec_conformance/governance_vectors.json
```

Output:

```text
OK  GV-GENESIS-ADOPTED
OK  GV-SUCCESSION-ROTATED
OK  GV-ANCESTOR-FORK
OK  GV-GENESIS-WITH-ANCESTOR
OK  GV-HIJACK-MINTED-PAIR
OK  GV-UNDER-CARDINALITY
OK  GV-SIGS-BELOW-THRESHOLD
OK  GV-UNBOUND-KEY
OK  GV-BOUND-KEYS-AUTHORIZE
OK  GV-FOREIGN-JURISDICTION
OK  GV-ORPHAN-OUTSIDE-CLOSURE
OK  GV-COMPETING-SUCCESSORS
OK  GV-KEYSTATE-UNRELATED-IGNORED
OK  GV-KEYSTATE-UNAUTH-PROFILE
OK  GV-KEYSTATE-UNQUORUMED
OK  GV-KEYSTATE-QUORUM-REFUSED

GOVERNANCE-GO: ALL PASS (16/16)
```

### Governance Differential

Command:

```sh
python3 tests/governance_differential.py
```

Output:

```text
GOVERNANCE-DIFFERENTIAL: ALL AGREE (23/23)
```

### Federation Go Regression

Command:

```sh
cd impl-go && ./sigma-federation-go replay ../tests/spec_conformance/federation_vectors.json
```

Output:

```text
OK  FV-ASSERT-VALID
OK  FV-ASSERT-UNKNOWN-FIELD
OK  FV-ASSERT-PARTIAL-WAVE
OK  FV-POLICY-VALID
OK  FV-POLICY-BAD-FIELD
OK  FV-SELECT-LATEST
OK  FV-CONFLICT-TIE
OK  FV-STALE-EXCLUDED
OK  FV-SELECT-FUTURE-EXCLUDED
OK  FV-SELECT-ACTOR-DESC-PREFIX
OK  FV-SELECT-ACTOR-NONASCII
OK  FV-SELECT-NODE-FILTER
OK  FV-QUOTA-ACTOR-EPOCH
OK  FV-SELECT-BAD-METADATA
OK  FV-WAVE-ASSERTION-OVER-PIN
OK  FV-WAVE-STRUCTURAL
OK  FV-WAVE-APPLY-ASSERTION-OVERRIDES
OK  FV-VIEW-ID
OK  FV-SET-ROOT
OK  FV-FOLD-UNSOUND
OK  FV-BOOK-I-UNREACHABLE

FEDERATION-GO: ALL PASS (21/21)
```

### Federation Differential Regression

Command:

```sh
python3 tests/federation_differential.py
```

Output:

```text
FEDERATION-DIFFERENTIAL: ALL AGREE (40/40)
```

## Deviations

None.
