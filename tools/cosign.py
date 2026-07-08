#!/usr/bin/env python3
"""Append a co-signature to a warrant envelope in .warrants/records/.

    python3 tools/cosign.py <warrant-id> <actor-id> <keyfile>

Signs the raw WarrantID bytes with the Ed25519 seed in <keyfile> (hex64, one
line) and appends {actor, key, sig} to the envelope's sigs. Co-signatures
never change a warrant's identity (Warrant SPEC §5) — the body is untouched
and the record id stays the hash of the body. Refuses double-signing by the
same key and verifies the body hash before touching anything.
"""
import hashlib, json, os, sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canon(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    wid, actor, keyfile = sys.argv[1], sys.argv[2], sys.argv[3]
    path = os.path.join(REPO, ".warrants", "records", wid + ".json")
    env = json.load(open(path))
    if hashlib.sha256(canon(env["body"])).hexdigest() != wid:
        sys.exit("record id != SHA-256(canonical body) — refusing")
    seed = open(os.path.expanduser(keyfile)).read().strip()
    sk = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
    pub = sk.public_key().public_bytes_raw().hex()
    if any(s.get("key") == pub for s in env.get("sigs", [])):
        sys.exit(f"key {pub[:12]}… already signed this warrant")
    env.setdefault("sigs", []).append(
        {"actor": actor, "key": pub,
         "sig": sk.sign(bytes.fromhex(wid)).hex()})
    with open(path, "w") as f:
        json.dump(env, f, indent=2, sort_keys=True, ensure_ascii=False)
    print(f"co-signed {wid[:12]}… as {actor} ({len(env['sigs'])} sigs)")


if __name__ == "__main__":
    main()
