<!-- produced via tools/or_review.py | model: moonshotai/kimi-k2.6 | two-pass blind protocol | gates run by maintainer | pass-1 (blind) preserved at reviews/2026-07-kimi-adr006-gate.md.pass1 -->

# Review: ADR-006 Annotation Federation — Gate 3 Conceptual Pass

## Verdict

**Adopt F1-strict (selection-only normative core). Reject F3, F2, and the F1.5 named non-settlement score-profile extension point.**

I accept the maintainer-supplied gate transcripts (all exit 0). I did not run code. All arithmetic below is my own derivation from first principles against the Book II and Warrant v0.3 specifications.

---

## FOCUS 1: Adjudicate F1-strict vs F1.5 — Named Score Profiles as Governance Backdoor

**Finding: P1 — Spec silent on de-facto canonicity via defaults.**

Codex (gate 2) voted F1.5: selection-only normative core plus "named non-settlement score profiles" as an extension point. I reject this extension point. It is not a safe pressure valve; it is a governance backdoor through which non-settlement aggregation creeps into de-facto canonicity.

**Governance dynamics argument.** The sigma-glyph protocol does not regulate only on-chain behavior; it regulates what implementers ship. Once the protocol acknowledges "named profiles" as a first-class concept—even if explicitly labeled non-normative—the reference client will ship with a default profile for developer ergonomics. Network effects do the rest: wallet authors, explorers, and indexers will converge on that default because reimplementing ranking logic is expensive and user-confusing. Within two release cycles, the "popular profile" becomes the truth that users see. If that profile averages amplitudes, decays entropy, or applies any non-trivial arithmetic, F3 has re-entered through the social layer. The protocol cannot prevent this by saying "pretty please, treat it as non-canonical." The only safe move is to keep arithmetic aggregation entirely outside the protocol scope—client-local, unnameable, and non-discoverable.

**No protocol use case requires it.** Codex correctly conceded that no consensus-grade consumer needs arithmetic merge for canonical `wave(h)`. Ranking, discovery, and dashboards are query-layer concerns. They belong in client analytics, not in a protocol-extensible profile registry.

**Concrete text proposal (P1):**
```text
ADR-006 §Normative core MUST specify that the only settlement-grade
derivation of an effective WaveVectorQ is selection by policy from
accepted assertions (zero, one, or explicit conflict set). The protocol
MUST NOT define identifiers, discovery endpoints, default values, or
serialization formats for non-settlement score profiles. Any arithmetic
aggregation of multiple assertions over a node MUST be treated as an
untrusted client-side convenience and MUST NOT be referenceable from
warrant bodies, tunnel records, or jurisdiction metadata.
```

---

## FOCUS 2: Attack AnnotationViewID — Canonicalization, Replay, Privacy, Decidability

**Finding: P1 — Proposed schema is mechanically unsafe on four independent axes.**

Codex (gate 2) contributed `AnnotationViewID` as `SHA-256(JCS({...}))` over a structure containing `roots`, `policies`, `active_assertions`, and `selection_rule`. The intuition is correct—federation needs mechanical divergence naming—but the proposed execution fails.

### 2.1 Canonicalization pitfalls
Codex proposed a JCS object containing sorted arrays of WarrantIDs (`roots`, `policies`, `active_assertions`). Canonical JSON sorting over unbounded arrays is O(N log N) and brittle across implementations: string encoding of WarrantIDs (hex vs base64), Unicode normalization of `selection_rule`, and integer representation of epoch timestamps can all diverge. More critically, **the field set itself is not closed**. If two implementations include different optional metadata (e.g., one includes `warrant_profile` as `"warrant-v0.3"`, another as a hash), they produce different ViewIDs for the same logical view, defeating the purpose of "portable disagreement names."

