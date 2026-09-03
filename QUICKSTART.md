# Σ-GLYPH in ten minutes

No Books required. Three commands to trust nothing, one to compute.

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
python3 impl/sigma_glyph.py         # Book I  (compute core)   -> ALL PASS
python3 impl/sigma_wave.py          # Book II (wave views)     -> WAVE: ALL PASS
python3 impl/sigma_federation.py    # Book III (federation)    -> FEDERATION: ALL PASS
```

`pip install sigma-glyph` (0.6.7 on PyPI) gets the same three modules as
`python -m sigma_glyph` / `sigma_wave` / `sigma_federation`. **Clone anyway if
you want the sentence below to be true:** the wheel does not ship
`tests/spec_conformance/`, so an installed copy runs its property checks in full
and announces the recorded-vector replays as an explicit `SKIP`. Re-deriving
every vector is the checkout's job.

## What just happened

You ran the reference implementations and their local suites. That covers the
predicates those suites name, not every sentence in the Books. In particular,
`tools/spec_audit.py` lists unresolved predicates and clauses outside its reach.
The adopted Book currently says the Python oracle wins a prose/vector conflict;
PR #24 records why that is a specification defect and proposes removing it.

## Compute one thing

The relation implemented by `eval_hash(term_hash, atp, content_store)` is
deterministic, integer-only, and **total at the semantic layer**: every term with
a uint32 budget and valid partial CAS has exactly one of — a normal form,
`ATP Exhausted`, or `Unresolved Reference` — as a content-addressed
node. Work and peak semantic materialized-node count are bounded by the budget;
process memory is not, and a concrete implementation may still raise a local
resource fault. A verifier should pass `VERIFIER_LIMITS` or its own `max_atp`
policy before accepting a stranger's budget.

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'impl')
import sigma_glyph as sg

st = sg.Store()
for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES): st.put(b)

A = lambda l, r: ('app', l, r)
I, K = ('lit', sg.sha(b'I')), ('lit', sg.sha(b'K'))
def put(t):
    if t[0] == 'app': put(t[1]); put(t[2])
    return st.put(sg.term_bytes(t))

term = put(A(I, K))                      # I K  ->  K
result, spent = sg.eval_hash(term, 100, st)
print("result:", sg.term_hash(result).hex()[:16], "spent:", spent)

# An infinite loop is not an error — it is a priced, canonical outcome:
W = A(A(('lit', sg.sha(b'S')), I), I)
omega = put(A(W, W))                     # (S I I)(S I I) forever
result, spent = sg.eval_hash(omega, 1000, st)
print("Omega:", "ATP Exhausted" if result[1] == sg.sha(b'ATP Exhausted') else "?",
      "spent:", spent)
PY
```

Two strangers running this with the same demanded store content get
byte-identical terms and spend. A result hash alone does not identify which exit
occurred; that receipt gap is part of the next Book I candidate.

## The three layers in one paragraph each

**Book I — TRUTH.** A content-addressed SKI machine. Identity is
`SHA-256` of canonical bytes; evaluation is lazy, budgeted (`atp` pays
for work and semantic materialized size: `size − 1 ≤ spent` is a proved invariant), and
total. This is the only layer two nodes must agree on.

**Book II — NAVIGATION.** Waves (phase/amplitude/entropy) are *views*
over nodes — never part of identity, never able to touch `eval()` (there
is a vector proving that). Interference, decay, crystallization: math
for navigating, not for deciding.

**Book III — FEDERATION.** Annotations are *claims*, carried as signed
[Warrant](https://github.com/s0fractal/warrant) records inside
jurisdictions. A policy selects at most one claim per node; conflicts
surface explicitly and are never merged. Jurisdictions may disagree
forever — by design, with a mechanical name for every disagreement.

## Audit the project itself

Governed anchor adoptions and the adjudication records stored here are signed,
re-runnable records; ordinary commits and reviews are not thereby adopted:

```bash
python3 tools/warrant_gate.py .warrants  # consume the real Warrant verifier's machine report
```

Deeper: `spec/book-1-truth.md` is ~200 lines and self-contained.
`reviews/README.md` explains how to attack this project properly —
adversarial reviews are the development model, and yours is welcome.
