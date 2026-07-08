#!/usr/bin/env python3
"""Read-only verifier for ADR-007 governed anchors (PROPOSED — see proposals/ADR-007-governed-anchors.md).

Answers "is the current ANCHORS.txt release authorized?" as a pure function of
(.warrants store, trust config), with an exit code. Until ADR-007 passes its
gate and a first adoption warrant is filed, `status` honestly reports
UNGOVERNED — this tool existing first is the Decision Process's implementation
precondition, not an activation.

Commands:
  status    [default] report governance state of the current ANCHORS.txt section
  make-blob print the canonical anchor-set blob for the current section (JCS)
  selftest  exercise the verification logic against fixture stores

Key binding model: signatures count only for keys listed in trust-config
`actors` (genesis binding). Rotation-derived key state (Warrant §5.1) is the
full CLI's job; on any rotation warrant in the store this tool refuses with
`ERR: key-state warrants present — verify with the warrant CLI` rather than
silently mis-binding.
"""
import hashlib, json, os, re, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHORS = os.path.join(REPO, "spec", "ANCHORS.txt")
STORE = os.path.join(REPO, ".warrants")
TRUST = os.path.join(REPO, "trust-config.json")

PROFILE_TAG = "sigma-glyph.anchor-governance@v1"
ANCHOR_SET_TAG = "sigma-glyph.anchor-set@v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey)
    HAVE_ED25519 = True
except ImportError:
    HAVE_ED25519 = False


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


# ---------- ANCHORS.txt projection ----------

def parse_anchors(path):
    """Return [(release, historical, [(path, anchor), ...])] in file order."""
    sections, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^== (v[\w.]+)\s*(\(.*\))?\s*==\s*$", line)
        if m:
            cur = (m.group(1), bool(m.group(2)), [])
            sections.append(cur)
            continue
        m = re.match(r"^([0-9a-f]{64})\s+(\S+)\s*$", line)
        if m and cur is not None:
            cur[2].append((m.group(2), m.group(1)))
    return sections


def anchor_set_blob(release, entries, ancestor=None):
    blob = {"governance": ANCHOR_SET_TAG, "release": release,
            "anchors": [{"path": p, "anchor": a}
                        for p, a in sorted(entries)]}
    if ancestor is not None:
        blob["ancestor"] = ancestor
    return blob


# ---------- store ----------

def load_store(store):
    recs = {}
    rdir = os.path.join(store, "records")
    if os.path.isdir(rdir):
        for f in os.listdir(rdir):
            if f.endswith(".json"):
                recs[f[:-5]] = json.load(open(os.path.join(rdir, f)))
    bdir = os.path.join(store, "blobs")
    blobs = set(os.listdir(bdir)) if os.path.isdir(bdir) else set()
    return recs, blobs, bdir


def read_blob(bdir, h):
    p = os.path.join(bdir, h)
    if not os.path.exists(p):
        return None
    b = open(p, "rb").read()
    return b if sha256(b) == h else None


def parse_json_blob(bdir, h):
    b = read_blob(bdir, h)
    if b is None:
        return None
    try:
        return json.loads(b)
    except ValueError:
        return None


# ---------- validation ----------

def valid_threshold_policy(doc):
    """Exact Warrant v0.3 §5 grammar: two top-level fields, closed threshold."""
    if not isinstance(doc, dict) or set(doc) != {"warrant_policy", "threshold"}:
        return None
    if doc["warrant_policy"] != "0.3":
        return None
    t = doc["threshold"]
    if not isinstance(t, dict) or set(t) != {"min_sigs", "actors"}:
        return None
    a, m = t["actors"], t["min_sigs"]
    if not (isinstance(a, list) and a and len(set(a)) == len(a)
            and all(isinstance(x, str) and x for x in a)):
        return None
    if not (isinstance(m, int) and not isinstance(m, bool) and 1 <= m <= len(a)):
        return None
    return t


def valid_profile(doc):
    return (isinstance(doc, dict)
            and set(doc) == {"governance_policy", "scope"}
            and doc["governance_policy"] == PROFILE_TAG
            and doc["scope"] == "spec/ANCHORS.txt")


