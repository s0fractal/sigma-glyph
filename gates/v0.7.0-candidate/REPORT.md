# v0.7.0 candidate — final report

Written at `461fe7b6ffcf3f9235d546fac6642601b66f1c24`, branch
`spec/book1-v0.7.0-candidate`, draft PR #35, title
"CANDIDATE v0.7.0 — three inputs, a receipt, one arbiter (NOT ADOPTED)".

**Status: NOT READY FOR ROSTER SIGNATURES.** Two things are missing, and only one
of them was known in advance. They are in §10.

---

## 1. What changed in each Book

### Book I — `spec/book-1-truth.md`, 0.5.2 → 0.6.0

| Section | Change |
| --- | --- |
| §3.4 | The interface is `eval(term_hash, atp: uint32, env) → Receipt`. Three inputs, stated as three. |
| §3.4 | `Receipt = { exit, result_hash, atp_spent }`; the three exits are canonical, deterministic and identical across nodes for the same **demanded** environment. |
| §3.4 | The two-value form survives as a named compatibility profile (MAY), losing no guarantee except the ability to answer `exit`. |
| §3.4 | An `atp` outside `uint32` is not a budget: refused per §3.6, and clamping to `2³²−1` is forbidden by name. *(Round 1 finding — this clause previously said "MAY reject/clamp" while §3.6 said MUST refuse.)* |
| §3.4 | Size is named a **semantic** measure of materialization, with what the bound is not: RSS, heap, evaluator stack, store index, hashing buffers, allocator. |
| §3.5 | `env` is a content-addressed map: `SHA-256(bytes) = key`, over the **raw buffer, before §4.1 validation**. Bytes under a key they do not hash to MUST NOT execute as that key's node. *(Round 2 finding: the property had been written `NodeHash(bytes) = key`, which is undefined for a buffer that is not a node.)* |
| §3.5 | The property is checked for every hash the evaluation **actually resolves**. An undemanded entry MUST NOT change any canonical `Receipt`; a verifier declining such an environment is exercising admission, which yields no `Receipt`. *(Round 2 finding: round 1's version said both that an undemanded entry cannot affect the result and that a wider check must refuse.)* |
| §3.5 | Determinism is over the demanded environment; extension of the environment can change **only** the `unresolved_reference` exit — mechanized as `EvalMachine.evalHash_stable`. |
| §3.6 | Admission is a required deployment boundary: a verifier MUST be able to refuse before executing, and that refusal MUST NOT be serialized as a DISSONANCE or presented as a result. Out-of-domain `atp` and a `term_hash` that is not 32 bytes are refused the same way. |
| §5.1 | The ASCII-byte convention stated outright instead of implied. |
| §7 | One arbitration rule, and the five record fields that carry a prose claim: `term`/`bytes`, `atp`, `expected.outcome`, `expected.result_hash`, `expected.atp_spent`. |
| §7 | A notation clause: `eval(·, atp)` abbreviates evaluation over the edition's own vector-suite environment; `= ⟨X⟩` asserts `normal_form` with that result hash. *(Round 1 finding.)* |
| §3.4 | Typo `преф лайт` → `префлайт`. |

`spec/book-1-truth.en.md` mirrors every one of these. It is informative, not
anchored, and the gate reads it precisely so that a divergence between the two
texts would be a finding.

### Books II and III — 0.6.1 → 0.7.0

Two changes, no algorithm touched:

1. "The reference oracle wins" is gone, replaced by the rule Book I §7 states.
2. Each says how that rule maps onto **its own** suite schema: for Book II the
   inputs `w1`, `w2` and `expected` entire; for Book III `kind`, `doc` and
   `expected` entire; `id` and `note` are explanatory in both. Book I's field
   list is explicitly not transported literally. *(Round 1 finding.)*

Book III additionally lost a false attribution: it credited the arbitration
discipline to "Book I §7", which in the previous edition said something else.

---

## 2. What happened to oracle precedence

It is gone from all three Books, and this is the change most likely to make a
conforming implementation non-conformant without anyone editing a line of it.

Before: Books II and III named `impl/sigma_wave.py` and
`impl/sigma_federation.py` as the arbiter where prose and vectors disagreed.
An engine that matched the oracle was conformant by construction, and the
specification could not be wrong — only unimplemented.

After: the prose and the vector suite MUST be mutually consistent; an edition in
which they disagree is non-conformant and MUST NOT be used as a source of
consensus until corrected and re-anchored; and **no implementation, the reference
one included, has precedence over the edition's normative artifacts**.

Two consequences, stated because they are costs and not only benefits:

- An engine that deferred to the oracle where the oracle and the suite diverged
  was conformant to 0.6.1 and is not conformant to 0.7.0. That is why the bump is
  MINOR rather than PATCH under `spec/VERSIONS.md`'s own test, and two reviewers
  pressed on exactly this; the answer is in ADR-010.
- The reference implementation is now falsifiable by the specification. Where it
  disagrees with the Book, it is the implementation that is wrong. Nothing in the
  repository enforces this beyond the conformance run itself.

---

## 3. The store/CAS model and local admission, exactly

**The environment.** `env` is a partial map from hash to bytes with one property:
`SHA-256(bytes) = key`, over the raw buffer, checked **before** §4.1 validation.
Two questions are kept apart on purpose:

- *Is this buffer a valid `SigmaNodeV2`?* — canonical answer. A buffer that fails
  §4.1 materializes the Canonical Invalid Object (§4.2), priced as one force.
- *Do these bytes belong under this key?* — **no canonical answer at all.** A
  mismatch is a local fault: the implementation refuses, and MUST NOT return a
  canonical result.

Conflating them was a real defect: until the audit of 2026-08-29 the reference
oracle executed foreign-key bytes as the requested node, which is an
Identity-by-Hash violation that lets two engines diverge while both believe they
are following the Book.

**Scope of the check.** For every hash the evaluation actually resolves. An entry
never demanded MUST NOT change any canonical `Receipt`. This is the demand-scoped
reading, and it is forced by determinism being stated over the *demanded*
environment.

**Extension.** `evalHash_stable`: if `env₂` answers every lookup `env₁` answers,
a settled exit — normal form or exhaustion — is the same `Receipt` under both.
Only `unresolved_reference` can change. The hypothesis is on lookups rather than
set inclusion because `storeGet` returns the first entry whose hash matches, and
ruling out a differing answer by assuming SHA-256 injective would assume
something false by counting. Differential evidence:
`proofs/store_mono_bridge_check.py`, **67 grown and 1153 shrunk over 33
evaluation vectors**.

**Admission.** `eval` is total, so a stranger's term always terminates; that is
not the same as being affordable. A `uint32` budget admits up to 4 294 967 295
priced actions, and because `size ≤ spent + 1` the budget the stranger picks is
also their licence over the verifier's memory. So a verifier MUST be able to
refuse **before** executing. A refusal:

- is **not** a canonical outcome and MUST NOT be serialized as a DISSONANCE;
- says the verifier declined, not what the term evaluates to;
- produces no `Receipt`, which is why a verifier that validates the whole
  environment on admission cannot diverge from one that does not — it has nothing
  to disagree with.

`impl/sigma_glyph.py` carries `admit()` and a `VERIFIER_LIMITS` preset whose
default leaves the cap unset, because this module is also the conformance oracle
and an oracle that refuses is not an oracle. Nothing forces a verifier to adopt
the preset. That is the assumption, not the mitigation.

---

## 4. The receipt, and the exit/result ambiguity

`Receipt = { exit, result_hash, atp_spent }`, `exit` exactly one of
`normal_form`, `atp_exhausted`, `unresolved_reference`.

**The result hash never carried the exit, and did not start failing to.**
`DISSONANCE(ATP Exhausted)` is an ordinary term: put it in a store and evaluate
it and it is a normal form. So `8bb0006f4c0a…` is reachable both as an exhaustion
and as a normal form, and a caller reading only the hash cannot tell "finished"
from "ran out". `tests/receipt_test.py` produces both and fails if either half
stops being true; it was verified to fail under two perturbations.

`evalHash_settles` proves every run ends on a settled configuration and therefore
exits through exactly one of `step`'s three non-firing results. It does **not**
prove the three result terms are pairwise distinct, and they are not. The
trichotomy is about the exit, not the term.

The two-value form remains available as a named compatibility profile and a
receipt still unpacks as a pair, so the four call sites in `warrant` that consume
`ski@v1` reasons are unchanged and were exercised against this oracle.

---

## 5. Semantic materialization vs physical memory

`size` counts materialized nodes: a tree node-count over the materialized graph,
thunks counting 1, nodes synthesized by reductions counted. The theorem
`EvalMachine.evalHash_peak_size` is `size ≤ atp + 1` at **every** configuration
the run passes through, and its per-step lemma is that every priced action grows
the term by strictly less than its cost.

What the bound says nothing about: resident set size, heap bytes, evaluator
stack depth, the store's index, hashing buffers, allocator behaviour. The
correspondence between the semantic measure and any physical one is a refinement
layer that is **not proven and not claimed**.

One practical consequence is stated normatively in Book I §3.4: `spent` is an
upper bound on size, not a lower one, so a fault-guard keyed on `spent` wrongly
kills divergent terms of tiny size. A guard MUST measure actual `size(t)` or
depth.

---

## 6. Every claim in paper v2: checked / unresolved / outside scope

`python3 tools/paper_claims.py` — **75 checked, 0 failing**, and
`--selftest` rewrites each of the 74 load-bearing numbers in turn and demands the
audit go red. The one check with no literal to rewrite is named rather than
silently excluded.

### Checked (75), by group

| Group | Claims | What is recounted |
| --- | --- | --- |
| Headline / abstract | 4 | guarded theorems, fronts, evaluator theorems, `native_decide` theorems |
| Contributions §1 | 4 | `native_decide` of the total, total, the complement, evaluator theorems |
| §4.4 trusted base | 8 | total, per-front distribution (`size` 2, `bytes` 12, `eval` 16, `wave` 6, `c1` 5), statement pins 44, deliberately unguarded 19 |
| §4.3 Lean artifact | 12 | file count, line total, and **every one of the ten files individually** |
| §6.1 / §6.3 machinery | 12 | definition pins 156, `proof_guard.py` 1465, registry 179 KB, `proof_guard_test.py` 981, six bridges, 929 bridge lines, ratio 2.4, both places each is stated |
| §6.2 conformance | 9 | 49 vectors, 33/8/8 by kind, 36 CAS objects, outcome distribution 17/12/3/1 |
| §6.3 implementations | 4 | `sigma_glyph.py` 618, `main.rs` 1112 (twice), `main.go` 1948 |
| §3.6 / §6.1 store monotonicity | 7 | 67 grown, 1153 shrunk, 33 vectors, in both places, plus the abstract's 1220 — taken by **running the bridge**, not by copying its output |
| §6.1 table | 6 | per-front theorem counts as the table prints them, and the total |
| Guard paper | 7 | `proof_guard.py`, registry KB, Lean total, statement and definition pins, suite lines, and the title's twenty-one against the body's enumeration |

### Unresolved / not checked (7 categories, each printed by the tool with the command that would produce it)

| Category | Why, and what produces it |
| --- | --- |
| The §6.1 wall-clock column | Host-, load- and toolchain-dependent. Time each bridge individually; the sequential figure by timing six in one loop. **`tools/test-all.sh` does not produce these — it times nothing.** |
| The §6.1 differential counts (861 steps, 334 buffers, 33 vectors, 582 cases, 3000 λ-terms) | Each bridge prints its own total; running them here would put `lean` on the checker's critical path. `test-all.sh` owns them. |
| 122 guard checks, 2103 property checks | Emitted at runtime: `python3 tests/proof_guard_test.py \| grep -c '^ok'`. |
| 5347 fuzz vectors and the three CI seeds | Generated, not stored, by `ci.yml`'s three `book1_fuzz.py` invocations. |
| Claims about external repositories — `warrant-go`, PyPI versions and upload times | Outside this tree. CI pins the first by commit hash; the second was checked against the PyPI JSON API by hand. |
| Why each bypass worked; adoption-warrant signatures | Mechanically uncheckable here. |
| That the arguments are correct | This checks arithmetic, not reasoning. |

### Outside scope, deliberately

- **Paper v2 is not deposited.** The committed `paper.pdf` is byte-identical to
  the deposited artifact (MD5 `f07e9c3a6301cf2be34771746d7e5c63`, confirmed
  against the Zenodo record for DOI 10.5281/zenodo.22069651) and is untouched.
  `build.sh` writes to that name, so it now carries a warning and `README.md`
  says not to overwrite it.
- Both papers' `author` metadata was a list of maps, which pandoc's default
  LaTeX template renders by its truthiness — every build, **including the
  deposited one**, printed the word "true" where the author's name belongs. Fixed
  in the source of both; the deposited PDF is left as the historical artifact.

---

## 7. Exact SHAs and digests

### Revisions

| | |
| --- | --- |
| branch head (this report) | `461fe7b6ffcf3f9235d546fac6642601b66f1c24` |
| candidate first written | `1c2b6ca42cb95cdc035fc887cd0587a5758862d7` |
| round 2 bytes | `1e91131c891dcc8f8b02ee27957330ab2251e2b6` |
| round 3 bytes | `fb7b650360b2a03d0bc60ccae50c1c208f68befd` |
| adopted release | `v0.6.7` at `16a1355` |
| `master` | `f07edad`, unchanged — no normative byte was merged |

### Anchors, adopted vs candidate (`NodeHash(LITERAL, atom=SHA-256(bytes))`)

| Path | v0.6.7 adopted | v0.7.0 candidate |
| --- | --- | --- |
| `spec/book-1-truth.md` | `a98a03bd…` | **`96d47223bed17078254d9155c70fa29d9c0c0eb8a27bcff17e739d4064949c67`** |
| `spec/book-2-navigation.md` | `7733dfb0…` | **`c88d78f7bd4dd514186fab5cbf2e448295f8e5cabe3049a29e2ea10574ff22bc`** |
| `spec/book-3-federation.md` | `e7bdbac8…` | **`f9f6b1f7652032110a867ef8e1e5050c84cd88f2a25832c36adb1230f687ccb0`** |
| `tests/spec_conformance/vectors.json` | `08116edb…` | **`a4b02b642a2b90e4716bcbcb63a959419df3a4c46bb391c932f369ed4225ef39`** |
| `tests/spec_conformance/wave_vectors.json` | `9ef44d02…` | **`904395f210097f537f6c852816e5052e28dedf37b9b52ebe0f07bc115045cb36`** |
| `tests/spec_conformance/federation_vectors.json` | `310296a8…` | **`392f74ef5320976cde1dcd5ade01e3d872d681ec1eddef9bd8edd36956e7b40f`** |
| `tests/spec_conformance/governance_vectors.json` | `14ead59a…` | `14ead59a…` unchanged |
| `spec/GOV-anchors.md` | `59bbb117…` | `59bbb117…` unchanged |
| `spec/LORE.md` | `9bd7977c…` | `9bd7977c…` unchanged |
| `spec/appendix-a-complexity.md` | `2df9194b…` | `2df9194b…` unchanged |

### Raw file digests of the frozen candidate (SHA-256)

    7948b2b58ddbf3fbd7b08a16487e23c1c521f838ad1bffd8f913f54215e2cb70  spec/book-1-truth.md
    2d55f4d8b0619ca061eacb72a691edd3df86e0e852b31bed2c7ab4a99525df53  spec/book-1-truth.en.md
    7ef8f91b45854828a46b6f503f41211bdbe455836a1870b22e7ee5298ce902d6  spec/book-2-navigation.md
    c0c5d48b27aa58eba9f02ddb22e1d7e6b115f871620f8e5bd327b574074a654a  spec/book-3-federation.md
    bda72b13dbe9edd1448b63b665c73af7b29be8110c643ec39d8953c6a7409196  tests/spec_conformance/vectors.json

### Papers

| | |
| --- | --- |
| `papers/one-integer-for-work-and-memory/paper.md` | `a00f7fccc78eb553d919c6c5296d4ee792216466b2e518253713fea26637ab44` |
| `papers/one-integer-for-work-and-memory/paper.pdf` | MD5 `f07e9c3a6301cf2be34771746d7e5c63` — **the deposited artifact, unmodified** |

The v2 PDF was built three times in clean `git archive` checkouts for visual
verification (22 pages, TOC, bibliography, code blocks, DOI note, no stale
correction text) and deliberately **not** committed.

### Anchor-set blobs

| Round | SHA-256 |
| --- | --- |
| round 1 | `0bac2605fd46f0b7fdadf7b06cce7738445d75f713632754fe2e718e4935726e` |
| round 2 | `79bf939a737e88d310a029150facb7ba77e9e9483e622e868deeca57f628e9b5` |
| round 3 (current) | `4c93717a7007ef8af179ae39ee62492a59594e23be8fdc4a4eef5e04a98f3ae9` |

### Release artifacts

**None.** No tag, no GitHub Release, no PyPI upload, no Zenodo deposit or
version, and no rebuild of the deposited PDF.

---

## 8. The three blind gates

One prompt per round, identical across reviewers; fresh context each; no reviewer
shown another's answer; every frozen digest re-hashed before sending. Raw
responses, model ids as the API answered them, prompt digests, reply budgets and
UTC timestamps are in `gates/v0.7.0-candidate/round-{1,2,3}/`.

| Round | Anchor set | Gemini 3.1 Pro | DeepSeek v4 Pro | Kimi k3 |
| --- | --- | --- | --- | --- |
| 1 | `0bac2605…` | REJECT | REJECT | REJECT |
| 2 | `79bf939a…` | ADOPT | REJECT | NO VERDICT (truncated at 24k) |
| 3 | `4c93717a…` | ADOPT | NO VERDICT (HTTP 402) | NO VERDICT (HTTP 402) |

**Round 1 — three REJECTs.** All three families independently found that the
candidate had added §3.6 requiring an out-of-domain budget to be refused while
leaving §3.4 saying it may be clamped. Two produced the same counterexample:
`H(I)`, `atp = 2³²`, empty environment. Also found: §7's two-argument call shape
under a rule the candidate itself adds; Books II/III importing a field list that
does not fit their schemas; and the GOV-anchors pin.

**Round 2 — the repair contradicted itself.** DeepSeek found that §3.5 now said
both that an undemanded entry cannot affect the result and that a permitted wider
check MUST refuse, with `H(I)`, `atp = 10`, canonical `I` bytes under the zero
key. It also found `NodeHash(bytes) = key` undefined for buffers failing §4.1.
Kimi was cut off mid-reasoning by a 24 000-token reply budget — a fact about the
budget, not the candidate; `--max-tokens` now exists and every review records it.

**Round 3 — did not complete.** Gemini ADOPT. DeepSeek and Kimi returned
`HTTP Error 402: Payment Required`; the OpenRouter account had $0.168 left after
three rounds of a 130 KB prompt across three models. DeepSeek was retried at
12 000 tokens and returned 402 again. **One verdict is not a gate**, and the two
families whose findings produced round 3's edits have not seen them.

**An independence limit, recorded rather than glossed.** From round 2 the prompt
carries ADR-010, and ADR-010 carries the previous round's dispositions —
necessarily including why a reviewer was disagreed with. Reviewers are blind to
each other *within* a round and not blind to earlier rounds' arguments. Round 2
made that concrete: Gemini reversed its round-1 GOV-anchors P0 citing Kimi's
round-1 reasoning by name, and did so again in round 3. That is a legitimate
change of mind and it is **not** independent confirmation. On that question the
honest count is one line of reasoning with two subscribers against one standing
P0 — not two-to-one.

The alternative, withholding the dispositions, would leave reviewers unable to
see what changed and why. The weakness is named so nobody reads the vote total as
more than it is.

**Green CI is not counted as a gate anywhere in this record.** The system prompt
tells every reviewer why: the CI, the guard it runs and the tests it runs all
live in the revision under review.

---

## 9. The unsigned adoption warrant

`gates/v0.7.0-candidate/round-3/adoption-warrant.unsigned.json`, **0 signatures**,
outside `.warrants/`.

| | |
| --- | --- |
| decision | `accept` |
| subject | `4c93717a7007ef8af179ae39ee62492a59594e23be8fdc4a4eef5e04a98f3ae9` |
| ancestor | `d985e8b811e29c4e11142acde79a7f330211310205b7b49d8fff5c8a9e1b61b5` |
| prior | `b4dc05e307b81e7415536a2e2442ff5db41d29ea5b392423735e1892236e095c` |
| under | `b86122047ed676ef…` (governance profile), `f4fe3a55d7c2a62c…` (threshold policy) |
| threshold | 2-of-3: `claude-fable-5@sigma-glyph`, `codex@sigma-glyph`, `s0fractal@sigma-glyph` |
| **WarrantID**, if filed by `s0fractal@sigma-glyph` at `ts = 1788000000` | **`e9dd72bccb56444b64fb4faf475bf56e6926c39c41607cea3e1bc6aa79cbc5da`** |

The ID is conditional on the filer and the timestamp because both are inside the
body and therefore inside the hash. There is no single WarrantID for this
adoption until a real signer fixes them, and a document stating one without
stating them would be stating a guess.

    python3 tools/prepare_adoption.py gates/v0.7.0-candidate/round-3 \
      --actor <roster actor> --ts <filing time>

prints the ID and then the exact commands: copy the envelope to
`.warrants/records/<id>.json` and the blob to `.warrants/blobs/<subject>`, then
`python3 tools/cosign.py <id> <actor-id> <keyfile>` once per signer, then
`python3 tools/warrant_verify.py` and
`python3 tools/anchor_governance.py status --trust-config <out-of-band> --enforce`
to confirm it **settles** rather than merely exists. The trust config MUST come
from outside the tree; a run that reads it from the repository proves nothing
about the repository.

`prepare_adoption.py` holds no keys, has no `--sign`, refuses an actor the
threshold policy does not name, and warns when a set's ancestor is not the
adopted one — that is a fork, not a successor.

---

## 10. Residual blockers

**1. I, Claude Opus 5, cannot myself create any legitimate roster signature.**
The roster is `s0fractal@sigma-glyph` (the human founder), `codex@sigma-glyph`
and `claude-fable-5@sigma-glyph`, at 2-of-3. The first two are other actors'
keys and I will not use them; I am not `claude-fable-5` and will not sign as it.
This was known in advance and is why the work stops before adoption.

**2. The candidate has no gate.** Round 3 returned one verdict because the
OpenRouter account ran out of credit. This is a prerequisite *additional to* the
signature threshold: adoption needs a completed three-family round over
`4c93717a…`, and two of the three families have not seen these bytes — including
the one whose findings produced them. Re-running needs credit on the account;
about $3–4 covers a full round at the current prompt size.

**3. The GOV-anchors dependency pin is unresolved, by choice.**
`spec/GOV-anchors.md` is defined against "Book I v0.5.2 / Book II v0.6.1 / Book
III v0.6.1 as anchored in this release", and this candidate makes that sentence
name versions the bundle no longer carries. Round 1: P0, P0, P3. Round 2 and 3:
Gemini reversed to "not a P0", DeepSeek held P0 in round 2 and was unreachable in
round 3. It is not resolved by the author because a document that governs which
bytes are the specification should not be amended by the author of the bytes it
is being asked to govern. Both readings and the two available remedies — leave it,
or prepare a GOV-anchors 2.0.0 with its own MAJOR version, its own §7 suite and
its own governed adoption — are in ADR-010. **This is the decision the candidate
most needs from the roster.**

**4. Not attempted, and available.** Non-normative tooling could be split into a
PR against `master` — but `tools/paper_claims.py` now checks paper v2's text, and
paper v2 is not merged, so the checker would fail on `master`'s older paper. The
split is possible but not clean, and it was left for the roster rather than done
by guess.

---

## What is true about the tree right now

- `master` is `f07edad` and carries **no** normative candidate byte.
- The candidate lives on a **draft** PR titled NOT ADOPTED; the `v0.7.0` section
  of `spec/ANCHORS.txt` is marked CANDIDATE; `anchor_governance.py status` does
  not list it.
- `tools/test-all.sh` is ALL GREEN. On the PR, the five GitHub Actions checks
  (`test` ×2, `lean` ×2, `cross-repo`) and GitGuardian pass, and the new
  claims-recount step was verified to parse into a real job rather than an empty
  one — the failure mode that once let five green checks sit on a workflow that
  created no jobs at all. SonarCloud raised 11 issues, all in the tooling written
  here: two cognitive-complexity refactors, one path built from a command-line
  value without validating it as a content address, and eight smells. All are
  fixed and SonarCloud passes at `b4421b5`, so every check on the pull request is
  green — which, per the system prompt every reviewer was given, is a fact about
  scripts that live in this revision and is not evidence for anything in §8.
- No tag, release, publication or deposit was made; no history was rewritten; no
  force-push was performed; no key was used.
