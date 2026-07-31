# Adjudication — z-ai/glm-4.7 on `proofs/proof_guard.py` (2026-07-30)

Raw review: [`2026-07-glm47-guard-coverage.md`](2026-07-glm47-guard-coverage.md)
(z-ai/glm-4.7 via OpenRouter, **no execution** — source reading only; the model was given
`proof_guard.py`, the vulnerability history and the current design).

**Headline: this is the one confirmed external code defect of the 2026-07-30/31 cross-family
round.** A reviewer that could not run anything read the file walk and saw that it was not
recursive. Six internal adversarial rounds had not seen it — not because it was deep, but
because every internal attack silently assumed the proof files sit where they currently sit.

**This was not an independent gate.** Same operator, same task framing as the other four
reviews in this round; see [`README.md`](README.md) § *Cross-family round, 2026-07-30/31*.

## Dispositions

| glm-4.7 finding | Verification | Verdict |
|---|---|---|
| **P1 (Incomplete)** `source_guard`/`coverage_guard` iterate `os.listdir(proofs_dir)` and never enter subdirectories, so `proofs/Sub/Evil.lean` is analysed by nothing — `axiom`/`sorry` undetected, declarations never checked against the registry | **Reproduced on the real tree before any fix**, with the reviewer's own vector: `proofs/Sub/Evil.lean` = `axiom backdoor : False` + `theorem secret_sauce`. `guard_sources(size front, "proofs") -> []`; `coverage_guard -> []`; `registry_guard -> []`; `python3 proofs/bridge_check.py` printed `BRIDGE: PREMISE HOLDS ON ALL OBSERVED STEPS` and exited 0 | **REAL — fixed** (`a4e7de1`, merged `6e0bb04`) |
| **"No P0 found"** — six routes traced and closed (sorry/`sorryAx` via `collectName`; definition gutting caught by `collectDeps` + statement pins; `native_decide` sources pinned; `strip_lean_source` blanking; string literals dumped as hex; audit scope derived from the kernel environment) | Each of the six matches the guard as shipped | **AGREED**, and useful as an independent statement of what the guard *does* cover |

## What the reviewer got wrong inside a correct finding

The reproduction narrative says `coverage_guard` "sees `Sub` (a directory), skips it, and sees
`Module.lean`". Under the pre-fix code it did **not** see `proofs/Sub/Module.lean` either —
`os.listdir("proofs")` never descends, so both files in the subdirectory were invisible. The
sub-claim is wrong; the finding it supports is right, and stronger than the reviewer stated.

The reviewer also framed the severity as **P1 (Incomplete)** — "an incompleteness in the
coverage audit rather than a soundness hole". The maintainer's disposition was harder: this
repo's severity ladder puts an unsound axiom that no textual layer reads in the same class as
the F2a/F2c bypasses, and the fix makes an unregistered `.lean` at any depth a **hard failure**.

## Fix, and the two holes the reviewer did NOT name

`a4e7de1` (branch `fix/subdir-coverage`, merged `6e0bb04`): one recursive enumeration,
`proof_guard.lean_sources()`, now feeds every source-layer check, so a future check inherits the
walk instead of repeating the bug; a source's module name is derived from its path
(`Sub/Evil.lean` → `Sub.Evil`) and that is the identity the registry, the import allowlist, the
core-shadow check and `build_olean`/`build_front` all use.

Chasing the finding surfaced two by-products, **both reproduced**, neither in the review:

1. **The import allowlist was built from the audited file's own directory listing.** A decoy
   `proofs/Sub/Lean.lean` made `import Lean` legal for its neighbours — F2c (the import that
   makes the guard's query spoofable) reopened *by path*. The most dangerous route found in the
   session, and it was living quietly.
2. **`_shadows_core` was applied only to module names a front already registers**, never to the
   module a file's *path* implies (`proofs/Lean/Foo.lean` → `Lean.Foo`).

Rejected alternatives are recorded in the commit body: an "auditable but unbuilt" tier (exactly
where an unsound axiom would legally live) and "scan it but do not require registration" (a scan
that finds nothing is indistinguishable from a scan that never ran; only refusal is observable).

## Test evidence

12 new F21 cases in `tests/proof_guard_test.py`, including the reviewer's exact vector against
the **real** `proofs/` tree (created and removed, directory and all). Red evidence: run against
master's `proof_guard.py` behind a shim giving master's behaviour the post-fix API — 9 named
FAILs plus the subdirectory build aborting with `object file Sub/Deep.olean does not exist`,
exit 1. Green after: `PROOF-GUARD: ALL PASS, 118 ok, 0 FAIL`, and the same vector now yields
three problems and `BRIDGE: FAILED`, exit 1. `tools/test-all.sh`: ALL GREEN, 17 surfaces, zero
skips.

## What was NOT done

The pin registry is unchanged — no front gains a subdirectory source; the capability is proven
by fixtures, not adopted into `proofs/`. `regen` was not run; no pin, claim or hash moved. The
semantic layer is untouched. Two latent instances of the same "hardcoded enumeration" shape were
surveyed, reported and left alone as out of scope (the vectors-freshness check in
`tools/test-all.sh` enumerates four filenames by hand; `tools/repo_map.py` scans a hardcoded
`SCAN`/`SCAN_DIRS` list).

**No independent adversarial gate ran against the fix, and nothing here is adopted.** Green
suites are not a gate — in this repository every real defect was found while the suites were
green, this one included.
