#!/bin/sh
# Negative controls for tests/resume_differential.py: each deliberately broken
# copy of the Rust engine MUST make the differential report a disagreement.
# A differential that agrees with a broken engine compares nothing.
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
status=0
control() {
  name=$1; from=$2; to=$3
  mkdir -p "$tmp/$name"
  cp -R "$root/impl-rs/Cargo.toml" "$root/impl-rs/src" "$tmp/$name/"
  [ -f "$root/impl-rs/Cargo.lock" ] && cp "$root/impl-rs/Cargo.lock" "$tmp/$name/"
  python3 - "$tmp/$name/src/main.rs" "$from" "$to" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
assert t.count(sys.argv[2]) == 1, "mutant site not unique"
p.write_text(t.replace(sys.argv[2], sys.argv[3]))
PY
  (cd "$tmp/$name" && cargo build --release -q 2>/dev/null) || { echo "FAIL  $name: did not build"; status=1; return; }
  if BOOK1="$tmp/$name/target/release/book1" python3 "$root/tests/resume_differential.py" >/dev/null 2>&1; then
    echo "FAIL  $name: the differential agreed with a broken engine"; status=1
  else
    echo "ok    $name: disagreement reported"
  fi
}
control "force-charged-1" "let cost = term_size(&materialized)?;" "let cost = 1u64;"
control "blocked-as-paused" 'Err(StepError::Blocked(h)) => return Ok(done("BLOCKED_REFERENCE", term, Some(h))),' 'Err(StepError::Blocked(h)) => return Ok(done("PAUSED", term, Some(h))),'
echo "DIFFERENTIAL CONTROLS: $([ $status = 0 ] && echo 'ALL BITE' || echo 'SOME DID NOT BITE')"
exit $status
