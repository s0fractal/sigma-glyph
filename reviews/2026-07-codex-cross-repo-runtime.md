<!-- TRANSCRIPTION, not the reviewer's own text. There is no raw artifact for this
     review: Codex delivered it as a message inside an interactive session and no file
     was captured. Everything below is reconstructed by a later agent from the commit
     bodies of the fixes it caused, which DO carry the reproductions. Treat every claim
     attributed to Codex here as a paraphrase whose wording is the maintainer's.
     NOT an independent gate: same operator, same task framing as the other four
     reviews in this round. -->

# Codex cross-repo audit — TRANSCRIPTION (2026-07-31)

> **Provenance warning, read first.** Unlike the other five reviews of this round, this one
> has **no artifact**. Codex ran it agentically inside an interactive session and produced its
> findings as messages; nobody saved the transcript. This file was written afterwards from the
> commit bodies of the fixes, plus the maintainer's contemporaneous Ukrainian-language response
> note. It is therefore:
>
> - **Not the reviewer's text.** No sentence below is quoted from Codex. Severity labels,
>   framing and emphasis are the maintainer's reconstruction.
> - **Biased toward what was acted on.** A finding Codex made that produced no commit would be
>   invisible to this method, and there is no way to tell whether any such finding existed.
> - **Sound on the reproductions.** The reproductions recorded below were re-run by the
>   maintainer before any fix, and are quoted from commit bodies written at the time.
>
> If the transcript is ever recovered, it should be filed verbatim beside this file and this
> file demoted to a disposition.

**Scope.** Cross-repository: `oaip` (runtime attribution), `warrant` (WPL compiler),
GitHub Actions workflows in all three, and `sigma-glyph` documentation status drift. Codex is
one of two reviewers in this round that **executed** — every finding below came with a
reproduction, and none of its claims was refuted.

**This was not an independent gate**, and Codex is recorded as having said so itself. See
[`README.md`](README.md) § *Cross-family round, 2026-07-30/31*.

## Findings and dispositions

