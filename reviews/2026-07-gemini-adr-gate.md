# Review: Gemini 3.1 Pro (via agy) v0.5 ADR gate - 2026-07-05

## Verdict

Adopt ADR-002 with the Book II §5.1 Resonance Identity supersession checklist. 
Adopt ADR-001 and ADR-003 jointly strictly under the **Hash-Leaf Size Model** (Option 3 for their composition).

## Verified vectors statement

I ran the required validation scripts on the current v0.4.x suite before reviewing:

```bash
python3 impl/sigma_glyph.py
python3 tests/spec_conformance/run_reference.py
python3 tools/verify_anchors.py
```

Outputs verified exactly as follows:
- `impl/sigma_glyph.py` finished with `ALL PASS`.
- `tests/spec_conformance/run_reference.py` finished with `CONFORMANCE: ALL PASS (39/39)`.
- `tools/verify_anchors.py` finished with `anchors verified`.

## Findings By Severity

### P1 - Option 3 (Hash-Leaf Size Model) is the only mathematically sound composition for ADR-001 and ADR-003

The composition section of ADR-001 lists three options for resolving the conflict between size-priced ATP and lazy spine resolution. Attacking the memory-bound theorem (`size(t_n) - size(t_0) < ATP_spent`) under each:

1. **Strict size-priced R-S (Option 1):** The memory bound holds, but measuring `size(z)` defeats the entire purpose of ADR-003 by forcing the materialization of dead branches. 
2. **Lazy demand-priced R-S (Option 2):** The memory bound is completely broken under tree semantics.
   *Attack Vector:* Let `T` be an already-materialized, extremely large subtree. An attacker triggers `S K K T`, which resolves to `K T (K T)`. Under demand pricing, `cost(R-S)` is a small constant `C`. Because `T` is already materialized, the tree size instantaneously grows by `size(T)` nodes (due to physical duplication in tree semantics). Since `size(T) >> C`, the growth vastly exceeds the ATP spent. The OOM DoS vector is reopened.
3. **Hash-Leaf Size Model (Option 3):** The memory bound is preserved perfectly across the entire reduction graph, while allowing true laziness.
   *Proof:* Redefine `size(t)` strictly as the count of materialized nodes, where any unresolved hash leaf counts as `1`.
   - When R-S duplicates an argument `z`, it pays `1 + size(z)`. If `z` contains an unresolved hash `h`, `h` contributes `1` to the cost, and the tree size grows by exactly `1` node (the copied reference to `h`). `growth < cost` holds globally.
   - When the lazy evaluator demands `h` and resolves it via R-R, the rewrite pays `cost(R-R) = size(resolve(h))`. The tree size increases by `size(resolve(h)) - 1` (replacing the hash leaf of size 1 with the resolved subtree). `growth < cost` holds perfectly.

**Concrete Text Proposal for ADR-001 & ADR-003 Composition:**
Replace the "Composition" sections with:
> **Decision: Hash-Leaf Size Model.** `size(t)` is strictly defined as the count of materialized nodes in the tree, with any unresolved hash leaf counting as size 1. R-S pays `1 + size(z)` immediately without forcing the resolution of hashes inside `z`. When a hash is demanded by the leftmost-outermost search, R-R pays `size(resolve(h))`. This preserves lazy liveness while strictly maintaining the memory-bound theorem.

### P1 - Genesis Constants Must Be Intrinsic (Hash-Thunk Machine)

ADR-003 leaves the genesis constants question open. If genesis constants are not intrinsic, evaluating `REF(K_H)` alone would yield `Unresolved Reference` if the local node happens to lack `K`'s bytes in its store. This is absurd: genesis glyphs are the foundational axioms of the system, and their bytes and semantics are globally known by all conforming implementations.

**Concrete Text Proposal for ADR-003:**
Replace the open question with:
> **Genesis Intrinsic Rule:** Genesis glyphs (I, K, S, FALSE) are intrinsic constants. Implementations MUST NOT produce `Unresolved Reference` for their canonical hashes. Non-genesis hashes MUST resolve in the local store to be reported as a normal form if they appear in the demanded spine.

### P2 - ADR-002's Entropy Crystallization is Physically Sound

ADR-002 breaks Book II's Resonance Identity by causing entropy to drift by -256 per constructive self-application, clamping at -32768. 

I verified this drift by executing:
```bash
python3 -c "
def div_round_half_up(x, d): return (x + (d // 2)) // d
def clamp_i16(x): return max(-32768, min(32767, x))
en = 0
for i in range(5):
    en = clamp_i16(div_round_half_up(en + en, 2) + div_round_half_up(-32767, 128))
    print(en)
"
# Output: -256, -512, -768, -1024, -1280
```

This supersession of the Resonance Identity is not a defect; it is a profound and necessary enhancement. Book II specifies that "information flows toward En<0", but the old math provided no mechanism for this flow. ADR-002 mathematically formalizes "crystallization": perfectly ordered self-resonance cools the wave down to its minimum entropy state (a literal ground state). `{am=65535, en=-32768}` is the correct physical fixed point for a standing wave. 

**Concrete Text Proposal for ADR-002:**
Accept the ADR exactly as written, and apply the Book II §5.1 rewrite checklist provided in the 2026-07 amendment. No damping floor is needed; linear drift to -32768 is functionally equivalent to crystallization and requires no new state parameters.

## Relation to Prior Reviews

- **Agreement with Codex:** I strongly agree with Codex's recommendation on the hash-thunk machine (genesis glyphs must be intrinsic). I also agree that Option 1 and Option 2 for the ADR-001/003 composition conflict are flawed (as verified by my attack on Option 2 above).
- **Novel Contribution & Disagreement:** Prior reviews (including Codex) treated the composition question as unresolved and framed the Hash-Leaf Size Model (Option 3) cautiously, stating it "changes the meaning of tree sizes". I disagree with treating this as a negative or an open problem. I have formally shown that Option 3 is the *only* mathematically sound option that preserves ADR-001's memory bound without destroying ADR-003's liveness. The redefinition of `size(t)` to simply count unresolved hashes as size `1` seamlessly satisfies the `size(t_n) - size(t_0) < ATP_spent` invariant across both R-S duplication and R-R materialization. The conflict is definitively resolved by Option 3.
