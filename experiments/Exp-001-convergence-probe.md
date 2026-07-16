# EXP-001 — Convergence Probe: does the adversarial patch-loop have a fixed point?

**Task for:** Claude Code, operating over the real corpus of `sigma-glyph` (+ `trinity`, `warrant`).
**Type:** falsifiable measurement, not a build. **Primary success = refuting the stated hypothesis.**
**Author of the hypothesis under test:** Claude (in conversation). Treat it as a claim to be broken, not a spec to satisfy.

---

## 0. Why this exists (one paragraph, do not expand into theory)

`sigma-glyph`'s development *is* an instance of a recursive adversarial patch-loop: `reviews/`
are patches, the "Settled points" list in `reviews/README.md` is the accumulated layer-stack, each
settled point closes an attack surface and many carry their own falsifiers (executable test vectors:
TV-6, TV-9, TV-11, WV-*). Some settled points **supersede** earlier ones. `trinity` records already
tag every claim with a supersession mode (`strict_superset` / `backward_compatible` / `corrective`)
and carry `falsifiers:`. The loop already ran and left an audit trail. **We do not build a toy loop —
we measure the one that exists.**

The question: **does this loop converge to a fixed point, or accumulate layers without termination?**
(The negative example is `OMEGA_EXPORT`'s Translation-Policy spine; the positive example is `trinity`'s
key-rotation invariant that held across all versions.)

---

## 1. The hypothesis under test (break it)

