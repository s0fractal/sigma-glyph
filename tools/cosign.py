#!/usr/bin/env python3
"""Append a co-signature to a warrant envelope in .warrants/records/.

    python3 tools/cosign.py <warrant-id> <actor-id> <keyfile>

Signs the Warrant SPEC v0.4 §5 domain-separated message (built by
tools/warrant_sig.py, never here) with the Ed25519 seed in <keyfile> (hex64,
one line), and appends {actor, key, sig} to the envelope's sigs.
Co-signatures never change a warrant's identity (Warrant SPEC §5) — the
body is untouched and the record id stays the hash of the body. Refuses
double-signing by the same key and verifies the body hash before touching
anything.
"""
import hashlib, json, os, re, sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warrant_sig  # noqa: E402  (the one signing-message construction)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RECORDS = os.path.join(REPO, ".warrants", "records")


def canon(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def record_path(wid):
    """Resolve a content-addressed record name without accepting a path."""
    if not isinstance(wid, str) or HEX64.fullmatch(wid) is None:
        raise ValueError(
            "warrant id must be exactly 64 lowercase hexadecimal characters")
    path = os.path.join(RECORDS, wid + ".json")
    if os.path.islink(path):
        raise ValueError("warrant record must not be a symbolic link")
    return path


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    wid, actor, keyfile = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        path = record_path(wid)
    except ValueError as exc:
        sys.exit(str(exc))
    with open(path, encoding="utf-8") as src:
        env = json.load(src)
    if hashlib.sha256(canon(env["body"])).hexdigest() != wid:
        sys.exit("record id != SHA-256(canonical body) — refusing")
    with open(os.path.expanduser(keyfile), encoding="utf-8") as src:
        seed = src.read().strip()
    sk = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
    pub = sk.public_key().public_bytes_raw().hex()
    if any(s.get("key") == pub for s in env.get("sigs", [])):
        sys.exit(f"key {pub[:12]}… already signed this warrant")
    env.setdefault("sigs", []).append(warrant_sig.sig_entry(actor, sk, wid))
    with open(path, "w") as f:
        json.dump(env, f, indent=2, sort_keys=True, ensure_ascii=False)
    print(f"co-signed {wid[:12]}… as {actor} ({len(env['sigs'])} sigs)")


if __name__ == "__main__":
    main()
