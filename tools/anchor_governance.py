#!/usr/bin/env python3
"""Read-only verifier for ADR-007 governed anchors (PROPOSED, rev 2 — see proposals/ADR-007-governed-anchors.md).

Answers "is this ANCHORS.txt release authorized?" as a pure function of
(.warrants store, out-of-band trust config), with an exit code. Until ADR-007
passes its gate and a first adoption warrant is filed, `status` honestly
reports UNGOVERNED — this tool existing first is the Decision Process's
implementation precondition, not an activation.

Rev 2 (adjudicating the 2026-07 three-family gate round — GPT-5, Gemini 3.1
Pro, DeepSeek v4 Pro):
  - trust config is OUT-OF-BAND and versioned; never read from the verified
    tree (Gemini ask-1; DeepSeek 6.4);
  - adoption warrants count only inside the settlement closure of the pinned
    jurisdiction root (GPT-5 P1-A);
  - anchor-set blobs embed the jurisdiction root (GPT-5 §2, DeepSeek §2 — 2:1
    over Gemini);
  - governance profile hash-pins its threshold policy; `under` MUST be exactly
    one profile + one threshold; policy lineage walks profile adoptions each
    authorized under the policy being replaced (3/3 blind convergence);
  - competing successor adoptions freeze the chain as a conflict — never
    auto-picked (DeepSeek 6.1 finding accepted, smallest-WarrantID tie-break
    rejected as grindable; Book III client rule applied);
  - missing 'cryptography' is a hard error, not a silent pass (Gemini A);
  - `status --enforce` fails on UNGOVERNED (Gemini B);
  - key-state refusal scoped to warrants under governance policy blobs
    (DeepSeek 6.5); full key-state derivation stays the warrant CLI's job.

Commands:
  status    [--trust-config F] [--enforce]   governance state of ANCHORS.txt
  make-blob --jurisdiction HEX64 [--ancestor HEX64]   canonical anchor-set blob
  selftest                                   deterministic fixtures (fixed seeds)
"""
import argparse, hashlib, json, os, re, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHORS = os.path.join(REPO, "spec", "ANCHORS.txt")
STORE = os.path.join(REPO, ".warrants")

PROFILE_TAG = "sigma-glyph.anchor-governance@v1"
ANCHOR_SET_TAG = "sigma-glyph.anchor-set@v1"
TRUST_TAG = "sigma-glyph.anchor-trust@v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey)
    HAVE_ED25519 = True
except ImportError:
    HAVE_ED25519 = False


def canon(obj):
    # RFC 8785 (JCS) for this schema family: sorted keys, no whitespace,
    # UTF-8, integers only (I-JSON) — identical to the Warrant convention.
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


def anchor_set_blob(release, entries, jurisdiction, ancestor=None):
    blob = {"governance": ANCHOR_SET_TAG, "jurisdiction": jurisdiction,
            "release": release,
            "anchors": [{"path": p, "anchor": a} for p, a in sorted(entries)]}
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


# ---------- schema validation ----------

def valid_trust(doc):
    if not isinstance(doc, dict):
        return None
    need = {"governance_trust", "jurisdiction", "genesis_profile", "actors"}
    if set(doc) != need or doc["governance_trust"] != TRUST_TAG:
        return None
    if not (isinstance(doc["jurisdiction"], str) and HEX64.match(doc["jurisdiction"])):
        return None
    if not (isinstance(doc["genesis_profile"], str) and HEX64.match(doc["genesis_profile"])):
        return None
    a = doc["actors"]
    if not (isinstance(a, dict) and a and all(
            isinstance(k, str) and k and isinstance(v, list) and v
            and all(isinstance(x, str) and HEX64.match(x) for x in v)
            for k, v in a.items())):
        return None
    return doc


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
            and set(doc) == {"governance_policy", "scope", "threshold"}
            and doc["governance_policy"] == PROFILE_TAG
            and doc["scope"] == "spec/ANCHORS.txt"
            and isinstance(doc["threshold"], str)
            and HEX64.match(doc["threshold"])) or False


