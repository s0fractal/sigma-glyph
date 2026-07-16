#!/usr/bin/env python3
"""hermes_review.py — local AI review that emits a signed, check-backed Warrant.

    python3 tools/hermes_review.py [<git-ref>]     # default HEAD

Flow (the "hermes proposes, the check decides, the key binds" pattern):
  1. take the diff of <git-ref>;
  2. ask the LOCAL hermes model (ollama) for an adversarial review;
  3. run the deterministic conformance gate OURSELVES (not the model);
  4. pin the diff, the check command, and the check transcript as
     content-addressed blobs in .warrants/blobs/;
  5. emit a Warrant v0.1 record in .warrants/records/, signed by hermes'
     Ed25519 key. decision = accept iff the gate passed.

The model's opinion is never trusted on its own — the warrant's weight is the
pinned pass/fail transcript that its opinion provoked. Verify offline with
tools/warrant_verify.py; ratify (human co-sign) with tools/cosign.py.

Env: HERMES_MODEL (default qwen3-coder:30b), HERMES_OLLAMA (default
http://localhost:11434), HERMES_CHECK (default the run_reference.py gate),
HERMES_KEY (default ~/.config/sigma-hermes/ed25519.key — auto-created).
"""
import hashlib, json, os, subprocess, sys, time, urllib.request

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(REPO, ".warrants")
ACTOR = os.environ.get("HERMES_ACTOR", "hermes-qwen3-coder@local")
MODEL = os.environ.get("HERMES_MODEL", "qwen3-coder:30b")
OLLAMA = os.environ.get("HERMES_OLLAMA", "http://localhost:11434")
CHECK = os.environ.get("HERMES_CHECK",
                       "python3 tests/spec_conformance/run_reference.py")
KEYFILE = os.path.expanduser(
    os.environ.get("HERMES_KEY", "~/.config/sigma-hermes/ed25519.key"))
MODEL_INPUT_CAP = 16000  # chars of diff fed to the model; full diff is pinned


def canon(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def put_blob(data: bytes) -> str:
    """Content-address `data` into .warrants/blobs/ and return its hash."""
    h = hashlib.sha256(data).hexdigest()
    path = os.path.join(STORE, "blobs", h)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    return h


def load_key() -> Ed25519PrivateKey:
    if not os.path.exists(KEYFILE):
        os.makedirs(os.path.dirname(KEYFILE), exist_ok=True)
        seed = Ed25519PrivateKey.generate().private_bytes_raw().hex()
        with open(KEYFILE, "w") as f:
            f.write(seed + "\n")
        os.chmod(KEYFILE, 0o600)
        pub = Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(seed)).public_key().public_bytes_raw().hex()
        print(f"[hermes] new identity key created: {KEYFILE}\n"
              f"[hermes] pubkey {pub}", file=sys.stderr)
    return Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(open(KEYFILE).read().strip()))


def ask_hermes(diff: str, note: str) -> str:
    prompt = (
        "You are an adversarial code reviewer. Review the following git change "
        "for correctness bugs, spec violations, and risk. Be concise: a one-line "
        "VERDICT (LGTM / CONCERNS / BLOCK), then bullet findings. Do not restate "
        f"the diff.\n\nCHANGE: {note}\n\n----- DIFF -----\n{diff[:MODEL_INPUT_CAP]}"
    )
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=json.dumps({"model": MODEL, "prompt": prompt,
                         "stream": False}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r).get("response", "").strip()


def run_check() -> tuple[str, str]:
    """Run the deterministic gate; return (transcript, verdict)."""
    p = subprocess.run(CHECK, shell=True, cwd=REPO, capture_output=True,
                       text=True)
    transcript = (f"$ {CHECK}\n[exit {p.returncode}]\n"
                  f"----- stdout -----\n{p.stdout}\n"
                  f"----- stderr -----\n{p.stderr}")
    return transcript, ("pass" if p.returncode == 0 else "fail")


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    sha = subprocess.check_output(["git", "rev-parse", ref], cwd=REPO,
                                  text=True).strip()
    subject = subprocess.check_output(["git", "log", "-1", "--format=%s", sha],
                                      cwd=REPO, text=True).strip()
    diff = subprocess.check_output(["git", "show", "--format=medium", sha],
                                   cwd=REPO, text=True)
    note = f"hermes review of {sha[:12]}: {subject}"

    print(f"[hermes] reviewing {sha[:12]} with {MODEL} …", file=sys.stderr)
    review = ask_hermes(diff, note)
    print(f"[hermes] running gate: {CHECK}", file=sys.stderr)
    transcript, verdict = run_check()

    diff_h = put_blob(diff.encode())
    check_h = put_blob((CHECK + "\n").encode())
    trans_h = put_blob(transcript.encode())

    body = {
        "actor": {"id": ACTOR},
        "because": [
            {"kind": "prose", "text": review},
            {"kind": "check", "runtime": "cmd@v1", "check": check_h,
             "transcript": trans_h, "verdict": verdict},
        ],
        "decision": "accept" if verdict == "pass" else "reject",
        "evidence": [trans_h],
        "prior": [],
        "subject": {"hash": diff_h, "note": note},
        "ts": int(time.time()),
        "under": [],
        "warrant": "0.1",
    }
    wid = hashlib.sha256(canon(body)).hexdigest()
    sk = load_key()
    env = {"body": body, "sigs": [{
        "actor": ACTOR, "key": sk.public_key().public_bytes_raw().hex(),
        "sig": sk.sign(bytes.fromhex(wid)).hex()}]}
    rec = os.path.join(STORE, "records", wid + ".json")
    with open(rec, "w") as f:
        json.dump(env, f, indent=2, sort_keys=True, ensure_ascii=False)

    print(f"\n--- hermes review ---\n{review}\n")
    print(f"gate verdict: {verdict.upper()}  ->  decision: {body['decision']}")
    print(f"warrant {wid[:12]}… written to .warrants/records/{wid}.json")
    print(f"verify: python3 tools/warrant_verify.py")
    print(f"ratify: python3 tools/cosign.py {wid} you@host <yourkey>")


if __name__ == "__main__":
    main()
