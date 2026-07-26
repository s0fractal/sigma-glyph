# ADR-008: Resonant Precedent — a cross-project precedent profile over Books II–III

**Status:** PROPOSED (2026-07-27, rev 15 after the Codex item-0 final gate) — awaiting the Decision Process gate (≥3 independent families). Non-normative until gated. ADR-008 is a cross-project OAIP/Warrant **precedent profile** composing a projection (OAIP), a new Warrant check runtime (`sigma-glyph.wave@v1`), and Book II/III math into one verifiable, content-addressed citation. The runtime (C1) is specified in **[WRT-001](../../warrant/proposals/WRT-001-wave-v1-runtime.md)** (its normative home); **this ADR defers to WRT-001 for the one temporal contract and the effective-lifecycle derivation, and never restates a competing formula.**

**rev 15 changelog (Codex item-0 final gate — three parser/parity P1s):**
- **One strict I-JSON domain (P1).** Trust/genesis decoding now rejects **invalid UTF-8** (Go) and **NaN/Infinity** (Python) and validates a **total genesis schema** (null/scalar `roots` → bounded no-op, no Python traceback) — identical digest-pinned bytes authorize identical roots in both impls. Vectors added.
- **Record count no longer hidden (P1).** The differential helper now compares **all three** summary fields; Python's summary counts valid + load-error records to match Go, so a malformed record + broken trust is genuinely `(1 record, 1 error, 0 warnings)` in both.
- **Non-vacuous genesis security assertion (P1).** The dup-key genesis vector now asserts the attacker root is **not adopted** (unadopted-root warning) against a clean-genesis baseline that **is** adopted.
- **R0/R1 stated separately in the C1 prose too (P2).**

**rev 14 changelog (Codex item-0 done-candidate gate — two composition P1s):**
- **Trust short-circuit precedes any per-record report (P1).** A malformed record plus broken trust is now exactly `(1, 0)` in **both** Python and Go (Python previously emitted the record load-error before the trust short-circuit → `(2, 0)`). Vector added.
- **`genesis.json` parsed by one strict I-JSON decode in both impls (P1).** A hash-pinned genesis with a duplicate `roots` key no longer adopts an attacker root in Go while Python rejects it; roots must be hex64. Vector added.
- **R0 / R1 modes stated separately (P2).** R0 = `raw_active_for(J)` (no citation/supersede subtraction); R1 = `authorized_effective_active_for(J, checkpoint)` minus the bound citation WID (unresolved, needs key-state).

**rev 13 changelog (Codex rev-12 / Warrant item-0 recheck-2):**
- **R0 ranks over RAW eligibility, not the censorship set (P1).** `verify_query` now uses `active_records` (`use_effective=False`); an unauthorized foreign `supersede` of the cited assertion **does not change** an R0 result (probe: still `pass`). The naïve effective derivation is used only by the R1-anticipating path as an explicitly-failing research vector; authorized effective lifecycle is R1-only. WRT-001 §6 no longer normatively requires the censorship formula.
- **Warrant generic refactor hardened (working tree).** The single snapshot is now threaded through the **re-litigation path** (`settlement_admissibility`/`tunnel`/`tunnel_fingerprints` no longer reload — a two-record lineage reads the store once, was 5); **`genesis.json` is hashed and parsed as the same bytes** (no swap-in attacker root); the runtime view retains **no live record map / raw store** (deep-copied private snapshot, TCB model stated) and its **CAS meter counts wrong-digest reads**; **failed-trust continuation is short-circuit, identical Python↔Go on empty AND non-empty stores** `(1,0)` (was Py `(1,1)` vs Go `(1,2)`/`(2,2)`), with vectors.

