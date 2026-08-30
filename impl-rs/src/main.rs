use std::collections::{BTreeMap, HashMap, HashSet};
use std::env;
use std::fs;
use std::process::ExitCode;

type Hash = [u8; 32];

const LITERAL: u8 = 0x00;
const REF: u8 = 0x01;
const APPLY: u8 = 0x02;
const DISSONANCE: u8 = 0xff;
const F_ATOM: u8 = 0x01;
const F_LEFT: u8 = 0x02;
const F_RIGHT: u8 = 0x04;

const I_EXPECTED: &str = "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162";
const K_EXPECTED: &str = "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c";
const S_EXPECTED: &str = "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6";
const FALSE_EXPECTED: &str = "65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098";
const INVALID_EXPECTED: &str = "af69b5176c7ac3855c2eac3d1f6159c74d5328e92aac0a33cdba68bbaeba4507";

// ---------------------------------------------------------------------------
// Resource fences (Book I §3.6)
// ---------------------------------------------------------------------------
// §3.6: breaching a local resource limit is an IMPLEMENTATION FAULT — a refusal
// to execute — and MUST NOT be serialized as a DISSONANCE. The three canonical
// outcomes are the only canonical outcomes. Until v0.6.7 this binary had no
// fences at all: `step`, `term_hash`, `term_size` and the JSON parser were all
// unbounded recursions, so a deep left spine or a nested-array vectors file
// aborted the process ("thread 'main' has overflowed its stack / fatal runtime
// error: stack overflow", SIGABRT), where impl/sigma_glyph.py raises
// ResourceFault. An abort is spec-legal in the narrow sense that it is not a
// canonical failure, but it is not a refusal either — the caller learns
// nothing, and README.md calls this binary safe by construction.
//
// MAX_TERM_DEPTH mirrors impl/sigma_glyph.py DEFAULT_LIMITS["max_node_depth"]
// so the two implementations fault on the same shapes; the ATP budget already
// bounds memory semantically (§3.4), so this is the second fence, not the first.
const MAX_TERM_DEPTH: usize = 4096;
// The conformance format nests four levels deep (root / vectors / vector /
// expected). 64 leaves room for growth and still cannot reach the stack.
const MAX_JSON_DEPTH: usize = 64;
// A depth fence is only a fence if the stack can hold that many frames. It
// cannot on a default 2 MiB spawned-thread stack — the first `cargo test` run
// against MAX_TERM_DEPTH proved it, aborting with SIGABRT *inside the refusal
// path*. So the work runs on a thread whose stack is sized for the fence
// instead of relying on whatever the platform hands us. Virtual reservation:
// untouched pages cost nothing.
const WORK_STACK_BYTES: usize = 64 * 1024 * 1024;

/// Run `work` on a stack big enough for MAX_TERM_DEPTH frames.
fn on_fenced_stack<T: Send + 'static>(work: impl FnOnce() -> T + Send + 'static) -> Option<T> {
    std::thread::Builder::new()
        .stack_size(WORK_STACK_BYTES)
        .spawn(work)
        .ok()?
        .join()
        .ok()
}

/// A local, NON-canonical implementation fault (Book I §3.6). Never a DISSONANCE.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ResourceFault(pub &'static str);

impl std::fmt::Display for ResourceFault {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "local resource fault: {} (Book I §3.6 — an implementation fault, \
             NOT a canonical Book I failure)",
            self.0
        )
    }
}

fn sha256(input: &[u8]) -> Hash {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut state: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let bit_len = (input.len() as u128 * 8) as u64;
    let mut padded = input.to_vec();
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());

    for block in padded.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (i, word) in block.chunks_exact(4).enumerate() {
            w[i] = u32::from_be_bytes(word.try_into().unwrap());
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = state;
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        for (slot, value) in state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *slot = slot.wrapping_add(value);
        }
    }
    let mut out = [0u8; 32];
    for (chunk, word) in out.chunks_exact_mut(4).zip(state) {
        chunk.copy_from_slice(&word.to_be_bytes());
    }
    out
}

fn encode_hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 15) as usize] as char);
    }
    out
}

fn decode_hex(text: &str) -> Result<Vec<u8>, String> {
    if !text.len().is_multiple_of(2) {
        return Err("hex string has odd length".into());
    }
    fn nibble(byte: u8) -> Option<u8> {
        match byte {
            b'0'..=b'9' => Some(byte - b'0'),
            b'a'..=b'f' => Some(byte - b'a' + 10),
            b'A'..=b'F' => Some(byte - b'A' + 10),
            _ => None,
        }
    }
    text.as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let hi = nibble(pair[0]).ok_or_else(|| "invalid hex digit".to_string())?;
            let lo = nibble(pair[1]).ok_or_else(|| "invalid hex digit".to_string())?;
            Ok((hi << 4) | lo)
        })
        .collect()
}

fn hash_from_hex(text: &str) -> Result<Hash, String> {
    decode_hex(text)?
        .try_into()
        .map_err(|_| "hash must contain exactly 32 bytes".into())
}

