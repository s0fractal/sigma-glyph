# PR 52 — Codex pre-merge review

Reviewed original head `28460e1eb7e3a74d239d34fdcc3d093443a6b9f9` against
`281a12517d188e20878ab064e8deca78aaf55cb0`. Claude authored the transition;
Codex inspected it and independently exercised counterexamples, then authored
the corrections below. Corrections are not an independent review of themselves.
No roster authority or normative adoption is asserted.

## Reproduced and corrected

1. **Subject omission hides resurrection.** In an isolated checkout, remove the
   `HANDOFF.md` row from work-orders-2026-07.json and restore its exact before
   bytes with `git show 281a125:HANDOFF.md`. The original whole checker exits 0,
   reports 3 VALID records and six postconditions despite the live retired file.
   The corrected checker refuses `SUBJECT_INVENTORY_MISMATCH:work-orders-2026-07`.
   Inventories independently bind each lineage's sorted (path, digest, mode)
   set. They cannot be edited solely by changing the data being checked.
2. **Relative zombie citation.** Feed surface_scan the retired path
   `reviews/2026-07-codex.md` and a tracked `reviews/README.md` containing
   `[current](2026-07-codex.md)`. Original scan accepts. Corrected scan refuses
   `ZOMBIE_REFERENCE`; same-directory and parent-directory mutations retained.
3. **Preservation overclaim.** For every subject compare SHA256 of
   `git show 7ecba6a:<path>` with its record. All paths exist but HANDOFF differs
   (the before revision adds a dated status envelope). 106 exact blobs match,
   not 107. Ledger and record policies now say so. This is source-revision
   verification, not public Zenodo download-back verification.
4. Narrowed the ledger's blanket statement that every July finding was
   adjudicated and dispositioned: it contradicted the retained residual list
   and the cross-family round's explicit lack of warrants.

## Validation and limits

- 43 selftest controls; three VALID records; six replayed postconditions.
- Original live omission + resurrection counterexample replayed after fix:
  refuses, exit 1. Temporary mutations restored; no changes to historical blobs.
- All 107 subjects equal the actual deletion set at the apply commit, with no
  overlaps. Each before-revision digest is checked by the normal consumer.
- repo_map --check-map, verify_anchors, version_check, paper_claims (94/94),
  and git diff --check pass locally. Final exact-head CI is required before merge.
- The local inventory is a review-visible fixture, not protection against an
  author who edits both checker and records. Zombie scanning is lexical over
  tracked UTF-8 text, not a complete Markdown/URL parser or all-file admission
  system. Existing exclusions remain explicit.
- Lean runner residual, missing August response, and historical exp-001 replay
  boundary remain open. Retirement neither fixes nor hides them.
- Use a merge commit, preserving the actual before/apply/receipt ancestry.
  Squash or rebase would discard the durable reachability of pinned commits.

User explicitly authorized Codex to perform the final merge if review passes.
