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

class Counting(dict):
    """An environment that counts how often it is read."""
    reads = 0

    def get(self, k, d=None):
        Counting.reads += 1
        return super().get(k, d)


def reads_of(f, *a):
    """(what f(*a) returned or raised, how many environment reads it made)."""
    Counting.reads = 0
    got = tried(f, *a)
    return got, Counting.reads


ghost = sg.sha(b"this node was never stored")
i_ghost = app(I_H, ghost)
dis_atp = sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=sg.R_ATP)
omega_half = app(sg.node_hash(sii), sg.node_hash(sii))   # (S I I)(S I I)
omega_env = env_of(si, sii, omega_half)

# §3.4: the interface and the Receipt
exits = [receipt(ik, env_of(ik))[2], receipt(skki, env_of(sk, skk, skki), atp=11)[2], receipt(i_ghost, env_of(i_ghost))[2]]
r_dict = tried(lambda: sorted(sg.eval_receipt(sg.node_hash(ik), 10, env_of(ik)).as_dict()))
foreign_exit = tried(sg.Receipt, ("lit", ATOM), 0, "finished")
check("B201 a Receipt is {exit, result_hash, atp_spent}, its exit one of normal_form, atp_exhausted, unresolved_reference "
      "and no other", exits == ["normal_form", "atp_exhausted", "unresolved_reference"]
      and r_dict == ["atp_spent", "exit", "result_hash"] and foreign_exit == "ValueError", (exits, r_dict, foreign_exit))
stored = receipt(dis_atp, env_of(dis_atp))
exhausted = receipt(skki, env_of(sk, skk, skki), atp=11)
check("B202 the same result_hash can be a normal form or an exhaustion: a stored DISSONANCE(ATP Exhausted) evaluates to "
      "itself with exit normal_form", stored[0] == exhausted[0] and stored[2] == "normal_form" and exhausted[2] == "atp_exhausted",
      (stored, exhausted))
out_of_domain = [reads_of(sg.eval_receipt, sg.node_hash(ik), atp, Counting(env_of(ik)))
                 for atp in (2 ** 32, -1, True, 1.5, 2 ** 64)]
edges = [tried(lambda n=n: tuple(sg.eval_receipt(I_H, n, {}))[1]) for n in (0, 2 ** 32 - 1)]
check("B203 an ATP budget outside uint32 is refused locally (ValueError), before the environment is read, never clamped; "
      "0 and 2^32-1 are budgets", all(got == "ValueError" and n == 0 for got, n in out_of_domain) and edges == [0, 0],
      (out_of_domain, edges))
ref_missing = sg.ser(sg.REF, sg.F_ATOM, atom=sg.sha(b"missing"))
zero = reads_of(lambda: (lambda r: (r.exit, r.atp_spent))(sg.eval_receipt(sg.node_hash(ref_missing), 0, Counting(env_of(ref_missing)))))
check("B204 at spent == atp exhaustion is decided before any store access: eval(REF(missing), 0) = ATP Exhausted, spent 0, "
      "no read", zero == (("atp_exhausted", 0), 0), zero)
tv8 = receipt(i_ghost, env_of(i_ghost))
check("B205 a failed resolve is not charged: APPLY(I, ghost) is Unresolved Reference at 4 ATP (TV-8)",
      tv8 == (sg.node_hash(sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=sg.R_UNRES)).hex(), 4, "unresolved_reference"), tv8)
omega = [receipt(omega_half, omega_env, atp=n)[2] for n in (0, 1, 7, 100, 1000)]
check("B206 eval is total: Omega at budgets 0, 1, 7, 100, 1000 returns DISSONANCE(ATP Exhausted), never an exception (TV-7)",
      omega == ["atp_exhausted"] * 5
      and sg.node_hash(omega_half).hex() == "0609d7e3bac2c6927c34ade51c7d6728a75c6ac0206fdb184524843b4fb94211", omega)