| # | Finding (paraphrased) | Reproduced? | Disposition |
|---|---|---|---|
| **BLOCKER** | `sigma-glyph/master` and `warrant/master` are mutually incompatible: warrant master is on SPEC v0.4, sigma master is not, so the X1 HEAD↔HEAD cross-repo check is red. Sigma's local CI is green only through an old pin — correct for reproducibility, but it does not test the current ecosystem seam | Yes — Codex independently ran the migration branch and got `pass=13 fail=0 skip=0` | **CONFIRMED as a known, deliberate state, not a regression.** The migration was waiting on one co-signature. Its recommended order (fresh review at the exact SHA → signatures → re-run enforce and X1 → a separate merge decision) was followed. Closed: `v0.6.7 AUTHORIZED — adopted by b4dc05e307b8 (2/2 of 3)`; sigma master `7ab2753` TEST-ALL ALL GREEN; warrant master 33/33, and the X1 seam is green again |
| **P1** | `oaip` runs the validation check through `sh -c` on the host and labels the runtime `cmd@v1` — which Warrant SPEC §6 defines as execution in an **isolated container** — then passes that tag across the bridge unchanged. A signed record promises an execution profile that did not happen. Second half, worse: the check runs *after* the Execution's after-snapshot, so a check that writes into the workspace still yields a signed decision reading `effects=0`. Codex noted correctly that this is **not** shell injection — the check is the user's own; it is a provenance defect | Yes — both halves, before any change. On the unfixed tree, a check of `touch check-escaped-container` produced `execution … effects=0`, `ACCEPTED -> warrant 7b243952…`, with `sentinel_in_observed_workspace=yes` | **REAL — fixed.** oaip `d5ee3ba`, merged `d62f9b9`. `oaip-host-shell@v1` registered in §7.3 saying what actually happens; `cmd@v1` stays readable (§6 forbids invalidating older records) and is never written again. `oaip claim` now snapshots around the **check's own** window and refuses on effects, or files them under `--allow-check-effects` with a `check-effects` artifact in `evidence`. SA-12/SA-13 state plainly that this **observes and does not confine** — the mutation has already happened when it is seen — and a test asserts the sentinel is still on disk after the refusal so the suite cannot be misread as evidence of a sandbox. Found on the way: the shipped auth demo and the README quickstart both documented a check that writes `__pycache__` into the observed workspace — the defect's first real instance, in our own documentation |
| **P1** | `warrant`'s WPL compiler takes `--headroom` as an arbitrary integer and writes `atp + headroom` unchecked. `-1` emits a well-formed blob whose verdict the verifier answers `fail` — a wrong verdict with no error anywhere; `5000000000` emits an `atp` outside `uint32` that the verifier refuses as a malformed blob. A frontend whose whole contract is "refuse what you cannot compile" was refusing in someone else's verifier instead. Codex's sharpest requirement was the third: re-execute the **serialized** check with the **pinned** ATP before writing | Yes — both cases before any change | **REAL — fixed.** warrant `cf087ad`, merged `432f32e`. The fix is deliberately not a range check: `_validate_emission` serializes the doc, decodes it back, and reasons only from what came back — fields through `warrant.validate_ski_blob` (the verifier's own predicate, imported rather than restated), the pin against `SKI_REEXEC_MAX_ATP`, and the term re-reduced under the pinned atp and compared to `expect`. The validated bytes are the bytes stored. A hazard surfaced doing it: `import warrant` resolved to an older pip-installed copy, so the compiler would have been certifying against a verifier other than the one shipped beside it — sibling-file-first now. Sweep found the same shape in `impl/ski_policy.py`. Section L of `tests/policy_lang.py`, 17 assertions, 12 red against the pre-fix compiler including three mutants that tamper at the moment of serialization |
| **P2** | All three `publish.yml` workflows use mutable action refs (`pypa/gh-action-pypi-publish@release/v1`, and `checkout`/`setup-python`/artifact by major tag) in a job with `id-token: write`. For a stack whose subject is provenance, a mutable ref in the job that mints an OIDC token and publishes is the wrong default. warrant's `ci.yml` even acknowledged this in a comment and did nothing | n/a — inspection | **REAL — fixed in all three.** sigma-glyph `fd70898` (merged `0144564`), oaip `a18c820` (merged `6c81314`), warrant `89fb801` (merged `0d147aa`): full-SHA pins |
| **P2** | Documentation and version drift: ADR-007 still read `PROPOSED` / "No adoption warrants exist yet" while `spec/GOV-anchors.md` — the normative document adopted *from* it — reads `STANDARD` and the store holds threshold adoptions for v0.6.2 … v0.6.6. Separately, oaip HEAD requires Warrant ≥ 0.6.0 while `pyproject.toml` still said 0.2.1 | n/a — inspection | **REAL — partly fixed.** sigma-glyph `9f2a4ec` (merged `c0b4bab`): ADR-007 marked `SUPERSEDED`, **rev-3 text left unrewritten** — a decision record is history, and editing it to match today would destroy what it exists to preserve; the header now names which document governs and which sentence stopped being true. The maintainer records having hit this same drift from the other side the previous day, telling the operator a founder act was needed to close a gate that had already closed, because he read the status line and not the store. The oaip version bump was deferred and landed with the 0.3.0 release (`969afb2`) |

## Why this review is weighted differently from the others

Codex filed **no P0 that a single command refutes**, and every finding carried a reproduction.
Three of the four non-agentic reviewers in the same round did the opposite. This is the second
external run in twenty-four hours in which an outside reader found what six internal adversarial
rounds did not, and the mechanism was the same both times: the internal attacks assumed what the
code assumed. The first (glm-4.7) found a non-recursive file walk; this one found two defects in
**what a tag claims about what happened** — a question no internal round had asked, because
every internal round was checking whether the construction was correct rather than whether the
label was true.

## What this review was NOT

Codex stated this itself and the maintainer declined to upgrade it: **not an independent gate,
and not a governance adoption.** No roster threshold was met by it, no warrant records it, and
nothing in this file is adopted.