def valid_anchor_set(doc):
    if not isinstance(doc, dict):
        return False
    keys = set(doc)
    if not ({"governance", "release", "anchors"} <= keys
            and keys <= {"governance", "release", "anchors", "ancestor"}):
        return False
    if doc["governance"] != ANCHOR_SET_TAG or not isinstance(doc["release"], str):
        return False
    if "ancestor" in doc and not (isinstance(doc["ancestor"], str)
                                  and HEX64.match(doc["ancestor"])):
        return False
    rows = doc["anchors"]
    if not (isinstance(rows, list) and rows):
        return False
    paths = []
    for r in rows:
        if not (isinstance(r, dict) and set(r) == {"path", "anchor"}
                and isinstance(r["path"], str) and r["path"]
                and isinstance(r["anchor"], str) and HEX64.match(r["anchor"])):
            return False
        paths.append(r["path"])
    return paths == sorted(paths) and len(set(paths)) == len(paths)


def store_has_key_state_warrants(recs, bdir):
    """Conservative: any accept/supersede whose subject blob parses as
    {"actor":..., "key":...} is key-state material we do not derive."""
    for env in recs.values():
        body = env.get("body", {})
        if body.get("decision") not in ("accept", "supersede"):
            continue
        doc = parse_json_blob(bdir, body.get("subject", {}).get("hash", ""))
        if isinstance(doc, dict) and set(doc) == {"actor", "key"}:
            return True
    return False


def verify_adoption(recs, blobs, bdir, blob_hash, trust_actors, prior_set_hash):
    """Return (authorized: bool, notes: [str]) for one anchor-set blob hash."""
    notes = []
    doc = parse_json_blob(bdir, blob_hash)
    if doc is None:
        return False, [f"anchor-set blob {blob_hash[:12]} missing or corrupt"]
    if not valid_anchor_set(doc):
        return False, [f"anchor-set blob {blob_hash[:12]} schema-invalid"]
    if prior_set_hash is None:
        if "ancestor" in doc:
            return False, ["genesis anchor-set must not carry an ancestor"]
    elif doc.get("ancestor") != prior_set_hash:
        return False, [f"ancestor {doc.get('ancestor', 'absent')[:12]} != "
                       f"adopted prior {prior_set_hash[:12]} (fork, not upgrade)"]
    if store_has_key_state_warrants(recs, bdir):
        return False, ["ERR: key-state warrants present — verify with the warrant CLI"]

    for rid in sorted(recs):
        env = recs[rid]
        body = env.get("body", {})
        if body.get("decision") != "accept":
            continue
        if body.get("subject", {}).get("hash") != blob_hash:
            continue
        if sha256(canon(body)) != rid:
            notes.append(f"{rid[:12]}: record id mismatch — skipped")
            continue
        threshold, profile_ok = None, False
        for u in body.get("under", []):
            u_doc = parse_json_blob(bdir, u)
            if valid_profile(u_doc):
                profile_ok = True
            t = valid_threshold_policy(u_doc)
            if t is not None:
                threshold = t
        if not profile_ok:
            notes.append(f"{rid[:12]}: no anchor-governance profile in under")
            continue
        if threshold is None:
            notes.append(f"{rid[:12]}: no valid v0.3 threshold policy in under")
            continue
        counted = set()
        for s in env.get("sigs", []):
            actor = s.get("actor")
            if actor not in threshold["actors"] or actor in counted:
                continue
            if s.get("key") not in trust_actors.get(actor, []):
                continue
            if HAVE_ED25519:
                try:
                    Ed25519PublicKey.from_public_bytes(
                        bytes.fromhex(s["key"])).verify(
                        bytes.fromhex(s["sig"]), bytes.fromhex(rid))
                except Exception:
                    continue
            counted.add(actor)
        if len(counted) >= threshold["min_sigs"]:
            notes.append(f"adopted by {rid[:12]} "
                         f"({len(counted)}/{threshold['min_sigs']} of "
                         f"{len(threshold['actors'])})")
            return True, notes
        notes.append(f"{rid[:12]}: {len(counted)} bound sigs < "
                     f"min_sigs {threshold['min_sigs']}")
    notes.append("no satisfying adoption warrant")
    return False, notes


