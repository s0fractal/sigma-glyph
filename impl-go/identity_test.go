package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
	"reflect"
	"testing"
)

// Book II §6.2 pins FALSE ≡ APPLY(K,I) BY NODEHASH, so this file has to be able
// to say which node it is looking at — and being able to say it consistently is
// not the same as saying it correctly.
//
// `derivedPins` and `structuralPin` both key off `nodeHashOf`. A wrong
// serialization would key the store and the lookup identically, so
// alias-equivalence and the wave differential would both stay green while every
// digest was wrong. These are external bindings: the expected values are Book
// I's, printed in the anchored specification (§5.1 for the genesis LITERALs,
// §5.2 for FALSE) and reproduced by `impl/sigma_glyph.py`. If Go's layout drifts
// by one byte, these fail and the self-consistent ones do not.
func TestNodeHashOfMatchesBookI(t *testing.T) {
	cases := []struct {
		name string
		term any
		want string
	}{
		// Book I §5.1: ser(LITERAL, F_ATOM, atom=SHA-256(name)), opcode 00 flags 01.
		{"I", "I", "2f33694d09810641fa5b8c47a7c0dc42e1b99eb8c9784a00aaee9a66330f4162"},
		{"K", "K", "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c"},
		{"S", "S", "887045bc22935aec5cba2dc11400d4e4357bc34d06681a6e92f06e7795b1f8a6"},
		// Book I §5.2 / TV-2: ser(APPLY, F_LEFT|F_RIGHT), opcode 02 flags 06.
		{"APPLY(K,I) ≡ FALSE", []any{"APPLY", "K", "I"},
			"65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098"},
		// Nested, so the recursion is bound too and not only the one-level case.
		{"APPLY(FALSE,I)", []any{"APPLY", []any{"APPLY", "K", "I"}, "I"},
			"d941c09b17232af7ec541e8b9c5420c3a8b1c50cc577c7c9d86f5fab2fc9e4fd"},
		{"APPLY(S,APPLY(FALSE,I))",
			[]any{"APPLY", "S", []any{"APPLY", []any{"APPLY", "K", "I"}, "I"}},
			"ac4eb4bf5534a2c40fe5ef3b71c3be89079ae21de6567c36631439f3de1b45c8"},
		// The alias resolves to the same node as its structure.
		{"FALSE by name", "FALSE",
			"65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098"},
		// A ph-only NODE: identity present, wave absent.
		{"SATOSHI", "SATOSHI",
			"11c856acd4b6868a91c2cc2cf6331d57bf268f56adcae0c0f3070c4ec00ed3c7"},
		// Composite over a ph-only node, so the recursion reaches one too.
		{"APPLY(SATOSHI,I)", []any{"APPLY", "SATOSHI", "I"}, ""},
	}
	for _, c := range cases {
		digest, ok := nodeHashOf(canonicalTerm(c.term))
		if !ok {
			t.Fatalf("%s: nodeHashOf returned not-ok", c.name)
		}
		if c.want == "" {
			continue // composite: identity must exist; its value is checked below
		}
		if got := hex.EncodeToString(digest[:]); got != c.want {
			t.Fatalf("%s: got %s, the Book prints %s", c.name, got, c.want)
		}
	}
	// The Book prints Pantheon digests only as prefix...suffix, so that is what
	// is asserted. Writing a full literal here meant inventing the middle, and
	// this test caught exactly that on its first run.
	tesla, ok := nodeHashOf("TESLA")
	teslaHex := hex.EncodeToString(tesla[:])
	if !ok {
		t.Fatal("TESLA must have a NodeHash")
	}
	// Two separate claims, and they come from different Books. The full digest
	// is only ever the OUTPUT of Book II 6.4's forging formula -- the Book
	// prints its edges, not its middle -- so the formula is the oracle for the
	// value and the printed edges are the oracle for the formula.
	atom := sha256.Sum256([]byte("TESLA"))
	forged := sha256.Sum256(append([]byte{0x00, 0x01}, atom[:]...))
	if teslaHex != hex.EncodeToString(forged[:]) {
		t.Fatalf("TESLA: nodeHashOf gives %s, Book II 6.4 forging yields %s",
			teslaHex, hex.EncodeToString(forged[:]))
	}
	if !strings.HasPrefix(teslaHex, "193e0542") || !strings.HasSuffix(teslaHex, "d9de3748") {
		t.Fatalf("TESLA: the forged digest %s does not match the prefix and "+
			"suffix printed by Book II 6.4 (193e0542...d9de3748)", teslaHex)
	}

	// The composite is built from the ph-only node's own digest, not skipped.
	satoshi, _ := nodeHashOf("SATOSHI")
	iHash, _ := sigmaLeafHash("I")
	buf := append([]byte{0x02, 0x06}, satoshi[:]...)
	buf = append(buf, iHash[:]...)
	expectedComposite := sha256.Sum256(buf)
	got, ok := nodeHashOf([]any{"APPLY", "SATOSHI", "I"})
	if !ok || got != expectedComposite {
		t.Fatalf("APPLY(SATOSHI,I): got %x, expected %x", got, expectedComposite)
	}
}

