# Retirement: the Warrant 0.x gates (2026-10-19)

**Status:** APPLIED on branch `forget/warrant-0x-gates`. The before revision is `f3fd1dd6ad967d92002d6a4b1063468c66df305b` (master after #65).

**Authority:** the repository owner told the agent in the working session on 2026-10-19: "warrant_gate, anchor_governance і x1_* - можеш зносити" ("you may tear down warrant_gate, anchor_governance and x1_*"). The owner left the rest of the scope to the agent's discretion. This line records where the act was given. It is not a proof that the act was within anyone's power.

**Not reviewed independently.** This change touches a governance boundary. Under AGENTS.md rule 6, it needs the independent adversarial gate before merge. Merging needs the owner.

## Why

These tools verified this repository against **Warrant 0.x**:
- `warrant_gate` is a connector over `warrant verify --store-mode --json`.
- `anchor_governance` is the GOV-anchors adoption verifier, with the anchor-trust roster fetched from the Warrant repo.
- `x1_*` is the HEAD-vs-frozen-0.x compatibility matrix.

Warrant was rebuilt as Warrant 2 on 2026-10-18 and keeps 0.x only at the tag `history/warrant-0.x-2026-10-18`. These gates checked against a consumer that no longer exists as a current path. They kept stale state alive in CI and in the documents that readers, human and model, take as current.

## Subjects (removed from the default tree)

| Path | sha256 at `f3fd1dd` |
| --- | --- |
| `.github/workflows/x1-cross-repo.yml` | `e0d89b203f6c48d1d513fddfa24b9eaa0f907269cc7b2c21fda33154231224a8` |
| `experiments/receipt-atom/DEMO.md` | `ee3a8f44466000fcdb213e18e3b9e0eda142957c6e899632f487f8f09932b0dd` |
| `experiments/receipt-atom/inputs/governance_vectors.json` | `2ab354b4ede71cc4d9a28429649761073c973a3a7ee0725e9e1f20c3315c2a30` |
| `experiments/receipt-atom/receipt.json` | `9003b81551a2b6ab1a84bac210c30184ca0deb501e1e03e26f8917528586f701` |
| `experiments/receipt-atom/verify_receipt.py` | `3c6b0bed312738ad18777fd6fc0ade33ef2421d64d56a8c18e249d825516c2f2` |
| `tests/governance_differential.py` | `2f49c3d7695620d6f92e37c3ee518e4f9d92d31fc37feb38df451d0889f3bc2a` |
| `tests/warrant_gate_test.py` | `20278882f9cbdb88c0ff2f51900c4dd6f02bca76bc6edb96cbe7641adb2312f3` |
| `tools/anchor_governance.py` | `7f1df185fee25e871d9821ec1e2466a4cffae8ab5e014852c7ef687dea9cdf8f` |
| `tools/prepare_adoption.py` | `0c47881646eb6e8657f344428a7647f2699e7e6c9ce82c51620c4e2637305020` |
| `tools/warrant_gate.py` | `409c8ceb1204af3e720e97242e2948c7d0cca487b1628b542bc89abf31cdd5b3` |
| `tools/x1-warrant-commit` | `ee9cb43f68d037243c48ace6ef1f19dd2f4e4817f66d17c3494d8a2c9be1b019` |
| `tools/x1_cross_repo.sh` | `fbc6c6b3b308ba0c1827f155447832c4eab4e16064f7b285163d2a4fb8e077b0` |
| `tools/x1_negative_control.sh` | `2cc72fbc2e286d3ccdde3d5ee7dbd25b57685631429ea6a3e40a324caf32e2d9` |

These were also removed from inside files that stay:
- the Go twin of `anchor_governance`: `gov-replay` and its GOV-anchors code in `impl-go/main.go` (about 790 lines), plus the now-unused `warrantSigDomain` constant;
- the CI steps that ran the tools above.

Why the other subjects went with them:
- `prepare_adoption.py` and `experiments/receipt-atom/` could only run through `anchor_governance`.
- The differential compared the two GOV verifiers.

## What replaced each role

| Role | Now |
| --- | --- |
| Required check `cross-repo` | `.github/workflows/cross-repo.yml`. A Sigma wheel from this checkout is installed beside **Warrant 2** at a pinned commit, from a local wheelhouse. It runs the provider self-test plus Warrant 2's `compute` and `agent_compute` suites (compute C13/C15 check Sigma's own identity formulas). It fails when Sigma's environment identity drifts, which was checked by mutation. |
| Verifying this repo's `.warrants` (Warrant 0.x format) | The pinned Warrant 0.x CLI is called directly, at base and settlement grade, in `ci.yml` and `tools/test-all.sh`; the decision is its **exit status**. Lost from `warrant_gate`: the closed-schema parsing of `verify --store-mode --json` (report tag, field set, grade-downgrade, empty stderr, findings/counts agreement). Kept: a corrupted record or a missing store still exits non-zero (checked in review). |
| The two-jurisdictions demo's store check | It calls `$WARRANT verify --store-mode --json` itself and reads the report closed-world (`report_problem`): tag, field set, grade, types, findings/counts and exit agreement, empty stderr. It refuses a stub that prints only `{"ok": true, "errors": 0}`. It now runs only where `warrant.py` is available; before, it ran unconditionally and needed `$WARRANT` anyway. |
| `evidence_view` adoption section | Reports `retired` / UNCHECKED and gives no adoption credit. |
| `one_signing_path` Go mirror | It now asserts that **no** Warrant signing construction is left in any tracked `impl-go/*.go`, instead of passing on a dead constant. It now runs in `ci.yml`; before, it ran only in `tools/test-all.sh`. Checked by mutation: a new `impl-go/sig.go` containing `ed25519` fails it. |

