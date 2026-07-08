#!/usr/bin/env bash
# The complete validation matrix, one command (Codex v0.6.4 hardening audit P2:
# `go test ./...` / `cargo test` from the root give incomplete/misleading
# results; the real gates are custom commands). CI runs the same surfaces.
# Run from the repository root: tools/test-all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n=== %s ===\n' "$1"; }

say "Book I / II / III oracles"
python3 impl/sigma_glyph.py    | tee /dev/stderr | grep -q "ALL PASS"
python3 impl/sigma_wave.py     | tee /dev/stderr | grep -q "WAVE: ALL PASS"
python3 impl/sigma_federation.py | tee /dev/stderr | grep -q "FEDERATION: ALL PASS"

say "Conformance + properties"
python3 tests/spec_conformance/run_reference.py  | tee /dev/stderr | grep -q "ALL PASS"
python3 tests/spec_conformance/test_properties.py

say "Book I third implementation (Rust)"
( cd impl-rs && cargo build --release )
./impl-rs/target/release/book1 selftest    | tee /dev/stderr | grep -q "SELFTEST: ALL PASS"
./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json \
  | tee /dev/stderr | grep -q "RUST-CONFORMANCE: ALL PASS"

say "Federation + governance second implementation (Go) + differentials"
( cd impl-go && go build -o sigma-federation-go . )
./impl-go/sigma-federation-go replay tests/spec_conformance/federation_vectors.json \
  | tee /dev/stderr | grep -q "FEDERATION-GO: ALL PASS"
./impl-go/sigma-federation-go gov-replay tests/spec_conformance/governance_vectors.json \
  | tee /dev/stderr | grep -q "GOVERNANCE-GO: ALL PASS"
python3 tests/federation_differential.py   | tee /dev/stderr | grep -q "FEDERATION-DIFFERENTIAL: ALL AGREE"
python3 tests/governance_differential.py   | tee /dev/stderr | grep -q "GOVERNANCE-DIFFERENTIAL: ALL AGREE"

say "Anchors + governance"
python3 tools/verify_anchors.py            | tee /dev/stderr | grep -q "anchors verified"
python3 tools/anchor_governance.py selftest | tee /dev/stderr | grep -q "ANCHOR-GOVERNANCE: ALL PASS"
python3 tools/anchor_governance.py replay  | tee /dev/stderr | grep -q "GOVERNANCE-REPLAY: ALL PASS"

say "Adjudication warrants"
python3 tools/warrant_verify.py            | tee /dev/stderr | grep -q "errors 0"

# Lean proofs + bridges run only where `lean` is installed (heavy toolchain).
if command -v lean >/dev/null 2>&1; then
  say "Lean proofs + differential bridges"
  for b in bridge_check byte_bridge_check eval_bridge_check wave_bridge_check; do
    python3 "proofs/$b.py" | tee /dev/stderr | grep -qE "HOLD|ALL AGREE"
  done
else
  printf '\n(skipping Lean bridges: `lean` not on PATH — install elan to include them)\n'
fi

printf '\nTEST-ALL: ALL GREEN\n'