### 2.2 Replay across jurisdictions
Codex's schema lists `roots` but does not require that the **jurisdiction genesis root be bound to the assertion subject blob**. Warrant §9 scopes settlement by roots, but a single blob can be referenced from multiple jurisdictions. An assertion warrant filed under jurisdiction A can be replayed into jurisdiction B's store (Warrant §9 explicitly allows shared blob stores). If B's policy does not explicitly reject foreign assertions, B's `active_assertions` array may include A's warrants. The resulting ViewID would name a view in B that silently inherits A's annotation graph without A's authorization. This is cross-jurisdiction replay.

### 2.3 Privacy of listing `active_assertions`
Listing the full sorted array of `active_assertions` in the ViewID object (or in any verifiable projection) leaks the entire annotation graph of a jurisdiction: who asserted what, when, and with which checks. For sensitive domains (medical, legal, corporate policy), this is unacceptable. The view must be nameable and verifiable without exposing the full candidate set.

### 2.4 `selection_rule` as string id is not mechanically decidable
Codex proposes `"selection_rule": "<policy-defined rule id>"`. A string label such as `"latest-trusted"` or `"rule-7"` is **not mechanically decidable**. Two conforming implementations cannot agree on what `"latest-trusted"` means unless they share an out-of-band registry, a central semantic authority, or identical source code. That reintroduces the exact divergence risk that F1 was meant to eliminate.

**Concrete text proposal (P1):**
```text
AnnotationViewID = SHA-256(JCS({
  "view": "sigma-glyph.annotation-view@v1",
  "jurisdiction": "<hex64 WarrantID of genesis root>",
  "node": "<hex64 NodeHash>",
  "policy": "<hex64 hash of machine-readable policy blob>",
  "epoch": <uint64>
}))

The `active_assertions` list MUST NOT appear in the ViewID or in
unencrypted projection metadata. Instead, the view metadata carries
`assertion_set_root`: the SHA-256 of a canonical JCS array of the
WarrantIDs of active assertions. Clients verify the root against the
array only if they have independently fetched the warrants.

`selection_rule` MUST be the hash of a deterministic, machine-readable
policy blob (JCS I-JSON), not a human-readable string id. The policy
blob MUST define a total ordering over candidate assertions using only
verifiable warrant fields (e.g., {"sort_keys":["ts","warrant_id"],
"order":"desc"}).
```

---

## FOCUS 3: Attack the Zero-or-One-or-Conflict-Set Selection Rule

**Finding: P1 — Conflict sets relocate the merge problem to clients without normative guidance.**

### 3.1 What policies actually select on
A deterministic selection policy can only consume fields that are mechanically verifiable from the warrant DAG:

| Selectable axis | Verifiable? | Notes |
|---|---|---|
| `warrant_id` (lexicographic) | Yes | Content-addressed, unforgeable. |
| `ts` (uint64) | Partially | Warrant §5.1 rejects wall-clock trust, but `ts` is signed and immutable. |
| `actor` (string) | Yes | Bound to key state. |
| `check_atp` / `check_hash` | Yes | Present in `because` array. |
| Supersede chain depth | Yes | Computable from `prior` links. |
| Trust rank / reputation | Only if defined | Must be a deterministic function of the warrant DAG (e.g., stake-weighted threshold signatures), not an out-of-band label. |

Policies cannot select on "correctness" of the wave because there is no oracle for what a node's wave "should" be. Any policy pretending to select on "truth" is merely laundering subjective authority into protocol grammar.

### 3.2 Explicit conflict sets relocate the merge problem
When a jurisdiction emits a conflict set instead of selecting one assertion, it abdicates the resolution that F1 promised to provide. Downstream clients—indexers, wallets, UI renderers—must then decide what to display. The spec is silent on client behavior, so implementers will inevitably reintroduce arithmetic merging (averaging, interference, or first-wins) to "resolve" the conflict for their users. This is F3 reintroduced by the back door, except now it is **undisciplined**: every client applies its own ad-hoc merge, producing a fragmentary de-facto F3 that is not even canonical within one jurisdiction.

