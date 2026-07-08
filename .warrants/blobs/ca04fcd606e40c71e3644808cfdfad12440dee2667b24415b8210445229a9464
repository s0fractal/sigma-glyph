/- Book I byte-level machine correspondence, mechanized (Lean 4 core).

   Models §1.1/§2/§4.1: SigmaNodeV2 canonical serialization
   `[Op:1][Flags:1][Atom?:32][Left?:32][Right?:32]` with the exact
   normative flags per opcode, deserialization/validation, and NodeHash =
   SHA-256(CanonicalBytes) (proofs/Sha256.lean). The differential bridge
   proofs/byte_bridge_check.py ties this model to the live oracle: every
   CAS key of the conformance suite is recomputed by the executed Lean
   pipeline, and validation verdicts agree on adversarial mutations.

   Theorems:
     * serialize_injective  — distinct well-formed nodes never share
                              canonical bytes: identity is injective up to
                              SHA-256 (the hash layer itself rides the
                              CP-24 collision assumption, stated, not
                              provable)
     * deser_serialize      — round-trip: parsing canonical bytes yields
                              the node back
     * serialize_deser      — canonicity: a valid buffer IS the
                              serialization of its parse (no second byte
                              form for any node)
     * deser_wf             — validation only ever yields well-formed nodes
     * valid_lengths        — §4.1 rule 3: valid buffers are 34 or 66 bytes
     * reserved_opcode_invalid — §1.2: opcode 0x03 (and every opcode
                              outside the table) never parses
     * lit_bytes_never_app / glyph-recognition disjointness — the byte-0
              discrimination behind glyph_eq's O(1) redex recognition
     * genesis pins         — H(I), H(K), H(S) (TV-1), FALSE_H (§5.2 "FALSE
              is a theorem"), the Canonical Invalid Object bytes and hash —
              all recomputed end-to-end (serialize ∘ sha256) and pinned to
              the spec constants -/
import Sha256

namespace MachineBytes

abbrev Bytes := List UInt8

inductive Node where
  | lit (atom : Bytes)
  | ref (target : Bytes)
  | app (left right : Bytes)
  | dis (reason : Bytes)
deriving Repr, DecidableEq

/-- §4.1 field discipline: every hash field is exactly 32 bytes. -/
def Wf : Node → Prop
  | .lit a => a.length = 32
  | .ref t => t.length = 32
  | .app l r => l.length = 32 ∧ r.length = 32
  | .dis r => r.length = 32

/-- §2 canonical layout with the §1.1 normative flags
    (LITERAL 0x00/F_ATOM, REF 0x01/F_ATOM, APPLY 0x02/F_LEFT|F_RIGHT,
    DISSONANCE 0xFF/F_ATOM). -/
def serialize : Node → Bytes
  | .lit a   => 0x00 :: 0x01 :: a
  | .ref t   => 0x01 :: 0x01 :: t
  | .app l r => 0x02 :: 0x06 :: (l ++ r)
  | .dis r   => 0xFF :: 0x01 :: r

/-- §4.1 validation + parse. The accepted set is exactly: known opcode,
    flags equal to the opcode's normative value (which also forces
    `flags & ~0x07 = 0`), length equal to `2 + 32·popcount(flags)`. -/
def deserialize : Bytes → Option Node
  | 0x00 :: 0x01 :: rest =>
      if rest.length = 32 then some (.lit rest) else none
  | 0x01 :: 0x01 :: rest =>
      if rest.length = 32 then some (.ref rest) else none
  | 0x02 :: 0x06 :: rest =>
      if rest.length = 64 then some (.app (rest.take 32) (rest.drop 32))
      else none
  | 0xFF :: 0x01 :: rest =>
      if rest.length = 32 then some (.dis rest) else none
  | _ => none

def nodeHash (n : Node) : Bytes := Sha256.sha256 (serialize n)

/- ---------- structural theorems ---------- -/

/-- Length-equal prefixes of equal appends are equal (with their suffixes). -/
theorem append_inj' {α : Type} {l1 r1 l2 r2 : List α}
    (h : l1 ++ r1 = l2 ++ r2) (hl : l1.length = l2.length) :
    l1 = l2 ∧ r1 = r2 := by
  induction l1 generalizing l2 with
  | nil =>
    cases l2 with
    | nil => exact ⟨rfl, h⟩
    | cons y ys => simp at hl
  | cons x xs ih =>
    cases l2 with
    | nil => simp at hl
    | cons y ys =>
      simp only [List.cons_append, List.cons.injEq] at h
      simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
      obtain ⟨hxy, h'⟩ := h
      obtain ⟨h1, h2⟩ := ih h' hl
      exact ⟨by rw [hxy, h1], h2⟩

/-- Taking exactly the length of the left summand recovers it. -/
theorem take_length_append {α : Type} (l r : List α) :
    (l ++ r).take l.length = l := by
  induction l with
  | nil => simp
  | cons x xs ih => simp [ih]

/-- Dropping exactly the length of the left summand recovers the right. -/
theorem drop_length_append {α : Type} (l r : List α) :
    (l ++ r).drop l.length = r := by
  induction l with
  | nil => simp
  | cons x xs ih => simp [ih]