**rev 12 changelog (Codex rev-11 gate):**
- **Generic Warrant refactor genuinely closed (working tree).** Trust config is parsed **once** and closed-schema-validated (nested types too), passed by value — no second read, no nested-invalid escape; **Python↔Go parity** on missing/malformed/non-object/trailing/dup-key **and nested-invalid** trust, with vectors. Runtime handlers now get a **deeply read-only view + digest-authenticating CAS resolver** (no mutable records, no raw store/settlement — a handler can neither crash the verifier nor reach store authority); **core runtimes cannot be overlaid**; Warrant-local hook tests cover base/settlement/failed-settlement, single-snapshot, CAS, and mutation isolation. **Parity scope is explicit:** trust fail-closed is Py↔Go; the registry/handler/CAS layer is Python-only (Go/Rust runtime parity remains deferred).
- **Genuine non-filing R0 (P1).** R0 is now a `verify_query(...)` call that files **no** Warrant (record count unchanged; `cw_wid=None`, no role-binding, no self-subtraction). The stored role-bound path is exclusively R1.
- **Effective set is R1-only / unresolved (P1).** The main algorithm no longer embeds the censorship-prone "active minus supersede targets"; it names `authorized_effective_active_for(J, checkpoint)` as unresolved pending key-state. The naïve derivation survives only as an explicitly-failing research vector in the probe.

**rev 11 changelog (Codex rev-10 gate):**
- **Generic Warrant refactor completed with cross-impl parity (working tree).** `verify_store` now uses one record snapshot, fail-closed trust-context construction with a **Python↔Go stable reason + differential vectors**, and a `(body_version, runtime)`-scoped dispatch registry (no raw settlement authority) with Warrant-local hook tests. `0.1/0.2/cmd@v1/ski@v1` byte-for-byte; wave **not** registered. (rev 10 called this "landed" prematurely — the Go fail-open divergence is now closed.)
- **Effective-lifecycle is a CANDIDATE, not resolved (P1).** The naïve "active minus supersede targets" set is a **censorship primitive** — any self-signed actor can supersede another's WarrantID (probe shows a foreign actor censoring the cited assertion). Authorized effective supersession needs **key-state**, so effective-lifecycle and key-state are inseparable and both precede R1/budget.
- **R0 is a direct query, not a stored reason (P1).** The probe exposes R0 as a direct `verify_citation(...)` call; the `verify_store` demonstration is relabelled as *anticipating R1* (a stored reason needs the R1 authorized checkpoint the schema does not yet carry).

**rev 10 changelog (Codex rev-9 gate):**
- **Effective records, not raw eligibility (P1).** Warrant `active_records` is eligibility and still contains superseded records. The profile now uses one **effective set** (active minus active-`supersede` targets) identically for C2, C0 cardinality, and Book III `select()` (WRT-001 §6). Probe: a superseded cited assertion is `unverified`; a superseded projection + replacement verifies at **effective cardinality 1, not 2**.
- **R0 is an ephemeral query; STORED citations require R1 (P1).** A live-head reason cannot converge in an append-only store (a new citation does not deactivate the stale one, and stale→`unverified`→ERR poisons every prior citation). Decision: a `wave@v1` reason MUST NOT be filed settlement-active under R0; stored precedent needs the R1 authorized checkpoint (key-state). Ordered **before** budget.
- **Generic Warrant refactor landed (P1 plumbing).** `verify_store` builds its single settlement context **fail-closed** (broken trust → one global error, no crash/no silent zero) with a dispatch hook — `0.1/0.2/cmd@v1/ski@v1` byte-for-byte preserved, wave **not** registered.
- **Binding edge + §7 honesty (P2).** A resolvable-check borrower with `subject != check.entry` fails with the exact binding reason; the §7 output is relabelled an obsolete tuple sketch (real `fingerprint()` returns `None`).

