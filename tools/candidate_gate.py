#!/usr/bin/env python3
"""Put one frozen candidate in front of three model families, blind, and record it.

    python3 tools/candidate_gate.py gates/v0.7.0-candidate

The project's own rule (ADR-007, GOV-anchors) is that a normative change is
gated by three independently-prompted reviewers from three different families
before it can be adopted. This runs that gate and writes down what it actually
did, because the failure mode a gate has is not "a reviewer was wrong" — it is
"nobody can tell afterwards what the reviewer was shown".

So every run records, per reviewer: the exact model id the API answered with,
the SHA-256 of the prompt, UTC timestamps for request and response, and the raw
response verbatim, in a file nobody edits. A reviewer that times out, errors or
returns nothing is written down as NO VERDICT with the reason. NO VERDICT is a
result; a missing file is not.

Each reviewer gets a fresh context and the same prompt. No reviewer sees another
reviewer's answer, and none is shown prior reviews of earlier releases — a gate
whose subject is "do you agree with the last three reviewers" measures something
else.

One honest limit on that, from round 2 onward. The prompt carries the candidate's
own ADR, and once a round has produced findings the ADR records their
dispositions — which necessarily includes why a reviewer was disagreed with.
Reviewers are therefore blind to each other *within* a round and not blind to
earlier rounds' arguments. This is a real weakening and not a hypothetical one:
in round 2 of the v0.7.0 candidate, one family reversed a P0 it had raised in
round 1 and cited another family's round-1 reasoning as its ground. That is a
legitimate change of mind and it is not independent confirmation. Where a
disputed point survives a round, count the independent judgments, not the
verdicts.

Before anything is sent, every byte named in the freeze record is re-hashed and
must match. A gate over bytes that have since moved is worse than no gate,
because it reads as coverage.

The key comes from $OPENROUTER_API_KEY, or from OPEN_ROUTER in ~/.env. It is
never written to any output file.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://openrouter.ai/api/v1/chat/completions"

# Three families, one reviewer each. Dated ids where the vendor publishes one,
# so "which model said this" survives the vendor moving a floating alias.
REVIEWERS = [
    ("google", "google/gemini-3.1-pro-preview"),
    ("deepseek", "deepseek/deepseek-v4-pro-0813"),
    ("moonshot", "moonshotai/kimi-k3"),
]

# Shown to every reviewer, in this order.
SOURCES = [
    "proposals/ADR-010-three-inputs-and-a-receipt.md",
    "spec/book-1-truth.md",
    "spec/book-2-navigation.md",
    "spec/book-3-federation.md",
    "spec/VERSIONS.md",
    "spec/GOV-anchors.md",
    "spec/book-1-truth.en.md",
]

SYSTEM = """You are one of three independent reviewers, each from a different \
model family, deciding whether a proposed change to a normative specification \
may be adopted. You are not being asked to be agreeable and you are not being \
asked to be harsh. You are being asked to be correct.

You cannot run code. Do not pretend you did. Where a claim is checkable by \
arithmetic or by reading the supplied bytes, check it and show the work.

Some things you must NOT treat as evidence:
- that the project's CI is green. The CI, the guard it runs and the tests it \
runs all live in the revision under review; a change can alter all three \
together. Green CI is a fact about a script, not an independent attestation.
- that previous releases were gated. You are reviewing these bytes.
- that the authors say a check exists. If the text does not say it normatively, \
an implementer is not bound by it.

Severity ladder:
  P0  two conforming implementations can disagree on a result, or the text \
contradicts itself or the vector suite
  P1  the text is silent where an implementer must guess, or a normative \
requirement is unenforceable as written
  P2  clarity, naming, structure
  P3  future work

For every P0 and P1, give an executable counterexample: a concrete term, budget \
and environment (or a concrete document state) plus the two different results \
two conforming implementations would produce. A severity claim with no \
counterexample is a P2.

End your review with exactly one line, alone, of the form:

VERDICT: ADOPT
VERDICT: ADOPT-WITH-AMENDMENTS
VERDICT: REJECT

