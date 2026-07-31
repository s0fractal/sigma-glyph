<!-- verbatim external review, filed unedited from the operator's working copy
     (strategy-2026-07/reviews-external/rv-guard-dsv32.md, 2026-07-30).
     model: deepseek/deepseek-v3.2 via OpenRouter. NO execution -- source reading only.
     scope: sigma-glyph/proofs/proof_guard.py.
     NOT an independent gate: same operator, same task framing as the other four.
     All three P0 claims are refuted by a line in the file the model was given.
     disposition: 2026-07-deepseekv32-guard-response.md -->

# guard review — deepseek/deepseek-v3.2

_tokens: prompt=16022 completion=1741_

Looking at this code and its history, I can identify several potential issues that could allow false or vacuous theorems to pass. Here's my analysis:

## P0 Issues (False/Vacuous Theorem Could Pass):

### 1. **Missing Pin Verification for `opaque` Declarations**
**Severity: P0**
**File:** `proof_guard.py` line ~800 in `dumpConst` function (in GUARD_DRIVER)
**Issue:** The driver's `dumpConst` function handles `opaqueInfo` but pins only the type and value. However, `opaque` declarations in Lean hide their implementation from the kernel while the compiler still uses it. The guard should either prohibit `opaque` entirely (it's currently not in the deny list) or pin them specially.

**Reproduction:**
```lean
-- In an audited file
opaque fake_proof : TheoremStatement := by
  native_decide  -- Compiler runs this, kernel doesn't see it

theorem guarded_theorem : TheoremStatement := fake_proof
```
The theorem would pass all checks: its statement is pinned, it depends only on `fake_proof` (which would be pinned), but `fake_proof`'s actual "value" that the compiler uses could be anything.

**Evidence:** `opaque` is mentioned in the deny list comments but isn't actually in the `_DENY` list. The driver's `dumpConst` treats `opaqueInfo` like `defnInfo`, dumping its value, but that value is what the kernel sees (an opaque constant), not what the compiler runs.

### 2. **Partial Compilation Trust**
**Severity: P0**
**File:** `proof_guard.py` line ~300 in `_RUNNER_ONLY`
**Issue:** `partial def` is only denied for strict profile, not runner. But what if a `partial def` appears in a module that's compiled but not listed as a runner source? The `source_guard` function only checks files based on whether they're in `runner_sources`, but compilation happens for all modules in `build`.

**Reproduction:**
1. Create `Proofs/Helper.lean` with:
```lean
partial def malicious_native_decide (p : Prop) : p := by
  native_decide
```
2. Don't list it in `runner_sources` (so it gets strict checking)
3. But also don't list it in `strict_sources` (maybe an oversight)
4. It won't be checked by `source_guard` because `coverage_guard` only checks files listed in sources
5. Yet it can be imported and used by guarded theorems

**Evidence:** The `coverage_guard` function scans all `.lean` files, but `source_guard` for a front only scans files in `strict_sources ∪ runner_sources`. A file not in either set won't get the `partial` check but could still be compiled if its module is in `build`.

### 3. **Trusted `native_decide` Axioms Can Come From Anywhere**
**Severity: P0**
**File:** `proof_guard.py` line ~700 in `guard_semantics`
**Issue:** The code checks that `native_decide` trust axioms come from declarations listed in `native_decide_sources`. However, there's no verification that those source declarations actually use `native_decide`. A malicious declaration could be added to `native_decide_sources` without actually using `native_decide`, creating a trust anchor for arbitrary false theorems.

**Reproduction:**
1. Add a fake declaration to `native_decide_sources`:
```lean
-- Not actually using native_decide
def fake_native_source : Nat := 42
```
2. Now any theorem can use `native_decide` and claim trust from this source
3. The theorem passes because the axiom shape matches and source is in the list

**Evidence:** The check at line ~700 only verifies `src in native_src`, not that `src` actually contains `native_decide`.

## P1 Issues (Incomplete Coverage):

### 4. **Unchecked `#eval` in Comments/Literals**
**Severity: P1**
**File:** `proof_guard.py` in `strip_lean_source`
**Issue:** The string/comment stripper blanks string literal contents, but what if a string literal contains `#eval` that the Lean compiler might process during compilation? While `#eval` is in the deny list, it's checked after stripping. A `#eval` inside a string literal wouldn't be caught.

**Reproduction:**
```lean
def s : String := "#eval unsafe_perform_io (print \"subverting\")"
-- The stripper replaces this with `""`, so the `#eval` check never sees it
```

**Evidence:** The deny list matching happens on the stripped body where string contents are blanked.

### 5. **Module Shadowing via LEAN_PATH Manipulation**
**Severity: P1**
**File:** `proof_guard.py` in `env_query` and `build_olean`
**Issue:** The guard uses `LEAN_PATH=olean_dir` when running queries. If `olean_dir` contains a module named `Lean` or `Init`, it shadows the real core modules. While `_shadows_core` checks for this, it only checks modules listed in the front's configuration, not what actually ends up in `olean_dir`.

**Reproduction:**
1. Manually place a malicious `Lean.olean` in the olean directory
2. The driver's `import Lean` would load this instead of core Lean
3. The driver itself could be compromised

**Evidence:** The `env_query` function sets `LEAN_PATH=olean_dir`, and the driver imports `Lean`. Nothing prevents malicious `.olean` files from being placed there.

### 6. **Time-of-Check vs Time-of-Use in Compilation**
**Severity: P1**
**File:** `proof_guard.py` in `build_front` and `guard_semantics`
**Issue:** There's a race condition: `build_front` compiles modules, then `guard_semantics` queries them. What if the source file changes between compilation and query? The check would see the compiled `.olean` (from old source) but the source checks ran on new source.

**Reproduction:**
1. CI script: compile clean source → run source guards → maliciously modify source → query (uses already-compiled oleans)
2. The query sees old correct theorems, source guard saw correct source, but actual compiled code is from modified source

**Evidence:** The workflow assumes compilation and checking happen atomically, but they're separate steps.

## What I Tried and Found Nothing For:

1. **Elaborator Hooks**: Checked if `@[app_unexpander]` or `@[command_elab]` could sneak past - they're in the deny list.
2. **Kernel Extensions**: Looked for ways to modify the kernel via environment extensions - the driver uses the kernel environment directly.
3. **Proof Irrelevance Abuse**: Considered if `Subsingleton` proofs could be swapped - but statement pinning prevents this.
4. **Universe Polymorphism Tricks**: Checked if universe level tricks could hide changes - level params are pinned.
5. **Compiler Plugins**: Looked for Lean compiler plugin mechanisms - none in the deny list, but also not standard.
6. **FFI via Extern**: `extern` is denied, so foreign code can't be called.
7. **Unsafe Operations**: `unsafe` is denied.
8. **Tactic Automation Hiding Proofs**: Checked if tactics could hide `sorry` - but the driver looks at kernel terms, not proof scripts.

The most serious issue is **#1 (opaque declarations)** - it directly allows compiler/kernel divergence and is not adequately defended against. This could be exploited to pass false theorems while maintaining all pins and checks.

**Recommendation**: Add `opaque` to the `_DENY` list immediately, as it's fundamentally incompatible with the guard's goal of ensuring kernel-checked proofs.