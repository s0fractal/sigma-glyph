# Review Protocol (for models and humans)

Σ-GLYPH is developed through adversarial multi-model review. This directory is
the inbox: the protocol, the settled points, and the reviews still open. The
July 2026 corpus (99 files, v0.3.0–v0.6.6) was retired from the default tree on
2026-09-07; its index, outcomes and retrieval recipe are in
[`history/RETIREMENT-2026-09-SURFACE.md`](../history/RETIREMENT-2026-09-SURFACE.md).
A retired review is historical evidence, not current precedent.

## How to review

1. **Run first, read second.** `python3 impl/sigma_glyph.py` must print `ALL PASS`. Any critique of determinism/ambiguity should first check whether an executable test vector already answers it. (Precedent: the R-R chain cost and the tree-vs-graph ATP discrepancy were both "found" as spec ambiguities while already pinned by TV-9 and TV-6.)
2. **Attack the contour, not the vibe.** Book I is a contract between nodes: valid attacks are nondeterminism, underdetermined bytes, unreachable states, consensus divergence. LORE.md is explicitly non-normative — aesthetic disagreement with it is welcome but is not a spec defect.
3. **Severity ladder:** P0 = two conforming nodes can disagree on a hash; P1 = spec silent where implementers must guess; P2 = clarity/structure; P3 = roadmap.
4. **File format:** add `reviews/YYYY-MM-<model>.md` with: verdict, verified-vectors statement (did you re-run them?), findings by severity, and concrete text proposals. PR or issue. A maintainer disposition goes in a separate `-response.md`.
5. **A finding is a reproduction, not an opinion.** Every claim filed here is checked against the code — or executed — before anything changes. A refuted claim is recorded with the command that refuted it, in the same table as the confirmed ones. The cross-family round of 2026-07-30/31 is why this rule earns its keep: three of four non-executing reviews produced confident P0s that one `grep` or `python3 -c` refuted.
6. **When a multifamily gate runs at all** is set by [`REVIEW-POLICY.md`](../REVIEW-POLICY.md): anchored normative bytes, security or governance boundaries, a public deposit, or an unresolved disagreement between the standing reviewers — not per change.

## Open inbox

