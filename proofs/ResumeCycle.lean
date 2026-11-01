/- sigma-resume §5, mechanized: what an accepted cycle witness means (Lean 4 core).

   A cycle witness claims that a computation never reaches a normal form: from
   the root, a run to exactly `entry_spent_total` reaches an entry state, and
   from there `cycle_action_count` actions costing `cycle_cost` return to the
   same state. `checkCycle` is `impl/sigma_resume.py` `verify_cycle` over the
   machine of `ResumeMachine.lean`, in its order of checks:
     1. `n = 0` or `cost = 0`, or `n > cost` (every action costs at least 1):
        refused (INVALID_CYCLE_WITNESS);
     2. `cost` above the host ceiling `maxAtp`: NOT_ASSESSED (a local refusal);
     3. the prefix: `advance` from the start with `entry_spent` credit. Its own
        admission ceiling turns `entry_spent > maxAtp` into a non-PAUSED
        outcome, which `verify_cycle` reads as PREFIX_MISMATCH (refused);
        otherwise the run must spend exactly `entry_spent`, stop PAUSED (an
        action fires from the entry) and stop at the claimed entry state;
     4. the period: `runN entry cost n` must do `n` actions, spend exactly
        `cost`, and end at the entry state.
   The checks `verify_cycle` makes on documents (the witness's shape and
   integer domain, its `computation_id` against the chosen root, the root's
   environment, runtime and cost model) only refuse; they are outside the
   model, which makes it more permissive and the theorems stronger. So are its
   host fences, which in `verify_cycle` turn into refusals.

   The bridge proofs/resume_bridge_check.py runs `checkCycle`, compiled
   (ResumeCycleRun.lean), against `verify_cycle` on generated transition
   tables, true witnesses and their neighbours.

   Theorems:
     * checkCycle_sound — CYCLE_PROVEN means `adv` from the start by
                          `entry_spent` reaches the entry spending exactly that,
                          and `n ≥ 1` actions from the entry return to it at `cost`
     * cycle_fires_forever — then for every `m`, `m` actions fire from the start
     * cycle_no_stop    — then at every budget, `adv` from the start ends at a
                          state from which an action fires: never a normal form,
                          never a blocked reference
     * cycle_proven_no_normal_form — the two together, from `checkCycle` alone

   Moved from s0fractal/minds (proofs/Vars1/Cycle.lean, without the VARS gate)
   on 2026-11-01. -/
import ResumeMachine

set_option linter.unusedSectionVars false

namespace SigmaResume

variable (M : Machine)

/-- `true` exactly when an action fires. -/
def Act.isFire {S : Type} : Act S → Bool
  | .fire _ _ => true
  | _ => false

/-- `sigma_resume._run(s, b, max_actions=n)` without host fences: (state, spent, actions done). -/
def runN : M.S → Nat → Nat → M.S × Nat × Nat
  | s, _, 0 => (s, 0, 0)
  | s, b, n + 1 =>
      match M.step s with
      | .fire s' c =>
          if c ≤ b then
            let r := runN s' (b - c) n
            (r.1, c + r.2.1, r.2.2 + 1)
          else (s, 0, 0)
      | _ => (s, 0, 0)

/-- `n` fired actions from `s`, whatever they cost: the state reached and their total cost. -/
def steps : Nat → M.S → Option (M.S × Nat)
  | 0, s => some (s, 0)
  | n + 1, s =>
      match M.step s with
      | .fire s' c => (steps n s').map (fun r => (r.1, c + r.2))
      | _ => none

/-- What `verify_cycle` returns, up to the name of a refusal. -/
inductive CycleStatus where
  | proven | notAssessed | refused
  deriving DecidableEq, Repr

variable [DecidableEq M.S]

