#!/usr/bin/env python3
"""sigma-resume as an installable provider: the consumer surface of the resumable
kernel (impl/sigma_resume.py), for a caller that has only the installed wheel.

The consumer surface over spec/sigma-resume.md's reference implementation. This
module adds no semantics; every answer comes from sigma_resume / sigma_glyph.

Library (bytes and hex in, JSON-able values out):

    term(expr)                                  -> {"input", "nodes"}     parse `S K (K I)`, `#<hex>`
    start(runtime, input, hashes)               -> {"checkpoint", "state", "computation_id"}
    advance(runtime, hashes, blobs, checkpoint, state, credit, max_actions=None)
                                                -> {"outcome", "checkpoint", "state", "result"?}
    verify(runtime, input, hashes, blobs, chain, cache=False)
                                                -> [{"basis", "code", "result"?}]
    resume(runtime, input, hashes, blobs, checkpoint, state, credit, max_actions=None)
                                                -> {"base_verification", "status", ...}   (checked foreign resume)
    find_cycle(runtime, input, hashes, blobs, max_steps) -> {"witness"} | {"outcome"}
    verify_cycle(runtime, input, hashes, blobs, witness) -> "CYCLE_PROVEN" | refusal
    identity_of(sources)                        -> the provider identity of these module bytes

`hashes` is the computation's environment: the sorted node hashes it may demand.
`blobs` maps hex hash -> bytes actually delivered. A hash outside `hashes` is the
kernel answer BLOCKED_REFERENCE; a hash inside it whose bytes were not delivered
is the local outcome EVIDENCE_UNAVAILABLE, never an answer.

Process protocol (`python -m sigma_provider serve`): one JSON request on stdin,
one JSON response on stdout:

    {"sigma_provider": 1, "op": <name>, "args": {...}, "blobs": {hex: base64}}
 -> {"sigma_provider": 1, "ok": {...}} | {"sigma_provider": 1, "refused": "<reason>"}

Bytes travel as base64. A refusal is never an answer. `python -m sigma_provider`
with no verb runs the self-test.

IDENTITY. `identity_of({"sigma_glyph.py": b, "sigma_resume.py": b,
"sigma_provider.py": b})` is SHA-256 over the canonical JSON
`{"provider": "sigma-resume", "files": {name: sha256(bytes)}}`. A consumer computes
it from the bytes it will execute and decides itself whether it accepts them; this
module reporting its own identity grants nothing. Runtime semantics, cost model
and environment are inside every computation root (sigma_resume.root), and the
verifier identity is sigma_resume.VERIFIER_ID.
"""
import base64
import hashlib
import json
import sys
from pathlib import Path

import sigma_glyph as G
import sigma_resume as R

PROTOCOL = 1
PROVIDER = "sigma-resume"
FILES = ("sigma_glyph.py", "sigma_resume.py", "sigma_provider.py")
RUNTIMES = tuple(R.PROFILES)
ATOMS = {"S": G.S_H, "K": G.K_H, "I": G.I_H, "Y": R.Y_H, "M": R.M_H, "W": R.W_H}
VERBS = ("serve",)


class Refused(Exception):
    """A request this provider will not answer; the message is the reason."""


def identity_of(sources):
    files = {name: hashlib.sha256(sources[name]).hexdigest() for name in FILES}
    doc = {"provider": PROVIDER, "files": files}
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---------------------------------------------------------------- terms

def _parse(expr):
    toks = expr.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def atom():
        nonlocal pos
        if pos >= len(toks):
            raise Refused("term: unexpected end")
        t = toks[pos]
        pos += 1
        if t == "(":
            v = seq()
            if pos >= len(toks) or toks[pos] != ")":
                raise Refused("term: unbalanced parentheses")
            pos += 1
            return v
        if t in ATOMS:
            return ("thunk", ATOMS[t])
        if t.startswith("#") and len(t) == 65:
            try:
                return ("thunk", bytes.fromhex(t[1:]))
            except ValueError:
                raise Refused(f"term: not a node hash {t!r}") from None
        raise Refused(f"term: unknown token {t!r}")

    def seq():
        v = atom()
        while pos < len(toks) and toks[pos] != ")":
            v = ("app", v, atom())
        return v

    v = seq()
    if pos != len(toks):
        raise Refused("term: trailing tokens")
    return v


