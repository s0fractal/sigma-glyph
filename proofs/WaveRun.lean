/- Differential-bridge runner: stdin lines "ph1 am1 en1 ph2 am2 en2",
   stdout lines "ph am en" — one interfere() per line, in order.
   Semantics come from WaveAlgebra.interfere (which mirrors
   impl/sigma_wave.py); this file adds only I/O plumbing. -/
import WaveAlgebra

open WaveAlgebra

def main : IO Unit := do
  let stdin ← IO.getStdin
  let input ← stdin.readToEnd
  for line in input.splitOn "\n" do
    let nums := ((line.splitOn " ").filter (fun s => !s.isEmpty)).map String.toInt!
    match nums with
    | [] => pure ()  -- blank line
    | [p1, a1, e1, p2, a2, e2] =>
      let w := interfere ⟨p1, a1, e1⟩ ⟨p2, a2, e2⟩
      IO.println s!"{w.ph} {w.am} {w.en}"
    | _ => throw (IO.userError s!"bad input line: {line}")
