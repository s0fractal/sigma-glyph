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

## Open proposals (see proposals/)

- ADR-001: size-priced ATP (memory linearly bounded by budget; breaks ATP vectors; v0.5 candidate).
- ADR-002: entropy–coherence coupling in interfere() (breaks pinned wave math; v0.5 candidate).

## Open fronts (contributions wanted)

- Federation/gossip protocol for WaveAnnotations (conflict semantics, convergence).
- Storage economics: CAS spam, rent/pruning — ATP prices computation, nothing prices bytes.
- Governance over Specification Anchors (Senate layer).
- Additional frontend profiles beyond C1; formal proofs (confluence is trivial for leftmost-outermost determinism, but a mechanized proof would be welcome).
