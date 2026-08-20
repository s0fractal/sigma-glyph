#!/usr/bin/env python3
"""Two sovereign jurisdictions, one node — Book III live, end to end.

Everything the Books promise on paper, exercised with real artifacts:
actual Warrant-format records (signed, content-addressed, verifiable by
tools/warrant_verify.py), a file-copy transport between two stores, and
every view derived by the reference oracle impl/sigma_federation.py.

    python3 examples/two-jurisdictions/demo.py [--keep DIR]

What it shows, in order:
  1. Two jurisdictions are forged (genesis root + selection policy each).
  2. Kyiv actors assert waves for the same node; Kyiv's policy selects one.
  3. Lviv selects differently under its own policy — divergence by design.
  4. Gossip = copying files. Kyiv's records sync into Lviv's store and
     change nothing: assertions embed their jurisdiction root (§2 replay
     resistance), so foreign assertions are never live locally.
  5. A genuine tie in Lviv surfaces as a ConflictSet -> the node is
     treated as unannotated; the conflict poisons structural derivation.
  6. Divergence is named mechanically: AnnotationViewID + assertion_set_root.
  7. Both stores pass the read-only warrant verifier — these are real
     records, not mocks.

Node ids here are synthetic hex64 (the same convention as the oracle's own
vectors); a production annotator would use Book I NodeHashes. Warrant ids in
this transcript are deterministic (fixed timestamps; signatures never enter a
WarrantID) — only key material differs between runs.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "impl"))
from sigma_federation import (  # noqa: E402
    ASSERTION_TAG, POLICY_TAG, assertion_set_root, select, view_id, wave_fed)

# The signed message comes from tools/, not from a copy in the demo. This is an
# example, and an example that open-codes the construction teaches it -- which
# is how six of the seven pre-consolidation copies came to exist. The import
# direction is examples/ -> tools/ and never impl/ -> tools/: the oracles in
# impl/ are a dependency-free reference implementation and sign nothing.
sys.path.insert(0, os.path.join(REPO, "tools"))
import warrant_sig  # noqa: E402

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    sys.exit("demo needs the 'cryptography' package (pip install cryptography)")


def jcs(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


NODE = sha(b"demo-node:SATOSHI")          # the one node everyone argues about
TERM = "DEMO_SATOSHI"                     # its symbolic name for wave_fed
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STORE_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


def content_path(directory, digest, suffix=""):
    """Map a content address to one regular path beneath ``directory``."""
    if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
        return None
    root = os.path.realpath(directory)
    path = os.path.realpath(os.path.join(root, digest + suffix))
    try:
        if os.path.commonpath((root, path)) != root:
            return None
    except ValueError:
        return None
    return path


class Jurisdiction:
    """A real .warrants store: records/, blobs/, genesis.json."""

    def __init__(self, name, root_dir, policy):
        if STORE_NAME.fullmatch(name) is None:
            raise ValueError("jurisdiction name must be a simple lowercase label")
        self.name = name
        self.dir = os.path.join(os.path.realpath(root_dir), name)
        os.makedirs(os.path.join(self.dir, "records"))
        os.makedirs(os.path.join(self.dir, "blobs"))
        self.keys = {}
        self.policy = policy
        self.policy_hash = self.put_blob(jcs(policy))
        manifesto = f"jurisdiction {name}: annotation policy in force".encode()
        self.root = self.file(
            "propose", f"founder@{name}", self.put_blob(manifesto),
            prior=[], ts=1783400000, note=f"genesis of {name}")
        with open(os.path.join(self.dir, "genesis.json"), "w",
                  encoding="utf-8") as genesis:
            json.dump({"roots": [self.root]}, genesis, sort_keys=True,
                      separators=(",", ":"))

    def put_blob(self, b):
        h = sha(b)
        path = content_path(os.path.join(self.dir, "blobs"), h)
        if path is None:  # generated SHA-256; an invariant guard, not user input
            raise ValueError("generated blob hash is not hex64")
        with open(path, "wb") as f:
            f.write(b)
        return h

    def key(self, actor):
        if actor not in self.keys:
            self.keys[actor] = Ed25519PrivateKey.generate()
        return self.keys[actor]

    def file(self, decision, actor, subject_hash, prior, ts, note):
        body = {"warrant": "0.2", "decision": decision,
                "subject": {"hash": subject_hash, "note": note},
                "under": [self.policy_hash],
                "because": [{"kind": "prose", "text": note}],
                "evidence": [], "actor": {"id": actor},
                "prior": prior, "ts": ts}
        wid = sha(jcs(body))
        sk = self.key(actor)
        env = {"body": body, "sigs": [warrant_sig.sig_entry(actor, sk, wid)]}
        path = content_path(os.path.join(self.dir, "records"), wid, ".json")
        if path is None:  # generated SHA-256; an invariant guard, not user input
            raise ValueError("generated warrant id is not hex64")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(env, f, indent=2, sort_keys=True)
        return wid

    def assert_wave(self, actor, epoch, wave, ts):
        blob = jcs({"annotation": ASSERTION_TAG, "jurisdiction": self.root,
                    "node": NODE, "epoch": epoch, "wave": wave})
        return self.file("accept", actor, self.put_blob(blob),
                         prior=[self.root], ts=ts,
                         note=f"wave assertion by {actor}, epoch {epoch}")

    def candidates(self):
        """Store -> oracle candidates: accepted assertions under our policy.

        (A settlement-grade pipeline would also run threshold/key-state
        checks via the warrant CLI first; the demo keeps that stage out of
        frame and takes every well-formed accept at face value.)
        """
        out = []
        records = os.path.join(self.dir, "records")
        blobs = os.path.join(self.dir, "blobs")
        for filename in sorted(os.listdir(records)):
            candidate = _load_candidate(records, blobs, filename)
            if candidate is not None:
                out.append(candidate)
        return out

    def view(self, epoch):
        sel = select(self.candidates(), self.policy, self.root, NODE, epoch)
        resolve = lambda term: sel if term == TERM else None
        return {
            "selection": sel,
            "wave": wave_fed(TERM, resolve),
            "derived_apply": wave_fed(["APPLY", "I", TERM], resolve),
            "view_id": view_id(self.root, NODE, self.policy_hash, epoch),
            "set_root": assertion_set_root(
                [c["warrant_id"] for c in self.candidates()
                 if c["assertion"]["jurisdiction"] == self.root]),
        }


def _load_candidate(records, blobs, filename):
    if not filename.endswith(".json"):
        return None
    warrant_id = filename.removesuffix(".json")
    record_path = content_path(records, warrant_id, ".json")
    if record_path is None or not os.path.isfile(record_path):
        return None
    with open(record_path, encoding="utf-8") as record_source:
        body = json.load(record_source)["body"]
    if body["decision"] != "accept":
        return None
    blob_path = content_path(blobs, body["subject"].get("hash"))
    if blob_path is None or not os.path.isfile(blob_path):
        return None
    try:
        with open(blob_path, "rb") as blob_source:
            doc = json.loads(blob_source.read())
    except ValueError:
        return None
    if not isinstance(doc, dict) or doc.get("annotation") != ASSERTION_TAG:
        return None
    return {"warrant_id": warrant_id, "actor": body["actor"]["id"],
            "ts": body["ts"], "assertion": doc}


def _copy_gossip_file(source_dir, target_dir, filename, suffix):
    digest = (filename.removesuffix(suffix)
              if suffix and filename.endswith(suffix) else filename)
    source = content_path(source_dir, digest, suffix)
    target = content_path(target_dir, digest, suffix)
    if source is None or target is None or not os.path.isfile(source):
        return False
    if os.path.exists(target):
        return False
    shutil.copy(source, target)
    return True


def gossip(src, dst):
    """The entire transport profile: copy record and blob files."""
    n = 0
    for sub in ("records", "blobs"):
        source_dir = os.path.join(src.dir, sub)
        target_dir = os.path.join(dst.dir, sub)
        suffix = ".json" if sub == "records" else ""
        for filename in os.listdir(source_dir):
            n += _copy_gossip_file(source_dir, target_dir, filename, suffix)
    return n


def show(tag, name, v):
    sel = v["selection"]
    if sel["status"] == "selected":
        who = sel["selected"]["actor"]
        line = f"selected {who}'s assertion -> wave {v['wave']}"
    elif sel["status"] == "conflict":
        line = (f"ConflictSet of {len(sel['conflict_set'])} "
                f"-> node treated as UNANNOTATED (wave {v['wave']})")
    else:
        line = f"absent (wave {v['wave']})"
    print(f"  [{tag}] {name}: {line}")
    print(f"        APPLY(I, node) structural derivation -> {v['derived_apply']}")
    print(f"        ViewID   {v['view_id']}")
    print(f"        set_root {v['set_root']}")


def main():
    epoch_label = "epoch 8"
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", metavar="DIR",
                    help="build stores under DIR instead of a temp dir")
    args = ap.parse_args()
    root = args.keep or tempfile.mkdtemp(prefix="sigma-fed-demo-")
    if args.keep:
        os.makedirs(root, exist_ok=True)

    print("== 1. Forge two jurisdictions ==")
    kyiv = Jurisdiction("kyiv", root, {
        "federation_policy": POLICY_TAG,
        "order": [{"field": "epoch", "dir": "desc"},
                  {"field": "warrant_id", "dir": "asc"}],
        "max_age_epochs": 10})
    lviv = Jurisdiction("lviv", root, {
        "federation_policy": POLICY_TAG,
        "order": [{"field": "epoch", "dir": "desc"}]})  # no tiebreak: ties surface
    print(f"  kyiv root {kyiv.root}")
    print(f"  lviv root {lviv.root}")
    print(f"  the node in dispute: {NODE}")

    print("\n== 2. Kyiv asserts ==")
    kyiv.assert_wave("alice@kyiv", 5, {"ph": 8192, "am": 40000, "en": -100},
                     ts=1783400100)
    kyiv.assert_wave("bob@kyiv", 7, {"ph": 8192, "am": 20000, "en": 50},
                     ts=1783400200)
    show(epoch_label, "kyiv", kyiv.view(8))

    print("\n== 3. Lviv asserts — its own truth, same node ==")
    lviv.assert_wave("carol@lviv", 3, {"ph": 8192, "am": 65535, "en": -32768},
                     ts=1783400300)
    show(epoch_label, "lviv", lviv.view(8))

    print("\n== 4. Gossip: kyiv -> lviv (transport = copying files) ==")
    n = gossip(kyiv, lviv)
    v = lviv.view(8)
    print(f"  {n} objects copied into lviv's store")
    show(epoch_label, "lviv after sync", v)
    assert v["selection"]["selected"]["actor"] == "carol@lviv", \
        "replay resistance broken: a foreign assertion went live"
    print("  -> kyiv's assertions are present but NOT live: each embeds the")
    print("     kyiv root (Book III §2); lviv's view is untouched. Sovereignty.")

    print("\n== 5. A genuine tie in lviv ==")
    lviv.assert_wave("eve@lviv", 3, {"ph": 16384, "am": 1000, "en": 0},
                     ts=1783400400)
    show(epoch_label, "lviv", lviv.view(8))
    print("  -> clients MUST NOT merge; automation treats the node as")
    print("     unannotated, and the absence poisons APPLY derivation (§4/§5).")

    print("\n== 6. Divergence, named mechanically ==")
    kv, lv = kyiv.view(8), lviv.view(8)
    print(f"  kyiv ViewID {kv['view_id']}")
    print(f"  lviv ViewID {lv['view_id']}")
    print("  same node, different (jurisdiction, policy) coordinates —")
    print(f"  permanent and by design; kyiv still sees wave {kv['wave']}.")

    print("\n== 7. These are real warrant stores ==")
    verifier = os.path.join(REPO, "tools", "warrant_verify.py")
    ok = True
    for j in (kyiv, lviv):
        r = subprocess.run([sys.executable, verifier, j.dir],
                           capture_output=True, text=True)
        print(f"  {j.name}: {r.stdout.strip().splitlines()[-1]}")
        ok &= r.returncode == 0
    if not ok:
        sys.exit("warrant verification FAILED")

    if args.keep:
        print(f"\nstores kept under {root}")
    else:
        shutil.rmtree(root)
    print("\nDEMO: ALL ASSERTIONS HELD (sovereign views diverge, "
          "replay is dead, ties surface, stores verify)")


if __name__ == "__main__":
    main()