theorem serialize_injective (n1 n2 : Node) (h1 : Wf n1) (h2 : Wf n2)
    (h : serialize n1 = serialize n2) : n1 = n2 := by
  cases n1 <;> cases n2 <;>
    simp_all only [serialize, Wf, List.cons.injEq, Node.app.injEq] <;>
    first
    | (exact absurd h.1 (by decide))
    | (obtain ⟨-, -, happ⟩ := h
       exact append_inj' happ (h1.1.trans h2.1.symm))
    | exact h.2.2

theorem deser_serialize (n : Node) (h : Wf n) :
    deserialize (serialize n) = some n := by
  cases n with
  | lit a =>
    have ha : a.length = 32 := h
    simp [serialize, deserialize, ha]
  | ref t =>
    have ht : t.length = 32 := h
    simp [serialize, deserialize, ht]
  | app l r =>
    have hl : l.length = 32 := h.1
    have hr : r.length = 32 := h.2
    have ht : (l ++ r).take 32 = l := by
      rw [show (32 : Nat) = l.length from hl.symm]
      exact take_length_append l r
    have hd : (l ++ r).drop 32 = r := by
      rw [show (32 : Nat) = l.length from hl.symm]
      exact drop_length_append l r
    simp [serialize, deserialize, hl, hr, ht, hd]
  | dis r =>
    have hr : r.length = 32 := h
    simp [serialize, deserialize, hr]

theorem serialize_deser (b : Bytes) (n : Node)
    (h : deserialize b = some n) : serialize n = b := by
  unfold deserialize at h
  split at h
  · split at h
    · injection h with h'; subst h'; rfl
    · simp at h
  · split at h
    · injection h with h'; subst h'; rfl
    · simp at h
  · split at h
    · injection h with h'
      subst h'
      simp [serialize, List.take_append_drop]
    · simp at h
  · split at h
    · injection h with h'; subst h'; rfl
    · simp at h
  · simp at h

theorem deser_wf (b : Bytes) (n : Node) (h : deserialize b = some n) :
    Wf n := by
  unfold deserialize at h
  split at h
  · split at h
    · rename_i hlen
      injection h with h'; subst h'; exact hlen
    · simp at h
  · split at h
    · rename_i hlen
      injection h with h'; subst h'; exact hlen
    · simp at h
  · split at h
    · injection h with h'
      subst h'
      constructor
      · rw [List.length_take]; omega
      · rw [List.length_drop]; omega
    · simp at h
  · split at h
    · rename_i hlen
      injection h with h'; subst h'; exact hlen
    · simp at h
  · simp at h

theorem valid_lengths (b : Bytes) (n : Node) (h : deserialize b = some n) :
    b.length = 34 ∨ b.length = 66 := by
  unfold deserialize at h
  split at h
  · split at h
    · simp only [List.length_cons]
      omega
    · simp at h
  · split at h
    · simp only [List.length_cons]
      omega
    · simp at h
  · split at h
    · simp only [List.length_cons]
      omega
    · simp at h
  · split at h
    · simp only [List.length_cons]
      omega
    · simp at h
  · simp at h

theorem reserved_opcode_invalid (rest : Bytes) :
    deserialize (0x03 :: rest) = none := by
  unfold deserialize
  split <;> first
    | rfl
    | (rename_i heq
       rw [List.cons.injEq] at heq
       exact absurd heq.1 (by decide))

/-- byte-0 discrimination: a LITERAL's canonical bytes never coincide with
    an APPLY/REF/DISSONANCE node's — the provable layer under glyph_eq's
    O(1) redex recognition (the hash layer adds only CP-24). -/
theorem lit_bytes_disjoint (a : Bytes) (n : Node)
    (hk : ∀ x, n ≠ .lit x) : serialize (.lit a) ≠ serialize n := by
  cases n with
  | lit x => exact absurd rfl (hk x)
  | ref t =>
    intro h
    rw [serialize, serialize, List.cons.injEq] at h
    exact absurd h.1 (by decide)
  | app l r =>
    intro h
    rw [serialize, serialize, List.cons.injEq] at h
    exact absurd h.1 (by decide)
  | dis r =>
    intro h
    rw [serialize, serialize, List.cons.injEq] at h
    exact absurd h.1 (by decide)

/- ---------- genesis pins (end-to-end: serialize ∘ SHA-256) ---------- -/

set_option linter.deprecated false in
def hexOf (b : Bytes) : String := String.join (b.map (fun u =>
  let s := Nat.toDigits 16 u.toNat
  (if s.length = 1 then "0" else "") ++ String.mk s))

def hIT : Bytes := Sha256.sha256 ("I".toUTF8.toList)
def hKT : Bytes := Sha256.sha256 ("K".toUTF8.toList)
def hST : Bytes := Sha256.sha256 ("S".toUTF8.toList)

/-- TV-1: the three intrinsic axiom hashes (Book I §5.1). -/
theorem genesis_I :
    hexOf (nodeHash (.lit hIT)) =
    "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162" := by
  native_decide

theorem genesis_K :
    hexOf (nodeHash (.lit hKT)) =
    "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c" := by
  native_decide

theorem genesis_S :
    hexOf (nodeHash (.lit hST)) =
    "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6" := by
  native_decide

/-- §5.2 "FALSE is a theorem": APPLY(⟨K⟩, ⟨I⟩), constructible without a
    store — its identity now recomputed inside the proof assistant. -/
theorem false_is_a_theorem :
    hexOf (nodeHash (.app (nodeHash (.lit hKT)) (nodeHash (.lit hIT)))) =
    "65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098" := by
  native_decide

/-- §4.2 Canonical Invalid Object: DISSONANCE(SHA-256("Invalid Object")). -/
theorem invalid_object_pins :
    hexOf (nodeHash (.dis (Sha256.sha256 ("Invalid Object".toUTF8.toList)))) =
    "af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507" := by
  native_decide

end MachineBytes
