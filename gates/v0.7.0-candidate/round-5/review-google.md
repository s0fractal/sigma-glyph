<!--
family: google
model_requested: google/gemini-3.1-pro-preview
model_answered: google/gemini-3.1-pro-preview
requested_utc: 2026-08-30T06:33:20+00:00
answered_utc: 2026-08-30T06:35:46+00:00
finish_reason: stop
attempt: 1
max_tokens: 24000
prompt_sha256: f2199026e07469de308c4b35d42f7f6fa8f22d82ae5f2ca18a183a3641569486
system_sha256: a87d162d7a1c13ce15756bcf1565daf55701b91fd7e47ed432dfae4d3a819d2a
frozen_commit: 61eb3ea88bcc3bc0a03ed5692c8d3f974ed5ebf1
response_sha256: 9b095eb76544b33e174248470d177307eacfed379fb43b6f779c973841794e80
verdict: REJECT
-->

**P0: The text contradicts itself on the fallback derivation for APPLY nodes, leading to divergent implementations.**

Book III §1 states that Book II defines the wave algebra, Book III only determines whose assertions are accepted, and on conflict, Book II > Book III. 

Book II §2 defines the wave of an `APPLY` node as `wave(APPLY(f,a)) = complete(interfere(wave(f), wave(a)), pin(APPLY(f,a)))`, explicitly applying the explicit pin (e.g., `FALSE` gets `Ph=49152`). 

However, Book III §5 specifies the explicit formula for a federated wave of an `APPLY` node as:
`wave_fed(APPLY(f, a)) = selected(...) якщо є пряме твердження`, and `interfere(wave_fed(f), wave_fed(a)) інакше` (referencing Book II §5, which is strictly the mathematical interference function). This fallback branch explicitly omits the `pin(APPLY(f,a))` step from Book II §2.

**Counterexample:**
* Term: `FALSE = APPLY(K, I)`.
* Environment: Empty jurisdiction (no assertions filed).
* **Implementation A** follows Book III §5 exactly: `wave_fed(FALSE)` has no direct assertion, so it executes the fallback `interfere(wave_fed(K), wave_fed(I))`. Leaves `K` and `I` have no assertions and fall back to their Book II pins (`ph=32768` and `ph=0`). `interfere` returns `ph=32768` (due to Left Dominance).
* **Implementation B** observes the contradiction and applies the Book II > Book III priority rule (Book III §1). It uses Book II §2's `complete` rule, correctly reasoning that an empty jurisdiction must yield the canonical Book II pins. It computes `complete(interfere(...), pin(FALSE))` and returns `ph=49152` (per Book II §6.2).
* Result: Two conforming implementations disagree on the federated phase of `FALSE`.

*(Fix: Update the fallback branch in Book III §5 to `complete(interfere(wave_fed(f), wave_fed(a)), pin(APPLY(f,a)))` to match Book II).*

VERDICT: REJECT
