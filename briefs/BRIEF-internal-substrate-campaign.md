# BRIEF: Make Sigma-Glyph an internal substrate

Status: owner-approved execution brief, non-normative.

This file authorizes preparation and review work. It does not adopt an ADR,
change a Specification Anchor, authorize a merge, publish a release, or create
authority on behalf of a roster member.

## Owner decision

For this campaign, assume that no outside implementer, user, or reviewer ever
arrives. Build for the owner's repositories, future clean-room rebuilds, and
agents that do not inherit the session in which a feature was written.

External adoption is therefore not the primary success metric. External
validation remains necessary only for claims that are explicitly external:
independent implementability, novelty, general usefulness, portability across
uncontrolled implementations, or public adoption. Do not use the absence of
strangers to excuse an external claim, but do not require strangers to justify
an internal tool.

The campaign succeeds when another owned repository consumes a released,
pinned Sigma boundary without copying its evaluator, relying on a Sigma source
checkout, or inheriting hidden state from the author's machine.

The strategic thesis is:

> Re-executability does not eliminate persuasion. It shrinks persuasion's
> jurisdiction to the choice of what to check. Inside this ecosystem, the
> practical test is whether a claim can cross a repository boundary as bytes,
> inputs, and a receipt instead of as trust in the producing session.

## Starting snapshot

These facts were rechecked on 2026-08-31. They are a starting snapshot, not a
substitute for checking the live repository before acting.

- `sigma-glyph/master`:
  `0481bd0ea2c8b66d26f31edbdb1bcdb4ec1634f4`.
- Adopted anchor-set release: `v0.7.0`.
- Anchor-set blob:
  `abf10f2a9c932f31e28973c41658ba728501fef438b35b7538e78c21d37adf59`.
- Adoption warrant:
  `0e634c176b002d02d835e5c6436e4b254d065adeab4bc7704585339567ba46e1`.
- Book I anchor:
  `e3e5d00863d7dcf875258168029611949339fe307ad3d9e5e565c12543cc94fd`.
- Raw SHA-256 of the current `spec/book-1-truth.md`:
  `f5aadc405c1c7d9f4d2e1f0431c91f40027e6b4037b43c2cbf6b278f4093ac6`.
  This is a raw-file digest, not the Book I Specification Anchor.
- `manifesto/main`:
  `8d36a9e3c2fb75d0edc7b85b7c13bbb49c0d8e3a`.
- The existing local ADR-012 worktree is
  `/Users/s0fractal/Projects/.worktrees/sigma-glyph-surface`, branch
  `proposal/stranger-verification-surface`, head
  `9b45f7965a9e8105f65b0f9be05ebe27474daf6b`.
- The deposited engine-paper record is version DOI
  `10.5281/zenodo.22069651`, concept DOI
  `10.5281/zenodo.22069650`, version label `0.6.7-paper1`.
- The committed `papers/one-integer-for-work-and-memory/paper.pdf` is the
  deposited v1 artifact. It is historical evidence and MUST NOT be overwritten
  by the v2 build.
- ADR-011 is merged as a non-normative proposal. It is not adopted.
- `EXP-ADR011-01` is pre-registered and has not started.

Before each phase, re-read the relevant repository's `AGENTS.md`, record the
actual branch and SHA, and report any divergence from this snapshot before
building on it.

## Common working protocol

Apply these rules to every phase.

1. Work on a dedicated branch or worktree. Never commit directly to
   `master`/`main`.
2. Preserve existing dirty and untracked files. Do not stage, delete, rename,
   or absorb work from another session.
3. Keep phases in separate commits and separate pull requests. A paper
   correction, a manifesto correction, an ADR, and an implementation are four
   different review subjects.
4. Reproduce a defect before correcting it. A historical statement may be
   retained if visibly labelled historical; do not silently make the past say
   what is true now.
5. A check is not load-bearing until the guarded implementation has been
   mutated and the check has been seen to fail for its stated reason.
6. Counts and digests in a report must come from the files on disk at the exact
   reported SHA. A terminal probe is not a repository artifact.
7. A green CI board establishes only that the scripts in that revision were
   green. It is not independent review, adoption, publication, semantic truth,
   or evidence of external usefulness.
