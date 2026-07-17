/-! # Book I §6: the canonical λ→SKI compiler (Profile C1), mechanized

Models the §6 C1 algorithm — `C1[x]=x`, `C1[(M N)]=APPLY(C1 M, C1 N)`,
`C1[λx.M]=A(x, C1 M)` with the bracket-abstraction rules A-1/A-2/A-3 — and
proves its central correctness property:

  **C1 preserves free variables exactly** (`mem_skiFv_c1`), hence a CLOSED
  λ-term compiles to a variable-free SKI term (`c1_closed`).

That is the totality the reference implementation (`impl/sigma_glyph.py`,
`_abstract`) enforces at runtime with a `free variable escapes abstraction`
guard: for closed input that guard can *never* fire — here it is a theorem, not
a runtime check. Determinism is definitional: `c1` is a total pure function.

Core Lean 4 (v4.31.0), no mathlib. Discharge with `lean proofs/C1Compiler.lean`.
The §6 TV-10 vectors are pinned concretely by `rfl` at the end.
-/

namespace Book1.C1

/-- λ-terms: the C1 frontend accepts closed λ-terms (var / application /
abstraction). -/
inductive Lam where
  | var : String → Lam
  | app : Lam → Lam → Lam
  | lam : String → Lam → Lam
deriving Repr, DecidableEq

/-- Book I SKI terms. `var` appears only transiently during abstraction; the
theorem below shows C1 on closed input yields a var-free term (⟨I⟩/⟨K⟩/⟨S⟩ and
applications only — a genuine Book I term). -/
inductive Ski where
  | I : Ski
  | K : Ski
  | S : Ski
  | app : Ski → Ski → Ski
  | var : String → Ski
deriving Repr, DecidableEq

/-- Free variables of a λ-term (§6 FV, capture-avoiding). -/
def fv : Lam → List String
  | .var x   => [x]
  | .app f a => fv f ++ fv a
  | .lam x b => (fv b).filter (· != x)

/-- Free variables of an SKI term (I/K/S are closed). -/
def skiFv : Ski → List String
  | .app f a => skiFv f ++ skiFv a
  | .var x   => [x]
  | _        => []

/-- §6 bracket abstraction `A(x, M)`, checked strictly in order (A-1, A-2, A-3).
Total by construction: C1 only ever hands `A` an already-compiled SKI term
(I/K/S/app/var), never a λ, so the reference's "free variable escapes" case —
`x ∈ FV(m)` with `m` neither `var x` nor an application — is unreachable, since
I/K/S are closed and a lone `var y` with `y ≠ x` has `x ∉ FV`. -/
def abstr (x : String) : Ski → Ski
  | .var y   => if y = x then .I else .app .K (.var y)   -- A-1 / A-2 on a var
  | .app f a =>
      -- §6 checks A-2 (`x ∉ FV M → K M`) BEFORE A-3, for applications too.
      if x ∈ skiFv f ++ skiFv a
      then .app (.app .S (abstr x f)) (abstr x a)        -- A-3 (x ∈ FV)
      else .app .K (.app f a)                            -- A-2 (x ∉ FV)
  | m        => .app .K m                                -- A-2: I/K/S are closed

/-- The §6 compiler. -/
def c1 : Lam → Ski
  | .var x   => .var x
  | .app f a => .app (c1 f) (c1 a)
  | .lam x b => abstr x (c1 b)

/-- `A(x, ·)` removes exactly `x` from the free variables. -/
theorem mem_skiFv_abstr (x z : String) (m : Ski) :
    z ∈ skiFv (abstr x m) ↔ z ∈ skiFv m ∧ z ≠ x := by
  induction m with
  | var y =>
    by_cases h : y = x
    · subst h; simp [abstr, skiFv]
    · simp only [abstr, if_neg h, skiFv, List.nil_append, List.mem_singleton]
      constructor
      · intro hz; exact ⟨hz, fun hzx => h (hz ▸ hzx)⟩
      · exact fun hz => hz.1
  | app f a ihf iha =>
    simp only [abstr]
    split
    · -- A-3 branch: x ∈ FV, so abstr = S (abstr x f) (abstr x a)
      simp only [skiFv, List.nil_append, List.mem_append, ihf, iha]
      constructor
      · rintro (⟨hf, hx⟩ | ⟨ha, hx⟩)
        · exact ⟨Or.inl hf, hx⟩
        · exact ⟨Or.inr ha, hx⟩
      · rintro ⟨hf | ha, hx⟩
        · exact Or.inl ⟨hf, hx⟩
        · exact Or.inr ⟨ha, hx⟩
    · -- A-2 branch: x ∉ FV, so abstr = K (app f a); z ∈ FV already forces z ≠ x
      rename_i hin
      simp only [skiFv, List.nil_append, List.mem_append]
      constructor
      · intro hz
        exact ⟨hz, fun h => hin (List.mem_append.mpr (h ▸ hz))⟩
      · exact fun hz => hz.1
  | I => simp [abstr, skiFv]
  | K => simp [abstr, skiFv]
  | S => simp [abstr, skiFv]

/-- **C1 preserves free variables exactly.** -/
theorem mem_skiFv_c1 (z : String) (t : Lam) :
    z ∈ skiFv (c1 t) ↔ z ∈ fv t := by
  induction t with
  | var x => simp [c1, skiFv, fv]
  | app f a ihf iha =>
    simp [c1, skiFv, fv, List.mem_append, ihf, iha]
  | lam x b ih =>
    simp only [c1, fv, mem_skiFv_abstr, ih, List.mem_filter, bne_iff_ne]

/-- **A closed λ-term compiles to a variable-free SKI term.** The reference
implementation's runtime "free variable escapes abstraction" guard can never
fire on closed input. -/
theorem c1_closed (t : Lam) (h : ∀ z, z ∉ fv t) : ∀ z, z ∉ skiFv (c1 t) := by
  intro z hz
  exact h z ((mem_skiFv_c1 z t).mp hz)

/-- §6 / TV-10 pinned concretely: `C1[λx.x] = ⟨I⟩`. -/
example : c1 (.lam "x" (.var "x")) = .I := rfl

/-- §6 / TV-10 pinned concretely: `C1[λx.λy.x] = APPLY(APPLY(⟨S⟩, APPLY(⟨K⟩,⟨K⟩)), ⟨I⟩)`
(the `S (K K) I` citizen extensionally equal to K; C1 is syntactically, not
extensionally, canonical). -/
example : c1 (.lam "x" (.lam "y" (.var "x")))
    = .app (.app .S (.app .K .K)) .I := rfl

end Book1.C1
