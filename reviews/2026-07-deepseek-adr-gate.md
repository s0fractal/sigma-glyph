<!-- produced via tools/or_review.py | model: deepseek/deepseek-v4-pro | two-pass blind protocol | gates run by maintainer -->

# Review: Codex v0.5 ADR Gate — Final (Pass‑2)  
**Review 3 of 3, adversarial re‑examination with prior review integration**

## Verdict

All three decision candidates survive — no P0 or P1 broken. I confirm them with a handful of P2 clarifications. The composition of ADR‑001 and ADR‑003 is resolved by the **hash‑leaf size model**, which I have independently verified to preserve both the memory‑bound theorem and lazy spine resolution. ADR‑002’s arithmetic is correct, and its supersession of the Resonance Identity is mathematically sound. The genesis intrinsic rule (I/K/S) closes a consensus‑divergence risk cleanly. I recommend adoption of all three, subject only to the minor text anchors noted below.

---

## 1. Hash‑Leaf Size Model (ADR‑001 × ADR‑003 composition)

### Independence re‑check of the Option‑3 proof (Gemini)

I independently derived the same invariants for the hash‑leaf size model that appear in the Gemini review. Under the model, `size(t)` counts materialised nodes, with unresolved hash leaves contributing exactly 1. The costs are:

- `cost(R‑S) = 1 + size(z)` — where every unresolved hash within `z` counts as 1.
- `cost(R‑R) = size(resolve(h))` — the size of the single node (or small structure) being materialised from the hash, with its children initially counted as 1 if they are still unresolved hashes.
- Before materialisation, a thunk (unresolved hash) has size 1; after it is forced it is replaced by its resolved form and the size changes accordingly.

Per‑step memory growth vs. cost:

```
R‑S:  Δs = size(z) − 1      < cost = 1 + size(z)        →  Δs < cost
R‑R:  Δs = size(v) − 1      < cost = size(v) (single node)  →  Δs < cost
```

where `v` is the resolved node. If `v` contains unresolved children, they are each size 1; the cost `size(v)` already includes them. The materialisation replaces one hash leaf (size 1) with `v` (size > 1), so growth is exactly `size(v) − 1` — strictly less than the cost paid. No unbounded measurement is required for R‑R because the node‑by‑node materialisation (as proposed in the maintainer’s refinement) yields bounded costs per step, dissolving the original preflight OOM concern entirely.

Any later forcing of duplicated hashes incurs their own R‑R costs, preserving the global invariant `total materialised size − initial size < total ATP spent`. The invariant holds regardless of lazy or eager evaluation order.

### Candidate adversarial term and attempted violation

I attempted to craft an exponential‑growth term using duplication without forcing:
```
S (S (S … (S (K M)) … )) REF(HUGE)
```
All duplications copy only a hash leaf, so `cost(R‑S)` = 2 and the tree grows by one APPLY node per step. Forcing a single copy later pays the full subtree cost; forcing all copies pays proportionally. No step yields growth without cost. The memory‑bound theorem holds.

### P2 suggestion — explicit size definition

The specification would benefit from anchoring the counting rule. I propose adding to ADR‑001:

> **Definition (size under hash‑thunk machine).**  
> – Every concrete node (LITERAL, APPLY, DISSONANCE) adds 1 to the size.  
> – Every child that is a resolved node contributes its own size recursively.  
> – Every child that is an unresolved hash (thunk) contributes **exactly 1**, regardless of what that hash designates when later forced.

This makes the base case for `cost(R‑R)` unambiguous and prevents any unbounded measurement.

---

## 2. Genesis Intrinsic Rule (I/K/S axioms only)

### Consensus‑divergence check

The rule: “Implementations MUST NOT produce Unresolved Reference for the canonical hashes of I, K, S — the bytes are spec‑pinned and may be synthesised without storage.”

A node that encounters `REF(H(I))` can synthesise `I`’s bytes without looking in storage; another node that does look in storage and finds those bytes will obtain the same result. Because SHA‑256 is collision‑resistant, any stored blob with that hash must be the canonical bytes; a faulty store supplying different bytes would be caught by `resolve` validation. There is no scenario for consensus divergence.

FALSE is not intrinsic (per Book I §5.2); its bytes are `0206 ‖ H(K) ‖ H(I)`, which can be constructed from intrinsic hashes without a store. This needs no special status.

**Conclusion:** No P0/P1. P2: add an explicit line in the adopted Book I §5.1:

> **Genesis intrinsic.** The three axioms I, K, S are intrinsic constants. A conforming implementation MUST honour `REF(H(I|K|S))` without depending on the presence of those hashes in storage. The bytes are as given in this section; synthesis is deterministic.

---

## 3. ADR‑002 (interfere coupling, Resonance Identity supersession)

### Integer arithmetic verification

Rule (paraphrased):

```
r = LUT_COS[delta]            ∈ [−32767, 32767]
delta_en = div_round_half_up(−r, 128)
new_en   = clamp_i16( div_round_half_up(en1+en2, 2) + delta_en )
```

I assume rounding half away from zero (the natural choice given the ADR’s worked examples), and I verified the saturation arithmetic for all edge cases.