def term(expr):
    """The input hash of `expr` and the bytes of every APPLY node it builds."""
    t = _parse(expr)
    nodes, stack = {}, [t]
    while stack:
        x = stack.pop()
        if x[0] == "app":
            b = G.term_bytes(x)
            nodes[G.node_hash(b).hex()] = b
            stack += [x[1], x[2]]
    return {"input": G.term_hash(t).hex(), "nodes": nodes}


# ---------------------------------------------------------------- computation

def _runtime(runtime):
    if runtime not in R.PROFILES:
        raise Refused(f"unsupported runtime {runtime!r}")
    return runtime


class _Delivered:
    def __init__(self, blobs):
        self.blobs = blobs

    def get(self, h):
        return self.blobs.get(h.hex())


def _env(hashes, blobs):
    try:
        return R.Environment([bytes.fromhex(h) for h in hashes], _Delivered(blobs))
    except ValueError:
        raise Refused("environment: hashes must be 64 hex characters") from None


def _root(runtime, inp, env):
    return R.root(bytes.fromhex(inp), env, _runtime(runtime))


def _result(state_bytes):
    return G.term_hash(R.decode_state(state_bytes)[1]).hex()


def start(runtime, inp, hashes):
    env = _env(hashes, {})
    _, cid = _root(runtime, inp, env)
    doc, _, sb = R.start(cid, bytes.fromhex(inp))
    return {"checkpoint": R._canon(doc), "state": sb, "computation_id": cid}


def advance(runtime, hashes, blobs, checkpoint, state, credit, max_actions=None):
    env = _env(hashes, blobs)
    doc, ck_id = R.parse_checkpoint(checkpoint)
    res = R.advance(doc, ck_id, state, env, credit, runtime=_runtime(runtime), max_actions=max_actions)
    out = {"outcome": res.outcome, "checkpoint": R._canon(res.checkpoint), "state": res.state_bytes,
           "missing": res.missing, "detail": res.detail}
    if res.outcome == R.NORMAL_FORM:
        out["result"] = _result(res.state_bytes)
    return out


def verify(runtime, inp, hashes, blobs, chain, cache=False):
    """Replay each (checkpoint, state) from the root THIS caller names. With
    `cache`, a later checkpoint may start from an earlier verified one; the
    answers must not depend on it."""
    env = _env(hashes, blobs)
    root = _root(runtime, inp, env)
    vc = R.VerifiedCache() if cache else None
    out = []
    for ck, st in chain:
        basis, code, _ = R.verify(root, env, ck, st, cache=vc)
        r = {"basis": basis, "code": code}
        if basis == R.REPLAYED and code == R.NORMAL_FORM:
            r["result"] = _result(st)
        out.append(r)
    return out


TERMINAL = (R.NORMAL_FORM, R.BLOCKED_REFERENCE)
RESUMABLE = (R.PAUSED, R.PREFIX)


def resume(runtime, inp, hashes, blobs, checkpoint, state, credit, max_actions=None):
    """Continue a checkpoint someone else produced, from the root THIS caller names.

    `advance` is the producer's primitive: it trusts its checkpoint. A consumer
    must first know the checkpoint is reachable from its own root under its own
    runtime and environment, and that the next action can run here. So:
      verify the base against the caller's root (replay, sigma_resume.verify);
      not REPLAYED                      -> REFUSED, advance is never called;
      REPLAYED, a terminal kernel code  -> TERMINAL, no segment, no credit added;
      REPLAYED, PAUSED or PREFIX        -> ADVANCED: one advance from those bytes;
      REPLAYED, any other code          -> DEFERRED: a local diagnostic (bytes not
                                           delivered, a host limit), no credit.
    The base verification and the segment are returned separately: a verified
    prefix is not an answer, and the caller still verifies a final receipt for
    its own purpose. Pure in its inputs: the same parent and credit give the same
    segment, with no hidden job between calls."""
    env = _env(hashes, blobs)
    root = _root(runtime, inp, env)
    basis, code, _ = R.verify(root, env, checkpoint, state)
    base = {"basis": basis, "code": code, "verifier": R.VERIFIER_ID}
    if basis != R.REPLAYED:
        return {"status": "REFUSED", "base_verification": base}
    if code in TERMINAL:
        out = {"status": "TERMINAL", "base_verification": base, "code": code}
        if code == R.NORMAL_FORM:
            out["result"] = _result(state)
        return out
    if code not in RESUMABLE:
        return {"status": "DEFERRED", "base_verification": base, "diagnostic": code}
    return {"status": "ADVANCED", "base_verification": base,
            "segment": advance(runtime, hashes, blobs, checkpoint, state, credit, max_actions)}


