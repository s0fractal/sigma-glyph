#!/usr/bin/env python3
"""Differential tests for Book III federation.

Drives the Python oracle and the independent Go binary over the pinned
federation vector classes plus adversarial edge cases:

    python3 tests/federation_differential.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "impl"))
import sigma_federation as sf  # noqa: E402
from sigma_wave import interfere  # noqa: E402

GO_DIR = ROOT / "impl-go"
VEC_PATH = ROOT / "tests/spec_conformance/federation_vectors.json"


def build_go():
    out = Path(tempfile.gettempdir()) / "sigma-federation-go-differential"
    env = os.environ.copy()
    env["GOCACHE"] = str(GO_DIR / ".gocache")
    subprocess.run(["go", "build", "-o", str(out), "."], cwd=GO_DIR,
                   env=env, check=True)
    return out


GO = build_go()


def go_cmd(cmd, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    p = subprocess.run([str(GO), cmd], input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=True)
    return json.loads(p.stdout.decode())


def chk(name, got, want):
    if got != want:
        print("FAIL", name)
        print("  got :", json.dumps(got, ensure_ascii=False, sort_keys=True))
        print("  want:", json.dumps(want, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1)
    checks.append(name)


def sel_expected(res):
    return {
        "status": res["status"],
        "selected_warrant": res["selected"]["warrant_id"] if res["selected"] else None,
        "conflict_set": res["conflict_set"],
    }


def go_select(candidates, policy, jurisdiction, node, epoch):
    return go_cmd("select", {
        "candidates": candidates,
        "policy": policy,
        "jurisdiction": jurisdiction,
        "node": node,
        "epoch": epoch,
    })


def go_wave(term, selection=None, selected_wave=None, selections=None):
    req = {"term": term}
    if selections is not None:
        req["selections"] = selections
    elif selection is not None:
        req["selection"] = selection
        req["selected_wave"] = selected_wave
    return go_cmd("wave", req)["wave"]


def wid(ch):
    return ch * 64


def cand(ch, actor, ts, epoch, wave, jur=sf.J, node=sf.NODE):
    return {
        "warrant_id": wid(ch),
        "actor": actor,
        "ts": ts,
        "assertion": {
            "annotation": sf.ASSERTION_TAG,
            "jurisdiction": jur,
            "node": node,
            "epoch": epoch,
            "wave": wave,
        },
    }


checks = []
doc = json.loads(VEC_PATH.read_text())

# Pinned vector classes.
for v in doc["vectors"]:
    k = v["kind"]
    if k == "validate_assertion":
        chk(v["id"], go_cmd("validate-assertion", v["doc"])["error"],
            sf.validate_assertion(v["doc"]))
    elif k == "validate_policy":
        chk(v["id"], go_cmd("validate-policy", v["doc"])["error"],
            sf.validate_policy(v["doc"]))
    elif k == "select":
        chk(v["id"],
            go_select(v["candidates"], v["policy"], v["jurisdiction"], v["node"], v["epoch"]),
            sel_expected(sf.select(v["candidates"], v["policy"],
                                   v["jurisdiction"], v["node"], v["epoch"])))
    elif k == "wave_fed":
        if v["selected_wave"] is not None:
            py_sel = {"status": "selected", "conflict_set": [],
                      "selected": {"assertion": {"wave": v["selected_wave"]}}}
            py = sf.wave_fed(v["term"], lambda t, term=v["term"]: py_sel if t == term else None)
            go = go_wave(v["term"], {"status": "selected"}, v["selected_wave"])
        else:
            py = sf.wave_fed(v["term"], lambda t: None)
            go = go_wave(v["term"])
        chk(v["id"], go, py)
    elif k == "view_id":
        chk(v["id"],
            go_cmd("viewid", {"jurisdiction": v["jurisdiction"], "node": v["node"],
                              "policy_hash": v["policy_hash"], "epoch": v["epoch"]})["view_id"],
            sf.view_id(v["jurisdiction"], v["node"], v["policy_hash"], v["epoch"]))
    elif k == "assertion_set_root":
        chk(v["id"],
            go_cmd("setroot", {"warrant_ids": v["warrant_ids"]})["assertion_set_root"],
            sf.assertion_set_root(v["warrant_ids"]))
    elif k == "fold_probe":
        py = {"left": interfere(interfere(v["w1"], v["w2"]), v["w3"]),
              "right": interfere(v["w1"], interfere(v["w2"], v["w3"]))}
        go_left = go_cmd("interfere", {"w1": v["w1"], "w2": v["w2"]})["wave"]
        go = {"left": go_cmd("interfere", {"w1": go_left, "w2": v["w3"]})["wave"],
              "right": go_cmd("interfere", {
                  "w1": v["w1"],
                  "w2": go_cmd("interfere", {"w1": v["w2"], "w2": v["w3"]})["wave"],
              })["wave"]}
        chk(v["id"], go, py)
    elif k == "book1_unreachable":
        chk(v["id"], go_cmd("book1-unreachable"), sf._book1_fixture())
    else:
        raise SystemExit(f"unknown vector kind {k}")


# Adversarial validation.
bad_assertions = [
    ("ADV-ASSERT-BOOL-EPOCH", {**cand("1", "a", 1, 1, sf.W(1, 2, 3))["assertion"], "epoch": True}),
    ("ADV-ASSERT-EN-OVERFLOW", {**cand("1", "a", 1, 1, sf.W(1, 2, 3))["assertion"],
                                "wave": {"ph": 1, "am": 2, "en": 32768}}),
]
for name, doc0 in bad_assertions:
    chk(name, go_cmd("validate-assertion", doc0)["error"], sf.validate_assertion(doc0))

bad_policies = [
    ("ADV-POLICY-UNKNOWN", {**sf.POLICY, "x": 1}),
    ("ADV-POLICY-QUOTA-BOOL", {**sf.POLICY, "quota_per_actor_epoch": False}),
]
for name, pol in bad_policies:
    chk(name, go_cmd("validate-policy", pol)["error"], sf.validate_policy(pol))


def select_case(name, cands, policy, epoch, jurisdiction=sf.J, node=sf.NODE):
    chk(name, go_select(cands, policy, jurisdiction, node, epoch),
        sel_expected(sf.select(cands, policy, jurisdiction, node, epoch)))


select_case("ADV-PREFIX-ASC", [
    cand("1", "a", 1, 1, sf.W(0, 1, 0)),
    cand("2", "aa", 1, 1, sf.W(0, 2, 0)),
], {"federation_policy": sf.POLICY_TAG, "order": [{"field": "actor", "dir": "asc"}]}, 1)

select_case("ADV-ASTRAL-DESC", [
    cand("1", "😀actor", 1, 1, sf.W(0, 1, 0)),
    cand("2", "🧠actor", 1, 1, sf.W(0, 2, 0)),
], {"federation_policy": sf.POLICY_TAG, "order": [{"field": "actor", "dir": "desc"}]}, 1)

select_case("ADV-DECLARED-TIE-THREE", [
    cand("1", "a", 1, 7, sf.W(0, 1, 0)),
    cand("2", "b", 2, 7, sf.W(0, 2, 0)),
    cand("3", "c", 3, 7, sf.W(0, 3, 0)),
], sf.POLICY_TIE, 7)

select_case("ADV-FUTURE-BEFORE-STALE", [
    cand("1", "old", 1, 1, sf.W(0, 1, 0)),
    cand("2", "future", 2, 20, sf.W(0, 2, 0)),
], {**sf.POLICY_TIE, "max_age_epochs": 2}, 4)

select_case("ADV-QUOTA-WARRANT-TIEBREAK", [
    cand("b", "same", 1, 3, sf.W(0, 1, 0)),
    cand("a", "same", 1, 3, sf.W(0, 2, 0)),
    cand("c", "same", 1, 3, sf.W(0, 3, 0)),
], {"federation_policy": sf.POLICY_TAG,
    "order": [{"field": "actor", "dir": "asc"}],
    "quota_per_actor_epoch": 1}, 3)

select_case("ADV-MALFORMED-METADATA", [
    {**cand("1", "a", 1, 1, sf.W(0, 1, 0)), "warrant_id": wid("A")},
    {**cand("2", "b", 1, 1, sf.W(0, 2, 0)), "ts": True},
    {**cand("3", "c", 1, 1, sf.W(0, 3, 0)), "actor": ""},
], sf.POLICY_TIE, 1)

bad_blob = cand("1", "a", 1, 1, sf.W(0, 1, 0))
bad_blob["assertion"] = {**bad_blob["assertion"], "extra": "reject"}
select_case("ADV-MALFORMED-ASSERTION-SKIPPED", [bad_blob], sf.POLICY_TIE, 1)

select_case("ADV-WHITESPACE-ACTOR-NOT-LIVE", [
    {**cand("1", "a", 1, 1, sf.W(0, 1, 0)), "actor": "   "},
    {**cand("2", "b", 1, 1, sf.W(0, 2, 0)), "actor": "\u00a0\t"},
], sf.POLICY_TIE, 1)


# Adversarial wave semantics.
chk("ADV-WAVE-PIN-K", go_wave("K"), sf.wave_fed("K", lambda t: None))
chk("ADV-WAVE-PH-ONLY-ABSENT", go_wave("SATOSHI"), sf.wave_fed("SATOSHI", lambda t: None))
chk("ADV-WAVE-FALSE-ALIAS", go_wave("FALSE"), sf.wave_fed("FALSE", lambda t: None))
conflict = {"status": "conflict", "conflict_set": [wid("1"), wid("2")]}
chk("ADV-WAVE-CONFLICT-POISONS", go_wave("K", conflict),
    sf.wave_fed("K", lambda t: {"status": "conflict", "selected": None,
                                "conflict_set": [wid("1"), wid("2")]}))
term = ["APPLY", "K", "I"]
direct = sf.W(123, 456, -7)
chk("ADV-WAVE-APPLY-DIRECT-OVERRIDE", go_wave(term, {"status": "selected"}, direct),
    sf.wave_fed(term, lambda t: {"status": "selected", "conflict_set": [],
                                 "selected": {"assertion": {"wave": direct}}} if t == term else None))


ph = sf.sha_hex(sf.jcs(sf.POLICY_ACTOR_DESC))
chk("ADV-VIEWID", go_cmd("viewid", {"jurisdiction": sf.J2, "node": sf.NODE,
                                    "policy_hash": ph, "epoch": 42})["view_id"],
    sf.view_id(sf.J2, sf.NODE, ph, 42))
ids = [wid("f"), wid("0"), wid("a"), wid("0")]
chk("ADV-SETROOT-DUP-SORT", go_cmd("setroot", {"warrant_ids": ids})["assertion_set_root"],
    sf.assertion_set_root(ids))

n = len(checks)
print(f"FEDERATION-DIFFERENTIAL: ALL AGREE ({n}/{n})")
