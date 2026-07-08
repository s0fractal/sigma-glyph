/- Book II wave algebra, mechanized (Lean 4 core, no mathlib).

   Mirrors impl/sigma_wave.py `interfere` exactly (the differential bridge
   proofs/wave_bridge_check.py checks this claim against the live oracle).
   Theorems:
     * `interfere_valid`     — range closure: valid in ⇒ valid out (the §3
                               width guarantee behind the int64 port note)
     * `zero_amp_cascade`    — Book II §6.2 "zero-amplitude cascade is a
                               theorem": a silent operand silences the result
     * `left_dominance_ph`   — §5.2: the output phase is the left operand's
     * `crystallization`     — §5.1 Resonance Identity: the unique non-zero
                               fixed point of self-interference is
                               {am = 65535, en = −32768} (phase free)
     * `fold_not_associative`— the ADR-006 fold killer as a checked witness
                               (FV-FOLD-UNSOUND operands)
     * `not_commutative`     — Law of Left Dominance has algebraic teeth

   LUT_COS is imported as generated data (proofs/LutData.lean); its
   generator inherits the Book II §4 SHA-256 arbiter fail-fast. -/
import LutData

namespace WaveAlgebra

/-- Book II §3: round-half-AWAY-FROM-ZERO, divisor strictly positive. -/
def divRoundHalfUp (n : Int) (d : Nat) : Int :=
  let a := n.natAbs
  let q : Nat := a / d + (if d ≤ 2 * (a % d) then 1 else 0)
  if n < 0 then -(q : Int) else (q : Int)

def clampI16 (x : Int) : Int := max (-32768) (min 32767 x)

structure Wave where
  ph : Int
  am : Int
  en : Int
deriving Repr, DecidableEq

def Valid (w : Wave) : Prop :=
  0 ≤ w.ph ∧ w.ph < 65536 ∧ 0 ≤ w.am ∧ w.am ≤ 65535 ∧
  -32768 ≤ w.en ∧ w.en ≤ 32767

instance : DecidablePred Valid := fun w => by unfold Valid; infer_instance

def lut (delta : Nat) : Int := lutCos[delta]!

/-- Book II §5 with the v0.5 entropy–coherence coupling. -/
def interfere (w1 w2 : Wave) : Wave :=
  let d32 := (w1.ph - w2.ph).natAbs
  let delta := min d32 (65536 - d32)
  let r := lut delta
  let deltaEn := divRoundHalfUp (-r) 128
  let newEn := clampI16 (divRoundHalfUp (w1.en + w2.en) 2 + deltaEn)
  let ampFactor := divRoundHalfUp ((r + 32767) * 65535) 65534
  let prod01 := divRoundHalfUp (w1.am * w2.am) 65535
  let newAm := divRoundHalfUp (prod01 * ampFactor) 65535
  ⟨w1.ph.emod 65536, newAm, newEn⟩

/- ---------- LUT facts (decided over the generated data) ---------- -/

theorem lut_size : lutCos.size = 32769 := by native_decide

theorem lut_range : ∀ d : Nat, d < 32769 → -32767 ≤ lut d ∧ lut d ≤ 32767 := by
  native_decide

theorem lut_zero : lut 0 = 32767 := by native_decide

/- ---------- divRoundHalfUp bounds ---------- -/

theorem dr_nonneg (n : Int) (d : Nat) (hn : 0 ≤ n) :
    0 ≤ divRoundHalfUp n d := by
  unfold divRoundHalfUp
  simp only [if_neg (by omega : ¬ n < 0)]
  exact Int.natCast_nonneg _

theorem dr_le_65535 (n : Int) (hn : 0 ≤ n) (h : n ≤ 65535 * 65535) :
    divRoundHalfUp n 65535 ≤ 65535 := by
  simp only [divRoundHalfUp]
  split <;> split <;> omega