fn serialize(op: u8, atom: Option<&Hash>, left: Option<&Hash>, right: Option<&Hash>) -> Vec<u8> {
    let flags =
        atom.map_or(0, |_| F_ATOM) | left.map_or(0, |_| F_LEFT) | right.map_or(0, |_| F_RIGHT);
    let mut out = vec![op, flags];
    for field in [atom, left, right].into_iter().flatten() {
        out.extend_from_slice(field);
    }
    out
}

#[derive(Clone, Debug)]
enum Node {
    Literal(Hash),
    Ref(Hash),
    Apply(Hash, Hash),
    Dissonance(Hash),
}

fn deserialize(bytes: &[u8]) -> Option<Node> {
    if bytes.len() < 2 {
        return None;
    }
    let op = bytes[0];
    let flags = bytes[1];
    if flags & !0x07 != 0 {
        return None;
    }
    let required = match op {
        LITERAL | REF | DISSONANCE => F_ATOM,
        APPLY => F_LEFT | F_RIGHT,
        _ => return None,
    };
    if flags != required {
        return None;
    }
    let expected = 2 + 32 * (flags & 0x07).count_ones() as usize;
    if bytes.len() != expected {
        return None;
    }
    let read_hash = |offset: usize| -> Hash { bytes[offset..offset + 32].try_into().unwrap() };
    Some(match op {
        LITERAL => Node::Literal(read_hash(2)),
        REF => Node::Ref(read_hash(2)),
        APPLY => Node::Apply(read_hash(2), read_hash(34)),
        DISSONANCE => Node::Dissonance(read_hash(2)),
        _ => unreachable!(),
    })
}

fn reason_hash(reason: &str) -> Hash {
    sha256(reason.as_bytes())
}

fn genesis() -> (Hash, Hash, Hash, Hash) {
    let i = sha256(&serialize(LITERAL, Some(&sha256(b"I")), None, None));
    let k = sha256(&serialize(LITERAL, Some(&sha256(b"K")), None, None));
    let s = sha256(&serialize(LITERAL, Some(&sha256(b"S")), None, None));
    let false_hash = sha256(&serialize(APPLY, None, Some(&k), Some(&i)));
    (i, k, s, false_hash)
}

#[derive(Clone, Debug)]
enum Term {
    Thunk(Hash),
    Literal(Hash),
    Ref(Hash),
    Dissonance(Hash),
    Apply(Box<Term>, Box<Term>),
}

impl Drop for Term {
    /// The derived drop glue for `Apply(Box<Term>, Box<Term>)` is recursion the
    /// input controls, and it runs on the fault path — so fencing `step` alone
    /// only moved the stack overflow from evaluation to cleanup. Found by the
    /// `cargo test` added alongside this fence, which aborted with SIGABRT on a
    /// 4104-deep term the fences had correctly refused to evaluate.
    /// Dismantle iteratively instead.
    fn drop(&mut self) {
        const STUB: Term = Term::Thunk([0u8; 32]);
        let mut pending: Vec<Term> = Vec::new();
        let detach = |term: &mut Term, into: &mut Vec<Term>| {
            if let Term::Apply(left, right) = term {
                into.push(std::mem::replace(&mut **left, STUB));
                into.push(std::mem::replace(&mut **right, STUB));
            }
        };
        detach(self, &mut pending);
        while let Some(mut child) = pending.pop() {
            detach(&mut child, &mut pending);
            // `child` drops here with both of its children already replaced by
            // leaves, so this recursion is one frame deep, always.
        }
    }
}

fn term_hash(term: &Term) -> Result<Hash, ResourceFault> {
    term_hash_at(term, 0)
}

fn term_hash_at(term: &Term, depth: usize) -> Result<Hash, ResourceFault> {
    if depth > MAX_TERM_DEPTH {
        return Err(ResourceFault("term depth (hashing)"));
    }
    Ok(match term {
        Term::Thunk(hash) => *hash,
        Term::Literal(atom) => sha256(&serialize(LITERAL, Some(atom), None, None)),
        Term::Ref(target) => sha256(&serialize(REF, Some(target), None, None)),
        Term::Dissonance(reason) => sha256(&serialize(DISSONANCE, Some(reason), None, None)),
        Term::Apply(left, right) => sha256(&serialize(
            APPLY,
            None,
            Some(&term_hash_at(left, depth + 1)?),
            Some(&term_hash_at(right, depth + 1)?),
        )),
    })
}

fn term_size(term: &Term) -> Result<u64, ResourceFault> {
    term_size_at(term, 0)
}

fn term_size_at(term: &Term, depth: usize) -> Result<u64, ResourceFault> {
    if depth > MAX_TERM_DEPTH {
        return Err(ResourceFault("term depth (sizing)"));
    }
    Ok(match term {
        Term::Apply(left, right) => 1u64
            .saturating_add(term_size_at(left, depth + 1)?)
            .saturating_add(term_size_at(right, depth + 1)?),
        Term::Ref(_) => 2,
        _ => 1,
    })
}

