# Full-system audit before the next Zenodo version

**Date:** 2026-08-29  
**Reviewer:** Codex  
**Target:** `master@c60594e0e977cff2423b418d0af470689d82f8ca`  
**Disposition:** findings filed; release and normative adoption are not implied

## Scope and epistemic boundary

This review covers the current Book I implementation, the Python/Rust/Go and
Lean gates, specification/version/release surfaces, the two open pull requests,
the public GitHub and SonarCloud state, and the deposited Zenodo record
`10.5281/zenodo.22069651` (`7ecba6a`).  It does not claim independent adoption,
peer review, or correctness outside the predicates actually exercised below.

`tools/test-all.sh` completed at the target SHA with no accepted skips.  That is
the baseline, not the verdict: the suite replays declared surfaces and cannot by
itself establish that the declarations cover the public claims.

## Findings

### P0 — the deposited paper is no longer a truthful description of the tree

The Zenodo version is correctly frozen, but several load-bearing statements in
its PDF are false of the current repository and two were already false when
written:

- the headline interface names `(term_hash, atp)` although evaluation depends on
  a third input, the content store;
- `result_hash` does not identify the exit: a normal form can have the same hash
  as the canonical ATP-exhausted term;
- the paper says 36 guarded theorems and 11 evaluator theorems.  The current
  registry has 41 guarded theorems (2 + 12 + 16 + 6 + 5), 44 statement pins and
  156 definition pins;
- the paper's implementation and Lean line counts predate the merged
  store-monotonicity work (`proofs/*.lean` is now 1,404 lines);
- “peak memory” is a theorem about semantic materialized-node count.  It is not
  a bound on RSS, stack, allocator overhead, transient old-and-new terms, store
  indexes, or SHA buffers;
- “safe to run a stranger's computation by construction” omits the local
  admission decision.  The normative maximum permits a 32-bit ATP claim; the
  verifier must choose and enforce a smaller operational limit before touching
  the store.

`tools/paper_claims.py` still prints green because it checks seven counts from
the *proof-guard companion paper*.  It explicitly leaves the engine paper's
complexity and benchmark claims unchecked.  A green `PAPER-CLAIMS` line is
therefore not evidence that the Zenodo paper is current.

**Required before a v2 deposit:** rewrite the paper rather than append a third
correction; qualify memory as semantic materialization; state the fixed-content
environment and exit receipt; recount from the release candidate; rebuild the
PDF; archive exactly that candidate; and make the Zenodo metadata repeat the
same bounded claims.

### P1 — the normative interface still omits consensus inputs and output state

Book I 0.5.2 still specifies
`eval(term_hash, atp) -> result-node` and says the answer is identical on all
nodes.  The executable relation is over `(term_hash, atp, store)`, and the
result node alone cannot distinguish normal completion from exhaustion.

The next Book I edition needs to define:

1. a valid partial CAS view (`NodeHash -> exact canonical bytes`);
2. determinism for the same demanded content, not merely the same term/budget;
3. monotonicity under valid store extension (only `Unresolved` may change);
4. an execution receipt carrying at least `exit`, `result_hash`, and
   `atp_spent`; and
5. refusal of bytes returned under a key that is not their SHA-256.

PR #24 fixes the oracle-precedence clause but does not fix this interface.

### P1 — PR #24 is knowingly incomplete as an adoption candidate

The candidate correctly removes Python's authority over Book I prose and fixes
the genesis convention.  It also records that it cannot be adopted as-is:

- Book II retains “the oracle wins”;
- Book III retains the same rule and falsely attributes it to Book I section 7,
  which the candidate removes;
- Book II and Book III suite versions already disagree with their Books; and
- the Book I store/receipt defect above remains in the anchored text.

A release candidate should resolve these in one frozen normative set or split
them into explicitly ordered candidates.  Adopting #24 unchanged would create a
new anchor with a known false cross-reference.

The PR's displayed checks are also stale: they ran against base `d3f1b51`,
before `version_check.py` entered `master`.  Applying #24 to the audited target
and running that check produced `FAIL README calls v0.6.7 current and the top
ANCHORS section is v0.7.0`.  README is correct: the labelled candidate is not in
force.  The audit branch changes the version checker to skip candidate headings
and adds a negative selftest so a proposal cannot become “current” by being
placed first in the file.

### P1 — the Python oracle accepted a broken content-addressed store

Reproducer against the audited target:

```python
fake = sha(b"claimed-key")
eval_hash(fake, 10, {fake: I_BYTES})
```

The oracle returned `I` after one ATP although `SHA-256(I_BYTES) != fake`.
Rust rejects an equivalent suite load, and the Lean `Store` lookup is defined by
the bytes' actual hash.  A plain mapping passed to the public Python API could
therefore violate Identity by Hash and disagree with the other engines.

The same boundary accepted `atp=-1`, `1.5`, and `True` even though the consensus
domain is `uint32`.  The audit branch adds fail-before-execution validation and
`tests/oracle_input_boundary_test.py` for both defects.

### P1 — “Edit the Cop” is reproduced in the live repository policy

The public repository currently reports no rulesets and no protection for
`master`.  Thus a change can edit the proof, `proof_guard.py`, its regression
tests, and the workflow that invokes them in one commit.  Green CI establishes
only that the commit's own chosen controls accepted it.  The previously recorded
V22 candidate is therefore confirmed at the repository-control layer.

Branch protection cannot make the repository owner unable to rewrite history,
but required checks plus an external immutable pin materially reduce accidental
or agent-driven self-approval.  This is an external governance change, not a
source-code patch, and needs owner authorization.

### P2 — SonarCloud's green gate hides the current security debt

The public API reports 14 unresolved issues on `master`: 8 code smells and 6
items classified as vulnerabilities; the project security rating is `C`.
The quality gate is green because its conditions apply to “new code” since the
previous version, not because the project has no open findings.

Several security findings are expected capabilities or false positives
(`subprocess.run(..., shell=False)`, deterministic test PRNG, explicit local
output paths), but they must be dispositioned individually.  A green badge must
not be summarized as “Sonar found nothing.”

### P2 — DA-SIGMA-0002 does not present a `k` versus `k-1` owner choice

PR #25's corrected head already contains the decisive answer: Book I section
3.4 permits physical sharing and requires reported ATP to match tree accounting.
The proposed capability exists.  The correct owner disposition is
`existing-contract`; `k` and `k-1` would describe a different ALife metabolic
metric and must not be reported as Sigma-Glyph `atp_spent`.

## Release order

1. Land the non-normative/runtime audit fixes with their negative controls.
2. Resolve #25 as `existing-contract`; it is evidence routing, not a Book change.
3. Supersede or extend #24 so all changed Books/suites form one coherent frozen
   candidate, including the store/receipt boundary.
4. Run a fresh multi-family gate over the exact normative bytes.  Test authors
   and candidate authors are evidence sources, not independent adoption votes.
5. File the threshold adoption warrant and only then promote the anchor section.
6. Recount and rewrite the paper against the adopted candidate; make the paper
   claims gate cover its headline quantities and explicit blind spots.
7. Build the PDF and repository archive from a clean exact-SHA tree, verify their
   digests, prepare Zenodo metadata, and publish a new version under concept DOI
   `10.5281/zenodo.22069650` only after an explicit final authorization for those
   exact outward-facing bytes.

Until step 7, the existing DOI remains a truthful frozen record of what was
deposited, but not a current statement of Sigma-Glyph.