def bound_holds(top, env, atp):
    """Whether materialized_size(t) - 1 <= spent at every step of eval(top, atp)."""
    t, spent, stats = ("thunk", sg.node_hash(top)), 0, {"fetches": 0}
    while True:
        r = tried(sg.step5, t, atp - spent, env, stats, sg.DEFAULT_LIMITS)
        if r is None or isinstance(r, str):
            return True
        t, spent = r[0], spent + r[1]
        if sg.size(t) - 1 > spent:
            return False


tv6 = app(sg.node_hash(sii), sg.node_hash(ik))       # S I I (I K)
check("B207 along every execution materialized_size(t) - 1 <= spent: TV-6 (S I I (I K)) and Omega, step by step",
      bound_holds(tv6, env_of(si, sii, ik, tv6), 1000) and bound_holds(omega_half, omega_env, 500)
      and receipt(tv6, env_of(si, sii, ik, tv6))[1:] == (21, "normal_form"))
# §3.5: the content environment
foreign = {sg.node_hash(ik): sg.K_BYTES}
not_bytes = {sg.node_hash(ik): bytearray(ik)}
check("B208 bytes under a key they do not hash to are not executed as that key's node, nor is a value that is not bytes: "
      "a local refusal, no Receipt", tried(sg.eval_receipt, sg.node_hash(ik), 10, foreign) == "ResourceFault"
      and tried(sg.eval_receipt, sg.node_hash(ik), 10, not_bytes) == "ResourceFault",
      (tried(sg.eval_receipt, sg.node_hash(ik), 10, foreign), tried(sg.eval_receipt, sg.node_hash(ik), 10, not_bytes)))
extra = {**env_of(ki, k_i_missing), sg.sha(b"unrelated"): b"\x03\x01" + ATOM, sg.sha(b"wrong key"): sg.I_BYTES}
check("B209 an entry the execution never demands changes no Receipt (even an invalid one, or one under a foreign key)",
      receipt(k_i_missing, extra) == receipt(k_i_missing, env_of(ki, k_i_missing)), receipt(k_i_missing, extra))
check("B210 adding content changes only an unresolved_reference exit: a settled normal_form or atp_exhausted Receipt stays",
      receipt(skki, {**env_of(sk, skk, skki), **env_of(lit, ref, apl)}) == receipt(skki, env_of(sk, skk, skki))
      and receipt(skki, {**env_of(sk, skk, skki), **env_of(lit)}, atp=11) == receipt(skki, env_of(sk, skk, skki), atp=11))
check("B211 a demanded hash that is neither stored nor a genesis axiom gives DISSONANCE(Unresolved Reference)",
      tv8[2] == "unresolved_reference" and tv8[0] == sg.node_hash(sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=H(
          "75daae55453d9a98bfadb847d70b73fdd0be91d3b6ef8511d22fc42aa2c7c8e2"))).hex(), tv8)
# §3.6: local refusals are not results
tight = dict(sg.DEFAULT_LIMITS, max_store_fetches=2)
check("B212 a local resource limit breached during eval is a ResourceFault, never serialized as a DISSONANCE",
      tried(sg.eval_receipt, sg.node_hash(skki), 100, env_of(sk, skk, skki), tight) == "ResourceFault",
      tried(sg.eval_receipt, sg.node_hash(skki), 100, env_of(sk, skk, skki), tight))
policy = dict(sg.DEFAULT_LIMITS, max_atp=100)
admission = reads_of(sg.eval_receipt, sg.node_hash(ik), 101, Counting(env_of(ik)), policy)
at_limit = tried(lambda: sg.eval_receipt(sg.node_hash(ik), 100, env_of(ik), policy).exit)
refusal = sg.AdmissionRefused(101, 100)
check("B213 a verifier may refuse before execution: a budget above its admission limit is AdmissionRefused (naming what was "
      "claimed and allowed, not a ResourceFault), no read, no Receipt; a budget at the limit runs",
      admission == ("AdmissionRefused", 0) and at_limit == "normal_form" and (refusal.claimed, refusal.allowed) == (101, 100)
      and not isinstance(refusal, (sg.ResourceFault, tuple)), (admission, at_limit))
