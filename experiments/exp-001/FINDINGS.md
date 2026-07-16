# EXP-001 — FINDINGS

Instrument: `experiments/exp-001/probe.py` (deterministic; if this file and the tool
disagree, the tool wins). Corpus: `sigma-glyph` at HEAD, `~/trinity`. Run 2026-07.

## Headline (lead with the refutation, per the task)

**H_converge is NOT confirmed — and, more precisely, it is UNDECIDABLE from this
corpus as instrumented.** The premise that "the loop already ran and left an audit
trail" is only half true: it left a **prose** trail, not a **quantifiable** one. The
convergence curve cannot be drawn because the layer-stack is not version-binnable.
Two narrower, real conserved quantities do survive measurement.

## §3 — convergence trend (the pretty story): mostly UNMEASURABLE

| claim | measured basis | verdict |
|---|---|---|
| (a) invariants added per round declines | 4 / 21 settled points carry a clean `vX.Y.Z` stamp (README:14–34) | **UNMEASURABLE** — 17/21 unstamped ⇒ no per-version `a(t)` |
| (b) supersession/addition ratio rises | **2** supersession events in the entire history (README L29, L33) | **UNMEASURABLE** — a trend cannot be read off 2 points |
| (c) `L(t)` concave → asymptote | derived from `a(t)` | **UNMEASURABLE** — depends on (a) |
| (d) new P0/P1 per round declines | `P0`×96 `P1`×217 are *mentions*, and "P0" also means "No P0 found" / "closes the P0" | **UNMEASURABLE deterministically** — raised/absent/closed conflated; needs a semantic read of all 66 files; the corpus forbids estimates |

`r(t)` = 66 review `.md` (+11 blind pass-1 artifacts); 48 name a version, but *targets*
vs *mentions* are not regex-separable. **mode-mix** (trinity `strict_superset /
backward_compatible / corrective`): **UNMEASURABLE** — the frontmatter carries
`claim_kind`/`mode`, not that taxonomy (only 3 files even contain those words), and
trinity records do not map 1:1 onto sigma review-patches.

> This is the primary result: the loop did not leave machine-readable convergence
> evidence. H_converge is neither confirmed nor cleanly refuted — it is **not
> measurable** here. Do not round it toward "converges."

## §4a — compute-layer conserved bound: **HOLDS** ✓

`size − 1 ≤ spent` holds on **8/8** vectors (`tools/complexity_metrics.py`, TV-4…TV-11).
This is a real conserved quantity: it *forbids states* — the `O(2^ATP)` blow-up is
impossible by construction. Physics, not metaphor, at the compute layer.

## §4b — governance conserved kernel: **EXISTS** (with a caveat)

Stable kernel `K` = points present in the settled-set and never in a supersession:
`{hash is identity, wave ∉ hash, SKI-only consensus}` (the doc's 4th candidate,
"aggregate is never a field", is not literally in this list). Both supersession
events (L29 eager→lazy materialization; L33 blob-validation timing) live in the
**eval/validation shell**, not the kernel.

- kernel `K` **EXISTS**: a conserved core with a dissipative shell around it.
- **corrective-preserves-K: HOLDS** — no supersession event touches a `K` keyword.
- **Caveat (honest):** this is a keyword-intersection heuristic over 2 events, not a
  semantic proof. It is the strongest claim the corpus deterministically supports;
  it is not the same strength as §4a's forbidden-state bound.

## §5.3 — FEP promotion: **DO NOT PROMOTE**

`FREE_ENERGY_PRINCIPLE.v0.1` is `aspirational`, awaiting one empirical correlation
between a computed `F_total` and substrate health (its own falsifier #1). This study
computes **no** `F_total` and cannot draw the convergence trend the mapping needs
(§3 unmeasurable). It yields only a **static** observation (a conserved kernel),
weaker than FEP's **dynamic** "free energy declines" claim. The corpus is
**insufficient to decide** the FEP-health mapping — so it warrants neither promotion
nor refutation of the contract.

## One-line verdicts

- H_converge (a) → **unmeasurable** · (b) → **unmeasurable** · (c) → **unmeasurable** · (d) → **unmeasurable**
- §4a compute bound → **holds** · §4b kernel → **exists** · corrective-preserves-K → **holds (heuristic)**
- FEP → **do not promote** (corpus insufficient)

*End of run. No EXP-002; no added theory (termination condition observed).*
