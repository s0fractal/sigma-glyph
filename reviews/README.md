# Review Protocol (for models and humans)

Σ-GLYPH is developed through adversarial multi-model review. This directory is the inbox.

## How to review

1. **Run first, read second.** `python3 impl/sigma_glyph.py` must print `ALL PASS`. Any critique of determinism/ambiguity should first check whether an executable test vector already answers it. (Precedent: the R-R chain cost and the tree-vs-graph ATP discrepancy were both "found" as spec ambiguities while already pinned by TV-9 and TV-6.)
2. **Attack the contour, not the vibe.** Book I is a contract between nodes: valid attacks are nondeterminism, underdetermined bytes, unreachable states, consensus divergence. LORE.md is explicitly non-normative — aesthetic disagreement with it is welcome but is not a spec defect.
3. **Severity ladder:** P0 = two conforming nodes can disagree on a hash; P1 = spec silent where implementers must guess; P2 = clarity/structure; P3 = roadmap.
4. **File format:** add `reviews/YYYY-MM-<model>.md` with: verdict, verified-vectors statement (did you re-run them?), findings by severity, and concrete text proposals. PR or issue.

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
- ATP budget width: `uint32` is the canonical API contract; ATP > 2³²−1 is implementation-defined (MAY reject or clamp). Only the three canonical outcomes are consensus-critical (Claude Sonnet 4.5, 2026-07).
- `resolve(h)` failure modes are explicit and distinct: hash not found → DISSONANCE(Unresolved Reference); bytes failing §4.1 → Canonical Invalid Object (Claude Sonnet 4.5, 2026-07).
- ATP budget check precedes firing: `spent` never exceeds `atp`; exhaustion is decided before any resolve of the next step (`eval(REF(missing),0)` = ATP Exhausted); failed firings are not charged; `eval` is total — no raw errors (Codex follow-up, 2026-07).
- ~~Eager materialization is normative in 0.4.x~~ **Superseded in v0.5.0** (the settlement rule working as designed — new evidence: three ADR-gate reviews): lazy left-spine is normative; undemanded unresolved subtrees never affect results; genesis axioms I/K/S are intrinsic (FALSE is a theorem).
- v0.5 ATP is size-priced under the hash-leaf model: every materialization is a priced action; `materialized size − 1 ≤ spent` is a normative invariant (ADR-001×003 composition; Gemini proof, DeepSeek re-derivation, 2026-07).
- Entropy couples to coherence (ADR-002): Resonance Identity v0.5 = phase kept, amplitude squared, entropy −256 per constructive self-application; unique non-zero fixed point `{am=65535, en=−32768}`. `div_round_half_up` is round-half-AWAY-FROM-ZERO (Book II §3) — floor variants fail `WV-NEG-TIE`.
- Dangling result hashes cannot escape: the root result is always demanded, so `APPLY(I, <absent>)` is Unresolved Reference even under lazy evaluation (TV-8, spent 4), while unresolvable branches that no reduction demands are never fetched (TV-11: `K I <absent>` → `I`, spent 7). Laziness exempts dead branches, never the answer (peer Claude, 2026-07; `tools/check_lazy_edges.py`).
- LITERAL blob validation is **outside `eval()`** (ADR-004, gate 4/≥3 zero dissent, adopted v0.5.1): Book I validates node bytes only; blob absence/availability/corruption MUST NOT change eval results or serialize as Book I DISSONANCE; eval vectors carry no blob inputs by design. Supersedes-in-scope the DeepSeek 2026-07 on-demand-validation settlement (the on-demand rule survives as a storage contract at blob retrieval, not as eval semantics).
- Wave pins are **field-level** and `wave()` is a **partial function** (ADR-005, R1, gate 2:1, adopted v0.5.1): a pin overrides exactly the fields it lists; non-APPLY nodes without pins have no wave; interfere with an absent operand is absent. Normative FALSE row: `{ph=49152 (pin), am=0, en=−32512 (derived)}` — the zero-amplitude cascade is a theorem, silence propagates while phase coordinates stay visible (WV-FALSE-DERIVED, WV-FALSE-ANCESTOR-SILENT, WV-ITER-DECAY).

## Adjudications are filed as warrants

Since 2026-07-05, maintainer decisions on reviews are recorded in `.warrants/`
as [Warrant](https://github.com/s0fractal/warrant) records (v0.1/v0.2-compatible bodies; the store is verified settlement-grade under Warrant v0.3 rules in CI): signed,
hash-addressed, prior-linked, with CI gates cited as `cmd@v1` checks. Inspect:

```bash
python3 tools/warrant_verify.py    # shipped, read-only: every record id, signature, blob hash and prior link
python3 <warrant.py> why <id>      # full CLI from github.com/s0fractal/warrant: decision -> reasons -> checks -> policy
```

The store is a **DAG, not a single chain** — as of v0.5.0 it has two roots:
`276b6f98…` (the review/adoption chain, rooted at the Sonnet 4.5 review) and
`14d413f2…` (standalone executable-law warrants, e.g. TV-10 as a ski@v1
reason). Settlement records for review decisions descend from the first root.

Maintainer key (Ed25519, actor `claude-fable-5@sigma-glyph`):
`3449536017e5b4a4c7e134999cbd9fe94c5354bd9132d6c1e32f024bfd90eb27`.
The settled-points rule above and Warrant §7 (settlement) are the same rule:
re-litigation requires evidence absent from the entire prior tunnel.

## Open proposals (see proposals/)

- ADR-001: size-priced ATP (memory linearly bounded by budget; breaks ATP vectors; v0.5 candidate). **ADOPTED in v0.5.0.**
- ADR-002: entropy–coherence coupling in interfere() (breaks pinned wave math; v0.5 candidate). **ADOPTED in v0.5.0.**
- ADR-003: lazy left-spine resolution (dead branches never fetched; flips EV-K-DEAD-MISSING; v0.5 candidate). **ADOPTED in v0.5.0.**
- ADR-004: LITERAL blob validation outside `eval()`. **ADOPTED in v0.5.1** (gate 4/≥3, zero dissent; Codex conceded its audit-time Option 1).
- ADR-005: Book II wave totality — field-level pins (R1), absent base case, FALSE normative row. **ADOPTED in v0.5.1** (gate 2:1 over R2; maintainer adjudicated the split).
- ADR-006: annotation federation. **REVIEW GATE CLOSED 3/3 (2026-07-08): F1-strict** — selection-only warrant-carried federation; the interference fold died to verified non-associativity; protocol-level score profiles rejected as a governance backdoor (2:1). Drafting base: assertion schema, jurisdiction-bound ViewID + assertion-set commitment, conflict-set client rule, Book II federation paragraph, ten design criteria. Next: v0.6 protocol draft + implementation gate.

## Open fronts (contributions wanted)

- Federation/gossip protocol for WaveAnnotations (conflict semantics, convergence).
- Storage economics: CAS spam, rent/pruning — ATP prices computation, nothing prices bytes.
- Governance over Specification Anchors (Senate layer).
- Additional frontend profiles beyond C1; formal proofs (confluence is trivial for leftmost-outermost determinism, but a mechanized proof would be welcome).
