/- Book I evaluator, mechanized (Lean 4 core).

   A faithful model of the v0.5 hash-thunk machine (`step5`/`eval_hash` in
   impl/sigma_glyph.py): leftmost-outermost reduction with lazy left-spine
   resolution and size-priced ATP under the hash-leaf size model. Terms are
   graphs of materialized nodes over unresolved hashes (thunks); genesis
   I/K/S are recognized by hash without a store (§5.1). The differential
   bridge proofs/eval_bridge_check.py ties this to the live oracle on every
   eval conformance vector (result hash AND atp_spent, byte-exact).

   Theorems:
     * step_cost_pos — every priced action costs ≥ 1 (the spec's "minimum
                       cost of any action is 1"): reduction cannot stall on a
                       zero-cost loop, so eval is total by construction
     * eval_spent_le — `eval` never spends more than its budget: spent ≤ atp
                       (Book I §3.4 "spent never exceeds atp", now a theorem
                       for ALL terms and budgets, not just the pinned vectors)
   Totality is definitional (fuel-indexed structural recursion, a total
   function); determinism is definitional (it is a function). The bridge is
   the empirical check that this total, budget-respecting function IS the
   oracle. -/
import MachineBytes

namespace EvalMachine

open MachineBytes (Bytes)

/-- Hash-thunk terms (mirrors impl/sigma_glyph.py: thunk/lit/ref/dis/app). -/
inductive Term where
  | thunk (h : Bytes)
  | lit (atom : Bytes)
  | ref (target : Bytes)
  | dis (reason : Bytes)
  | app (f a : Term)
deriving Repr, Inhabited

/-- Hash-leaf size model (ADR-001×003): materialized nodes count 1, an
    unresolved hash leaf counts 1, a materialized REF counts 2. -/
def size : Term → Nat
  | .app f a => 1 + size f + size a
  | .ref _ => 2
  | _ => 1

/-- NodeHash of a term (hash-transparent on thunks). -/
def termHash : Term → Bytes
  | .thunk h => h
  | .lit a => MachineBytes.nodeHash (.lit a)
  | .ref h => MachineBytes.nodeHash (.ref h)
  | .dis r => MachineBytes.nodeHash (.dis r)
  | .app f a => MachineBytes.nodeHash (.app (termHash f) (termHash a))

/-- reason hashes (§4.2 / §3.4 canonical outcomes). -/
def rInvalid : Bytes := Sha256.sha256 ("Invalid Object".toUTF8.toList)
def rATP : Bytes := Sha256.sha256 ("ATP Exhausted".toUTF8.toList)
def rUnres : Bytes := Sha256.sha256 ("Unresolved Reference".toUTF8.toList)

/-- genesis atoms and node hashes (§5.1, intrinsic). -/
def atomI : Bytes := Sha256.sha256 ("I".toUTF8.toList)
def atomK : Bytes := Sha256.sha256 ("K".toUTF8.toList)
def atomS : Bytes := Sha256.sha256 ("S".toUTF8.toList)
def gI : Bytes := MachineBytes.nodeHash (.lit atomI)
def gK : Bytes := MachineBytes.nodeHash (.lit atomK)
def gS : Bytes := MachineBytes.nodeHash (.lit atomS)

def isGenesis (h : Bytes) : Bool := h = gI || h = gK || h = gS

/-- O(1) glyph check for redex heads (§3.2 Identity by Hash): a thunk carries
    its hash; a materialized LITERAL hashes; nothing else can equal a
    LITERAL's NodeHash (modulo CP-24). -/
def glyphEq : Term → Bytes → Bool
  | .thunk h, gh => h = gh
  | .lit a, gh => MachineBytes.nodeHash (.lit a) = gh
  | _, _ => false

/-- CAS: bytes are keyed by their SHA-256. -/
abbrev Store := List Bytes

def storeGet (st : Store) (h : Bytes) : Option Bytes :=
  st.find? (fun b => Sha256.sha256 b = h)

/-- Node → Term (a freshly materialized node has thunk children). -/
def ofNode : MachineBytes.Node → Term
  | .lit a => .lit a
  | .ref t => .ref t
  | .dis r => .dis r
  | .app l r => .app (.thunk l) (.thunk r)

/-- Materialize ONE node from hash h; genesis intrinsic, deser failure →
    Canonical Invalid Object. `none` = unresolved (not in store, not genesis). -/
def force (h : Bytes) (st : Store) : Option Term :=
  if h = gI then some (.lit atomI)
  else if h = gK then some (.lit atomK)
  else if h = gS then some (.lit atomS)
  else match storeGet st h with
    | none => none
    | some b => match MachineBytes.deserialize b with
        | none => some (.dis rInvalid)
        | some n => some (ofNode n)

/-- one priced action of the machine. -/
inductive StepResult where
  | nf                              -- normal form
  | exhausted                       -- demanded action unaffordable
  | unresolved                      -- demanded hash absent
  | step (t : Term) (cost : Nat)    -- fired: new term, cost spent
deriving Repr

/-- `step t remaining store` — leftmost-outermost, lazy spine, size-priced.
    Structural recursion on the term: the spine descent recurses only on the
    subterms of an `app`. Redex heads (§3.1) are recognized by hash: R-I when
    the function is ⟨I⟩; R-K when it is `app ⟨K⟩ _`; R-S when it is
    `app (app ⟨S⟩ _) _` (note `glyphEq` is false on any `app`, so R-K/R-S only
    fire on the exact spine shapes — matching step5). -/
def step (t : Term) (remaining : Nat) (st : Store) : StepResult :=
  match t with
  | .thunk h =>
      if isGenesis h then .nf                       -- NF leaf by hash (§5.1)
      else if remaining < 1 then .exhausted
      else match force h st with
        | none => .unresolved
        | some v =>
            let c := size v                          -- 1/2/3 by node kind
            if c > remaining then .exhausted         -- fetched bytes discarded
            else .step v c
  | .ref h =>
      if remaining < 1 then .exhausted
      else .step (.thunk h) 1                        -- R-R: one level
  | .lit _ => .nf
  | .dis _ => .nf
  | .app f a =>
      -- descent: demand the function spine, then the argument (step5's tail)
      let descend : StepResult :=
        match step f remaining st with
        | .step f' c => .step (.app f' a) c
        | .nf =>
            match step a remaining st with
            | .step a' c => .step (.app f a') c
            | other => other
        | other => other
      match f with
      | .app (.app f11 f12) f2 =>                    -- f = ((f11 f12) f2)
          if glyphEq f11 gS then                     -- R-S: x=f12, y=f2, z=a
            (if 1 + size a > remaining then .exhausted
             else .step (.app (.app f12 a) (.app f2 a)) (1 + size a))
          else descend
      | .app f1 f2 =>                                -- f = (f1 f2), f1 not an app
          if glyphEq f1 gK then
            (if remaining < 1 then .exhausted else .step f2 1)  -- R-K
          else descend
      | _ =>                                         -- f not an app
          if glyphEq f gI then
            (if remaining < 1 then .exhausted else .step a 1)   -- R-I
          else descend
  termination_by sizeOf t

