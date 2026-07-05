"""Sigma-GLYPH v0.3.1 — Reference Implementation, Book I (Milestone 1).

Scope: SigmaNodeV2 canonical serialization/deserialization, validation,
SHA-256 NodeHash, CAS object store, genesis I/K/S, normal-order SKI
evaluator with ATP accounting, resolution contract, resource guards.
No waves. No pantheon. No agents. (Book II is another milestone.)
"""
import hashlib

sha = lambda b: hashlib.sha256(b).digest()

# ---------- OpCodes / Flags ----------
LITERAL, REF, APPLY, RESERVED, DISSONANCE = 0x00, 0x01, 0x02, 0x03, 0xFF
F_ATOM, F_LEFT, F_RIGHT = 0x01, 0x02, 0x04
FLAGS_REQ = {LITERAL: F_ATOM, REF: F_ATOM, APPLY: F_LEFT | F_RIGHT, DISSONANCE: F_ATOM}

# ---------- Reason hashes ----------
R_INVALID = sha(b"Invalid Object")
R_ATP     = sha(b"ATP Exhausted")
R_UNRES   = sha(b"Unresolved Reference")

# ---------- Canonical serialization ----------
def ser(op, flags, atom=None, left=None, right=None):
    b = bytes([op, flags])
    for f in (atom, left, right):
        if f is not None:
            assert len(f) == 32
            b += f
    return b

def node_hash(b): return sha(b)

def deser(buf):
    """Validate + parse. Returns dict or None (caller maps None -> Invalid Object)."""
    if len(buf) < 2: return None
    op, flags = buf[0], buf[1]
    if flags & ~0x07: return None
    if op not in FLAGS_REQ: return None            # covers RESERVED 0x03
    if flags != FLAGS_REQ[op]: return None
    exp = 2 + 32 * bin(flags & 0x07).count("1")
    if len(buf) != exp: return None
    out, off = {"op": op, "flags": flags}, 2
    for bit, name in ((F_ATOM, "atom"), (F_LEFT, "left"), (F_RIGHT, "right")):
        if flags & bit:
            out[name] = buf[off:off + 32]; off += 32
    return out

INVALID_OBJECT = ser(DISSONANCE, F_ATOM, atom=R_INVALID)

# ---------- Genesis ----------
I_BYTES = ser(LITERAL, F_ATOM, atom=sha(b"I"))
K_BYTES = ser(LITERAL, F_ATOM, atom=sha(b"K"))
S_BYTES = ser(LITERAL, F_ATOM, atom=sha(b"S"))
I_H, K_H, S_H = map(node_hash, (I_BYTES, K_BYTES, S_BYTES))
FALSE_BYTES = ser(APPLY, F_LEFT | F_RIGHT, left=K_H, right=I_H)
FALSE_H = node_hash(FALSE_BYTES)

# ---------- CAS ----------
class Store:
    def __init__(self): self.m = {}
    def put(self, b):
        h = node_hash(b); self.m[h] = b; return h
    def get(self, h): return self.m.get(h)  # None => unresolved

class ResourceFault(Exception):
    """Local, NON-canonical implementation fault (limits breached). Not a DISSONANCE."""

# ---------- Terms (tree semantics) ----------
# term := ("lit", atom) | ("ref", h) | ("app", t, t) | ("dis", reason)
def load(h, store, stats, limits):
    stats["fetches"] += 1
    if stats["fetches"] > limits["max_store_fetches"]: raise ResourceFault("fetches")
    b = store.get(h)
    if b is None: return None
    n = deser(b)
    if n is None: return ("dis", R_INVALID)  # malformed bytes in store
    op = n["op"]
    if op == LITERAL:    return ("lit", n["atom"])
    if op == REF:        return ("ref", n["atom"])
    if op == DISSONANCE: return ("dis", n["atom"])
    l = load(n["left"], store, stats, limits)
    r = load(n["right"], store, stats, limits)
    if l is None or r is None: return None
    return ("app", l, r)

def term_bytes(t):
    if t[0] == "lit": return ser(LITERAL, F_ATOM, atom=t[1])
    if t[0] == "ref": return ser(REF, F_ATOM, atom=t[1])
    if t[0] == "dis": return ser(DISSONANCE, F_ATOM, atom=t[1])
    return ser(APPLY, F_LEFT | F_RIGHT, left=term_hash(t[1]), right=term_hash(t[2]))

def term_hash(t): return node_hash(term_bytes(t))

def size(t):
    return 1 if t[0] != "app" else 1 + size(t[1]) + size(t[2])
