#!/usr/bin/env python3
"""sigma-resume, two engines, one corpus (redesign P5: N61, N62, N69).

The Python reference (impl/sigma_resume.py) and the Rust engine
(`impl-rs/target/release/book1 resume`) run the same states, budgets and
environments; every supported outcome must agree on outcome, state bytes,
spent, actions, peak and the missing hash. Local limits are compared as local
outcomes, never against a canonical answer.

Scope: the Book I runtime profile. The rich profile (Y, M, W) has no Rust
engine yet; this file says so instead of comparing it.
"""
import hashlib
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_glyph as G      # noqa: E402
import sigma_resume as R     # noqa: E402

import os  # noqa: E402
# BOOK1 lets a negative control point this test at a deliberately broken engine.
BOOK1 = Path(os.environ.get("BOOK1") or ROOT / "impl-rs" / "target" / "release" / "book1")
CID = hashlib.sha256(b"differential corpus").hexdigest()
I, K, S = G.I_H, G.K_H, G.S_H
results = {}


def app(left, right):
    return G.ser(G.APPLY, G.F_LEFT | G.F_RIGHT, left=left, right=right)


def rust(state, available, manifest, delivered, max_actions=None):
    req = {"available": available, "state": state.hex(), "manifest": sorted(h.hex() for h in manifest),
           "delivered": {h.hex(): b.hex() for h, b in delivered.items()}}
    if max_actions is not None:
        req["max_actions"] = max_actions
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(req, f)
    r = subprocess.run([str(BOOK1), "resume", f.name], capture_output=True, text=True, check=False)
    Path(f.name).unlink()
    return json.loads(r.stdout)


def python(state, available, manifest, delivered, max_actions=None):
    if len(state) > R.MAX_STATE_BYTES if hasattr(R, "MAX_STATE_BYTES") else False:
        return {"outcome": "ADMISSION_REFUSED"}
    if available > G.VERIFIER_LIMITS["max_atp"]:
        return {"outcome": "ADMISSION_REFUSED"}
    _, term = R.decode_state(state)
    env = R.Environment(list(manifest), dict(delivered))
    term, spent, actions, peak, outcome, _ = R._run(term, available, env, G.VERIFIER_LIMITS, max_actions)
    outcome = outcome or "INCOMPLETE"           # the reference names an action limit by detail only
    missing = env.missing.hex() if outcome == "BLOCKED_REFERENCE" and env.missing else None
    if outcome in ("EVIDENCE_UNAVAILABLE", "CAS_MISMATCH"):
        missing = "local"
    return {"outcome": outcome, "state": R.encode_state(CID, term).hex(), "spent": spent,
            "actions": actions, "peak": peak, "missing": missing}


def same(py, rs):
    keys = ("outcome", "state", "spent", "actions", "peak")
    if any(py.get(k) != rs.get(k) for k in keys if k in py or k in rs):
        return False
    if py["outcome"] == "BLOCKED_REFERENCE":
        return py["missing"] == rs.get("missing")
    return True


def corpus():
    """(label, term hash, manifest, delivered). Built, never hand-written bytes."""
    out = []
    store = {}

    def put(b):
        h = G.node_hash(b)
        store[h] = b
        return h
    skk = put(app(put(app(S, K)), K))
    kis = put(app(put(app(K, I)), S))
    prog = put(app(skk, kis))
    a = put(app(put(app(S, I)), I))
    omega = put(app(a, a))
    ghost = G.node_hash(b"absent")
    blocked = put(app(I, ghost))
    dead = put(app(put(app(K, I)), ghost))
    base = dict(store)
    out += [("SKK (KIS)", prog, set(base), base), ("Omega", omega, set(base), base),
            ("I ghost: blocked", blocked, set(base), base),
            ("K I ghost: dead branch", dead, set(base), base),
            ("I ghost: in manifest, not delivered", blocked, set(base) | {ghost}, base)]
    wrong = dict(base)
    wrong[prog] = app(K, I)
    out.append(("wrong bytes under a hash", prog, set(base), wrong))
    rng = random.Random(20261017)
    for n in range(120):
        def rand(d):
            if d == 0 or rng.random() < 0.3:
                return rng.choice([I, K, S])
            return put(app(rand(d - 1), rand(d - 1)))
        h = rand(5)
        out.append((f"random #{n}", h, set(store), dict(store)))
    return out