/-- `sigma_resume.verify_cycle` on the machine-level fields of a witness: the start state of the root the verifier
chose, the entry state the witness names, `entry_spent`, `cycle_actions`, `cycle_cost`. -/
def checkCycle (maxAtp : Nat) (start entry : M.S) (entrySpent n cost : Nat) : CycleStatus :=
  if n = 0 ∨ cost = 0 then .refused
  else if cost < n then .refused
  else if maxAtp < cost then .notAssessed
  else if maxAtp < entrySpent then .refused
  else
    let p := adv M start entrySpent
    if p.2 = entrySpent ∧ (M.step p.1).isFire = true ∧ p.1 = entry then
      let r := runN M p.1 cost n
      if r.2.2 = n ∧ r.2.1 = cost ∧ r.1 = p.1 then .proven else .refused
    else .refused

/-- A run of `runN` that did all `n` actions is `n` fired steps. -/
theorem runN_steps : ∀ (n : Nat) (s : M.S) (b : Nat),
    (runN M s b n).2.2 = n → steps M n s = some ((runN M s b n).1, (runN M s b n).2.1)
  | 0, s, b, _ => by simp [runN, steps]
  | n + 1, s, b, h => by
    simp only [runN, steps] at h ⊢
    split at h
    · rename_i s' c hs
      by_cases hc : c ≤ b
      · simp only [hc, if_true] at h ⊢
        rw [runN_steps n s' (b - c) (by omega)]
        rfl
      · simp [hc] at h
    · simp at h

theorem steps_add : ∀ (a b : Nat) (s : M.S),
    steps M (a + b) s =
      (steps M a s).bind (fun r => (steps M b r.1).map (fun q => (q.1, r.2 + q.2)))
  | 0, b, s => by
    simp only [Nat.zero_add, steps, Option.bind_some]
    cases steps M b s <;> simp
  | a + 1, b, s => by
    rw [show a + 1 + b = (a + b) + 1 by omega]
    simp only [steps]
    split
    · rename_i s' c _
      rw [steps_add a b s']
      cases steps M a s' with
      | none => simp
      | some r =>
        simp only [Option.bind_some, Option.map_some]
        cases steps M b r.1 <;> simp [Nat.add_assoc]
    · simp

/-- A prefix of a run that fires is a run that fires. -/
theorem steps_prefix {a b : Nat} {s : M.S} (h : a ≤ b) (hb : (steps M b s).isSome) : (steps M a s).isSome := by
  obtain ⟨k, rfl⟩ : ∃ k, b = a + k := ⟨b - a, by omega⟩
  rw [steps_add] at hb
  cases ha : steps M a s with
  | none => rw [ha] at hb; simp at hb
  | some _ => rfl

/-- What `adv` reaches, `steps` reaches, at the same cost. -/
theorem adv_reach (s : M.S) (b : Nat) : ∃ m, steps M m s = some (adv M s b) := by
  induction b using Nat.strongRecOn generalizing s with
  | _ b ih =>
    rw [adv_eq]
    split
    · rename_i s' c hs
      split
      · rename_i hc
        have hpos := M.cost_pos s s' c hs
        obtain ⟨m, hm⟩ := ih (b - c) (by omega) s'
        exact ⟨m + 1, by simp [steps, hs, hm]⟩
      · exact ⟨0, rfl⟩
    · exact ⟨0, rfl⟩
    · exact ⟨0, rfl⟩

/-- From an entry that returns to itself in `n ≥ 1` actions, every number of actions fires. -/
theorem cycle_from_entry {e : M.S} {n cost : Nat} (hn : 0 < n) (hc : steps M n e = some (e, cost)) :
    ∀ j, (steps M j e).isSome := by
  intro j
  induction j using Nat.strongRecOn with
  | _ j ih =>
    by_cases hj : j < n
    · exact steps_prefix M (Nat.le_of_lt hj) (by rw [hc]; rfl)
    · have e1 : j = n + (j - n) := by omega
      rw [e1, steps_add, hc]
      have := ih (j - n) (by omega)
      cases h : steps M (j - n) e with
      | none => rw [h] at this; simp at this
      | some _ => simp [h]

/-- **The machine never stops.** If the start reaches the entry by firing, and the entry returns to itself in
`n ≥ 1` actions, then from the start every number of actions fires. -/
theorem cycle_fires_forever {s e : M.S} {k k' n cost : Nat} (hpre : steps M k s = some (e, k')) (hn : 0 < n)
    (hc : steps M n e = some (e, cost)) : ∀ m, (steps M m s).isSome := by
  intro m
  by_cases hm : m ≤ k
  · exact steps_prefix M hm (by rw [hpre]; rfl)
  · have e1 : m = k + (m - k) := by omega
    rw [e1, steps_add, hpre]
    have := cycle_from_entry M hn hc (m - k)
    cases h : steps M (m - k) e with
    | none => rw [h] at this; simp at this
    | some _ => simp [h]

/-- If `m + 1` actions fire from `s`, the state after `m` of them fires. -/
theorem steps_succ_fires {m : Nat} {s t : M.S} {c : Nat} (h : steps M m s = some (t, c))
    (h1 : (steps M (m + 1) s).isSome) : (M.step t).isFire = true := by
  rw [steps_add, h] at h1
  simp only [Option.bind_some] at h1
  cases hs : M.step t with
  | fire _ _ => rfl
  | nf => simp [steps, hs] at h1
  | blocked => simp [steps, hs] at h1

/-- **No budget stops it.** Under the same premises, at every budget `adv` from the start ends at a state from which
an action fires: never a normal form, never a blocked reference; the run only ever pauses. -/
theorem cycle_no_stop {s e : M.S} {k k' n cost : Nat} (hpre : steps M k s = some (e, k')) (hn : 0 < n)
    (hc : steps M n e = some (e, cost)) (b : Nat) : (M.step (adv M s b).1).isFire = true := by
  obtain ⟨m, hm⟩ := adv_reach M s b
  exact steps_succ_fires M hm (cycle_fires_forever M hpre hn hc (m + 1))

