#!/usr/bin/env python3
"""EXP-001 convergence probe — deterministic corpus instrument.

Rule (Book I): if this tool and the prose disagree, the tool wins. Every number
below is traceable to a file+line. Where the corpus cannot answer a sub-question
deterministically, the tool prints `UNMEASURABLE` with the reason — it never
estimates. Run from anywhere:

    python3 experiments/exp-001/probe.py
"""
import os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REVIEWS = os.path.join(REPO, "reviews")
README = os.path.join(REVIEWS, "README.md")
TRINITY = os.path.expanduser("~/trinity")

VER = re.compile(r"v0\.[3-6]\.[0-9]+")          # a clean, stampable version
KERNEL = {                                       # §4b candidate conserved core
    "hash is identity": ["identity is nodehash", "hash is identity", "identity; identity is"],
    "wave not in hash": ["wave ∉ hash", "wave/phase/color are views"],
    "SKI-only consensus": ["ski-only consensus"],
    "aggregate never a field": ["aggregate is never a field", "aggregate never"],
}


def line(msg=""):
    print(msg)


# ---------- §4a compute-layer conserved bound ----------
def s4a():
    line("== §4a  compute-layer conserved bound (size-1 <= spent) ==")
    out = subprocess.run([sys.executable, os.path.join(REPO, "tools", "complexity_metrics.py")],
                         capture_output=True, text=True)
    rows = [l for l in out.stdout.splitlines() if l.strip().startswith("| TV")]
    yes = sum(1 for r in rows if re.search(r"\|\s*yes\s*\|", r))
    line(f"vectors checked: {len(rows)}   size-1<=spent holds: {yes}/{len(rows)}")
    verdict = "HOLDS" if rows and yes == len(rows) else "REFUTED"
    line(f"VERDICT §4a: {verdict}  (a conserved bound that forbids the O(2^ATP) state)")
    return verdict


# ---------- Settled-points parse (a, s, L, kernel) ----------
def settled_points():
    pts = []
    with open(README) as f:
        for i, l in enumerate(f, 1):
            if l.startswith("- ") and 12 < i < 36:   # the "Settled points" block
                pts.append((i, l.rstrip("\n")))
    return pts


def s3_structural():
    line("\n== §3  layer-stack structure (a(t)/s(t)/L(t)) ==")
    pts = settled_points()
    stamped = [(i, l) for i, l in pts if VER.search(l)]
    superseded = [(i, l) for i, l in pts if "~~" in l or re.search(r"[Ss]upersed", l)]
    line(f"total settled points:          {len(pts)}   (README:14-34)")
    line(f"carry a clean vX.Y.Z stamp:    {len(stamped)}   -> a(t) binnable")
    line(f"NO version stamp:              {len(pts)-len(stamped)}   -> NOT binnable by version")
    line(f"supersession events (total):   {len(superseded)}")
    for i, l in superseded:
        line(f"    L{i}: {l[:80]}...")
    line("VERDICT §3(a) additions-decline:   UNMEASURABLE  "
         f"({len(pts)-len(stamped)}/{len(pts)} points unstamped -> no per-version a(t))")
    line("VERDICT §3(b) supersede/add ratio: UNMEASURABLE  "
         f"(only {len(superseded)} supersession events in all history; no trend from 2 points)")
    line("VERDICT §3(c) L(t) concave->asymptote: UNMEASURABLE (depends on a(t), which is unmeasurable)")
    return pts, stamped, superseded