**Concrete text proposal (P1):**
```text
A jurisdiction's selection policy MUST define a strict total ordering
over accepted assertions. It MUST emit a ConflictSet only when the
top-two candidates are equivalent under that ordering (ties). Clients
receiving a ConflictSet MUST NOT apply arithmetic merge, interference,
averaging, or any other aggregation to derive a single WaveVectorQ.
Automated systems MUST treat a conflicted node as unannotated for
Mass-aggregation and navigation purposes. Human-facing clients MAY
surface the conflict for review, but MUST NOT auto-select among the
candidates.
```

---

## FOCUS 4: The Semantic Status of Book II Waves in a Federated World

**Finding: P1 — Current text under-determines implementer behavior by implying a global navigation layer.**

Both prior reviews touched this but neither closed it. Here is the honest semantic status:

- **`interfere()` is a computation operator**, not a consensus operator. It models how a function's orientation shapes its argument's contribution during evaluation (Book II §5). It is correct for deriving a wave from child subtrees under `APPLY`.
- **Merging opinions is not computation.** When multiple actors assert different waves for the same node, they are not "interfering" physical waves; they are making conflicting claims about semantic significance. Applying `interfere()` to these claims is a category error. My arithmetic below proves this independently: the operator is non-associative and order-dependent, so it has no stable meaning for unordered sets of assertions.

Therefore, in a federated world, **a Book II wave is a per-jurisdiction, per-policy derived coordinate**, not a global attribute of a node. It is computed as follows:
1. Leaf nodes: select zero or one accepted assertion per jurisdiction; if none, wave is absent.
2. `APPLY` nodes: derive wave via `interfere()` from the selected waves of the function and argument subtrees.

This means divergence is **permanent and structural**, not a transient bug. The spec must stop promising that two jurisdictions "should" converge on the same wave for a node.

**Recommended text for Book II §Federation (new paragraph):**
```text
In a federated deployment, a WaveAnnotation is a claim filed by an
actor within a jurisdiction. The effective wave of a NodeHash in
jurisdiction J is derived by applying J's selection policy to the
accepted assertions for that node; if no assertion is selected, the
wave is absent. The `interfere()` operator defined in §5 applies
exclusively to structural derivation: computing the derived wave of an
APPLY node from the waves of its function and argument subtrees.
`interfere()` MUST NOT be used to merge multiple assertions for the
same node; such merging is algebraically unsound (non-commutative,
non-associative, and order-dependent) and not convergence-safe. Book
II waves are therefore per-jurisdiction, per-policy computed
coordinates, not global attributes of a node. Jurisdictions may diverge
permanently; this is by design. The normative pins in §6 are defaults
for the null jurisdiction and MAY be overridden by any jurisdiction's
genesis policy.
```

---

## FOCUS 5: Conceptually Missing from the Six Design Criteria

**Finding: P2 — Four load-bearing criteria are absent.**

The current six criteria (Book I unreachable, determinism, explicit divergence, weight costs, state bounded, auditability) leave critical gaps:

### 5.1 Verification work boundedness (Criterion 7)
State is bounded (criterion 5), but **work is not**. A client deriving a jurisdiction's current view must verify the warrant DAG: settlement status, supersede chains, key state, and tunnel records. If a jurisdiction has a long history, naive re-verification from genesis is O(total warrants). The protocol must permit incremental verification.

**Proposal:**
```text
7. Verification work bounded: deriving or updating a jurisdiction's
   effective view MUST require at most O(Δ warrants) re-verification
   work per epoch, where Δ is the set of newly accepted, superseded,
   or key-state-changed warrants. Implementations MUST NOT require
   full DAG replay from genesis for routine view updates.
```

### 5.2 Replay resistance (Criterion 8)
As noted in FOCUS 2, assertion warrants can be replayed across jurisdictions because Warrant §9 permits shared blob stores. The federation layer must prevent an assertion filed under jurisdiction A from being adopted by jurisdiction B without B-specific authorization.

