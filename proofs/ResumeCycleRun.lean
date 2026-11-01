/- Executable runner for the resume differential bridge (proofs/resume_bridge_check.py):
   `SigmaResume.checkCycle` (ResumeCycle.lean), compiled, over a finite transition table.

   stdin, one case per line: `N`, then `N` table entries (`0` normal form, `1`
   blocked reference, `2 j c` fire to state `j` at cost `c ≥ 1`), then
   `start entry entry_spent cycle_actions cycle_cost max_atp`. States are
   `0…N-1`; any other index is a normal form.
   stdout, one line per case: `P` (CYCLE_PROVEN), `N` (NOT_ASSESSED), `R`
   (refused), or `E` (a malformed line). -/
import ResumeCycle

set_option linter.all false

open SigmaResume

/-- A table entry's cost is stored as `c - 1`, so every fired action costs at least 1 by construction. -/
def tableStep (t : Array (Act Nat)) (i : Nat) : Act Nat :=
  match t[i]? with
  | some (.fire j c) => .fire j (c + 1)
  | some .blocked => .blocked
  | _ => .nf

def tableMachine (t : Array (Act Nat)) : Machine where
  S := Nat
  step := tableStep t
  cost_pos := by
    intro s s' c h
    unfold tableStep at h
    split at h <;> first | (cases h; omega) | cases h

instance (t : Array (Act Nat)) : DecidableEq (tableMachine t).S := inferInstanceAs (DecidableEq Nat)

partial def parseTable (ts : List Nat) (k : Nat) (acc : Array (Act Nat)) : Option (Array (Act Nat) × List Nat) :=
  if k = 0 then some (acc, ts) else
  match ts with
  | 0 :: rest => parseTable rest (k - 1) (acc.push .nf)
  | 1 :: rest => parseTable rest (k - 1) (acc.push .blocked)
  | 2 :: j :: c :: rest => if c = 0 then none else parseTable rest (k - 1) (acc.push (.fire j (c - 1)))
  | _ => none

def answer (line : String) : String :=
  let ts := (line.splitOn " ").filter (· ≠ "") |>.map String.toNat?
  if ts.any (·.isNone) then "E" else
  match ts.filterMap id with
  | n :: rest =>
    match parseTable rest n #[] with
    | some (t, [start, entry, k, acts, cost, maxAtp]) =>
      match checkCycle (tableMachine t) maxAtp start entry k acts cost with
      | .proven => "P"
      | .notAssessed => "N"
      | .refused => "R"
    | _ => "E"
  | [] => "E"

partial def loop (stdin : IO.FS.Stream) (stdout : IO.FS.Stream) : IO Unit := do
  let line ← stdin.getLine
  if line.isEmpty then return
  stdout.putStrLn (answer ((line.replace "\n" "").replace "\r" ""))
  stdout.flush
  loop stdin stdout

def main : IO Unit := do
  loop (← IO.getStdin) (← IO.getStdout)
