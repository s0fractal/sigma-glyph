# Disposition — Codex, the evaluator's implicit world parameter (2026-08-27)

Raw: [`2026-08-codex-store-parameter.md`](2026-08-codex-store-parameter.md).
Written 2026-09-07, after the v2 engine paper was deposited as
[10.5281/zenodo.22646920](https://doi.org/10.5281/zenodo.22646920). This
disposition is late: the review changed the specification (ADR-010, adopted
2026-08-30) and the paper (v2, built from `47cf57d`) before anyone wrote down,
per finding, what was accepted. That order — act, then account — is the wrong
one under the protocol, and this file exists so the account is at least complete.

Each finding: verdict, the reproduction or refutation, and where the resolution
now lives. "Lives in" means a checked artifact, not a sentence in this file.

## Dispositions

- **§1 `Store` is a hidden third input; two conforming nodes, same `term_hash`
  and budget, different canonical results (BLOCKER) — ACCEPTED, REPRODUCED.**
  The counterexample is the shape of six `Unresolved` vectors in
  `tests/spec_conformance/vectors.json` and of the GROW/SHRINK directions in
  `proofs/store_mono_bridge_check.py`: remove a demanded node from the store and
  a normal form becomes `Unresolved Reference` on the same term and budget.
  Resolved by **ADR-010** (adopted 2026-08-30, warrant `0e634c17…46e1`, 2-of-3):
  Book I now states `eval(term, budget, environment)` and the CAS condition; the
  bound on how far the third input reaches is `EvalMachine.evalHash_stable`
  (extending an environment can change only an unresolved outcome), tied to the
  live oracle by `store_mono_bridge_check.py` in CI. The paper's v2 abstract opens
  with this statement and §3.6 carries it; §3.9 quotes the v1 sentence it
  corrects. The README claim the review quoted ("same `term_hash` and budget →
  same `result_hash`") no longer appears in that form.
- **§2 `result_hash` does not encode how the run ended (MAJOR) — ACCEPTED.**
  `DISSONANCE(ATP Exhausted)` is an ordinary term, so one digest is reachable as
  an exhaustion and as a normal form. Resolved by the receipt in ADR-010 / Book I
  (exit, result hash, spent) — paper v2 §3.7. The result hash alone is documented
  as insufficient for "finished vs ran out"; consumers that read only the hash
  are reading less than the machine returns.
- **§3 title stronger than the theorem; `size` is a semantic node measure, not
  RSS/heap/stack (MAJOR) — ACCEPTED.** The v2 paper is retitled *One Integer for
  Semantic Work and Materialization…*; the abstract states "the bound is
  semantic, not physical" and names what is outside it (RSS, heap, stack, store
  index, hashing buffers, allocator); §7 says there is no verified refinement,
  no extraction, and no proof that the Lean `Store` models a content-addressed
  store. The reviewer's refinement ladder (ATP → semantic measure → runtime
  operations/heap/RSS, the second arrow unproven) is now the paper's own
  framing. `CITATION.cff` carries the same sentence. Not resolved: the
  refinement itself, which nobody has attempted.
- **§4 "safe to run a stranger's reason" — bounded is not affordable; admission
  is a verifier policy, not a canonical outcome (MAJOR) — ACCEPTED.** Paper v2
  §3.8 *Admission: totality is not affordability*; Book I (v0.7.0) states
  admission as the verifier's decision outside the canonical result;
  `SECURITY-ASSUMPTIONS.md` preamble ("the verifier must apply a local admission
  policy"). The Warrant-side consequence — an attacker must not set the
  verifier's spend — is the same rule at the consumer boundary; it is a Warrant
  obligation and is tracked there, not here.
- **§5 prose/vector conflict decided by the Python oracle; "three independent
  implementations" (MAJOR) — ACCEPTED, both parts.** The arbitration rule
  changed with ADR-010 ("one arbitration rule shared by all three Books",
  paper §3.9): a prose/vector disagreement is an inconsistent release, not a
  win for the oracle. ADR-008 (*specification is the arbiter*) was closed
  SUPERSEDED on 2026-09-07 (PR #53) because that rule now lives in the Books.
  The wording is fixed as the reviewer proposed, verbatim: paper v2 §6.3 says
  **three separately implemented engines from one development lineage** and
  tells the reader to read the older phrase as this one wherever it survives;
  §7 *One implementation lineage* says why agreement among them is weak
  evidence about specification error.
- **§6 V22 "Edit the Cop" — the guard lives in the artifact it guards
  (candidate, not reproduced by the reviewer) — ACCEPTED as a limitation, OPEN
  as a control.** Paper v2 §7 records V22 by that name. The control the
  reviewer asks for — a verifier pinned outside the candidate revision — does
  not exist in this repository; branch protection is not readable from the
  repository and is not claimed as a control. Carried forward to the guard
  paper (*Twenty-One Ways…*), which is not deposited and is where this belongs.
- **§7 on the papers — MIXED.** (a) "21 is a taxonomy count, not 21 independent
  vulnerabilities" — accepted for the guard paper; the engine paper v2 says
  "twenty-one reproduced bypasses over six internal hardening rounds", a
  taxonomy statement, and claims nothing about independence. Open in the guard
  paper. (b) "literature has almost nothing to say" — the engine paper v2 §2
  and §8 cite resource-aware type systems, separation logics with space
  credits, the de Bruijn criterion, independent re-checkers and proof
  engineering at scale; the phrase does not appear in v2. Open for the guard
  paper if it appears there. (c) EXP-004 "preregistered" — not a claim of this
  paper (zero occurrences in v2); it is the EXP-004 deposit's claim
  (`experiments/exp-004/`) and its README already records the post-result
  apparatus repair. (d) Strong confluence: not attacked successfully by the
  reviewer, nothing to change. (e) "Correction: the evaluator had an implicit
  world parameter" — done, and kept visible: paper v2 abstract, §3.9 (v1 text
  quoted), and the correction record before §8.

## What this review changed, in one line

The specification's interface (three inputs, receipt, admission, arbitration),
the paper's title and abstract, and the sentence used for the implementation
count. The blocker was real, reproduced by two families (Kimi's counterexample in
the ADR-010 gate is the same one), and is the reason v2 exists.

## Not done

- No refinement proof from the semantic measure to any physical resource.
- V22's external control.
- The guard paper has not been revised against §6–§7 and is not deposited.
