/- Executable runner for the eval differential bridge (proofs/eval_bridge_check.py).

   stdin protocol:
     line 1:            N                       -- object pool size
     next N lines:      <hex bytes>             -- pool[0..N-1] (store objects)
     next line:         M                       -- number of queries
     next M lines:      <termhash_hex> <atp> <k> <i1> .. <ik>
                        -- k visible objects for this query, indices into pool
   stdout: M lines "<result_hash_hex> <atp_spent>", in order. -/
import EvalMachine

set_option linter.all false

open EvalMachine

private def hexVal (c : Char) : Nat :=
  if '0' ≤ c ∧ c ≤ '9' then c.toNat - '0'.toNat
  else if 'a' ≤ c ∧ c ≤ 'f' then c.toNat - 'a'.toNat + 10
  else if 'A' ≤ c ∧ c ≤ 'F' then c.toNat - 'A'.toNat + 10
  else 0

private def decodeHex (s : String) : List UInt8 :=
  let cs := s.toList
  let rec go : List Char → List UInt8
    | a :: b :: rest => UInt8.ofNat (hexVal a * 16 + hexVal b) :: go rest
    | _ => []
  go cs

partial def main : IO Unit := do
  let stdin ← IO.getStdin
  let readLine : IO String := do return (← stdin.getLine).trim
  let n := (← readLine).toNat!
  let mut pool : Array (List UInt8) := #[]
  for _ in [0:n] do
    pool := pool.push (decodeHex (← readLine))
  let m := (← readLine).toNat!
  let mut out : String := ""
  for _ in [0:m] do
    let parts := (← readLine).splitOn " "
    let termHex := parts[0]!
    let atp := parts[1]!.toNat!
    let k := parts[2]!.toNat!
    let mut store : Store := []
    for j in [0:k] do
      let idx := parts[3 + j]!.toNat!
      store := pool[idx]! :: store
    let (res, spent) := evalHash (decodeHex termHex) atp store
    out := out ++ MachineBytes.hexOf (termHash res) ++ " " ++ toString spent ++ "\n"
  IO.print out