WORKER = ROOT / "impl-rs" / "wasm-resume" / "resume_worker.mjs"
WASM = ROOT / "impl-rs" / "wasm-resume" / "target" / "wasm32-unknown-unknown" / "release" / "sigma_resume_wasm.wasm"


def wasm(state, available, manifest, delivered, deadline_ms=10000):
    req = {"available": available, "state": state.hex(), "manifest": sorted(h.hex() for h in manifest),
           "delivered": {h.hex(): b.hex() for h, b in delivered.items()}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(req, f)
    r = subprocess.run(["node", str(WORKER), f.name, str(deadline_ms)], capture_output=True, text=True, check=False)
    Path(f.name).unlink()
    return json.loads(r.stdout)


def wasm_route(budgets):
    """The same engine file built for wasm32, run in a disposable JS worker."""
    import shutil
    if not WASM.is_file() or shutil.which("node") is None:
        print("UNRUN N69-wasm: wasm build or node missing (cargo build --release --target wasm32-unknown-unknown)")
        return
    agree = total = 0
    for label, h, manifest, delivered in corpus()[:12]:
        state = R.encode_state(CID, ("thunk", h))
        for b in budgets[::2]:
            total += 1
            agree += rust(state, b, manifest, delivered) == wasm(state, b, manifest, delivered)
    case("N69-wasm", agree == total, f"wasm-in-worker agrees with native Rust on {agree}/{total} runs")
    _, omega, man, dl = corpus()[1]
    late = wasm(R.encode_state(CID, ("thunk", omega)), G.VERIFIER_LIMITS["max_atp"], man, dl, deadline_ms=50)
    case("N62-worker", late == {"outcome": "DEADLINE"},
         "deadline in the worker: the worker is terminated, DEADLINE is local, no state and no answer", late)


def case(nid, ok, what, detail=""):
    results[nid] = ok
    print(("ok    " if ok else "FAIL  ") + f"{nid} {what}" + ("" if ok else f" | {detail}"))


def main():
    if not BOOK1.is_file():
        print("UNRUN  impl-rs not built (cargo build --release in impl-rs)")
        return 3
    budgets = [0, 1, 2, 3, 5, 8, 13, 50, 500]
    agree, total, first_bad, kinds = 0, 0, None, set()
    for label, h, manifest, delivered in corpus():
        state = R.encode_state(CID, ("thunk", h))
        for b in budgets:
            for limit in (None, 2):
                py = python(state, b, manifest, delivered, limit)
                rs = rust(state, b, manifest, delivered, limit)
                total += 1
                kinds.add(py["outcome"])
                if same(py, rs):
                    agree += 1
                elif first_bad is None:
                    first_bad = (label, b, limit, py, rs)
    case("N69", agree == total, f"Python and Rust agree on {agree}/{total} runs; outcomes covered: {sorted(kinds)}",
         first_bad)
    big = R.encode_state(CID, ("thunk", I))
    huge_avail = rust(big, G.VERIFIER_LIMITS["max_atp"] + 1, set(), {})
    py_avail = python(big, G.VERIFIER_LIMITS["max_atp"] + 1, set(), {})
    case("N61", huge_avail["outcome"] == py_avail["outcome"] == "ADMISSION_REFUSED",
         "available credit over the local ceiling: ADMISSION_REFUSED in both, before any decode",
         (huge_avail, py_avail))
    _, prog, man, dl = corpus()[0]
    st = R.encode_state(CID, ("thunk", prog))
    cut_py, cut_rs = python(st, 500, man, dl, 3), rust(st, 500, man, dl, 3)
    resumed = rust(bytes.fromhex(cut_rs["state"]), 500 - cut_rs["spent"], man, dl)
    whole = rust(st, 500, man, dl)
    case("N62", cut_py["outcome"] == cut_rs["outcome"] == "INCOMPLETE" and cut_py["state"] == cut_rs["state"]
         and resumed["state"] == whole["state"] and cut_rs["spent"] + resumed["spent"] == whole["spent"],
         "stopped by a limit: INCOMPLETE with the last atomic state, which resumes to the same normal form",
         (cut_py, cut_rs))
    wasm_route(budgets)
    print()
    print("RESUME DIFFERENTIAL:", "ALL AGREE" if all(results.values()) else "DISAGREEMENT")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
