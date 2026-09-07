# Disposition — Qwen, critique of the deposited paper (2026-08-27)

Raw: [`2026-08-qwen-paper-critique.md`](2026-08-qwen-paper-critique.md).
Written 2026-09-07, after the v2 deposit
([10.5281/zenodo.22646920](https://doi.org/10.5281/zenodo.22646920)). The
review is an essay about the v1 paper, not a spec review; it is dispositioned
here because the registration file promised that its factual claims would be
checked against the tree, and because three of its points changed the v2 text.

## Factual claims, checked

- **"`native_decide` … is a gap."** Partly accurate as a description, wrong as a
  count. `native_decide` is used, and the paper says so: ten of the 41 guarded
  theorems are permitted it, which puts the Lean compiler in their trusted base
  (paper v2 §1 item 4, §4.4); the sixteen evaluator theorems, including the
  bound, have axiom cone `{propext, Classical.choice, Quot.sound}` and do not
  use it. The review presents the gap as unstated; v1 already stated it per
  theorem and v2 keeps that table.
- **"Bridges check compiled Lean against the Python oracle *and production
  binaries (Rust, Go)*."** Inaccurate. Every `proofs/*_bridge_check.py`
  compares the executed Lean model with `impl/sigma_glyph.py` only. Rust and
  `warrant-go` are compared with the oracle on the conformance vectors (paper
  §6.2), not through the bridges. The review's own conclusion — a proof about
  Lean source is not a proof about compiled code — stands and is stated in the
  paper (§7: "no verified refinement, no extraction").
- **Version label `0.6.7-paper1`.** Correct.

## Critiques

- **1. Proof vs practice gap — ACCEPTED as stated; not closed.** Paper v2
  abstract: "the bound is semantic, not physical"; §7 names the missing
  refinement and extraction. The review asks for a verified compiler or
  extraction proof; nobody has attempted one and the paper does not claim one.
- **2. ATP as the only metric oversimplifies (work ≠ memory, cache, I/O,
  amortisation) — BY DESIGN, with the scope now written down.** The bound is
  over semantic reduction cost and peak materialized nodes of a pure combinator
  machine; there is no I/O, no cache and no concurrency inside reduction, by
  Book I's contract (no clock, no network). Whether one integer generalises to
  effectful systems is not a claim of the paper. The v2 title carries the
  narrower scope.
- **3. "21 bypasses" is not exhaustive; who checks the checker — ACCEPTED for
  the guard paper; also raised by Codex as V22 (see the Codex disposition).**
  Open there.
- **4. No performance benchmarks — ACKNOWLEDGED, OUT OF SCOPE.** The paper
  claims determinism, totality and a bound, not speed, and says nothing about
  practical throughput. A benchmark would be a different paper; none is
  planned. Recorded so the absence is deliberate rather than overlooked.
- **5. AI authorship: reproducibility, auditability, responsibility —
  ACKNOWLEDGED.** The disclosure stays in the paper and in `papers/README.md`
  ("written by a language model working as maintainer"). Responsibility is the
  named author's; the review's question has no repository-side fix.
- **6. SKI-only scope — BY DESIGN.** Settled point in `reviews/README.md`
  ("SKI-only consensus; LAMBDA removed"). Generalisation to Wasm, contracts or
  mutable state is not proposed.

## Methodological notes

- **Preprint, not peer-reviewed — TRUE, and stated everywhere the DOI is
  cited** ("deposited, not peer reviewed"). v2 is the same kind of object.
- **Single author, "three independent implementations" — ACCEPTED; the phrase
  is gone.** v2 §6.3: "three separately implemented engines from one
  development lineage", with §7 *One implementation lineage* explaining why
  their agreement is weak evidence about specification error. The same point
  reached the paper independently through Codex §5.
- **Repository-centric publication assumes the repository persists — the
  deposit exists for this reason.** Each version carries a `git archive` of
  the exact commit under the DOI; a reader needs Zenodo, not GitHub.

## Recommendations

Verified compilation: not attempted. Benchmarks: out of scope. Generalisation
roadmap: none; scope is deliberate. Third-party audit: wanted, and the paper's
§7 names an implementation by someone who has not read this code as the single
most valuable missing datum. Peer review: not submitted anywhere.

## Net effect on v2

Three changes trace to this review: the "one lineage" wording, the explicit
scope statement in the title and abstract, and keeping the `native_decide`
per-theorem account rather than summarising it. Everything else is recorded as
by-design or out of scope, which is a disposition, not a dismissal.