# ---------- commands ----------

def cmd_status():
    sections = parse_anchors(ANCHORS)
    live = [(r, e) for r, hist, e in sections if not hist]
    if not live:
        print("ERR: no live release sections in ANCHORS.txt")
        return 1
    release, entries = live[0]
    recs, blobs, bdir = load_store(STORE)
    trust = json.load(open(TRUST))["actors"]
    # governance activates at the first adopted set; walk oldest-live-first
    prior = None
    verdicts = []
    for rel, ent in reversed(live):
        h = sha256(canon(anchor_set_blob(rel, ent, prior)))
        if h not in blobs:
            verdicts.append((rel, "UNGOVERNED (no anchor-set blob)"))
            continue
        ok, notes = verify_adoption(recs, blobs, bdir, h, trust, prior)
        verdicts.append((rel, ("AUTHORIZED — " if ok else "NOT AUTHORIZED — ")
                         + "; ".join(notes)))
        if ok:
            prior = h
    for rel, v in verdicts:
        print(f"{rel:10s} {v}")
    if all(v.startswith("UNGOVERNED") for _, v in verdicts):
        print("\nGOVERNANCE: not active (ADR-007 is PROPOSED; "
              "no adoption warrants may be filed before its gate closes)")
        return 0
    return 0 if verdicts[-1][1].startswith("AUTHORIZED") else 1


def cmd_make_blob():
    sections = parse_anchors(ANCHORS)
    release, _, entries = next(s for s in sections if not s[1])
    blob = anchor_set_blob(release, entries)
    sys.stdout.buffer.write(canon(blob) + b"\n")
    print(f"# sha256 {sha256(canon(blob))}", file=sys.stderr)
    return 0


# ---------- selftest ----------

def _mk_store(root):
    os.makedirs(os.path.join(root, "records"))
    os.makedirs(os.path.join(root, "blobs"))


def _put_blob(root, b):
    h = sha256(b)
    open(os.path.join(root, "blobs", h), "wb").write(b)
    return h


def _file_accept(root, subject, under, signers, note="adopt"):
    body = {"warrant": "0.2", "decision": "accept",
            "subject": {"hash": subject, "note": note},
            "under": under, "because": [{"kind": "prose", "text": note}],
            "evidence": [], "actor": {"id": signers[0][0]},
            "prior": [], "ts": 1783400000}
    rid = sha256(canon(body))
    env = {"body": body, "sigs": [
        {"actor": a, "key": pub, "sig": sk.sign(bytes.fromhex(rid)).hex()}
        for a, pub, sk in signers]}
    open(os.path.join(root, "records", rid + ".json"), "w").write(
        json.dumps(env, indent=2, sort_keys=True))
    return rid


