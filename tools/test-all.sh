#!/usr/bin/env bash
# The complete validation matrix, one command (Codex v0.6.4 hardening audit P2:
# `go test ./...` / `cargo test` from the root give incomplete/misleading
# results; the real gates are custom commands). CI runs the same surfaces.
# Run from the repository root: tools/test-all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

say() {
  local heading="$1"
  printf '\n=== %s ===\n' "$heading"
}

# A skipped surface is not a passed one. This script printed ALL GREEN and exited
# 0 after skipping the Lean bridges, or the two network-dependent parity checks,
# so `tools/test-all.sh && echo verified` reported success on a machine where the
# proofs were never checked. Demonstrated 2026-07-29 by forcing the lean branch to
# its else arm: "(skipping Lean bridges...)" followed by "ALL GREEN", exit 0.
#
# Skips are now counted and named in the verdict, and the exit status says so.
# ALLOW_SKIPS=1 is how an operator states the gap was accepted on purpose.
SKIPPED=""
skip() {
  local reason="$1"
  SKIPPED="$SKIPPED  - $reason"$'\n'
  printf '\n(skipping: %s)\n' "$reason"
}

say "Book I / II / III oracles"
python3 impl/sigma_glyph.py    | tee /dev/stderr | grep -q "ALL PASS"
python3 impl/sigma_wave.py     | tee /dev/stderr | grep -q "WAVE: ALL PASS"
python3 impl/sigma_federation.py | tee /dev/stderr | grep -q "FEDERATION: ALL PASS"

say "Version-state guard: candidates are not adopted releases"
python3 tests/version_check_selftest.py | tee /dev/stderr | grep -q "VERSION-CHECK-SELFTEST: ALL PASS"

say "Guard regression: the three self-tests put their verdict in the EXIT STATUS"
# impl/sigma_glyph.py called run_tests() and discarded the boolean, so it printed
# FAILURES PRESENT and exited 0 — every gate above catches that only by grepping
# stdout, and `python -m sigma_glyph && ./anything` reported success on a failing
# Book I oracle. This substitutes a failing entry function into each module and
# demands a non-zero exit (and a passing one, exit 0).
python3 tests/exit_status_guard.py         | tee /dev/stderr | grep -q "EXIT-STATUS-GUARD: ALL PASS"

say "Guard regression: exactly one construction of the Warrant signing message"
# Warrant SPEC v0.4 §5 domain-separates the signed message, and this repository
# had SEVEN hand-rolled copies of it in six Python files plus an eighth in
# impl-go -- found while migrating, and only because something unrelated went
# red. A signer and a verifier that disagree about those 47 bytes make this
# repository's own tools split on the same store, one reporting a valid
# signature and the other a forgery. The construction now lives in
# tools/warrant_sig.py; this fails if any other file open-codes it, in either
# the visible form (the literal) or the silent one (signing a bare digest).
python3 tests/one_signing_path.py          | tee /dev/stderr | grep -q "ONE-SIGNING-PATH: ALL PASS"

say "Security boundaries: content addresses and local check commands"
python3 tests/security_boundary_test.py   | tee /dev/stderr | grep -q "SECURITY-BOUNDARY: ALL PASS"
python3 tests/oracle_input_boundary_test.py | tee /dev/stderr | grep -q "ORACLE-INPUT-BOUNDARY: ALL PASS"

say "Release surface (what an installed copy promises)"
# The checkout half only. It drives the gate's classifier against the two real
# 0.6.6 install failures, then re-runs the three self-tests and the documented
# QUICKSTART snippet. Measuring the built WHEEL needs a build and a venv, so
# that half runs in .github/workflows/publish.yml, before the publish it guards.
#
# It also now runs EVERY declared verb against a non-checkout copy of impl/ —
# `gen` included. That verb was in the wheel for four releases and no gate had
# ever executed it from outside a checkout, where it ended in FileNotFoundError.
python3 tools/check_release_surface.py --selftest | tee /dev/stderr | grep -q "RELEASE-SURFACE-SELFTEST: ALL PASS"
python3 tools/check_release_surface.py            | tee /dev/stderr | grep -q "RELEASE SURFACE: ALL PASS"

say "Conformance + properties"
python3 tests/spec_conformance/run_reference.py  | tee /dev/stderr | grep -q "ALL PASS"
python3 tests/spec_conformance/test_properties.py

