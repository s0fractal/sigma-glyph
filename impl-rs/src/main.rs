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

fn term_hash(term: &Term) -> Hash {
    match term {
        Term::Thunk(hash) => *hash,
        Term::Literal(atom) => sha256(&serialize(LITERAL, Some(atom), None, None)),
        Term::Ref(target) => sha256(&serialize(REF, Some(target), None, None)),
        Term::Dissonance(reason) => sha256(&serialize(DISSONANCE, Some(reason), None, None)),
        Term::Apply(left, right) => sha256(&serialize(
            APPLY,
            None,
            Some(&term_hash(left)),
            Some(&term_hash(right)),
        )),
    }
}

fn term_size(term: &Term) -> u64 {
    match term {
        Term::Apply(left, right) => 1u64
            .saturating_add(term_size(left))
            .saturating_add(term_size(right)),
        Term::Ref(_) => 2,
        _ => 1,
    }
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
) -> Result<Option<(Term, u64)>, StepError> {
    match term {
        Term::Thunk(hash) => {
            if hash == &glyphs.0 || hash == &glyphs.1 || hash == &glyphs.2 {
                return Ok(None);
            }
            if remaining < 1 {
                return Err(StepError::Exhausted);
            }
            let materialized = force(hash, store, glyphs)?;
            let cost = term_size(&materialized);
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
                        let cost = 1u64.saturating_add(term_size(argument));
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
            if let Some((new_function, cost)) = step(function, remaining, store, glyphs)? {
                return Ok(Some((
                    Term::Apply(Box::new(new_function), Box::new((**argument).clone())),
                    cost,
                )));
            }
            if let Some((new_argument, cost)) = step(argument, remaining, store, glyphs)? {
                return Ok(Some((
                    Term::Apply(Box::new((**function).clone()), Box::new(new_argument)),
                    cost,
                )));
            }
            Ok(None)
        }
    }
}

fn evaluate(term_hash_value: Hash, atp: u64, store: &HashMap<Hash, Vec<u8>>) -> (Hash, u64) {
    let (i, k, s, _) = genesis();
    let glyphs = (i, k, s);
    let mut term = Term::Thunk(term_hash_value);
    let mut spent = 0u64;
    loop {
        let remaining = atp - spent;
        match step(&term, remaining, store, &glyphs) {
            Ok(Some((next, cost))) => {
                term = next;
                spent += cost;
            }
            Ok(None) => return (term_hash(&term), spent),
            Err(StepError::Exhausted) => {
                let dis = Term::Dissonance(reason_hash("ATP Exhausted"));
                return (term_hash(&dis), spent);
            }
            Err(StepError::Unresolved) => {
                let dis = Term::Dissonance(reason_hash("Unresolved Reference"));
                return (term_hash(&dis), spent);
            }
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
}

impl<'a> JsonParser<'a> {
    fn parse(bytes: &'a [u8]) -> Result<Json, String> {
        let mut parser = Self { bytes, offset: 0 };
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
            Some(b'{') => self.object_value(),
            Some(b'[') => self.array_value(),
            Some(b'"') => self.string_value().map(Json::String),
            Some(b't') => self.literal(b"true", Json::Bool(true)),
            Some(b'f') => self.literal(b"false", Json::Bool(false)),
            Some(b'n') => self.literal(b"null", Json::Null),
            Some(b'0'..=b'9') => self.number_value(),
            _ => Err(self.error("expected a JSON value")),
        }
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
            let (actual_hash, actual_spent) = evaluate(term, atp, &store);
            let expected = field(vector, "expected")?.object()?;
            let expected_hash = field(expected, "result_hash")?.string()?;
            let expected_spent = field(expected, "atp_spent")?.number()?;
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
    if field(root, "format_version")?.number()? != 2 {
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
        match check_vector(vector, &objects) {
            Ok(()) => {
                println!("OK  {id}");
                passed += 1;
            }
            Err(error) => println!("FAIL {id}: {error}"),
        }
    }
    println!();
    if passed == 49 && vectors.len() == 49 {
        println!("RUST-CONFORMANCE: ALL PASS (49/49)");
        Ok(true)
    } else {
        println!("RUST-CONFORMANCE: FAIL ({passed}/{})", vectors.len());
        Ok(false)
    }
}

fn usage(program: &str) {
    eprintln!("usage: {program} selftest | conformance <vectors.json>");
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    let ok = match args.as_slice() {
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
    };
    if ok {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}