def selftest():
    if not HAVE_ED25519:
        print("selftest needs the 'cryptography' package")
        return 2
    ok_all = True

    def check(name, got, want):
        nonlocal ok_all
        good = got == want
        ok_all &= good
        print(("OK  " if good else "FAIL") + "  " + name)

    keys = {}
    for actor in ("founder@s0fractal", "model-a@sigma-glyph", "model-b@sigma-glyph"):
        sk = Ed25519PrivateKey.generate()
        pub = sk.public_key().public_bytes_raw().hex()
        keys[actor] = (pub, sk)
    trust = {a: [pub] for a, (pub, sk) in keys.items()}
    signer = lambda a: (a, keys[a][0], keys[a][1])

    profile = canon({"governance_policy": PROFILE_TAG, "scope": "spec/ANCHORS.txt"})
    policy = canon({"warrant_policy": "0.3", "threshold":
                    {"min_sigs": 2, "actors": list(keys)}})
    set1 = canon(anchor_set_blob("v0.6.1", [("spec/book-1-truth.md", "a" * 64)]))
    set2 = canon(anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "b" * 64)],
                                 ancestor=sha256(set1)))

    with tempfile.TemporaryDirectory() as td:
        _mk_store(td)
        hp, ht = _put_blob(td, profile), _put_blob(td, policy)
        h1, h2 = _put_blob(td, set1), _put_blob(td, set2)
        _file_accept(td, h1, [ht, hp],
                     [signer("founder@s0fractal"), signer("model-a@sigma-glyph")])
        recs, blobs, bdir = load_store(td)

        ok, _ = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("2-of-3 adoption authorized", ok, True)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust, h1)
        check("unadopted successor not authorized", ok, False)
        ok, notes = verify_adoption(recs, blobs, bdir, h2, trust, "c" * 64)
        check("ancestor mismatch is a fork", ok, False)
        check("fork named in notes", any("fork" in n for n in notes), True)

    with tempfile.TemporaryDirectory() as td:  # under-threshold + bad sigs
        _mk_store(td)
        hp, ht = _put_blob(td, profile), _put_blob(td, policy)
        h1 = _put_blob(td, set1)
        _file_accept(td, h1, [ht, hp], [signer("founder@s0fractal")])
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("1 sig < min_sigs 2 rejected", ok, False)

        stranger = Ed25519PrivateKey.generate()
        _file_accept(td, h1, [ht, hp],
                     [signer("founder@s0fractal"),
                      ("model-a@sigma-glyph", stranger.public_key()
                       .public_bytes_raw().hex(), stranger)])
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("unbound key does not count", ok, False)

        _file_accept(td, h1, [ht, hp],
                     [signer("founder@s0fractal"), signer("founder@s0fractal")])
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("duplicate actor counts once", ok, False)

    with tempfile.TemporaryDirectory() as td:  # policy grammar + profile binding
        _mk_store(td)
        bad_policy = canon({"warrant_policy": "0.3", "threshold":
                            {"min_sigs": 1, "actors": list(keys), "note": "x"}})
        hp, hb = _put_blob(td, profile), _put_blob(td, bad_policy)
        h1 = _put_blob(td, set1)
        _file_accept(td, h1, [hb, hp], [signer("founder@s0fractal")])
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("unknown field in threshold invalidates policy", ok, False)

        ht = _put_blob(td, policy)
        _file_accept(td, h1, [ht],  # no profile blob
                     [signer("founder@s0fractal"), signer("model-a@sigma-glyph")])
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("threshold without governance profile rejected", ok, False)

        check("genesis set with ancestor field rejected",
              valid_anchor_set(json.loads(set2)) and
              verify_adoption(recs, blobs, bdir, h1, trust, None)[0], False)

    with tempfile.TemporaryDirectory() as td:  # key-state refusal
        _mk_store(td)
        hp, ht = _put_blob(td, profile), _put_blob(td, policy)
        h1 = _put_blob(td, set1)
        rot = _put_blob(td, canon({"actor": "model-a@sigma-glyph", "key": "d" * 64}))
        _file_accept(td, rot, [ht], [signer("founder@s0fractal"),
                                     signer("model-b@sigma-glyph")], note="rotate")
        _file_accept(td, h1, [ht, hp],
                     [signer("founder@s0fractal"), signer("model-a@sigma-glyph")])
        recs, blobs, bdir = load_store(td)
        ok, notes = verify_adoption(recs, blobs, bdir, h1, trust, None)
        check("refuses stores with key-state warrants",
              (ok, any("warrant CLI" in n for n in notes)), (False, True))

    # projection: live repo ANCHORS.txt parses and round-trips
    sections = parse_anchors(ANCHORS)
    live = [s for s in sections if not s[1]]
    check("ANCHORS.txt parses (live sections)", len(live) >= 3, True)
    check("current section is v0.6.1 with 8 anchors",
          (live[0][0], len(live[0][2])), ("v0.6.1", 8))
    blob = anchor_set_blob(live[0][0], live[0][2])
    check("current anchor-set blob schema-valid", valid_anchor_set(blob), True)

    print("\nANCHOR-GOVERNANCE: " + ("ALL PASS" if ok_all else "FAILURES"))
    return 0 if ok_all else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        sys.exit(cmd_status())
    if cmd == "make-blob":
        sys.exit(cmd_make_blob())
    if cmd == "selftest":
        sys.exit(selftest())
    sys.exit(f"unknown command {cmd!r} (status | make-blob | selftest)")


if __name__ == "__main__":
    main()