short_hash = [reads_of(sg.eval_receipt, h, 10, Counting(env_of(ik))) for h in (sg.node_hash(ik)[:31], sg.node_hash(ik) + b"\x00")]
check("B214 a term_hash that is not exactly 32 bytes is refused locally, before the environment is read",
      all(got == "ValueError" and n == 0 for got, n in short_hash), short_hash)
# §5.2, §5.3
check("B215 the reason hashes are SHA-256 of their names, as the Book prints them",
      [sg.R_INVALID.hex(), sg.R_ATP.hex(), sg.R_UNRES.hex()] == [
          "7cc62bcc7c921683532cec1c1c331ca81d76b001e0c7f407a4078df7f696efe8",
          "dc435a08513893bacd07abd802b9c526e92ae57ca6db40c1c8f369fd7032e090",
          "75daae55453d9a98bfadb847d70b73fdd0be91d3b6ef8511d22fc42aa2c7c8e2"])
damped = sg.sha(b"Signal Damped")
reasons = {receipt(skki, env_of(sk, skk, skki), atp=11)[0], tv8[0], INVALID_HEX}
check("B216 no rule of Book I produces the reserved reason Signal Damped",
      sg.node_hash(sg.ser(sg.DISSONANCE, sg.F_ATOM, atom=damped)).hex() not in reasons
      and damped not in (sg.R_INVALID, sg.R_ATP, sg.R_UNRES))
# §6: C1
lam = lambda x, m: ("lam", x, m)
var = lambda x: ("var", x)
kxy = tried(lambda: sg.term_hash(sg.c1(lam("x", lam("y", var("x"))))).hex())
eta = tried(lambda: sg.term_hash(sg.c1(lam("f", lam("x", ("lapp", var("f"), var("x")))))))
check("B217 C1[λx.λy.x] is S (K K) I with the Book's hash (TV-10), and no η-reduction: C1[λf.λx.f x] is not C1[λf.f] = I",
      kxy == "bed95fbc7ccd2cf53d3562138a69a90a9c38de9f7a23d9015eef1b6638d4eb1d" and eta != I_H and isinstance(eta, bytes),
      (kxy, eta))
free = tried(sg.c1, lam("x", ("lapp", var("y"), var("x"))))
const = tried(lambda: sg.c1(lam("x", lam("y", var("y")))))
check("B218 A(x, M) = K M when x is not free in M: λx.λy.y is K I, and λx.y x is S (K y) I with y left free, not bound",
      const == ("app", sg.KG, sg.IG) and free == ("app", ("app", sg.SG, ("app", sg.KG, var("y"))), sg.IG), (free, const))
# §7: the suite
import subprocess  # noqa: E402
suite = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve().parent / "spec_conformance" / "run_reference.py")],
                       capture_output=True, text=True)
check("B219 the machine-readable suite is part of the edition: every vector of vectors.json replays on the oracle",
      suite.returncode == 0 and "CONFORMANCE: ALL PASS" in suite.stdout, suite.stdout[-300:])
tv4 = [receipt(ik, env_of(ik), atp=n)[1:] for n in (0, 2, 3)]
check("B220 TV-4 at budgets 0, 2, 3: exhausted with spent 0, 0 (the root's bytes discarded: force costs 3 > 2) and 3",
      tv4 == [(0, "atp_exhausted"), (0, "atp_exhausted"), (3, "atp_exhausted")], tv4)

pair = tried(lambda: sg.eval_hash(sg.node_hash(ik), 10, env_of(ik)))
full = sg.eval_receipt(sg.node_hash(ik), 10, env_of(ik))
check("B221 the compatibility profile eval -> (result_term, atp_spent) is the Receipt's answer without exit, and a Receipt "
      "unpacks as that pair", not isinstance(pair, str) and (sg.term_hash(pair[0]), pair[1]) == (full.result_hash, full.atp_spent)
      and len(tuple(full)) == 2 and sg.term_hash(tuple(full)[0]) == full.result_hash, (pair, full))