def valid_anchor_set(doc):
    if not isinstance(doc, dict):
        return False
    keys = set(doc)
    base = {"governance", "jurisdiction", "release", "anchors"}
    if not (base <= keys and keys <= base | {"ancestor"}):
        return False
    if doc["governance"] != ANCHOR_SET_TAG or not isinstance(doc["release"], str):
        return False
    if not (isinstance(doc["jurisdiction"], str) and HEX64.match(doc["jurisdiction"])):
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


# ---------- settlement scoping ----------

def settlement_closure(recs, root):
    """Root + descendants via prior edges (Warrant §9 scoping)."""
    if root not in recs:
        return set()
    closure = {root}
    changed = True
    while changed:
        changed = False
        for rid, env in recs.items():
            if rid in closure:
                continue
            if any(p in closure for p in env.get("body", {}).get("prior", [])):
                closure.add(rid)
                changed = True
    return closure


def counted_sigs(env, rid, threshold, trust_actors):
    counted = set()
    for s in env.get("sigs", []):
        actor = s.get("actor")
        if actor not in threshold["actors"] or actor in counted:
            continue
        if s.get("key") not in trust_actors.get(actor, []):
            continue
        try:
            Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(s["key"])).verify(
                bytes.fromhex(s["sig"]), bytes.fromhex(rid))
        except Exception:
            continue
        counted.add(actor)
    return counted


def _accepts_of(recs, closure, bdir):
    """Yield (rid, body, subject_doc) for id-sound accepts inside the closure."""
    for rid in sorted(closure):
        env = recs[rid]
        body = env.get("body", {})
        if body.get("decision") != "accept":
            continue
        if sha256(canon(body)) != rid:
            continue
        doc = parse_json_blob(bdir, body.get("subject", {}).get("hash", ""))
        yield rid, body, doc


def _under_is(body, profile_hash, threshold_hash):
    """Exactly one profile + one threshold, and exactly the bound pair."""
    u = body.get("under", [])
    return len(u) == 2 and set(u) == {profile_hash, threshold_hash}


def derive_current_profile(recs, closure, bdir, trust):
    """Walk profile adoptions from the genesis profile; each hop must be
    authorized under the policy being replaced (Warrant §5.1 current-policy
    rule applied to governance). Returns (profile_hash, gov, error|None)
    where gov is the AUTHORIZED lineage: [(profile_hash, threshold_dict,
    threshold_hash), ...] for every policy that ever governed. Only this set
    may scope anything downstream — a profile-shaped blob whose adoption
    never carried a quorum is not governance, it is litter (Kimi
    verification pass, P1-R: the collector must not trust unsigned shapes)."""
    cur = trust["genesis_profile"]
    seen = {cur}
    gov = []
    while True:
        p_doc = parse_json_blob(bdir, cur)
        if not valid_profile(p_doc):
            return cur, gov, f"current profile {cur[:12]} missing or schema-invalid"
        t_hash = p_doc["threshold"]
        t = valid_threshold_policy(parse_json_blob(bdir, t_hash))
        if t is None:
            return cur, gov, f"threshold {t_hash[:12]} pinned by profile is invalid"
        gov.append((cur, t, t_hash))
        nxt = set()
        for rid, body, doc in _accepts_of(recs, closure, bdir):
            if not valid_profile(doc):
                continue
            if not _under_is(body, cur, t_hash):
                continue
            if len(counted_sigs(recs[rid], rid, t, trust["actors"])) < t["min_sigs"]:
                continue
            nxt.add(body["subject"]["hash"])
        nxt -= seen
        if not nxt:
            return cur, gov, None
        if len(nxt) > 1:
            return cur, gov, ("profile-succession conflict: "
                              + ", ".join(h[:12] for h in sorted(nxt))
                              + " — chain frozen, resolve by settlement")
        cur = nxt.pop()
        seen.add(cur)


