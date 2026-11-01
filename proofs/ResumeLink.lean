/- sigma-resume over Book I: the abstract machine instantiated with `EvalMachine.step` (Lean 4 core).

   `EvalMachine.step t remaining store` mechanizes `sigma_glyph.step5`, the
   transition `sigma_resume` runs; it takes the remaining budget as an
   argument, while `SigmaResume.Machine.step` does not. The link is
   sigma-resume §2 "No control state" ("which action it picks does not depend
   on the remaining budget, only whether it is affordable"), proved here for
   the Lean model:
     * step_nf_any       — a normal form is a normal form at every budget
     * step_fire_any     — a fired action fires, unchanged, at every budget
                           that covers its cost
     * step_cost_le_size — an action from `t` costs at most `size t + 2`
   So `bookStep (st, t) := step t (size t + 2) st` is the budget-free
   transition, and:
     * run_eq_adv        — `_run` (without host fences), written over
                           `EvalMachine.step` as Python writes it, equals
                           `adv bookMachine`; with ResumeMachine.lean this
                           carries adv_split / adv_spent_det to Book I
     * adv_store         — a run never changes the environment
     * book_cycle_no_normal_form — from an accepted cycle witness, `_run` over
                           `EvalMachine.step` at any budget stops at a term that
                           is not a normal form at any budget. No Book I term
                           with a state cycle is known, so for Book I this says
                           what an accepted witness would mean; the experimental
                           Y/M/W profile is not mechanized.
   A state is `(store, term)`: the store is the environment the computation
   root fixes. Moved from s0fractal/minds (proofs/Vars1Sigma/Link.lean, without
   the VARS checkpoint lineage) on 2026-11-01. -/
import EvalMachine
import ResumeMachine
import ResumeCycle

namespace SigmaResume

open EvalMachine

deriving instance DecidableEq for Term

theorem step_nf_any (t : Term) (r : Nat) (st : Store) (h : step t r st = .nf) (R : Nat) :
    step t R st = .nf := by
  fun_induction step t r st <;> grind [step]

theorem step_fire_any (t : Term) (r : Nat) (st : Store) (t' : Term) (c : Nat)
    (h : step t r st = .step t' c) (R : Nat) (hR : c ≤ R) : step t R st = .step t' c := by
  fun_induction step t r st generalizing t' c <;> grind [step, step_nf_any, size_pos]

theorem force_size (h : MachineBytes.Bytes) (st : Store) (v : Term) (hv : force h st = some v) :
    size v ≤ 3 := by
  unfold force at hv
  split at hv
  · cases hv; simp [size]
  split at hv
  · cases hv; simp [size]
  split at hv
  · cases hv; simp [size]
  split at hv
  · cases hv
  split at hv
  · cases hv; simp [size]
  · rename_i n _; cases hv; cases n <;> simp [ofNode, size]

theorem step_cost_le_size (t : Term) (r : Nat) (st : Store) (t' : Term) (c : Nat)
    (h : step t r st = .step t' c) : c ≤ size t + 2 := by
  fun_induction step t r st generalizing t' c <;> grind [size, force_size]

/-- The budget-free Book I transition on `(store, term)`. An unaffordable answer
cannot occur at budget `size t + 2` (it would need a cost above the bound); it is
mapped to `blocked`, never to `nf`, so `isNF` is never granted by it. -/
def bookStep (s : Store × Term) : Act (Store × Term) :=
  match step s.2 (size s.2 + 2) s.1 with
  | .nf => .nf
  | .unresolved => .blocked
  | .exhausted => .blocked
  | .step t' c => .fire (s.1, t') c

theorem bookStep_cost_pos (s s' : Store × Term) (c : Nat) (h : bookStep s = .fire s' c) :
    0 < c := by
  unfold bookStep at h
  cases hs : step s.2 (size s.2 + 2) s.1 with
  | step t' c' =>
    rw [hs] at h
    have := step_cost_pos _ _ _ _ _ hs
    cases h; omega
  | nf => rw [hs] at h; cases h
  | unresolved => rw [hs] at h; cases h
  | exhausted => rw [hs] at h; cases h

/-- Book I as a `SigmaResume.Machine`. -/
def bookMachine : Machine where
  S := Store × Term
  step := bookStep
  cost_pos := bookStep_cost_pos

instance : DecidableEq bookMachine.S := inferInstanceAs (DecidableEq (Store × Term))

/-- `sigma_resume._run` over `EvalMachine.step`, without host fences (resource
checks, recursion depth, `max_actions`): ask `step` with what is left of the
budget; stop on anything but a fired action. -/
def run (st : Store) : Nat → Term → Nat → Nat → Term × Nat
  | 0, t, _, sp => (t, sp)
  | f + 1, t, av, sp =>
      match step t (av - sp) st with
      | .step t' c => run st f t' av (sp + c)
      | _ => (t, sp)

/-- **The Python-shaped run is the abstract `adv`.** With fuel above the budget
(each action costs ≥ 1), `_run` from `spent = sp` with `b` available returns the
state and spending of `adv bookMachine`. -/
theorem run_eq_adv (st : Store) :
    ∀ (b f : Nat) (t : Term) (sp : Nat), b < f →
      run st f t (sp + b) sp =
        ((adv bookMachine (st, t) b).1.2, sp + (adv bookMachine (st, t) b).2) := by
  intro b
  induction b using Nat.strongRecOn with
  | _ b ih =>
    intro f t sp hf
    obtain ⟨f, rfl⟩ : ∃ g, f = g + 1 := ⟨f - 1, by omega⟩
    rw [adv_eq]
    simp only [run, Nat.add_sub_cancel_left]
    -- nothing fires at budget `b` unless the budget-free step fires the same action
    have lift : ∀ t'' c'', step t b st = .step t'' c'' →
        step t (size t + 2) st = .step t'' c'' ∧ c'' ≤ b := fun t'' c'' hb =>
      ⟨step_fire_any _ _ _ _ _ hb _ (step_cost_le_size _ _ _ _ _ hb), step_cost_le _ _ _ _ _ hb⟩
    cases hR : step t (size t + 2) st with
    | nf =>
      simp [bookMachine, bookStep, hR, step_nf_any _ _ _ hR b]
    | unresolved =>
      cases hb : step t b st with
      | step t'' c'' => have := (lift _ _ hb).1; rw [hR] at this; cases this
      | _ => simp [bookMachine, bookStep, hR]
    | exhausted =>
      cases hb : step t b st with
      | step t'' c'' => have := (lift _ _ hb).1; rw [hR] at this; cases this
      | _ => simp [bookMachine, bookStep, hR]
    | step t' c =>
      have hc := step_cost_pos _ _ _ _ _ hR
      simp only [bookMachine, bookStep, hR]
      by_cases hcb : c ≤ b
      · rw [step_fire_any _ _ _ _ _ hR b hcb]
        simp only [hcb, if_true]
        have e : sp + b = (sp + c) + (b - c) := by omega
        rw [e, ih (b - c) (by omega) f t' (sp + c) (by omega)]
        simp only [bookMachine, Prod.mk.injEq, true_and]; omega
      · simp only [hcb, if_false]
        cases hb : step t b st with
        | step t'' c'' =>
          obtain ⟨h2, h3⟩ := lift _ _ hb
          rw [hR] at h2; cases h2; omega
        | _ => simp

/-- `isNF` of the budget-free step is the Python probe's `NORMAL_FORM` with zero
actions, at whatever credit the probe is given. -/
theorem bookStep_isNF_iff (st : Store) (t : Term) (r : Nat) :
    (bookStep (st, t)).isNF = true ↔ step t r st = .nf := by
  unfold bookStep
  constructor
  · intro h
    split at h <;> simp_all [Act.isNF]
    rename_i hnf; exact step_nf_any _ _ _ hnf r
  · intro h
    rw [step_nf_any _ _ _ h]; rfl

/-- `adv` never changes the environment. -/
theorem adv_store (s : bookMachine.S) (b : Nat) : (adv bookMachine s b).1.1 = s.1 := by
  induction b using Nat.strongRecOn generalizing s with
  | _ b ih =>
    rw [adv_eq]
    simp only [bookMachine, bookStep]
    cases hs : step s.2 (size s.2 + 2) s.1 with
    | step t' c =>
      have := step_cost_pos _ _ _ _ _ hs
      simp only
      split
      · exact ih (b - c) (by omega) _
      · rfl
    | _ => simp

/-- **An accepted cycle witness for Book I.** If `checkCycle` over `bookMachine` returns `CYCLE_PROVEN`, then for
every budget `b`, the Python-shaped `_run` of `EvalMachine.step` from the start with `b` available stops at a term
that `step` does not call a normal form, at whatever budget it is asked. -/
theorem book_cycle_no_normal_form {maxAtp : Nat} {start entry : bookMachine.S} {k n cost : Nat}
    (h : checkCycle bookMachine maxAtp start entry k n cost = .proven) (b r : Nat) :
    step (run start.1 (b + 1) start.2 b 0).1 r start.1 ≠ .nf := by
  have hrun := run_eq_adv start.1 b (b + 1) start.2 0 (by omega)
  rw [Nat.zero_add] at hrun
  have hfire := (cycle_proven_no_normal_form bookMachine h).2 b
  have hst := adv_store start b
  have e : (adv bookMachine (start.1, start.2) b).1 =
      (start.1, (adv bookMachine (start.1, start.2) b).1.2) := Prod.ext hst rfl
  rw [hrun]
  simp only
  intro hnf
  have := (bookStep_isNF_iff start.1 _ r).2 hnf
  have hfire' : (bookStep (adv bookMachine (start.1, start.2) b).1).isFire = true := hfire
  rw [e] at hfire'
  rw [isFire_not_isNF hfire'] at this
  cases this

end SigmaResume
