# Σ-GLYPH in ten minutes

No Books required. Three commands to trust nothing, one to compute.

```bash
git clone https://github.com/s0fractal/sigma-glyph && cd sigma-glyph
python3 impl/sigma_glyph.py         # Book I  (compute core)   -> ALL PASS
python3 tests/resume_test.py        # sigma-resume              -> SIGMA-RESUME: … PASS, 0 FAIL
```

`pip install sigma-glyph` gets the same modules as `python -m sigma_glyph` and
`python -m sigma_provider` (0.8.0 is the first release with the resume surface).
**Clone anyway if you want the sentences below to be true:** the wheel does not
ship `tests/`, so an installed copy runs its property checks and cannot replay
the conformance vectors or the claims witnesses. Re-deriving every vector is the
checkout's job.

## What just happened

You ran the reference implementations and their local suites. That covers the
predicates those suites name, not every sentence of the specification.
`.warrant/claims.json` covers 68 normative sentences of Book I and sigma-resume:
each is a claim that names the cases witnessing it and the mutants that must
break them, or says why it is unbacked (`warrant claims view`). The registry is
not complete: some MUST clauses have no claim yet (Book I §6's ban on capturing
a free variable, §7's prose/vector agreement), and `warrant claims check` checks
the registered claims against their documents, not the documents for clauses
nobody registered. `tools/spec_audit.py` lists what is still outside its reach. No implementation,
the reference one included, takes precedence over the normative text and the
anchored suite: a prose/vector disagreement is a defect to file, not a call the
oracle makes.

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
occurred; `eval_receipt(term, atp, store)` returns the exit explicitly (Book I
0.6.0 §3.4), and `eval_hash` above is the result-and-spend convenience that the
earlier PyPI 0.6.7 module also has. The snippet is kept to that shared surface
so the release gate can run it both ways.

## Resume one thing

The same kind of computation, run as six segments of 5 ATP each, reaches the
result one segment of 1000 ATP reaches, and the chain of checkpoints verifies by
replay:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'impl')
import sigma_provider as p

RT = "sigma-book1-0.6.0/hash-thunk/leftmost-outermost"
t = p.term("S K K (S K K (K I))")                 # -> K I
inp, nodes = t["input"], t["nodes"]; hashes = sorted(nodes)
s = p.start(RT, inp, hashes)
ck, st, chain, n = s["checkpoint"], s["state"], [(s["checkpoint"], s["state"])], 0
while True:
    a = p.advance(RT, hashes, nodes, ck, st, 5); n += 1
    ck, st = a["checkpoint"], a["state"]; chain.append((ck, st))
    if a["outcome"] != "PAUSED": break
one = p.advance(RT, hashes, nodes, s["checkpoint"], s["state"], 1000)
print(n, "segments:", a["outcome"], a["result"][:16])
print("one run:   ", one["outcome"], one["result"][:16])
print("verify:", sorted({v["code"] for v in p.verify(RT, inp, hashes, nodes, chain)}))
PY
```

```text
6 segments: NORMAL_FORM 65cd957fee7ec9fb
one run:    NORMAL_FORM 65cd957fee7ec9fb
verify: ['NORMAL_FORM', 'PAUSED']
```

`65cd957f…` is `K I`, Book I §5.2's "FALSE is a theorem". To continue a
stranger's checkpoint use `p.resume(...)`, which replays it from your own root
first; `advance` trusts the checkpoint it is given.

## The two layers in one paragraph each

**Book I — TRUTH.** A content-addressed SKI machine. Identity is
`SHA-256` of canonical bytes; evaluation is lazy, budgeted (`atp` pays
for work and semantic materialized size: `size − 1 ≤ spent` is a proved invariant), and
total. This is the only layer two nodes must agree on.

**sigma-resume.** A long computation in budgeted segments: each segment ends in
a normal form, an explicit local refusal or a checkpoint (PAUSED); anyone can
resume a checkpoint from their own root and verify a receipt by replaying it.
Specified in `spec/sigma-resume.md`; Book I governs the transition.

## Audit the project itself

```bash
tools/test-all.sh                   # the whole matrix CI runs, one command
python3 tools/verify_anchors.py     # the anchored specification bytes (Book I §8)
```

Deeper: `spec/book-1-truth.md` is ~250 lines and self-contained;
`spec/sigma-resume.md` builds on it. Adversarial
review is the development model: attack one exact claim, with a reproducer.
