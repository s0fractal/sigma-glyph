/- sigma-resume, mechanized: the run a segment makes (Lean 4 core).

   An abstract machine for `spec/sigma-resume.md`: a deterministic transition
   whose fired actions cost at least 1 ATP (Book I §3.4 "the minimum cost of any
   action is 1"; `EvalMachine.step_cost_pos`), and `adv`, the run
   `impl/sigma_resume.py` `_run` makes without host fences: fire greedily while
   the next action is affordable from what is left of the budget; stop at a
   normal form, a blocked reference, or the first unaffordable action (PAUSED,
   nothing changed). `ResumeLink.lean` instantiates the machine with Book I's
   `EvalMachine.step` and proves `_run` over it equals `adv`.

   Theorems:
     * adv_le        — a run never spends more than its budget
     * adv_seg       — a segment that spends its whole budget splits the run there
     * adv_split     — §2 segmentation invariance with credit that accumulates
                       (§3: what a segment may spend is credit_total +
                       additional_credit − spent_total): a run with `a + b`
                       equals a run with `a`, then a run from where it stopped
                       with what it left over plus `b`
     * adv_spent_det — §4 "spent strictly increases, so exactly one state has
                       it": two budgets that spend the same reach the same state

   Host fences (admission ceilings, resource checks, recursion depth, absent
   evidence) are outside the model; in `_run` they end a segment in a local
   outcome, which §2 excludes from segmentation invariance. Moved from
   s0fractal/minds (proofs/Vars1/Replay.lean, the abstract part; adv_split and
   adv_spent_det proved on top of it) on 2026-11-01. -/

namespace SigmaResume

/-- What the transition does from a state. -/
inductive Act (S : Type) where
  /-- normal form (`step5` returns `None`) -/
  | nf
  /-- the demanded hash is absent (`Unresolved`, BLOCKED_REFERENCE) -/
  | blocked
  /-- the demanded action, its successor state and its ATP price -/
  | fire (s : S) (cost : Nat)

/-- A deterministic, positively priced transition system. -/
structure Machine where
  S : Type
  step : S → Act S
  cost_pos : ∀ s s' c, step s = .fire s' c → 0 < c

variable (M : Machine)

/-- `sigma_resume._run` without host fences: greedy, atomic, pre-checked charging. -/
def adv (s : M.S) (b : Nat) : M.S × Nat :=
  match _hstep : M.step s with
  | .fire s' c =>
      if c ≤ b then ((adv s' (b - c)).1, c + (adv s' (b - c)).2) else (s, 0)
  | .nf => (s, 0)
  | .blocked => (s, 0)
termination_by b
decreasing_by have := M.cost_pos s s' c _hstep; omega

theorem adv_eq (s : M.S) (b : Nat) :
    adv M s b =
      match M.step s with
      | .fire s' c =>
          if c ≤ b then ((adv M s' (b - c)).1, c + (adv M s' (b - c)).2) else (s, 0)
      | .nf => (s, 0)
      | .blocked => (s, 0) := by
  rw [adv]; split <;> simp_all

/-- `adv` never spends more than its budget (Book I §3.4). -/
theorem adv_le (s : M.S) (b : Nat) : (adv M s b).2 ≤ b := by
  induction b using Nat.strongRecOn generalizing s with
  | _ b ih =>
    rw [adv_eq]
    split
    · rename_i s' c h
      split
      · have hc := M.cost_pos s s' c h
        have := ih (b - c) (by omega) s'
        simp only; omega
      · simp
    · simp
    · simp

/-- **Segmentation invariance, whole segments.** When the first segment spends its whole budget
(no budget refusal stopped it early), the run splits at that point. -/
theorem adv_seg (s s₁ s₂ : M.S) (a b d : Nat)
    (h₁ : adv M s a = (s₁, a)) (h₂ : adv M s₁ b = (s₂, d)) :
    adv M s (a + b) = (s₂, a + d) := by
  induction a using Nat.strongRecOn generalizing s with
  | _ a ih =>
    rw [adv_eq] at h₁
    rw [adv_eq]
    split
    · rename_i s' c hstep
      rw [hstep] at h₁
      have hc := M.cost_pos s s' c hstep
      by_cases hca : c ≤ a
      · simp only [hca, if_true, Prod.mk.injEq] at h₁
        have hrest : adv M s' (a - c) = (s₁, a - c) := by
          rw [Prod.ext_iff]; exact ⟨h₁.1, by omega⟩
        have := ih (a - c) (by omega) s' hrest
        have e : a + b - c = a - c + b := by omega
        simp only [show c ≤ a + b by omega, if_true, e, this, Prod.mk.injEq]
        exact ⟨trivial, by omega⟩
      · simp only [hca, if_false, Prod.mk.injEq] at h₁
        obtain ⟨rfl, ha⟩ := h₁
        subst ha
        simp only [Nat.zero_add]
        rw [← h₂, adv_eq M s b, hstep]
    · rename_i hstep
      rw [hstep] at h₁
      simp only [Prod.mk.injEq] at h₁
      obtain ⟨rfl, ha⟩ := h₁
      subst ha
      rw [adv_eq, hstep] at h₂
      simp_all
    · rename_i hstep
      rw [hstep] at h₁
      simp only [Prod.mk.injEq] at h₁
      obtain ⟨rfl, ha⟩ := h₁
      subst ha
      rw [adv_eq, hstep] at h₂
      simp_all

/-- **Segmentation invariance (§2), with credit that accumulates (§3).** A run with `a + b` equals a run with `a`,
then a run from where it stopped with what it left over plus `b`. -/
theorem adv_split (s : M.S) (a b : Nat) :
    adv M s (a + b) =
      ((adv M (adv M s a).1 (a - (adv M s a).2 + b)).1,
       (adv M s a).2 + (adv M (adv M s a).1 (a - (adv M s a).2 + b)).2) := by
  induction a using Nat.strongRecOn generalizing s with
  | _ a ih =>
    rw [adv_eq M s a]
    split
    · rename_i s' c hstep
      have hc := M.cost_pos s s' c hstep
      by_cases hca : c ≤ a
      · simp only [hca, if_true]
        have hle := adv_le M s' (a - c)
        have := ih (a - c) (by omega) s'
        rw [adv_eq M s (a + b), hstep]
        simp only [show c ≤ a + b by omega, if_true]
        have e : a + b - c = a - c + b := by omega
        rw [e, this]
        have e2 : a - (c + (adv M s' (a - c)).2) + b = a - c - (adv M s' (a - c)).2 + b := by omega
        rw [e2]
        simp only [Prod.mk.injEq]
        exact ⟨trivial, by omega⟩
      · simp only [hca, if_false, Nat.sub_zero, Nat.zero_add]
    · simp only [Nat.sub_zero, Nat.zero_add]
    · simp only [Nat.sub_zero, Nat.zero_add]

/-- **One state per spent (§4).** `spent` strictly increases, so at most one run reaches a given spent: two budgets
that spend the same reach the same state. -/
theorem adv_spent_det (s : M.S) (a b : Nat) (h : (adv M s a).2 = (adv M s b).2) :
    (adv M s a).1 = (adv M s b).1 := by
  induction a using Nat.strongRecOn generalizing s b with
  | _ a ih =>
    rw [adv_eq M s a, adv_eq M s b] at h ⊢
    cases hstep : M.step s with
    | fire s' c =>
      simp only [hstep] at h ⊢
      have hc := M.cost_pos s s' c hstep
      by_cases hca : c ≤ a <;> by_cases hcb : c ≤ b <;> simp only [hca, hcb, if_true, if_false] at h ⊢
      · exact ih (a - c) (by omega) s' (b - c) (by omega)
      · omega
      · omega
    | nf => simp only [hstep]
    | blocked => simp only [hstep]

/-- `true` exactly on a normal form. -/
def Act.isNF {S : Type} : Act S → Bool
  | .nf => true
  | _ => false

end SigmaResume
