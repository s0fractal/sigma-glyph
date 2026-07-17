#!/usr/bin/env python3
"""Read-only verifier for the .warrants/ store (Warrant v0.1/v0.2 record bodies; settlement-grade v0.3 checks live in the full CLI).

Shipped so that auditors can verify the adjudication evidence with the same
locality standard as the spec vectors — no external checkout needed.
Checks: record id = SHA-256(canonical JSON body); every Ed25519 signature
over the raw record id; every subject/evidence/check/transcript/under blob
hash; every prior link. Reports DAG roots (the store is a DAG, not a single
chain). Full CLI (why/propose/accept/...): https://github.com/s0fractal/warrant
"""
import glob, hashlib, json, os, sys

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    HAVE_ED25519 = True
except ImportError:
    HAVE_ED25519 = False

STORE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".warrants")


def canon(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


# Reject small-order / non-canonical Ed25519 public keys (Warrant SPEC §5). Such
# a key lets an all-zero signature verify for a fraction of messages, and
# libraries disagree on which they accept — so two auditors split on the same
# store. Byte/integer checks only; agrees with the Warrant CLI by construction.
_ED25519_P = (1 << 255) - 19
_ED25519_SMALL_ORDER = {bytes.fromhex(h) for h in (
    "0100000000000000000000000000000000000000000000000000000000000000",
    "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a",
    "0000000000000000000000000000000000000000000000000000000000000080",
    "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05",
    "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
    "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc85",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac03fa",
    # non-canonical sign-bit variants of the x=0 torsion points (y=1, y=p-1):
    # current libs reject these at decode; blocklisted as defense-in-depth so a
    # lenient third implementation cannot accept them (Gemini 3.1 Pro audit).
    "0100000000000000000000000000000000000000000000000000000000000080",
    "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
)}


def weak_ed25519_pubkey(raw):
    if len(raw) != 32 or raw in _ED25519_SMALL_ORDER:
        return True
    return (int.from_bytes(raw, "little") & ((1 << 255) - 1)) >= _ED25519_P


def main():
    records = {os.path.basename(f)[:-5]: json.load(open(f))
               for f in glob.glob(os.path.join(STORE, "records", "*.json"))}
    blobs = {os.path.basename(f) for f in glob.glob(os.path.join(STORE, "blobs", "*"))}
    errs, roots = [], []
    for rid in sorted(records):
        env = records[rid]
        body = env["body"]
        if hashlib.sha256(canon(body)).hexdigest() != rid:
            errs.append(f"{rid[:12]}: record id != SHA-256(canonical body)")
            continue
        if not body.get("prior"):
            roots.append(rid)
        for p in body.get("prior", []):
            if p not in records:
                errs.append(f"{rid[:12]}: missing prior {p[:12]}")
        refs = [("under", u) for u in body.get("under", [])]
        refs += [("evidence", e) for e in body.get("evidence", [])]
        subj = body.get("subject", {})
        if isinstance(subj, dict) and "hash" in subj:
            refs.append(("subject", subj["hash"]))
        for b in body.get("because", []):
            for k in ("check", "transcript"):
                if b.get("kind") == "check" and b.get(k):
                    refs.append((k, b[k]))
        for kind, h in refs:
            path = os.path.join(STORE, "blobs", h)
            if h not in blobs:
                errs.append(f"{rid[:12]}: missing {kind} blob {h[:12]}")
            elif hashlib.sha256(open(path, "rb").read()).hexdigest() != h:
                errs.append(f"{rid[:12]}: {kind} blob {h[:12]} content mismatch")
        sigs = env.get("sigs", [])
        if not sigs:
            errs.append(f"{rid[:12]}: no signatures")
        for s in sigs:
            if not HAVE_ED25519:
                continue
            try:
                key = bytes.fromhex(s["key"])
                if weak_ed25519_pubkey(key):
                    raise ValueError("small-order or non-canonical pubkey")
                Ed25519PublicKey.from_public_bytes(key).verify(
                    bytes.fromhex(s["sig"]), bytes.fromhex(rid))
            except Exception:
                errs.append(f"{rid[:12]}: bad signature by {s.get('actor')}")
    for e in errs:
        print("ERR ", e)
    print(f"records {len(records)}, blobs {len(blobs)}, "
          f"roots {[r[:12] for r in roots]}, errors {len(errs)}"
          + ("" if HAVE_ED25519 else " (signatures NOT checked: no 'cryptography')"))
    if not HAVE_ED25519:
        sys.exit(2)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