# §7: prose and suite agree, field by field; the suite's schema is closed; exit and outcome are two levels
import json  # noqa: E402
import re  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import spec_audit as sa  # noqa: E402
import suite_schema as ss  # noqa: E402


def prose_problems():
    """What spec_audit's part B (prose against vectors, test by test) reports for the Book's own text."""
    uk = sa.UK.read_text()
    glyphs = dict(re.findall(r'\|\s*(\w)\s*\|\s*`0001`\+SHA-256\("\w"\)\s*\|\s*`([0-9a-f]{64})`\s*\|', uk))
    false_hash = re.search(r'Bytes\s*`0206‖H\(K\)‖H\(I\)`;\s*Hash\s*`([0-9a-f]{64})`', uk)
    if false_hash:
        glyphs["FALSE"] = false_hash.group(1)
    setup, problems = [], []
    proved, derived = sa.store_verified(setup), sa.derivable_constants(uk, setup)
    report = sa.prose_matches_vectors(uk, glyphs, proved, derived, problems)
    return problems, report.decided


disagree, decided = prose_problems()
check("B222 §7's prose and the suite's records agree on every checked statement (subject, budget, exit, result hash, "
      "ATP spent), and at least 30 statements are checked", disagree == [] and decided >= 30, (disagree[:3], decided))
suite_path, schema_path = ss.SUITES[0]
suite_doc = json.loads((Path(__file__).resolve().parents[1] / suite_path).read_text())
schema_doc = json.loads((Path(__file__).resolve().parents[1] / schema_path).read_text())


def errors_of(doc):
    errors = []
    ss.validate(doc, schema_doc, schema_doc, "", errors)
    return errors


grown = dict(suite_doc, meaning="for one reader only")
vector_grown = dict(suite_doc, vectors=[dict(suite_doc["vectors"][-1], hint="x")] + suite_doc["vectors"][1:])
check("B223 the suite's schema is closed: the suite validates, and an unknown field at the top or in a record makes it "
      "invalid", errors_of(suite_doc) == [] and errors_of(grown) != [] and errors_of(vector_grown) != [],
      (errors_of(suite_doc)[:2], errors_of(grown)[:1], errors_of(vector_grown)[:1]))
ev = schema_doc["$defs"]
exits = next(set(d["properties"]["expected"]["properties"]["exit"]["enum"]) for d in ev.values()
             if "expected" in d.get("properties", {}) and "exit" in d["properties"]["expected"].get("properties", {}))
outcomes = next(set(d["properties"]["expected"]["properties"]["outcome"]["enum"]) for d in ev.values()
                if "expected" in d.get("properties", {}) and "outcome" in d["properties"]["expected"].get("properties", {}))
evals = [v["expected"] for v in suite_doc["vectors"] if v["kind"] == "eval"]
invalid = [e for e in evals if e["outcome"] == "invalid_object"]
check("B224 exit and outcome are two levels: the schema's exit enum is exactly the Receipt's three exits, outcome adds "
      "only invalid_object, and an invalid_object outcome is a normal_form exit whose result is the Canonical Invalid "
      "Object", exits == set(sg.EXITS) and outcomes == set(sg.EXITS) | {"invalid_object"} and invalid
      and all(e["exit"] == "normal_form" and e["result_hash"] == INVALID_HEX for e in invalid)
      and all(e["exit"] == e["outcome"] for e in evals if e["outcome"] != "invalid_object"), (exits, outcomes, invalid))

print(f"\nBOOK1-CLAIMS: {'ALL PASS' if not failures else 'FAILURES ' + ' '.join(failures)}")
sys.exit(1 if failures else 0)