8. State the blind zone of every audit. Prefer a finite inventory of what is
   checked and what is not checked over a broad claim such as "the paper is
   consistent" or "the interface is portable".
9. Do not use OpenRouter for ordinary engine, test, documentation, or internal
   consumer changes. Codex-plus-Claude review is sufficient for non-normative
   internal work unless normative anchored bytes move or an external claim is
   being made.
10. Stop before any action explicitly reserved to the owner at the end of this
    brief.

## Campaign order

Execute the phases in order. Phase 4 is a plan only until ADR-012 has been
reviewed and the owner explicitly authorizes implementation.

---

## Phase 1 — Correct the engine paper and prepare a Zenodo v2 candidate

### Objective

Bring the paper into temporal agreement with the adopted v0.7.0 repository
state, strengthen the machine audit over the claims that actually changed, and
produce a reproducible v2 deposit candidate without altering the deposited v1
artifact or uploading anything.

### Required reading

- `papers/one-integer-for-work-and-memory/paper.md`
- `papers/one-integer-for-work-and-memory/README.md`
- `tools/paper_claims.py`
- `spec/ANCHORS.txt`
- `.warrants/records/`
- `CHANGELOG.md`
- `gates/v0.7.0-candidate/round-6/AMENDMENT.md`
- `proposals/ADR-010-three-inputs-and-a-receipt.md`
- the current Zenodo record metadata and downloaded v1 files

### Defect to reproduce first

The paper still describes v0.7.0 as a candidate, says it is not adopted, and
names v0.6.7 as the most recent adopted anchor set. Show each stale statement
with file and line before changing it. Also distinguish:

- measurements made at a candidate implementation commit;
- normative claims now adopted in v0.7.0;
- later non-normative ADR-011 work;
- the immutable deposited v1 artifact;
- the proposed v2 correction.

Do not rewrite a historical account merely because the candidate later became
adopted. Where the date of observation matters, write both temporal facts: what
was true when measured and what is true at v2 publication time.

### Paper changes

At minimum, make the paper state accurately:

- the exact adopted `v0.7.0` anchor-set digest;
- the full adoption-warrant ID and the fact that it has the threshold required
  by the roster;
- the current Book I document version and anchor;
- the distinction between the commit at which measurements were taken and the
  specification edition now in force;
- the exact status of ADR-011: merged proposal, non-normative, not adopted;
- that `church@v0` cannot settle `PLUS 7 5` and `EXP-ADR011-01` has not started;
- that two full-receipt Book I implementations and one compatibility-profile
  verifier were the honest description until the later Warrant-Go receipt work;
  re-measure the current statement rather than copying this sentence if that
  work has since landed;
- that green repository checks are bounded evidence about named predicates, not
  proof that all prose and all artifacts agree.

Preserve the deposited v1 correction history. Do not imply that the v1 PDF was
silently changed after deposit.

### Claim audit

Extend `tools/paper_claims.py` only with exact predicates the tool can actually
decide. At minimum cover:

- current bundle/release identifier;
- complete anchor-set digest;
- complete adoption-warrant ID;
- absence of a current-tense `not adopted` statement about v0.7.0;
- current source/artifact location used by the reproduction instructions;
- every changed number, SHA, count, or version in the v2 patch.

For every new predicate, add a mutation that changes only its subject and
requires the audit to fail for that predicate. Do not promote a prose parser
into a semantic verifier. Its output must print what it decided and identify
what remains outside its contract.

### Reproducible v2 package

Build the v2 candidate in a clean checkout at an exact SHA. Do not overwrite
`paper.pdf`. Produce a separate staging directory containing at least:

- the new PDF;
- the source Markdown and bibliography/assets required to rebuild it;
- a source archive pinned to the reviewed SHA;
- a manifest with filenames, sizes, SHA-256 digests, build command,
  `SOURCE_DATE_EPOCH`, tool versions, source commit, adopted anchor-set digest,
  and adoption-warrant ID;
- a download-back verification procedure for use after eventual publication.

Build twice from clean state and compare bytes. If byte-identical output is not
achievable, record the exact nondeterministic fields and compare normalized
content; do not call it reproducible without saying which sense is meant.

