<!-- produced via tools/or_review.py | model: deepseek/deepseek-v4-pro | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-deepseek-adr45-gate.md.pass1 -->

# Review: ADR-004 and ADR-005 Gate Review

## Verdict

**ADR‑004** — **Adopt Option 2** (blob validation outside `eval()`). The blob is not part of the hash‑thunk machine’s deterministic state space; forcing it into `eval()` would break content‑addressed consensus. Paragraph 2 of Book I §1.1 is a contradiction of Paragraph 1 and must be removed. The existing oracle (`EV‑LIT‑FORCE`) and vectors already implement the correct rule, so no new vector is required. The recommended replacement prose given below closes the gap without altering observed behaviour.

**ADR‑005** — **Adopt R1** (field‑level pin semantics) along with a base‑case rule for unpinned LITERALs and a small set of conformance vectors that cover the derived FALSE wave, Ph‑only pin derivation, and the iterated decay chain. R2 would inject unmotivated defaults that conflict with the spec’s “Pin > Derived” framework; R1 is the conservative, internally consistent path.

Both decisions are fully compatible with the v0.5 oracle and the pinned lazy‑edges / size‑priced settlements.

---

## ADR‑004: LITERAL blob inside or outside `eval()`?

### (a) Verification of underlying claims

**Claim 1 – Book I §1.1 self‑contradiction**  
The two adjacent paragraphs in `spec/book‑1‑truth.md` §1.1 are:

1. “Отримання та валідація blob … — контракт сховища **поза цією Книгою**.”  
2. “Нормативна поведінка `resolve(h)` для LITERAL: fetch blob, валідувати `SHA‑256(blob) == atom`, і якщо валідація невдала — матеріалізувати Canonical Invalid Object.”

These assign opposite scopes to blob validation. The contradiction is direct, not a matter of interpretation. **P1** (spec is silent where it appears to speak).

**Claim 2 – oracle blob‑channel absence**  
The warrant store verification transcript confirms that the reference oracle (`impl/sigma_glyph.py`) contains only a node‑CAS and no BlobStore. The vector `EV‑LIT‑FORCE` forces a LITERAL to normal form in 1 ATP with no blob present. The maintainer’s reproduction confirmed that `eval(LITERAL(sha("dummy blob")))` yields normal form. No blob‑related code path exists. Claim verified.

**Claim 3 – `EV‑LIT‑FORCE` is interim law**  
Book I §7: “при розбіжності з прозою виграє оракул `impl/sigma_glyph.py`.” Since the prose contradicts itself, the oracle’s behaviour (no blob dependency) is currently normative. Claim verified.

### (b) Decision criterion: consensus scenario where identical node‑CAS forces agreement on a blob‑dependent outcome

The ADR asks: *name a consensus scenario where identical node‑CAS forces agreement on a blob‑dependent outcome, or state none exists.*

**Answer: None exists.**  

Two honest nodes with identical node‑CAS share the same set of canonical SigmaNodeV2 bytes, keyed by NodeHash. The `eval()` machine’s transitions depend only on:

- the current term (hash‑thunks and materialized nodes),
- the ATP budget,
- the mapping NodeHash → canonical bytes (the node‑CAS).

A LITERAL node’s canonical bytes contain only the operator, flags, and a 32‑byte `atom` (SHA‑256 of the user blob) — never the blob itself. No reduction rule inspects the blob content; `resolve(h)` for a LITERAL fetches only the node bytes. Thus, for any two nodes with identical node‑CAS, `eval(term_hash, budget)` yields the same result regardless of whether their blob storage differs. Blob‑CAS state is external to the deterministic closure of `eval()`.

Therefore, no consensus scenario can force a blob‑dependent agreement. Option 1 (blob validation inside `eval()`) would introduce exactly such a divergence surface: two honest nodes with the same node‑CAS but different blob possession could produce different canonical hashes, violating content‑addressed determinism.

### (c) Standing positions