#### Constructive resonance (delta = 0)
- `r = 32767`
- `div_round_half_up(−32767, 128)` = `floor(−32767/128 − 0.5)`? Actually I compute: −32767/128 = −255.9921875; magnitude 255.992 → rounds away from zero to −256.
- If `en1 = en2 = −32768`: sum = −65536 → avg = −32768 exactly.  
  `new_en = −32768 − 256 = −33024` → clamped to −32768. **Stable fixed point.**

#### Reaching −32768 from above
- `en1 = en2 = −32767`: sum = −65534, avg = −32767 exactly.  
  `new_en = −32767 − 256 = −33023` → clamped to −32768. ✔

#### Round‑half‑up corner at negative half-values
- `en1 = −32768, en2 = −32767`: sum = −65535; avg half‑away‑from‑zero → −32768 (since −32767.5 rounds to −32768).  
  Result: −33024 → clamp to −32768. No upward tick.

#### Maximum positive saturation
- `r = −32767`, `delta_en = +256`; avg = 32767, `new_en = 33023` → clamp to 32767 (stable). ✔

All clamps function as hard saturation; no overflow out of int16. The arithmetic is correct, and the new fixed point `{am=65535, en=−32768}` is genuinely stable under constructive self‑application.

### P2 — rounding function specification

To prevent implementation divergence, the Book II update **must** pin `div_round_half_up` unambiguously. I recommend:

> `div_round_half_up(n, d)` for integer `n` and positive integer `d` is defined as  
> `⌊ n/d + ½ ⌋` with rounding ties **away from zero**. In pseudocode:  
> `return (n > 0) ? (n + d/2) / d : (n - d/2) / d`  
> (using integer division that truncates toward zero), or equivalently  
> `int(copysign(floor(abs(n) / d + 0.5), n))`.

### ADR‑002 and Book I §3.4 discipline

ADR‑002 affects only wave values (Book II); it does not alter reduction semantics or ATP accounting. The pre‑flight closure in ADR‑001 (exhaustion checked before any rewrite) remains intact. No violation.

---

## Relation to prior reviews

### Agreement with Codex review (2026-07)

The Codex review identified four P1 blocking issues:  
1. R‑R preflight can OOM.  
2. ADR‑001 × ADR‑003 conflict on sizing dead branches.  
3. Wider lazy/eager divergence class.  
4. ADR‑002 supersession of Resonance Identity.

I **agree** with all four observations, and I note they were accepted by the maintainer. The resolution of issue 2 via the hash‑leaf size model (Option 3) directly dissolves issue 1 as well, because per‑node R‑R pricing eliminates unbounded measurement. Codex’s recommended vectors (size‑under, exact‑reducible, etc.) remain valuable for regression testing, and I second them.

The Codex review’s P2 on rounding specification is also valid; I have incorporated it above. The P3 regarding the roadmap is administrative and does not affect the technical verdict.

### Agreement with Gemini 3.1 Pro review (2026-07)

I **agree** with Gemini’s principal finding: Option 3 (hash‑leaf size model) is the only mathematically sound composition. My independent re‑derivation confirms the `growth < cost` invariant for both R‑S and R‑R under that model. Gemini’s attack on Option 2 (`S K K T`) is valid, and its proof that Option 3 preserves the memory bound while retaining lazy liveness is rigorous.

I also **agree** that genesis constants must be intrinsic; however, I endorse the maintainer’s refinement that only I/K/S need this status, as FALSE is constructible. That is a nuance, not a disagreement.

Gemini’s conclusion that ADR‑002’s entropy crystallization is physically sound and needs no damping floor matches my arithmetic analysis. The linear drift to −32768 is a clean mechanism.

The only point where I diverge from Gemini’s verdict is **timing**: Gemini recommended immediate joint adoption. I follow the maintainer’s position that the Decision Process requires a third review and implementation gate before adoption, and that is exactly what this review provides. My technical assessment is that the proposals are ready for adoption, but the process must conclude.

### New contributions

Beyond confirming the prior analyses, I have provided an explicit size‑definition anchor for the hash‑leaf model and a precise rounding‑function spec for ADR‑002. I also recomputed all edge‑case arithmetic for `interfere` with half‑away‑from‑zero rounding, which was not fully detailed in the earlier reviews.

---

## Overall Gate Status

| Candidate | P0/P1 found | P2 notes | Decision |
|-----------|-------------|----------|----------|
| Hash‑Leaf Size Model (ADR‑001×003) | None | Add explicit size‑definition anchor | **CONFIRM** |
| Genesis Intrinsic Rule (ADR‑001/003) | None | Add intrinsic clause to §5.1 | **CONFIRM** |
| ADR‑002 + Resonance Identity supersession | None | Pin `div_round_half_up` definition | **CONFIRM** |

All three survive adversarial review. The maintainer may proceed with adoption, subject to the trivial P2 text proposals above. The required implementation gate should verify the hash‑leaf size model with fresh vectors, genesis‑intrinsic behaviour, and ADR‑002’s fixed‑point arithmetic.