def find_cycle(runtime, inp, hashes, blobs, max_steps):
    """Producer side: one action at a time until a machine state repeats."""
    env = _env(hashes, blobs)
    _, cid = _root(runtime, inp, env)
    doc, ck_id, sb = R.start(cid, bytes.fromhex(inp))
    seen = {}
    for _ in range(max_steps):
        sid = R.state_id(sb)
        if sid in seen:
            e_doc, e_sb, e_n = seen[sid]
            w = R.cycle_witness(cid, e_doc, e_sb, len(seen) - e_n, doc["spent_total"] - e_doc["spent_total"])
            return {"witness": R._canon(w)}
        seen[sid] = (doc, sb, len(seen))
        res = R.advance(doc, ck_id, sb, env, 1_000_000, runtime=runtime, max_actions=1)
        if res.checkpoint["transition_claim"]["actions"] == 0:
            return {"outcome": res.outcome}
        doc, ck_id, sb = dict(res.checkpoint, credit_total=res.checkpoint["spent_total"]), res.checkpoint_id, res.state_bytes
    return {"outcome": "NO_CYCLE_WITHIN_LIMIT"}


def verify_cycle(runtime, inp, hashes, blobs, witness):
    env = _env(hashes, blobs)
    try:
        doc = R.parse_cycle_witness(witness)
    except R.InvalidEncoding as e:
        return f"INVALID_CYCLE_WITNESS: {e}"
    return R.verify_cycle(_root(runtime, inp, env), env, doc)


# ---------------------------------------------------------------- process protocol

def _need(ok, why):
    if not ok:
        raise Refused(why)


def _hex64(v):
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _int(v, low=0):
    return type(v) is int and v >= low


# The operands each op reads, with their JSON types, checked before any is used
# (S64-01: a list where a mapping or string belonged reached .items / .replace).
_ARGS = {
    "term": {"expr": lambda v: isinstance(v, str)},
    "start": {"runtime": lambda v: isinstance(v, str), "input": _hex64,
              "hashes": lambda v: isinstance(v, list) and all(_hex64(h) for h in v)},
    "advance": {"checkpoint": lambda v: isinstance(v, str), "state": lambda v: isinstance(v, str),
                "credit": _int, "max_actions": lambda v: v is None or _int(v, 1)},
    "verify": {"chain": lambda v: isinstance(v, list) and all(
                   isinstance(x, list) and len(x) == 2 and all(isinstance(y, str) for y in x) for x in v),
               "cache": lambda v: isinstance(v, bool)},
    "resume": {"checkpoint": lambda v: isinstance(v, str), "state": lambda v: isinstance(v, str),
               "credit": _int, "max_actions": lambda v: v is None or _int(v, 1)},
    "find_cycle": {"max_steps": lambda v: _int(v, 1)},
    "verify_cycle": {"witness": lambda v: isinstance(v, str)},
}
_COMMON = ("runtime", "input", "hashes")
_OPTIONAL = {"max_actions", "cache"}


def _check_args(op, args):
    spec = dict(_ARGS[op])
    if op != "term":
        spec.update({k: _ARGS["start"][k] for k in _COMMON})
    for key, ok in spec.items():
        if key in args:
            _need(ok(args[key]), f"{op}: {key} has the wrong type or form")
        else:
            _need(key in _OPTIONAL, f"{op}: {key} is required")
    _need(not set(args) - set(spec), f"{op}: unknown arguments {sorted(set(args) - set(spec))}")


def _b(v):
    return base64.b64decode(v, validate=True)


def _e(v):
    return base64.b64encode(v).decode()


def _op_term(a, blobs):
    out = term(a["expr"])
    return {"input": out["input"], "nodes": {h: _e(b) for h, b in out["nodes"].items()}}