say "Guard regression: the Book I/II generators refuse a spec-contradicting oracle"
# Replaying oracle-written vectors against that oracle can only detect CHANGE.
# generate.py / sigma_wave.py gen now hold hand-declared, spec-cited values and
# fail closed on disagreement; this proves the refusal fires (7 mutations, all
# of which sailed through the pre-0.6.7 generators).
python3 tests/spec_expectation_guard.py    | tee /dev/stderr | grep -q "SPEC-EXPECTATION-GUARD: ALL PASS"

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
# MSRV: Cargo.toml declares one and, until v0.6.7, nothing ever checked it —
# "MSRV 1.87" was a comment. Compare it against the toolchain actually in use.
python3 - <<'PY'
import re, subprocess, sys
declared = re.search(r'^rust-version\s*=\s*"([\d.]+)"',
                     open("impl-rs/Cargo.toml").read(), re.M)
if not declared:
    sys.exit("ERR: impl-rs/Cargo.toml declares no rust-version (MSRV)")
have = re.search(r"rustc (\d+)\.(\d+)\.(\d+)",
                 subprocess.run(["rustc", "--version"], capture_output=True,
                                text=True).stdout)
if not have:
    sys.exit("ERR: cannot read `rustc --version`")
want = tuple(int(p) for p in declared.group(1).split("."))
got = tuple(int(p) for p in have.groups())
if got < want + (0,) * (3 - len(want)):
    sys.exit(f"ERR: rustc {'.'.join(map(str, got))} is below the declared MSRV "
             f"{declared.group(1)} — either the toolchain or Cargo.toml is wrong")
print(f"MSRV OK: declared {declared.group(1)}, toolchain {'.'.join(map(str, got))}")
PY
( cd impl-rs && cargo build --release )
# `cargo test` ran ZERO tests until v0.6.7 and CI never invoked it at all, so
# the resource fences, the JSON parser and the suite-size accounting had no
# unit coverage whatsoever.
( cd impl-rs && cargo test ) | tee /dev/stderr | grep -qE "test result: ok\. [1-9][0-9]* passed"
./impl-rs/target/release/book1 selftest    | tee /dev/stderr | grep -q "SELFTEST: ALL PASS"
# The count is pinned HERE, by whoever names the canonical file — it used to be
# hardwired inside the binary, which made every other vectors file report FAIL.
./impl-rs/target/release/book1 conformance tests/spec_conformance/vectors.json \
  | tee /dev/stderr | grep -q "RUST-CONFORMANCE: ALL PASS (49/49)"

say "Book I §3.6 resource fences (deep spine + hostile vectors file, Python vs Rust)"
# impl-rs had no fences: a deep left spine or a nested-array vectors file
# aborted the process with a stack overflow where the Python oracle raises
# ResourceFault. Every gate was blind to it — book1_fuzz.py capped depth at 5.
python3 tests/book1_resource_fence.py      | tee /dev/stderr | grep -q "BOOK1-FENCE: ALL PASS"

say "Three-way Book I differential fuzz (now including deep left spines)"
# Requires the Rust engine by name: "ALL AGREE" with only the Python oracle in
# the list would be the oracle agreeing with itself.
python3 tests/book1_fuzz.py --terms 60 --seed 20260730 \
  | tee /dev/stderr | grep -qE "BOOK1-FUZZ: ALL AGREE .*python-oracle\+rust"

say "Federation + governance second implementation (Go) + differentials"
( cd impl-go && go build -o sigma-federation-go . )
_gofed="$(./impl-go/sigma-federation-go replay tests/spec_conformance/federation_vectors.json | tee /dev/stderr)"
grep -q "FEDERATION-GO: ALL PASS" <<<"$_gofed"
# impl-go has no Book I evaluator; its FV-BOOK-I-UNREACHABLE "pass" was an echo
# of a hand-transcribed constant. It must declare itself vacuous and stay out of
# the tally — if this line ever disappears, a Go report can be read as Book I
# coverage again.
grep -q "VACUOUS FV-BOOK-I-UNREACHABLE" <<<"$_gofed"
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

say "Guard regression: WARRANT_PIN extraction fails hard on duplicate/malformed pins"
python3 tests/warrant_pin_guard_test.py    | tee /dev/stderr | grep -q "PIN-GUARD: ALL PASS"

# The papers in papers/ state numbers about this repository -- guard line counts,
# pin totals, Lean size, front distributions, vector totals, implementation line
# counts. They were correct on the day they moved in and nothing enforced that,
# which is the defect the second paper is about. The selftest runs first and on
# its own line: a claims checker whose checks cannot fail is the same defect one
# level up, and it is the cheaper of the two, so it fails faster.
python3 tools/paper_claims.py --selftest   | tee /dev/stderr | grep -q "PAPER-CLAIMS-SELFTEST: ALL PASS"
python3 tools/paper_claims.py              | tee /dev/stderr | grep -q "PAPER-CLAIMS: ALL PASS"