// A term this language carries no bytes for has no identity here, and therefore
// no derived pin — rather than a pin under some improvised key.
func TestNodeHashOfRefusesUnhashableTerms(t *testing.T) {
	// V is a sector coordinate and has no NodeHash. SATOSHI is NOT in this
	// list: it is a node with a printed NodeHash whose wave is absent (2.1).
	for _, term := range []any{"V", map[string]any{"lit": "unpinned"},
		[]any{"APPLY", "V", "I"}, []any{"NOTAPPLY", "K", "I"}} {
		if _, ok := nodeHashOf(canonicalTerm(term)); ok {
			t.Fatalf("%v: expected no computable identity", term)
		}
	}
}

// Synonyms are allowed; contradictions fail closed. A map would settle two pins
// for one node by iteration order, which is a specification defect decided by
// whichever entry was written last.
func TestDerivedPinsFailClosedOnContradiction(t *testing.T) {
	saved := aliases
	defer func() { aliases = saved }()

	aliases = map[string]aliasDef{
		"FALSE":      {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": uint16(49152)}},
		"ALSO-FALSE": {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": uint16(49152)}},
	}
	pins, err := loadAnnotationProfile(aliases, map[string]map[string]any{}, map[string]nodePin{})
	if err != nil {
		t.Fatalf("synonyms must be allowed, got %v", err)
	}
	if len(pins) != 1 {
		t.Fatalf("two names for one node must yield one pin, got %v", pins)
	}

	aliases = map[string]aliasDef{
		"FALSE":      {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": uint16(49152)}},
		"ALSO-FALSE": {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": uint16(1)}},
	}
	_, err = loadAnnotationProfile(aliases, map[string]map[string]any{}, map[string]nodePin{})
	if err == nil {
		t.Fatal("contradictory pins must fail closed, not resolve silently")
	}
	for _, want := range []string{"FALSE", "ALSO-FALSE",
		"65cd957fee7ec9fb310bc9d9712cec1726c78f8026fda679ac8f237938a32098"} {
		if !contains(err.Error(), want) {
			t.Fatalf("the refusal must name %q; got %q", want, err.Error())
		}
	}

	// Differently TYPED values that print identically are different pins. A
	// comparison through fmt.Sprint called uint16(1) and "1" the same thing,
	// so a table holding both would have been accepted as synonyms.
	aliases = map[string]aliasDef{
		"FALSE":      {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": uint16(1)}},
		"ALSO-FALSE": {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": "1"}},
	}
	if _, err = loadAnnotationProfile(aliases, map[string]map[string]any{}, map[string]nodePin{}); err == nil {
		t.Fatal("uint16(1) and \"1\" print alike but are not the same pin")
	}
}

// The profile must be refused while loading, before any wave is answered.
// Building it inside the lookup let a contradictory table serve every query
// that missed the contradiction.
// Admission must see every node-level source at once. fullPins and aliases were
// separate authorities, so an alias could re-pin a genesis node and be admitted.
func TestAdmissionSpansFullPinsAndAliases(t *testing.T) {
	kHash, ok := nodeHashOf("K")
	if !ok {
		t.Fatal("K must have a NodeHash")
	}
	key := hex.EncodeToString(kHash[:])

	conflicting := map[string]aliasDef{
		"ALSO-K": {Term: "K", Pin: map[string]any{"ph": uint16(1)}},
	}
	_, err := loadAnnotationProfile(conflicting, fullPins, map[string]nodePin{})
	if err == nil {
		t.Fatal("an alias re-pinning a full-pinned node must be refused")
	}
	for _, want := range []string{"K", "ALSO-K", key} {
		if !contains(err.Error(), want) {
			t.Fatalf("the refusal must name %q; got %q", want, err.Error())
		}
	}

	// A synonym of a full-pinned node is not a contradiction.
	same := map[string]aliasDef{"ALSO-K": {Term: "K", Pin: fullPins["K"]}}
	profile, err := loadAnnotationProfile(same, fullPins, map[string]nodePin{})
	if err != nil {
		t.Fatalf("an identical pin under a second name must be allowed: %v", err)
	}
	if !sameWavePin(profile[key], fullPins["K"]) {
		t.Fatalf("K's pin must survive the synonym: %v", profile[key])
	}

	// The edition's own profile covers exactly the node-level sources.
	edition, err := loadAnnotationProfile(aliases, fullPins, nodePins)
	if err != nil {
		t.Fatalf("the edition's profile must load: %v", err)
	}
	// The eleven node-level sources of section 6 as an exact NodeHash -> Pin
	// map, built from independent sources and compared whole. Comparing only
	// the SET OF HASHES let a Pin move without any test noticing: the phases
	// below were written down and then never read.
	//
	//   I/K/S     Book I constants, with Book II 6.1 Pins
	//   FALSE     APPLY(K,I) computed here, with Book II 6.2's ph
	//   SATOSHI   Book II 6.3's full printed constant
	//   Pantheon  Book II 6.4's formula, re-implemented, edges checked
	expected := map[string]map[string]any{}
	for glyph, pin := range map[string]map[string]any{
		"I": {"ph": uint16(0), "am": uint16(65535), "en": int16(-32768)},
		"S": {"ph": uint16(16384), "am": uint16(65535), "en": int16(-32768)},
		"K": {"ph": uint16(32768), "am": uint16(65535), "en": int16(-32768)},
	} {
		digest, _ := sigmaLeafHash(glyph)
		expected[hex.EncodeToString(digest[:])] = pin
	}
	kHashRaw, _ := sigmaLeafHash("K")
	iHashRaw, _ := sigmaLeafHash("I")
	falseBuf := append([]byte{0x02, 0x06}, kHashRaw[:]...)
	falseBuf = append(falseBuf, iHashRaw[:]...)
	falseDigest := sha256.Sum256(falseBuf)
	expected[hex.EncodeToString(falseDigest[:])] = map[string]any{"ph": uint16(49152)}

	const bookSatoshi = "11c856acd4b6868a91c2cc2cf6331d57bf268f56adcae0c0f3070c4ec00ed3c7"
	expected[bookSatoshi] = map[string]any{"ph": uint16(8192)}
	if satoshiNodeHash != bookSatoshi {
		t.Fatalf("production satoshiNodeHash %s is not Book II 6.3's constant %s",
			satoshiNodeHash, bookSatoshi)
	}
	if satoshiNodeHash == forgeNodeHash("SATOSHI") {
		t.Fatal("SATOSHI's NodeHash must be the Book's constant, not the forging method")
	}

	pantheon := map[string]struct {
		ph             uint16
		prefix, suffix string
	}{
		"TESLA":   {8192, "193e0542", "d9de3748"},
		"TURING":  {20480, "f7864d5e", "f6850375"},
		"BACH":    {21845, "878c08d8", "221e50c2"},
		"LEIBNIZ": {24576, "06696f7a", "5ab412cd"},
		"GODEL":   {40960, "d5f715d7", "e467eb96"},
		"HEGEL":   {57344, "5654c5dc", "8054a186"},
	}
	for name, row := range pantheon {
		nameAtom := sha256.Sum256([]byte(name))
		forgedDigest := sha256.Sum256(append([]byte{0x00, 0x01}, nameAtom[:]...))
		digest := hex.EncodeToString(forgedDigest[:])
		if !strings.HasPrefix(digest, row.prefix) || !strings.HasSuffix(digest, row.suffix) {
			t.Fatalf("%s: Book II 6.4 forging yields %s, which does not match the "+
				"printed %s...%s", name, digest, row.prefix, row.suffix)
		}
		expected[digest] = map[string]any{"ph": row.ph}
	}
	if len(expected) != 11 {
		t.Fatalf("expected eleven node-level sources, listed %d", len(expected))
	}
	if !reflect.DeepEqual(edition, expected) {
		t.Fatalf("the edition profile is not the eleven expected NodeHash -> Pin "+
			"entries.\n got: %v\nwant: %v", edition, expected)
	}

	if _, found := nodeHashOf("V"); found {
		t.Fatal("V is a sector coordinate and must have no node identity")
	}
	if _, isPin := nodePins["V"]; isPin {
		t.Fatal("V must not be a node-level Pin")
	}
}

// The contract closed in the Python mirror, checked here for its own reasons.
func TestProfileIsClosedUnderDeclaredIdentity(t *testing.T) {
	declared := map[string]nodePin{
		"SATOSHI": {NodeHash: strings.Repeat("a", 64),
			Pin: map[string]any{"ph": uint16(8192)}},
	}
	none := map[string]map[string]any{}

	cases := []struct {
		name    string
		aliases map[string]aliasDef
		fulls   map[string]map[string]any
		nodes   map[string]nodePin
		needle  string
	}{
		{"a declared hash conflicting through an alias is refused at that hash",
			map[string]aliasDef{"ALSO-SATOSHI": {Term: "SATOSHI",
				Pin: map[string]any{"ph": uint16(3)}}}, none, declared,
			strings.Repeat("a", 64)},
		{"a composite APPLY over a declared label uses the declared child",
			map[string]aliasDef{
				"PAIR":      {Term: []any{"APPLY", "SATOSHI", "I"}, Pin: map[string]any{"ph": uint16(7)}},
				"ALSO-PAIR": {Term: []any{"APPLY", "SATOSHI", "I"}, Pin: map[string]any{"ph": uint16(9)}},
			}, none, declared, "PAIR"},
		{"a node entry may not re-bind a genesis label", map[string]aliasDef{}, none,
			map[string]nodePin{"K": {NodeHash: strings.Repeat("b", 64), Pin: fullPins["K"]}},
			"Book I 5.1"},
		{"an alias may not re-bind a genesis label",
			map[string]aliasDef{"K": {Term: "I", Pin: map[string]any{"ph": uint16(5)}}},
			none, map[string]nodePin{}, "alias table"},
		{"a full Pin whose node cannot be named is refused", map[string]aliasDef{},
			map[string]map[string]any{"X": {"ph": uint16(1)}}, map[string]nodePin{}, "X"},
		{"an alias cycle is refused as a cycle",
			map[string]aliasDef{
				"A": {Term: "B", Pin: map[string]any{"ph": uint16(1)}},
				"B": {Term: "A", Pin: map[string]any{"ph": uint16(1)}},
			}, none, map[string]nodePin{}, "revisits"},
		{"a malformed declared NodeHash is refused", map[string]aliasDef{}, none,
			map[string]nodePin{"X": {NodeHash: "not-a-hash", Pin: map[string]any{"ph": uint16(1)}}},
			"not a 32-byte NodeHash"},
	}
	for _, c := range cases {
		_, err := loadAnnotationProfile(c.aliases, c.fulls, c.nodes)
		if err == nil {
			t.Fatalf("%s: admitted", c.name)
		}
		if !contains(err.Error(), c.needle) {
			t.Fatalf("%s: refusal must mention %q; got %q", c.name, c.needle, err.Error())
		}
	}

	// Positives, so "refuses everything" cannot pass as correctness.
	synonym, err := loadAnnotationProfile(
		map[string]aliasDef{"ALSO-SATOSHI": {Term: "SATOSHI",
			Pin: map[string]any{"ph": uint16(8192)}}}, none, declared)
	if err != nil || len(synonym) != 1 || synonym[strings.Repeat("a", 64)] == nil {
		t.Fatalf("a synonym at the declared hash must yield one entry: %v %v", synonym, err)
	}
	long := map[string]aliasDef{}
	for i := 0; i < 64; i++ {
		long[fmt.Sprintf("L%d", i)] = aliasDef{Term: fmt.Sprintf("L%d", i+1),
			Pin: map[string]any{"ph": uint16(8192)}}
	}
	long["L64"] = aliasDef{Term: "SATOSHI", Pin: map[string]any{"ph": uint16(8192)}}
	if _, err := loadAnnotationProfile(long, none, declared); err != nil {
		t.Fatalf("a long acyclic chain must be admitted, not depth-limited: %v", err)
	}
	reused, err := loadAnnotationProfile(
		map[string]aliasDef{"BOTH": {Term: []any{"APPLY", "SATOSHI", "SATOSHI"},
			Pin: map[string]any{"ph": uint16(2)}}}, none, declared)
	if err != nil || len(reused) != 2 {
		t.Fatalf("one alias reused in both APPLY branches is not a cycle: %v %v", reused, err)
	}
}

func TestStructuralPinRequiresALoadedProfile(t *testing.T) {
	saved := annotationProfile
	defer func() { annotationProfile = saved }()

	annotationProfile = nil
	if _, err := structuralPin([]any{"APPLY", "K", "I"}); err == nil {
		t.Fatal("a wave query with no loaded profile must refuse, not answer")
	}
	if err := requireAnnotationProfile(); err != nil {
		t.Fatalf("the edition's own profile must load: %v", err)
	}
	pin, err := structuralPin([]any{"APPLY", "K", "I"})
	if err != nil || pin == nil {
		t.Fatalf("after loading, FALSE's pin must be found: %v %v", pin, err)
	}
}

func TestSameWavePinIsTypeSafe(t *testing.T) {
	if sameWavePin(map[string]any{"ph": uint16(1)}, map[string]any{"ph": "1"}) {
		t.Fatal("uint16(1) and \"1\" must not compare equal")
	}
	if sameWavePin(map[string]any{"ph": uint16(1)}, map[string]any{"ph": 1}) {
		t.Fatal("uint16(1) and int(1) must not compare equal")
	}
	if !sameWavePin(map[string]any{"ph": uint16(1)}, map[string]any{"ph": uint16(1)}) {
		t.Fatal("identical pins must compare equal")
	}
	if !reflect.DeepEqual(map[string]any{}, map[string]any{}) {
		t.Fatal("empty pins are equal")
	}
}

func contains(haystack, needle string) bool {
	for i := 0; i+len(needle) <= len(haystack); i++ {
		if haystack[i:i+len(needle)] == needle {
			return true
		}
	}
	return false
}