def key_state_under_governance(recs, closure, bdir, gov, trust):
    """Quorum-authorized key-state warrants filed under an AUTHORIZED
    governance policy force refusal to a key-state-deriving verifier.
    Two scopings, both required (Kimi P1-R):
      - the policy hash must come from the authorized lineage, not from any
        profile-shaped blob in the store;
      - the key-state warrant itself must satisfy the quorum of the lineage
        policy it cites — per Warrant §5.1 a key-state record that fails
        current-policy authorization is an invalid record, not a conflict,
        and an attacker without a quorum cannot manufacture one."""
    by_hash = {h: (p, t) for p, t, h in
               [(p, t, th) for p, t, th in gov]}
    gov_hashes = set(by_hash) | {p for p, _, _ in gov}
    threshold_of = {}
    for p, t, th in gov:
        threshold_of[p] = t
        threshold_of[th] = t
    for rid in sorted(closure):
        env = recs[rid]
        body = env.get("body", {})
        if body.get("decision") not in ("accept", "supersede"):
            continue
        cited = set(body.get("under", [])) & gov_hashes
        if not cited:
            continue
        doc = parse_json_blob(bdir, body.get("subject", {}).get("hash", ""))
        if not (isinstance(doc, dict) and set(doc) == {"actor", "key"}):
            continue
        if sha256(canon(body)) != rid:
            continue
        for h in cited:
            t = threshold_of[h]
            if len(counted_sigs(env, rid, t, trust["actors"])) >= t["min_sigs"]:
                return True
    return False


def verify_adoption(recs, blobs, bdir, blob_hash, trust, prior_set_hash):
    """(authorized: bool, notes: [str]) for one anchor-set blob hash, under
    the out-of-band trust config. Pure function of (store, trust)."""
    if not HAVE_ED25519:
        return False, ["ERR: python 'cryptography' missing — signatures "
                       "cannot be verified, refusing to authorize"]
    notes = []
    doc = parse_json_blob(bdir, blob_hash)
    if doc is None:
        return False, [f"anchor-set blob {blob_hash[:12]} missing or corrupt"]
    if not valid_anchor_set(doc):
        return False, [f"anchor-set blob {blob_hash[:12]} schema-invalid"]
    if doc["jurisdiction"] != trust["jurisdiction"]:
        return False, [f"jurisdiction {doc['jurisdiction'][:12]} != pinned root "
                       f"{trust['jurisdiction'][:12]} (foreign blob, replay refused)"]
    if prior_set_hash is None:
        if "ancestor" in doc:
            return False, ["genesis anchor-set must not carry an ancestor"]
    elif doc.get("ancestor") != prior_set_hash:
        return False, [f"ancestor {doc.get('ancestor', 'absent')[:12]} != "
                       f"adopted prior {prior_set_hash[:12]} (fork, not upgrade)"]

    closure = settlement_closure(recs, trust["jurisdiction"])
    if not closure:
        return False, [f"jurisdiction root {trust['jurisdiction'][:12]} not in store"]
    cur_profile, gov, err = derive_current_profile(recs, closure, bdir, trust)
    if err:
        return False, ["ERR: " + err]
    if key_state_under_governance(recs, closure, bdir, gov, trust):
        return False, ["ERR: key-state warrants under governance policy — "
                       "derive key state with the warrant CLI first"]
    p_doc = parse_json_blob(bdir, cur_profile)
    t_hash = p_doc["threshold"]
    t = valid_threshold_policy(parse_json_blob(bdir, t_hash))

    # competing successor rule: another AUTHORIZED adoption of a DIFFERENT
    # valid anchor-set with the same ancestor freezes the chain (no tie-break
    # — a deterministic winner rule would be grindable; ties surface).
    rivals = set()
    for rid, body, rdoc in _accepts_of(recs, closure, bdir):
        if not (isinstance(rdoc, dict) and valid_anchor_set(rdoc)):
            continue
        h = body["subject"]["hash"]
        if h == blob_hash or rdoc["jurisdiction"] != trust["jurisdiction"]:
            continue
        if rdoc.get("ancestor") != (prior_set_hash if prior_set_hash else None):
            if not (prior_set_hash is None and "ancestor" not in rdoc):
                continue
        if not _under_is(body, cur_profile, t_hash):
            continue
        if len(counted_sigs(recs[rid], rid, t, trust["actors"])) >= t["min_sigs"]:
            rivals.add(h)
    if rivals:
        return False, ["adoption conflict: rival authorized successor(s) "
                       + ", ".join(h[:12] for h in sorted(rivals))
                       + " share this ancestor — chain frozen"]

    for rid, body, rdoc in _accepts_of(recs, closure, bdir):
        if body["subject"]["hash"] != blob_hash:
            continue
        if not _under_is(body, cur_profile, t_hash):
            notes.append(f"{rid[:12]}: under != current (profile, threshold) pair")
            continue
        counted = counted_sigs(recs[rid], rid, t, trust["actors"])
        if len(counted) >= t["min_sigs"]:
            notes.append(f"adopted by {rid[:12]} ({len(counted)}/{t['min_sigs']}"
                         f" of {len(t['actors'])})")
            return True, notes
        notes.append(f"{rid[:12]}: {len(counted)} bound sigs < "
                     f"min_sigs {t['min_sigs']}")
    notes.append("no satisfying adoption warrant in settlement closure")
    return False, notes


