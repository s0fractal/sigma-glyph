import sys, itertools
sys.path.insert(0, sys.argv[1] + "/impl")
import sigma_glyph as G
N = int(sys.argv[2])
S = G.Store(); L = G.DEFAULT_LIMITS
leaves = [G.IG, G.KG, G.SG]
def trees(n):
    if n == 1:
        yield from leaves; return
    for k in range(1, n):
        for a in trees(k):
            for b in trees(n - k):
                yield ("app", a, b)
def enc(t):
    if t[0] == "app": return b"(" + enc(t[1]) + enc(t[2]) + b")"
    if t[0] == "thunk": return b"T" + t[1]
    return {G.I_H: b"I", G.K_H: b"K", G.S_H: b"S"}.get(G.term_hash(t), b"?")
found = []
total = 0
for n in range(1, N + 1):
    for t0 in trees(n):
        total += 1
        t, seen = t0, {}
        for i in range(300):
            e = enc(t)
            if e in seen:
                found.append((enc(t0).decode(), seen[e], i - seen[e])); break
            seen[e] = i
            if G.size(t) > 400: break
            r = G.step5(t, 10**9, S, {"fetches": 0}, L)
            if r is None: break
            t = r[0]
print("terms:", total, "cycles:", len(found))
for f in found[:10]: print("  term", f[0], "enters cycle at step", f[1], "period", f[2])
