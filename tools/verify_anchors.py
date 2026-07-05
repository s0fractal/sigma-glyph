#!/usr/bin/env python3
"""Verify detached Specification Anchors: Anchor = NodeHash(LITERAL, atom=SHA-256(doc))."""
import hashlib, sys
sha = lambda b: hashlib.sha256(b).digest()
anchor = lambda p: hashlib.sha256(bytes([0x00, 0x01]) + sha(open(p, 'rb').read())).hexdigest()
ok = True
for line in open('spec/ANCHORS.txt'):
    parts = line.split()
    if len(parts) == 2 and len(parts[0]) == 64:
        expected, path = parts
        got = anchor(path)
        status = "OK " if got == expected else "FAIL"
        ok &= (got == expected)
        print(status, path, got)
print("anchors verified" if ok else "ANCHOR MISMATCH")
sys.exit(0 if ok else 1)
