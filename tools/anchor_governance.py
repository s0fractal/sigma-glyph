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


MODEL_C = "model-c@sigma-glyph"


def _successor_blob(td, hx, byte="b"):
    s = canon(anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", byte * 64)],
                              hx["root"], ancestor=hx["h1"]))
    return _put_blob(td, s)


# ---------- scenarios: the pinned claim surface ----------
# Each builder populates a fresh store and returns
# (trust, candidate_blob_hash, prior_set_hash_or_None, expect_authorized,
#  note_substring_that_MUST_appear).

def _scn_genesis_adopted(td):
    trust, hx = _fixture(td)
    return trust, hx["h1"], None, True, "adopted by"


def _scn_succession_rotated(td):
    trust, hx = _fixture(td)
    t2 = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                              {"min_sigs": 2, "actors": ACTORS[:2] + [MODEL_C]}}))
    p2 = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                              "scope": "spec/ANCHORS.txt", "threshold": t2}))
    _file(td, "accept", ACTORS[0], p2, [hx["p1"], hx["t1"]], [hx["wid1"]],
          [ACTORS[0], ACTORS[1]], note="rotate policy to include model-c")
    h2 = _successor_blob(td, hx)
    trust2 = dict(trust, actors={**trust["actors"], MODEL_C: [_pub(MODEL_C)]})
    _file(td, "accept", ACTORS[0], h2, [p2, t2], [hx["wid1"]],
          [ACTORS[0], MODEL_C], note="adopt v0.7.0")
    return trust2, h2, hx["h1"], True, "adopted by"


def _scn_ancestor_fork(td):
    trust2, h2, _, _, _ = _scn_succession_rotated(td)
    return trust2, h2, "c" * 64, False, "fork, not upgrade"


def _scn_genesis_with_ancestor(td):
    trust, hx = _fixture(td)
    bad = anchor_set_blob("v0.6.1", [("spec/book-1-truth.md", "a" * 64)],
                          hx["root"], ancestor="a" * 64)
    hb = _put_blob(td, canon(bad))
    return trust, hb, None, False, "must not carry an ancestor"


def _scn_hijack_minted_pair(td):
    trust, hx = _fixture(td)
    t_evil = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                                  {"min_sigs": 1, "actors": [ACTORS[1]]}}))
    p_evil = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                                  "scope": "spec/ANCHORS.txt",
                                  "threshold": t_evil}))
    h2 = _successor_blob(td, hx, byte="e")
    _file(td, "accept", ACTORS[1], h2, [p_evil, t_evil], [hx["wid1"]],
          [ACTORS[1]], note="unilateral hijack attempt")
    return trust, h2, hx["h1"], False, "no satisfying adoption warrant"


def _scn_under_cardinality(td):
    trust, hx = _fixture(td)
    t_extra = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                                   {"min_sigs": 1, "actors": [ACTORS[1]]}}))
    h2 = _successor_blob(td, hx)
    _file(td, "accept", ACTORS[1], h2, [hx["p1"], hx["t1"], t_extra],
          [hx["wid1"]], [ACTORS[0], ACTORS[1]], note="fat under")
    return trust, h2, hx["h1"], False, "under != current (profile, threshold) pair"


def _scn_sigs_below_threshold(td):
    trust, hx = _fixture(td)
    h2 = _successor_blob(td, hx)
    _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
          [ACTORS[0]], note="one sig")
    _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
          [ACTORS[0], ACTORS[0]], note="dup actor")
    return trust, h2, hx["h1"], False, "bound sigs < min_sigs"


def _scn_unbound_key(td):
    trust, hx = _fixture(td)
    h2 = _successor_blob(td, hx)
    _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
          [ACTORS[0], ACTORS[1]], note="two sigs")
    stranger = hashlib.sha256(b"adr007-fixture:stranger").hexdigest()
    trust_bad = dict(trust, actors={**trust["actors"], ACTORS[1]: [stranger]})
    return trust_bad, h2, hx["h1"], False, "bound sigs < min_sigs"


def _scn_bound_keys_authorize(td):
    trust, hx = _fixture(td)
    h2 = _successor_blob(td, hx)
    _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [hx["wid1"]],
          [ACTORS[0], ACTORS[1]], note="two sigs")
    return trust, h2, hx["h1"], True, "adopted by"