- **Codex** prefers Option 1, preserving the v0.4.2 settlement text that demanded on‑demand blob validation.
- **Kimi** argues Option 2 on the basis that `eval()`’s transitive closure never touches the blob and that Option 1 breaks consensus. Analysis is correct.
- **Maintainer** leans Option 2, noting that a mismatched blob cannot exist under its own atom (the storage key is `SHA‑256(blob)`), and that canonical failures ≠ local resource faults already forbids canonizing blob absence.
- **My assessment**: Option 2 is architecturally required. Option 1 would make `eval()` dependent on blob‑CAS, contradict the v0.5 hash‑leaf model, and require a new conformance‑vector format. It would also resurrect the “canonical Invalid Object for blob mismatch” path that §3.5 closed.

### (d) Verdict: Adopt Option 2

**Normative text replacement for Book I §1.1** (delete the two contradictory paragraphs, replace with):

```markdown
**LITERAL — інертний commitment.** Канонічний вузол містить digest, не blob. Для редукції blob не потрібен ніколи: LITERAL — нормальна форма, комбінатори розпізнаються за NodeHash (§3.2). Node‑storage зберігає лише канонічні байти SigmaNodeV2; отримання та валідація вмісту blob (`SHA‑256(blob) == atom` MUST) — зовнішній контракт сховища поза межами цієї Книги. `resolve(h)` для LITERAL не вимагає blob; матеріалізація завжди успішна (1 ATP), поки вузол десеріалізується коректно за §4.1. Жодна відмова blob‑рівня не впливає на результат `eval()`.
```

**Conformance vector:** No new vector needed. `EV‑LIT‑FORCE` already pins the behaviour. The delete of the second paragraph aligns the prose with the oracle. A brief comment in `vectors.json` noting the scope clarification suffices.

---

## ADR‑005: Wave totality — partial pins, base‑case, iteration

### (a) Verification of underlying claims

**Claim 1: `interfere(K, I) → am=0` and ancestor cascade**  
Compute using Book II §5 rules with exact integer arithmetic.

Trinity pins:  
`K = {ph=32768, am=65535, en=-32768}`  
`I = {ph=0, am=65535, en=-32768}`  

- Phase difference: `|32768−0| = 32768`. `delta = min(32768, 65536−32768) = 32768`.  
- `r = LUT_COS[32768] = −32767` (anchored value).  
- `amp_factor = div_round_half_up( (r + 32767) * 65535, 65534 )`.  
  `r+32767 = 0`, so `amp_factor = 0`.  
- `prod01 = div_round_half_up(65535 * 65535, 65535)`.  
  `65535² = 4,294,836,225`. Dividing by `65535` gives `65535` exact (no remainder). So `prod01 = 65535`.  
- `new_am = div_round_half_up(prod01 * amp_factor, 65535) = div_round_half_up(65535*0, 65535) = 0`.  

Thus derived FALSE amplitude is **0**. Because `prod01` multiplies child amplitudes, any child with `am=0` forces the parent’s `new_am=0`. Induction shows that **every ancestor of an `am=0` node inherits amplitude zero** — a silent wave. Verified.

**Claim 2: Ph‑only pins in §6.2–6.4 have undefined field semantics**  
§6.2 (Grand Cross) lists FALSE with `Ph=49152` only, while §6.1 (Trinity) gives full vectors. §2 describes “Pin > Derived” but does not specify whether a pin that omits `Am`/`En` overrides the entire vector (making those fields undefined) or only overrides the listed columns and leaves the rest to derivation. For `FALSE ≡ APPLY(K, I)`, derivation yields `am=0`; an implementer could instead assign a default maximum amplitude. The spec is silent, so a conforming annotator cannot determine the wave of any Pantheon entity. **Gap is real, P1.** Verified.

**Claim 3: no base‑case wave for unpinned LITERALs**  
The spec defines wave for `APPLY` nodes via the Derived rule, and provides explicit pins for select glyphs. For an arbitrary unpinned LITERAL (e.g., a user‑stored blob), there is no rule. The natural inference is that such nodes have **no wave at all** — wave is a partial function. But the spec never states this, leaving implementers to guess whether an absent wave means “silence” or “error”. **Gap is real.** Verified.

**Claim 4: iterated decay chain 49151 → 36863 → 20735 → 6560 → 657 → 7 → 0 is unpinned**  
Starting with `am=49151` (75%‑ish of max) and applying self‑interference via the Resonance Identity (`amp_factor=65535`, `prod01=am²/65535` rounded half‑up). Arithmetic (all exact integers):

