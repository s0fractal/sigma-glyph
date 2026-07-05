#!/usr/bin/env python3
"""Property-based conformance tests (stdlib-only, seeded => deterministic).

Properties are drawn from the multi-model reviews (Sonnet 4.5 P3.2):
  P1  serialization canonicity: ser(deser(b)) == b for every valid buffer
  P2  deser never crashes on arbitrary bytes; valid parses round-trip
  P3  eval is deterministic: same (hash, atp) -> same (result, spent), twice
  P4  ATP exactness: budget == spent reaches the same normal form;
      budget == spent-1 exhausts (when spent > 0)
  P5  normal forms are fixed points: re-eval of a result spends 0 ATP
  P6  C1 output is pure SKI (no var/lam) and compilation is deterministic

    python3 tests/spec_conformance/test_properties.py
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as sg  # noqa: E402

SEED = 0x516  # "Σ16"; fixed seed — change only with a rationale in the commit
rng = random.Random(SEED)

ok = []


def chk(name, cond, detail=""):
    ok.append(cond)
    if not cond:
        print("FAIL", name, detail)


# ---------- generators ----------
Ig, Kg, Sg = ("lit", sg.sha(b"I")), ("lit", sg.sha(b"K")), ("lit", sg.sha(b"S"))


def rand_ski(depth):
    if depth == 0 or rng.random() < 0.3:
        return rng.choice((Ig, Kg, Sg))
    return ("app", rand_ski(depth - 1), rand_ski(depth - 1))


def rand_lambda(depth, bound):
    r = rng.random()
    if depth == 0 or (r < 0.35 and bound):
        return ("var", rng.choice(bound)) if bound else ("lam", "x", ("var", "x"))
    if r < 0.6:
        v = f"v{len(bound)}"
        return ("lam", v, rand_lambda(depth - 1, bound + [v]))
    return ("lapp", rand_lambda(depth - 1, bound), rand_lambda(depth - 1, bound))


def rand_valid_node():
    op = rng.choice((sg.LITERAL, sg.REF, sg.APPLY, sg.DISSONANCE))
    flags = sg.FLAGS_REQ[op]
    fields = [rng.randbytes(32) for _ in range(bin(flags).count("1"))]
    if op == sg.LITERAL:
        return sg.ser(op, flags, atom=fields[0])
    if op in (sg.REF, sg.DISSONANCE):
        return sg.ser(op, flags, atom=fields[0])
    return sg.ser(op, flags, left=fields[0], right=fields[1])


def put_tree(t, st):
    if t[0] == "app":
        put_tree(t[1], st)
        put_tree(t[2], st)
    return st.put(sg.term_bytes(t))


# ---------- P1: canonicity round-trip on valid nodes ----------
for i in range(500):
    b = rand_valid_node()
    n = sg.deser(b)
    chk(f"P1[{i}] valid node parses", n is not None, b.hex())
    if n is not None:
        rt = sg.ser(n["op"], n["flags"], atom=n.get("atom"),
                    left=n.get("left"), right=n.get("right"))
        chk(f"P1[{i}] ser(deser(b)) == b", rt == b, b.hex())

# ---------- P2: deser total on arbitrary bytes; valid parses round-trip ----------
for i in range(2000):
    b = rng.randbytes(rng.randrange(0, 120))
    n = sg.deser(b)  # must not raise
    if n is not None:
        rt = sg.ser(n["op"], n["flags"], atom=n.get("atom"),
                    left=n.get("left"), right=n.get("right"))
        chk(f"P2[{i}] fuzz round-trip", rt == b, b.hex())
chk("P2 deser total (no crash on 2000 fuzz buffers)", True)

# ---------- P3/P4/P5: eval determinism, ATP exactness, fixed points ----------
BUDGET = 200
for i in range(150):
    st = sg.Store()
    t = rand_ski(rng.randrange(1, 6))
    h = put_tree(t, st)
    try:
        r1, s1 = sg.eval_hash(h, BUDGET, st)
        r2, s2 = sg.eval_hash(h, BUDGET, st)
    except sg.ResourceFault:
        continue  # local fault, non-canonical; not this test's subject
    chk(f"P3[{i}] eval deterministic",
        sg.term_hash(r1) == sg.term_hash(r2) and s1 == s2)
    if r1 == ("dis", sg.R_ATP):
        continue  # exhausted at BUDGET; exactness below needs a normal form
    r3, s3 = sg.eval_hash(h, s1, st)
    chk(f"P4[{i}] exact budget reaches same NF",
        sg.term_hash(r3) == sg.term_hash(r1) and s3 == s1)
    if s1 > 0:
        r4, _ = sg.eval_hash(h, s1 - 1, st)
        chk(f"P4[{i}] budget spent-1 exhausts", r4 == ("dis", sg.R_ATP))
    hr = put_tree(r1, st)
    r5, s5 = sg.eval_hash(hr, BUDGET, st)
    chk(f"P5[{i}] normal form is a fixed point (0 ATP)",
        sg.term_hash(r5) == sg.term_hash(r1) and s5 == 0)

# ---------- P6: C1 compiles closed lambda terms to pure SKI, deterministically ----------
def pure_ski(t):
    if t[0] == "app":
        return pure_ski(t[1]) and pure_ski(t[2])
    return t[0] == "lit"


for i in range(200):
    lt = ("lam", "v0", rand_lambda(rng.randrange(1, 5), ["v0"]))
    c1a, c1b = sg.c1(lt), sg.c1(lt)
    chk(f"P6[{i}] C1 output is pure SKI", pure_ski(c1a))
    chk(f"P6[{i}] C1 deterministic", sg.term_hash(c1a) == sg.term_hash(c1b))

n = len(ok)
print(f"{'PROPERTIES: ALL PASS' if all(ok) else 'PROPERTIES: FAILURES PRESENT'} ({sum(ok)}/{n}, seed=0x{SEED:x})")
sys.exit(0 if all(ok) else 1)