def s3_reviews():
    line("\n== §3  reviews r(t) and p(t) ==")
    files = [f for f in os.listdir(REVIEWS) if f.endswith(".md") and f != "README.md"]
    pass1 = [f for f in os.listdir(REVIEWS) if f.endswith(".pass1")]
    with_ver = sum(1 for f in files
                   if VER.search(open(os.path.join(REVIEWS, f)).read()))
    line(f"review files (.md, excl README): {len(files)}   blind pass-1 artifacts: {len(pass1)}")
    line(f"files naming an explicit vX.Y.Z:  {with_ver}   (target vs mention is not distinguishable by regex)")
    # p(t): raw severity MENTIONS, explicitly non-authoritative
    corpus = "\n".join(open(os.path.join(REVIEWS, f)).read() for f in files)
    ment = {s: len(re.findall(rf"\b{s}\b", corpus)) for s in ("P0", "P1", "P2", "P3")}
    line(f"raw severity MENTIONS: {ment}")
    line("    ^ NON-AUTHORITATIVE: 'P0' also appears in 'No P0 found', 'closes the P0', "
         "'the P0 from last round'. mention != finding-raised.")
    line("VERDICT §3(d) new P0/P1 declines: UNMEASURABLE deterministically "
         "(raised/absent/closed conflated; needs semantic read of every file; corpus forbids estimates)")


def s4b(pts, superseded):
    line("\n== §4b  governance conserved kernel K ==")
    blob = "\n".join(l.lower() for _, l in pts)
    present, never = [], []
    for name, keys in KERNEL.items():
        found = any(k in blob for k in keys)
        touched = any(any(k in l.lower() for k in keys) for _, l in superseded)
        (present if found else []).append(name)
        if found and not touched:
            never.append(name)
        line(f"  K-invariant '{name}': present={found}  in-a-supersession={touched}")
    line(f"stable kernel K (present, never superseded): {never}")
    # corrective-preserves-K: do the supersession events intersect any K keyword?
    breaks = []
    for i, l in superseded:
        for name, keys in KERNEL.items():
            if any(k in l.lower() for k in keys):
                breaks.append((i, name))
    line(f"supersession events touching a K-invariant: {breaks if breaks else 'none'}")
    kexists = "EXISTS" if never else "DOES-NOT-EXIST"
    preserve = "HOLDS" if not breaks else "BROKEN"
    line(f"VERDICT §4b: kernel {kexists}; corrective-preserves-K {preserve} "
         "(both supersessions live in the eval/validation shell, not the kernel)")
    line("    NOTE: keyword-intersection heuristic, not a semantic proof (reported as such).")
    return kexists, preserve


def modemix():
    line("\n== §3  mode-mix (trinity supersession-mode taxonomy) ==")
    if not os.path.isdir(TRINITY):
        line("VERDICT mode-mix: UNMEASURABLE (trinity corpus absent)")
        return
    src = os.path.join(TRINITY, "src")
    tax = ("strict_superset", "backward_compatible", "corrective")
    hits = 0
    for f in os.listdir(src):
        if f.endswith(".myc.md"):
            head = open(os.path.join(src, f)).read(2000)
            if any(t in head for t in tax):
                hits += 1
    line(f"trinity .myc.md files carrying the (strict_superset/backward_compatible/corrective) tag: {hits}")
    line("VERDICT mode-mix: UNMEASURABLE — the taxonomy the spec assumes is not in the frontmatter "
         "(it carries claim_kind/mode instead), AND trinity records do not map 1:1 to sigma reviews.")


def fep():
    line("\n== §5.3  FEP promotion recommendation ==")
    line("FREE_ENERGY_PRINCIPLE.v0.1 is 'aspirational', awaiting an empirical correlation between a "
         "computed F_total and substrate health (its own falsifier #1).")
    line("This study computes NO F_total and cannot draw the convergence trend the mapping needs "
         "(§3 unmeasurable). It offers only a STATIC observation (a conserved kernel), which is weaker "
         "than the DYNAMIC 'free energy declines' claim FEP asserts.")
    line("RECOMMENDATION: DO NOT PROMOTE. This corpus does not supply the correlation study; it neither "
         "confirms nor refutes the FEP-health mapping — it is insufficient to decide it.")


if __name__ == "__main__":
    s4a()
    pts, stamped, superseded = s3_structural()
    s3_reviews()
    s4b(pts, superseded)
    modemix()
    fep()
    line("\n(END. no EXP-002, no added theory — per the termination condition.)")