- Step 1: `49151² = 2,415,820,801`. Divide by 65535: `65535 * 36863 = 2,415,816,705` (remainder 4096). Since `2×4096 = 8192 < 65535`, round down → **36863**.  
- Step 2: `36863² = 1,358,880,769`. `65535 * 20735 = 1,358,868,225` (remainder 12,544). `2×12544 = 25088 < 65535`, round down → **20735**.  
- Step 3: `20735² = 429,940,225`. `65535 * 6560 = 429,909,600` (remainder 30,625). `2×30625 = 61250 < 65535`, round down → **6560**.  
- Step 4: `6560² = 43,033,600`. `65535 * 656 = 42,990,960` (remainder 42,640). `2×42640 = 85280 ≥ 65535`, round up → **657**.  
- Step 5: `657² = 431,649`. `65535 * 6 = 393,210` (remainder 38,439). `2×38439 = 76878 ≥ 65535`, round up → **7**.  
- Step 6: `7² = 49`. `49/65535` round half‑up: remainder 49, `2×49=98 < 65535`, so quotient 0 → **0**.

The sequence matches the ADR’s list. None of the 17 existing wave vectors test iterative self‑interference; the chain is unpinned. **Gap confirmed.**

### (b) Decision criterion: a use where a FALSE‑containing term’s wave must be non‑silent

The ADR asks: *name a use where a FALSE‑containing term’s wave must be non‑silent, or state none exists.*

**Answer: None exists today.**  

The wave layer is currently scoped for navigation, not consensus. Amplitude zero for a term is a well‑defined signal: the term carries no weight in mass aggregations, but its pinned phase (e.g., FALSE’s `ph=49152`) remains visible. This is consistent with Book II’s design principle that “Wave ∉ hash — це предмет федеративного узгодження”. No existing protocol (federation/gossip is planned for v0.6+) requires a non‑zero amplitude for FALSE. If a future protocol needs it, it can define a different base amplitude, but that would be a new specification. For now, the silent cascade is a derived property of the interfere function, not a bug.

Thus, no use case demands non‑silent FALSE.

### (c) Standing positions: R1 (field‑level pins) vs R2 (full‑vector defaults)

- **Kimi** flagged the partial‑pin ambiguity but did not prescribe R1/R2.
- **Maintainer** is undecided.
- **My recommendation: R1.**

  R2 (give every Ph‑only entity default `Am=65535`, `En=−32768`) would make FALSE carry maximal amplitude, contradicting the Derived rule and the orthogonal relationship between K and I. It would also create an arbitrary asymmetry: why are Trinity entities pinned with exact amplitudes but others get MAX? The existing spec statement that “Phase is not an identifier” and the density‑cluster reuse (SATOSHI/TESLA share phase 8192) are consistent with phase‑only pins being sufficient for navigation; amplitude and entropy then reflect actual wave heritage. R1 simply states that a pin overrides only the fields it explicitly lists; unlisted fields follow the Derived rule if the node is an APPLY, or are absent (no wave) otherwise. This is the minimal, conservative interpretation that preserves the existing framing.

  R1 also avoids introducing new hidden complexity. It keeps FALSE’s amplitude at 0 and the cascade intact, which is exactly what the interference function computes. If a future use needs non‑silent FALSE, a full‑vector pin can be added to the table without breaking any existing wave vectors.

### (d) Verdict: Adopt R1 + base‑case clarification + new vectors

**Normative text proposals**

1. **Amend Book II §2 (“Пріоритет анотацій”) to define field‑level pin semantics**  
   ```markdown
   Pin перекриває Derived **поле‑за‑полем**: для вузла з явною анотацією (Pin) кожне поле (ph, am, en) береться з Pin, якщо воно вказане; інакше — обчислюється за Derived, якщо це APPLY‑вузол. Якщо Derived не застосовне (не‑APPLY, або операнди без хвилі), анотація відсутня — `wave()` є частковою функцією, визначеною лише для носіїв анотацій. Відсутність хвилі дозволена; `interfere` з відсутнім операндом означає відсутню результуючу хвилю.
   ```

