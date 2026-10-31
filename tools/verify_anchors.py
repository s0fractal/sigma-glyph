#!/usr/bin/env python3
"""Verify detached Specification Anchors: Anchor = NodeHash(LITERAL, atom=SHA-256(doc)).

A file of the current section that was retired (history/RETIREMENT-2026-10-ECHO.md) is verified at the commit
it was retired from, as Git holds it there: the anchored bytes still exist and still hash to their anchor."""
import hashlib, os, subprocess, sys
sha = lambda b: hashlib.sha256(b).digest()
anchor_of = lambda data: hashlib.sha256(bytes([0x00, 0x01]) + sha(data)).hexdigest()
RETIRED_AT = "96414ab0b14f5430641c3da424f684c5eae821ad"   # the before revision of the 2026-10-31 retirement


def read(path, root="."):
    """(bytes, where): the working tree's file, else the retired file at RETIRED_AT."""
    if os.path.exists(os.path.join(root, path)):
        return open(os.path.join(root, path), 'rb').read(), "tree"
    r = subprocess.run(["git", "-C", root, "cat-file", "blob", f"{RETIRED_AT}:{path}"], capture_output=True)
    if r.returncode:
        sys.exit(f"ANCHOR MISSING: {path} is neither in the tree nor at {RETIRED_AT[:12]}")
    return r.stdout, f"retired, at {RETIRED_AT[:12]}"


def main():
    ok = True
    # verify only the topmost (current) section; everything below "== ...ancestors..." is history
    sections = open('spec/ANCHORS.txt').read().split("\n== ")
    current = sections[1] if len(sections) > 1 else ""
    for line in current.splitlines():
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            expected, path = parts
            data, where = read(path)
            got = anchor_of(data)
            status = "OK " if got == expected else "FAIL"
            ok &= (got == expected)
            print(status, path, got, "" if where == "tree" else f"({where})")
    print("anchors verified" if ok else "ANCHOR MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