**Proposal:**
```text
8. Replay resistance: an assertion subject blob MUST include the
   WarrantID of the jurisdiction root under which it is filed. A
   jurisdiction's selection policy MUST reject assertions whose
   embedded jurisdiction root does not match the viewing jurisdiction's
   genesis root or an authorized federated peer root.
```

### 5.3 Revocation / supersession soundness (Criterion 9)
The ADR problem statement mentions staleness, but the criteria do not address how assertions expire or are superseded. Warrant v0.3 has `prior` for supersede chains, but ADR-006 does not say how a jurisdiction's policy uses them to exclude stale annotations.

**Proposal:**
```text
9. Revocation soundness: a jurisdiction's effective view MUST exclude
   any assertion for which a later-settled supersede warrant is
   accepted under that jurisdiction's policy. Assertions MUST carry an
   explicit expiry epoch or refresh mechanism; jurisdictions MAY define
   a maximum assertion age after which stale assertions become
   settlement-inactive for wave derivation.
```

### 5.4 Privacy boundedness (Criterion 10)
Listing `active_assertions` (as in Codex's proposed ViewID) leaks behavioral graphs. The protocol should support private annotation without requiring public enumeration.

**Proposal:**
```text
10. Privacy boundedness: the protocol MUST support view verification
    against a content-addressed assertion-set root without requiring
    disclosure of the full candidate list to all querying clients.
    Jurisdictions MAY encrypt annotation subject blobs; selection
    policy hashes MUST remain public for determinism.
```

---

## Relation to Prior Reviews

### Agreements
- **Reject F3 / F2:** I independently verified the algebraic failure of the interference fold. My own vectors show `(w1·w2)·w3 = {ph=0, am=16384, en=0}` vs `w1·(w2·w3) = {ph=0, am=32768, en=-128}` for `w1={0,65535,0}, w2={16384,65535,0}, w3={16384,65535,0}`, confirming non-associativity with a 2× amplitude divergence and entropy divergence. I also verified same-phase entropy non-associativity: for `A={8192,65535,0}, B={8192,65535,-256}, C={8192,65535,-256}`, `((A·B)·C).en = -576` while `(A·(B·C)).en = -512`. This aligns with Gemini's reported non-associativity and Codex's phase-flip observations.
- **ski@v1 amplitude pricing fails:** I independently confirmed the amortization attack. One `ski@v1` check with ATP budget `B` can be cited across `N` assertions. If amplitude is capped by `f(B)` per assertion, total claimable weight scales as `N × f(B)` while prover cost remains `O(B)`. This confirms Gemini's free-riding finding and Codex's "proof supports facts; policy meters weight" conclusion.
- **F1 is sufficient:** I agree with both prior reviewers that no protocol use case requires arithmetic merge for canonical `wave(h)`.

### Disagreements
- **F1.5 extension point:** Codex voted F1.5; I vote **F1-strict**. The named non-settlement score profile is a governance backdoor, not a safe pressure valve. Network effects will canonize the reference implementation's default profile, reintroducing non-settlement aggregation as de-facto truth. The protocol must forbid protocol-level naming or discovery of such profiles.
- **AnnotationViewID schema:** I agree with Codex that a canonical view identifier is necessary, but I reject the proposed schema. Codex's inclusion of `active_assertions` as a plaintext sorted array creates canonicalization fragility, cross-jurisdiction replay, and privacy leaks. I replace it with a jurisdiction-bound, policy-hashed, Merkle-rooted design.

### New contributions relative to both prior reviews
- **Governance dynamics:** The argument that F1.5's extension point fails at the social/consensus layer, not the implementation layer.
- **Conflict-set client behavior:** Neither review specified what clients must do with conflict sets. I specify that clients must not merge them; automated systems must treat them as absent.
- **Book II paragraph:** A concrete normative paragraph for Book II that explicitly divorces `interfere()` from assertion merging and declares waves per-jurisdiction derived coordinates.
- **Missing criteria:** Four new criteria (verification work, replay resistance, revocation soundness, privacy boundedness) that close gaps left by the existing six.