# ---------- commands ----------

def cmd_status(trust_path, enforce):
    sections = parse_anchors(ANCHORS)
    live = [(r, e) for r, hist, e in sections if not hist]
    if not live:
        print("ERR: no live release sections in ANCHORS.txt")
        return 1
    trust = None
    if trust_path:
        if os.path.realpath(trust_path).startswith(os.path.realpath(REPO) + os.sep):
            print("ERR: trust config must be out-of-band — refusing a path "
                  "inside the verified tree")
            return 1
        trust = valid_trust(json.load(open(trust_path)))
        if trust is None:
            print("ERR: trust config invalid (want sigma-glyph.anchor-trust@v1)")
            return 1
    if trust is None:
        for rel, _ in reversed(live):
            print(f"{rel:10s} UNGOVERNED (no out-of-band trust config)")
        print("\nGOVERNANCE: not active (ADR-007 is PROPOSED; no adoption "
              "warrants may be filed before its gate closes)")
        return 1 if enforce else 0
    recs, blobs, bdir = load_store(STORE)
    prior, all_ok = None, True
    for rel, ent in reversed(live):
        h = sha256(canon(anchor_set_blob(rel, ent, trust["jurisdiction"], prior)))
        if h not in blobs:
            print(f"{rel:10s} NOT AUTHORIZED — no anchor-set blob in store")
            all_ok = False
            continue
        ok, notes = verify_adoption(recs, blobs, bdir, h, trust, prior)
        print(f"{rel:10s} " + ("AUTHORIZED — " if ok else "NOT AUTHORIZED — ")
              + "; ".join(notes))
        if ok:
            prior = h
        else:
            all_ok = False
    return 0 if all_ok else 1


def cmd_make_blob(jurisdiction, ancestor):
    sections = parse_anchors(ANCHORS)
    release, _, entries = next(s for s in sections if not s[1])
    blob = anchor_set_blob(release, entries, jurisdiction, ancestor)
    sys.stdout.buffer.write(canon(blob) + b"\n")
    print(f"# sha256 {sha256(canon(blob))}", file=sys.stderr)
    return 0


# ---------- selftest (deterministic: fixed seeds, fixed ts) ----------

def _sk(actor):
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"adr007-fixture:" + actor.encode()).digest())


def _pub(actor):
    return _sk(actor).public_key().public_bytes_raw().hex()


def _mk_store(root):
    os.makedirs(os.path.join(root, "records"))
    os.makedirs(os.path.join(root, "blobs"))


def _put_blob(root, b):
    h = sha256(b)
    open(os.path.join(root, "blobs", h), "wb").write(b)
    return h


def _file(root, decision, actor, subject, under, prior, signers, note="x"):
    body = {"warrant": "0.2", "decision": decision,
            "subject": {"hash": subject, "note": note},
            "under": under, "because": [{"kind": "prose", "text": note}],
            "evidence": [], "actor": {"id": actor},
            "prior": prior, "ts": 1783400000}
    rid = sha256(canon(body))
    env = {"body": body, "sigs": [
        {"actor": a, "key": _pub(a), "sig": _sk(a).sign(bytes.fromhex(rid)).hex()}
        for a in signers]}
    open(os.path.join(root, "records", rid + ".json"), "w").write(
        json.dumps(env, indent=2, sort_keys=True))
    return rid


