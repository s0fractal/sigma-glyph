import sys, hashlib
sys.path.insert(0, sys.argv[1] + "/impl")
import sigma_glyph as G
N = int(sys.argv[2]); S = G.Store(); L = G.DEFAULT_LIMITS
X, Y = ("lit", hashlib.sha256(b"x").digest()), ("lit", hashlib.sha256(b"y").digest())
leaves = [G.IG, G.KG, G.SG]
def trees(n):
    if n == 1: yield from leaves; return
    for k in range(1, n):
        for a in trees(k):
            for b in trees(n - k): yield ("app", a, b)
def enc(t):
    if t[0] == "app": return "(" + enc(t[1]) + " " + enc(t[2]) + ")"
    glyph = {G.I_H: "I", G.K_H: "K", G.S_H: "S"}.get(G.term_hash(t))
    if glyph: return glyph
    if t == X: return "x"
    if t == Y: return "y"
    return "?"
def nf(t, n=200):
    for _ in range(n):
        if G.size(t) > 300: return None
        r = G.step5(t, 10**9, S, {"fetches": 0}, L)
        if r is None: return t
        t = r[0]
    return None
want = enc(("app", Y, ("app", ("app", X, X), Y)))
hits = []
for n in range(1, N + 1):
    for T in trees(n):
        r = nf(("app", ("app", T, X), Y))
        if r is not None and enc(r) == want:
            hits.append(T)
print("candidates T with T x y ->> y (x x y):", len(hits))
for T in hits[:8]:
    t, seen, spent = ("app", ("app", T, T), G.IG), {}, 0
    res = "no cycle in 3000 steps"
    for i in range(3000):
        e = enc(t)
        if e in seen: res = f"CYCLE entry {seen[e][0]} period {i-seen[e][0]} cost {spent-seen[e][1]}"; break
        seen[e] = (i, spent)
        if G.size(t) > 2000: res = "grows"; break
        r = G.step5(t, 10**9, S, {"fetches": 0}, L)
        if r is None: res = "normal form"; break
        t, spent = r[0], spent + r[1]
    print(" T =", enc(T), "->", res)