Render every page and inspect it visually. Check title/author metadata, table of
contents, links, code blocks, Unicode, page breaks, bibliography, DOI note, and
the visible v1-to-v2 correction statement.

### Phase 1 output

- one dedicated branch;
- one draft PR, clearly labelled paper-v2 candidate;
- a report with exact SHA, changed claims, audit predicates, mutation results,
  build commands, PDF page count, file digests, and stated blind zones;
- no merge, tag, release, Zenodo version creation, upload, or publication.

---

## Phase 2 — Apply the eleven manifesto corrections without rewriting history

### Objective

Transfer the factual corrections discovered by ADR-011 into the manifesto
repository while preserving AIE-0.1 as a historical publication and without
letting the safer Sigma profile inherit results it never produced.

### Source of truth for the correction set

Read the complete file:

`/Users/s0fractal/Projects/sigma-glyph/proposals/adr-011/MANIFESTO-CORRECTIONS.md`

Treat its eleven items as claims to reproduce against the live
`/Users/s0fractal/Projects/manifesto` checkout, not as text to paste blindly.
Record the live `manifesto/main` SHA before editing.

### Required result

Choose the repository's existing correction mechanism if it has one. Otherwise
add a clearly visible errata/supersession document and link it from every
current entry point that could lead a reader to the affected AIE-0.1 claims.
Preserve the original deposited text and date.

The corrections must retain these boundaries:

- one observation point does not establish equality of arbitrary terms;
- identical result addresses do not by themselves imply identical receipts or
  exits;
- ATP exhaustion and other canonical exits cannot be collapsed into equality;
- the two sides need independent admission, observation, and evaluation status;
- sequentially sharing one budget or a mutable observation environment can make
  the result order-dependent;
- `profile_id` is a label, not identity;
- the current local `profile_commitment` is not a portable,
  cross-implementation descriptor;
- the `601 ATP` and related `PLUS 7 5` result belongs to the permissive
  `manifesto/tools/glyphlib.py` experiment, not to `church@v0`;
- `church@v0` is a safety reference for written-out numerals and does not admit
  the computed Church expression that motivated ADR-011;
- cross-agent justification deduplication remains blocked while portable
  settlement is blocked;
- marker digests must name the marker set that produced them; do not cite the
  ad-hoc `sha("X")` digest as if it came from `EqualityProfile`.

Regenerate and verify the SSD pack using the manifesto repository's own
declared commands. Add negative controls for every newly enforced correction
that can be made mechanical. Print what remains an argument or documentation
claim rather than reporting all eleven as machine-proved.

### Phase 2 output

- a separate branch and draft PR in `manifesto`;
- an explicit mapping from C1-C11 to files, lines, tests, and any unresolved
  judgment;
- regenerated artifacts and their digests where the repository requires them;
- no rewrite of the deposited AIE-0.1 artifact, no Zenodo action, no merge.

---

## Phase 3 — Reframe ADR-012 as a checkout-independent consumer surface

### Objective

Turn the existing stranger-facing proposal into a narrowly scoped internal
dependency proposal. The surface must serve owned repositories without relying
on a Sigma checkout or copied evaluator. It must not pretend to solve general
language embedding, arbitrary equality, or public adoption.

### Existing work to preserve

The unpublished worktree is:

`/Users/s0fractal/Projects/.worktrees/sigma-glyph-surface`

Its branch is `proposal/stranger-verification-surface`, recorded head
`9b45f7965a9e8105f65b0f9be05ebe27474daf6b`. It was based on an older master.
Record its actual head, dirty state, and merge base before changing anything.
Because the branch is unpublished, it may be rebased locally onto current
`master` after preserving the old head in the report. Do not rebase or
force-push a shared branch.

Read the full existing proposal and preserve the useful technical core. Rename
and rewrite it around **checkout-independent consumers**, not strangers.

### Contract to keep

The proposal should retain:

- the exact Book I relation with three explicit inputs: term/root, ATP budget,
  and content environment;
- the complete Receipt: `exit`, `result_hash`, `atp_spent`;
- no boolean `.ok` that conflates canonical exits, admission refusal, and local
  faults;
- a filesystem CAS adapter compatible with Warrant's `.warrants/blobs` layout;
- explicit local limits and their refusal/fault surface;
- a reproducible conformance asset made from adopted bytes;
- no Python, Jupyter, pytest, or arbitrary-JSON frontend in the protocol
  surface;