fn glyph_eq(term: &Term, glyph: &Hash) -> bool {
    match term {
        Term::Thunk(hash) => hash == glyph,
        Term::Literal(atom) => sha256(&serialize(LITERAL, Some(atom), None, None)) == *glyph,
        _ => false,
    }
}

#[derive(Debug)]
enum StepError {
    Exhausted,
    Unresolved,
    /// Book I §3.6: local limit breached. Deliberately NOT one of the two
    /// canonical failures above — `evaluate` propagates it to the caller
    /// instead of minting a DISSONANCE for it.
    Fault(ResourceFault),
}

impl From<ResourceFault> for StepError {
    fn from(fault: ResourceFault) -> Self {
        StepError::Fault(fault)
    }
}

fn force(
    hash: &Hash,
    store: &HashMap<Hash, Vec<u8>>,
    genesis_hashes: &(Hash, Hash, Hash),
) -> Result<Term, StepError> {
    let bytes = if hash == &genesis_hashes.0 {
        serialize(LITERAL, Some(&sha256(b"I")), None, None)
    } else if hash == &genesis_hashes.1 {
        serialize(LITERAL, Some(&sha256(b"K")), None, None)
    } else if hash == &genesis_hashes.2 {
        serialize(LITERAL, Some(&sha256(b"S")), None, None)
    } else {
        store.get(hash).cloned().ok_or(StepError::Unresolved)?
    };
    Ok(match deserialize(&bytes) {
        Some(Node::Literal(atom)) => Term::Literal(atom),
        Some(Node::Ref(target)) => Term::Ref(target),
        Some(Node::Apply(left, right)) => {
            Term::Apply(Box::new(Term::Thunk(left)), Box::new(Term::Thunk(right)))
        }
        Some(Node::Dissonance(reason)) => Term::Dissonance(reason),
        None => Term::Dissonance(reason_hash("Invalid Object")),
    })
}

fn step(
    term: &Term,
    remaining: u64,
    store: &HashMap<Hash, Vec<u8>>,
    glyphs: &(Hash, Hash, Hash),
    depth: usize,
) -> Result<Option<(Term, u64)>, StepError> {
    // The left-spine descent below is the recursion that a hostile term drives.
    // Fence it before the stack does (§3.6): a fault, never an abort.
    if depth > MAX_TERM_DEPTH {
        return Err(StepError::Fault(ResourceFault("term depth (stepping)")));
    }
    match term {
        Term::Thunk(hash) => {
            if hash == &glyphs.0 || hash == &glyphs.1 || hash == &glyphs.2 {
                return Ok(None);
            }
            if remaining < 1 {
                return Err(StepError::Exhausted);
            }
            let materialized = force(hash, store, glyphs)?;
            let cost = term_size(&materialized)?;
            if cost > remaining {
                return Err(StepError::Exhausted);
            }
            Ok(Some((materialized, cost)))
        }
        Term::Ref(target) => {
            if remaining < 1 {
                Err(StepError::Exhausted)
            } else {
                Ok(Some((Term::Thunk(*target), 1)))
            }
        }
        Term::Literal(_) | Term::Dissonance(_) => Ok(None),
        Term::Apply(function, argument) => {
            if glyph_eq(function, &glyphs.0) {
                if remaining < 1 {
                    return Err(StepError::Exhausted);
                }
                return Ok(Some(((**argument).clone(), 1)));
            }
            if let Term::Apply(f1, f2) = function.as_ref() {
                if glyph_eq(f1, &glyphs.1) {
                    if remaining < 1 {
                        return Err(StepError::Exhausted);
                    }
                    return Ok(Some(((**f2).clone(), 1)));
                }
                if let Term::Apply(f11, f12) = f1.as_ref() {
                    if glyph_eq(f11, &glyphs.2) {
                        let cost = 1u64.saturating_add(term_size(argument)?);
                        if cost > remaining {
                            return Err(StepError::Exhausted);
                        }
                        let z = (**argument).clone();
                        let result = Term::Apply(
                            Box::new(Term::Apply(Box::new((**f12).clone()), Box::new(z.clone()))),
                            Box::new(Term::Apply(Box::new((**f2).clone()), Box::new(z))),
                        );
                        return Ok(Some((result, cost)));
                    }
                }
            }
            if let Some((new_function, cost)) = step(function, remaining, store, glyphs, depth + 1)?
            {
                return Ok(Some((
                    Term::Apply(Box::new(new_function), Box::new((**argument).clone())),
                    cost,
                )));
            }
            if let Some((new_argument, cost)) = step(argument, remaining, store, glyphs, depth + 1)?
            {
                return Ok(Some((
                    Term::Apply(Box::new((**function).clone()), Box::new(new_argument)),
                    cost,
                )));
            }
            Ok(None)
        }
    }
}

