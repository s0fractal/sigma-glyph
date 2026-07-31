#!/usr/bin/env python3
"""There is exactly one construction of a Warrant signing message in this tree.

    python3 tests/one_signing_path.py

WHY THIS EXISTS
---------------
Warrant SPEC v0.4 §5 says a signature covers `"warrant-sig-v1:" || WarrantID_raw`
(47 bytes). Migrating to it found SEVEN hand-rolled copies of that rule across
six files -- two verifiers and five signers -- and found them only because
something unrelated went red. Nothing in the suite could name the copies, so
copy number eight would have arrived the same way: silently, agreeing with the
spec on the day it was written and drifting from it afterwards. (Copy number
eight in fact already existed, in Go; see the impl-go section below.)

A duplicated crypto construction is not a tidiness problem. If one copy drifts,
this repository ships a store where its own verifier and its own governance
adjudicator disagree about the same bytes -- one reporting a valid signature and
the other a forgery. Two conforming implementations disagreeing is the outcome
sigma-glyph and warrant both exist to forbid, and it would be produced here by a
line of code, not by an attacker.

So: the construction lives in `tools/warrant_sig.py`. This test fails if any
other file builds it, and it fails for the two distinct ways a copy appears.

THE TWO FAILURE SHAPES
----------------------
A. **A visible copy.** The literal `warrant-sig-v1` appears in a .py file other
   than the module. That is someone re-deriving the rule -- which will be right
   today.
B. **A silent copy.** A `.sign(...)` or `.verify(...)` whose MESSAGE argument is
   a bare `bytes.fromhex(...)` -- the pre-v0.4 construction, written by someone
   who did not know about the separator at all. This is the more dangerous
   shape, because it contains no distinctive string to grep for, and it is
   exactly what all seven original sites looked like before migration.

Shape B needs an allowlist, and the allowlist is the interesting part of this
file: an entry must name a file AND a reason, and a reason has to be a claim
about a DIFFERENT protocol, not "this one is fine". A stale entry -- one whose
file no longer signs a bare digest -- is itself a failure, because an exemption
outliving its subject is how the next copy gets in under it.

WHAT THIS DOES NOT DO
---------------------
It reads source text. It does not prove the module is correct; the executable
part of that is the round-trip and the two negative vectors at the end, and the
real guarantee is `tests/governance_differential.py` driving Python against Go
over the same records. It cannot see a copy in a language it does not scan, or
one assembled at runtime from string fragments, or one in an untracked file. It
is a floor, not a ceiling: it makes copy number eight impossible to add by
accident, which is the failure that actually happened here.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import warrant_sig  # noqa: E402

MODULE = "tools/warrant_sig.py"
GO_MIRROR = "impl-go/main.go"
SELF = "tests/one_signing_path.py"

# Two files are exempt from the source scans, for two different reasons:
#   MODULE -- it IS the construction.
#   SELF   -- it names the literal in order to search for it, and it signs a
#             bare digest on purpose, as the negative control proving that the
#             old construction does not verify. A test that could not write the
#             wrong thing could not show that the wrong thing is rejected.
SELF_EXEMPT = {MODULE, SELF}

# Shape B allowlist: path -> why signing a bare digest is CORRECT there.
BARE_DIGEST_ALLOWED = {
    "experiments/receipt-atom/verify_receipt.py":
        "sigma-glyph.verdict-receipt@v1 is NOT a Warrant: different envelope "
        "shape ({body, sig} with no sigs[]/actor/key), different tag, and its "
        "id is a receipt id rather than a WarrantID. Its signature must not be "
        "reachable as a Warrant signature, and after v0.4 it is not -- which is "
        "the property warrant-sig-v1 exists to give. RECORDED, NOT FIXED: that "
        "protocol has no domain separator of its own, so a receipt signature "
        "remains reachable as some OTHER bare-digest protocol's signature. It "
        "is an experiment, and changing its construction would move the "
        "receipt.json committed beside it.",
}

# impl/ is a dependency-free reference implementation (Book I/II/III oracles).
# It signs nothing and must not acquire a dependency on tools/. The import
# direction is one-way and this asserts it, because the cheapest way to "fix" a
# future signing site in impl/ would be to cross that line.
NO_TOOLS_IMPORT = "impl/"

LITERAL = warrant_sig.SIG_DOMAIN.decode().rstrip(":")   # "warrant-sig-v1"

# Whole-file (not per-line) searches: every original copy was written across two
# lines, so a line-anchored pattern would have found none of them.
BARE_SIGN = re.compile(r"\.sign\(\s*bytes\.fromhex\(", re.S)
BARE_VERIFY = re.compile(
    r"\.verify\(\s*(?:[^,()]|\([^()]*\))*,\s*bytes\.fromhex\(", re.S)


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as f:
        return f.read()


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def main():
    files = tracked_files()
    failures = []
    checks = 0

    if MODULE not in files:
        print(f"FAIL  {MODULE} is not tracked -- there is no one signing path")
        return 1

    py = [p for p in files if p.endswith(".py") and p not in SELF_EXEMPT]

    # --- Shape A: the literal appears outside the module -------------------
    for path in py:
        checks += 1
        text = read(path)
        for m in re.finditer(re.escape(LITERAL), text):
            failures.append(
                f"{path}:{line_of(text, m.start())}: open-codes the signing "
                f"domain ({LITERAL!r}). The construction belongs in {MODULE}: "
                f"`import warrant_sig` and call warrant_sig.sign / .verify / "
                f".sig_entry.")

    # --- Shape B: signing or verifying a bare digest ------------------------
    for path in py:
        checks += 1
        if path in BARE_DIGEST_ALLOWED:
            continue
        text = read(path)
        for pat in (BARE_SIGN, BARE_VERIFY):
            for m in pat.finditer(text):
                failures.append(
                    f"{path}:{line_of(text, m.start())}: signs or verifies a "
                    f"BARE digest -- the pre-v0.4 construction. SPEC v0.4 §5 "
                    f"covers '{LITERAL}:' || WarrantID_raw. Use {MODULE}. If "
                    f"these bytes really are another protocol's, add the file "
                    f"to BARE_DIGEST_ALLOWED here, with the reason.")

    # --- An exemption must still have a subject -----------------------------
    for path in BARE_DIGEST_ALLOWED:
        checks += 1
        if path not in files:
            failures.append(f"BARE_DIGEST_ALLOWED names {path}, which is not "
                            f"tracked. Remove the exemption.")
            continue
        text = read(path)
        if not (BARE_SIGN.search(text) or BARE_VERIFY.search(text)):
            failures.append(
                f"BARE_DIGEST_ALLOWED exempts {path}, but it no longer signs "
                f"or verifies a bare digest. Remove the exemption.")

    # --- impl/ stays dependency-free ----------------------------------------
    for path in py:
        if not path.startswith(NO_TOOLS_IMPORT):
            continue
        checks += 1
        text = read(path)
        if re.search(r"^\s*(?:import\s+warrant_sig|from\s+warrant_sig\s)", text,
                     re.M):
            failures.append(
                f"{path} imports warrant_sig. impl/ is a dependency-free "
                f"reference implementation and must not depend on tools/. If a "
                f"signing site is genuinely needed in impl/, the boundary moves "
                f"deliberately -- it is not crossed to satisfy this test.")

    # --- The Go mirror is pinned to the module ------------------------------
    # impl-go cannot import Python, so that copy is legitimate and is the ONLY
    # legitimate one. It is compared against the module's own constant rather
    # than against a string written a second time in this file.
    go = read(GO_MIRROR)
    checks += 1
    if f'"{warrant_sig.SIG_DOMAIN.decode()}"' not in go:
        failures.append(
            f"{GO_MIRROR} does not contain the domain separator "
            f"{warrant_sig.SIG_DOMAIN.decode()!r} that {MODULE} defines. The "
            f"Go governance verifier and the Python one would then disagree "
            f"about which signatures count.")
    checks += 1
    if re.search(r"ed25519\.Verify\([^,]+,\s*ridBytes\s*,", go):
        failures.append(
            f"{GO_MIRROR}: ed25519.Verify over the bare ridBytes -- the "
            f"pre-v0.4 construction. It must verify the domain-separated "
            f"message.")

    # --- The module does what everything above assumes ----------------------
    wid = "a" * 64
    checks += 1
    msg = warrant_sig.signing_message(wid)
    if msg != b"warrant-sig-v1:" + bytes.fromhex(wid) or len(msg) != 47:
        failures.append(
            f"warrant_sig.signing_message is wrong: {msg!r} ({len(msg)} bytes)")

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey)
    except ImportError:
        print("FAIL  'cryptography' is required to execute the round-trip; a "
              "source scan alone is not this test's claim")
        return 1

    sk = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    entry = warrant_sig.sig_entry("someone@somewhere", sk, wid)
    checks += 1
    if not warrant_sig.is_valid(entry["key"], entry["sig"], wid):
        failures.append("warrant_sig.sig_entry produced a signature that its "
                        "own verify rejects")

    # The negative that gives the positive its meaning: a signature made the OLD
    # way must NOT verify. A verifier accepting both has no domain separation.
    checks += 1
    if warrant_sig.is_valid(entry["key"], sk.sign(bytes.fromhex(wid)).hex(), wid):
        failures.append("a pre-v0.4 bare-WarrantID signature VERIFIES -- the "
                        "domain separation is not in force")

    checks += 1
    if warrant_sig.is_valid(entry["key"], entry["sig"], "b" * 64):
        failures.append("a signature over one WarrantID verifies against "
                        "another")

    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        print(f"\nONE-SIGNING-PATH: {len(failures)} FAILURES ({checks} checks)")
        return 1
    print(f"ONE-SIGNING-PATH: ALL PASS ({checks} checks; the construction "
          f"exists in {MODULE} and, of necessity, in {GO_MIRROR})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
