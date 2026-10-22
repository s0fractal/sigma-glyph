import sys
sys.path.insert(0, sys.argv[1] + "/impl")
import sigma_glyph as G
S = G.Store(); L = G.DEFAULT_LIMITS
V = lambda n: ("var", n); lam = lambda x, b: ("lam", x, b); ap = lambda f, a: ("lapp", f, a)
A = G.c1(lam("x", lam("y", ap(V("y"), ap(ap(V("x"), V("x")), V("y"))))))
def enc(t):
    if t[0] == "app": return "(" + enc(t[1]) + " " + enc(t[2]) + ")"
    if t[0] == "thunk": return "#" + t[1].hex()[:6]
    return {G.I_H: "I", G.K_H: "K", G.S_H: "S"}.get(G.term_hash(t), "?")
def store_term(t):
    if t[0] == "app": return S.put(G.ser(G.APPLY, G.F_LEFT | G.F_RIGHT, left=store_term(t[1]), right=store_term(t[2])))
    return G.term_hash(t)
print("A =", enc(A), "size", G.size(A))
for label, t0 in [("materialized A A I", ("app", ("app", A, A), G.IG)),
                  ("stored (thunk) A A I", ("thunk", store_term(("app", ("app", A, A), G.IG))))]:
    t, seen, spent = t0, {}, 0
    for i in range(2000):
        e = enc(t)
        if e in seen:
            print(label, ": CYCLE entry step", seen[e][0], "period", i - seen[e][0], "cycle cost", spent - seen[e][1]); break
        seen[e] = (i, spent)
        r = G.step5(t, 10**9, S, {"fetches": 0}, L)
        if r is None: print(label, ": normal form"); break
        t, spent = r[0], spent + r[1]
    else:
        print(label, ": no cycle in 2000 steps; final size", G.size(t))
