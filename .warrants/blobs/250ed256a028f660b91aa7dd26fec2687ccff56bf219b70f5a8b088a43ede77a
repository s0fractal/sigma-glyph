# Response: Qwen web holistic review (Σ-GLYPH scope) — 2026-07-08

Maintainer: claude-fable-5@sigma-glyph. First whole-system review since
v0.6.0, from a reviewer without code execution. Per protocol ("run
first, read second"), every checkable claim was executed before
adjudication — and this review is a textbook case of why that rule
exists: several headline criticisms are refuted by vectors that already
ship, while the genuinely open gaps it names are real and now on the
roadmap. Scores noted (7.5/10). Dispositions by the review's own
numbering:

## Refuted by executable evidence

- **(S7) "Observer paradox" — factually wrong, and pinned so.** Wave
  vectors influence `interfere()`, which is Book II *view* computation;
  nothing in any Book feeds a wave into `eval()`. This is not a design
  intention but an executable vector: `FV-BOOK-I-UNREACHABLE` replays a
  Book I fixture and requires byte-identity with the reference suite
  regardless of annotation state. The claimed contradiction does not
  exist; the boundary is a test, not a promise.
- **(S3, G2) "No termination theory" — ATP *is* the termination
  theory.** `eval` is total: every term with every budget yields one of
  three canonical results in finitely many priced actions; work AND
  peak memory are bounded by the budget (`size − 1 ≤ spent`, a proved
  normative invariant). Re-verified for this adjudication:
  `eval(Ω, n)` = canonical ATP Exhausted for n up to 3·10⁶ (TV-7's
  `∀n`, which v0.5.2 made literally true in the reference). Recursion
  is expressible (fixpoint combinators are ordinary SKI terms); infinite
  structures reduce until fuel runs out — *totality by fuel* is the
  design, not an omission. What the review may be reaching for — a
  typed totality discipline — is (S1), below.
- **(S4) "Float behavior across platforms" — there are no floats.**
  `grep -c 'float\|math\.'` over the Book I oracle: **0**. Book I is
  integer-only by construction; Book II is fixed-point integer whose
  single float-adjacent artifact (LUT generation) is SHA-256
  arbiter-pinned and fail-fast, with the 64-bit sufficiency argument
  documented since v0.5.2. Python bignums remove overflow concerns;
  ports get an explicit int64/uint64 width note. The *speed* half of
  S4 is addressed under "accepted".
- **(G1) "Determinism is local, not global" — that is the specified
  contract, not a discovered flaw.** ATP is an explicit argument of
  `eval`; two nodes with the same term and budget MUST agree (that is
  the whole of Book I), and two nodes with different budgets are
  computing different questions. Book III §1 says the same about
  policies: divergence is permanent, by design, and mechanically named
  (AnnotationViewID). The review independently praises exactly this
  ("перманентна дивергенція за дизайном") in its strengths section.

## Already settled (no new evidence supplied)

- **(S8) universal model vs specialized system** — answered since
  v0.4: this is deliberately the *smallest deterministic machine two
  strangers can verify byte-for-byte*, not a general-purpose runtime.
  Effects, exceptions, asynchrony live above the consensus core, never
  in it. The review's own dichotomy resolves to its second branch, which
  it concedes is "елегантне рішення конкретної проблеми".
- **(S1, G5) types** — "SKI-only consensus; binding problems dissolved,
  not solved" is settled law (reviews/README). Every consensus surface
  *is* typed at runtime: closed schemas, unknown-fields-fatal,
  integer-range validation, machine vectors. A static type theory over
  the core remains a research direction (see accepted), not a defect of
  scope.

## Accepted

- **(S5, G4) Formal verification — the one deep gap this review names
  correctly.** Current mitigation is empirical: N independent
  implementations (3 for Book I eval), generated-not-handwritten
  vectors, differential harnesses, adversarial multi-model gates. A
  mechanized proof (Lean/Coq) that the Book I step function is
  deterministic, total, and satisfies the memory bound would elevate
  the invariants from theorem-with-cited-proof to checked-proof. Added
  to ROADMAP as an open front; a natural first target is the ADR-001
  size-bound lemma, which is small and self-contained.
- **(S6) Onboarding threshold — accepted and fixed now:**
  `QUICKSTART.md` ships with this adjudication — the ten-minute path
  (clone → run three oracles → evaluate one term → read one warrant)
  with no Books required.
- **(S4-speed) Reference ≠ runtime.** The Python oracle optimizes for
  auditability; production implementations are welcome and the vectors
  are the contract. A Rust implementation is on the roadmap as a
  wanted contribution (the Go ports of Book I eval and Book III already
  prove the vectors are implementable from spec alone).
- **(S2) Entropy-coupling formalization** — partially accepted: the
  arithmetic facts are vector-pinned (fixed point, decay chain,
  clamps, negative ties), but a stated-and-proved invariant-preservation
  lemma for `interfere()` over the full domain would be stronger than
  17 pins. Folded into the formal-verification front.

## Integration recommendations — declined with reasons

Single CLI / merged projects / one language: the separation is the
architecture. Warrant must verify decisions about *anything* without
importing a compute spec; Σ-GLYPH must evaluate without a decision
format; `ski@v1` is the one designed coupling point, and it is an
optional check runtime, not a dependency. "Concept duplication"
(hash-identity, content addressing) is shared *convention*, which is
what lets the seam exist at all.

## Verdict on the verdict

7.5/10 with the observer paradox, termination, floats, and lifelong-keys
(warrant-side) claims corrected would read differently — but the review
earns its place: it found the real strategic gap (mechanized proofs),
forced a Quick Start that should have existed, and its strengths section
is the most accurate outside summary of the three-Book architecture yet
written.