def _scn_foreign_jurisdiction(td):
    trust, hx = _fixture(td)
    foreign = anchor_set_blob("v0.7.0", [("spec/book-1-truth.md", "b" * 64)],
                              "f" * 64, ancestor=hx["h1"])
    hf = _put_blob(td, canon(foreign))
    _file(td, "accept", ACTORS[0], hf, [hx["p1"], hx["t1"]], [hx["wid1"]],
          [ACTORS[0], ACTORS[2]], note="foreign jurisdiction blob")
    return trust, hf, hx["h1"], False, "replay refused"


def _scn_orphan_outside_closure(td):
    trust, hx = _fixture(td)
    h2 = _successor_blob(td, hx)
    _file(td, "accept", ACTORS[0], h2, [hx["p1"], hx["t1"]], [],
          [ACTORS[0], ACTORS[2]], note="orphan adoption outside closure")
    return trust, h2, hx["h1"], False, "no satisfying adoption warrant"


def _scn_competing_successors(td):
    trust, hx = _fixture(td)
    for byte, note in (("b", "successor A"), ("d", "successor B")):
        h = _successor_blob(td, hx, byte=byte)
        _file(td, "accept", ACTORS[0], h, [hx["p1"], hx["t1"]], [hx["wid1"]],
              [ACTORS[0], ACTORS[2]], note=note)
    return trust, h, hx["h1"], False, "chain frozen"


def _scn_keystate_unrelated_ignored(td):
    trust, hx = _fixture(td)
    rot = _put_blob(td, canon({"actor": ACTORS[1], "key": "d" * 64}))
    other = _put_blob(td, b"an unrelated policy blob")
    _file(td, "accept", ACTORS[0], rot, [other], [hx["root"]],
          [ACTORS[0], ACTORS[2]], note="key-state under UNRELATED policy")
    return trust, hx["h1"], None, True, "adopted by"


def _scn_keystate_unauth_profile(td):
    # Kimi P1-R part 1: an unauthorized profile-shaped accept must not
    # expand the governance set
    trust, hx = _fixture(td)
    rot = _put_blob(td, canon({"actor": ACTORS[1], "key": "d" * 64}))
    t_fake = _put_blob(td, canon({"warrant_policy": "0.3", "threshold":
                                  {"min_sigs": 1, "actors": [ACTORS[1]]}}))
    p_fake = _put_blob(td, canon({"governance_policy": PROFILE_TAG,
                                  "scope": "spec/ANCHORS.txt",
                                  "threshold": t_fake}))
    _file(td, "accept", ACTORS[1], p_fake, [p_fake, t_fake], [hx["root"]],
          [ACTORS[1]], note="unauthorized profile-shaped adoption")
    _file(td, "accept", ACTORS[1], rot, [p_fake], [hx["root"]],
          [ACTORS[1]], note="key-state under the unauthorized profile")
    return trust, hx["h1"], None, True, "adopted by"


def _scn_keystate_unquorumed(td):
    # Kimi P1-R part 2: key-state citing the REAL policy without its quorum
    # is an invalid record (Warrant s5.1), not a refusal trigger
    trust, hx = _fixture(td)
    rot = _put_blob(td, canon({"actor": ACTORS[1], "key": "d" * 64}))
    _file(td, "accept", ACTORS[1], rot, [hx["t1"]], [hx["root"]],
          [ACTORS[1]], note="key-state under governance, NO quorum")
    return trust, hx["h1"], None, True, "adopted by"


def _scn_keystate_quorum_refused(td):
    trust, hx = _fixture(td)
    rot = _put_blob(td, canon({"actor": ACTORS[1], "key": "d" * 64}))
    _file(td, "accept", ACTORS[0], rot, [hx["t1"]], [hx["root"]],
          [ACTORS[0], ACTORS[2]], note="key-state under GOVERNANCE policy")
    return trust, hx["h1"], None, False, "warrant CLI"