/// The three exits of §3.4. The result hash never identified the exit:
/// `DISSONANCE(ATP Exhausted)` is an ordinary term, so a run can settle on it
/// with `Exit::NormalForm`. Carrying the exit separately is the point of the
/// Receipt, and this engine has always known it at each return site — it used to
/// throw it away, which left the conformance runner comparing two observables
/// where the specification names four.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Exit {
    NormalForm,
    AtpExhausted,
    UnresolvedReference,
}

impl Exit {
    fn as_str(self) -> &'static str {
        match self {
            Exit::NormalForm => "normal_form",
            Exit::AtpExhausted => "atp_exhausted",
            Exit::UnresolvedReference => "unresolved_reference",
        }
    }
}

/// `Ok((result_hash, spent, exit))` is one of the three canonical outcomes of
/// §3.4. `Err(ResourceFault)` is §3.6: this implementation refused to run the
/// term. The two are different types on purpose — a fault cannot be mistaken
/// for, or silently widened into, a canonical DISSONANCE.
fn evaluate(
    term_hash_value: Hash,
    atp: u64,
    store: &HashMap<Hash, Vec<u8>>,
) -> Result<(Hash, u64, Exit), ResourceFault> {
    let (i, k, s, _) = genesis();
    let glyphs = (i, k, s);
    let mut term = Term::Thunk(term_hash_value);
    let mut spent = 0u64;
    loop {
        let remaining = atp - spent;
        match step(&term, remaining, store, &glyphs, 0) {
            Ok(Some((next, cost))) => {
                term = next;
                spent += cost;
            }
            Ok(None) => return Ok((term_hash(&term)?, spent, Exit::NormalForm)),
            Err(StepError::Exhausted) => {
                let dis = Term::Dissonance(reason_hash("ATP Exhausted"));
                return Ok((term_hash(&dis)?, spent, Exit::AtpExhausted));
            }
            Err(StepError::Unresolved) => {
                let dis = Term::Dissonance(reason_hash("Unresolved Reference"));
                return Ok((term_hash(&dis)?, spent, Exit::UnresolvedReference));
            }
            Err(StepError::Fault(fault)) => return Err(fault),
        }
    }
}

#[derive(Clone, Debug)]
enum Json {
    Null,
    Bool(bool),
    Number(u64),
    String(String),
    Array(Vec<Json>),
    Object(BTreeMap<String, Json>),
}

impl Json {
    fn object(&self) -> Result<&BTreeMap<String, Json>, String> {
        match self {
            Json::Object(value) => Ok(value),
            _ => Err("expected JSON object".into()),
        }
    }
    fn array(&self) -> Result<&[Json], String> {
        match self {
            Json::Array(value) => Ok(value),
            _ => Err("expected JSON array".into()),
        }
    }
    fn string(&self) -> Result<&str, String> {
        match self {
            Json::String(value) => Ok(value),
            _ => Err("expected JSON string".into()),
        }
    }
    fn number(&self) -> Result<u64, String> {
        match self {
            Json::Number(value) => Ok(*value),
            _ => Err("expected nonnegative JSON integer".into()),
        }
    }
    fn boolean(&self) -> Result<bool, String> {
        match self {
            Json::Bool(value) => Ok(*value),
            _ => Err("expected JSON boolean".into()),
        }
    }
}

struct JsonParser<'a> {
    bytes: &'a [u8],
    offset: usize,
    /// Nesting fence. `value -> object_value/array_value -> value` is mutual
    /// recursion driven entirely by the input file: `[[[[…` aborted the process
    /// with a stack overflow before this existed. A vectors file is untrusted
    /// input — it is exactly what a second implementation is handed.
    depth: usize,
}

impl<'a> JsonParser<'a> {
    fn parse(bytes: &'a [u8]) -> Result<Json, String> {
        let mut parser = Self {
            bytes,
            offset: 0,
            depth: 0,
        };
        let value = parser.value()?;
        parser.whitespace();
        if parser.offset != bytes.len() {
            return Err(parser.error("trailing data"));
        }
        Ok(value)
    }

    fn error(&self, message: &str) -> String {
        format!("JSON byte {}: {}", self.offset, message)
    }

    fn whitespace(&mut self) {
        while self
            .bytes
            .get(self.offset)
            .is_some_and(|b| matches!(b, b' ' | b'\n' | b'\r' | b'\t'))
        {
            self.offset += 1;
        }
    }

    fn take(&mut self, expected: u8) -> Result<(), String> {
        if self.bytes.get(self.offset) == Some(&expected) {
            self.offset += 1;
            Ok(())
        } else {
            Err(self.error(&format!("expected '{}'", expected as char)))
        }
    }

    fn literal(&mut self, text: &[u8], value: Json) -> Result<Json, String> {
        if self.bytes.get(self.offset..self.offset + text.len()) == Some(text) {
            self.offset += text.len();
            Ok(value)
        } else {
            Err(self.error("invalid literal"))
        }
    }

