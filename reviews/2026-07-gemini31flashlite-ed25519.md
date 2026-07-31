<!-- verbatim external review, filed unedited from the operator's working copy
     (strategy-2026-07/reviews-external/rv-ed25519-gemini.md, 2026-07-30).
     model: google/gemini-3.1-flash-lite via OpenRouter. NO execution -- source reading
     only, and sent FUNCTION SLICES WITHOUT THE FILE HEADER (operator packaging error,
     which produced finding 2 below; recorded as such rather than scored against the model).
     scope: oaip/impl/oaip.py Ed25519 verifier.
     NOT an independent gate: same operator, same task framing as the other four.
     disposition: 2026-07-gemini31flashlite-ed25519-response.md -->

# ed25519 review — google/gemini-3.1-flash-lite

_tokens: prompt=6715 completion=1063_

I have reviewed the provided Python implementation. Below are the findings based on an analysis of the Ed25519 arithmetic and the structural control flow.

### Findings

#### 1. SEVERITY: P1 (Latent arithmetic bug)
**Location:** `_ed_recover_x` (line 46)
```python
    return _ED_P - x if x & 1 != sign else x
```
**Observation:** The variable `sign` was extracted in `_ed_decompress` using `y >> 255`. In Ed25519, `sign` is the least significant bit of the encoding of $x$ (post-decompression), which is meant to match the `sign` bit of the encoding of $y$. However, the standard mandates using the **least significant bit of $x$** as the sign bit. 
**Defect:** In your `_ed_recover_x`, you use `x & 1 != sign` to determine which root to pick. This assumes the `sign` bit passed into the function is the parity of $x$. But in your `_ed_decompress` (line 53), you pass `sign = y >> 255`, which is the parity of **$y$**. 
**Consequence:** For roughly 50% of valid signatures, this will choose the wrong square root (the negative one), resulting in the point being rejected (wrongful rejection). This explains why your point-decompression test passed (it likely used points where $x$ parity happened to match $y$ parity or tested on-curve checks that don't verify full round-trips).

#### 2. SEVERITY: P2 (Robustness / Exception risk)
**Location:** `ed25519_verify` (line 122)
```python
    k = int.from_bytes(hashlib.sha512(sig[:32] + pub + msg).digest(),
                       "little") % _ED_L
```
**Observation:** You use `hashlib.sha512` but the import is missing from the provided code snippet.
**Defect:** If `hashlib` is not explicitly imported in the actual file, this raises a `NameError` at runtime. While this is a trivial fix, in a security-critical routine, missing standard library imports in the context of the decision gate can lead to process crashes or bypasses depending on global error handling.

---

### What I Checked
*   **Small-order/Non-canonical inputs:** Checked `weak_ed25519_pubkey` logic. It correctly identifies the 32-byte non-canonical range ($y \ge P$) and blocks the specified small-order points. The use of `& ((1 << 255) - 1)` is correct for clearing the sign bit.
*   **Malleability:** `ed25519_verify` checks `S >= _ED_L`, which is the correct defense against the $S + L$ malleability attack.
*   **Coordinate arithmetic:** The choice of extended coordinates $(x, y, 1, xy)$ and the `_ed_add` formula matches the standard complete addition formulas effectively.
*   **Gate logic (`accepting_signature`):** The logic to separate "decision-making" signatures from "co-signatures" using `SIG_DECIDE_CAP` is robust. By using `id(s)` for memoization, you prevent double-verification of the same object, though the logic is sound even if an attacker attempts to flood the list.
*   **Modular Square Root:** The branch `if (x * x - xx) % _ED_P != 0` correctly implements the Legendre symbol check. However, refer to P1 regarding the selection of the root.
*   **Python `int` conversion:** `int.from_bytes` on a 32-byte string is safe and will not raise an exception; `len(pub) != 32` checks ensure the inputs remain within safe bounds.

### Recommendations
1.  **Fix `_ed_decompress`:** You must derive the `sign` bit from the input byte string $b$ correctly. Per RFC 8032, $b[31] \& 0x80$ is the sign bit of $y$, but the bit used to choose the $x$ coordinate must be the parity of $x$. You should define `sign = b[31] >> 7` for the Y-coordinate check, but in `_ed_recover_x`, you need the parity of the computed $x$ to compare against the *provided* parity bit.
2.  **Explicit Imports:** Ensure `import hashlib` and `import shutil` are at the top of the file as per PEP 8, as `oaip` assumes a standalone environment.