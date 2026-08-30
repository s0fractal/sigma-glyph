package main

import (
	"encoding/hex"
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
	}
	for _, c := range cases {
		digest, ok := nodeHashOf(canonicalTerm(c.term))
		if !ok {
			t.Fatalf("%s: nodeHashOf returned not-ok", c.name)
		}
		if got := hex.EncodeToString(digest[:]); got != c.want {
			t.Fatalf("%s: got %s, Book I says %s", c.name, got, c.want)
		}
	}
}

// A term this language carries no bytes for has no identity here, and therefore
// no derived pin — rather than a pin under some improvised key.
func TestNodeHashOfRefusesUnhashableTerms(t *testing.T) {
	for _, term := range []any{"V", "SATOSHI", map[string]any{"lit": "unpinned"},
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
	pins, err := loadAnnotationProfile(aliases)
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
	_, err = loadAnnotationProfile(aliases)
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
	if _, err = loadAnnotationProfile(aliases); err == nil {
		t.Fatal("uint16(1) and \"1\" print alike but are not the same pin")
	}
}

// The profile must be refused while loading, before any wave is answered.
// Building it inside the lookup let a contradictory table serve every query
// that missed the contradiction.
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
