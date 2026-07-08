/- Pure SHA-256 (FIPS 180-4) in core Lean 4. Total: padding is computed
   arithmetically up front, and the block loop is fuel-by-construction
   (`for i in [0:nBlocks]` over `Std.Range`, which is total in core).
   Correctness is established differentially: the genesis pins in
   MachineBytes.lean and the byte bridge recompute known digests. -/

namespace Sha256

/-- FIPS 180-4 §4.2.2 round constants. -/
def K : Array UInt32 := #[
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]

/-- FIPS 180-4 §5.3.3 initial hash value. -/
def H0 : Array UInt32 := #[
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

@[inline] def rotr (x : UInt32) (n : UInt32) : UInt32 :=
  (x >>> n) ||| (x <<< (32 - n))

@[inline] def bsig0 (x : UInt32) : UInt32 := rotr x 2 ^^^ rotr x 13 ^^^ rotr x 22
@[inline] def bsig1 (x : UInt32) : UInt32 := rotr x 6 ^^^ rotr x 11 ^^^ rotr x 25
@[inline] def ssig0 (x : UInt32) : UInt32 := rotr x 7 ^^^ rotr x 18 ^^^ (x >>> 3)
@[inline] def ssig1 (x : UInt32) : UInt32 := rotr x 17 ^^^ rotr x 19 ^^^ (x >>> 10)

/-- §5.1.1 padding: append 0x80, zero bytes to 56 mod 64, then the 64-bit
    big-endian bit length. The zero count is computed arithmetically so the
    definition is total by construction. -/
def pad (msg : List UInt8) : Array UInt8 :=
  let len := msg.length
  let zeros := (119 - len % 64) % 64
  let bitLen := len * 8
  let lenBytes : List UInt8 :=
    (List.range 8).map (fun i => UInt8.ofNat ((bitLen >>> ((7 - i) * 8)) % 256))
  msg.toArray ++ #[(0x80 : UInt8)] ++
    (List.replicate zeros (0 : UInt8)).toArray ++ lenBytes.toArray

/-- Big-endian 32-bit word at byte offset `i` (out-of-range reads 0;
    never exercised on padded input). -/
@[inline] def word (a : Array UInt8) (i : Nat) : UInt32 :=
  ((a.getD i 0).toUInt32 <<< 24) |||
  ((a.getD (i + 1) 0).toUInt32 <<< 16) |||
  ((a.getD (i + 2) 0).toUInt32 <<< 8) |||
  (a.getD (i + 3) 0).toUInt32

/-- §6.2.2 compression of one 512-bit block at byte offset `off`. -/
def compress (h : Array UInt32) (msg : Array UInt8) (off : Nat) :
    Array UInt32 := Id.run do
  let mut w : Array UInt32 := Array.mkEmpty 64
  for t in [0:16] do
    w := w.push (word msg (off + 4 * t))
  for t in [16:64] do
    w := w.push (ssig1 (w.getD (t - 2) 0) + w.getD (t - 7) 0 +
                 ssig0 (w.getD (t - 15) 0) + w.getD (t - 16) 0)
  let mut a := h.getD 0 0
  let mut b := h.getD 1 0
  let mut c := h.getD 2 0
  let mut d := h.getD 3 0
  let mut e := h.getD 4 0
  let mut f := h.getD 5 0
  let mut g := h.getD 6 0
  let mut hh := h.getD 7 0
  for t in [0:64] do
    let t1 := hh + bsig1 e + ((e &&& f) ^^^ ((~~~e) &&& g)) +
              K.getD t 0 + w.getD t 0
    let t2 := bsig0 a + ((a &&& b) ^^^ (a &&& c) ^^^ (b &&& c))
    hh := g
    g := f
    f := e
    e := d + t1
    d := c
    c := b
    b := a
    a := t1 + t2
  return #[h.getD 0 0 + a, h.getD 1 0 + b, h.getD 2 0 + c, h.getD 3 0 + d,
           h.getD 4 0 + e, h.getD 5 0 + f, h.getD 6 0 + g, h.getD 7 0 + hh]

/-- SHA-256 of a byte list; returns exactly 32 bytes. Total: the number of
    blocks is fixed up front from the padded length. -/
def sha256 (msg : List UInt8) : List UInt8 := Id.run do
  let p := pad msg
  let nBlocks := p.size / 64
  let mut h := H0
  for i in [0:nBlocks] do
    h := compress h p (64 * i)
  let mut out : Array UInt8 := Array.mkEmpty 32
  for i in [0:8] do
    let v := h.getD i 0
    out := out.push (v >>> 24).toUInt8
    out := out.push (v >>> 16).toUInt8
    out := out.push (v >>> 8).toUInt8
    out := out.push v.toUInt8
  return out.toList

end Sha256
