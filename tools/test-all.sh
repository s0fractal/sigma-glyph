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

say "Conformance vectors are fresh (regeneration is a no-op)"
# CI diffs regenerated vectors against the committed tree; locally we assert the
# stronger, commit-state-independent property: regenerating changes nothing in
# the working tree. Catches a stale generator or hand-edited vectors.
python3 -c "import cryptography" 2>/dev/null || {
  echo "ERR: 'cryptography' is required for the governance generator"; exit 1; }
_freshdir="$(mktemp -d)"
trap 'rm -rf "$_freshdir"' EXIT
_vecs=(vectors.json wave_vectors.json federation_vectors.json governance_vectors.json)
for f in "${_vecs[@]}"; do cp "tests/spec_conformance/$f" "$_freshdir/$f"; done
python3 tests/spec_conformance/generate.py >/dev/null
python3 impl/sigma_wave.py gen           >/dev/null
python3 impl/sigma_federation.py gen     >/dev/null
python3 tools/anchor_governance.py gen   >/dev/null
for f in "${_vecs[@]}"; do
  diff -q "$_freshdir/$f" "tests/spec_conformance/$f" >/dev/null \
    || { echo "STALE VECTORS: tests/spec_conformance/$f changed on regeneration"; exit 1; }
done

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

say "Book III live (two-jurisdictions demo, real stores)"
python3 examples/two-jurisdictions/demo.py | tee /dev/stderr | grep -q "DEMO: ALL ASSERTIONS HELD"

say "Anchors + governance"
python3 tools/verify_anchors.py            | tee /dev/stderr | grep -q "anchors verified"
python3 tools/anchor_governance.py selftest | tee /dev/stderr | grep -q "ANCHOR-GOVERNANCE: ALL PASS"
python3 tools/anchor_governance.py replay  | tee /dev/stderr | grep -q "GOVERNANCE-REPLAY: ALL PASS"

say "Adjudication warrants"
python3 tools/warrant_verify.py            | tee /dev/stderr | grep -q "errors 0"

# Network-gated surfaces that CI runs against pinned out-of-band sources (the
# anchor trust anchor and the Warrant CLI both live in the warrant repo, never
# in this tree). Run them when reachable; skip cleanly offline so the local
# matrix stays runnable without network.
WARRANT_REV=c038ce36b61445a5d82371975afd21d541e07752
TRUST_REV=a4270f863f6bcee837f7ef0363536b7e6cdf5ee6
RAW=https://raw.githubusercontent.com/s0fractal/warrant

say "Governance status --enforce (out-of-band trust anchor)"
if curl -sfL "$RAW/$TRUST_REV/trust/sigma-glyph-anchor-trust.json" \
        -o "$_freshdir/anchor-trust.json" 2>/dev/null; then
  python3 tools/anchor_governance.py status --enforce \
    --trust-config "$_freshdir/anchor-trust.json" | tee /dev/stderr | grep -q "AUTHORIZED"
else
  echo "(skipping: out-of-band anchor trust not reachable — run online for full parity)"
fi

say "Settlement-grade adjudication warrants (Warrant CLI, incl. ski@v1 re-runs)"
if curl -sfL "$RAW/$WARRANT_REV/impl/warrant.py" -o "$_freshdir/warrant.py" 2>/dev/null; then
  SIGMA_GLYPH=impl python3 "$_freshdir/warrant.py" verify
  SIGMA_GLYPH=impl python3 "$_freshdir/warrant.py" verify --settlement --trust-config trust-config.json
else
  echo "(skipping: Warrant CLI not reachable — run online for full parity)"
fi

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