/-- **What `CYCLE_PROVEN` establishes.** -/
theorem checkCycle_sound {maxAtp : Nat} {start entry : M.S} {entrySpent n cost : Nat}
    (h : checkCycle M maxAtp start entry entrySpent n cost = .proven) :
    adv M start entrySpent = (entry, entrySpent) ∧ 0 < n ∧ steps M n entry = some (entry, cost) := by
  unfold checkCycle at h
  simp only at h
  split at h; · cases h
  split at h; · cases h
  split at h; · cases h
  split at h; · cases h
  rename_i h0 _ _ _
  split at h
  · rename_i hp
    obtain ⟨hsp, -, hen⟩ := hp
    split at h
    · rename_i hr
      obtain ⟨hdone, hcost, hstate⟩ := hr
      have hst := runN_steps M n _ cost hdone
      rw [hcost, hstate, hen] at hst
      refine ⟨?_, by omega, hst⟩
      rw [Prod.ext_iff]; exact ⟨hen, hsp⟩
    · cases h
  · cases h

/-- **An accepted cycle witness: no normal form, at any budget.** -/
theorem cycle_proven_no_normal_form {maxAtp : Nat} {start entry : M.S} {entrySpent n cost : Nat}
    (h : checkCycle M maxAtp start entry entrySpent n cost = .proven) :
    (∀ m, (steps M m start).isSome) ∧ ∀ b, (M.step (adv M start b).1).isFire = true := by
  obtain ⟨hadv, hn, hc⟩ := checkCycle_sound M h
  obtain ⟨k, hk⟩ := adv_reach M start entrySpent
  rw [hadv] at hk
  exact ⟨cycle_fires_forever M hk hn hc, cycle_no_stop M hk hn hc⟩

theorem isFire_not_isNF {S : Type} {a : Act S} (h : a.isFire = true) : a.isNF = false := by
  cases a <;> simp_all [Act.isFire, Act.isNF]

end SigmaResume