/-- iterate `step` under a fuel bound (fuel = an upper bound on the number of
    priced actions; `atp + 1` always suffices since each action costs ≥ 1).
    Returns (result term, atp spent). Total: structural recursion on fuel. -/
def eval : Nat → Term → Nat → Nat → Store → Term × Nat
  | 0,        t, _,   spent, _  => (t, spent)          -- fuel out (unreached at atp+1)
  | fuel + 1, t, atp, spent, st =>
      match step t (atp - spent) st with
      | .nf => (t, spent)
      | .exhausted => (.dis rATP, spent)
      | .unresolved => (.dis rUnres, spent)
      | .step t' c => eval fuel t' atp (spent + c) st

/-- top-level: eval a term hash under a budget. -/
def evalHash (h : Bytes) (atp : Nat) (st : Store) : Term × Nat :=
  eval (atp + 1) (.thunk h) atp 0 st

/- ---------- theorems ---------- -/

/-- the hash-leaf size of any term is ≥ 1. -/
theorem size_pos (t : Term) : 1 ≤ size t := by
  cases t <;> simp [size] <;> omega

/-- both bounds at once, in a shape `fun_induction step` can chew on: whatever
    `step` returns, a fired action's cost sits in `[1, remaining]`. -/
theorem step_bounds (t : Term) (rem : Nat) (st : Store) :
    (match step t rem st with
     | .step _ c => 1 ≤ c ∧ c ≤ rem
     | _ => True) := by
  fun_induction step t rem st <;> grind [size_pos, size]