**rev 9 changelog (Codex rev-8 gate):**
- **One index formula, LIVE-HEAD (P1).** The stale `strict_prior_closure(citation) ∩ active` formula is removed everywhere; the single contract is **`settlement_active_for(J)` minus the current citation WarrantID** (WRT-001 §6). It is complete (a filer cannot omit an active rival) but **live**: store growth **stales** a citation. A replayable historical checkpoint is R1 (needs key-state).
- **Citation role binding (P1).** A record is excluded from the universe only if it **is** this citation (`citation.subject == check.entry`), never for merely carrying a wave reason — so a rival assertion that borrows a valid reason still competes in Book III `select()` (probe: it wins and the cited loses).
- **Fail-closed, honest integration (P1).** A requested settlement verification with a broken context is a **global** error (not a silent zero even for a non-wave store). The probe is labelled a **wrapper prototype**; the real single-context/one-reporter `verify_store` change is required (WRT-001 §3).
- **§7 is PROPOSED-AND-DEFERRED (P1).** The real `fingerprint()` returns `None` for a wave reason; this ADR no longer claims registration/tunnel closure is specified.
- **Profile anchor not yet governed (P1/P2).** Book II/III use real anchors; the profile member must become an externally anchored artifact before adoption.
- **Warning honesty (P2).** The fixture carries 5 unbound-signature warnings (key-state deferred); `0 warnings` was a `quiet=True` artifact.

**Origin:** Book II let the wave leave the hash so it could be *navigation* (LORE). The outward-facing use of a computed-not-learned, byte-exact coordinate is **retrieval** — find the prior decisions a decision resonates with, verifiably, where a vector DB structurally cannot.

**Verified probes (run all three — reviews/README §1):**
- `examples/resonant_precedent_probe.py` — metric/query core (findings 1–4).
- `examples/resonant_precedent_contracts_probe.py` — coherence kernel + `PrecedentIndexViewID` (C2) + canonical result encoding (C3).
- `examples/resonant_precedent_join_probe.py` — **Warrant runtime integration (wrapper prototype)**: `wave@v1` under a non-retroactive version, dispatched via `verify_store`, deriving its LIVE-HEAD index, binding one exact (provisional) ruleset, role-bound citations. Happy fixture → `0 errors` (5 unbound-signature warnings); a malformed record → bounded, no crash; a broken context → global error; fifteen negatives → `≥1 error`; a live-head staleness demo.

**rev 7 changelog (Codex rev-6 gate, steps 1–4 done; 5–7 deferred):**
- **Non-retroactive version (P1).** `wave@v1` is permitted only under a new body version tag (`0.2+sigma-wave.1`); "0.2" bytes are untouched, so a clean Warrant 0.2 verifier **rejects** a wave record as an unknown version rather than re-interpreting 0.2. Cross-impl agreement on 0.2 is preserved.
- **Dispatcher inside `verify_store` (P1).** The public verifier itself re-executes `wave@v1` reasons and folds their errors/warnings into its count (the `ski@v1` pattern). A claimed-verdict lie now surfaces as a `verify_store` **error**, not only in a side hook.
- **Total dispatch (P1).** Every record shape is guarded and every runtime exception becomes `unverified`; a malformed inactive record (`because: ["not-an-object"]`) no longer raises — `verify_store` stays bounded.
- **Index derived, no host context (P1).** The index is derived **inside the runtime** from the settlement context and its set-commit compared to C2. *(Superseded by rev 9: the formula is LIVE-HEAD — `settlement_active_for(J)` minus the current citation — not the prior-closure intersection this entry originally proposed, which was filer-selectable.)*
- **Ruleset binds semantics (P1).** The runtime implements exactly one *exact* ruleset hash (Book II + Book III anchors; the profile member is provisional until governed); any other ruleset — even well-shaped — is `unverified`.
- **Set schemas (P2).** `anchor_set.books` and `vocabulary.leaves` are sorted duplicate-free sets.
- **Dependency scope corrected.** Book II (coherence/LUT), Book III (assertion schema + `select`), profile (C0/C1/C2 + join), Warrant (context/settlement/failure). Book I is **unreachable**; the only narrow Book I dependency is NodeHash identity.

---

## The metric/query core (settled in the core probe)