def depth(t):
    return 1 if t[0] != "app" else 1 + max(depth(t[1]), depth(t[2]))

def is_glyph(t, gh): return term_hash(t) == gh   # Identity by Hash, even in semantics

# ---------- Normal-order stepper ----------
class Unresolved(Exception): pass

def step(t, store, stats, limits):
    """One leftmost-outermost step. Returns new term or None (normal form)."""
    kind = t[0]
    if kind == "ref":
        nt = load(t[1], store, stats, limits)
        if nt is None: raise Unresolved()
        return nt                                            # R-R, 1 ATP
    if kind == "app":
        f, a = t[1], t[2]
        if is_glyph(f, I_H):                                  # R-I
            return a
        if f[0] == "app" and is_glyph(f[1], K_H):             # R-K
            return f[2]
        if (f[0] == "app" and f[1][0] == "app"
                and is_glyph(f[1][1], S_H)):                  # R-S
            x, y, z = f[1][2], f[2], a
            return ("app", ("app", x, z), ("app", y, z))
        nf = step(f, store, stats, limits)
        if nf is not None: return ("app", nf, a)
        na = step(a, store, stats, limits)
        if na is not None: return ("app", f, na)
        return None
    return None  # lit / dis are normal forms

DEFAULT_LIMITS = dict(max_node_depth=4096, max_materialized_nodes=1_000_000,
                      max_store_fetches=1_000_000)

def eval_hash(h, atp, store, limits=None):
    """eval(term_hash, atp) -> (result_term, atp_spent).
    Canonical outcomes: normal form | DISSONANCE(ATP Exhausted) | DISSONANCE(Unresolved Reference).
    Resource limit breach -> ResourceFault (local, non-canonical)."""
    limits = limits or DEFAULT_LIMITS
    stats = {"fetches": 0}
    t = load(h, store, stats, limits)
    if t is None: return ("dis", R_UNRES), 0
    spent = 0
    while True:
        if depth(t) > limits["max_node_depth"] or size(t) > limits["max_materialized_nodes"]:
            raise ResourceFault("term growth")
        try:
            nt = step(t, store, stats, limits)
        except Unresolved:
            return ("dis", R_UNRES), spent
        if nt is None:
            return t, spent                                   # normal form
        spent += 1
        t = nt
        if spent >= atp and step(t, store, stats, limits) is not None:
            return ("dis", R_ATP), spent
        if spent > atp:
            return ("dis", R_ATP), spent



# ---------- Canonical Lambda->SKI Compiler, Profile C1 ----------
# lambda term := ("var", name) | ("lam", name, body) | ("lapp", f, a) | SKI term (passthrough)
IG, KG, SG = ("lit", sha(b"I")), ("lit", sha(b"K")), ("lit", sha(b"S"))

def _fv(t):
    k = t[0]
    if k == "var": return {t[1]}
    if k == "lam": return _fv(t[2]) - {t[1]}
    if k in ("lapp", "app"): return _fv(t[1]) | _fv(t[2])
    return set()

def c1(t):
    k = t[0]
    if k == "var": return t
    if k == "lapp": return ("app", c1(t[1]), c1(t[2]))
    if k == "lam": return _abstract(t[1], c1(t[2]))
    return t  # SKI passthrough

def _abstract(x, m):
    if m == ("var", x): return IG                                   # A-1
    if x not in _fv(m): return ("app", KG, m)                       # A-2
    if m[0] == "app":                                                # A-3
        return ("app", ("app", SG, _abstract(x, m[1])), _abstract(x, m[2]))
    raise ValueError("free variable escapes abstraction")

