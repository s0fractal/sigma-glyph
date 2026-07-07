/-
Σ-GLYPH — mechanized proof of the semantic memory bound (Book I §3.4, ADR-001×003)

  THEOREM (memory bound):  along any evaluation,  materialized_size − 1 ≤ spent.

SCOPE — what this file proves and what it does not.

This file mechanizes the ACCOUNTING LEMMA: the per-action (size-growth, cost)
algebra of Book I §3.4 entails the invariant by induction over evaluation
traces. It abstracts the machine state to the pair (size, spent) and each
priced action to its exact effect on that pair, as fixed by the spec:

  action                     size'            spent'        Book I §3.4
  ─────────────────────────  ───────────────  ────────────  ──────────────────
  force LITERAL/DISSONANCE   s                p + 1         cost 1, thunk(1)→node(1)
  force REF                  s + 1            p + 2         cost 2, thunk(1)→node+thunk(2)
  force APPLY                s + 2            p + 3         cost 3, thunk(1)→node+2·thunks(3)
  R-R  (REF → target thunk)  s − 1            p + 1         cost 1, node(2)→thunk(1)
  R-I  (APPLY(I,x) → x)      s' with s'+2 ≤ s p + 1         cost 1, drops APPLY + ⟨I⟩
  R-K  (K x y → x)           s' with s'+4 ≤ s p + 1         cost 1, drops 2×APPLY + ⟨K⟩ + y(≥1)
  R-S  (S x y z → xz(yz))    s + z − 1        p + 1 + z     cost 1+size(z); net = dup of z
                                                            minus the dropped ⟨S⟩ spine node

The correspondence of THESE seven rows to the byte-level machine is not proved
here; it is enforced empirically by the reference oracle and its generated
vectors (tests/spec_conformance/: property P7 checks the invariant on ~2000
random traces; TV-6/TV-7 and the EV-* suite pin the per-rule costs). The two
layers together give: checked algebra (this file) + pinned implementation
(the vectors). Hand-written antecedents: Gemini gate proof and DeepSeek
re-derivation, 2026-07 (cited in Book I §3.4).

Verified with Lean 4 core only (no mathlib):  lean proofs/SizeBound.lean
-/

namespace SigmaGlyph

/-- Machine state, abstracted to the accounting pair. -/
structure Acc where
  size  : Nat
  spent : Nat

/-- One priced action of the Book I §3.4 machine, by its exact accounting
    effect. Rules that shrink carry their shrink as a hypothesis (R-I drops
    an APPLY node and the ⟨I⟩ leaf: at least 2; R-K additionally drops the
    discarded argument, whose size is at least 1, and the ⟨K⟩ leaf: at
    least 4). R-S is parametrized by the size `z ≥ 1` of the duplicated
    argument in its current materialization (hash-leaf model: thunks
    count 1 and are not forced). -/
inductive Step : Acc → Acc → Prop where
  | forceAtom  {s p : Nat} :
      Step ⟨s, p⟩ ⟨s, p + 1⟩
  | forceRef   {s p : Nat} :
      Step ⟨s, p⟩ ⟨s + 1, p + 2⟩
  | forceApply {s p : Nat} :
      Step ⟨s, p⟩ ⟨s + 2, p + 3⟩
  | rr {s p : Nat} (h : 2 ≤ s) :
      Step ⟨s, p⟩ ⟨s - 1, p + 1⟩
  | ri {s p s' : Nat} (h : s' + 2 ≤ s) :
      Step ⟨s, p⟩ ⟨s', p + 1⟩
  | rk {s p s' : Nat} (h : s' + 4 ≤ s) :
      Step ⟨s, p⟩ ⟨s', p + 1⟩
  | rs {s p z : Nat} (h : 1 ≤ z) :
      Step ⟨s, p⟩ ⟨s + z - 1, p + 1 + z⟩

/-- The §3.4 invariant: materialized size never exceeds spent + 1. -/
def Inv (a : Acc) : Prop := a.size ≤ a.spent + 1

/-- Per-rule lemma ("кожна дія коштує строго більше, ніж додає розміру"):
    every action preserves the invariant. -/
theorem step_preserves {a b : Acc} (st : Step a b) (inv : Inv a) : Inv b := by
  cases st <;> simp_all [Inv] <;> omega

/-- Evaluation traces: eval starts from a single root thunk
    (size 1, spent 0) and takes priced actions. -/
inductive Reach : Acc → Prop where
  | init : Reach ⟨1, 0⟩
  | step {a b : Acc} : Reach a → Step a b → Reach b

/-- THE MEMORY BOUND (Book I §3.4, normative invariant):
    every reachable accounting state satisfies size − 1 ≤ spent —
    equivalently, size ≤ spent + 1, with Nat subtraction avoided. -/
theorem memory_bound {a : Acc} (r : Reach a) : a.size ≤ a.spent + 1 := by
  induction r with
  | init => simp
  | step _ st ih => exact step_preserves st ih

/-- Corollary, stated as the spec writes it: a preflight memory estimate —
    peak size never exceeds 1 + the full budget, whatever the term does.
    (This is the bound v0.5.2 clarified MUST NOT be used as a live fault
    trigger on `spent`; see Book I §3.4 and the Opus M1 adjudication.) -/
theorem preflight_bound {a : Acc} (r : Reach a) (budget : Nat)
    (hb : a.spent ≤ budget) : a.size ≤ budget + 1 :=
  Nat.le_trans (memory_bound r) (Nat.succ_le_succ hb)

end SigmaGlyph