    fn value(&mut self) -> Result<Json, String> {
        self.whitespace();
        match self.bytes.get(self.offset).copied() {
            Some(b'{') => self.nested(Self::object_value),
            Some(b'[') => self.nested(Self::array_value),
            Some(b'"') => self.string_value().map(Json::String),
            Some(b't') => self.literal(b"true", Json::Bool(true)),
            Some(b'f') => self.literal(b"false", Json::Bool(false)),
            Some(b'n') => self.literal(b"null", Json::Null),
            Some(b'0'..=b'9') => self.number_value(),
            _ => Err(self.error("expected a JSON value")),
        }
    }

    /// Run one container parser one level deeper, refusing past MAX_JSON_DEPTH.
    fn nested(
        &mut self,
        parse_container: fn(&mut Self) -> Result<Json, String>,
    ) -> Result<Json, String> {
        if self.depth >= MAX_JSON_DEPTH {
            return Err(self.error("JSON nesting deeper than MAX_JSON_DEPTH — refused \
                                   (local resource fault, not a Book I outcome)"));
        }
        self.depth += 1;
        let value = parse_container(self);
        self.depth -= 1;
        value
    }

    fn object_value(&mut self) -> Result<Json, String> {
        self.take(b'{')?;
        let mut values = BTreeMap::new();
        self.whitespace();
        if self.bytes.get(self.offset) == Some(&b'}') {
            self.offset += 1;
            return Ok(Json::Object(values));
        }
        loop {
            self.whitespace();
            let key = self.string_value()?;
            self.whitespace();
            self.take(b':')?;
            let value = self.value()?;
            if values.insert(key, value).is_some() {
                return Err(self.error("duplicate object key"));
            }
            self.whitespace();
            match self.bytes.get(self.offset) {
                Some(b',') => self.offset += 1,
                Some(b'}') => {
                    self.offset += 1;
                    return Ok(Json::Object(values));
                }
                _ => return Err(self.error("expected ',' or '}'")),
            }
        }
    }

    fn array_value(&mut self) -> Result<Json, String> {
        self.take(b'[')?;
        let mut values = Vec::new();
        self.whitespace();
        if self.bytes.get(self.offset) == Some(&b']') {
            self.offset += 1;
            return Ok(Json::Array(values));
        }
        loop {
            values.push(self.value()?);
            self.whitespace();
            match self.bytes.get(self.offset) {
                Some(b',') => self.offset += 1,
                Some(b']') => {
                    self.offset += 1;
                    return Ok(Json::Array(values));
                }
                _ => return Err(self.error("expected ',' or ']'")),
            }
        }
    }

    fn string_value(&mut self) -> Result<String, String> {
        self.take(b'"')?;
        let mut out = String::new();
        loop {
            let byte = *self
                .bytes
                .get(self.offset)
                .ok_or_else(|| self.error("unterminated string"))?;
            self.offset += 1;
            match byte {
                b'"' => return Ok(out),
                b'\\' => {
                    let escape = *self
                        .bytes
                        .get(self.offset)
                        .ok_or_else(|| self.error("unterminated escape"))?;
                    self.offset += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let code = self.unicode_escape()?;
                            let ch = char::from_u32(code as u32)
                                .ok_or_else(|| self.error("invalid Unicode escape"))?;
                            out.push(ch);
                        }
                        _ => return Err(self.error("invalid string escape")),
                    }
                }
                0x00..=0x1f => return Err(self.error("control byte in string")),
                0x20..=0x7f => out.push(byte as char),
                _ => {
                    self.offset -= 1;
                    let tail = std::str::from_utf8(&self.bytes[self.offset..])
                        .map_err(|_| self.error("invalid UTF-8"))?;
                    let ch = tail
                        .chars()
                        .next()
                        .ok_or_else(|| self.error("invalid UTF-8"))?;
                    out.push(ch);
                    self.offset += ch.len_utf8();
                }
            }
        }
    }

    fn unicode_escape(&mut self) -> Result<u16, String> {
        let digits = self
            .bytes
            .get(self.offset..self.offset + 4)
            .ok_or_else(|| self.error("short Unicode escape"))?;
        self.offset += 4;
        let text = std::str::from_utf8(digits).map_err(|_| self.error("invalid Unicode escape"))?;
        u16::from_str_radix(text, 16).map_err(|_| self.error("invalid Unicode escape"))
    }

    fn number_value(&mut self) -> Result<Json, String> {
        let start = self.offset;
        while self
            .bytes
            .get(self.offset)
            .is_some_and(|b| b.is_ascii_digit())
        {
            self.offset += 1;
        }
        if self.offset - start > 1 && self.bytes[start] == b'0' {
            return Err(self.error("leading zero in number"));
        }
        let text = std::str::from_utf8(&self.bytes[start..self.offset]).unwrap();
        let value = text
            .parse::<u64>()
            .map_err(|_| self.error("integer out of range"))?;
        Ok(Json::Number(value))
    }
}

fn field<'a>(object: &'a BTreeMap<String, Json>, name: &str) -> Result<&'a Json, String> {
    object
        .get(name)
        .ok_or_else(|| format!("missing field '{name}'"))
}

