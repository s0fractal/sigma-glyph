#!/usr/bin/env python3
"""Verify detached Specification Anchors: Anchor = NodeHash(LITERAL, atom=SHA-256(doc)).

A file of the current section that was retired (history/RETIREMENT-2026-10-ECHO.md) is verified at the commit
it was retired from, as Git holds it there: the anchored bytes still exist and still hash to their anchor. Only
the paths in RETIRED are read there; any other missing file is a failure, never history (Codex on #72, F2).

    python3 tools/verify_anchors.py              # the current section
    python3 tools/verify_anchors.py --selftest   # a missing live file, a retired file, a changed live file"""
import hashlib, os, shutil, subprocess, sys, tempfile
sha = lambda b: hashlib.sha256(b).digest()
anchor_of = lambda data: hashlib.sha256(bytes([0x00, 0x01]) + sha(data)).hexdigest()
RETIRED_AT = "96414ab0b14f5430641c3da424f684c5eae821ad"   # the before revision of the 2026-10-31 retirement
RETIRED = frozenset((
    "spec/book-2-navigation.md", "spec/book-3-federation.md", "spec/LORE.md", "spec/GOV-anchors.md",
    "tests/spec_conformance/wave_vectors.json", "tests/spec_conformance/federation_vectors.json",
    "tests/spec_conformance/governance_vectors.json",
    "spec/schemas/book2-wave-conformance.schema.json", "spec/schemas/book3-federation-conformance.schema.json",
))


class Missing(Exception):
    pass


def read(path, root="."):
    """(bytes, where): the working tree's file; a RETIRED path absent from the tree, at RETIRED_AT."""
    if os.path.exists(os.path.join(root, path)):
        return open(os.path.join(root, path), 'rb').read(), "tree"
    if path not in RETIRED:
        raise Missing(f"ANCHOR MISSING: {path} is not in the tree and was not retired")
    r = subprocess.run(["git", "-C", root, "cat-file", "blob", f"{RETIRED_AT}:{path}"], capture_output=True)
    if r.returncode:
        raise Missing(f"ANCHOR MISSING: retired {path} is not at {RETIRED_AT[:12]} (a shallow checkout?)")
    return r.stdout, f"retired, at {RETIRED_AT[:12]}"


def verify(root="."):
    """(ok, lines) for the topmost (current) section; everything below it is history."""
    sections = open(os.path.join(root, 'spec/ANCHORS.txt')).read().split("\n== ")
    current = sections[1] if len(sections) > 1 else ""
    ok, lines = True, []
    for line in current.splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            expected, path = parts
            try:
                data, where = read(path, root)
            except Missing as e:
                ok = False
                lines.append(f"FAIL {e}")
                continue
            got = anchor_of(data)
            ok &= (got == expected)
            lines.append(f"{'OK ' if got == expected else 'FAIL'} {path} {got} {'' if where == 'tree' else f'({where})'}")
    return ok, lines


def selftest():
    """Three trees, each a full-history clone of this checkout: the verdict must follow the file, not the fallback."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results = []
    with tempfile.TemporaryDirectory() as td:
        clone = os.path.join(td, "c")
        subprocess.run(["git", "clone", "-q", "--no-local", root, clone], check=True)
        for rel in ("tools/verify_anchors.py", "spec/ANCHORS.txt"):        # the tree under test, not HEAD's
            shutil.copy2(os.path.join(root, rel), os.path.join(clone, rel))
        live = "spec/book-1-truth.md"
        base, _ = verify(clone)
        results.append(("the clone verifies, retired files read at the before revision", base))
        retired_read = read("spec/GOV-anchors.md", clone)[1].startswith("retired")
        results.append(("a retired file absent from the tree is read at the before revision", retired_read))
        kept = open(os.path.join(clone, live), "rb").read()
        os.remove(os.path.join(clone, live))
        gone, lines = verify(clone)
        results.append(("a missing live file fails, and is not read as history",
                        not gone and any("not in the tree and was not retired" in x for x in lines)))
        with open(os.path.join(clone, live), "wb") as f:
            f.write(kept + b"\n")
        changed, _ = verify(clone)
        results.append(("a changed live file fails", not changed))
    for name, good in results:
        print(("ok  " if good else "FAIL"), name)
    ok = all(good for _, good in results)
    print("VERIFY-ANCHORS-SELFTEST: ALL PASS" if ok else "VERIFY-ANCHORS-SELFTEST: FAILURES")
    return ok


def main():
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    ok, lines = verify()
    print("\n".join(lines))
    print("anchors verified" if ok else "ANCHOR MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