SCENARIOS = [
    ("GV-GENESIS-ADOPTED", "2-of-3 genesis adoption authorizes", _scn_genesis_adopted),
    ("GV-SUCCESSION-ROTATED", "successor adopted under rotated policy (lineage hop)", _scn_succession_rotated),
    ("GV-ANCESTOR-FORK", "ancestor mismatch is a fork, not an upgrade", _scn_ancestor_fork),
    ("GV-GENESIS-WITH-ANCESTOR", "genesis set carrying ancestor is invalid", _scn_genesis_with_ancestor),
    ("GV-HIJACK-MINTED-PAIR", "minted 1-of-1 profile+threshold pair rejected (lineage rule, 3/3 blind gate finding)", _scn_hijack_minted_pair),
    ("GV-UNDER-CARDINALITY", "under with extra blob is ineligible", _scn_under_cardinality),
    ("GV-SIGS-BELOW-THRESHOLD", "one signature and duplicate-actor signatures stay below min_sigs", _scn_sigs_below_threshold),
    ("GV-UNBOUND-KEY", "signature by a key not bound in trust config does not count", _scn_unbound_key),
    ("GV-BOUND-KEYS-AUTHORIZE", "same record authorizes once keys are bound", _scn_bound_keys_authorize),
    ("GV-FOREIGN-JURISDICTION", "embedded jurisdiction mismatch refused before signature work", _scn_foreign_jurisdiction),
    ("GV-ORPHAN-OUTSIDE-CLOSURE", "adoption outside the settlement closure is ignored", _scn_orphan_outside_closure),
    ("GV-COMPETING-SUCCESSORS", "rival authorized successors freeze the chain (no tie-break)", _scn_competing_successors),
    ("GV-KEYSTATE-UNRELATED-IGNORED", "key-state under an unrelated policy is out of scope", _scn_keystate_unrelated_ignored),
    ("GV-KEYSTATE-UNAUTH-PROFILE", "unauthorized profile cannot expand key-state scope (P1-R)", _scn_keystate_unauth_profile),
    ("GV-KEYSTATE-UNQUORUMED", "unquorumed key-state under governance ignored (Warrant s5.1)", _scn_keystate_unquorumed),
    ("GV-KEYSTATE-QUORUM-REFUSED", "quorum-authorized key-state refuses to the warrant CLI", _scn_keystate_quorum_refused),
]

VEC_PATH = os.path.join(REPO, "tests", "spec_conformance", "governance_vectors.json")


def _serialize_store(td):
    records, blobs = {}, {}
    for f in sorted(os.listdir(os.path.join(td, "records"))):
        records[f[:-5]] = json.load(open(os.path.join(td, "records", f)))
    for h in sorted(os.listdir(os.path.join(td, "blobs"))):
        blobs[h] = open(os.path.join(td, "blobs", h), "rb").read().hex()
    return {"records": records, "blobs": blobs}


def _materialize_store(td, store):
    _mk_store(td)
    for wid, env in store["records"].items():
        open(os.path.join(td, "records", wid + ".json"), "w").write(
            json.dumps(env, indent=2, sort_keys=True))
    for h, hexbytes in store["blobs"].items():
        open(os.path.join(td, "blobs", h), "wb").write(bytes.fromhex(hexbytes))


def _run_scenarios(emit=None):
    """Assert the oracle agrees with every scenario's declared expectation.
    With emit, also collect serialized vectors."""
    failures = []
    for vid, desc, builder in SCENARIOS:
        with tempfile.TemporaryDirectory() as td:
            trust, cand, prior, want_ok, note = builder(td)
            recs, blobs, bdir = load_store(td)
            got_ok, notes = verify_adoption(recs, blobs, bdir, cand, trust, prior)
            joined = "; ".join(notes)
            ok = got_ok == want_ok and note in joined
            print(("OK  " if ok else "FAIL") + "  " + vid + "  " + desc)
            if not ok:
                failures.append(f"{vid}: authorized={got_ok} (want {want_ok}); notes: {joined}")
            if emit is not None:
                emit.append({"id": vid, "description": desc, "trust": trust,
                             "store": _serialize_store(td), "candidate": cand,
                             "prior_set": prior,
                             "expected": {"authorized": want_ok, "note": note}})
    return failures


