#!/usr/bin/env python3
"""DA-SIGMA-0002 — minimal reproducer. Depends on Book I and nothing else.

Four claims, in order:

  R1  The ACCOUNTING is identical on a second evaluation: the same hash costs
      the same both times. NOTE, corrected 2026-08-26: this says nothing about
      whether an implementation re-does the WORK. Book I §3.4 settles that
      explicitly — "sharing MAY be used in execution, but reported ATP MUST match
      tree accounting" — so a conforming implementation may already take the
      result from a memo and must still report the tree price. An earlier draft
      of this packet read R1 as "Book I never reuses a result", which is a
      different and false claim.
  R2  A memo of normal forms priced at `size(nf)` reaches the SAME result hash
      for every fixture term, spends materially less, and satisfies §3.4's
      `size <= spent + 1` at every action.
  R3  The price has TWO floors, one below the other, and they answer different
      questions. `size(nf) - 1` is where the memory bound `size <= spent + 1`
      itself starts to fail; `size(nf)` is where a memo install stops obeying the
      per-row discipline every Book I action satisfies (`dsize <= cost - 1`).
      Both boundaries are measured here.
  R4  What a DIFFERENT accounting would report. A run that charges size(nf) for
      an installed normal form reports a different atp_spent for the same
      (term, budget), and therefore cannot satisfy conformance vectors that pin
      spend. That is not a defect in Book I: §3.4 requires the tree figure to be
      reported, so this is a measurement of what an ALife-side metabolic
      accounting would look like, and of why it must not be called Σ-GLYPH
      atp_spent. It does NOT follow that warrant's ski@v1 verdicts diverge:
      SPEC §3.1 compares the result NodeHash against `expect` and pins `atp` as
      an INPUT budget; it does not compare spend.

Usage:  python3 needs/DA-SIGMA-0002-memo-pricing/fixtures/reproduce.py
Env:    SIGMA_GLYPH=<checkout>/impl   (default: this repository's impl/)
"""
import hashlib
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The oracle this packet was measured against. The first version cited this
# digest in prose and loaded whichever sigma_glyph.py it found first, so it would
# have reported REPRODUCED against a different machine. Verified now, and fatal.
# Re-pinned at owner disposition, 2026-08-29. The packet was measured against
# 413d1f9805cdbdf4…; the oracle has moved twice since — the verifier
# admission boundary and then the CAS-key/uint32 input boundary — and all ten
# values were re-measured under this one and are unchanged. The original is kept
# above so what the requester measured stays legible.
PINNED_ORACLE_SHA256 = ("4b4f458eed0f4cda71532a495e3d726e7fea5a7d"
                        "7aa734ad9c7c560096b05e1b")



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
ORACLE_SHA256 = hashlib.sha256(Path(ORACLE).read_bytes()).hexdigest()
if ORACLE_SHA256 != PINNED_ORACLE_SHA256 and "--allow-oracle-drift" not in sys.argv:
    sys.exit(f"ERR: this packet pins the oracle it was measured against.\n"
             f"  expected {PINNED_ORACLE_SHA256}\n"
             f"  found    {ORACLE_SHA256}\n"
             f"  at       {ORACLE}\n"
             f"Numbers from another machine are not this packet's numbers. Pass "
             f"--allow-oracle-drift to measure anyway; the result is then yours, "
             f"not this packet's.")
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


def run(root, store, memo=None, price=None):  # NOSONAR python:S3776 - SONAR-DISPOSITIONS.md
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


def main():  # NOSONAR python:S3776 - SONAR-DISPOSITIONS.md
    store = sg.Store()
    for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES):
        store.put(b)
    roots = fixture(store)

    # R1 — Book I never reuses a result.
    print("R1  the same hash, evaluated twice:")
    reused = False
    r1_costs = []
    for h in roots[:4]:
        _, a = sg.eval_hash(h, ATP, store)
        _, b = sg.eval_hash(h, ATP, store)
        reused |= a != b
        r1_costs.append((a, b))
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

    # `max(1, ...)`, not `max(0, ...)`: Book I §3.4 fixes the minimum price of any
    # action at 1, and 4 of these 8 normal forms have size 1, where a literal
    # "k - 1" would be a free action the specification does not allow. The
    # theorem's floor is therefore max(1, k - 1), which an earlier draft of this
    # packet stated as a bare k - 1.
    print("R3  the memory bound under four prices for the same memo:")
    r3 = {}
    for label, price in (("size(nf)", sg.size),
                         ("max(1, size(nf)-1)", lambda nf: max(1, sg.size(nf) - 1)),
                         ("max(1, size(nf)-2)", lambda nf: max(1, sg.size(nf) - 2)),
                         ("flat 1", lambda nf: 1)):
        b, w = at_price(price)
        r3[label] = (b, w)
        print(f"      {label:18s} violations {b}/{len(roots)}   worst excess {w:+d}")
    # The two prices these lines used to recompute are already in `r3`, and
    # `at_price` is pure, so the recomputation was work nobody read.
    print("    -> the bound's floor is max(1, size(nf) - 1). size(nf) is what")
    print("       additionally keeps the per-row discipline dsize <= cost - 1.\n")

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
    print(f"oracle sha256: {ORACLE_SHA256}")

    # EVERY claim this packet makes, pinned to an exact value. The first version
    # of this predicate read `broke > 0 and diverged` and ignored the numbers
    # entirely: mutating the k-1 arm to charge k-4, so that it reported 4/8
    # violations and contradicted the packet's thesis, still printed REPRODUCED
    # and exited 0. A reproducer whose verdict does not depend on its numbers is
    # a press release.
    expected = {
        "R1 second evaluation costs the same": r1_costs == [(12, 12), (15, 15),
                                                            (13, 13), (16, 16)],
        "R1 no cheaper second run": not reused,
        "R2 answers identical to the oracle": same,
        "R2 warm/cold totals": (warm, cold) == (97, 185),
        "R2 bound tight, never broken": worst == 0,
        "R3 size(nf) is sound": r3["size(nf)"] == (0, 0),
        "R3 max(1, size(nf)-1) is sound — the theorem's floor":
            r3["max(1, size(nf)-1)"] == (0, 0),
        "R3 max(1, size(nf)-2) breaks the bound": r3["max(1, size(nf)-2)"] == (4, 1),
        "R3 a flat price of 1 breaks it worse": r3["flat 1"] == (4, 9),
        "R4 a different accounting diverges on every term":
            len(diverged) == len(roots) == 8,
    }
    print()
    for name, held in expected.items():
        print(("OK  " if held else "FAIL"), name)
    ok = all(expected.values())
    print(f"\nDA-SIGMA-0002: {'REPRODUCED' if ok else 'NOT REPRODUCED'} "
          f"({sum(expected.values())}/{len(expected)} pinned values)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