ADOPT-WITH-AMENDMENTS means every P0 is absent and the P1s you list are, in your \
judgement, fixable by editing the text without changing what the machine does. \
REJECT means at least one P0 stands, or the candidate should not proceed in this \
shape."""


def key():
    found = os.environ.get("OPENROUTER_API_KEY")
    if not found:
        env = Path.home() / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                name, sep, value = line.partition("=")
                if sep and name.strip() == "OPEN_ROUTER":
                    found = value.strip().strip('"').strip("'")
                    break
    if not found:
        sys.exit("no OpenRouter key: set OPENROUTER_API_KEY, or OPEN_ROUTER in ~/.env")
    return found


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def frozen_digests(freeze):
    """The SHA-256 block of the freeze record, as {path: digest}."""
    text = (ROOT / freeze / "FREEZE.md").read_text()
    return {path: value for value, path in
            re.findall(r"^ {4}([0-9a-f]{64}) {2}(\S+)$", text, re.M)}


def check_freeze(freeze):
    """Refuse to gate bytes that have moved since they were frozen."""
    expected = frozen_digests(freeze)
    if not expected:
        sys.exit(f"{freeze}/FREEZE.md lists no file digests; nothing to verify")
    moved = [path for path, want in expected.items() if digest(path) != want]
    if moved:
        sys.exit("these files have changed since the freeze — re-freeze and "
                 "re-gate, do not reuse a verdict:\n  " + "\n  ".join(moved))
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    print(f"[gate] {len(expected)} frozen files verified at {head[:12]}",
          file=sys.stderr)
    return head, expected


def build_prompt():
    # Against the WORKING TREE, not HEAD. The files whose digests `check_freeze`
    # has just verified are the ones on disk; diffing HEAD instead made the
    # prompt depend on which commit happened to be checked out, so re-running
    # the tool after any later commit produced a different prompt for the same
    # frozen bytes — and silently overwrote the record of what a reviewer saw.
    diff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "v0.6.7", "--",
         "spec/book-1-truth.md", "spec/book-2-navigation.md",
         "spec/book-3-federation.md"],
        capture_output=True, text=True, check=True).stdout
    sources = "\n\n".join(
        f"===== FILE: {p} (sha256 {digest(p)}) =====\n{(ROOT / p).read_text()}"
        for p in SOURCES)
    return f"""A candidate revision of a normative specification is proposed for \
adoption. It is NOT adopted: its anchor section is marked CANDIDATE and it \
carries no signature.

The adopted release is v0.6.7 (Book I 0.5.2, Books II and III 0.6.1). The \
candidate is v0.7.0 (Book I 0.6.0, Books II and III 0.7.0).

THE CHANGE, as a diff of the three normative Books against the adopted release:

```diff
{diff}```

THE CANDIDATE'S OWN ARGUMENT, and then the full text of every Book at the \
candidate revision, plus the versioning rules and the governance profile:

{sources}

Two facts about scope, so you spend your attention where it matters:

1. The English rendering `spec/book-1-truth.en.md` is informative, not \
normative. It is included because the candidate claims it carries the same \
requirements as the Ukrainian text; disagreement between them is a finding.
2. `spec/GOV-anchors.md` is unchanged by this candidate, and pins its normative \
dependencies as "Book I v0.5.2 / Book II v0.6.1 / Book III v0.6.1". The authors \
did not edit it and say so. Whether that is correct is in scope.

