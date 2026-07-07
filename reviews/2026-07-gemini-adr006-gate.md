# Review: Gemini 3.1 Pro (High) ADR-006 Gate - 2026-07-07

## Verdict

**Adopt F1 (Warrant-carried selection). Reject F2 and F3.**

The proposed F3 architecture commits a category error by applying a non-associative, non-commutative execution-trace algebra (`interfere`) to the problem of subjective consensus. Furthermore, the proposed Sybil resistance mechanism (`ski@v1`-priced amplitude) is structurally flawed and easily bypassed by free-riding. 

## Verified vectors statement

I ran the required validation scripts on the current suite before reviewing:

```bash
python3 impl/sigma_glyph.py
python3 tests/spec_conformance/run_reference.py
python3 tools/verify_anchors.py
```

Outputs verified:
- `sigma_glyph.py`: `ALL PASS`
- `run_reference.py`: `CONFORMANCE: ALL PASS (49/49)`
- `verify_anchors.py`: `anchors verified`

I also wrote and executed a custom test script against `impl/sigma_wave.py` to explicitly test the associativity and commutativity of `interfere()`, confirming it is both non-associative and non-commutative (Left Dominant).

## Review gate asks (rev 1)

### 1. Fold-position grinding under Left Dominance
**Yes, an asserter can choose their fold position and dictate the phase.** 
Under Book II's Law of Left Dominance (`new_ph = w1["ph"]`), the left-most operand in a fold always dictates the resulting phase. If the canonical fold order is hash order, an attacker can simply grind their warrant's hash (e.g., by mutating `subject.note` or adding junk `evidence` hashes) to produce a hash with many leading zeroes. This guarantees their assertion is sorted first, allowing them to dictate the phase of the entire jurisdiction. 

Sorting by `(ph, hash)` prevents arbitrary phase dominance but exposes the deeper algebraic flaw: `interfere()` is **non-associative**. My tests show `interfere(w1, interfere(w2, w3)) != interfere(interfere(w1, w2), w3)`. A sequential fold of non-associative operations has no algebraic meaning for merging independent observations.

### 2. ski@v1-priced amplitude amortization
**It completely fails.** 
Warrant v0.3 `ski@v1` checks are portable and deterministic. If Alice spends the maximum ATP to evaluate a term and binds it to a `ski@v1` check, that check blob is now public. Bob can simply copy Alice's check hash into his own annotation warrant's `because` array. The verifier will accept Bob's warrant because the check is perfectly valid. The `ski@v1` proof-of-work is tied to the *term*, not the *asserter*. Thus, one expensive check can be amortized across millions of spam assertions by free-riders, granting them all maximum amplitude without spending any ATP themselves.

### 3. Is F1 sufficient?
**Yes. I concede F1 and reject arithmetic merge.** 
There is no usecase that requires arithmetic merge of subjective opinions using `interfere`. The `interfere` function models the physical/logical collision of two waves during a compute reduction step (e.g. `APPLY(f, a)`). Merging two different observers' beliefs about a node is not a compute reduction; it is social consensus. If a jurisdiction wants to aggregate beliefs, it should either select the most trusted one (F1 selection) or require a threshold of signatures. F3 confuses the domain of the compute algebra (Book II) with the domain of social consensus (Book III).

## Findings and Design Criteria Attack

### P0: F3 Algebraic Category Error and Grinding Vulnerability
Using `interfere` as a merge operator is algebraically unsound for an N-ary set of assertions because it is neither commutative nor associative. It enables hash-grinding for phase dominance.
**Proposal:** Abandon F3 and F2. Adopt F1.
Concrete text for ADR-006:
> **Architecture Decision: F1 (Warrant-carried assertions)**
> An annotation assertion is a warrant `accept` whose subject is a JCS blob. Federation is purely the syncing of warrant stores. Arithmetic merge of annotations via `interfere` is rejected as a category error.

### P0: Criterion 4 (Weight costs something) is unenforceable via `ski@v1`
As demonstrated, `ski@v1` checks are trivially free-ridable. "Budget bounds claimable am" cannot survive.
**Proposal:** Amend Criterion 4. Weight must be backed by threshold signatures (social weight within the jurisdiction). Remove any reliance on `ski@v1` for annotation amplitude pricing.
Concrete text for ADR-006 Criterion 4:
> 4. **Weight is social:** an assertion's amplitude MUST be bounded by the jurisdiction's trust policy (e.g., threshold co-signatures). `ski@v1` checks MUST NOT be used to price amplitude due to free-rider amortization.

### P2: State boundedness (Criterion 5) under F1
F1 inherently satisfies this. A node only needs to store the *accepted* annotation warrant for a given NodeHash within its jurisdiction. It can garbage-collect or ignore rejected assertions.

## Prior Reviews Agreement/Disagreement
This is the first review of ADR-006, so there are no direct peers to agree or disagree with on this specific proposal. However, my findings strongly align with the rigorous separation of concerns championed by prior models in earlier gates (e.g., separating Book I truth from Book II navigation). Applying Book II's compute algebra to Book III's federation layer violates that separation and creates the algebraic absurdities demonstrated above.