# ---------- Test suite ----------
def run_tests():
    st = Store()
    for b in (I_BYTES, K_BYTES, S_BYTES, FALSE_BYTES): st.put(b)

    A = lambda l, r: ("app", l, r)
    Ig, Kg, Sg = ("lit", sha(b"I")), ("lit", sha(b"K")), ("lit", sha(b"S"))

    def put_tree(t):
        if t[0] == "app": put_tree(t[1]); put_tree(t[2])
        return st.put(term_bytes(t))

    ok = []
    def chk(name, cond): ok.append(cond); print(("OK  " if cond else "FAIL"), name)

    # Genesis hashes
    chk("I hash",     I_H.hex() == "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162")
    chk("K hash",     K_H.hex() == "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c")
    chk("S hash",     S_H.hex() == "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6")
    chk("FALSE hash", FALSE_H.hex() == "65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098")

    # Validation / negative
    chk("invalid: flags high bits", deser(bytes([0x00, 0x09]) + b"\x00"*32) is None)
    chk("invalid: reserved 0x03",   deser(bytes([0x03, 0x02]) + b"\x00"*32) is None)
    chk("invalid: bad length",      deser(bytes([0x02, 0x06]) + b"\x00"*33) is None)
    chk("invalid object bytes",     INVALID_OBJECT.hex() ==
        "ff01" + R_INVALID.hex())

    # TV2-4: APPLY(I,K) -> K in 1 ATP; budget 0 -> ATP Exhausted
    h = put_tree(A(Ig, Kg))
    r, sp = eval_hash(h, 1, st);  chk("I·K -> K (1 ATP)", term_hash(r) == K_H and sp == 1)
    r, sp = eval_hash(h, 0, st);  chk("I·K budget 0 -> ATP",  r == ("dis", R_ATP))

    # TV2-5: SKK·I -> I in 2 ATP
    h = put_tree(A(A(A(Sg, Kg), Kg), Ig))
    r, sp = eval_hash(h, 10, st); chk("SKK·I -> I (2 ATP)", term_hash(r) == I_H and sp == 2)
    r, sp = eval_hash(h, 1, st);  chk("SKK·I budget 1 -> ATP", r == ("dis", R_ATP))

    # TV2-6 (new): duplication cost — T = S I I (I K), tree semantics
    T = A(A(A(Sg, Ig), Ig), A(Ig, Kg))
    hT = put_tree(T)
    r, sp = eval_hash(hT, 100, st)
    nf = term_hash(r)
    print("      SII(IK): normal form =", "APPLY(K,K)" if nf == node_hash(
        ser(APPLY, 0x06, left=K_H, right=K_H)) else nf.hex(), "| ATP =", sp,
        "| T hash =", hT.hex())
    chk("SII(IK) normal form APPLY(K,K)", nf == node_hash(ser(APPLY, 0x06, left=K_H, right=K_H)))

    # TV2-7 (new): Omega = SII(SII) — non-terminating, deterministic exhaustion
    W = A(A(Sg, Ig), Ig)
    Om = A(W, W)
    hO = put_tree(Om)
    r, sp = eval_hash(hO, 50, st)
    print("      Omega hash =", hO.hex(), "| result:", "ATP Exhausted" if r == ("dis", R_ATP) else r)
    chk("Omega -> ATP Exhausted", r == ("dis", R_ATP))

    # TV2-8 (new): unresolved child — APPLY(I, missing)
    ghost = sha(b"this node was never stored")
    hb = st.put(ser(APPLY, 0x06, left=I_H, right=ghost))
    r, sp = eval_hash(hb, 10, st)
    chk("missing child -> Unresolved Reference", r == ("dis", R_UNRES))

    # REF chain: REF -> REF -> K, costs 2 ATP
    r1 = st.put(ser(REF, F_ATOM, atom=K_H))
    r2 = st.put(ser(REF, F_ATOM, atom=r1))
    r, sp = eval_hash(r2, 10, st)
    chk("REF chain -> K (2 ATP)", term_hash(r) == K_H and sp == 2)


    # TV2-10 (C1 canonical compiler)
    lam_id = ("lam", "x", ("var", "x"))
    chk("C1[lx.x] = I", term_hash(c1(lam_id)) == I_H)
    lam_k = ("lam", "x", ("lam", "y", ("var", "x")))
    ck = c1(lam_k)   # expected S (K K) I
    exp = A(A(Sg, A(Kg, Kg)), Ig)
    chk("C1[lxy.x] = S(KK)I", term_hash(ck) == term_hash(exp))
    print("      C1[lxy.x] hash =", term_hash(ck).hex())
    # behaves as K: (C1[lxy.x] S) K -> S
    ht = put_tree(A(A(ck, Sg), Kg))
    r, sp = eval_hash(ht, 16, st)
    chk("C1[lxy.x] S K -> S", term_hash(r) == S_H)
    print("      C1 K-behavior ATP =", sp)

    # Resource guard: tiny depth limit trips as FAULT, not dissonance
    try:
        eval_hash(hO, 10_000, st, limits=dict(max_node_depth=8,
                  max_materialized_nodes=10**6, max_store_fetches=10**6))
        chk("resource fault raised", False)
    except ResourceFault:
        chk("resource fault raised (non-canonical)", True)

    print("\nALL PASS" if all(ok) else "\nFAILURES PRESENT")
    return all(ok)

if __name__ == "__main__":
    run_tests()