> **H_converge (Claude's claim):** the loop converges. As spec-version advances v0.3.0 → v0.6.6,
> (a) invariants ADDED per review round declines, (b) the supersession/addition ratio rises,
> (c) the active layer-stack `L(t)` is concave and approaches an asymptote, (d) new P0/P1 findings
> per review round declines. Informally: *confirmation-pressure dominates innovation-pressure in the limit.*

> **H_accumulate (null):** additions stay roughly constant or grow, supersessions ≈ 0, `L(t)` grows
> ~linearly, new P0/P1 does not decline. The loop is unbounded accumulation dressed as progress.

**You are not here to confirm H_converge. You are here to return the numbers that decide between them.**
The most valuable outcome is a clean refutation of H_converge (e.g. `L(t)` linear, or no stable kernel).
If the data is ambiguous, say "ambiguous" and show why — do not round toward the pretty answer.

---

## 2. Corpus (real paths — read, do not invent)

- `sigma-glyph/reviews/` — every `2026-07-<model>-*.md` is a patch. Extract: version targeted, findings by
  severity (P0/P1/P2/P3), verdict.
- `sigma-glyph/reviews/README.md` "Settled points" — the layer-stack. Each bullet: version introduced,
  and any `Superseded`/`Supersedes-in-scope`/`~~strikethrough~~` marker = a removal event.
- `sigma-glyph/spec/ANCHORS.txt` + `spec/appendix-a-complexity.md` — version lineage and the compute-layer
  cost model (`size − 1 ≤ spent`).
- `sigma-glyph/.warrants/records/*.json` — adjudications (warrant schema: `because`, `prior`, `under`).
- `trinity/src/*.myc.md` frontmatter — `claim_kind`, `falsifiers:`, and the supersession-mode taxonomy
  (`strict_superset` / `backward_compatible` / `corrective`). Use these to classify each patch's *type*.
- `trinity/contracts/FREE_ENERGY_PRINCIPLE.v0.1.md` — the FEP-as-health-metric contract. It is
  `implementation_status: aspirational` and explicitly *awaits at least one empirical correlation study
  before promotion*. **This experiment is that study.**
- `trinity/src/x8300_physics.ts` + `physics_test.ts` — existing bounded `pressure ∈ [0,1]` scalar and
  `classify()` regime map. Reuse; do not reinvent.

> Note: clone `sigma-glyph` at full depth (`git clone` without `--depth 1`) so commit timestamps are
> available. If a metric cannot be extracted deterministically from the corpus, record it as
> `unmeasurable-from-corpus` — never estimate.

---

## 3. What to measure

For each spec-version transition `t` (v0.3.0, v0.4.x, v0.5.0, v0.5.1, v0.6.4, v0.6.6):

| symbol | definition | source |
|---|---|---|
| `a(t)` | invariants ADDED | settled-points list, by version stamp |
| `s(t)` | invariants SUPERSEDED/removed | strikethrough + "Superseded" markers |
| `L(t)` | active stack = `L(t−1) + a(t) − s(t)` | derived |
| `p(t)` | new P0/P1 findings raised | `reviews/` files at that version |
| `r(t)` | reviews filed | count of review files at that version |
| mode-mix | fraction `corrective` vs `strict_superset` vs `backward_compatible` | trinity frontmatter classification |

Then compute and plot (ASCII table is fine — no framework):
- `a(t)` and `p(t)/r(t)` trends → declining? (H_converge (a),(d))
- `s(t)/a(t)` trend → rising? (H_converge (b))
- `L(t)` shape → concave-to-asymptote vs linear vs accelerating (H_converge (c))
- mode-mix over time → does `corrective` share rise (collapse) or stay near zero (pure accumulation)?

---

## 4. The conserved-quantity probe (the physics-vs-poetry test)

This is the sharper half. In conversation the claim was: *"name a conserved quantity, or your
thermodynamics is a metaphor."* Test it at two layers.

**4a. Compute layer (known to hold — verify it):** re-run `tools/complexity_metrics.py` and confirm
`size − 1 ≤ spent` across all vectors. This is a real conserved bound: it *forbids states* (the
`O(2^ATP)` blow-up is impossible by construction). ✓ physics at the compute layer. Report the table.

**4b. Governance layer (open — this is the actual research):** enumerate the settled invariants that
were **never superseded** across v0.3→v0.6.6 (candidates: `hash is identity`, `wave ∉ hash`,
`aggregate is never a field`, `SKI-only consensus`). Call this kernel `K`.
- Is there a stable `K` (never touched) while the periphery churns? → "conserved core + dissipative
  shell". If yes, that is the governance analogue of the ATP bound — a **real finding**.
- Sharper, and the falsifiable bridge: **does every `corrective` supersession preserve `K`?** Write a
  deterministic check that scans supersession events and verifies none violates a `K`-invariant. If such
  a check passes over the whole history, `K` is *conserved under the loop's own dynamics* — i.e. it
  forbids states → physics, not poetry. If no stable `K` exists, or a corrective step breaks one →
  "conserved quantity" at governance layer is **refuted**. Report which.

---

## 5. Deliverables (and then STOP)

1. `experiments/exp-001/probe.py` (or `.ts`) — extracts §3 + §4 metrics deterministically from the
   corpus. Reproducible; "if the table and the tool disagree, the tool wins" (same rule as Book I).
2. `experiments/exp-001/FINDINGS.md` — the metric tables, plus a **one-line verdict per item**:
   H_converge (a)/(b)/(c)/(d) → supported / refuted / ambiguous; §4b kernel → exists / does-not-exist;
   corrective-preserves-K → holds / broken. Lead with whichever result refutes H_converge if any does.
3. One-sentence recommendation on `FREE_ENERGY_PRINCIPLE.v0.1.md`: does the data warrant promotion from
   `aspirational`, or does it refute the FEP-health mapping for this corpus?

**Termination condition (first-class, per the Jazz-daemon primitive):** produce the three deliverables,
then stop. Do **not** add a theoretical layer. Do **not** generalize beyond these repos. Do **not**
propose EXP-002. If you feel the pull to write "this opens up further questions…", that pull is the
unbounded-layer attractor this whole experiment exists to measure — resist it and end the run.

---

## 6. Scope guard

- Instrument existing corpus only. No edits to `spec/`, `impl/`, or `proofs/`.
- ≤ one new directory: `experiments/exp-001/`.
- Every number must be traceable to a file+line. No vibes, no estimates presented as measurements.
- If the corpus can't answer a sub-question deterministically, that *is* a finding: report the gap.