#!/usr/bin/env python3
"""Witnesses of sigma-resume's claims (spec/sigma-resume.md, .warrant/claims.json): one case per observable.

Each case prints `ok   ID …` or `FAIL ID …`; the run exits non-zero on any FAIL. As in book1_claims_test.py,
an exception is a wrong value, so a mutant that makes the reference raise is seen on the case's assertion.

    python3 tests/resume_claims_test.py"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "impl"))
import sigma_glyph as G   # noqa: E402
import sigma_resume as R  # noqa: E402

failures = []


def check(case, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + case + ("" if ok else f" -- {detail}"))
    if not ok:
        failures.append(case)


def tried(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


class Delivered(dict):
    reads = 0

    def get(self, h, default=None):
        Delivered.reads += 1
        return super().get(h, default)


def app(left, right):
    return G.ser(G.APPLY, G.F_LEFT | G.F_RIGHT, left=left, right=right)


def env_of(*nodes, manifest=()):
    d = Delivered({G.node_hash(b): b for b in nodes})
    return R.Environment(list(d) + list(manifest), d)


I_H, K_H, S_H = G.I_H, G.K_H, G.S_H
si = app(S_H, I_H)
sii = app(G.node_hash(si), I_H)
ik = app(I_H, K_H)
tv6 = app(G.node_hash(sii), G.node_hash(ik))            # S I I (I K): 21 ATP to K K
TV6 = (si, sii, ik, tv6)


def run(top, nodes, grants, runtime=R.RUNTIME_SEMANTICS_ID, **kw):
    """The final Result of granting `grants` one after another to a fresh computation of `top`."""
    env = env_of(*nodes)
    rt = R.root(G.node_hash(top), env, runtime)
    doc, cid, sb = R.start(rt[1], G.node_hash(top))
    res = None
    for g in grants:
        res = R.advance(doc, cid, sb, env, g, runtime=runtime, **kw)
        doc, cid, sb = res.checkpoint, res.checkpoint_id, res.state_bytes
    return res, rt, env


# §1 identities
env6 = env_of(*TV6)
root_doc, cid = R.root(G.node_hash(tv6), env6)
canon = json.dumps(root_doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
check("R01 computation_id is SHA-256 of the root's canonical JSON (sorted keys, no whitespace, UTF-8)",
      cid == hashlib.sha256(canon).hexdigest() and b" " not in canon, (cid, canon))
check("R02 no budget is part of the root: it has exactly schema, runtime, cost model, input term, environment",
      sorted(root_doc) == ["cost_model_id", "environment_id", "input_term_hash", "runtime_semantics_id", "schema"], root_doc)
rich = R.root(G.node_hash(tv6), env6, R.RICH_RUNTIME_ID)
check("R03 the runtime profile is part of the root: one term under two profiles is two computations",
      rich[1] != cid and rich[0]["runtime_semantics_id"] != root_doc["runtime_semantics_id"], (rich[1], cid))
hs = sorted(G.node_hash(b) for b in TV6)
want_env = hashlib.sha256(json.dumps({"schema": "sigma-resume.environment@draft-1", "hashes": [h.hex() for h in hs]},
                                     sort_keys=True, separators=(",", ":")).encode()).hexdigest()
check("R04 environment_id is SHA-256 of {schema: sigma-resume.environment@draft-1, hashes: sorted lowercase hex}, "
      "whatever order the manifest is given in", env6.environment_id == want_env
      and R.Environment(list(reversed(hs)), {}).environment_id == want_env, env6.environment_id)
ghost = hashlib.sha256(b"not in the manifest").digest()
blocked = run(app(I_H, ghost), [app(I_H, ghost)], [100])[0]
named = hashlib.sha256(b"named, never delivered").digest()
env_u = R.Environment([G.node_hash(app(I_H, named)), named], Delivered({G.node_hash(app(I_H, named)): app(I_H, named)}))
rt_u = R.root(G.node_hash(app(I_H, named)), env_u)
d_u, c_u, s_u = R.start(rt_u[1], G.node_hash(app(I_H, named)))
undelivered = R.advance(d_u, c_u, s_u, env_u, 100)
check("R05 a hash outside the manifest is BLOCKED_REFERENCE (a kernel answer, the hash named); one in the manifest whose "
      "bytes are not delivered is EVIDENCE_UNAVAILABLE (local)",
      (blocked.outcome, blocked.missing, blocked.kernel) == (R.BLOCKED_REFERENCE, ghost.hex(), True)
      and (undelivered.outcome, undelivered.kernel) == (R.EVIDENCE_UNAVAILABLE, False),
      (blocked.outcome, blocked.missing, undelivered.outcome))
t = ("app", ("thunk", K_H), ("app", ("lit", b"\x01" * 32), ("ref", b"\x02" * 32)))
manual = b"SGS1" + bytes.fromhex(cid) + b"A" + b"T" + K_H + b"A" + b"L" + b"\x01" * 32 + b"R" + b"\x02" * 32
enc = tried(R.encode_state, cid, t)
check("R06 a state is SGS1 ‖ computation_id ‖ the tree in preorder (A, then T/L/R/D with 32 bytes), and state_id is "
      "SHA-256 of those bytes", enc == manual and R.state_id(manual) == hashlib.sha256(manual).hexdigest(), enc)
lit_bytes = G.ser(G.LITERAL, G.F_ATOM, atom=b"\x03" * 32)
cold, warm = ("thunk", G.node_hash(lit_bytes)), ("lit", b"\x03" * 32)
check("R07 a cold thunk and the node it materializes to share a term hash and not a state_id",
      G.term_hash(cold) == G.term_hash(warm) and R.state_id(R.encode_state(cid, cold)) != R.state_id(R.encode_state(cid, warm)))
bad_states = [manual[:-1], manual + b"\x00", manual[:36] + b"X" + b"\x00" * 32]
check("R08 bytes that are not exactly a state encoding (truncated, trailing bytes, an unknown tag) are INVALID_ENCODING",
      [tried(R.decode_state, b) for b in bad_states] == ["InvalidEncoding"] * 3, [tried(R.decode_state, b) for b in bad_states])
# §1 checkpoints
good_doc, good_id = R.checkpoint(cid, manual, 10, 4, 3, None, 2)
good_raw = R._canon(good_doc)


def variant(**change):
    return R._canon(dict(good_doc, **change))


parsed = tried(R.parse_checkpoint, good_raw)
refused = {"spaced": good_raw.replace(b",", b", "), "beyond 2^53": variant(credit_total=2 ** 53),
           "spent over credit": variant(spent_total=11)}
check("R09 a checkpoint is canonical JSON with integers in 0..2^53-1 and spent <= credit; anything else is refused",
      isinstance(parsed, tuple) and all(tried(R.parse_checkpoint, r) == "InvalidEncoding" for r in refused.values()),
      {k: tried(R.parse_checkpoint, r) for k, r in refused.items()})
dup = good_raw.replace(b'{"computation_id"', b'{"computation_id":"' + b"0" * 64 + b'","computation_id"', 1)
more = {"duplicate name": dup, "float": variant(credit_total=1.5), "boolean": variant(peak_semantic_size=True),
        "unknown field": variant(signature="x")}
check("R10 duplicate names, floats, booleans and unknown fields are refused, never normalized",
      all(tried(R.parse_checkpoint, r) == "InvalidEncoding" for r in more.values()),
      {k: tried(R.parse_checkpoint, r) for k, r in more.items()})
# §2-§3 advance
whole = run(tv6, TV6, [21])[0]
splits = [[1] * 21, [3, 18], [10, 11], [20, 1], [5, 5, 5, 6], [0, 21]]
results = [(lambda r: (r.checkpoint["state_id"], r.checkpoint["spent_total"], r.outcome))(run(tv6, TV6, s)[0]) for s in splits]
check("R11 segmentation invariance: every split of 21 credit reaches the state, spent and outcome of one segment of 21",
      all(r == (whole.checkpoint["state_id"], 21, R.NORMAL_FORM) for r in results), results)
mismatch = R.Environment([G.node_hash(ik)], {G.node_hash(ik): G.K_BYTES})
rt_m = R.root(G.node_hash(ik), mismatch)
d_m, c_m, s_m = R.start(rt_m[1], G.node_hash(ik))
cas = R.advance(d_m, c_m, s_m, mismatch, 10)
check("R12 a local outcome never stands in for an answer: EVIDENCE_UNAVAILABLE and CAS_MISMATCH are not kernel outcomes",
      (undelivered.kernel, cas.outcome, cas.kernel) == (False, R.CAS_MISMATCH, False), (cas.outcome, cas.kernel))
paused = run(tv6, TV6, [3, 2])[0]          # after 3, the next action costs more than 2
three = run(tv6, TV6, [3])[0]
check("R13 PAUSED changes nothing: the action that does not fit is not taken, state and spent stay, and more credit "
      "continues from them", paused.outcome == R.PAUSED and paused.checkpoint["state_id"] == three.checkpoint["state_id"]
      and paused.checkpoint["spent_total"] == three.checkpoint["spent_total"] == 3, (paused.outcome, paused.checkpoint))
Delivered.reads = 0
zero = run(tv6, TV6, [0])[0]
check("R14 at available credit 0 a non-genesis thunk is not fetched: PAUSED with no store read",
      (zero.outcome, Delivered.reads) == (R.PAUSED, 0), (zero.outcome, Delivered.reads))
top_doc, top_id = R.checkpoint(cid, R.encode_state(cid, ("thunk", G.node_hash(tv6))), R.MAX_INT, 0, 1, None, 0)
check("R15 integers are never wrapped: credit beyond 2^53-1 is refused (IntegerOverflow), not wrapped or clamped",
      tried(R.advance, top_doc, top_id, R.encode_state(cid, ("thunk", G.node_hash(tv6))), env6, 1) == "IntegerOverflow")
big = b"SGS1" + b"\x00" * (R.MAX_STATE_BYTES + 1)
big_doc = dict(good_doc, state_id=R.state_id(big))
admitted = tried(R.advance, big_doc, "0" * 64, big, env6, 1)
check("R16 a state larger than this host admits is ADMISSION_REFUSED before it is decoded",
      getattr(admitted, "outcome", admitted) == R.ADMISSION_REFUSED, getattr(admitted, "outcome", admitted))
del big
# §4 verify
mid = run(tv6, TV6, [10])[0]
raw_mid = R._canon(mid.checkpoint)
other_env = env_of(*TV6, manifest=[ghost])
check("R17 the verifier chooses the root and its context: the same checkpoint under another environment is CONTEXT_MISMATCH",
      R.verify((root_doc, cid), other_env, raw_mid, mid.state_bytes)[:2] == (R.UNVERIFIED, "CONTEXT_MISMATCH")
      and R.verify((root_doc, cid), env6, raw_mid, mid.state_bytes)[0] == R.REPLAYED,
      R.verify((root_doc, cid), other_env, raw_mid, mid.state_bytes))
limited = run(tv6, TV6, [21], max_actions=2)[0]        # INCOMPLETE: credit left over
v_limited = R.verify((root_doc, cid), env6, R._canon(limited.checkpoint), limited.state_bytes)
check("R18 replay goes to the claimed spent, not the claimed credit: a prefix stopped with credit left is REPLAYED as PREFIX",
      limited.outcome == R.INCOMPLETE and v_limited[:2] == (R.REPLAYED, R.PREFIX), (limited.outcome, v_limited))
forged = dict(mid.checkpoint, peak_semantic_size=mid.checkpoint["peak_semantic_size"] + 1)
v_forged = R.verify((root_doc, cid), env6, R._canon(forged), mid.state_bytes)
check("R19 REPLAYED only when this verifier reproduced state, spent and peak: a checkpoint claiming another peak is not",
      v_forged[0] == R.UNVERIFIED and v_forged[1].startswith("UNVERIFIED_PREFIX"), v_forged)
# §5 cycles (the only known cycles are in the experimental profile: the cycle verifier is profile-independent)
yi = app(R.Y_H, I_H)
hy = G.node_hash(yi)
env_y = R.Environment([hy], {hy: yi})
rt_y = R.root(hy, env_y, R.RICH_RUNTIME_ID)
c_y, i_y, s_y = R.start(rt_y[1], hy)
entry = R.advance(c_y, i_y, s_y, env_y, 3, runtime=R.RICH_RUNTIME_ID)


def witness(n, cost, **change):
    return dict(R.cycle_witness(rt_y[1], entry.checkpoint, entry.state_bytes, n, cost), **change)


verdicts = {"proof": R.verify_cycle(rt_y, env_y, witness(2, 3)), "wrong cost": R.verify_cycle(rt_y, env_y, witness(2, 4)),
            "no action": R.verify_cycle(rt_y, env_y, witness(0, 0)), "half a period": R.verify_cycle(rt_y, env_y, witness(1, 1))}
check("R20 CYCLE_PROVEN requires a priced action, the exact cost and the same machine state at the end (Y I, period 2, "
      "cost 3)", verdicts["proof"] == "CYCLE_PROVEN"
      and all(v.startswith("INVALID_CYCLE_WITNESS") for k, v in verdicts.items() if k != "proof"), verdicts)
shapes = {"unknown field": R.verify_cycle(rt_y, env_y, witness(2, 3, note="x")),
          "more actions than cost": R.verify_cycle(rt_y, env_y, witness(5, 3)),
          "bad digest": R.verify_cycle(rt_y, env_y, witness(2, 3, entry_state_id="XYZ"))}
check("R21 a witness is exactly {schema: sigma-resume.cycle@draft-1, computation_id, entry_spent_total, entry_state_id, "
      "cycle_action_count, cycle_cost}; a malformed one is refused by name before any replay: unknown field, more actions "
      "than cost, a bad digest", witness(2, 3)["schema"] == "sigma-resume.cycle@draft-1"
      and sorted(witness(2, 3)) == ["computation_id", "cycle_action_count", "cycle_cost", "entry_spent_total",
                                    "entry_state_id", "schema"]
      and shapes["unknown field"] == "INVALID_CYCLE_WITNESS: fields are not exactly the witness schema's"
      and shapes["more actions than cost"] == "INVALID_CYCLE_WITNESS: more actions than cost (every action costs at least 1)"
      and shapes["bad digest"].startswith("INVALID_CYCLE_WITNESS"), shapes)
# §5 on the wire: the witness is bytes, and the provider must refuse a malformed encoding before it reads the store
import sigma_provider as P  # noqa: E402


class Counted(dict):
    """A store that counts reads: replay reads it, a refusal before replay does not."""
    reads = 0

    def get(self, key, default=None):
        self.reads += 1
        return super().get(key, default)


wire_ok = R._canon(witness(2, 3))
y_store = Counted({hy.hex(): yi})
y_args = (R.RICH_RUNTIME_ID, hy.hex(), [hy.hex()], y_store)
wire = {"spaced": json.dumps(witness(2, 3), sort_keys=True).encode(),
        "duplicate name": wire_ok.replace(b"{", b'{"cycle_cost":false,', 1),
        "float count": wire_ok.replace(b'"cycle_cost":3', b'"cycle_cost":3.0'),
        "trailing newline": wire_ok + b"\n",
        "unsorted": json.dumps(witness(2, 3), separators=(",", ":")).encode(),
        "nested": b'{"schema":' + b"[" * 10**6 + b"0" + b"]" * 10**6 + b"}",
        "actions over cost, another root": R._canon(witness(5, 3, computation_id="0" * 64))}
got = {}
for k, raw in wire.items():
    y_store.reads = 0
    try:
        got[k] = (P.verify_cycle(*y_args, raw), y_store.reads)
    except Exception as x:          # an exception is no named refusal: the case fails, it does not crash the suite
        got[k] = (f"raised {type(x).__name__}", y_store.reads)
y_store.reads = 0
proof = (P.verify_cycle(*y_args, wire_ok), y_store.reads)
check("R23 a cycle witness is canonical JSON on the wire: whitespace, an overwritten duplicate name, a float, a trailing "
      "newline, unsorted names, nesting past the recursion limit, or more actions than cost (whatever root it names) are "
      "refused as INVALID_CYCLE_WITNESS before the store is read; the canonical bytes of "
      "the same witness prove the cycle", proof[0] == "CYCLE_PROVEN" and proof[1] > 0
      and all(code.startswith("INVALID_CYCLE_WITNESS") and reads == 0 for code, reads in got.values())
      and "duplicate name" in got["duplicate name"][0] and "non-integer" in got["float count"][0]
      and all("not canonical" in got[k][0] for k in ("spaced", "trailing newline", "unsorted"))
      and "nested too deeply" in got["nested"][0] and "more actions than cost" in got["actions over cost, another root"][0]
      and wire["unsorted"] != wire_ok and json.loads(wire["unsorted"]) == witness(2, 3), {**got, "proof": proof})
# §6 the profile
book1 = G.eval_receipt(G.node_hash(tv6), 1000, {G.node_hash(b): b for b in TV6})
check("R22 the Book I profile is this specification's: its runtime and cost-model ids are the Book's, and resume reaches "
      "Book I's result and spent", (root_doc["runtime_semantics_id"], root_doc["cost_model_id"])
      == ("sigma-book1-0.6.0/hash-thunk/leftmost-outermost", "atp/size-priced/adr-001+adr-003")
      and G.term_hash(whole.term()) == book1.result_hash and whole.checkpoint["spent_total"] == book1.atp_spent,
      (root_doc["runtime_semantics_id"], root_doc["cost_model_id"]))

print(f"\nRESUME-CLAIMS: {'ALL PASS' if not failures else 'FAILURES ' + ' '.join(failures)}")
sys.exit(1 if failures else 0)
