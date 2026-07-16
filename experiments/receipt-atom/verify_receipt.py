#!/usr/bin/env python3
"""Self-verifying verdict-receipt — one atom.

Reuses sigma-glyph/warrant primitives ONLY (JCS `canon` + Ed25519 from
`tools/anchor_governance.py`, and the existing `anchor_governance.py replay`
tool as the deterministic computation). No new crypto, no new schema family:
a receipt is a warrant-style `{body, sig}` envelope whose body NAMES a
deterministic computation over content-addressed inputs plus the result the
producer claims.

The whole point: **VERIFIED means the fact was RE-DERIVED here.** The signature
binds *who* produced the receipt, never *whether* the claim is true. A verifier
(human or model) trusts the producer for the fact by exactly zero.

    python3 verify_receipt.py --mint    # producer side: emit receipt.json (+ inputs/)
    python3 verify_receipt.py           # any second node: verify from the bytes

The second node needs only: this file, receipt.json, inputs/, and the sigma-glyph
repo the computation names. It does NOT need the producer's reasoning.
"""
import hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))          # sigma-glyph root
sys.path.insert(0, os.path.join(REPO, "tools"))
from cryptography.hazmat.primitives.asymmetric.ed25519 import (   # noqa: E402
    Ed25519PrivateKey, Ed25519PublicKey)

RECEIPT = os.path.join(HERE, "receipt.json")
INPUTS = os.path.join(HERE, "inputs")
TAG = "sigma-glyph.verdict-receipt@v1"
# demo producer identity: "whoever holds this seed" — a fixed seed so the demo
# is reproducible. Identity only; it never makes the claim true.
_SEED = hashlib.sha256(b"receipt-atom:demo-producer").digest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def _run_replay(vectors_path):
    """The named deterministic computation, re-executed by whoever verifies."""
    out = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "anchor_governance.py"),
         "replay", vectors_path],
        capture_output=True, text=True)
    return out.stdout + out.stderr


def mint():
    sk = Ed25519PrivateKey.from_private_bytes(_SEED)
    pub = sk.public_key().public_bytes_raw().hex()
    src = os.path.join(REPO, "tests", "spec_conformance", "governance_vectors.json")
    raw = open(src, "rb").read()
    os.makedirs(INPUTS, exist_ok=True)
    open(os.path.join(INPUTS, "governance_vectors.json"), "wb").write(raw)
    digest = sha256(raw)
    # run the computation once at mint time to record the claimed result
    observed = _run_replay(os.path.join(INPUTS, "governance_vectors.json"))
    expect = "GOVERNANCE-REPLAY: ALL PASS (20/20)"
    assert expect in observed, "producer cannot mint a claim it cannot itself derive"
    body = {
        "receipt": TAG,
        "claim": ("The governance conformance vectors replay ALL PASS (20/20) — "
                  "the exact fact deepseek/gemini had to TRUST from a pasted "
                  "transcript at the v0.6.6 §0 gate. This receipt lets a second "
                  "node re-derive it instead of trusting the producer."),
        "computation": {
            "reexecute": "tools/anchor_governance.py replay <inputs/governance_vectors.json>",
            "expect_substring": expect,
        },
        "inputs": {"governance_vectors.json": digest},
        "producer": {"id": "receipt-atom:demo-producer", "key": pub},
    }
    rid = sha256(canon(body))
    env = {"body": body, "sig": sk.sign(bytes.fromhex(rid)).hex()}
    with open(RECEIPT, "w") as f:
        json.dump(env, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(f"minted {os.path.relpath(RECEIPT, HERE)}  (receipt id {rid[:12]}…)")


def verify():
    env = json.load(open(RECEIPT))
    body = env["body"]
    checks = []

    # 1. signature binds body <-> producer key. IDENTITY ONLY — proves who,
    #    not whether-true. We record it but it never counts toward the fact.
    rid = sha256(canon(body))
    key = body.get("producer", {}).get("key", "")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(
            bytes.fromhex(env["sig"]), bytes.fromhex(rid))
        sig_ok = True
    except Exception:
        sig_ok = False
    checks.append(("producer signature (identity only)", sig_ok))

    # 2. content-address integrity: the delivered input bytes hash to what the
    #    body commits to. Now we KNOW which bytes the claim is about.
    inputs_ok = True
    for name, digest in body.get("inputs", {}).items():
        p = os.path.join(INPUTS, name)
        got = sha256(open(p, "rb").read()) if os.path.exists(p) else None
        ok = (got == digest)
        inputs_ok &= ok
        checks.append((f"input {name} hash == committed", ok))

    # 3. THE FACT: re-execute the named computation over those exact bytes and
    #    confirm the producer's claimed result. This is where trust becomes 0.
    expect = body["computation"]["expect_substring"]
    fact_ok = False
    if inputs_ok:
        observed = _run_replay(os.path.join(INPUTS, "governance_vectors.json"))
        fact_ok = expect in observed
    checks.append((f"re-derived: {expect!r}", fact_ok))

    verified = inputs_ok and fact_ok       # note: NOT gated on sig_ok
    print("RECEIPT", body["receipt"])
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print()
    print("VERIFIED" if verified else "FAILED", "—",
          "the fact was re-derived from the bytes; trust in the producer for it = 0."
          if verified else "the claim did not reproduce.")
    print("(the signature proves WHO produced this receipt, never WHETHER the claim is true;",
          "VERIFIED does not depend on it.)")
    return 0 if verified else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mint":
        mint()
    else:
        sys.exit(verify())
