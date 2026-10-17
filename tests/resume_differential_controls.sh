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
  # $4, when given, is the case that must turn red (on target), not just any.
  name=$1; from=$2; to=$3; target=${4:-}
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
  out=$(BOOK1="$tmp/$name/target/release/book1" python3 "$root/tests/resume_differential.py" 2>&1)
  if [ $? -eq 0 ]; then
    echo "FAIL  $name: the differential agreed with a broken engine"; status=1
  elif [ -n "$target" ] && ! printf '%s\n' "$out" | grep -q "^FAIL  $target "; then
    echo "FAIL  $name: disagreement reported, but not by $target (off target)"; status=1
  else
    echo "ok    $name: disagreement reported${target:+ by $target}"
  fi
}
control "force-charged-1" "let cost = term_size(&materialized)?;" "let cost = 1u64;"
control "blocked-as-paused" 'Err(StepError::Blocked(h)) => return Ok(done("BLOCKED_REFERENCE", term, Some(h))),' 'Err(StepError::Blocked(h)) => return Ok(done("PAUSED", term, Some(h))),'
# Rich profile (SKI + Y + M + W): each broken rule must be caught by R-N69.
control "rich-Y-wrong-shape" "let again = Term::Apply(function.clone(), argument.clone());" "let again = Term::Apply(argument.clone(), function.clone());" "R-N69"
control "rich-M-priced-1" "return Ok(Some((Term::Apply(argument.clone(), argument.clone()), cost)));" "return Ok(Some((Term::Apply(argument.clone(), argument.clone()), 1)));" "R-N69"
echo "DIFFERENTIAL CONTROLS: $([ $status = 0 ] && echo 'ALL BITE' || echo 'SOME DID NOT BITE')"
exit $status
