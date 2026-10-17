import sys, itertools, random
sys.path.insert(0, sys.argv[1] + "/impl")
import sigma_glyph as G

S = G.Store()
def put_app(l, r): return S.put(G.ser(G.APPLY, G.F_LEFT | G.F_RIGHT, left=l, right=r))
I, K, Sx = G.I_H, G.K_H, G.S_H
stats = lambda: {"fetches": 0}
L = G.DEFAULT_LIMITS

# B04: cold thunk vs materialized APPLY(I,K)
h = put_app(I, K)
cold = ("thunk", h)
warm, c = G.step5(cold, 10, S, stats(), L)
print("B04 same term_hash:", G.term_hash(cold) == G.term_hash(warm), "size", G.size(cold), G.size(warm), "force cost", c)
nxt = G.step5(warm, 10, S, stats(), L)
print("    next step cost", nxt[1], "result is K:", G.glyph_eq(nxt[0], K))

# Atomicity / determinism of the demanded action w.r.t. remaining budget:
# for many terms and states, step5 with remaining r either does the SAME action
# (same new term, same cost) as with a large budget, or raises BudgetExhausted
# with the state untouched. Never a different action.
def run_states(h0, n=60):
    t, out = ("thunk", h0), []
    for _ in range(n):
        out.append(t)
        try:
            r = G.step5(t, 10**9, S, stats(), L)
        except (G.Unresolved, G.BudgetExhausted):
            break
        if r is None: break
        t = r[0]
    return out

random.seed(7)
atoms = [I, K, Sx]
def rand_term(d):
    if d == 0 or random.random() < 0.3: return random.choice(atoms)
    return put_app(rand_term(d - 1), rand_term(d - 1))
bad = 0; checked = 0; cycles = []
import hashlib
def enc(t):
    k = t[0]
    if k == "thunk": return b"T" + t[1]
    if k == "app": return b"A" + enc(t[1]) + enc(t[2])
    return k.encode()[:1] + t[1]
for trial in range(400):
    h0 = rand_term(5)
    states = run_states(h0, 200)
    seen = {}
    for i, t in enumerate(states):
        e = enc(t)
        if e in seen:
            cycles.append((h0.hex()[:10], seen[e], i)); break
        seen[e] = i
    for t in states:
        full = G.step5(t, 10**9, S, stats(), L)
        if full is None: continue
        for r in range(0, full[1] + 1):
            checked += 1
            try:
                got = G.step5(t, r, S, stats(), L)
            except G.BudgetExhausted:
                if r >= full[1]: bad += 1
                continue
            if got is None or enc(got[0]) != enc(full[0]) or got[1] != full[1]: bad += 1
print("action-determinism checks:", checked, "violations:", bad)
print("state cycles found among 400 random terms (<=200 steps):", len(cycles), cycles[:5])
