#!/usr/bin/env python3
"""Read-only verifier for the .warrants/ store (Warrant v0.1/v0.2 record bodies; settlement-grade v0.3 checks live in the full CLI).

Shipped so that auditors can verify the adjudication evidence with the same
locality standard as the spec vectors — no external checkout needed.
Checks: record id = SHA-256(canonical JSON body); every Ed25519 signature over
the domain-separated message of Warrant SPEC v0.4 §5 (47 bytes, built by
tools/warrant_sig.py and nowhere else in this repository); every
subject/evidence/check/transcript/under blob hash; every prior link. Reports
DAG roots (the store is a DAG, not a single chain).
Full CLI (why/propose/accept/...): https://github.com/s0fractal/warrant
"""
import glob, hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warrant_sig  # noqa: E402  (the one signing-message construction)

try:
    import cryptography.hazmat.primitives.asymmetric.ed25519  # noqa: F401
    HAVE_ED25519 = True
except ImportError:
    HAVE_ED25519 = False

STORE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".warrants")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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


def load_records():
    records = {}
    for path in glob.glob(os.path.join(STORE, "records", "*.json")):
        with open(path, encoding="utf-8") as source:
            records[os.path.basename(path)[:-5]] = json.load(source)
    return records


def body_refs(body):
    refs = [("under", value) for value in body.get("under", [])]
    refs.extend(("evidence", value) for value in body.get("evidence", []))
    subject = body.get("subject", {})
    if isinstance(subject, dict) and "hash" in subject:
        refs.append(("subject", subject["hash"]))
    for reason in body.get("because", []):
        if reason.get("kind") != "check":
            continue
        refs.extend((key, reason[key]) for key in ("check", "transcript")
                    if reason.get(key))
    return refs


def blob_error(rid, kind, digest, blobs):
    short = digest[:12] if isinstance(digest, str) else repr(digest)
    if (not isinstance(digest, str) or HEX64.fullmatch(digest) is None
            or digest not in blobs):
        return f"{rid[:12]}: missing {kind} blob {short}"
    path = os.path.join(STORE, "blobs", digest)
    with open(path, "rb") as source:
        actual = hashlib.sha256(source.read()).hexdigest()
    if actual != digest:
        return f"{rid[:12]}: {kind} blob {short} content mismatch"
    return None


def signature_error(rid, signature):
    if not HAVE_ED25519:
        return None
    try:
        key = bytes.fromhex(signature["key"])
        if weak_ed25519_pubkey(key):
            raise ValueError("small-order or non-canonical pubkey")
        # The shared helper constructs/verifies the Warrant v0.4 domain-separated
        # message; this independent auditor deliberately keeps v0.1/v0.2 severity.
        warrant_sig.verify(key, signature["sig"], rid)
        return None
    except Exception:
        return (
            f"{rid[:12]}: bad signature by {signature.get('actor')} "
            f"[pinned v0.1/v0.2 severity: fatal. Warrant SPEC v0.3 s6(3) "
            f"would report this as a WARNING and exclude the signature, "
            f"erroring only if no valid signature by the record's actor "
            f"remained. Re-check with the live CLI before acting on it.]")


def audit_record(rid, env, records, blobs):
    body = env["body"]
    if hashlib.sha256(canon(body)).hexdigest() != rid:
        return [f"{rid[:12]}: record id != SHA-256(canonical body)"], False
    errors = [f"{rid[:12]}: missing prior {prior[:12]}"
              for prior in body.get("prior", []) if prior not in records]
    errors.extend(error for kind, digest in body_refs(body)
                  if (error := blob_error(rid, kind, digest, blobs)) is not None)
    signatures = env.get("sigs", [])
    if not signatures:
        errors.append(f"{rid[:12]}: no signatures")
    errors.extend(error for signature in signatures
                  if (error := signature_error(rid, signature)) is not None)
    return errors, not body.get("prior")


def main():
    records = load_records()
    blobs = {os.path.basename(path)
             for path in glob.glob(os.path.join(STORE, "blobs", "*"))}
    errs, roots = [], []
    for rid in sorted(records):
        record_errors, is_root = audit_record(rid, records[rid], records, blobs)
        errs.extend(record_errors)
        if is_root:
            roots.append(rid)
    for e in errs:
        print("ERR ", e)
    print("scope: pinned Warrant v0.1/v0.2 body checks; settlement-grade v0.3 "
          "(key state, thresholds, tunnels) lives in the full CLI. Signature "
          "severity differs from v0.3 -- see the note on any bad-signature line.")
    print(f"records {len(records)}, blobs {len(blobs)}, "
          f"roots {[r[:12] for r in roots]}, errors {len(errs)}"
          + ("" if HAVE_ED25519 else " (signatures NOT checked: no 'cryptography')"))
    if not HAVE_ED25519:
        sys.exit(2)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