/-- a fired action never costs more than the remaining budget. -/
theorem step_cost_le (t : Term) (rem : Nat) (st : Store) (t' : Term) (c : Nat)
    (h : step t rem st = .step t' c) : c ≤ rem := by
  have := step_bounds t rem st; rw [h] at this; exact this.2

/-- every priced action costs ≥ 1: the machine cannot loop at zero cost, so
    reduction strictly draws down the budget (spec §3.4 "minimum cost 1"). -/
theorem step_cost_pos (t : Term) (rem : Nat) (st : Store) (t' : Term) (c : Nat)
    (h : step t rem st = .step t' c) : 1 ≤ c := by
  have := step_bounds t rem st; rw [h] at this; exact this.1

/-- `eval` never overspends: spent ≤ atp for all terms, budgets, fuel.
    (Uses `step_cost_le`: an accepted step's cost fits in `atp - spent`.) -/
theorem eval_spent_le (fuel : Nat) (t : Term) (atp spent : Nat) (st : Store)
    (h : spent ≤ atp) : (eval fuel t atp spent st).2 ≤ atp := by
  induction fuel generalizing t spent with
  | zero => simpa [eval] using h
  | succ fuel ih =>
      rw [eval]
      split
      · exact h
      · exact h
      · exact h
      · rename_i t' c heq
        have hc : c ≤ atp - spent := step_cost_le _ _ _ _ _ heq
        exact ih t' (spent + c) (by omega)

/-- top-level corollary: `evalHash` respects its budget. -/
theorem evalHash_spent_le (hsh : Bytes) (atp : Nat) (st : Store) :
    (evalHash hsh atp st).2 ≤ atp :=
  eval_spent_le _ _ _ _ _ (Nat.zero_le _)

/- ---------- the ADR-001 memory bound, ON the concrete evaluator ----------
   `SizeBound.lean` proves `size ≤ spent + 1` for an abstract seven-row
   accounting model, and `bridge_check.py` checks the per-step premise on
   live oracle traces without row-by-row correspondence. Here the premise is
   a THEOREM about the faithful evaluator itself: every priced action's size
   growth is ≤ cost − 1, so the bound holds end-to-end with no classifier. -/

/-- per-step memory accounting (the exact §3.4 row correspondence): a fired
    action grows the term by at most `cost − 1` (`size t' + 1 ≤ size t + c`).
    Note R-S is the only growing rule and it holds *unconditionally* — the
    discarded ⟨S⟩ head contributes `size ≥ 0` of slack, no leaf assumption. -/
theorem size_step (t : Term) (rem : Nat) (st : Store) :
    (match step t rem st with
     | .step t' c => size t' + 1 ≤ size t + c
     | _ => True) := by
  fun_induction step t rem st <;> grind [size, size_pos]

/-- `eval` preserves the memory bound `size ≤ spent + 1`. -/
theorem eval_size_bound (fuel : Nat) (t : Term) (atp spent : Nat) (st : Store)
    (h : size t ≤ spent + 1) :
    size (eval fuel t atp spent st).1 ≤ (eval fuel t atp spent st).2 + 1 := by
  induction fuel generalizing t spent with
  | zero => simpa [eval] using h
  | succ fuel ih =>
      rw [eval]
      split
      · simpa using h
      · simp [size]        -- ATP Exhausted: DISSONANCE leaf, size 1 ≤ spent+1
      · simp [size]        -- Unresolved Reference: likewise
      · rename_i t' c heq
        have hs := size_step t (atp - spent) st
        rw [heq] at hs
        exact ih t' (spent + c) (by omega)

/-- the memory bound on the top-level evaluator: the materialized result of
    `evalHash` never exceeds `spent + 1` nodes (ADR-001, §3.4), now a Lean
    theorem about the same function the differential bridge pins to the
    oracle — the step-tag / row-correspondence gap, closed by proof. -/
theorem evalHash_size_bound (hsh : Bytes) (atp : Nat) (st : Store) :
    size (evalHash hsh atp st).1 ≤ (evalHash hsh atp st).2 + 1 :=
  eval_size_bound _ _ _ _ _ (by simp [size])

end EvalMachine
