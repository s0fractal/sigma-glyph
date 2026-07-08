/- Executable runner for the byte bridge (proofs/byte_bridge_check.py).

   Reads stdin lines; each line is a lowercase-hex-encoded buffer (an empty
   line is the empty buffer). For each line prints:
     "<sha256-of-buffer-hex> <ok|invalid> <reser>"
   where the middle field says whether MachineBytes.deserialize accepts the
   buffer, and <reser> is the hex of `serialize` of the parsed node when ok,
   or `-` when invalid. -/
import MachineBytes

open MachineBytes

/-- Value of a single lowercase hex digit. -/
def hexVal (c : Char) : Option Nat :=
  if '0' ≤ c && c ≤ '9' then some (c.toNat - '0'.toNat)
  else if 'a' ≤ c && c ≤ 'f' then some (c.toNat - 'a'.toNat + 10)
  else none

/-- Decode a lowercase-hex character list into bytes. -/
def decodeHexChars : List Char → Option (List UInt8)
  | [] => some []
  | [_] => none
  | c1 :: c2 :: rest => do
    let hi ← hexVal c1
    let lo ← hexVal c2
    let tail ← decodeHexChars rest
    pure (UInt8.ofNat (hi * 16 + lo) :: tail)

def processLine (chars : List Char) : String :=
  match decodeHexChars chars with
  | none => "- invalid -"
  | some buf =>
    let hash := hexOf (Sha256.sha256 buf)
    match deserialize buf with
    | some n => s!"{hash} ok {hexOf (serialize n)}"
    | none => s!"{hash} invalid -"

partial def loop (stdin : IO.FS.Stream) (stdout : IO.FS.Stream) : IO Unit := do
  let line ← stdin.getLine
  if line.isEmpty then
    return ()
  stdout.putStrLn (processLine
    (line.toList.filter (fun c => c ≠ '\n' && c ≠ '\r' && c ≠ ' ' && c ≠ '\t')))
  loop stdin stdout

def main : IO Unit := do
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  loop stdin stdout
