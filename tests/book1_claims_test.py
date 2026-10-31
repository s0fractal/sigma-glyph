#!/usr/bin/env python3
"""Witnesses of Book I's claims (.warrant/claims.json): one case per observable a claim states.

Each case prints `ok   ID …` or `FAIL ID …` and the run exits non-zero on any FAIL. A case observes the
oracle (`impl/sigma_glyph.py`) through what the Book makes observable — bytes, hashes, a Receipt, a step's
price — and turns an exception into a wrong value, so a mutant that makes the oracle raise is seen on the
case's own assertion, never only as a crash. tests/claims_mutants.py names the mutants each claim cites.

    python3 tests/book1_claims_test.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "impl"))
import sigma_glyph as sg  # noqa: E402

failures = []


def check(case, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + case + ("" if ok else f" -- {detail}"))
    if not ok:
        failures.append(case)


def tried(f, *a):
    """f(*a), or the name of the exception it raised: a value a case can compare."""
    try:
        return f(*a)
    except Exception as e:  # noqa: BLE001  (any raise is a wrong answer here)
        return type(e).__name__


H = bytes.fromhex
APP = sg.F_LEFT | sg.F_RIGHT


def app(left, right):
    return sg.ser(sg.APPLY, APP, left=left, right=right)


def env_of(*nodes):
    return {sg.node_hash(b): b for b in nodes}


def receipt(top, env, atp=1000):
    """(result hash hex, spent, exit) of eval(top's hash, atp, env), or the exception's name."""
    r = tried(sg.eval_receipt, sg.node_hash(top), atp, env)
    return r if isinstance(r, str) else (r.result_hash.hex(), r.atp_spent, r.exit)


def forced(b):
    """What force() materializes from bytes b stored under their own hash."""
    return tried(sg.force, sg.node_hash(b), env_of(b), {"fetches": 0}, sg.DEFAULT_LIMITS)


def step_cost(term, env, remaining=1000):
    r = tried(sg.step5, term, remaining, env, {"fetches": 0}, sg.DEFAULT_LIMITS)
    return r if isinstance(r, str) or r is None else r[1]


ATOM = bytes(range(32))
I_HEX = "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162"
K_HEX = "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c"
S_HEX = "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6"
FALSE_HEX = "65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098"
INVALID_BYTES_HEX = "ff017cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8"
INVALID_HEX = "af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507"
I_H, K_H, S_H = H(I_HEX), H(K_HEX), H(S_HEX)

# §1.1, §4.1(2): flags
check("B101 a flag bit outside the mask 0x07 makes the buffer invalid",
      sg.deser(bytes([sg.LITERAL, 0x09]) + ATOM) is None and sg.deser(bytes([sg.APPLY, 0x0E]) + ATOM + ATOM) is None)
check("B102 flags must equal the opcode's: APPLY with F_ATOM set, LITERAL with F_LEFT set, are invalid",
      sg.deser(bytes([sg.APPLY, 0x07]) + ATOM * 3) is None and sg.deser(bytes([sg.LITERAL, 0x03]) + ATOM * 2) is None)
# §1.2, §4: an opcode outside the table degrades to the Canonical Invalid Object, never raises
bad = [bytes([op, 0x01]) + ATOM for op in (0x03, 0x10, 0xFE)]
check("B103 an opcode outside the table (0x03 included) materializes the Canonical Invalid Object",
      all(forced(b) == ("dis", sg.R_INVALID) for b in bad), [forced(b) for b in bad])
check("B104 the Canonical Invalid Object is ff01 || SHA-256(\"Invalid Object\"), with the Book's bytes and hash, and "
      "evaluating invalid bytes returns it as a normal form at the price of one materialization",
      sg.INVALID_OBJECT.hex() == INVALID_BYTES_HEX and sg.node_hash(sg.INVALID_OBJECT).hex() == INVALID_HEX
      and receipt(bad[0], env_of(bad[0])) == (INVALID_HEX, 1, "normal_form"), receipt(bad[0], env_of(bad[0])))
# §2: layout and identity
check("B105 the layout is [Op][Flags][Atom?][Left?][Right?], optional fields in the order Atom, Left, Right",
      app(I_H, K_H) == b"\x02\x06" + I_H + K_H and sg.K_BYTES == b"\x00\x01" + sg.sha(b"K"))
check("B106 NodeHash is SHA-256 of the canonical bytes: the genesis hashes and FALSE's are the Book's",
      [sg.node_hash(b).hex() for b in (sg.I_BYTES, sg.K_BYTES, sg.S_BYTES, sg.FALSE_BYTES)]
      == [I_HEX, K_HEX, S_HEX, FALSE_HEX])
# §4.1(3): length
check("B107 the length must equal 2 + 32·popcount(flags): one byte more or less is invalid",
      sg.deser(bytes([sg.LITERAL, 0x01]) + ATOM + b"\x00") is None and sg.deser(bytes([sg.LITERAL, 0x01]) + ATOM[:31]) is None
      and sg.deser(bytes([sg.LITERAL, 0x01]) + ATOM) is not None)
# §3.1: the rules
ik = app(I_H, K_H)
check("B108 R-I: APPLY(I, x) -> x (TV-4: 4 ATP: force the APPLY, fire R-I)",
      receipt(ik, env_of(ik)) == (K_HEX, 4, "normal_form"), receipt(ik, env_of(ik)))
ki = app(K_H, I_H)
kis = app(sg.node_hash(ki), S_H)
check("B109 R-K: APPLY(APPLY(K, x), y) -> x",
      receipt(kis, env_of(ki, kis))[::2] == (I_HEX, "normal_form"), receipt(kis, env_of(ki, kis)))
sk = app(S_H, K_H)
skk = app(sg.node_hash(sk), K_H)
skki = app(sg.node_hash(skk), I_H)
si = app(S_H, I_H)
sii = app(sg.node_hash(si), I_H)
siik = app(sg.node_hash(sii), K_H)
kk = sg.node_hash(app(K_H, K_H)).hex()
check("B110 R-S: S x y z -> x z (y z); S K K I reduces to I at TV-5's 12 ATP, and S I I K to K K (y z, not z y)",
      receipt(skki, env_of(sk, skk, skki)) == (I_HEX, 12, "normal_form")
      and receipt(siik, env_of(si, sii, siik))[::2] == (kk, "normal_form"),
      (receipt(skki, env_of(sk, skk, skki)), receipt(siik, env_of(si, sii, siik))))
ref2 = sg.ser(sg.REF, sg.F_ATOM, atom=I_H)
ref1 = sg.ser(sg.REF, sg.F_ATOM, atom=sg.node_hash(ref2))
one = tried(sg.step5, ("ref", sg.node_hash(ref2)), 1000, env_of(ref1, ref2), {"fetches": 0}, sg.DEFAULT_LIMITS)
check("B111 R-R unwraps one level per step: REF(h) steps to the thunk of h itself (not of what h refers to) at 1 ATP, "
      "and a chain REF -> REF -> I of length 2 costs 3·2 ATP (TV-9)",
      one == (("thunk", sg.node_hash(ref2)), 1) and receipt(ref1, env_of(ref1, ref2)) == (I_HEX, 6, "normal_form"),
      (one, receipt(ref1, env_of(ref1, ref2))))
# §3.2: identity by hash
lower_i = sg.ser(sg.LITERAL, sg.F_ATOM, atom=sg.sha(b"i"))
not_i = app(sg.node_hash(lower_i), K_H)
check("B112 a node is I/K/S only by its NodeHash: a LITERAL of another atom applied to K does not reduce",
      receipt(not_i, env_of(lower_i, not_i))[::2] == (sg.node_hash(not_i).hex(), "normal_form"),
      receipt(not_i, env_of(lower_i, not_i)))
# §3.3: laziness
missing = sg.sha(b"no such node")
k_i_missing = app(sg.node_hash(ki), missing)
check("B113 APPLY(APPLY(K, x), missing) -> x: the discarded argument is never demanded",
      receipt(k_i_missing, env_of(ki, k_i_missing))[::2] == (I_HEX, "normal_form"), receipt(k_i_missing, env_of(ki, k_i_missing)))
# §3.4: prices
lit = sg.ser(sg.LITERAL, sg.F_ATOM, atom=ATOM)
ref = sg.ser(sg.REF, sg.F_ATOM, atom=ATOM)
apl = app(ATOM, ATOM)
costs = [step_cost(("thunk", sg.node_hash(b)), env_of(b)) for b in (lit, ref, apl)]
check("B114 forcing a node costs its size with thunk children: 1 (LITERAL), 2 (REF), 3 (APPLY)", costs == [1, 2, 3], costs)
z = ("app", ("thunk", ATOM), ("thunk", ATOM))
s_redex = ("app", ("app", ("app", ("thunk", S_H), ("thunk", K_H)), ("thunk", K_H)), z)
check("B115 R-S costs 1 + size(z) in the current materialization: 4 for a materialized APPLY of two thunks",
      step_cost(s_redex, {}) == 4, step_cost(s_redex, {}))
short = receipt(skki, env_of(sk, skk, skki), atp=11)
check("B116 an action that costs more than what remains is not taken: S K K I at 11 ATP exhausts, never spending "
      "past its budget", short[0] == sg.node_hash(sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=sg.R_ATP)).hex()
      and short[2] == "atp_exhausted" and short[1] <= 11, short)
# §5.1: genesis
check("B117 a genesis hash is a normal form without materialization: eval(H(I)) with an empty environment is I at 0 ATP",
      tried(lambda: (lambda r: (r.result_hash.hex(), r.atp_spent, r.exit))(sg.eval_receipt(I_H, 10, {})))
      == (I_HEX, 0, "normal_form") and receipt(ik, env_of(ik))[2] == "normal_form",
      tried(lambda: tuple(sg.eval_receipt(I_H, 10, {}))))

print(f"\nBOOK1-CLAIMS: {'ALL PASS' if not failures else 'FAILURES ' + ' '.join(failures)}")
sys.exit(1 if failures else 0)