1. Pairwise (no fold); metric `LUT_COS[|Δph|]` is **symmetric**.
2. **Amplitude is not relevance** (conflates alignment with loudness); rejected.
3. **Coherence is relevance over a left-head phase bucket**, not head identity; co-located heads co-retrieve — settled phase-not-identity.
4. **Resolution = distinct phase buckets** (3 → 9 as vocabulary grows 3 → 11).

## The precedent citation (one settlement-carried, self-deriving proof)

`wave@v1` is a Warrant `check` reason. Its verifier, dispatched by `verify_store`,
takes only the reason-bearing WarrantID and the settlement context, and checks:

ruleset == the one exact ruleset the runtime implements (Book II/III governed; profile provisional)

  # the candidate universe differs by MODE — the two are NOT collapsed:
  R0 (a non-filing query, IMPLEMENTED):
     index := raw_active_for(J)                       # settlement eligibility, NO
                                                      # citation subtraction, NO
                                                      # supersede subtraction — so an
                                                      # unauthorized supersede cannot
                                                      # change a query result
  R1 (a stored citation, UNRESOLVED — needs key-state):
     index := authorized_effective_active_for(J, checkpoint)  MINUS this citation WID
                                                      # a supersede counts only if
                                                      # AUTHORIZED by target policy /
                                                      # key state; the naïve "active
                                                      # minus supersede targets" is a
                                                      # CENSORSHIP primitive and is
                                                      # NOT the algorithm; the stored
                                                      # citation is bound:
                                                      # citation.subject == check.entry