- no new signing envelope or authority layer: Warrant owns envelopes,
  signatures, key state, and settlement authority;
- demand-first store access, hash verification, path containment, and no
  recursive directory trust.

### New success metric

Replace every external-adoption metric with a measurable internal boundary:

1. Two owned repositories consume the same released and digest-pinned Sigma
   artifact.
2. Neither consumer vendors or reimplements the evaluator.
3. Neither consumer requires a Sigma source checkout, repository-relative path,
   mutable environment variable, or hidden local cache.
4. A clean environment reproduces the same full Receipt from the same three
   inputs.
5. An upgrade either reproduces the pinned behavior or fails closed at the
   boundary; it never silently changes a receipt.
6. Mutating each of `exit`, `result_hash`, `atp_spent`, blob bytes, artifact
   digest, Book anchor, and output schema makes at least one consumer gate fail
   for the named reason.
7. The shared layer deletes more consumer glue and duplicated semantic code than
   it adds in packaging and integration machinery.

The initial consumers are:

- Warrant's `ski@v1` evidence/replay path;
- the manifesto SSD pack.

Inspect both live consumers before asserting the exact integration seam. Do not
invent an API from remembered repository structure.

### Honest scope statements

The ADR must say explicitly:

- ADR-011 is a merged, non-normative proposal, not an adopted Sigma rule;
- `EXP-ADR011-01` has not started;
- `church@v0` cannot settle `PLUS 7 5`;
- portable equality settlement remains blocked because Sigma has no adopted
  content-addressed profile descriptor;
- this proposal exposes adopted Book I evaluation; it does not add kernel
  equality, a raw-byte frontend, Python-to-SKI compilation, or a universal
  application language;
- internal use is evidence of usefulness to this ecosystem, not evidence of
  general public utility or independent implementability.

### Phase 3 output

- a rebased/updated dedicated branch;
- the old and new branch heads recorded;
- one draft ADR PR against current `master`;
- no implementation, no normative Book edit, no anchor change, no OpenRouter
  gate, no merge.

Stop after owner/Codex review of this ADR. Phase 4 does not start merely because
the PR is green.

---

## Phase 4 — Implementation plan only

Do not write implementation code in this campaign run. Prepare the following
plan as a reviewable appendix to ADR-012 or a separate non-normative design
note.

### Minimal interface

The first candidate interface is intentionally small:

```text
sigma-glyph eval \
  --term <hex64> \
  --atp <uint32> \
  --blob-dir <path> \
  --max-* <explicit-local-limits> \
  --json
```

The exact executable/package name is a packaging decision, not a normative
Book change.

### Output and process status

On successful Book I evaluation, emit the full Receipt only:

```json
{
  "exit": "normal_form | atp_exhausted | unresolved_reference",
  "result_hash": "<hex64>",
  "atp_spent": 0
}
```

Do not add `ok`. Canonical exhaustion and unresolved-reference outcomes are
successful executions of the evaluator and should not be reported as process
failures. Malformed caller input, rejected content environment, and local
resource/tool faults need separate nonzero process exits and machine-readable
diagnostics. Pin the exact taxonomy before implementation.

### Store boundary

The plan must require:

- validate the term hash, ATP value, path, and local-limit arguments before any
  store read;
- fetch only hashes demanded by evaluation;
- never recurse over or trust an entire directory;
- reject path and symlink escapes;
- verify every loaded blob against the hash used to request it;
- distinguish missing content from malformed content and from a local I/O or
  resource fault;
- state whether blob filenames are lowercase hex and whether extra files are
  ignored or rejected.

### Release and conformance asset

Plan a release artifact that can be installed in a clean environment and is
pinned by a cryptographic digest. Its conformance asset must derive from the
adopted anchor-set bytes and must identify:

- release/package version;
- source commit;
- Book I anchor and anchor-set digest;
- suite/schema digests;
- supported platform/toolchain matrix;
- exact command and expected closed-set test inventory.

The artifact must not require network access after installation for local
replay.

### Consumer integration plan

For both Warrant and manifesto, specify:

- the exact current glue or evaluator code to be removed;
- the pinned artifact/digest and installation boundary;
- the three inputs supplied by the consumer;
- how the full Receipt is preserved without boolean collapse;
- clean-environment reproduction;
- upgrade procedure and rollback/fail-closed behavior;
- negative controls proving that the consumer depends on the released boundary
  rather than a copied implementation or source checkout.

The breaking-change drill must mutate, independently:

- `exit`;
- `result_hash`;
- `atp_spent`;
- one demanded blob byte;
- package/artifact digest;
- Book anchor or anchor-set digest;
- JSON field name/type or an unexpected field.

Each mutation must fail at the consumer that claims to bind that field, and for
the stated reason. A closed test set is preferred: adding or removing a test is
itself a visible contract change.

### Kill criteria

Recommend freezing or deleting the surface if any of these remains true after
the two integrations:

- it requires a new language or frontend to be useful;
- it creates a second envelope, signing, or authority protocol;
- consumers still vendor evaluator logic or require a Sigma checkout;
- it adds more maintained glue than it removes;
- full Receipt fields are collapsed or discarded at either consumer;
- upgrades cannot be pinned and made fail-closed;
- the only demonstrated benefit is that Sigma can call itself through a new
  wrapper.

## Explicit freezes

This campaign does not authorize work on:

- `EXP-ADR011-01`;
- kernel equality or adoption of ADR-011;
- new Book II or Book III semantics;
- Python-to-SKI compilation;
- Jupyter, pytest, ML, or arbitrary-language frontends;
- a new signing envelope, key system, governance layer, or transport protocol;
- Decision Archaeology, Kherson, ALife expansion, or unrelated repositories;
- outreach, mailing lists, an external-adoption campaign, or paid OpenRouter
  review for non-normative changes;
- another paper after the engine-paper v2 candidate.

If a phase appears to require one of these, stop and report the dependency. Do
not smuggle it in as implementation detail.

## Authority granted by this brief

The owner authorizes the agent to:

- inspect the in-scope repositories and public Zenodo record;
- create local worktrees and feature branches;
- edit the files required by Phases 1-3;
- run local tests, clean builds, renderers, and read-only verification;
- commit phase-scoped changes;
- push feature branches;
- open draft pull requests;
- prepare, but not publish, the paper-v2 deposit package.

The following still require a fresh, literal owner instruction at action time:

- merge to `master`/`main`;
- mark a PR ready if draft status is part of the review boundary;
- rewrite shared history, squash, rebase a shared branch, or force-push;
- tag, release, publish to PyPI, create or publish a Zenodo version, or upload
  public artifacts;
- sign or file an adoption warrant;
- edit adopted normative bytes or re-anchor a specification;
- start `EXP-ADR011-01`;
- contact anyone outside the owner's repositories;
- spend OpenRouter or other paid-review budget.

## Required reporting format

For each phase, report:

1. exact repository, branch, base SHA, head SHA, and working-tree status;
2. scope actually changed and files deliberately untouched;
3. every claim reproduced before correction;
4. commands run and their exact closed-set counts;
5. mutations run, the defect each restores, and the reason-specific failure;
6. artifacts produced with sizes and digests;
7. what the green result establishes and what it does not;
8. any deviation from this brief;
9. the next irreversible action, left unperformed.

Do not report a phase complete merely because its PR is green. Complete means
the phase's artifact exists at the reported SHA, its controls have been shown
discriminating, its blind zone is printed, and the next action is explicitly
separated.

## Campaign completion condition

This brief is complete when:

- the engine-paper v2 exists as a reproducible, reviewed deposit candidate;
- the eleven manifesto corrections exist in a reviewed draft PR without
  rewriting the deposited historical artifact;
- ADR-012 is reframed and reviewed as a checkout-independent internal consumer
  surface;
- the implementation plan is precise enough to falsify the two integrations;
- no merge, adoption, publication, experiment start, or outreach has been
  inferred from preparation authority.

The next campaign, if separately authorized, is implementation of the accepted
ADR-012 boundary in Sigma followed by Warrant and manifesto as the first two
consumers. Its evidence is not attention from strangers. Its evidence is that
the same pinned bytes replace duplicated semantics in two repositories and
continue to produce the same receipt after the authoring session is gone.
