<!-- verbatim external review, filed unedited from the operator's working copy
     (strategy-2026-07/reviews-external/rv-guard-glm.md, 2026-07-30).
     model: z-ai/glm-4.7 via OpenRouter. NO execution -- the model read source only.
     scope: sigma-glyph/proofs/proof_guard.py.
     NOT an independent gate: same operator, same task framing as the other four.
     This is the ONE confirmed external code defect of the round; reproduced on the
     real tree before any fix (a4e7de1, merged 6e0bb04).
     disposition: 2026-07-glm47-guard-coverage-response.md -->

# guard review — z-ai/glm-4.7

_tokens: prompt=15252 completion=38473_

After reviewing the `proof_guard.py` implementation, the history of vulnerabilities, and the current design, I have identified a **P1 (Incomplete)** vulnerability regarding file traversal coverage. I found **no P0** route that allows a false theorem to pass the semantic checks or a checked theorem to become vacuous without triggering a failure.

### **P1: Subdirectory Source Files Are Invisible to the Textual Guard**

The textual guard (`source_guard`, `coverage_guard`) iterates over `os.listdir(proofs_dir)` and only processes entries ending in `.lean`. It does **not** recursively traverse subdirectories. Consequently, source files in subdirectories (e.g., `proofs/Subdir/Helper.lean`) are never analyzed for banned constructs (`axiom`, `sorry`), nor are their declarations checked against the registry.

This violates the coverage requirement that "Every `theorem`/`lemma` in proofs/*.lean must be either guarded or explicitly registered as intentionally-unguarded." While the semantic guard would likely block the use of an unregistered dependency from a subdirectory in a guarded theorem (due to missing pin), the presence of unsound code (e.g., `axiom false_ax : False`) in a subdirectory file would not cause the CI to fail, provided it is not imported by a strictly guarded file. If imported via a loose chain (e.g., imported only by other unguarded files), it could theoretically persist in the repository as "dead code" that the guard never sees.

**SEVERITY:** P1 (Incomplete)
**EXACT REPRODUCTION:**
1.  Create a subdirectory in `proofs/`: `mkdir proofs/Sub`.
2.  Create a file with a banned construct or unregistered theorem: `proofs/Sub/Evil.lean`.
    ```lean
    -- proofs/Sub/Evil.lean
    axiom backdoor : False
    theorem secret_sauce : Nat := 0
    ```
3.  Create a top-level file that imports the subdirectory file (optional, to prove reachability): `proofs/Sub/Module.lean`.
    ```lean
    -- proofs/Sub/Module.lean
    import Evil
    ```
4.  (Optionally) Import `Sub.Module` into a main file.
5.  Run the guard.
    *   `coverage_guard` lists files in `proofs/`. It sees `Sub` (a directory), skips it, and sees `Module.lean`. It never enters `Sub/`.
    *   `source_guard` runs on `Module.lean`. The `allowed_imports` check allows importing `Evil` (if `Module.lean` is in the same dir or relative rules allow it).
    *   `source_guard` is **never** called on `proofs/Sub/Evil.lean`.
    *   The `axiom backdoor : False` is not detected by the textual layer.
    *   If `backdoor` is not used by a guarded theorem, the semantic guard does not inspect it.
    *   If `backdoor` IS used, the semantic guard will catch it (assuming `backdoor` is not a trusted axiom).
    *   However, the presence of the unaccounted theorem `secret_sauce` goes unnoticed.

**FILE:** `proofs/proof_guard.py`
**LINES:**
*   `source_guard` loop: `for f in sorted(os.listdir(proofs_dir)): ... if not f.endswith(".lean"): continue` (Approx line 453 in `guard_sources`).
*   `coverage_guard` loop: `for f in sorted(os.listdir(proofs_dir)): ... if not f.endswith(".lean"): continue` (Approx line 374 in `coverage_guard`).

***

### **No P0 Found**

I attempted to find a route where a **FALSE** theorem (or vacuous theorem) reaches a green bridge (i.e., passes the checks).

1.  **Axioms/Sorry:** The semantic guard walks the kernel environment of the proof term. Any use of `sorry` (which desugars to `sorryAx`) or `axiom` is detected via `collectName`. If present, they are checked against `allowed_axioms`. `sorryAx` is not in the standard allowlist. Custom axioms would need to be explicitly added to `GUARD_CLAIMS.txt` and `theorem_pins.json` (which requires a human-reviewed diff).
2.  **Definition Gutting:** `collectDeps` walks the transitive dependencies of the theorem's type and value. Every non-core dependency is dumped and pinned against `theorem_pins.json`. Modifying a definition (e.g., `Reach` or `Valid`) changes the structural hash/dump, causing `guard_semantics` to fail with a DEFINITION DRIFT error.
3.  **Native Decide:** The guard specifically pins the sources of `native_decide` axioms and checks that they match the allowed list (`native_decide_sources`) and that the source definitions are statement-pinned. This prevents arbitrary trust of the compiler.
4.  **Textual Bypass:** `strip_lean_source` effectively removes comments and blanks literal contents (strings, raw strings, char literals), preventing keyword blinding attacks. The regexes for `axiom`, `sorry`, `partial`, etc., run on the stripped body.
5.  **String Literal Swapping:** The driver dumps string literals as hex of their UTF-8 bytes (`hexOfString`). This prevents swapping a hash constant with a same-length but different-value string without changing the pin.
6.  **Pinning Scope:** The audit scope is derived from the kernel environment (complement of `core_modules`), preventing the exclusion of a module by simply removing it from a config list, as `env_query` validates that the loaded module set matches the build set.

**Conclusion:** The guard design appears sound against false proofs passing the check. The "glue" (Python script) correctly interfaces with the Lean compiler and driver to enforce these properties. The only identified gap is the non-recursive file traversal, which is an incompleteness in the coverage audit rather than a soundness hole in the verification of the specific theorems that *are* checked.