fn run_selftest() -> bool {
    let (i, k, s, false_hash) = genesis();
    let invalid = sha256(&serialize(
        DISSONANCE,
        Some(&reason_hash("Invalid Object")),
        None,
        None,
    ));
    let cases = [
        ("H(I)", i, I_EXPECTED),
        ("H(K)", k, K_EXPECTED),
        ("H(S)", s, S_EXPECTED),
        ("FALSE", false_hash, FALSE_EXPECTED),
        ("Canonical Invalid Object", invalid, INVALID_EXPECTED),
    ];
    let mut passed = true;
    for (name, actual, expected) in cases {
        let actual = encode_hex(&actual);
        let ok = actual == expected;
        println!("{} {} = {}", if ok { "OK " } else { "FAIL" }, name, actual);
        passed &= ok;
    }
    if passed {
        println!("SELFTEST: ALL PASS");
    } else {
        println!("SELFTEST: FAIL");
    }
    passed
}

fn check_vector(
    vector: &BTreeMap<String, Json>,
    all_objects: &HashMap<Hash, Vec<u8>>,
    format_version: u64,
) -> Result<(), String> {
    let kind = field(vector, "kind")?.string()?;
    match kind {
        "object" => {
            let bytes = decode_hex(field(vector, "bytes")?.string()?)?;
            let expected = field(field(vector, "expected")?.object()?, "hash")?.string()?;
            if encode_hex(&sha256(&bytes)) == expected {
                Ok(())
            } else {
                Err("serialized object hash mismatch".into())
            }
        }
        "deserialize" => {
            let bytes = decode_hex(field(vector, "bytes")?.string()?)?;
            let expected_valid = field(field(vector, "expected")?.object()?, "valid")?.boolean()?;
            let actual_valid = deserialize(&bytes).is_some();
            if actual_valid != expected_valid {
                return Err(format!(
                    "deserialization validity mismatch: expected {expected_valid}, got {actual_valid}"
                ));
            }
            if !actual_valid {
                let invalid_hash = sha256(&serialize(
                    DISSONANCE,
                    Some(&reason_hash("Invalid Object")),
                    None,
                    None,
                ));
                if encode_hex(&invalid_hash) != INVALID_EXPECTED {
                    return Err("invalid bytes did not materialize canonical invalid object".into());
                }
            }
            Ok(())
        }
        "eval" => {
            let term = hash_from_hex(field(vector, "term")?.string()?)?;
            let atp = field(vector, "atp")?.number()?;
            let store = if let Some(subset) = vector.get("store_subset") {
                let mut selected = HashMap::new();
                for item in subset.array()? {
                    let key = hash_from_hex(item.string()?)?;
                    let bytes = all_objects.get(&key).ok_or_else(|| {
                        format!("store_subset key {} is absent", encode_hex(&key))
                    })?;
                    selected.insert(key, bytes.clone());
                }
                selected
            } else {
                all_objects.clone()
            };
            // A fault is reported as a fault. It is NOT a conformance pass, and
            // it is NOT dressed up as a canonical DISSONANCE (§3.6).
            let (actual_hash, actual_spent, actual_exit) =
                evaluate(term, atp, &store).map_err(|fault| fault.to_string())?;
            let expected = field(vector, "expected")?.object()?;
            let expected_hash = field(expected, "result_hash")?.string()?;
            let expected_spent = field(expected, "atp_spent")?.number()?;
            // The exit and the classification are separate claims, checked
            // separately. `invalid_object` is not a fourth exit: it names a
            // normal form whose result is the Canonical Invalid Object.
            if let Ok(expected_exit) = field(expected, "exit").and_then(Json::string) {
                if actual_exit.as_str() != expected_exit {
                    return Err(format!(
                        "expected exit {expected_exit}, got {}",
                        actual_exit.as_str()
                    ));
                }
            } else if format_version >= 3 {
                return Err("format v3 requires expected.exit".into());
            }
            if let Ok(expected_outcome) = field(expected, "outcome").and_then(Json::string) {
                let invalid = Term::Dissonance(reason_hash("Invalid Object"));
                let actual_outcome = if actual_exit == Exit::NormalForm
                    && actual_hash == term_hash(&invalid).map_err(|e| e.to_string())?
                {
                    "invalid_object"
                } else {
                    actual_exit.as_str()
                };
                if actual_outcome != expected_outcome {
                    return Err(format!(
                        "expected outcome {expected_outcome}, got {actual_outcome}"
                    ));
                }
            }
            if encode_hex(&actual_hash) != expected_hash || actual_spent != expected_spent {
                Err(format!(
                    "expected ({expected_hash}, {expected_spent}), got ({}, {actual_spent})",
                    encode_hex(&actual_hash)
                ))
            } else {
                Ok(())
            }
        }
        other => Err(format!("unknown vector kind '{other}'")),
    }
}

