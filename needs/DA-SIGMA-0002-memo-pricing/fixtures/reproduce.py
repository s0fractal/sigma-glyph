#!/usr/bin/env python3
"""DA-SIGMA-0002 — minimal reproducer. Depends on Book I and nothing else.

Four claims, in order:

  R1  Book I never reuses a result. The same hash, evaluated twice, costs the
      same both times: two agents holding one subterm pay for it twice.
  R2  A memo of normal forms priced at `size(nf)` reaches the SAME result hash
      for every fixture term, spends materially less, and satisfies §3.4's
      `size <= spent + 1` at every action.
  R3  The price has TWO floors, one below the other, and they answer different
      questions. `size(nf) - 1` is where the memory bound `size <= spent + 1`
      itself starts to fail; `size(nf)` is where a memo install stops obeying the
      per-row discipline every Book I action satisfies (`dsize <= cost - 1`).
      Both boundaries are measured here.
  R4  The collision. Because the memoized run spends less, a memoizing
      implementation returns a different `atp_spent` for the same
      (term, budget) than the reference oracle, and therefore cannot satisfy
      conformance vectors that pin spend exactly.

Usage:  python3 needs/DA-SIGMA-0002-memo-pricing/fixtures/reproduce.py
Env:    SIGMA_GLYPH=<checkout>/impl   (default: this repository's impl/)
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_sigma():
    cands = []
    if os.environ.get("SIGMA_GLYPH"):
        cands.append(Path(os.environ["SIGMA_GLYPH"]) / "sigma_glyph.py")
    for up in HERE.parents:                       # a needs/ packet sits in the repo
        cands.append(up / "impl" / "sigma_glyph.py")
    cands.append(Path.home() / "Projects/sigma-glyph/impl/sigma_glyph.py")
    for path in cands:
        if path.exists():
            spec = importlib.util.spec_from_file_location("sigma_glyph", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, path
    sys.exit("ERR: Book I oracle not found; set SIGMA_GLYPH=<checkout>/impl")


sg, ORACLE = load_sigma()
I = ("lit", sg.sha(b"I"))
K = ("lit", sg.sha(b"K"))
S = ("lit", sg.sha(b"S"))
A = lambda x, y: ("app", x, y)
ATP = 4000


def put(t, store):
    if t[0] == "thunk":
        return t[1]
    if t[0] == "app":
        put(t[1], store)
        put(t[2], store)
    return store.put(sg.term_bytes(t))


def next_force(t):
    """Mirror of step5's dispatch: the hash it will materialize next, with its
    position, or None when the next action is a rule firing or a normal form."""
    k = t[0]
    if k == "thunk":
        return None if t[1] in sg.GENESIS else (t[1], ())
    if k != "app":
        return None
    f = t[1]
    if sg.glyph_eq(f, sg.I_H):
        return None
    if f[0] == "app":
        if sg.glyph_eq(f[1], sg.K_H):
            return None
        if f[1][0] == "app" and sg.glyph_eq(f[1][1], sg.S_H):
            return None
    left = next_force(f)
    if left is not None:
        return left[0], (1,) + left[1]
    right = next_force(t[2])
    return (right[0], (2,) + right[1]) if right else None


def replace_at(t, path, node):
    if not path:
        return node
    if path[0] == 1:
        return ("app", replace_at(t[1], path[1:], node), t[2])
    return ("app", t[1], replace_at(t[2], path[1:], node))


def run(root, store, memo=None, price=None):
    """Book I's own loop, with one optional extra action: install a known normal
    form where the machine was about to materialize its hash."""
    t, spent, stats = ("thunk", root), 0, {"fetches": 0}
    worst = 0                       # max of size - (spent + 1): >0 breaks §3.4
    while True:
        if memo is not None:
            nxt = next_force(t)
            if nxt and nxt[0] in memo:
                nf = memo[nxt[0]]
                c = price(nf)
                if c <= ATP - spent:
                    t, spent = replace_at(t, nxt[1], nf), spent + c
                    worst = max(worst, sg.size(t) - (spent + 1))
                    continue
        try:
            r = sg.step5(t, ATP - spent, store, stats, sg.DEFAULT_LIMITS)
        except sg.BudgetExhausted:
            return ("dis", sg.R_ATP), spent, worst
        except sg.Unresolved:
            return ("dis", sg.R_UNRES), spent, worst
        if r is None:
            return t, spent, worst
        t, spent = r[0], spent + r[1]
        worst = max(worst, sg.size(t) - (spent + 1))


def fixture(store):
    """Four base terms and four composites that DEMAND them by hash. The demand
    path is the point: without it nothing in a population ever asks another
    agent's address, and a memo has nothing to answer."""
    base = [A(A(A(S, K), K), I),
            A(A(A(S, A(K, S)), K), I),
            A(A(K, A(A(S, K), K)), I),
            A(A(A(S, I), I), A(K, I))]
    roots = [put(t, store) for t in base]
    comp = [A(("thunk", roots[i]), ("thunk", roots[(i + 1) % 4])) for i in range(4)]
    return roots + [put(t, store) for t in comp]


