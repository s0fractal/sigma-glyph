#!/usr/bin/env python3
"""The one place this repository constructs a Warrant signature.

WHY THIS EXISTS
---------------
Warrant SPEC v0.4 §5 domain-separates the signed message:

    msg = "warrant-sig-v1:" || WarrantID_raw          (15 + 32 = 47 bytes)

Before this module, sigma-glyph built that message by hand in SEVEN places
across six files -- two verifiers and five signers -- each an independent copy
of a rule that only means anything if every copy agrees. That is not a style
problem. A signer and a verifier that disagree about the message produce a store
that this repository's own tools split on: one tool reports a valid signature and
another reports a forgery over the identical bytes, which is precisely the
outcome sigma-glyph and warrant exist to make impossible.

It was also not caught by reading. The seven sites were found while migrating to
v0.4, and only because a test went red; nothing in the suite could have named the
copies, so an eighth would have landed the same way. `tests/one_signing_path.py`
is the part that makes this file load-bearing rather than merely tidy: it fails
if any other file open-codes the construction.

WHAT THIS IS NOT
----------------
Not a Warrant implementation. It builds the signed message and wraps
sign/verify; it says nothing about canonicalization, WarrantIDs, thresholds,
key state or settlement, all of which live in the Warrant CLI. It deliberately
does NOT accept the
pre-v0.4 bare-WarrantID message under any flag: a verifier that accepts both
constructions has no domain separation, and an option to re-enable the old one
is the same defect with a switch on it.

`impl/` does not import this module and must not: the Book I/II/III oracles are
a dependency-free reference implementation, and they sign nothing. The Go mirror
in `impl-go/main.go` cannot import Python at all, so the construction is
duplicated there by necessity -- that copy is pinned to this one by
`tests/one_signing_path.py`, which is the only honest thing available across a
language boundary.
"""

# The domain separator, as bytes, written once. Every other occurrence of this
# literal in a .py file in this repository is a test failure -- see
# tests/one_signing_path.py.
SIG_DOMAIN = b"warrant-sig-v1:"

# 15 bytes of separator + 32 raw bytes of WarrantID.
SIG_MESSAGE_LEN = len(SIG_DOMAIN) + 32


class WarrantSigError(ValueError):
    """A WarrantID that is not 64 lowercase hex characters."""


def warrant_id_bytes(warrant_id):
    """The 32 raw bytes of a WarrantID, or raise.

    Accepts the hex form used everywhere in the stores. Rejects anything else
    loudly: a signature over a truncated or upper-cased id is a signature over
    different bytes, and silently normalising it here would move the failure to
    whoever verifies later.
    """
    if isinstance(warrant_id, (bytes, bytearray)):
        if len(warrant_id) != 32:
            raise WarrantSigError(
                f"WarrantID must be 32 raw bytes, got {len(warrant_id)}")
        return bytes(warrant_id)
    if not isinstance(warrant_id, str):
        raise WarrantSigError(
            f"WarrantID must be hex str or 32 bytes, got {type(warrant_id).__name__}")
    if len(warrant_id) != 64 or any(c not in "0123456789abcdef" for c in warrant_id):
        raise WarrantSigError(
            f"WarrantID must be 64 lowercase hex characters, got {warrant_id!r}")
    return bytes.fromhex(warrant_id)


def signing_message(warrant_id):
    """The exact bytes a Warrant signature covers (SPEC v0.4 §5)."""
    msg = SIG_DOMAIN + warrant_id_bytes(warrant_id)
    assert len(msg) == SIG_MESSAGE_LEN, len(msg)
    return msg


def sign(private_key, warrant_id):
    """Sign `warrant_id` with an Ed25519 private key. Returns hex."""
    return private_key.sign(signing_message(warrant_id)).hex()


def verify(public_key, sig, warrant_id):
    """Raise unless `sig` is a valid Warrant signature over `warrant_id`.

    `public_key` may be raw bytes, hex, or an Ed25519PublicKey. `sig` may be hex
    or bytes. Raises rather than returning False: every call site here already
    sits inside a try/except that decides the severity, and the severities are
    NOT the same (the Warrant verifier reports validity, while governance
    counting decides whether a valid signature counts), so this must not decide
    for them.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if isinstance(public_key, str):
        public_key = bytes.fromhex(public_key)
    if isinstance(public_key, (bytes, bytearray)):
        public_key = Ed25519PublicKey.from_public_bytes(bytes(public_key))
    if isinstance(sig, str):
        sig = bytes.fromhex(sig)
    public_key.verify(bytes(sig), signing_message(warrant_id))


def is_valid(public_key, sig, warrant_id):
    """Boolean form of `verify` for call sites that want one. Never raises."""
    try:
        verify(public_key, sig, warrant_id)
        return True
    except Exception:
        return False


def sig_entry(actor, private_key, warrant_id):
    """One `{actor, key, sig}` element of a Warrant envelope's `sigs` list.

    Five of the seven pre-consolidation sites built this dict inline, which is
    why it is here: the public key and the signature must come from the same
    private key, and writing them on separate lines is how they stop doing so.
    """
    return {
        "actor": actor,
        "key": private_key.public_key().public_bytes_raw().hex(),
        "sig": sign(private_key, warrant_id),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        sys.stdout.write(signing_message(sys.argv[1]).hex() + "\n")
    else:
        sys.exit("usage: python3 tools/warrant_sig.py <warrant-id-hex64>\n"
                 "prints the hex of the 47 bytes a signature covers")