ACTORS = ["founder@s0fractal", "model-a@sigma-glyph", "model-b@sigma-glyph"]


def _fixture(td):
    """Genesis root + P1(pins T1) + genesis anchor-set adopted 2-of-3.
    Returns (trust, hashes dict)."""
    _mk_store(td)
    t1 = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                              {"min_sigs": 2, "actors": ACTORS}}))
    manifesto = _put_blob(td, b"governance jurisdiction manifesto")
    root = _file(td, "propose", ACTORS[0], manifesto, [t1], [],
                 [ACTORS[0]], note="governance genesis")
    p1 = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                              "scope": "spec/ANCHORS.txt", "threshold": t1}))
    trust = {"governance_trust": TRUST_TAG, "jurisdiction": root,
             "genesis_profile": p1, "actors": {a: [_pub(a)] for a in ACTORS}}
    set1 = canon(anchor_set_blob("v0.6.1", [("spec/book-1-truth.md", "a" * 64)], root))
    h1 = _put_blob(td, set1)
    wid1 = _file(td, "accept", ACTORS[0], h1, [p1, t1], [root],
                 [ACTORS[0], ACTORS[2]], note="adopt v0.6.1")
    return trust, {"t1": t1, "p1": p1, "root": root, "h1": h1, "wid1": wid1}


