# Adjudication — deepseek-v3.2 on `proofs/proof_guard.py` (2026-07-30)

Raw review: [`2026-07-deepseekv32-guard.md`](2026-07-deepseekv32-guard.md)
(deepseek/deepseek-v3.2 via OpenRouter, **no execution** — source reading only).

**Headline: six claims, zero defects.** Three of them are P0s, and each is refuted by a line in
the file the model was given. That is the finding worth filing: a review that does not check its
own assertions against its own input lowers the weight of its "nothing else found" as much as it
lowers the weight of its findings.

**This was not an independent gate.** Same operator, same task framing as the other four
reviews in this round; see [`README.md`](README.md) § *Cross-family round, 2026-07-30/31*.

## Dispositions

| deepseek-v3.2 claim | Verification | Verdict |
|---|---|---|
| **P0 #1** `opaque` "is mentioned in the deny list comments but isn't actually in the `_DENY` list", so `opaque fake_proof := by native_decide` passes | `proof_guard.py:355` — `(r"\bopaque\b", "\`opaque\` hides a definition from the kernel while the compiler still runs a body")`, inside `_DENY`. One `grep` | **REFUTED** |
| **P0 #2** a `.lean` in neither `strict_sources` nor `runner_sources` escapes `source_guard` but is still compiled | `guard_sources` (`:1233-1237`) walks **every** `.lean` in the tree and assigns `profile = "runner" if f in runners else "strict"` — an unregistered file gets the **stricter** profile, not none. Independently, `coverage_guard` (`:519`) and `registry_guard` hard-fail an unregistered declaration or file. The premise is inverted: registration *relaxes*, it does not enable | **REFUTED** |
| **P0 #3** a declaration that does not use `native_decide` can be added to `native_decide_sources`, creating a trust anchor for arbitrary false theorems | The check does not trust the *list*, it matches the **axiom's generator**: `_NATIVE_DECIDE = ^([^\s]+)\._native\.native_decide\.ax[_0-9]+$` (`:232`), and `guard_semantics` (`:1185`) requires that captured name to be on the front's list. A declaration that does not use `native_decide` generates no such axiom, so listing it is inert. Widening trust requires a *real* `native_decide` source, which `registry_guard` (`:715-721`) additionally forces to be guarded or registered-unguarded, and which appears **by name** in the `GUARD_CLAIMS.txt` diff | **REFUTED** |
| **P1 #4** `#eval` inside a string literal escapes the deny check because `strip_lean_source` blanks literal contents | Correct behaviour, not a defect. A blanked literal's contents are **data**, not a command Lean will run; scanning them would false-positive on any file that discusses the syntax. `strip_lean_source`'s docstring states this design ("Literal *contents* cannot smuggle unsoundness, so they are replaced with an empty literal rather than scanned") | **NOT A DEFECT** |
| **P1 #5** a malicious `Lean.olean` placed in `olean_dir` shadows core and compromises the driver | Theoretically true, practically unreachable: `olean_dir` is a fresh `tempfile.TemporaryDirectory()` created by the guard in the same run. Anyone who can write into it mid-run already has code execution as the same user, which is a loss by every other route first. Worth a line in residuals, no more. (`_shadows_core` was separately hardened to cover path-implied module names in `a4e7de1`, for the unrelated F21 reason) | **REAL BUT IN-SCOPE-OF-THREAT-MODEL** — no change |
| **P1 #6** TOCTOU between `build_front` and `guard_semantics` — source modified after compilation | Same category. Both steps run in one process against one temporary directory; the window is milliseconds and the attacker postulated already has write access to the working tree during the run | **REAL BUT IN-SCOPE-OF-THREAT-MODEL** — no change |

## Outcome

**Zero code changes; zero spec changes.** Three P0s refuted by a line of the file, one P1 that
describes the design working as intended, two P1s that restate the documented "local write
during the run means you have already won" boundary.

The reviewer's own "what I tried and found nothing for" list (elaborator hooks, kernel
extensions, proof irrelevance, universe polymorphism, compiler plugins, FFI via `extern`,
`unsafe`, tactics hiding `sorry`) is recorded as an independent statement of routes probed, and
is the more useful half of this review.

No independent gate ran; nothing adopted.
