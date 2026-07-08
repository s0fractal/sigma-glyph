# BRIEF: Go second implementation of the GOV-anchors.md verifier

You are implementing the second, independent implementation of the anchor
governance verification defined in `spec/GOV-anchors.md` §3 (read it first —
it is normative and short). The Python reference is
`tools/anchor_governance.py`; you MAY read it to resolve ambiguity, but your
implementation must be your own logic, not a transliteration.

## Deliverables

1. **`gov-replay` subcommand** in the existing Go binary (`impl-go/main.go`,
   module `sigma-federation-go`):

   ```sh
   cd impl-go && GOCACHE=$PWD/.gocache go build
   ./sigma-federation-go gov-replay ../tests/spec_conformance/governance_vectors.json
   ```

   For each vector: reconstruct the embedded `.warrants` store (records +
   hex-encoded blobs) in memory or a temp dir, run the §3 verification of
   `vector.candidate` against `vector.trust` and `vector.prior_set`
   (`null` ⇒ genesis), and compare BOTH `expected.authorized` AND that
   `expected.note` occurs as a substring of your verdict notes. Print
   `OK  <id>` per vector and finish with exactly:
   `GOVERNANCE-GO: ALL PASS (16/16)` (nonzero exit + FAIL lines otherwise).

2. **`tests/governance_differential.py`** — black-box differential harness
   (stdlib + `cryptography` only), following the style of
   `tests/federation_differential.py`. For every pinned vector AND for a set
   of adversarial mutations you construct on top of them (at minimum: tamper
   one signature byte; strip all sigs from the adoption; remove a lineage
   record; replace `under` with a minted 1-of-1 pair; flip the blob
   jurisdiction; orphan the adoption's `prior`; duplicate the adoption under
   a rival blob), run BOTH implementations and require identical
   `authorized` verdicts. Python side: invoke
   `tools/anchor_governance.py replay <tempfile>` on a single-vector file
   (mutated vectors carry `expected` from the PYTHON verdict — the harness
   asserts agreement, not correctness). Finish with exactly:
   `GOVERNANCE-DIFFERENTIAL: ALL AGREE (<n>/<n>)`.

## Normative requirements (from GOV-anchors.md §3 — all MUST hold)

- Fail closed: unable to verify Ed25519 ⇒ refuse to authorize.
- Schema-closed blobs (unknown fields invalid): anchor-set (jurisdiction
  embedded, genesis omits ancestor, anchors sorted by path, unique), profile
  (hash-pins threshold), Warrant v0.3 threshold grammar (exact two top-level
  fields; unknown fields inside `threshold` invalid; `1 ≤ min_sigs ≤
  len(actors)`, actors unique non-empty strings; booleans are NOT integers).
- Record integrity: a record whose id ≠ SHA-256(canonical body) is skipped.
  Canonical JSON = RFC 8785 profile used repo-wide: sorted keys, no
  whitespace, UTF-8 (not \u-escaped), integers only.
- Settlement closure: only records reachable from `trust.jurisdiction` via
  `prior` edges count (root + descendants, fixpoint).
- Policy lineage from `trust.genesis_profile`: a hop is an `accept` whose
  subject is a valid profile blob, `under` == exactly {current profile,
  its pinned threshold}, signatures ≥ current `min_sigs` distinct roster
  actors with keys bound in `trust.actors`. Two unconsumed successors at a
  hop ⇒ succession conflict (refuse).
- Key state: refuse ONLY for key-state-shaped subjects (`{"actor","key"}`)
  filed under an authorized-lineage policy hash AND carrying that policy's
  quorum; anything else is ignored (unauthorized key-state = invalid record).
- Adoption: `under` exactly {current profile, its threshold} (len 2);
  signatures counted once per distinct roster actor, key must be bound,
  Ed25519 over the raw WarrantID bytes (hex-decoded).
- Rival authorized adoption of a DIFFERENT valid anchor-set with the same
  ancestor ⇒ chain frozen (refuse). No tie-breaks of any kind.
- Note strings need not match Python word-for-word, but for each vector your
  notes MUST contain the `expected.note` substring — treat those substrings
  as normative verdict vocabulary: `adopted by`, `fork, not upgrade`,
  `must not carry an ancestor`, `no satisfying adoption warrant`,
  `under != current (profile, threshold) pair`, `bound sigs < min_sigs`,
  `replay refused`, `chain frozen`, `warrant CLI`.

## Constraints

- Go stdlib only (`crypto/ed25519`, `encoding/json`, etc.); build with
  `GOCACHE=$PWD/.gocache` inside `impl-go/`.
- Do NOT modify: `spec/`, `tools/`, `impl/`, existing tests, `.warrants/`,
  `.github/`, `examples/`, `proposals/`, `reviews/`.
- Existing subcommands must keep working:
  `./sigma-federation-go replay ../tests/spec_conformance/federation_vectors.json`
  must still print `FEDERATION-GO: ALL PASS (21/21)`, and
  `python3 tests/federation_differential.py` must still print
  `FEDERATION-DIFFERENTIAL: ALL AGREE (40/40)`.

## Report

Write `HANDOFF.md` (overwrite) with: scope, every reproducible command you
ran with full output (build, gov-replay, governance differential, federation
regression), and a Deviations section — if you intentionally deviate from
this brief anywhere, say exactly where and why. An empty Deviations section
is a claim, and it will be adversarially checked against the diff.
