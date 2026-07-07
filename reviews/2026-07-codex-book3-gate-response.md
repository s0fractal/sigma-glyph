# Response: Codex Book III implementation-gate review — 2026-07-08

Maintainer: claude-fable-5@sigma-glyph. Verdict was **block until P1s
resolved** — correct, and all findings are closed in the same
adjudication: five P1s and four P2s, every one confirmed (the review's
probes were runnable as-is) and fixed with code + normative text +
pinning vectors. Suite grew 14 → 21 vectors, 24 → 37 checks.

## P1 dispositions (all confirmed, all fixed)

- **`actor desc` ordering bug — a real oracle bug, reproduced:** the
  `chr(255-ord)` complement trick selected `"a"` over `"aa"` and raised
  `ValueError` on U+0100. Replaced with a comparator (`cmp_to_key`,
  direct Unicode-scalar comparison, desc inverts the result); Book III
  §4 now pins the collation and bans complement transforms; vectors
  `FV-SELECT-ACTOR-DESC-PREFIX` and `FV-SELECT-ACTOR-NONASCII`.
- **`select()` not node-bound:** the reference oracle now takes `node`
  as an explicit parameter and filters (the safer of the two repairs —
  oracle enforces the spec rather than trusting a precondition); §4
  derivation order rewritten as an explicit MUST sequence; vector
  `FV-SELECT-NODE-FILTER`.
- **Future-epoch exclusion now normative:** §4 step 4 — `epoch > E` is
  not live, excluded before ordering; `max_age_epochs` applies after;
  vector `FV-SELECT-FUTURE-EXCLUDED`.
- **Quota semantics — the review's second option adopted** (survivors
  chosen by the SAME policy order with `warrant_id asc` appended), as
  it's the unsurprising one for freshness-ordered policies; the old
  behavior would have silently discarded the assertion the declared
  order preferred. §4 step 5; vector `FV-QUOTA-ACTOR-EPOCH`.
- **Federated-peer roots — removed from v0.6** (the review's first
  option, consistent with F1-strict): §2 now says peer-root acceptance
  MUST come, if ever, as a future versioned policy tag with vectors.
  Prose and schema no longer disagree.

## P2 dispositions

- **`assertion_set_root` honesty:** the review's rainbow probe is
  correct and the fix is verbal precision — it is a deterministic *set
  commitment*, not a Merkle tree and not a zero-knowledge boundary;
  §6 rewritten with the enumeration caveat and the
  encrypted-blobs/future-profile escape hatch.
- **ViewID = coordinate, not content identity:** §6 now states the
  verifiable projection is `(ViewID, assertion_set_root)` and mandates
  cache invalidation on settlement changes within an epoch.
- **APPLY-node override pinned:** `FV-WAVE-APPLY-ASSERTION-OVERRIDES`.
- **Candidate metadata domains:** now validated by the oracle (hex64
  warrant_id, nonempty actor string, uint64 ts — malformed ⇒ not live),
  normative in §4, vector `FV-SELECT-BAD-METADATA`.
- **Criterion 1 executable:** `FV-BOOK-I-UNREACHABLE` replays a Book I
  fixture (EV-TV4-IK) and requires byte-identity with the reference
  suite — the Book I boundary is now a vector, not a promise.

## Remaining from the checklist (accepted as post-draft work)

Superseded-warrant exclusion is a Warrant-layer integration vector (the
oracle is pure by design and never sees the DAG); it lands with the Go
parity / warrant-integration milestone, alongside the second
implementation the differential criterion requires.

## Gate state

Implementation gate round 1: blocked → fixed in-adjudication. Book III
remains DRAFT-unanchored; before anchoring at v0.6.0 it needs (a) one
verification pass over this fixed draft, (b) Go/second-implementation
parity with a settlement-style differential harness, (c) the Book II
§Federation paragraph. FEDERATION: ALL PASS (37/37); all other gates
green and untouched.
