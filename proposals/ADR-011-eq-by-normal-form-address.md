# ADR-011: Equality by Normal-Form Address (candidate)

**Status:** DRAFT — external candidate, not yet through the gate. Written by
Claude (Fable 5) during the manifesto RVB/SSD sessions, 2026-08-30, at
s0fractal's direction; source material and measurements:
`manifesto/drafts/ADDRESSING-IS-EQUALITY.md` (AIE-0.1).
**Origin:** engineering incident in the SSD settlement gate
(`manifesto/tools/settle_gate.py`): settling `7+5=12` via in-language Church
equality exhausted a 50M ATP budget; the same fact settled for 601 ATP via
normal-form hash comparison.

## Problem

Equality expressed *inside* the object language pays a combinatorial tax on
computed arguments. `EQN = ISZERO ∘ SUB`, `SUB = iterated PRED`: under lazy
tree-semantics reduction the unevaluated argument (`PLUS 7 5`) is duplicated
by every `PRED` application. Measured on the reference oracle
(`eval_hash`, GATE limits, 2026-08-30):

| fact | in-language EQN (ATP) | NF-address compare (ATP) |
| --- | --- | --- |
| 3+2=5 | 260 780 | ~250 |
| 5+5=10 | 26 212 480 | ~500 |
| 7+5=12 | >59 452 030 (ATP Exhausted) | 601 |
| 100+100=200 | — | 9 997 |
| 200+200=400 | — | 19 997 |

The NF-address route is linear in result size (~50 ATP/unit under ADR-001
size pricing); the in-language route is unusable past single digits. Any
agent that needs equality of computed data either pays a five-orders tax or
reinvents the idiom below ad hoc, unblessed and unspecified.

## Candidate idiom (no spec fork required)

Bless, in Book I commentary or a conformance note, the **verifier idiom**:

```text
settle_eq(a, b, atp):
  (na, sa) = eval_hash(hash(a · F · X), atp,      store)   # F, X fresh inert literals
  (nb, sb) = eval_hash(hash(b · F · X), atp - sa, store)
  verdict  = (na == nb)          # comparison of canonical result hashes
  spend    = sa + sb
```

Content addressing already makes this sound: two conforming machines that
disagree on `na` have violated determinism, not equality. No kernel change,
no new rule, no vector renumbering. The idiom is expressible today; what is
missing is its *specification* — scope, exit semantics, and the soundness /
completeness asymmetry — so that receipts built on it mean one thing.

## Scope (the part that must be normative if adopted)

1. **Soundness is unconditional:** `na == nb ⇒ equal` (modulo SHA-256, which
   is already in the trust base).
2. **Completeness only for canonical data:** `na != nb ⇒ unequal` holds only
   when the NF is canonical for the equivalence class in question.
   First-order data applied at a generic point (Church numerals as `F^k(X)`)
   is canonical; arbitrary higher-order terms are NOT (η/extensionality).
   An adopted note must say this in normative text, or receipts will
   silently overclaim.
3. **Termination:** the idiom is defined only when both sides reach NF within
   budget; `ATP Exhausted` on either side is the canonical outcome, not a
   verdict of inequality. Interacts with the known receipt gap (result hash
   alone does not identify exit kind): a settle_eq receipt needs the exit
   kinds of BOTH evals, which strengthens the case already open in the next
   Book I candidate.

## Optional stronger candidate (spec fork, v-next)

A kernel primitive `EQ(h₁, h₂)` priced `spent₁ + spent₂ + 1` returning a
canonical boolean node. Trade-offs:

- (+) receipts carry one node instead of a two-eval protocol; exit-kind
  ambiguity solved structurally.
- (−) new rule, new vectors, Specification Anchor fork — heavy machinery for
  something the idiom already provides at the API layer.

Recommendation: **idiom-first**. Adopt the specification note; revisit the
primitive only if receipt-gap work (three-inputs-and-a-receipt, ADR-010)
lands a receipt format where the two-eval protocol is awkward.

## Prior art

Hash-consing (Ershov 1958; ATerm maximal sharing) — O(1) equality of built
terms; Merkle trees / git / Nix — identity of data by root hash;
normalization-by-evaluation — deciding conversion by evaluation at a generic
point. The candidate contribution is only the composition: equality as a
*priced settlement with a receipt* in a budgeted content-addressed machine,
plus the measured 10^5 asymmetry as the design argument.

## Addendum (2026-08-30, same day): the idiom already runs inside Warrant

Executed proof that no machinery is missing: a raw ski@v1 check with a
**non-boolean expect** — `term = (PLUS 74 1) F X`,
`expect = NodeHash(F^75(X))`, `atp = 2108` — was filed into a live evidence
pack (`manifesto/drafts/ssd-pack`, check
`0597575d21d62c…`) and `warrant … check` re-executes it to `pass` on the
bundled Book I oracle; the pack's settlement-grade verify stays at 0 errors /
0 warnings. `validate_ski_blob` requires only hex64 for `expect`, and
`run_ski_check` compares plain result hashes — the format and the verifier
both already permit equality-by-address. What remains missing is only the
*specification note* this ADR asks for (scope §1–§3), so that such checks
mean one thing to every reader. Comparison point in the same pack: the WPL
bit-fold route settles a three-clause integer predicate for 501 ATP — the two
approaches are complementary (WPL for predicates over small facts,
NF-addressing for equality of computed data), and both are honest answers to
the same enemy: in-language Church arithmetic.

## Falsifiers

- A prior statement of the settlement composition exists → this ADR reduces
  to a citation.
- A class of first-order canonical data where NF-address comparison yields a
  false inequality → scope §2 is wrong, not just narrow.
- A C1-grade compiler brings in-language equality within ~10x of the idiom →
  the design argument collapses to mere convenience.
