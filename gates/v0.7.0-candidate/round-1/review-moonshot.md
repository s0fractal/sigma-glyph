<!--
family: moonshot
model_requested: moonshotai/kimi-k3
model_answered: moonshotai/kimi-k3
requested_utc: 2026-08-29T16:50:55+00:00
answered_utc: 2026-08-29T16:58:33+00:00
finish_reason: stop
prompt_sha256: cccb925a4f76c75a004dba359254f621dbee82599adcd71474b9040ea2bff559
system_sha256: a87d162d7a1c13ce15756bcf1565daf55701b91fd7e47ed432dfae4d3a819d2a
frozen_commit: a49a106aefff9337a941cd30ce7fd3cecb95a105
response_sha256: 4b46fdf5e03c89fb5ba90471031411650bcdbf93b46e9f8d0af71056d9a69bfe
verdict: REJECT
-->

# Review of candidate v0.7.0 (Book I 0.6.0, Books II/III 0.7.0)

I reviewed the diff, the full candidate bytes of all three Books, ADR-010, VERSIONS.md, and GOV-anchors.md. I checked the arithmetic I could check (TV-4: 3+1=4 ✓; TV-9: 2·2+2·1=6 ✓; TV-12: 2+1=3 ✓; REF-chain 3n formula ✓; Book II `avg(−1,−2)=−2` and FALSE's `en=−32512`, `am=0` re-derived from §3/§5 and the printed LUT anchors ✓). I treated CI, gates, and authorship claims as non-evidence.

## P0-1 — §3.4 and §3.6 contradict each other for `atp ≥ 2^32`

The candidate **adds** §3.6 «Вхід поза оголошеною областю (MUST)»: an `atp` that is not a `uint32` **MUST** be refused locally, before the environment is consulted, and not as a canonical exit. The candidate **retains**, unchanged, the §3.4 bullet: «ATP > 2³²−1 — implementation-defined (MAY відхилити/clamp)».

Every integer `> 2³²−1` is an `atp` that is not a `uint32`. On that overlap the text says both "MAY clamp" and "MUST refuse" — i.e., it permits and forbids the same behavior with no stated priority between the two clauses (both are in Book I; the Book-priority rule does not apply *within* a Book). ADR-010's stated intent ("a budget that is not a `uint32`… is refused"; "-1, 1.5 and True… now raise") confirms §3.6 is the intended rule, but the §3.4 clause was never amended.

**Executable counterexample.** Term: `term_hash = 2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162` (H(I), intrinsic — no environment access needed, §5.1); budget `atp = 4294967296` (2³²); `env = ∅`.

- Implementation A, conforming to §3.6: refuses at admission; returns **no Receipt**; environment never consulted.
- Implementation B, conforming to §3.4 ("MAY clamp"): clamps to 4294967295 and evaluates a bare intrinsic thunk — zero priced actions — returning `Receipt { exit: normal_form, result_hash: 2f33694d…330f4162, atp_spent: 0 }`.

Two implementations, each citing MUST-level normative text, produce different observable outcomes for the same input, and the text cannot be harmonized as written. The fix is one line (strike "MAY відхилити/clamp" for out-of-range values and point at §3.6), but these bytes contain the contradiction.

## P1-1 — §3.5 is silent on *when* the env hash-property is checked, and §5.1's intrinsic bypass makes it reachable

§3.5 mandates: bytes under a foreign key MUST NOT be executed as that key's node, and "Реалізація, **що виявила** таку невідповідність, MUST відмовити локально." Nothing states whether detection is eager (validate the env at admission) or demand-scoped (check only bytes actually fetched). §5.1 separately mandates that intrinsic hashes are served **without depending on store bytes**, so a lazy implementation never even reads an entry under H(K).

**Executable counterexample.** Let `b = 0101‖H(K)` (canonical bytes of `REF(H(K))`, 34 bytes), `h = SHA-256(b)`. Environment `env = { h ↦ b, H(K) ↦ 0x00×66 }` — the second entry is a foreign-key poisoning (NodeHash ≠ H(K)). Term: `term_hash = h`; `atp = 10`.

- Implementation A (validates env entries at admission): detects the H(K) mismatch → per §3.5 MUST refuse locally, **no Receipt**.
- Implementation B (lazy): forces `h` (2 ATP) → REF node; R-R (1 ATP) → `thunk(H(K))`; §5.1 serves K intrinsically without touching the poisoned entry → `Receipt { normal_form, bc0c2fe2…bb0a486c, 3 }`. B executed no foreign bytes, violating nothing it can see.

The same ambiguity exists without intrinsics (poisoned entry under a never-demanded key). An implementer must guess whether "виявила" licenses or requires eager validation; the two readings diverge on a concrete input. Fixable by one sentence scoping detection (e.g., "the property MUST be verified for every hash actually resolved; entries never demanded do not affect the result").

## P2 findings

- **§7 prose uses the two-input call shape** (`eval(·,4)`, `eval(r2,6)`) although §3.4 now mandates three inputs. The environment is stated only in some TVs (TV-9's store, TV-12's empty store). Results are unaffected (the «Що саме має узгоджуватися» paragraph pins record fields, not call syntax), but the shorthand should be noted as such.
- **Books II/III import the new §7 rule as "те саме правило, що в Книзі I §7"** without saying whether Book I §7's second paragraph (the explicit list of which record fields represent prose claims) applies to their suites' schemas, which differ from Book I's. An auditor of wave/federation suite-vs-prose consistency must guess the mapping.
- **Books II/III version bumps**: VERSIONS.md's own MINOR criterion is "a conforming implementation of the previous version could become non-conformant"; the arbitration-rule change binds *editions*, not implementations, so MINOR is a stretch under the stated rule. VERSIONS.md declares this judgment uncheckable and is non-normative, so this is naming only.

## P3 findings

- **GOV-anchors.md** pins "Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1". Leaving it unedited is *correct* for this candidate: the only Book I semantics GOV consumes (`NodeHash(LITERAL, SHA-256(bytes))`) are unchanged, and GOV §0 makes re-pinning a governed breaking change. But after adoption the pin names versions no longer current in the bundle — schedule a re-pin at GOV's next revision.
- Retained typo «преф лайт» (§3.4). Pre-existing.

## On the two flagged scope questions

1. The English rendering reproduces both clashing clauses faithfully ("MAY reject/clamp" vs "MUST be refused"), so the translation does not drift from the normative text — the P0 lives in both.
2. GOV-anchors non-editing is sound, per the P3 above.

The P1-1 silence is textually fixable, but P0-1 is a standing self-contradiction in the normative bytes under review; per the severity ladder that bars ADOPT-WITH-AMENDMENTS.

VERDICT: REJECT