2. **In §6.2–6.4, for each Ph‑only entity, add a derived‑vector note and a normative row for FALSE**  
   ```markdown
   | FALSE ≡ APPLY(K,I) | 49152 | 0 | −32512 | `65cd957f…` | (виведено: Am=0 через ортогональність K/I, En=−32512)
   ```
   (En derivation: `avg_en = (−32768 + −32768)/2 = −32768`; `delta_en = div_round_half_up(−(−32767),128) = 256`; sum = −32512, clamped to −32512.)  
   For other Ph‑only entities (VOID/PAIR, Pantheon glyphs) state that Am/En are either absent (no child waves) or derived in a future release.

3. **Base‑case rule (new §2.1)**  
   ```text
   Для вузлів, які не є APPLY і не мають Pin, хвиля **відсутня**. Це включає всі непіновані LITERAL. Відсутність хвилі не впливає на консенсус Книги I і не обробляється `interfere` — спроба застосувати `interfere` до відсутнього операнда призводить до відсутньої результуючої хвилі.
   ```

**Conformance vector additions to `wave_vectors.json`**

- `WV‑FALSE‑DERIVED`: Verify that `wave(APPLY(K, I))` with the Ph pin (49152) yields `{ph=49152, am=0, en=−32512}`.  
- `WV‑PH‑ONLY‑DEFAULT`: (Optional) Demonstrate that a Ph‑only pin on a non‑APPLY LITERAL yields no wave.  
- `WV‑ITER‑DECAY`: Given initial `am=49151`, compute the full decay chain `[49151, 36863, 20735, 6560, 657, 7, 0]` by repeated self‑interference.

These vectors extend the existing suite without invalidating the 17 existing waveforms. The reference implementation will require a pin‑table layer to honour the Ph override for FALSE; with that layer, `wave(APPLY(K, I))` must produce the tabulated values. The changes are non‑breaking for Book I and only affect Book II’s anchored wave‑vectors file.

---

## Relation to prior reviews

### Agreement

- **Codex** (2026‑07‑06) first identified the LITERAL prose/oracle split and `EV‑LIT‑FORCE`. I confirm that the blob channel is absent and that the prose contradicts itself. Codex’s `EV‑LIT‑FORCE` observation is the anchoring evidence for Option 2.
- **Kimi** (2026‑07‑07) provided the definitive state‑space argument that identical node‑CAS can never force blob‑dependent agreement. That analysis directly answers ADR‑004’s decision criterion and is echoed in my own conclusion. I agree with Kimi’s arithmetic for `interfere(K,I) → am=0` (except the minor `en` slip, corrected by the maintainer), the partial‑pin gap, the missing base case, and the decay chain correctness.
- **Maintainer** (response to Codex) sharpened the self‑contradiction, and (response to Kimi) correctly refuted the “Synthetic Exclusion Lemma” concern. The size‑priced theorem is pinned; I do not re‑litigate it.

### Disagreement

- **Codex’s preference for Option 1** is noted but rejected. Option 1 would break content‑addressed determinism, as I detail in §ADR‑004(b). The hash‑thunk machine’s state‑space topology makes blob‑dependent `eval()` results a P0 consensus bug. The v0.4.2 settlement text cannot be preserved in v0.5 without introducing that bug. Option 2 is the only consensus‑compatible path.
- The **Kimi** review’s framing of iterative decay as contradicting a “crystallization narrative” is a slight misreading; Book II already states that partial commitment decays quadratically and that only the boundary `am=65535` is a fixed point. However, the underlying suite‑gap finding (no iteration vector) stands and is adopted in ADR‑005.

### New relative to prior reviews

- My ADR‑004 verdict explicitly ties the Option 2 normative text to the existing `EV‑LIT‑FORCE` vector, showing that no new vector is needed and that the change is purely prose‑alignment.
- For ADR‑005, I provide the first full R1 normative text and I propose a concrete set of conformance vectors (WV‑FALSE‑DERIVED, WV‑ITER‑DECAY) that pin the emergent behaviours. The maintainer will need to add a pin‑table to the wave oracle, but that is a straightforward extension that preserves all existing vectors.
- I also dot the I’s on FALSE’s `En` value (−32512, not the commonly mentioned −32768), which the maintainer’s response flagged. The normative row I propose includes this derived value, removing ambiguity.

All lazy‑edges and size‑priced points are settled; this review does not challenge them. The ADR‑004 and ADR‑005 resolutions close the spec gaps in a way that is fully backward‑compatible with the v0.5 oracle and vectors.