def _op_start(a, blobs):
    out = start(a["runtime"], a["input"], a["hashes"])
    return {"checkpoint": _e(out["checkpoint"]), "state": _e(out["state"]), "computation_id": out["computation_id"]}


def _op_advance(a, blobs):
    out = advance(a["runtime"], a["hashes"], blobs, _b(a["checkpoint"]), _b(a["state"]), a["credit"], a.get("max_actions"))
    return dict(out, checkpoint=_e(out["checkpoint"]), state=_e(out["state"]))


def _op_verify(a, blobs):
    chain = [(_b(ck), _b(st)) for ck, st in a["chain"]]
    return {"results": verify(a["runtime"], a["input"], a["hashes"], blobs, chain, a.get("cache", False)),
            "verifier": R.VERIFIER_ID}


def _op_resume(a, blobs):
    out = resume(a["runtime"], a["input"], a["hashes"], blobs, _b(a["checkpoint"]), _b(a["state"]), a["credit"],
                 a.get("max_actions"))
    if "segment" in out:
        seg = out["segment"]
        out["segment"] = dict(seg, checkpoint=_e(seg["checkpoint"]), state=_e(seg["state"]))
    return out


def _op_find_cycle(a, blobs):
    out = find_cycle(a["runtime"], a["input"], a["hashes"], blobs, a["max_steps"])
    return {"witness": _e(out["witness"])} if "witness" in out else out


def _op_verify_cycle(a, blobs):
    return {"code": verify_cycle(a["runtime"], a["input"], a["hashes"], blobs, _b(a["witness"])),
            "verifier": R.VERIFIER_ID}


OPS = {"term": _op_term, "start": _op_start, "advance": _op_advance, "verify": _op_verify, "resume": _op_resume,
       "find_cycle": _op_find_cycle, "verify_cycle": _op_verify_cycle}


def handle(req):
    """One protocol request -> one response. Malformed input is a refusal."""
    try:
        if not (isinstance(req, dict) and req.get("sigma_provider") == PROTOCOL and req.get("op") in OPS
                and isinstance(req.get("args"), dict)):
            raise Refused("not a sigma_provider 1 request with a known op")
        raw = req.get("blobs", {})
        _need(isinstance(raw, dict) and all(_hex64(h) and isinstance(v, str) for h, v in raw.items()),
              "blobs must map 64-hex hashes to base64 strings")
        _check_args(req["op"], req["args"])
        blobs = {h: _b(v) for h, v in raw.items()}
        return {"sigma_provider": PROTOCOL, "ok": OPS[req["op"]](req["args"], blobs)}
    except Refused as e:
        return {"sigma_provider": PROTOCOL, "refused": str(e)}
    except (R.InvalidEncoding, R.IntegerOverflow, ValueError, KeyError, TypeError) as e:
        return {"sigma_provider": PROTOCOL, "refused": f"{type(e).__name__}: {e}"}


