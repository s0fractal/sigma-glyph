"""B/C/T measurement on real WPL policies (sigma-warrant redesign, review §6).

    python3 experiments/resume-probes/bct_measure.py <warrant checkout> [policy.wpl ...]

Compiles each policy with warrant's WPL compiler (SKI), rebuilds the term from
the emitted blobs, applies Turner's optimisations bottom-up
    S (K f) (K g) -> K (f g)    S (K f) I -> f    S (K f) g -> B f g    S f (K g) -> C f g
and reduces both to normal form from a cold thunk of the stored root (the
canonical start; a pre-materialized tree pays S's duplication on its full size
and overstates ATP ~25x): SKI under Book I's step5, the optimised term
under step5 plus B f g x -> f (g x) and C f g x -> f x g at cost 1 each (they
duplicate nothing). Reports answer agreement, term size and ATP.
T is not produced by these rewrites and is not measured.
"""
import hashlib
import sys
from pathlib import Path

WARRANT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WARRANT / "impl"))
import policy_lang as PL                    # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "impl"))
import sigma_glyph as G                     # noqa: E402  Book I evaluator of this checkout
lit = lambda n: ("lit", hashlib.sha256(n).digest())
B, C = lit(b"B"), lit(b"C")
L = dict(G.DEFAULT_LIMITS, max_materialized_nodes=10**7, max_node_depth=100000)


def rebuild(h, blobs, memo):
    if h in memo:
        return memo[h]
    if h in G.GENESIS:
        t = {G.I_H: G.IG, G.K_H: G.KG, G.S_H: G.SG}[h]
    else:
        n = G.deser(blobs[h.hex()])
        t = ("lit", n["atom"]) if n["op"] == G.LITERAL else \
            ("app", rebuild(n["left"], blobs, memo), rebuild(n["right"], blobs, memo))
    memo[h] = t
    return t


def is_(t, g):
    return t[0] == "lit" and t[1] == g[1]


def turner(t):
    if t[0] != "app":
        return t
    t = ("app", turner(t[1]), turner(t[2]))
    f, g = t[1], t[2]
    if f[0] == "app" and is_(f[1], G.SG):
        a = f[2]
        ka = a[0] == "app" and is_(a[1], G.KG)
        kg = g[0] == "app" and is_(g[1], G.KG)
        if ka and kg:
            return ("app", G.KG, ("app", a[2], g[2]))
        if ka and is_(g, G.IG):
            return a[2]
        if ka:
            return ("app", ("app", B, a[2]), g)
        if kg:
            return ("app", ("app", C, a), g[2])
    return t


def is_g(t, g):
    """B/C as a materialized literal or as an unforced thunk of its literal node."""
    return G.glyph_eq(t, G.node_hash(G.ser(G.LITERAL, G.F_ATOM, atom=g[1])))


def store_term(t, store):
    if t[0] == "app":
        return store.put(G.ser(G.APPLY, G.F_LEFT | G.F_RIGHT, left=store_term(t[1], store), right=store_term(t[2], store)))
    return store.put(G.ser(G.LITERAL, G.F_ATOM, atom=t[1]))


def bc_step(t, r, store, stats):
    if t[0] != "app":
        return G.step5(t, r, store, stats, L)
    f, x = t[1], t[2]
    if f[0] == "app" and f[1][0] == "app":
        if is_g(f[1][1], B):
            if r < 1: raise G.BudgetExhausted()
            return ("app", f[1][2], ("app", f[2], x)), 1
        if is_g(f[1][1], C):
            if r < 1: raise G.BudgetExhausted()
            return ("app", ("app", f[1][2], x), f[2]), 1
    h = G._head_reduction(f, x, r)
    if h is not G._NO_REDUCTION:
        return h
    for i in (1, 2):
        s = bc_step(t[i], r, store, stats)
        if s:
            return (("app", s[0], t[2]) if i == 1 else ("app", t[1], s[0])), s[1]
    return None


def nf(t, step):
    spent, peak = 0, G.size(t)
    while True:
        s = step(t)
        if s is None:
            return t, spent, peak
        t, spent = s[0], spent + s[1]
        peak = max(peak, G.size(t))


def main():
    sys.setrecursionlimit(1_000_000)
    files = [Path(p) for p in sys.argv[2:]] or sorted((WARRANT / "examples" / "policies").glob("[0-9]*.wpl"))
    print(f"{'policy':28} {'size SKI':>9} {'size BC':>8} {'ATP SKI':>8} {'ATP BC':>7} {'peak SKI':>9} {'peak BC':>8}  answer")
    for f in files:
        blobs = {}
        c = PL.compile_source(f.read_text(), lambda b, blobs=blobs: blobs.setdefault(hashlib.sha256(b).hexdigest(), b) and hashlib.sha256(b).hexdigest())
        import json
        doc = json.loads(blobs[c.blob])
        ski = rebuild(bytes.fromhex(doc["term"]), blobs, {})
        opt = turner(ski)
        # Canonical start: a cold thunk of the stored root (Book I), not a pre-materialized tree.
        store = G.Store()
        h1, h2 = store_term(ski, store), store_term(opt, store)
        st = {"fetches": 0}
        r1, a1, p1 = nf(("thunk", h1), lambda t, store=store, st=st: G.step5(t, 10**12, store, st, L))
        r2, a2, p2 = nf(("thunk", h2), lambda t, store=store, st=st: bc_step(t, 10**12, store, st))
        same = G.term_hash(r1) == G.term_hash(r2)
        print(f"{f.name[:28]:28} {G.size(ski):9} {G.size(opt):8} {a1:8} {a2:7} {p1:9} {p2:8}  "
              f"{'same' if same else 'DIFFERENT'} ({'TRUE' if G.glyph_eq(r1, G.K_H) else 'FALSE/other'})")


if __name__ == "__main__":
    main()