decision Warrant  (in index; real body.subject.hash == C0.source_subject)
  → accepted C0 projection  (in index; decision==accept; subject==C0 blob;
                             under==[profile]; exactly one per (source_warrant,profile))
  → projected term          (C0.term == cited.node; C0.vocabulary == resolved anchor)
  → Book III wave           (cited assertion in index; accept; jurisdiction ==
                             view's; wins select() under the COMMITTED policy)
  → coherence claim          (LUT_COS[|Δph(query, cited)|] ≥ committed threshold)
```

### C0 — Projection (OAIP): `sigma-glyph.precedent-projection@v1`

Identifies the decision by **WarrantID** (a subject hash cannot — many Warrants
may decide one subject): `{projection, source_warrant, source_subject, profile,
term, vocabulary}`, all hex64. Lifecycle: the C0 blob is the subject of an
**accept** projection Warrant filed under `under == [profile]`, in the derived
snapshot, with `source_warrant.subject.hash == source_subject`; the `profile`
governs the resolved `vocabulary`. **Cardinality:** exactly one active projection
per `(source_warrant, profile)`. The executable projection **DSL** (semantic
vocabulary → phase) is deferred past R0 — the only genuinely *semantic* open
problem, isolated behind an executable structural bridge.

### C1 — Citation runtime (Warrant): `sigma-glyph.wave@v1` → **WRT-001**

The runtime is specified normatively in **[WRT-001](../../warrant/proposals/WRT-001-wave-v1-runtime.md)**.
In brief: a Warrant `check` reason under a **new body version** (not a `RUNTIMES["0.2"]`
extension — that would retroactively change 0.2 validity); a closed check blob
`{check, entry, query_assertion, threshold, ruleset}`; **dispatched by
`verify_store`** so the public error count includes wave outcomes; **fail-closed**
on context failure; **one** settlement context; total over the byte domain;
`unverified` → ERR for an active record. The `ruleset` binds one exact anchor-set
(real Book II/III anchors; profile provisional). The candidate universe is
**mode-specific** (WRT-001 §6): **R0** (the implemented non-filing query) ranks
over **`raw_active_for(J)`** — no citation or supersede subtraction, so an
unauthorized supersede cannot change a result; **R1** (a stored citation,
unresolved — needs key-state) uses **`authorized_effective_active_for(J,
checkpoint)` minus the bound citation WID**. The query is an explicit **free
retrieval vector** (a user-chosen phase, no standing); a decision-side query join
is the named R1 tightening.

### C2 — Index identity (profile): `PrecedentIndexViewID`

`sha_hex(jcs(tagged object))` with `{view, jurisdiction, genesis_roots (sorted
set; jurisdiction ∈ it), projection_profile, metric, sigma_ruleset, wave_selection_policy,
active_warrant_set_commit, epoch}`. The commitment is checked against the
runtime-derived snapshot, not a supplied set; the committed selection policy makes
the effective wave — hence the ranking — reproducible.

### C3 — Result encoding (profile)

Buckets by descending coherence; WarrantIDs sorted for canonical bytes only (no
rank/authority); index is a set keyed by `(decision_warrant, projection_profile)`.

## Normative home (Codex's split, kept)

| Contract | Home |
|---|---|
| C0 projection payload + governance | **OAIP** / explicit OAIP↔Σ projection profile |
| C1 `wave@v1` runtime + version/failure semantics | **Warrant** runtime registry |
| coherence metric + anchor | **Book II** |
| assertion schema + effective-wave selection | **Book III** |
| C2 view identity + C3 result + join algorithm | **the ADR-008 profile** |

## Design criteria for the gate

1. **Book I unreachable** (only NodeHash identity is borrowed).
2. **Determinism per view** — same `PrecedentIndexViewID` ⇒ byte-identical ranking.
3. **Divergence explicit** — the view ID names *which* ranking.
4. **Metric fixed, symmetric, amplitude-independent** — `LUT_COS[|Δph|]`.
5. **No new authority** — a citation changes what is *seen first*, never what settles.
6. **Total verifier, dispatched by `verify_store`** — no byte-domain input raises.
7. **Digest authentication** — every blob load checks `sha256(raw)==hash`.
8. **Non-retroactive version** — wave records live under a new body version only.
9. **Live-head index, role-bound** — the index is `settlement_active_for(J)` minus
   the current citation (bound by `citation.subject == check.entry`), derived from
   the settlement context, never supplied; store growth stales a citation.
10. **Ruleset binds semantics** — one exact anchor-set selects the runtime (Book II/III governed; profile provisional).
11. **Accept-gated**; **resolved anchors**; **serialization order ≠ semantics**.

## Remaining before the final structural gate (deferred, named — not faked)

The ordered close-out lives in **[WRT-001 §Deferred](../../warrant/proposals/WRT-001-wave-v1-runtime.md)** —
**reordered after the rev-8 gate** (budget is no longer next; it would meter an
unstable computation): (1) **real single-context verifier** (one context, one
reporter, inside `verify_store` — not a wrapper); (2) **key-state → the R1
authorized historical checkpoint**, moved *before* budget because a replayable
claim is not closed without it; (3) **exact §7 fingerprint + tunnel closure**;
(4) **externally governed profile anchor**; (5) **deterministic budget** — the
four counters (canonical bytes read, WarrantIDs examined, assertion candidates,
fixed per schema/digest check), not ATP verbatim, with exact/one-over vectors;
(6) **direct-R0 abstention vectors**; (7) **cross-implementation parity** (Go/Rust);
(8) **governance adoption** (2-of-3 roster) with real signing keys, only after 1–7.

## Open questions for reviewers (the gate)

1. Is the new body version (`0.2+sigma-wave.1`) the right non-retroactive vehicle,
   or should `wave@v1` ride a committed runtime-extension field instead?
2. Budget units (§Deferred item 5) — the four counters, or a single Σ-style
   size-priced measure over bytes read?
3. Free-query vector vs a query-side decision join for R1?
4. Is `(source_warrant, profile)` one-active-projection cardinality correct?

---

**Verified-vectors statement:** run all three probes; confirm the metric findings,
the C2/C3 contracts, and — decisively — the Warrant integration: a clean 0.2
verifier rejecting the wave reason, the public `verify_store` reporting `0` errors
on the happy fixture and `≥1` on every active-citation negative, and no crash on a
malformed record, before critiquing the prose.