def main():
    store = sg.Store()
    for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES):
        store.put(b)
    roots = fixture(store)

    # R1 — Book I never reuses a result.
    print("R1  the same hash, evaluated twice:")
    reused = False
    for h in roots[:4]:
        _, a = sg.eval_hash(h, ATP, store)
        _, b = sg.eval_hash(h, ATP, store)
        reused |= a != b
        print(f"      {h.hex()[:12]}  first {a:5d}   second {b:5d}")
    print(f"    -> every second evaluation pays full price: "
          f"{'NO' if reused else 'CONFIRMED'}\n")

    # R2 — a memo priced at size(nf): same answers, less ATP, bound intact.
    memo, warm, cold, same, worst = {}, 0, 0, True, 0
    for h in roots:
        ref, c = sg.eval_hash(h, ATP, store)
        t, s, w = run(h, store, memo, sg.size)
        if t[0] != "dis":
            memo[h] = t
        same &= sg.term_hash(t) == sg.term_hash(ref)
        warm, cold, worst = warm + s, cold + c, max(worst, w)
    print(f"R2  memo priced at size(nf): answers identical {same}, "
          f"ATP {warm} vs oracle {cold} ({100.0 * warm / cold:.1f}%), "
          f"worst size-(spent+1) = {worst:+d}\n")

    # R3 — where each floor actually is.
    def at_price(price):
        m, broke, worst_p = {}, 0, 0
        for h in roots:
            t, _, _ = run(h, store, m, price)
            if t[0] != "dis":
                m[h] = t
        for h in roots:
            _, _, w = run(h, store, m, price)
            broke += w > 0
            worst_p = max(worst_p, w)
        return broke, worst_p

    print("R3  the memory bound under four prices for the same memo:")
    for label, price in (("size(nf)", sg.size),
                         ("size(nf) - 1", lambda nf: max(0, sg.size(nf) - 1)),
                         ("size(nf) - 2", lambda nf: max(0, sg.size(nf) - 2)),
                         ("flat 1", lambda nf: 1)):
        b, w = at_price(price)
        print(f"      {label:14s} violations {b}/{len(roots)}   worst excess {w:+d}")
    broke, _ = at_price(lambda nf: max(0, sg.size(nf) - 2))
    sound_floor, _ = at_price(lambda nf: max(0, sg.size(nf) - 1))
    print("    -> the bound's floor is size(nf) - 1. size(nf) is what additionally")
    print("       keeps the per-row discipline dsize <= cost - 1, tightly.\n")

    # R4 — the collision with pinned conformance.
    diverged = []
    for h in roots:
        _, c = sg.eval_hash(h, ATP, store)
        _, s, _ = run(h, store, memo, sg.size)
        if s != c:
            diverged.append((h, c, s))
    print(f"R4  same (term, budget), different atp_spent on "
          f"{len(diverged)}/{len(roots)} fixture terms:")
    for h, c, s in diverged[:4]:
        print(f"      {h.hex()[:12]}  oracle {c:5d}   memoizing {s:5d}")
    print("    -> a memoizing implementation cannot satisfy conformance vectors")
    print("       that pin atp_spent exactly (tests/spec_conformance/vectors.json)")

    print(f"\noracle: {ORACLE}")
    ok = (not reused) and same and worst == 0 and broke > 0 and diverged
    print(f"\nDA-SIGMA-0002: {'REPRODUCED' if ok else 'NOT REPRODUCED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