def cmd_gen():
    if not HAVE_ED25519:
        print("gen needs the 'cryptography' package")
        return 2
    vectors = []
    failures = _run_scenarios(emit=vectors)
    if failures:
        print("\nREFUSING TO GENERATE — oracle disagrees with declared expectations:")
        for f in failures:
            print("  " + f)
        return 1
    doc = {"format": "sigma-glyph.governance-vectors@v1",
           "generator": "python3 tools/anchor_governance.py gen",
           "note": ("Deterministic fixtures (fixed seeds per RFC 8032, fixed ts). "
                    "A second implementation claims conformance by replaying every "
                    "vector: reconstruct the store, run the GOV-anchors.md s3 "
                    "verification, match authorized + note substring."),
           "vectors": vectors}
    with open(VEC_PATH, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(f"\nwrote {len(vectors)} vectors -> {os.path.relpath(VEC_PATH, REPO)}")
    return 0


def cmd_replay(path):
    if not HAVE_ED25519:
        print("replay needs the 'cryptography' package")
        return 2
    doc = json.load(open(path))
    if doc.get("format") != "sigma-glyph.governance-vectors@v1":
        print("ERR: unknown vector format")
        return 1
    ok_all = True
    for v in doc["vectors"]:
        with tempfile.TemporaryDirectory() as td:
            _materialize_store(td, v["store"])
            recs, blobs, bdir = load_store(td)
            got_ok, notes = verify_adoption(recs, blobs, bdir, v["candidate"],
                                            v["trust"], v["prior_set"])
        joined = "; ".join(notes)
        good = (got_ok == v["expected"]["authorized"]
                and v["expected"]["note"] in joined)
        ok_all &= good
        print(("OK  " if good else "FAIL") + "  " + v["id"])
        if not good:
            print(f"      authorized={got_ok} notes: {joined}")
    n = len(doc["vectors"])
    print("\nGOVERNANCE-REPLAY: " + ("ALL PASS" if ok_all else "FAILURES")
          + f" ({n}/{n})" if ok_all else "")
    return 0 if ok_all else 1


def selftest():
    if not HAVE_ED25519:
        print("selftest needs the 'cryptography' package")
        return 2
    failures = _run_scenarios()
    ok_all = not failures

    def check(name, got, want=True):
        nonlocal ok_all
        good = got == want
        ok_all &= good
        print(("OK  " if good else "FAIL") + "  " + name)

    # schema edges not expressible as adoption scenarios
    check("profile without threshold pin is schema-invalid",
          valid_profile({"governance_policy": PROFILE_TAG,
                         "scope": "spec/ANCHORS.txt"}), False)
    check("trust config schema closed",
          valid_trust({"governance_trust": TRUST_TAG, "jurisdiction": "a" * 64,
                       "genesis_profile": "b" * 64,
                       "actors": {"x": ["c" * 64]}, "extra": 1}) is None)

    # projection: live repo ANCHORS.txt parses and round-trips.
    # live sections form the governed line of descent (v0.6.2 genesis
    # onward); everything pre-governance is labeled ancestors
    sections = parse_anchors(ANCHORS)
    live = [s for s in sections if not s[1]]
    check("ANCHORS.txt parses (governed line of descent)",
          len(live) >= 1 and live[-1][0] == "v0.6.2")
    check("current section is v0.6.3 with 10 anchors",
          (live[0][0], len(live[0][2])), ("v0.6.3", 10))
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
    sub.add_parser("gen", help="write pinned conformance vectors from the scenarios")
    rp = sub.add_parser("replay", help="replay pinned vectors against this verifier")
    rp.add_argument("path", nargs="?", default=VEC_PATH)
    args = ap.parse_args()
    if args.cmd == "make-blob":
        sys.exit(cmd_make_blob(args.jurisdiction, args.ancestor))
    if args.cmd == "selftest":
        sys.exit(selftest())
    if args.cmd == "gen":
        sys.exit(cmd_gen())
    if args.cmd == "replay":
        sys.exit(cmd_replay(args.path))
    if args.cmd in (None, "status"):
        tc = getattr(args, "trust_config", None)
        enforce = getattr(args, "enforce", False)
        sys.exit(cmd_status(tc, enforce))


if __name__ == "__main__":
    main()