def selftest():
    if not HAVE_ED25519:
        print("selftest needs the 'cryptography' package")
        return 2
    ok_all = True

    def check(name, got, want=True):
        nonlocal ok_all
        good = got == want
        ok_all &= good
        print(("OK  " if good else "FAIL") + "  " + name)

    with tempfile.TemporaryDirectory() as td:
        trust, hx = _fixture(td)
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, hx["h1"], trust, None)
        check("genesis adoption 2-of-3 authorized", ok)

        # successor adopted under rotated policy
        t2 = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                                  {"min_sigs": 2, "actors": ACTORS[:2] +
                                   ["model-c@sigma-glyph"]}}))
        p2 = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                                  "scope": "spec/ANCHORS.txt", "threshold": t2}))
        _file(td, "accept", ACTORS[0], p2, [hx["p1"], hx["t1"]], [hx["wid1"]],
              [ACTORS[0], ACTORS[1]], note="rotate policy to include model-c")
        set2 = canon(anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "b" * 64)],
                                     hx["root"], ancestor=hx["h1"]))
        h2 = _put_blob(td, set2)
        trust2 = dict(trust, actors={**trust["actors"],
                                     "model-c@sigma-glyph": [_pub("model-c@sigma-glyph")]})
        _file(td, "accept", ACTORS[0], h2, [p2, t2], [hx["wid1"]],
              [ACTORS[0], "model-c@sigma-glyph"], note="adopt v0.7.0")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust2, hx["h1"])
        check("succession: v0.7.0 under rotated policy authorized", ok)
        ok, notes = verify_adoption(recs, blobs, bdir, h2, trust2, "c" * 64)
        check("ancestor mismatch is a fork", ok, False)
        check("fork named in notes", any("fork" in n for n in notes))

    with tempfile.TemporaryDirectory() as td:  # threshold hijack (3/3 finding)
        trust, hx = _fixture(td)
        t_evil = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                                      {"min_sigs": 1,
                                       "actors": ["model-a@sigma-glyph"]}}))
        p_evil = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                                      "scope": "spec/ANCHORS.txt",
                                      "threshold": t_evil}))
        set2 = canon(anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "e" * 64)],
                                     hx["root"], ancestor=hx["h1"]))
        h2 = _put_blob(td, set2)
        _file(td, "accept", ACTORS[1], h2, [p_evil, t_evil], [hx["wid1"]],
              [ACTORS[1]], note="unilateral hijack attempt")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust, hx["h1"])
        check("minted 1-of-1 policy pair rejected (lineage rule)", ok, False)

        # under cardinality: profile + BOTH thresholds
        _file(td, "accept", ACTORS[1], h2, [hx["p1"], hx["t1"], t_evil],
              [hx["wid1"]], [ACTORS[0], ACTORS[1]], note="fat under")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust, hx["h1"])
        check("under with extra blob ineligible (cardinality)", ok, False)

    with tempfile.TemporaryDirectory() as td:  # signature discipline
        trust, hx = _fixture(td)
        set2 = canon(anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "b" * 64)],
                                     hx["root"], ancestor=hx["h1"]))
        h2 = _put_blob(td, set2)
        _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
              [ACTORS[0]], note="one sig")
        _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
              [ACTORS[0], ACTORS[0]], note="dup actor")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust, hx["h1"])
        check("1 sig < min_sigs 2 and duplicate actor rejected", ok, False)

        stranger_key = sha256(b"stranger").ljust(64, "0")
        trust_bad = dict(trust, actors={**trust["actors"],
                                        ACTORS[1]: [stranger_key]})
        _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
              [ACTORS[0], ACTORS[1]], note="two sigs")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust_bad, hx["h1"])
        check("unbound key does not count", ok, False)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust, hx["h1"])
        check("same record with bound keys authorizes", ok)

    with tempfile.TemporaryDirectory() as td:  # jurisdiction + closure scoping
        trust, hx = _fixture(td)
        foreign = anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "b" * 64)],
                                  "f" * 64, ancestor=hx["h1"])
        hf = _put_blob(td, canon(foreign))
        _file(td, "accept", ACTORS[0], hf, [hx["p1"], hx["t1"]], [hx["wid1"]],
              [ACTORS[0], ACTORS[2]], note="foreign jurisdiction blob")
        recs, blobs, bdir = load_store(td)
        ok, notes = verify_adoption(recs, blobs, bdir, hf, trust, hx["h1"])
        check("foreign jurisdiction blob refused",
              (ok, any("replay refused" in n for n in notes)), (False, True))

        set2 = canon(anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "b" * 64)],
                                     hx["root"], ancestor=hx["h1"]))
        h2 = _put_blob(td, set2)
        _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [],  # prior=[]
              [ACTORS[0], ACTORS[2]], note="orphan adoption outside closure")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, h2, trust, hx["h1"])
        check("adoption outside settlement closure ignored", ok, False)

    with tempfile.TemporaryDirectory() as td:  # competing successors freeze
        trust, hx = _fixture(td)
        for byte, note in (("b", "successor A"), ("d", "successor B")):
            s = canon(anchor_set_blob("v0.7.0",
                                      [("spec/book-1-truth.md", byte * 64)],
                                      hx["root"], ancestor=hx["h1"]))
            h = _put_blob(td, s)
            _file(td, "accept", ACTORS[0], h, [hx["p1"], hx["t1"]], [hx["wid1"]],
                  [ACTORS[0], ACTORS[2]], note=note)
        recs, blobs, bdir = load_store(td)
        ok, notes = verify_adoption(recs, blobs, bdir, h, trust, hx["h1"])
        check("competing authorized successors freeze the chain",
              (ok, any("conflict" in n for n in notes)), (False, True))

    with tempfile.TemporaryDirectory() as td:  # scoped key-state refusal
        trust, hx = _fixture(td)
        rot = _put_blob(td, canon({"actor": ACTORS[1], "key": "d" * 64}))
        other_policy = _put_blob(td, b"an unrelated policy blob")
        _file(td, "accept", ACTORS[0], rot, [other_policy], [hx["root"]],
              [ACTORS[0], ACTORS[2]], note="key-state under UNRELATED policy")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, hx["h1"], trust, None)
        check("key-state under unrelated policy is ignored (scoped)", ok)

        # Kimi P1-R, part 1: an UNAUTHORIZED profile-shaped accept (no quorum)
        # must not expand the governance set — key-state filed under it is litter
        t_fake = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                                      {"min_sigs": 1, "actors": [ACTORS[1]]}}))
        p_fake = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                                      "scope": "spec/ANCHORS.txt",
                                      "threshold": t_fake}))
        _file(td, "accept", ACTORS[1], p_fake, [p_fake, t_fake], [hx["root"]],
              [ACTORS[1]], note="unauthorized profile-shaped adoption")
        _file(td, "accept", ACTORS[1], rot, [p_fake], [hx["root"]],
              [ACTORS[1]], note="key-state under the unauthorized profile")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, hx["h1"], trust, None)
        check("unauthorized profile cannot expand key-state scope (P1-R)", ok)

        # Kimi P1-R, part 2: a key-state warrant citing the REAL governance
        # policy but lacking its quorum is an invalid record (Warrant s5.1),
        # not a refusal trigger
        _file(td, "accept", ACTORS[1], rot, [hx["t1"]], [hx["root"]],
              [ACTORS[1]], note="key-state under governance, NO quorum")
        recs, blobs, bdir = load_store(td)
        ok, _ = verify_adoption(recs, blobs, bdir, hx["h1"], trust, None)
        check("unquorumed key-state under governance ignored (s5.1)", ok)

        _file(td, "accept", ACTORS[0], rot, [hx["t1"]], [hx["root"]],
              [ACTORS[0], ACTORS[2]], note="key-state under GOVERNANCE policy")
        recs, blobs, bdir = load_store(td)
        ok, notes = verify_adoption(recs, blobs, bdir, hx["h1"], trust, None)
        check("quorum-authorized key-state under governance refused to warrant CLI",
              (ok, any("warrant CLI" in n for n in notes)), (False, True))

    with tempfile.TemporaryDirectory() as td:  # schema edges
        trust, hx = _fixture(td)
        bad = anchor_set_blob("v0.6.1", [("spec/book-1-truth.md", "a" * 64)],
                              hx["root"], ancestor="a" * 64)
        recs, blobs, bdir = load_store(td)
        hb = _put_blob(td, canon(bad))
        ok, _ = verify_adoption(recs, blobs, bdir, hb, trust, None)
        check("genesis set carrying ancestor rejected", ok, False)
        check("profile without threshold pin is schema-invalid",
              valid_profile({"governance_policy": PROFILE_TAG,
                             "scope": "spec/ANCHORS.txt"}), False)
        check("trust config schema closed",
              valid_trust(dict(trust, extra=1)) is None)

    # projection: live repo ANCHORS.txt parses and round-trips.
    # exactly one live line of descent post-governance (v0.5.0-v0.6.1 are
    # pre-governance ancestors)
    sections = parse_anchors(ANCHORS)
    live = [s for s in sections if not s[1]]
    check("ANCHORS.txt parses (one live line of descent)", len(live), 1)
    check("current section is v0.6.2 with 9 anchors",
          (live[0][0], len(live[0][2])), ("v0.6.2", 9))
    check("current anchor-set blob schema-valid",
          valid_anchor_set(anchor_set_blob(live[0][0], live[0][2], "a" * 64)))

    print("\nANCHOR-GOVERNANCE: " + ("ALL PASS" if ok_all else "FAILURES"))
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser(prog="anchor_governance.py")
    sub = ap.add_subparsers(dest="cmd")
    st = sub.add_parser("status")
    st.add_argument("--trust-config", help="OUT-OF-BAND trust file "
                    "(sigma-glyph.anchor-trust@v1); never from the verified tree")
    st.add_argument("--enforce", action="store_true",
                    help="exit 1 when governance is not active")
    mb = sub.add_parser("make-blob")
    mb.add_argument("--jurisdiction", required=True,
                    help="hex64 WarrantID of the governance genesis root")
    mb.add_argument("--ancestor", help="hex64 sha256 of the prior adopted set")
    sub.add_parser("selftest")
    args = ap.parse_args()
    if args.cmd == "make-blob":
        sys.exit(cmd_make_blob(args.jurisdiction, args.ancestor))
    if args.cmd == "selftest":
        sys.exit(selftest())
    if args.cmd in (None, "status"):
        tc = getattr(args, "trust_config", None)
        enforce = getattr(args, "enforce", False)
        sys.exit(cmd_status(tc, enforce))


if __name__ == "__main__":
    main()