fn run_conformance(path: &str) -> Result<bool, String> {
    let input = fs::read(path).map_err(|error| format!("cannot read {path}: {error}"))?;
    let root = JsonParser::parse(&input)?;
    let root = root.object()?;
    // v3 adds `expected.exit`. v2 is still readable, and a v2 file is checked
    // on the observables it carries — but a v3 file MUST have its exit checked,
    // which is why the version is remembered rather than merely accepted.
    let format_version = field(root, "format_version")?.number()?;
    if format_version != 2 && format_version != 3 {
        return Err("unsupported conformance format version".into());
    }

    let mut objects = HashMap::new();
    for (key_text, value) in field(root, "objects")?.object()? {
        let key = hash_from_hex(key_text)?;
        let bytes = decode_hex(value.string()?)?;
        if sha256(&bytes) != key {
            return Err(format!("CAS key mismatch for {key_text}"));
        }
        objects.insert(key, bytes);
    }

    let vectors = field(root, "vectors")?.array()?;
    let mut passed = 0usize;
    let mut seen = HashSet::new();
    for vector in vectors {
        let vector = vector.object()?;
        let id = field(vector, "id")?.string()?;
        if !seen.insert(id.to_string()) {
            return Err(format!("duplicate vector id '{id}'"));
        }
        match check_vector(vector, &objects, format_version) {
            Ok(()) => {
                println!("OK  {id}");
                passed += 1;
            }
            Err(error) => println!("FAIL {id}: {error}"),
        }
    }
    println!();
    // The suite size used to be hardwired to 49 here, which made this binary
    // wrong for every other vectors file (tests/book1_fuzz.py had to parse the
    // per-vector lines to work around it) and made a real 49-vector regression
    // indistinguishable from a renamed file. The count assertion belongs to
    // whoever names the canonical file: tools/test-all.sh greps for the exact
    // "(49/49)" on tests/spec_conformance/vectors.json.
    let total = vectors.len();
    if total > 0 && passed == total {
        println!("RUST-CONFORMANCE: ALL PASS ({passed}/{total})");
        Ok(true)
    } else {
        println!("RUST-CONFORMANCE: FAIL ({passed}/{total})");
        Ok(false)
    }
}

#[cfg(test)]
mod tests {
    //! `cargo test` used to run zero tests here, so every property below was
    //! unguarded — including the resource fences, which did not exist, and the
    //! vector count, which was hardwired to 49.
    use super::*;

    /// Store a left spine `((… (I I) I) …) I` of `levels` APPLY nodes.
    fn spine(levels: usize) -> (Hash, HashMap<Hash, Vec<u8>>) {
        let (i, _, _, _) = genesis();
        let mut store = HashMap::new();
        let mut head = i;
        for _ in 0..levels {
            let bytes = serialize(APPLY, None, Some(&head), Some(&i));
            head = sha256(&bytes);
            store.insert(head, bytes);
        }
        (head, store)
    }

    #[test]
    fn genesis_constants_match_the_spec() {
        let (i, k, s, false_hash) = genesis();
        assert_eq!(encode_hex(&i), I_EXPECTED);
        assert_eq!(encode_hex(&k), K_EXPECTED);
        assert_eq!(encode_hex(&s), S_EXPECTED);
        assert_eq!(encode_hex(&false_hash), FALSE_EXPECTED);
        let invalid = sha256(&serialize(
            DISSONANCE,
            Some(&reason_hash("Invalid Object")),
            None,
            None,
        ));
        assert_eq!(encode_hex(&invalid), INVALID_EXPECTED);
    }