## What is lost

- Re-verification that the anchored bundle was **adopted** under the GOV-anchors 2-of-3 roster. The anchored bytes are still recomputed by `verify_anchors.py`, but nobody re-checks whether they were adopted.
- The independent second implementation (Go) of GOV-anchors and the Python–Go differential over `governance_vectors.json`.
- The X1 HEAD-vs-0.x crossings and their negative controls. Sigma is no longer checked against Warrant 0.x or `warrant-go`'s cross-repo matrix. The `warrant-go ski@v1` conformance step in `ci.yml` stays.
- The `sigma-glyph.verdict-receipt@v1` experiment.

## Still cited on purpose

These still cite the removed paths, and are not edited:
- `spec/GOV-anchors.md` and `tests/spec_conformance/governance_vectors.json` are anchored bytes in `spec/ANCHORS.txt`. They stay as historical normative text and data, and the STANDARD now has no executable verifier in this repository.
- `reviews/README.md` is a pinned replacement operand of retirement record `review-corpus-2026-07`. Editing it would break that record.
- `gates/`, `proposals/`, `papers/` (deposited bytes), `.warrants/`, `CHANGELOG.md` and the dated progress log in `ARCHITECT.md` are history.

Because the anchored files cite the removed paths, a machine record under `sigma-glyph.retirement-record@v0.1` could not satisfy its zombie-reference postcondition. So this retirement is recorded here and not as a record under `history/retirement-records/`.

## Recovery

```bash
git show f3fd1dd6ad967d92002d6a4b1063468c66df305b:<path>
```

Re-adoption of any of these would need a new owner decision. Restoring the bytes grants none.

## Validation, before the PR

- **`tools/test-all.sh`:** ALL GREEN, run in a venv with this tree installed and with `$WARRANT` set to the pinned 0.x CLI. One step was run separately: `check_release_surface.py`, in `--wheel` mode as CI runs it, which gave ALL PASS. Its local no-wheel mode fails the same way on unchanged master. `warrant-go` was skipped locally (not built); CI builds it from the pin.
- **`impl-go`:** `go vet` and `go test` pass.
- **New `cross-repo` job:** simulated locally on Python 3.11 with a no-index wheelhouse. Results: provider 16/16, Warrant 2 compute 15/15, agent_compute 6/6. A mutation of Sigma's environment schema makes C15 fail.
- **Same-model adversarial pass** (a fresh-context subagent, not independent): no P0 or P1. It found four P2s, all fixed in the follow-up commit: the demo check was weaker than the old gate; the CI `.warrants` loss was not declared; the `one_signing_path` Go scan covered one file and did not run in CI; and `README.md`, `publish.yml` and `ci.yml` had stale prose. `cross-repo` now pins `cryptography`.
- **Not done:** an independent adversarial review.
