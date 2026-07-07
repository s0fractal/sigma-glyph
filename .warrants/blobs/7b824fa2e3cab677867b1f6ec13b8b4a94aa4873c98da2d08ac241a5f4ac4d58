# Review: Gate Adjudication for ADR-004 and ADR-005

## Verdict

- **P0 — Consensus divergence:** The v0.5.0 executable core as shipped is solid. However, adopting ADR-004 Option 1 would create a P0 divergence surface by bridging off-chain state (blob storage) into the deterministic `eval()` pure function.
- **P1 — Specification underdetermination:** 
  1. **ADR-004:** Book I §1.1 contains a prose contradiction regarding whether `resolve(h)` for a `LITERAL` fetches and validates the blob.
  2. **ADR-005:** Book II lacks definition for partial pins (leaving `Am` and `En` ambiguous for entities like `FALSE`), lacks a wave base case for `LITERAL`s, and lacks an iterated decay vector to pin the exact sequence rounding.
- **P2 — Clarity:** Adopting full-vector defaults for partial pins cleanly eliminates the unpinned cascade.

## Verified-Vectors Statement

I executed the required scripts against the local tree. The verifiable behavior matches the spec entirely:
- `python3 impl/sigma_glyph.py` output: `ALL PASS`
- `python3 tests/spec_conformance/run_reference.py` output: `CONFORMANCE: ALL PASS (46/46)`
- `python3 tools/verify_anchors.py` output: `anchors verified`

## Findings & Adjudication

### 1. ADR-004: LITERAL blob validation scope (P1)

**Claims Verification:** 
I confirmed the contradiction in Book I §1.1 directly: paragraph 1 states "Для редукції blob не потрібен ніколи", while paragraph 2 mandates that `resolve(h)` must "fetch blob, валідувати... матеріалізувати Canonical Invalid Object" on failure. I verified that the reference oracle `impl/sigma_glyph.py` lacks any blob-fetching channel during evaluation, and the `EV-LIT-FORCE` conformance vector evaluates a LITERAL node successfully in 1 ATP without supplying a blob payload.

**Decision Criterion Answer:** 
*Is there ANY consensus scenario where two honest nodes with identical node-CAS must agree on a blob-dependent outcome?*
**None exists.** A `LITERAL` node commits to an `Atom` (the SHA-256 hash of the blob) in the node-CAS. The blob payload resides in a separate layer. Because the transition function over hash-thunks depends strictly on the node bytes (which only contain the `Atom`), making `eval()` behave differently depending on the external blob's presence would fork the consensus of two nodes that have perfectly synchronized node-CAS. 

**Engagement with Standing Positions:** 
I concur with Kimi and the maintainer (Option 2). I disagree with Codex's preference for Option 1, which wrongly prioritizes legacy prose over architectural purity and content-addressed determinism. "Canonical failures ≠ local resource faults" is already settled law.

**Normative Text Proposal (ADR-004):** 
Adopt **Option 2**.
In Book I §1.1, delete paragraph 2 entirely, or replace it with:
> "Нормативна поведінка `eval()` для LITERAL полягає виключно в матеріалізації вузла за його NodeHash (1 ATP). Blob не є частиною вузла. Відсутність або пошкодження blob-даних є локальною подією сховища і MUST NOT змінювати результат `eval()` або генерувати DISSONANCE."

---

### 2. ADR-005: Book II wave totality (P1)

**Claims Verification:** 
- **interfere(K,I) -> am=0:** Confirmed algebraically. The phase difference is 32768, which yields `r = LUT_COS[32768] = -32767`. This makes `amp_factor = 0`, forcing `new_am = 0`.
- **Zero-amplitude cascade:** Because `prod01` multiplies child amplitudes, a `0` amplitude at any node forces its parent `APPLY` to `0`, propagating to the root.
- **Ph-only pins:** Verified. Book II §6.2-6.4 tables list `Ph` coordinates for entities like `FALSE`, `SATOSHI`, and `TESLA`, but omit `Am` and `En`.
- **Base case:** Verified. `wave(LITERAL)` is undefined for unpinned entities.
- **Iterated decay sequence:** Confirmed the arithmetic (49151 -> 36863 -> 20735 -> 6560 -> 657 -> 7 -> 0) utilizing the spec's `div_round_half_up` logic. (e.g. `6560^2 / 65535 = 656.65` rounds up to `657`).

**Decision Criterion Answer:** 
*Name a use where a FALSE-containing term's wave must be non-silent, or state none exists.*
**Any non-trivial functional application.** The combinator `FALSE` (`APPLY(K,I)`) encodes the boolean false logic. If an entire application (e.g. a federated namespace resolver or voting contract) uses boolean conditionals and is compiled to SKI, it will contain `FALSE`. Under R1, the entire application's wave would cascade to `0` amplitude, erasing it from Mass-based routing and Gravity discovery. A simple boolean primitive must not render the overlying structure topologically invisible.

**Engagement with Standing Positions:** 
The maintainer is undecided, and Kimi simply pointed out the unpinned cascade. I strongly advocate for **R2** (full-vector defaults). R1's philosophical elegance ("falsehood has no amplitude") is practically lethal, zeroing out valid compound terms. R2 seals the state space predictably.

**Normative Text Proposal (ADR-005):** 
Adopt **R2** and the **absent base case**.
*For Book II §6:*
> "R2: Будь-яка сутність, що має частковий Pin (наприклад, лише `Ph`), неявно отримує дефолтні значення `{Am: 65535, En: -32768}` для неявно вказаних полів. Цей повний вектор має пріоритет над Derived."

*For Book II §2:*
> "Base case: `wave()` для будь-якого LITERAL, який не має явного Pin у таблицях §6, вважається **absent** (відсутнім). Операція `interfere` з відсутнім операндом також дає відсутню хвилю."

**Conformance-Vector Proposals (`wave_vectors.json`):**
1. **`WV-FALSE-R2-PIN`**: Pin evaluating `FALSE` directly to guarantee `{ph: 49152, am: 65535, en: -32768}` overrides the `am=0` derivation.
2. **`WV-ITERATED-DECAY-6560`**: Pin a step deep in the quadratic decay to catch rounding errors. `w1 = w2 = {ph: 0, am: 6560, en: 0}`, `expected = {ph: 0, am: 657, en: -256}`.
