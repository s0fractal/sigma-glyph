# Architecture roadmap — Σ-GLYPH

Living document for driving Σ-GLYPH to world-class engineering and academic
rigor. Companion to the three Books + GOV-anchors. Sibling repo: `warrant`
(warrant-go is the third independent Book I evaluator; its `ARCHITECT.md`
mirrors this).

## Definition of "world-class" (the bar we measure against)

1. **Every normative claim is backed by an executable vector or a machine
   proof** — not prose alone.
2. **Every consensus invariant is held by ≥3 independent implementations AND a
   differential fuzzer** (Python oracle, warrant-go, Rust). Pinned vectors
   catch known splits; the fuzzer catches the unknown ones.
3. **Every bug class we ever fixed by hand becomes an automatic gate** (uint
   overflow, small-order keys, trailing content, canonicality…).
4. **Proofs cover bytes and the compiler, not just the evaluator** — the
   assurance stack should reach serialization/hash canonicality and C1
   determinism, not stop at reduction.

## Operating rhythm

`harden (bounded pass) → independent external audit (the acceptance oracle) →
adjudicate findings as warrants in .warrants/ → repeat`. "Done" for a round =
an external audit returns 0×P0/P1.

## Backlog (ranked; status)

| id | item | done-criterion | status |
|----|------|----------------|--------|
| S2 | Cross-impl **differential fuzzer** over Python/Rust/warrant-go Book I: random terms + budgets → identical (result_hash, atp_spent) | CI gate, multi-seed, 0 divergences | **done** (`tests/book1_fuzz.py`, in CI) |
| S3 | Put **warrant-go** (independent Book I impl) into sigma's own CI as a conformance gate | CI job runs `warrant-go sigma-conformance` on every push | **done** (pinned by commit, in CI) |
| S1 | Extend Lean from eval → **serialization/hash canonicality + C1 compiler determinism** (the gap flagged in reviews/2026-07-fable5-v0.6.6.md) | Lean theorems: deser round-trip + C1 determinism, `lean`-checked | todo (multi-session) |
| S4 | ATP-boundary: per-impl unit test that cost arithmetic never wraps at `uint32` budgets + a Lean lemma (executable eval vector is infeasible: needs ~2³² ATP) | unit tests in each impl + lemma | todo |
| X1 | Combined CI: Book III verified against a live warrant store, so cross-repo coupling regressions surface | CI job across both repos | todo |

**Explicitly NOT doing** (anti-gold-plating): rewriting Book II/III for
elegance, new features, marketing, or spec prose without a vector behind it.

## Progress log

- **2026-07-17 (Fable 5, architect):** roadmap opened. The warrant-side
  hardening this cycle (a differential fuzzer, `reviews/2026-07-fable5-v0.6.6.md`
  fixes: warrant-go R-S uint32 overflow, small-order Ed25519 rejection,
  verifier trailing-content/panic/crash bugs) tightened the shared Book I +
  Ed25519 surface.
- **2026-07-17 (Fable 5, architect):** shipped **S2 + S3**.
  `tests/book1_fuzz.py` is a three-way Book I differential fuzzer: the Python
  oracle computes expected `(result_hash, atp_spent)` for random SKI terms +
  ATP budgets, and the two independent engines (Rust `book1`, warrant-go
  `ski@v1`) recompute them via the conformance harnesses — any split surfaces
  as a per-vector failure. ~1000 vectors/seed × 3 engines agree across seeds.
  CI now clones + builds **warrant-go pinned by commit** and runs both the
  pinned-suite conformance and the fuzzer (3 seeds), making warrant-go a
  first-class Book I gate — symmetric to warrant's CI pinning sigma. Next:
  **S1** (Lean → serialization/hash canonicality + C1 determinism).