theorem dr_le_65534 (n : Int) (hn : 0 ≤ n) (h : n ≤ 65534 * 65535) :
    divRoundHalfUp n 65534 ≤ 65535 := by
  simp only [divRoundHalfUp]
  split <;> split <;> omega

/-- exact multiples of 65535 divide back exactly (no half to round) -/
theorem dr_cancel_65535 (x : Int) (hx : 0 ≤ x) :
    divRoundHalfUp (x * 65535) 65535 = x := by
  simp only [divRoundHalfUp]
  split <;> split <;> omega

/-- averaging a doubled value is the identity -/
theorem dr_double (e : Int) : divRoundHalfUp (e + e) 2 = e := by
  simp only [divRoundHalfUp]
  split <;> split <;> omega

theorem clamp_range (x : Int) : -32768 ≤ clampI16 x ∧ clampI16 x ≤ 32767 := by
  simp only [clampI16]
  omega

/-- both `prod01` and `newAm` in `interfere` are 0.16 products of 0.16 values -/
theorem prod01_bounds (x y : Int) (hx : 0 ≤ x) (hx' : x ≤ 65535)
    (hy : 0 ≤ y) (hy' : y ≤ 65535) :
    0 ≤ divRoundHalfUp (x * y) 65535 ∧ divRoundHalfUp (x * y) 65535 ≤ 65535 := by
  have h0 : 0 ≤ x * y := Int.mul_nonneg hx hy
  have hb : x * y ≤ 65535 * y := Int.mul_le_mul_of_nonneg_right hx' hy
  exact ⟨dr_nonneg _ _ h0, dr_le_65535 _ h0 (by omega)⟩

/-- `ampFactor` bounds from the LUT range -/
theorem af_bounds (r : Int) (h1 : -32767 ≤ r) (h2 : r ≤ 32767) :
    0 ≤ divRoundHalfUp ((r + 32767) * 65535) 65534 ∧
      divRoundHalfUp ((r + 32767) * 65535) 65534 ≤ 65535 :=
  ⟨dr_nonneg _ _ (by omega), dr_le_65534 _ (by omega) (by omega)⟩

/-- the amplitude fixed-point scan behind the Resonance Identity:
    a² / 65535 (rounded) = a on [0, 65535] exactly at 0 and 65535 -/
theorem am_fixed_scan : ∀ a : Nat, a < 65536 →
    (divRoundHalfUp ((a : Int) * a) 65535 = a ↔ (a = 0 ∨ a = 65535)) := by
  native_decide

/- ---------- zero-amplitude cascade (Book II §6.2) ---------- -/

theorem zero_amp_cascade (w1 w2 : Wave) (h : w1.am = 0 ∨ w2.am = 0) :
    (interfere w1 w2).am = 0 := by
  have hprod : w1.am * w2.am = 0 := by rcases h with h | h <;> simp [h]
  have hz : divRoundHalfUp (0 : Int) 65535 = 0 := by native_decide
  simp only [interfere]
  rw [hprod, hz, Int.zero_mul, hz]

/- ---------- Left Dominance ---------- -/

theorem left_dominance_ph (w1 w2 : Wave) (h : Valid w1) :
    (interfere w1 w2).ph = w1.ph := by
  simp only [interfere]
  exact Int.emod_eq_of_lt h.1 h.2.1

/- ---------- range closure ---------- -/

theorem interfere_valid (w1 w2 : Wave) (h1 : Valid w1) (h2 : Valid w2) :
    Valid (interfere w1 w2) := by
  have h1' : 0 ≤ w1.ph ∧ w1.ph < 65536 ∧ 0 ≤ w1.am ∧ w1.am ≤ 65535 ∧
      -32768 ≤ w1.en ∧ w1.en ≤ 32767 := h1
  have h2' : 0 ≤ w2.ph ∧ w2.ph < 65536 ∧ 0 ≤ w2.am ∧ w2.am ≤ 65535 ∧
      -32768 ≤ w2.en ∧ w2.en ≤ 32767 := h2
  obtain ⟨hp1, hp1', ha1, ha1', he1, he1'⟩ := h1'
  obtain ⟨hp2, hp2', ha2, ha2', he2, he2'⟩ := h2'
  have hr := lut_range
    (min (w1.ph - w2.ph).natAbs (65536 - (w1.ph - w2.ph).natAbs)) (by omega)
  have haf := af_bounds _ hr.1 hr.2
  have hp01 := prod01_bounds w1.am w2.am ha1 ha1' ha2 ha2'
  have hnew := prod01_bounds _ _ hp01.1 hp01.2 haf.1 haf.2
  simp only [interfere, Valid]
  exact ⟨Int.emod_nonneg _ (by decide), Int.emod_lt_of_pos _ (by decide),
    hnew.1, hnew.2, (clamp_range _).1, (clamp_range _).2⟩

/- ---------- crystallization (Book II §5.1, Resonance Identity) ---------- -/

theorem crystallization (w : Wave) (hv : Valid w) (hnz : w.am ≠ 0) :
    interfere w w = w ↔ (w.am = 65535 ∧ w.en = -32768) := by
  obtain ⟨ph, am, en⟩ := w
  have hv' : 0 ≤ ph ∧ ph < 65536 ∧ 0 ≤ am ∧ am ≤ 65535 ∧
      -32768 ≤ en ∧ en ≤ 32767 := hv
  have hnz' : am ≠ 0 := hnz
  obtain ⟨hp, hp', ha, ha', he, he'⟩ := hv'
  show interfere ⟨ph, am, en⟩ ⟨ph, am, en⟩ = ⟨ph, am, en⟩ ↔
    (am = 65535 ∧ en = -32768)
  simp only [interfere, Int.sub_self, Int.natAbs_zero, Nat.sub_zero, Nat.zero_min]
  rw [lut_zero,
      show divRoundHalfUp (-(32767 : Int)) 128 = -256 from by native_decide,
      show divRoundHalfUp (((32767 : Int) + 32767) * 65535) 65534 = 65535 from by
        native_decide,
      dr_double,
      dr_cancel_65535 _ (dr_nonneg _ _ (Int.mul_nonneg ha ha)),
      Wave.mk.injEq]
  have hscan := am_fixed_scan am.toNat (by omega)
  have hcast : ((am.toNat : Nat) : Int) = am := by omega
  rw [hcast] at hscan
  constructor
  · intro hE
    obtain ⟨hE1, hE2, hE3⟩ := hE
    have h4 := hscan.mp hE2
    simp only [clampI16] at hE3
    exact ⟨by omega, by omega⟩
  · intro hE
    obtain ⟨hE1, hE2⟩ := hE
    refine ⟨Int.emod_eq_of_lt hp hp', hscan.mpr (Or.inr (by omega)), ?_⟩
    simp only [clampI16]
    omega

/- ---------- checked witnesses: fold unsoundness & non-commutativity ---- -/

/-- ADR-006 FV-FOLD-UNSOUND: interfere is not associative (left fold gives
    am = 16384, right fold gives am = 32768 on these operands). -/
theorem fold_not_associative :
    interfere (interfere ⟨0, 65535, 0⟩ ⟨16384, 65535, 0⟩) ⟨16384, 65535, 0⟩ ≠
      interfere ⟨0, 65535, 0⟩ (interfere ⟨16384, 65535, 0⟩ ⟨16384, 65535, 0⟩) := by
  native_decide

/-- Law of Left Dominance has algebraic teeth: interfere is not commutative. -/
theorem not_commutative :
    ∃ w1 w2 : Wave, interfere w1 w2 ≠ interfere w2 w1 :=
  ⟨⟨0, 65535, 0⟩, ⟨16384, 65535, 0⟩, by native_decide⟩

end WaveAlgebra