def serve():
    try:
        req = json.loads(sys.stdin.buffer.read(), object_pairs_hook=R._no_duplicates)   # a duplicate name is refused, not overwritten
    except (ValueError, RecursionError):
        req = None
    sys.stdout.write(json.dumps(handle(req), sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------- self-test

def selftest():
    results = []

    def ok(name, cond):
        results.append(cond)
        print(("OK   " if cond else "FAIL ") + name)

    t = term("S K K (K I)")
    hs = sorted(t["nodes"])
    b1 = R.RUNTIME_SEMANTICS_ID
    s = start(b1, t["input"], hs)
    a1 = advance(b1, hs, t["nodes"], s["checkpoint"], s["state"], 2)
    ok("a budgeted segment pauses", a1["outcome"] == R.PAUSED)
    a2 = advance(b1, hs, t["nodes"], a1["checkpoint"], a1["state"], 100)
    ok("the resumed segment reaches a normal form", a2["outcome"] == R.NORMAL_FORM)
    ok("S K K (K I) reduces to K I", a2.get("result") == G.term_hash(("app", ("thunk", G.K_H), ("thunk", G.I_H))).hex())
    v = verify(b1, t["input"], hs, t["nodes"], [(a1["checkpoint"], a1["state"]), (a2["checkpoint"], a2["state"])])
    ok("both checkpoints replay", [x["basis"] for x in v] == [R.REPLAYED, R.REPLAYED] and v[1]["code"] == R.NORMAL_FORM)
    vc = verify(b1, t["input"], hs, t["nodes"], [(a1["checkpoint"], a1["state"]), (a2["checkpoint"], a2["state"])], cache=True)
    ok("a verified-replay cache changes no answer", vc == v)
    other = term("K")["input"]
    ok("a checkpoint replayed under another root is not verified",
       verify(b1, other, hs, t["nodes"], [(a2["checkpoint"], a2["state"])])[0]["basis"] == R.UNVERIFIED)
    missing = advance(b1, hs, {}, s["checkpoint"], s["state"], 100)
    ok("bytes the environment names but nobody delivered: EVIDENCE_UNAVAILABLE", missing["outcome"] == R.EVIDENCE_UNAVAILABLE)
    y = term("Y I")
    sy = start(b1, y["input"], sorted(y["nodes"]))
    ay = advance(b1, sorted(y["nodes"]), y["nodes"], sy["checkpoint"], sy["state"], 100)
    ok("a reference outside the environment: BLOCKED_REFERENCE", ay["outcome"] == R.BLOCKED_REFERENCE)
    rich = R.RICH_RUNTIME_ID
    mm = term("M M")
    cyc = find_cycle(rich, mm["input"], sorted(mm["nodes"]), mm["nodes"], 50)
    ok("M M cycles under the rich profile, and the witness verifies",
       "witness" in cyc and verify_cycle(rich, mm["input"], sorted(mm["nodes"]), mm["nodes"], cyc["witness"]) == "CYCLE_PROVEN")
    kim = term("K I (M M)")
    ok("the same witness proves nothing about another root",
       verify_cycle(rich, kim["input"], sorted(kim["nodes"]), kim["nodes"], cyc.get("witness", b"{}")) != "CYCLE_PROVEN")
    bad = handle({"sigma_provider": PROTOCOL, "op": "start", "args": {"runtime": "latest", "input": t["input"], "hashes": hs}})
    ok("an unsupported runtime is refused, not guessed", "refused" in bad)
    ok("a malformed request is refused", "refused" in handle({"op": "verify"}))
    bad_shapes = [{"op": "term", "args": {"expr": "I"}, "blobs": []},
                  {"op": "term", "args": {"expr": []}},
                  {"op": "start", "args": {"runtime": b1, "input": t["input"], "hashes": "x"}},
                  {"op": "advance", "args": {"runtime": b1, "input": t["input"], "hashes": hs, "checkpoint": "", "state": "",
                                             "credit": True}},
                  {"op": "verify", "args": {"runtime": b1, "input": t["input"], "hashes": hs, "chain": [["a"]]}},
                  {"op": "find_cycle", "args": {"runtime": rich, "input": mm["input"], "hashes": [], "max_steps": "9"}}]
    rs = resume(b1, t["input"], hs, t["nodes"], a1["checkpoint"], a1["state"], 100)
    ok("resume verifies a foreign PAUSED checkpoint, then advances it to the normal form",
       rs["status"] == "ADVANCED" and rs["base_verification"]["basis"] == R.REPLAYED
       and rs["segment"]["outcome"] == R.NORMAL_FORM)
    ok("resume refuses a checkpoint under another root without advancing",
       resume(b1, other, hs, t["nodes"], a1["checkpoint"], a1["state"], 100)["status"] == "REFUSED")
    ok("operands of the wrong JSON type are refused, never a traceback",
       all("refused" in handle(dict(r, sigma_provider=PROTOCOL)) for r in bad_shapes)
       and "ok" in handle({"sigma_provider": PROTOCOL, "op": "term", "args": {"expr": "I"}, "blobs": {}}))
    here = {n: (Path(__file__).resolve().parent / n).read_bytes() for n in FILES}
    ok("the identity names these bytes", identity_of(here) != identity_of(dict(here, **{"sigma_resume.py": here["sigma_resume.py"] + b"\n"})))
    passed = all(results)
    print(f"PROVIDER: {'ALL PASS' if passed else 'FAILURES'} ({sum(results)}/{len(results)})")
    return 0 if passed else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return selftest()
    if argv == ["serve"]:
        return serve()
    print(f"sigma_provider: unknown verb {' '.join(argv)!r}; verbs: {', '.join(VERBS)} (none runs the self-test)",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