    /// Every test that walks near MAX_TERM_DEPTH must run on the same stack the
    /// binary gives itself; the default 2 MiB test-thread stack is smaller than
    /// the fence allows, and that mismatch is what SIGABRTed the first run.
    fn fenced<T: Send + 'static>(work: impl FnOnce() -> T + Send + 'static) -> T {
        on_fenced_stack(work).expect("worker thread")
    }

    #[test]
    fn shallow_spine_reduces_canonically() {
        // Well inside the fence: the fence must not fire on ordinary work.
        let (i, _, _, _) = genesis();
        let (root, store) = spine(64);
        let (hash, spent, _exit) = evaluate(root, 1_000_000, &store).expect("no fault expected");
        assert_eq!(hash, i, "((…(I I) I)…) I reduces to I");
        assert!(spent > 0);
    }

    #[test]
    fn deep_spine_faults_instead_of_overflowing_the_stack() {
        // Before the fence this aborted the process:
        //   "thread 'main' has overflowed its stack / fatal runtime error:
        //    stack overflow", SIGABRT.
        let outcome = fenced(|| {
            let (root, store) = spine(MAX_TERM_DEPTH * 4);
            evaluate(root, u32::MAX as u64, &store)
        });
        assert!(outcome.is_err(), "a hostile depth must be refused, not run");
    }

    #[test]
    fn a_fault_is_never_reported_as_a_canonical_outcome() {
        // Book I §3.6: a local limit breach MUST NOT be serialized as a
        // DISSONANCE. The type system carries that here — assert it anyway,
        // because the tempting "fix" is to return ATP Exhausted and move on.
        let outcome = fenced(|| {
            let (root, store) = spine(MAX_TERM_DEPTH * 4);
            evaluate(root, u32::MAX as u64, &store)
        });
        let atp_exhausted = sha256(&serialize(
            DISSONANCE,
            Some(&reason_hash("ATP Exhausted")),
            None,
            None,
        ));
        let unresolved = sha256(&serialize(
            DISSONANCE,
            Some(&reason_hash("Unresolved Reference")),
            None,
            None,
        ));
        match outcome {
            Err(fault) => {
                let text = fault.to_string();
                assert!(text.contains("§3.6"), "the fault must cite the rule: {text}");
                assert!(!text.contains(&encode_hex(&atp_exhausted)));
                assert!(!text.contains(&encode_hex(&unresolved)));
            }
            Ok((hash, spent, exit)) => panic!(
                "expected a §3.6 fault, got the canonical result {} / {spent} ATP \
                 with exit {}",
                encode_hex(&hash),
                exit.as_str()
            ),
        }
    }

    #[test]
    fn term_hash_and_term_size_are_fenced_too() {
        // `step` is not the only recursion a hostile term drives: R-S prices
        // itself with term_size(argument), and evaluate finishes with
        // term_hash(term). Both must refuse rather than recurse.
        let (sized, hashed) = fenced(|| {
            let mut term = Term::Thunk([0u8; 32]);
            for _ in 0..(MAX_TERM_DEPTH + 8) {
                term = Term::Apply(Box::new(term), Box::new(Term::Thunk([1u8; 32])));
            }
            (term_size(&term).is_err(), term_hash(&term).is_err())
        });
        assert!(sized, "term_size must refuse a term deeper than the fence");
        assert!(hashed, "term_hash must refuse a term deeper than the fence");
    }

    #[test]
    fn json_nesting_is_fenced() {
        // A vectors file is untrusted input. `[[[[…` aborted the process.
        let error = fenced(|| {
            let bomb: Vec<u8> = std::iter::repeat_n(b'[', 100_000)
                .chain(std::iter::repeat_n(b']', 100_000))
                .collect();
            JsonParser::parse(&bomb).map(|_| ())
        })
        .expect_err("must refuse");
        assert!(error.contains("nesting"), "{error}");
    }

    #[test]
    fn json_nesting_limit_is_exactly_max_json_depth() {
        let nest = |n: usize| -> Vec<u8> {
            std::iter::repeat_n(b'[', n)
                .chain(std::iter::repeat_n(b']', n))
                .collect()
        };
        assert!(JsonParser::parse(&nest(MAX_JSON_DEPTH)).is_ok());
        assert!(JsonParser::parse(&nest(MAX_JSON_DEPTH + 1)).is_err());
    }

    #[test]
    fn conformance_summary_follows_the_file_not_a_hardcoded_49() {
        // `if passed == 49 && vectors.len() == 49` meant this binary reported
        // FAIL on any other suite size — so tests/book1_fuzz.py had to count
        // per-vector "OK " lines to work around it, and a suite that lost a
        // vector was indistinguishable from one that never had 49.
        let doc = r#"{"format":"sigma-glyph-conformance","format_version":2,
            "objects":{},
            "vectors":[{"id":"T1","kind":"object","bytes":"0001",
                        "expected":{"hash":"b413f47d13ee2fe6c845b2ee141af81de858df4ec549a58b7970bb96645bc8d2"}}]}"#;
        let path = std::env::temp_dir().join(format!(
            "sigma-glyph-one-vector-{}.json",
            std::process::id()
        ));
        fs::write(&path, doc).unwrap();
        let ok = run_conformance(path.to_str().unwrap()).unwrap();
        let _ = fs::remove_file(&path);
        assert!(ok, "a one-vector suite that passes must report ALL PASS");
    }

    #[test]
    fn an_empty_suite_is_not_a_pass() {
        let doc = r#"{"format_version":2,"objects":{},"vectors":[]}"#;
        let path = std::env::temp_dir().join(format!(
            "sigma-glyph-empty-{}.json",
            std::process::id()
        ));
        fs::write(&path, doc).unwrap();
        let ok = run_conformance(path.to_str().unwrap()).unwrap();
        let _ = fs::remove_file(&path);
        assert!(!ok, "zero vectors is a vacuous green, not a pass");
    }
}

fn usage(program: &str) {
    eprintln!("usage: {program} selftest | conformance <vectors.json>");
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    match on_fenced_stack(move || dispatch(args)) {
        Some(true) => ExitCode::SUCCESS,
        Some(false) => ExitCode::FAILURE,
        None => {
            eprintln!("could not start the worker thread");
            ExitCode::FAILURE
        }
    }
}

fn dispatch(args: Vec<String>) -> bool {
    match args.as_slice() {
        [_, command] if command == "selftest" => run_selftest(),
        [_, command, path] if command == "conformance" => match run_conformance(path) {
            Ok(ok) => ok,
            Err(error) => {
                eprintln!("conformance error: {error}");
                false
            }
        },
        _ => {
            usage(args.first().map_or("book1", String::as_str));
            false
        }
    }
}
