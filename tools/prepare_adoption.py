#!/usr/bin/env python3
"""Build the adoption warrant for a frozen anchor set — and sign nothing.

    python3 tools/prepare_adoption.py gates/v0.7.0-candidate \
        --actor s0fractal@sigma-glyph --ts 1788000000

Adoption is a threshold warrant over the anchor-set blob, not a file edit and not
a tag. This assembles the exact body that warrant would carry, computes the
WarrantID it would have, and writes it out **unsigned**, outside `.warrants/`, so
that nothing in this repository can mistake a draft for a filed record.

It handles no keys. It has no `--sign`. It cannot acquire one by being run again
with different arguments. Signing is `tools/cosign.py` with a keyfile, run by the
person or actor who holds that key, and the commands are printed here for them to
read rather than executed here on their behalf.

Two fields cannot be chosen by a preparer, which is why they are required
arguments rather than defaults:

  --actor  the id of the actor filing the warrant. It is inside the body, so it
           is inside the WarrantID: a body prepared for one filer is not the body
           another filer signs.
  --ts     the filing timestamp, likewise inside the body. There is no honest
           default; "now" would produce an ID that expires the moment you read
           it.

So there is no single WarrantID for this adoption until those two are fixed. A
document that states one without stating them is stating a guess.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ".warrants"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# The governance policy pair in force, from the v0.6.7 adoption warrant's `under`.
GOVERNANCE_PROFILE = "b86122047ed676efa70975de368ba1e99582705163b8f5d61f4351b16003974c"
THRESHOLD_POLICY = "f4fe3a55d7c2a62c18ab14eed3b38ee03d9822d0051c430ab6b9f7a41ad3f16f"


def canon(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def blob_of(digest):
    """A blob, if it is one and parses. Not every blob in the store is JSON.

    A content address is a filename, not a path: the digest is checked against
    hex64 before it is joined to anything, because some of these values arrive
    from records this tool did not write.
    """
    if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
        return None
    path = ROOT / STORE / "blobs" / digest
    if not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_bytes())
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def prior_adoption():
    """The currently adopted anchor set's warrant, which this one succeeds."""
    records = ROOT / STORE / "records"
    latest = None
    for path in sorted(records.glob("*.json")):
        record = json.loads(path.read_text())
        subject = record.get("body", {}).get("subject", {}).get("hash")
        blob = blob_of(subject) if subject else None
        if blob and blob.get("governance") == "sigma-glyph.anchor-set@v1":
            ts = record["body"].get("ts", 0)
            if latest is None or ts > latest[0]:
                latest = (ts, path.stem, blob.get("release"))
    return latest


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("freeze", help="directory holding anchor-set.json")
    parser.add_argument("--actor", required=True,
                        help="id of the actor filing the warrant")
    parser.add_argument("--ts", required=True, type=int,
                        help="filing timestamp, seconds since the epoch")
    parser.add_argument("--because", help="override the stated reason")
    args = parser.parse_args()

    freeze = Path(args.freeze.rstrip("/"))
    blob_bytes = (ROOT / freeze / "anchor-set.json").read_bytes()
    blob = json.loads(blob_bytes)
    subject = hashlib.sha256(blob_bytes).hexdigest()

    threshold = blob_of(THRESHOLD_POLICY)
    if threshold is None:
        sys.exit(f"threshold policy blob {THRESHOLD_POLICY[:12]} is not in the store")
    roster = threshold["threshold"]["actors"]
    minimum = threshold["threshold"]["min_sigs"]
    if args.actor not in roster:
        sys.exit(f"{args.actor} is not on the roster {roster}; a warrant filed by "
                 f"an actor the policy does not name cannot reach the threshold")

    previous = prior_adoption()
    if previous is None:
        sys.exit("no prior anchor-set adoption found in .warrants/")
    _, prior_id, prior_release = previous
    prior_record = json.loads(
        (ROOT / STORE / "records" / f"{prior_id}.json").read_text())
    if blob.get("ancestor") and blob["ancestor"] != prior_record["body"]["subject"]["hash"]:
        print(f"warning: this set's ancestor is not the currently adopted "
              f"{prior_release} set; that makes it a fork, not a successor",
              file=sys.stderr)

    reason = args.because or (
        f"ADOPT {blob['release']} anchor-set: "
        "eval is a relation over three inputs, the receipt carries the exit, "
        "admission is a deployment boundary, one arbiter for all three Books")
    body = {
        "warrant": "0.2",
        "decision": "accept",
        "subject": {"hash": subject},
        "because": [{"kind": "prose", "text": reason}],
        "evidence": [],
        "under": [GOVERNANCE_PROFILE, THRESHOLD_POLICY],
        "prior": [prior_id],
        "actor": {"id": args.actor},
        "ts": args.ts,
    }
    warrant_id = hashlib.sha256(canon(body)).hexdigest()
    envelope = {"body": body, "sigs": []}

    out = ROOT / freeze / "adoption-warrant.unsigned.json"
    out.write_text(json.dumps(envelope, indent=1, sort_keys=True,
                              ensure_ascii=False) + "\n")

    print(f"release          {blob['release']}")
    print(f"subject (blob)   {subject}")
    print(f"ancestor         {blob.get('ancestor')}")
    print(f"prior warrant    {prior_id}  ({prior_release})")
    print(f"filed by         {args.actor}")
    print(f"ts               {args.ts}")
    print(f"threshold        {minimum}-of-{len(roster)}: {', '.join(roster)}")
    print(f"WarrantID        {warrant_id}")
    print(f"\nwritten unsigned to {out.relative_to(ROOT)} — 0 signatures\n")
    print("To file it, the holder of the first key runs, from the repository root:\n")
    print(f"    cp {out.relative_to(ROOT)} {STORE}/records/{warrant_id}.json")
    print(f"    cp {(freeze / 'anchor-set.json')} {STORE}/blobs/{subject}")
    print(f"    python3 tools/cosign.py {warrant_id} <actor-id> <keyfile>\n")
    print(f"and {minimum - 1} further roster actor(s) run the last line with their "
          f"own id and key.\nThen, to check that it settles rather than merely "
          f"exists:\n")
    print("    python3 tools/warrant_gate.py .warrants")
    print("    python3 tools/anchor_governance.py status "
          "--trust-config <out-of-band config> --enforce\n")
    print("The trust config MUST come from outside this tree (GOV-anchors §2). "
          "A run\nthat reads it from the repository proves nothing about the "
          "repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
