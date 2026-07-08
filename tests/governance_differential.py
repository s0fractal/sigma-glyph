#!/usr/bin/env python3
"""Differential tests for GOV anchor governance.

Drives the Python reference replay command and the independent Go gov-replay
command over pinned vectors plus adversarial single-vector mutations:

    python3 tests/governance_differential.py
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import anchor_governance as ag  # noqa: E402

GO_DIR = ROOT / "impl-go"
VEC_PATH = ROOT / "tests/spec_conformance/governance_vectors.json"


def build_go():
    out = Path(tempfile.gettempdir()) / "sigma-federation-go-governance-differential"
    env = os.environ.copy()
    env["GOCACHE"] = str(GO_DIR / ".gocache")
    subprocess.run(["go", "build", "-o", str(out), "."], cwd=GO_DIR,
                   env=env, check=True)
    return out


GO = build_go()


def jcs(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def sha_hex(b):
    return hashlib.sha256(b).hexdigest()


def sk(actor):
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"adr007-fixture:" + actor.encode()).digest())


def pub(actor):
    return sk(actor).public_key().public_bytes_raw().hex()


def signed_env(body, signers):
    rid = sha_hex(jcs(body))
    return rid, {
        "body": body,
        "sigs": [
            {"actor": actor, "key": pub(actor),
             "sig": sk(actor).sign(bytes.fromhex(rid)).hex()}
            for actor in signers
        ],
    }


def add_blob(v, obj):
    raw = jcs(obj) if not isinstance(obj, bytes) else obj
    h = sha_hex(raw)
    v["store"]["blobs"][h] = raw.hex()
    return h


def parse_blob(v, h):
    return json.loads(bytes.fromhex(v["store"]["blobs"][h]))


def find_accept(v, subject_hash):
    matches = []
    for rid, env in v["store"]["records"].items():
        body = env.get("body", {})
        if (body.get("decision") == "accept"
                and body.get("subject", {}).get("hash") == subject_hash):
            matches.append(rid)
    if not matches:
        raise RuntimeError(f"no accept for subject {subject_hash}")
    return sorted(matches)[0]


def replace_record(v, old_rid, body, signers):
    new_rid, env = signed_env(body, signers)
    del v["store"]["records"][old_rid]
    v["store"]["records"][new_rid] = env
    return new_rid


def add_record(v, body, signers):
    rid, env = signed_env(body, signers)
    v["store"]["records"][rid] = env
    return rid


def threshold_for_profile(v, profile_hash):
    profile = parse_blob(v, profile_hash)
    return profile["threshold"]


def oracle_verdict(v):
    with tempfile.TemporaryDirectory() as td:
        ag._materialize_store(td, v["store"])
        recs, blobs, bdir = ag.load_store(td)
        return ag.verify_adoption(recs, blobs, bdir, v["candidate"],
                                  v["trust"], v["prior_set"])


def single_doc(v):
    got_ok, _notes = oracle_verdict(v)
    out = copy.deepcopy(v)
    out["expected"] = {"authorized": got_ok, "note": ""}
    return {"format": "sigma-glyph.governance-vectors@v1",
            "vectors": [out]}


def run_replays(name, v):
    doc = single_doc(v)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f, sort_keys=True, ensure_ascii=False)
        f.write("\n")
        path = f.name
    try:
        py = subprocess.run([sys.executable, str(TOOLS / "anchor_governance.py"),
                             "replay", path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
        go = subprocess.run([str(GO), "gov-replay", path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    finally:
        os.unlink(path)
    if py.returncode != 0 or go.returncode != 0:
        print("FAIL", name)
        print("python stdout:\n" + py.stdout)
        print("python stderr:\n" + py.stderr)
        print("go stdout:\n" + go.stdout)
        print("go stderr:\n" + go.stderr)
        raise SystemExit(1)
    checks.append(name)


def clone(v):
    return copy.deepcopy(v)


def mut_tamper_signature(v):
    v = clone(v)
    rid = find_accept(v, v["candidate"])
    sig = v["store"]["records"][rid]["sigs"][0]["sig"]
    v["store"]["records"][rid]["sigs"][0]["sig"] = sig[:-2] + ("00" if sig[-2:] != "00" else "ff")
    return v


def mut_strip_adoption_sigs(v):
    v = clone(v)
    rid = find_accept(v, v["candidate"])
    v["store"]["records"][rid]["sigs"] = []
    return v


def mut_remove_lineage_record(v):
    v = clone(v)
    for rid, env in list(v["store"]["records"].items()):
        h = env.get("body", {}).get("subject", {}).get("hash")
        if h in v["store"]["blobs"] and h != v["trust"]["genesis_profile"]:
            try:
                if parse_blob(v, h).get("governance_policy") == ag.PROFILE_TAG:
                    del v["store"]["records"][rid]
                    return v
            except Exception:
                pass
    raise RuntimeError("no lineage record found")


def mut_replace_under_with_minted_pair(v):
    v = clone(v)
    evil_t = add_blob(v, {"warrant_policy": "0.3",
                          "threshold": {"min_sigs": 1,
                                        "actors": ["model-a@sigma-glyph"]}})
    evil_p = add_blob(v, {"governance_policy": ag.PROFILE_TAG,
                          "scope": "spec/ANCHORS.txt",
                          "threshold": evil_t})
    rid = find_accept(v, v["candidate"])
    body = copy.deepcopy(v["store"]["records"][rid]["body"])
    body["under"] = [evil_p, evil_t]
    replace_record(v, rid, body, ["model-a@sigma-glyph"])
    return v


def mut_flip_blob_jurisdiction(v):
    v = clone(v)
    blob = parse_blob(v, v["candidate"])
    blob["jurisdiction"] = "f" * 64
    new_h = add_blob(v, blob)
    rid = find_accept(v, v["candidate"])
    body = copy.deepcopy(v["store"]["records"][rid]["body"])
    body["subject"]["hash"] = new_h
    replace_record(v, rid, body, ["founder@s0fractal", "model-b@sigma-glyph"])
    v["candidate"] = new_h
    return v


def mut_orphan_adoption_prior(v):
    v = clone(v)
    rid = find_accept(v, v["candidate"])
    body = copy.deepcopy(v["store"]["records"][rid]["body"])
    body["prior"] = []
    replace_record(v, rid, body, ["founder@s0fractal", "model-b@sigma-glyph"])
    return v


def mut_duplicate_rival_blob(v):
    v = clone(v)
    candidate = parse_blob(v, v["candidate"])
    rival = copy.deepcopy(candidate)
    rival["anchors"][0]["anchor"] = "d" * 64
    rival_h = add_blob(v, rival)
    prior_accept = find_accept(v, v["prior_set"])
    p = v["trust"]["genesis_profile"]
    t = threshold_for_profile(v, p)
    body = {"warrant": "0.2", "decision": "accept",
            "subject": {"hash": rival_h, "note": "rival mutation"},
            "under": [p, t],
            "because": [{"kind": "prose", "text": "rival mutation"}],
            "evidence": [],
            "actor": {"id": "founder@s0fractal"},
            "prior": [prior_accept],
            "ts": 1783400000}
    add_record(v, body, ["founder@s0fractal", "model-b@sigma-glyph"])
    return v


checks = []
doc = json.loads(VEC_PATH.read_text())
vectors = doc["vectors"]
by_id = {v["id"]: v for v in vectors}

for v in vectors:
    run_replays(v["id"], v)

mutations = [
    ("ADV-TAMPER-SIGNATURE-BYTE", mut_tamper_signature(by_id["GV-GENESIS-ADOPTED"])),
    ("ADV-STRIP-ADOPTION-SIGS", mut_strip_adoption_sigs(by_id["GV-GENESIS-ADOPTED"])),
    ("ADV-REMOVE-LINEAGE-RECORD", mut_remove_lineage_record(by_id["GV-SUCCESSION-ROTATED"])),
    ("ADV-MINTED-UNDER-PAIR", mut_replace_under_with_minted_pair(by_id["GV-GENESIS-ADOPTED"])),
    ("ADV-FLIP-BLOB-JURISDICTION", mut_flip_blob_jurisdiction(by_id["GV-GENESIS-ADOPTED"])),
    ("ADV-ORPHAN-ADOPTION-PRIOR", mut_orphan_adoption_prior(by_id["GV-BOUND-KEYS-AUTHORIZE"])),
    ("ADV-DUPLICATE-RIVAL-BLOB", mut_duplicate_rival_blob(by_id["GV-BOUND-KEYS-AUTHORIZE"])),
]

for name, v in mutations:
    run_replays(name, v)

n = len(checks)
print(f"GOVERNANCE-DIFFERENTIAL: ALL AGREE ({n}/{n})")