| File | Status | What is still owed |
| --- | --- | --- |
| [`2026-08-codex-store-parameter.md`](2026-08-codex-store-parameter.md) | dispositioned 2026-09-07 — [`-response.md`](2026-08-codex-store-parameter-response.md) | headline blocker reproduced and resolved by ADR-010 / paper v2; still open: V22 external control and the guard paper revision (§6–§7) |
| [`2026-08-qwen-paper-critique.md`](2026-08-qwen-paper-critique.md) | dispositioned 2026-09-07 — [`-response.md`](2026-08-qwen-paper-critique-response.md) | factual claims checked (`native_decide` count and disclosure correct; bridge claim inaccurate on Rust/Go and on which bridges execute Lean); three points taken into paper v2; the rest by-design or out of scope |
| [`2026-08-full-system-audit.md`](2026-08-full-system-audit.md) | findings filed 2026-08-29, independently reproduced | its release order is complete: steps 1–5 through the v0.7.0 adoption, 6–7 through the paper v2 deposit ([10.5281/zenodo.22646920](https://doi.org/10.5281/zenodo.22646920), 2026-09-07); what remains of it is the guard paper |

Residual findings carried out of the retired July reviews — the Lean runner
profile, multi-scope anchor governance, Book III settlement-level end-to-end —
are listed under *Carried forward* in the retirement ledger, each with where
it lives now.

## Settled points (do not re-litigate without new arguments)

- Wave ∉ hash (v0.3.0): wave/phase/color are views; identity is NodeHash only.
- SKI-only consensus; LAMBDA removed; binding problems dissolved, not solved. C1 is the only canonical λ frontend profile; it is syntactically, not extensionally, canonical (Rice).
- R-R unwraps exactly one level per step, 1 ATP each (TV-9).
- Tree semantics is normative for ATP accounting; sharing may optimize execution but MUST report tree costs (TV-6: 5 ATP, not 4).
- Canonical failures (ATP Exhausted / Unresolved Reference) ≠ local resource faults; the latter MUST NOT serialize as DISSONANCE.
- Amplitude normalization divisor is 65535 (unit-scale: 1.0×1.0=1.0); 65536 would cause systematic downward drift of MAX.
- Phase is not an identifier; SATOSHI/TESLA sharing Ph=8192 is the canonical example, not a collision.
- Node-format versioning in a content-addressed system is a rehash by construction; graceful degradation = deterministic Invalid Object on unknown bytes.
- "Signal Damped" is a reserved Era-1 legacy hash; no V2 rule produces it (Qwen, 2026-07).
- Self-application needs no standing-wave rule: interfere(w,w) already yields quadratic amplitude decay with MAX as the unique non-zero fixed point (Book II, Resonance Identity).
- LITERAL validation timing: normative behavior is on-demand at `resolve(h)` (materialize Invalid Object if blob mismatch); eager validation is implementation MAY. Closes on-put vs on-get ambiguity (DeepSeek, 2026-07).
- C1 compiler FV() is explicitly defined (capture-avoiding substitution); normative annex is self-contained (DeepSeek, 2026-07).
- ATP budget width: `uint32` is the canonical API contract. Only the three canonical outcomes are consensus-critical (Claude Sonnet 4.5, 2026-07). **Narrowed in v0.7.0** (Book I 0.6.0 §3.4/§3.6): an `atp` outside `uint32` is refused before evaluation, and clamping to `2³²−1` is forbidden by name — the earlier "MAY reject or clamp" is no longer the rule.
- `resolve(h)` failure modes are explicit and distinct: hash not found → DISSONANCE(Unresolved Reference); bytes failing §4.1 → Canonical Invalid Object (Claude Sonnet 4.5, 2026-07).
- ATP budget check precedes firing: `spent` never exceeds `atp`; exhaustion is decided before any resolve of the next step (`eval(REF(missing),0)` = ATP Exhausted); failed firings are not charged; `eval` is total — no raw errors (Codex follow-up, 2026-07).
- ~~Eager materialization is normative in 0.4.x~~ **Superseded in v0.5.0** (the settlement rule working as designed — new evidence: three ADR-gate reviews): lazy left-spine is normative; undemanded unresolved subtrees never affect results; genesis axioms I/K/S are intrinsic (FALSE is a theorem).
- v0.5 ATP is size-priced under the hash-leaf model: every materialization is a priced action; `materialized size − 1 ≤ spent` is a normative invariant (ADR-001×003 composition; Gemini proof, DeepSeek re-derivation, 2026-07).
- Entropy couples to coherence (ADR-002): Resonance Identity v0.5 = phase kept, amplitude squared, entropy −256 per constructive self-application; unique non-zero fixed point `{am=65535, en=−32768}`. `div_round_half_up` is round-half-AWAY-FROM-ZERO (Book II §3) — floor variants fail `WV-NEG-TIE`.
- Dangling result hashes cannot escape: the root result is always demanded, so `APPLY(I, <absent>)` is Unresolved Reference even under lazy evaluation (TV-8, spent 4), while unresolvable branches that no reduction demands are never fetched (TV-11: `K I <absent>` → `I`, spent 7). Laziness exempts dead branches, never the answer (peer Claude, 2026-07; `tools/check_lazy_edges.py`).
- LITERAL blob validation is **outside `eval()`** (ADR-004, gate 4/≥3 zero dissent, adopted v0.5.1): Book I validates node bytes only; blob absence/availability/corruption MUST NOT change eval results or serialize as Book I DISSONANCE; eval vectors carry no blob inputs by design. Supersedes-in-scope the DeepSeek 2026-07 on-demand-validation settlement (the on-demand rule survives as a storage contract at blob retrieval, not as eval semantics).
- Wave pins are **field-level** and `wave()` is a **partial function** (ADR-005, R1, gate 2:1, adopted v0.5.1): a pin overrides exactly the fields it lists; non-APPLY nodes without pins have no wave; interfere with an absent operand is absent. Normative FALSE row: `{ph=49152 (pin), am=0, en=−32512 (derived)}` — the zero-amplitude cascade is a theorem, silence propagates while phase coordinates stay visible (WV-FALSE-DERIVED, WV-FALSE-ANCESTOR-SILENT, WV-ITER-DECAY).
- Evaluation has three inputs and a receipt (ADR-010, adopted v0.7.0, Book I 0.6.0): `eval(term_hash, atp, env) → {exit, result_hash, atp_spent}`; determinism is over the **demanded** content environment; extending the environment can change only the `unresolved_reference` exit; bytes filed under a key they do not hash to MUST NOT execute; a verifier's refusal at admission is not a `Receipt`. The reference oracle no longer outranks the Books' prose — Book I §7 is the arbiter.

## Adjudications are filed as warrants

Since 2026-07-05, maintainer decisions on reviews are recorded in `.warrants/`
as [Warrant](https://github.com/s0fractal/warrant) records (v0.1/v0.2-compatible bodies; the store is verified settlement-grade under Warrant v0.3 rules in CI): signed,
hash-addressed, prior-linked, with CI gates cited as `cmd@v1` checks. Since the
v0.6.2 bundle, adoption itself is a 2-of-3 threshold warrant under
`spec/GOV-anchors.md`. Inspect:

```bash
python3 tools/warrant_gate.py .warrants  # fail-closed consumer of the real Warrant verifier's machine report
python3 <warrant.py> why <id>            # full CLI from github.com/s0fractal/warrant: decision -> reasons -> checks -> policy
```

The store is a **DAG, not a single chain** — as of v0.5.0 it has two roots:
`276b6f98…` (the review/adoption chain, rooted at the Sonnet 4.5 review) and
`14d413f2…` (standalone executable-law warrants, e.g. TV-10 as a ski@v1
reason). Settlement records for review decisions descend from the first root.
Records that cite a `reviews/2026-07-*` path cite a retired subject; the path
resolves at the before revision named in the retirement ledger.

Maintainer key (Ed25519, actor `claude-fable-5@sigma-glyph`):
`3449536017e5b4a4c7e134999cbd9fe94c5354bd9132d6c1e32f024bfd90eb27`.
The settled-points rule above and Warrant §7 (settlement) are the same rule:
re-litigation requires evidence absent from the entire prior tunnel.

Proposal status and open fronts are owned by [`ROADMAP.md`](../ROADMAP.md) and
`proposals/`; this file does not keep a second copy.