# Network-gated surfaces that CI runs against pinned out-of-band sources (the
# anchor trust anchor and the Warrant CLI both live in the warrant repo, never
# in this tree). Run them when reachable; skip cleanly offline so the local
# matrix stays runnable without network.
#
# ONE pin, read from ci.yml — the single visible pin its header mandates.
# This script used to carry two sibling revs of its own (they had drifted to
# commits different from CI's, so "the same surfaces" ran against a different
# warrant than CI tested). ci.yml's header is the authority on what the pin
# means and when it may refresh.
#
# Extraction lives in tools/read_warrant_pin.sh and fails HARD on a duplicate
# WARRANT_PIN: line (the old inline sed+grep passed a two-line value, curl
# then choked, and both parity checks skipped as "not reachable" — a
# forbidden ci.yml state misdiagnosed as a network problem).
WARRANT_PIN="$(tools/read_warrant_pin.sh)" \
  || { echo "ERR: WARRANT_PIN extraction failed — see message above"; exit 1; }
RAW=https://raw.githubusercontent.com/s0fractal/warrant

say "Governance status --enforce (out-of-band trust anchor)"
if curl --proto '=https' --tlsv1.2 -sfL \
        "$RAW/$WARRANT_PIN/trust/sigma-glyph-anchor-trust.json" \
        -o "$_freshdir/anchor-trust.json" 2>/dev/null; then
  # `grep -q AUTHORIZED` matched NOT AUTHORIZED too -- the gate passed on an
  # unauthorized set and failed only because pipefail happened to catch the
  # exit status. Remove pipefail and the substring silently greens a store with
  # no adoption warrant in it. Verified: deleting the v0.6.7 adoption warrant
  # makes the old form pass and this one fail. Anchored to the column so a
  # release line must START with AUTHORIZED, and a second pass refuses if the
  # word NOT appears anywhere -- one release unauthorized fails the whole gate.
  python3 tools/anchor_governance.py status --enforce \
    --trust-config "$_freshdir/anchor-trust.json" | tee /dev/stderr \
    | grep -qE '^[^ ]+ +AUTHORIZED' \
    && ! python3 tools/anchor_governance.py status --enforce \
         --trust-config "$_freshdir/anchor-trust.json" 2>/dev/null \
       | grep -q "NOT AUTHORIZED"
else
  skip "out-of-band anchor trust not reachable — run online for full parity"
fi

say "Settlement-grade adjudication warrants (Warrant CLI, incl. ski@v1 re-runs)"
if curl --proto '=https' --tlsv1.2 -sfL \
        "$RAW/$WARRANT_PIN/impl/warrant.py" \
        -o "$_freshdir/warrant.py" 2>/dev/null; then
  SIGMA_GLYPH=impl python3 "$_freshdir/warrant.py" verify
  SIGMA_GLYPH=impl python3 "$_freshdir/warrant.py" verify --settlement --trust-config trust-config.json
else
  skip "Warrant CLI not reachable — run online for full parity"
fi

# Lean proofs + bridges run only where `lean` is installed (heavy toolchain).
# c1_bridge_check is in this loop because CI's proofs.yml runs it: omitting it
# locally meant the "complete validation matrix" checked one fewer proof
# surface than CI (2026-07 review).
if command -v lean >/dev/null 2>&1; then
  say "Lean proofs + differential bridges"
  for b in bridge_check byte_bridge_check eval_bridge_check wave_bridge_check \
           c1_bridge_check; do
    python3 "proofs/$b.py" | tee /dev/stderr | grep -qE "HOLD|ALL AGREE"
  done
  say "Guard regression: bridge soundness guard rejects the review's bypass vectors"
  python3 tests/proof_guard_test.py | tee /dev/stderr | grep -q "PROOF-GUARD: ALL PASS"
else
  skip "Lean bridges: \`lean\` not on PATH — install elan to include them"
fi

if [[ -n "$SKIPPED" ]]; then
  printf '\nTEST-ALL: NOT COMPLETE — these surfaces were not checked:\n%s' "$SKIPPED"
  if [[ "${ALLOW_SKIPS:-0}" = "1" ]]; then
    printf 'ALLOW_SKIPS=1: the gap above was accepted deliberately.\n'
    exit 0
  fi
  printf 'A skipped surface is not a passed one. Set ALLOW_SKIPS=1 to accept it.\n'
  exit 2
fi
printf '\nTEST-ALL: ALL GREEN\n' 