Review the candidate now."""


def ask(model, prompt, timeout, max_tokens):
    body = json.dumps({"model": model,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt}],
                       "max_tokens": max_tokens}).encode()
    request = urllib.request.Request(
        API, data=body,
        headers={"Authorization": f"Bearer {key()}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/s0fractal/sigma-glyph",
                 "X-Title": "sigma-glyph v0.7.0 candidate gate"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"api error: {payload['error']}")
    choice = payload["choices"][0]
    content = choice["message"].get("content") or choice["message"].get("reasoning")
    if not content or not content.strip():
        raise RuntimeError("empty content; finish_reason="
                           f"{choice.get('finish_reason')}")
    return content, payload.get("model", model), choice.get("finish_reason")


def no_verdict_reason(error, decision):
    """Why a reviewer has no verdict — the transport, or the reply itself."""
    if error:
        return error
    if decision:
        return None
    return "the response carries no single well-formed VERDICT line"


def verdict_of(text):
    found = re.findall(r"^VERDICT:\s*(ADOPT-WITH-AMENDMENTS|ADOPT|REJECT)\s*$",
                       text, re.M)
    if len(found) != 1:
        return None
    return found[0]


def keep_prompt(path, text):
    """Write the prompt, but never overwrite a different one already recorded.

    A round's prompt is evidence of what its reviewers were shown. Re-running the
    tool in a directory that already holds a different prompt means the round is
    not the round it was: refuse, rather than quietly replacing the record.
    """
    if path.exists() and path.read_text() != text:
        sys.exit(f"{path.relative_to(ROOT)} already records a different prompt. "
                 f"That round's reviewers saw the recorded one; freeze a new "
                 f"round rather than overwriting it.")
    path.write_text(text)


def review_one(freeze, family, model, context):
    """Ask one reviewer and write down everything about the asking."""
    asked = utc()
    print(f"[gate] {family}: {model} ...", file=sys.stderr)
    try:
        text, answered_by, finish = ask(model, context["prompt"],
                                        context["timeout"], context["max_tokens"])
        error = None
    except (OSError, RuntimeError, ValueError, LookupError) as failure:
        text, answered_by, finish, error = "", model, None, str(failure)
    decision = verdict_of(text) if text else None
    record = {
        "family": family,
        "model_requested": model,
        "model_answered": answered_by,
        "requested_utc": asked,
        "answered_utc": utc(),
        "finish_reason": finish,
        "max_tokens": context["max_tokens"],
        "prompt_sha256": context["prompt_sha256"],
        "system_sha256": context["system_sha256"],
        "frozen_commit": context["head"],
        "response_sha256": (hashlib.sha256(text.encode()).hexdigest()
                            if text else None),
        "verdict": decision or "NO VERDICT",
        "no_verdict_reason": no_verdict_reason(error, decision),
    }
    header = "\n".join(f"{k}: {v}" for k, v in record.items() if v is not None)
    body = (text.strip() + "\n" if text
            else f"NO VERDICT — {record['no_verdict_reason']}\n")
    (ROOT / freeze / f"review-{family}.md").write_text(f"<!--\n{header}\n-->\n\n{body}")
    (ROOT / freeze / f"review-{family}.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"[gate] {family}: {record['verdict']}", file=sys.stderr)
    return record


def report(results):
    """Print the round, and say plainly when it is not a round."""
    print()
    for record in results:
        print(f"  {record['family']:<10} {record['model_answered']:<34} "
              f"{record['verdict']}")
    verdicts = [r["verdict"] for r in results]
    named = [v for v in verdicts if v != "NO VERDICT"]
    rejects = verdicts.count("REJECT")
    print(f"\nGATE: {len(named)}/{len(results)} reviewers returned a verdict"
          + (f"; {rejects} REJECT" if rejects else ""))
    if len(named) < len(REVIEWERS):
        print("A three-family gate needs three verdicts. Re-run the reviewers "
              "that returned NO VERDICT; do not average what is missing.")
        return 1
    return 1 if rejects else 0


def run(freeze, timeout, only, max_tokens):
    head, _ = check_freeze(freeze)
    prompt = build_prompt()
    context = {
        "prompt": prompt,
        "timeout": timeout,
        "max_tokens": max_tokens,
        "head": head,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "system_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
    }
    print(f"[gate] prompt {len(prompt)} bytes, "
          f"sha256 {context['prompt_sha256'][:16]}", file=sys.stderr)
    keep_prompt(ROOT / freeze / "prompt.txt", prompt)
    keep_prompt(ROOT / freeze / "prompt.system.txt", SYSTEM)
    results = [review_one(freeze, family, model, context)
               for family, model in REVIEWERS
               if not only or family in only]
    return report(results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freeze", help="directory holding FREEZE.md")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-tokens", type=int, default=40000,
                        help="reply budget; a reviewer that reasons at length "
                             "and is cut off returns NO VERDICT, which is a "
                             "fact about this number and not about the candidate")
    parser.add_argument("--only", action="append", default=[],
                        help="run only this family (repeatable)")
    args = parser.parse_args()
    return run(args.freeze.rstrip("/"), args.timeout, args.only, args.max_tokens)


if __name__ == "__main__":
    raise SystemExit(main())
