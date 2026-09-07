# Disposition — Qwen, critique of the deposited paper (2026-08-27)

Raw: [`2026-08-qwen-paper-critique.md`](2026-08-qwen-paper-critique.md).
Written 2026-09-07, after the v2 deposit
([10.5281/zenodo.22646920](https://doi.org/10.5281/zenodo.22646920)). The
review is an essay about the v1 paper, not a spec review; it is dispositioned
here because the registration file promised that its factual claims would be
checked against the tree, and because three of its points changed the v2 text.

## Factual claims, checked

- **"The paper says `native_decide` is limited to 10 theorems, but does not
  detail how the verified-compilation gap is closed."** Both halves accurate.
  Ten of the 41 guarded theorems are permitted `native_decide` (paper v2 §1
  item 4, §4.4), and the paper closes no compilation gap: it states one (§7,
  "no verified refinement, no extraction"). The review's reading of the count
  and of the disclosure is correct; its concern is accepted below as critique 1.
  *An earlier draft of this disposition wrongly attributed a counting error to
  the reviewer; Codex's review of PR #54 caught it.*
- **"Bridges check compiled Lean against the Python oracle *and production
  binaries (Rust, Go)*."** Inaccurate on the binaries, and the paper's own
  account of the bridges is narrower than "compiled Lean" too. Per paper v2 §1:
  three bridges execute the compiled Lean model against `impl/sigma_glyph.py`
  (evaluation, bytes, wave); three check a weaker correspondence without
  executing Lean on the corpus — `bridge_check.py` drives the oracle against the
  step premise the proof consumes, `c1_bridge_check.py` compares the oracle's C1
  with a Python *transcription* of the Lean compiler model, and
  `store_mono_bridge_check.py` perturbs the oracle's store against the
  monotonicity bound. Rust and `warrant-go` enter none of them; they are compared
  with the oracle on the conformance vectors (§6.2). The review's conclusion — a
  proof about Lean source is not a proof about compiled code — stands, and the
  three weaker bridges are exactly where it bites hardest.
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
scope statement in the title and abstract, and the §1 sentence that separates
the three executed-Lean bridges from the three weaker checks. Everything else is recorded as
by-design or out of scope, which is a disposition, not a dismissal.
