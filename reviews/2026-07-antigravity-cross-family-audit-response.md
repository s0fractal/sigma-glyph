# Adjudication — Antigravity cross-family audit (2026-07-30)

Raw review: [`2026-07-antigravity-cross-family-audit.md`](2026-07-antigravity-cross-family-audit.md)
(Antigravity, **agentic** — the only reviewer in this round that executed anything. It ran the
oaip test batteries and all five Σ-GLYPH Lean bridge checks itself, and read the Ed25519
arithmetic line by line.)

**Headline: zero code defects, and the single most valuable output of the round is its attack on
the work's priorities rather than on its code.** That is an uncomfortable thing to file next to
the successes, so it is filed next to the successes.

**This was not an independent gate.** Same operator, same task framing as the other four
reviews in this round; see [`README.md`](README.md) § *Cross-family round, 2026-07-30/31*.

## Shape of the artifact

Two artifact-level notes, recorded rather than tidied:

- The header claims three repositories (`oaip/`, `sigma-glyph/`, `warrant/`) but the body
  contains findings and methodology for **two**. `warrant/` is asserted complete in §4 with no
  section of its own. Read the warrant coverage as unevidenced.
- §4 restates §§1–3 — the harness's closing message concatenated onto the report. Left as
  written.

The review answers a `REVIEW-BRIEF.md` that lives in the operator's private working directory
and is not in this repository; the six strategy questions are quoted inside the review itself,
which is the only public trace of them.

## Dispositions — code

| Antigravity finding | Verification | Verdict |
|---|---|---|
| **oaip Ed25519 + gate: no defects.** Independent reading of decompression via `(P+3)/8`, the `sqrt(-1)` branch, twist rejection, canonical-zero handling, extended coordinates with `a = -1`, `S < L`, projective equality. Separately traced whether the gate can be satisfied without a real signature: `body.actor.id` → `.oaip/trust.json` → `signature_verifies` with a `wid` already checked against `sha256(canon(body))` — **no** | Matches the code as shipped. This is the same verifier two other reviewers in this round attacked and missed on (see the glm-4.7 and gemini-3.1-flash-lite dispositions) | **AGREED — no action** |
| **proof guard: no open soundness bypass.** Confirms specifically that inductive **constructor types** really are pinned (`collectDeps` → `"ctor " ++ dumpExpr v.type`), that the driver reads `.olean` past elaboration via `importModules`, and that the token-level command walk closes single-line hiding | Confirmed at `proof_guard.py:829` (`.ctorInfo v => "ctor " ++ lp ++ dumpExpr v.type`) and `:870` / `:894` (`visit v.type` for `ctorInfo`) | **AGREED — no action** |
| **Residual named: runner I/O decoupling.** `BytesRun.lean` / `EvalRun.lean` / `WaveRun.lean` run under `profile="runner"`, which relaxes `partial`; a hostile edit there could print hardcoded answers and pass the differential tests. Only control is the external oracle | Confirmed: `_RUNNER_ONLY` (`:366-370`) denies `partial` everywhere except registered runners, and `theorem_pins.json` registers exactly `BytesRun.lean`, `EvalRun.lean`, `WaveRun.lean`. This matches the already-documented residual — which is the point: an outside reader reached it independently, so it is a real gap and not a formality | **AGREED — already documented, unchanged** |

**Note the asymmetry that follows.** This is the reviewer that could reproduce, and it filed
nothing false. The three reviewers that could only read filed six claims that a command refutes.
Five data points; the correlation is recorded and not promoted to a law.

## Dispositions — the plan critique

The critique is not a spec matter and cannot be adjudicated by a `grep`. It is recorded here
because it changed decisions, and because §5 of a paper drafted from this round rests on it.

| Question | Antigravity's position | Disposition |
|---|---|---|
| Q1 Is "quality × legitimacy, legitimacy = 0" the right diagnosis? | **No — it is a convenient one.** It masks a product-market-fit question: OTel + in-toto + append-only logs already satisfy enterprise audit today. "Nobody knows about us" licenses polishing mechanics instead of asking whether anyone wants cryptographic key management for ephemeral agent runs | **Accepted as a live objection.** Not resolved, not dismissed |
| Q2 Paper and distribution before a usable policy frontend? | **Sequencing is wrong.** Policies are hand-encoded `ski@v1` SKI terms today; no working engineer will author those. A readable frontend is a prerequisite for evaluation, not feature creep | **ACCEPTED — sequencing reversed.** Policy frontend now precedes distribution; it had been the other way round |
| Q3 Six rounds of guard hardening | **Streetlight effect.** Defending against hostile Lean proofs matters when third parties submit proofs; with zero external contributors the maintainer was defending against hypothetical PRs from himself, while real friction (keyring placement, policy syntax) was deferred | **ACCEPTED as a correct diagnosis of a suboptimal decision.** Recorded rather than argued with |
| Q4 DEC-001 signature domain separation: now or defer? | **Now.** With zero production users the migration cost is strictly zero; breaking it after integrators arrive is incomparably more expensive | **ACCEPTED — adopted immediately** as a breaking flag-day change across all three implementations |
| Q5 The honesty architecture (`llms.txt`, published defect lists) | Asset for peer review, **liability if it reads as a disclaimer of fragility**. Reframe "what was NOT validated" as a rigorous *Security Assumptions & Non-Goals* specification | **ACCEPTED as reframing, explicitly NOT as softening.** Same content, stated as a threat-model boundary rather than a confession |
| Q6 Model-actor governance | **Disqualifying** for SOC2 / ISO 27001 / FedRAMP: non-repudiation requires a legally accountable entity or an HSM. Position models as constrained delegated actors under human-signed root warrants, never maintainer-of-record | **ACCEPTED — positioning changed, mechanisms untouched.** The model remains a delegated actor; it is not maintainer-of-record |

Four of six changed a decision. None of them is a code change, and none of them is adopted
through this repository's governance machinery — they are maintainer decisions recorded
honestly, not warrants.

## Outcome

**Zero code changes from the code half; four decision changes from the plan half.** No
independent gate ran; nothing adopted.
