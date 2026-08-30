package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"reflect"
	"sort"
	"strconv"
	"strings"
)

const (
	assertionTag = "sigma-glyph.wave-assertion@v1"
	policyTag    = "sigma-glyph.selection@v1"
	viewTag      = "sigma-glyph.annotation-view@v1"
	lutArbiter   = "c16701c44851da342f5d1f977ba5284e66dde3abd2c6740b979e39ac1d4d38b2"

	// Warrant SPEC v0.4 §5: a signature covers "warrant-sig-v1:" followed by
	// the 32 raw bytes of the WarrantID, 47 bytes in all. A Go verifier that
	// counts a signature the Python verifier refuses is the
	// two-implementations-disagree outcome this repository exists to forbid.
	//
	// Go cannot import tools/warrant_sig.py, so this is the one copy of the
	// construction that must exist. tests/one_signing_path.py pins it to that
	// module's own constant, which is the only honest check available across a
	// language boundary -- and the reason it is a named constant here.
	warrantSigDomain = "warrant-sig-v1:"
)

var orderFields = map[string]bool{"epoch": true, "ts": true, "warrant_id": true, "actor": true}
var lutCos []int16

type Wave map[string]any

type Candidate struct {
	WarrantID string
	Actor     string
	TS        uint64
	Assertion map[string]any
	Raw       map[string]any
}

type OrderKey struct {
	Field string
	Dir   string
}

type Selection struct {
	Status      string
	Selected    *Candidate
	ConflictSet []string
}

func main() {
	lutCos = genLUT()
	// Book III §5: the annotation profile is validated before anything is
	// answered. A contradictory profile is refused here, at load, rather than
	// discovered by whichever query happens to reach the pinned node.
	if err := requireAnnotationProfile(); err != nil {
		die("annotation profile refused: " + err.Error())
	}
	if len(os.Args) < 2 {
		die("usage: sigma-federation-go <replay|gov-replay|select|wave|viewid|setroot|validate-assertion|validate-policy|interfere|book1-unreachable>")
	}
	var err error
	switch os.Args[1] {
	case "replay":
		if len(os.Args) != 3 {
			die("usage: sigma-federation-go replay tests/spec_conformance/federation_vectors.json")
		}
		err = replay(os.Args[2])
	case "gov-replay":
		if len(os.Args) != 3 {
			die("usage: sigma-federation-go gov-replay tests/spec_conformance/governance_vectors.json")
		}
		err = govReplay(os.Args[2])
	case "select":
		err = cmdSelect()
	case "wave":
		err = cmdWave()
	case "viewid":
		err = cmdViewID()
	case "setroot":
		err = cmdSetRoot()
	case "validate-assertion":
		err = cmdValidateAssertion()
	case "validate-policy":
		err = cmdValidatePolicy()
	case "interfere":
		err = cmdInterfere()
	case "book1-unreachable":
		// See book1EchoedConstantNotEvaluated: this prints a transcribed
		// constant. It is not evidence that Go can evaluate Book I.
		fmt.Fprintln(os.Stderr, "note: impl-go has NO Book I evaluator; "+
			"this output is a hand-transcribed constant, not an evaluation")
		err = writeJSON(book1EchoedConstantNotEvaluated())
	default:
		err = fmt.Errorf("unknown subcommand %q", os.Args[1])
	}
	if err != nil {
		die(err.Error())
	}
}

func die(msg string) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(1)
}

func readJSONStdin() (any, error) {
	dec := json.NewDecoder(os.Stdin)
	dec.UseNumber()
	var v any
	if err := dec.Decode(&v); err != nil {
		return nil, err
	}
	return v, nil
}

func readJSONFile(path string) (map[string]any, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	dec := json.NewDecoder(f)
	dec.UseNumber()
	var v map[string]any
	if err := dec.Decode(&v); err != nil {
		return nil, err
	}
	return v, nil
}

func writeJSON(v any) error {
	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)
	return enc.Encode(v)
}

func asMap(v any) (map[string]any, bool) {
	m, ok := v.(map[string]any)
	return m, ok
}

func asList(v any) ([]any, bool) {
	a, ok := v.([]any)
	return a, ok
}

func asString(v any) (string, bool) {
	s, ok := v.(string)
	return s, ok
}

func isHex64(s string) bool {
	if len(s) != 64 {
		return false
	}
	for _, c := range s {
		if !('0' <= c && c <= '9' || 'a' <= c && c <= 'f') {
			return false
		}
	}
	return true
}

func unsignedFits(value uint64, bits int) bool {
	return bits >= 64 || value < uint64(1)<<bits
}

func signedUnsigned(value int64, bits int) (uint64, bool) {
	if value < 0 {
		return 0, false
	}
	return boundedUnsigned(uint64(value), bits)
}

func boundedUnsigned(value uint64, bits int) (uint64, bool) {
	if !unsignedFits(value, bits) {
		return 0, false
	}
	return value, true
}

func floatUnsigned(value float64, bits int) (uint64, bool) {
	if value < 0 || math.Trunc(value) != value || (bits < 64 && value >= float64(uint64(1)<<bits)) {
		return 0, false
	}
	return uint64(value), true
}

func uintValue(v any, bits int) (uint64, bool) {
	switch x := v.(type) {
	case json.Number:
		u, err := strconv.ParseUint(x.String(), 10, bits)
		return u, err == nil
	case float64:
		return floatUnsigned(x, bits)
	case int:
		return signedUnsigned(int64(x), bits)
	case int64:
		return signedUnsigned(x, bits)
	case uint:
		return boundedUnsigned(uint64(x), bits)
	case uint16:
		return boundedUnsigned(uint64(x), bits)
	case uint64:
		return boundedUnsigned(x, bits)
	default:
		return 0, false
	}
}

func intValue(v any, bits int) (int64, bool) {
	switch x := v.(type) {
	case json.Number:
		i, err := strconv.ParseInt(x.String(), 10, bits)
		return i, err == nil
	case float64:
		if math.Trunc(x) != x {
			return 0, false
		}
		min, max := int64(-1)<<(bits-1), int64(1)<<(bits-1)-1
		if x < float64(min) || x > float64(max) {
			return 0, false
		}
		return int64(x), true
	case int:
		min, max := int64(-1)<<(bits-1), int64(1)<<(bits-1)-1
		if int64(x) < min || int64(x) > max {
			return 0, false
		}
		return int64(x), true
	case int64:
		min, max := int64(-1)<<(bits-1), int64(1)<<(bits-1)-1
		if x < min || x > max {
			return 0, false
		}
		return x, true
	case int16:
		return int64(x), true
	default:
		return 0, false
	}
}

func validateAssertion(doc any) *string {
	m, ok := asMap(doc)
	if !ok || !sameKeys(m, []string{"annotation", "jurisdiction", "node", "epoch", "wave"}) {
		return strPtr("assertion blob must have exactly {annotation, jurisdiction, node, epoch, wave}")
	}
	if s, ok := asString(m["annotation"]); !ok || s != assertionTag {
		return strPtr(fmt.Sprintf("annotation must be %q", assertionTag))
	}
	j, jok := asString(m["jurisdiction"])
	n, nok := asString(m["node"])
	if !jok || !nok || !isHex64(j) || !isHex64(n) {
		return strPtr("jurisdiction and node must be hex64")
	}
	if _, ok := uintValue(m["epoch"], 64); !ok {
		return strPtr("epoch must be a uint64")
	}
	w, ok := asMap(m["wave"])
	if !ok || !sameKeys(w, []string{"ph", "am", "en"}) {
		return strPtr("wave must be a complete WaveVectorQ {ph, am, en}")
	}
	if _, ok := uintValue(w["ph"], 16); !ok {
		return strPtr("ph and am must be uint16")
	}
	if _, ok := uintValue(w["am"], 16); !ok {
		return strPtr("ph and am must be uint16")
	}
	if _, ok := intValue(w["en"], 16); !ok {
		return strPtr("en must be int16")
	}
	return nil
}

func validateOrderKey(item any) *string {
	key, ok := asMap(item)
	if !ok || !sameKeys(key, []string{"field", "dir"}) {
		return strPtr("order keys must be {field, dir}")
	}
	field, fieldOK := asString(key["field"])
	if !fieldOK || !orderFields[field] {
		return strPtr("order field must be one of ('epoch', 'ts', 'warrant_id', 'actor')")
	}
	direction, directionOK := asString(key["dir"])
	if !directionOK || (direction != "asc" && direction != "desc") {
		return strPtr("order dir must be asc|desc")
	}
	return nil
}

func validatePolicy(doc any) *string {
	m, ok := asMap(doc)
	if !ok {
		return strPtr("policy has unknown fields")
	}
	allowed := map[string]bool{
		"federation_policy":     true,
		"order":                 true,
		"max_age_epochs":        true,
		"quota_per_actor_epoch": true,
	}
	for k := range m {
		if !allowed[k] {
			return strPtr("policy has unknown fields")
		}
	}
	if s, ok := asString(m["federation_policy"]); !ok || s != policyTag {
		return strPtr(fmt.Sprintf("federation_policy must be %q", policyTag))
	}
	order, ok := asList(m["order"])
	if !ok || len(order) == 0 {
		return strPtr("order must be a nonempty list")
	}
	for _, item := range order {
		if err := validateOrderKey(item); err != nil {
			return err
		}
	}
	if err := validatePolicyOptions(m); err != nil {
		return err
	}
	return nil
}

func validatePolicyOptions(policy map[string]any) *string {
	for _, option := range []string{"max_age_epochs", "quota_per_actor_epoch"} {
		value, exists := policy[option]
		if !exists {
			continue
		}
		if _, ok := uintValue(value, 64); !ok {
			return strPtr(fmt.Sprintf("%s must be a uint64", option))
		}
	}
	return nil
}

func sameKeys(m map[string]any, keys []string) bool {
	if len(m) != len(keys) {
		return false
	}
	for _, k := range keys {
		if _, ok := m[k]; !ok {
			return false
		}
	}
	return true
}

func strPtr(s string) *string { return &s }

func parseOrder(policy map[string]any) []OrderKey {
	raw, _ := asList(policy["order"])
	out := make([]OrderKey, 0, len(raw))
	for _, item := range raw {
		m, _ := asMap(item)
		field, _ := asString(m["field"])
		dir, _ := asString(m["dir"])
		out = append(out, OrderKey{Field: field, Dir: dir})
	}
	return out
}

func validMetadata(m map[string]any) (*Candidate, bool) {
	wid, wok := asString(m["warrant_id"])
	actor, aok := asString(m["actor"])
	ts, tok := uintValue(m["ts"], 64)
	if !wok || !isHex64(wid) || !aok || strings.TrimSpace(actor) == "" || !tok {
		return nil, false
	}
	assertion, ok := asMap(m["assertion"])
	if !ok {
		assertion = nil
	}
	return &Candidate{WarrantID: wid, Actor: actor, TS: ts, Assertion: assertion, Raw: m}, true
}

func liveCandidate(raw any, policy map[string]any, jurisdiction, node string, epoch uint64) *Candidate {
	m, ok := asMap(raw)
	if !ok {
		return nil
	}
	candidate, ok := validMetadata(m)
	if !ok || candidate.Assertion == nil || validateAssertion(candidate.Assertion) != nil {
		return nil
	}
	anode, _ := asString(candidate.Assertion["node"])
	ajur, _ := asString(candidate.Assertion["jurisdiction"])
	aepoch, _ := uintValue(candidate.Assertion["epoch"], 64)
	if anode != node || ajur != jurisdiction || aepoch > epoch {
		return nil
	}
	if maxRaw, exists := policy["max_age_epochs"]; exists {
		maxAge, _ := uintValue(maxRaw, 64)
		if epoch-aepoch > maxAge {
			return nil
		}
	}
	return candidate
}

func applyQuota(live []*Candidate, quota uint64, order []OrderKey) []*Candidate {
	groups := map[string][]*Candidate{}
	for _, candidate := range live {
		epoch, _ := uintValue(candidate.Assertion["epoch"], 64)
		key := candidate.Actor + "\x00" + strconv.FormatUint(epoch, 10)
		groups[key] = append(groups[key], candidate)
	}
	keys := make([]string, 0, len(groups))
	for key := range groups {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	survivors := []*Candidate{}
	for _, key := range keys {
		group := groups[key]
		sort.Slice(group, func(i, j int) bool { return cmpOrder(group[i], group[j], order) < 0 })
		keep := int(quota)
		if uint64(keep) != quota || keep > len(group) {
			keep = len(group)
		}
		survivors = append(survivors, group[:keep]...)
	}
	return survivors
}

func selectCandidates(candidates []any, policy map[string]any, jurisdiction, node string, epoch uint64) Selection {
	live := make([]*Candidate, 0, len(candidates))
	for _, raw := range candidates {
		candidate := liveCandidate(raw, policy, jurisdiction, node, epoch)
		if candidate != nil {
			live = append(live, candidate)
		}
	}
	order := parseOrder(policy)
	tieOrder := append(append([]OrderKey{}, order...), OrderKey{Field: "warrant_id", Dir: "asc"})
	if quotaRaw, exists := policy["quota_per_actor_epoch"]; exists {
		quota, _ := uintValue(quotaRaw, 64)
		live = applyQuota(live, quota, tieOrder)
	}
	if len(live) == 0 {
		return Selection{Status: "absent", ConflictSet: []string{}}
	}
	sort.Slice(live, func(i, j int) bool { return cmpOrder(live[i], live[j], tieOrder) < 0 })
	top := make([]*Candidate, 0)
	for _, c := range live {
		if cmpOrder(c, live[0], order) == 0 {
			top = append(top, c)
		}
	}
	if len(top) == 1 {
		return Selection{Status: "selected", Selected: top[0], ConflictSet: []string{}}
	}
	ids := make([]string, 0, len(top))
	for _, c := range top {
		ids = append(ids, c.WarrantID)
	}
	sort.Strings(ids)
	return Selection{Status: "conflict", ConflictSet: ids}
}

func fieldValue(c *Candidate, name string) any {
	if name == "epoch" {
		v, _ := uintValue(c.Assertion["epoch"], 64)
		return v
	}
	if name == "ts" {
		return c.TS
	}
	if name == "warrant_id" {
		return c.WarrantID
	}
	return c.Actor
}

func compareValues(left, right any) int {
	switch value := left.(type) {
	case uint64:
		other := right.(uint64)
		if value < other {
			return -1
		}
		if value > other {
			return 1
		}
	case string:
		other := right.(string)
		if value < other {
			return -1
		}
		if value > other {
			return 1
		}
	}
	return 0
}

func cmpOrder(a, b *Candidate, order []OrderKey) int {
	for _, k := range order {
		c := compareValues(fieldValue(a, k.Field), fieldValue(b, k.Field))
		if c != 0 {
			if k.Dir == "desc" {
				return -c
			}
			return c
		}
	}
	return 0
}

func selectionSummary(sel Selection) map[string]any {
	var selected any
	if sel.Selected != nil {
		selected = sel.Selected.WarrantID
	}
	return map[string]any{
		"status":           sel.Status,
		"selected_warrant": selected,
		"conflict_set":     sel.ConflictSet,
	}
}

func cmdSelect() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	req, ok := asMap(v)
	if !ok {
		return errors.New("select request must be an object")
	}
	policy, ok := asMap(req["policy"])
	if !ok {
		return errors.New("select request missing policy")
	}
	cands, ok := asList(req["candidates"])
	if !ok {
		return errors.New("select request missing candidates")
	}
	jur, _ := asString(req["jurisdiction"])
	node, _ := asString(req["node"])
	epoch, ok := uintValue(req["epoch"], 64)
	if !ok {
		return errors.New("select request epoch must be uint64")
	}
	return writeJSON(selectionSummary(selectCandidates(cands, policy, jur, node, epoch)))
}

func cmdWave() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	req, ok := asMap(v)
	if !ok {
		return errors.New("wave request must be an object")
	}
	term := req["term"]
	resolver := waveResolver(req, term)
	w, err := waveFed(term, resolver)
	if err != nil {
		return err
	}
	return writeJSON(map[string]any{"wave": w})
}

func waveResolver(req map[string]any, term any) map[string]map[string]any {
	resolver := map[string]map[string]any{}
	if sels, ok := asList(req["selections"]); ok {
		for _, raw := range sels {
			item, ok := asMap(raw)
			if !ok {
				continue
			}
			sel, _ := asMap(item["selection"])
			if sel == nil {
				continue
			}
			resolver[termKey(item["term"])] = sel
		}
	} else if sel, ok := asMap(req["selection"]); ok {
		if !isSelectionAbsent(sel) {
			sel = cloneMap(sel)
			if sw, exists := req["selected_wave"]; exists {
				sel["selected_wave"] = sw
			}
			resolver[termKey(term)] = sel
		}
	}
	return resolver
}

func isSelectionAbsent(sel map[string]any) bool {
	status, _ := asString(sel["status"])
	return status == "absent"
}

func cloneMap(m map[string]any) map[string]any {
	out := make(map[string]any, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}

func selectedWave(selection map[string]any) (any, bool) {
	status, _ := asString(selection["status"])
	if status == "conflict" {
		return nil, true
	}
	if status != "selected" {
		return nil, false
	}
	if wave, ok := asMap(selection["selected_wave"]); ok {
		return normalizeWave(wave), true
	}
	selected, ok := asMap(selection["selected"])
	if !ok {
		return nil, false
	}
	assertion, ok := asMap(selected["assertion"])
	if !ok {
		return nil, false
	}
	wave, ok := asMap(assertion["wave"])
	if !ok {
		return nil, false
	}
	return normalizeWave(wave), true
}

func applyWave(term []any, resolver map[string]map[string]any) (any, error) {
	left, err := waveFed(term[1], resolver)
	if err != nil || left == nil {
		return nil, err
	}
	right, err := waveFed(term[2], resolver)
	if err != nil || right == nil {
		return nil, err
	}
	leftMap, _ := asMap(left)
	rightMap, _ := asMap(right)
	// Book III §5's fallback is Book II §2's derived case, pin included. It was
	// `interfere` alone, so a node reached structurally lost the Pin a node
	// reached by name kept: one NodeHash, two waves. That is Identity by Hash
	// (Book I §3.2) failing, not a wrong vector.
	derived := interfere(leftMap, rightMap)
	pin, err := structuralPin(term)
	if err != nil {
		return nil, err
	}
	if pin == nil {
		return derived, nil
	}
	return complete(derived, pin), nil
}

// ---- Identity by Hash, enough of Book I to name a node ----------------------
//
// Book II §6.2 pins FALSE ≡ APPLY(K,I) BY NODEHASH, so a conforming Book II/III
// implementation has to be able to say which node it is looking at. That needs
// Book I's canonical serialization for APPLY and the three genesis LITERALs,
// and nothing else: this file still contains no evaluator.

func sigmaLeafHash(name string) ([32]byte, bool) {
	atom, ok := map[string][32]byte{
		"I": sha256.Sum256([]byte("I")),
		"K": sha256.Sum256([]byte("K")),
		"S": sha256.Sum256([]byte("S")),
	}[name]
	if !ok {
		return [32]byte{}, false
	}
	// ser(LITERAL, F_ATOM, atom): opcode 0x00, flags 0x01, then the atom.
	buf := append([]byte{0x00, 0x01}, atom[:]...)
	return sha256.Sum256(buf), true
}

// nodeHashOf returns Book I's NodeHash for a wave term, or ok=false when this
// term language carries no bytes for it (Ph-only leaves, unpinned LITERALs).
// Such a term has no derived pin rather than a pin under an improvised key.
func nodeHashOf(term any) ([32]byte, bool) {
	if name, ok := asString(term); ok {
		if digest, found := sigmaLeafHash(name); found {
			return digest, true
		}
		// Ph-only NODES have identity even though their wave is absent (2.1).
		// Treating them as identity-less was the same wrong model the Python
		// mirror carried: absent wave is not absent node.
		if pin, found := nodePins[name]; found {
			raw, err := hex.DecodeString(pin.NodeHash)
			if err != nil || len(raw) != 32 {
				return [32]byte{}, false
			}
			var digest [32]byte
			copy(digest[:], raw)
			return digest, true
		}
		return [32]byte{}, false
	}
	parts, ok := term.([]any)
	if !ok || len(parts) != 3 {
		return [32]byte{}, false
	}
	if head, _ := asString(parts[0]); head != "APPLY" {
		return [32]byte{}, false
	}
	left, okL := nodeHashOf(parts[1])
	right, okR := nodeHashOf(parts[2])
	if !okL || !okR {
		return [32]byte{}, false
	}
	// ser(APPLY, F_LEFT|F_RIGHT, left, right): opcode 0x02, flags 0x06.
	buf := append([]byte{0x02, 0x06}, left[:]...)
	buf = append(buf, right[:]...)
	return sha256.Sum256(buf), true
}

func canonicalTerm(term any) any { return canonicalTermIn(aliases, term) }

func canonicalTermIn(table map[string]aliasDef, term any) any {
	if name, ok := asString(term); ok {
		if alias, found := table[name]; found {
			return canonicalTermIn(table, alias.Term)
		}
		return term
	}
	if parts, ok := term.([]any); ok && len(parts) == 3 {
		if head, _ := asString(parts[0]); head == "APPLY" {
			return []any{"APPLY", canonicalTermIn(table, parts[1]),
				canonicalTermIn(table, parts[2])}
		}
	}
	return term
}

// loadAnnotationProfile validates a profile and returns its NodeHash -> Pin
// index. Book III §5 requires a profile with two different Pins for one NodeHash
// to be refused AT LOAD, before it answers anything: it is accepted whole or it
// does not exist for the engine.
//
// This used to be called from the lookup, so a contradictory profile loaded
// fine, answered every query that missed the contradiction, and refused only
// when a wave query happened to reach the pinned node. The normative sentence
// said load time and the code did query time.
// It admits EVERY node-level section 6 source in one pass, and resolves identity
// WITHIN the profile it is handed.
//
// Three defects this shape closes, all found by review of the Python mirror:
// validating the alias table alone left fullPins and aliases as separate
// authorities; re-reading a global identity table split one label into two nodes
// by route; and a Pin whose node could not be named was skipped, so an
// unresolvable Pin produced an empty profile that admitted cleanly.
//
// Ph-only entries are not all alike. SATOSHI (6.3) and the six Pantheon nodes
// (6.4) have NodeHashes printed in the Book: their wave is absent because am/en
// are underived (2.1), but their identity and their {ph} Pin are real and
// admission MUST cover them. Only V (6.2) has no NodeHash and stays out.
func loadAnnotationProfile(table map[string]aliasDef,
	fulls map[string]map[string]any,
	nodePins map[string]nodePin) (map[string]map[string]any, error) {

	type binding struct {
		digest string
		source string
	}
	bindings := map[string]binding{}

	// A label binds to one NodeHash, and every source naming it must agree.
	// This is a determinism requirement on profile lookup, not a claim that a
	// label is identity -- Book II 2.3 leaves labels as descriptors.
	bindLabel := func(name, digest, source string) error {
		if existing, seen := bindings[name]; seen && existing.digest != digest {
			return fmt.Errorf(
				"label %q is bound to %s by %s and to %s by %s. Within one "+
					"admitted profile a lookup label must resolve unambiguously "+
					"to one NodeHash; the label is not identity (Book II 2.3 "+
					"leaves labels as descriptors). Two resolutions for one "+
					"label make the profile inadmissible",
				name, existing.digest, existing.source, digest, source)
		}
		bindings[name] = binding{digest, source}
		return nil
	}

	for _, glyph := range []string{"I", "K", "S"} {
		digest, ok := sigmaLeafHash(glyph)
		if !ok {
			return nil, fmt.Errorf("genesis leaf %q has no NodeHash", glyph)
		}
		if err := bindLabel(glyph, hex.EncodeToString(digest[:]), "Book I 5.1"); err != nil {
			return nil, err
		}
	}
	nodeNames := sortedKeysNodePin(nodePins)
	for _, name := range nodeNames {
		declared := nodePins[name].NodeHash
		if !isHex64(declared) {
			return nil, fmt.Errorf(
				"%q declares %q, which is not a 32-byte NodeHash in lowercase "+
					"hexadecimal", name, declared)
		}
		if err := bindLabel(name, declared, "node-level Pin table (6.3-6.4)"); err != nil {
			return nil, err
		}
	}

	// Cycles are found by the alias names already visited, not by a depth
	// limit: a bound on chain length would invent a normative maximum, and a
	// long acyclic chain is well-formed.
	// The alias chain is followed ITERATIVELY, and the visited set is copied
	// once per resolve() rather than once per link. Recursing per link made the
	// admissible length depend on the stack, and copying per link made it
	// quadratic: a 20 000-link chain did not finish. APPLY nesting is still
	// structural recursion, bounded by how deeply a term is written.
	// label -> resolved NodeHash. A label's resolution depends on the tables,
	// never on the path taken to reach it, so a completed resolution is
	// reusable. Only COMPLETED ones are memoized: a label on the current path
	// is not yet resolved, so cycle detection still sees it.
	memo := map[string]string{}

	var resolve func(term any, seen map[string]bool) (string, error)
	resolve = func(term any, seen map[string]bool) (string, error) {
		visited := make(map[string]bool, len(seen)+8)
		for k := range seen {
			visited[k] = true
		}
		var chain []string
		remember := func(digest string) string {
			for _, label := range chain {
				memo[label] = digest
			}
			return digest
		}
		for {
			name, ok := asString(term)
			if !ok {
				break
			}
			if digest, cached := memo[name]; cached {
				return remember(digest), nil
			}
			alias, found := table[name]
			if !found {
				if b, bound := bindings[name]; bound {
					return remember(b.digest), nil
				}
				return remember(""), nil
			}
			if visited[name] {
				return "", fmt.Errorf("alias chain revisits %q", name)
			}
			visited[name] = true
			chain = append(chain, name)
			term = alias.Term
		}
		seen = visited
		parts, ok := term.([]any)
		if !ok || len(parts) != 3 {
			return remember(""), nil
		}
		if head, _ := asString(parts[0]); head != "APPLY" {
			return remember(""), nil
		}
		left, err := resolve(parts[1], seen)
		if err != nil {
			return "", err
		}
		if left == "" {
			return remember(""), nil
		}
		right, err := resolve(parts[2], seen)
		if err != nil {
			return "", err
		}
		if right == "" {
			return remember(""), nil
		}
		leftBytes, err1 := hex.DecodeString(left)
		rightBytes, err2 := hex.DecodeString(right)
		if err1 != nil || err2 != nil {
			return "", fmt.Errorf("unreadable child NodeHash under APPLY")
		}
		buf := append([]byte{0x02, 0x06}, leftBytes...)
		buf = append(buf, rightBytes...)
		sum := sha256.Sum256(buf)
		return remember(hex.EncodeToString(sum[:])), nil
	}

	pins := map[string]map[string]any{}
	claimedBy := map[string]string{}

	admit := func(name, key string, pin map[string]any, what string) error {
		// A Pin whose node cannot be named is REFUSED, not skipped.
		if key == "" {
			return fmt.Errorf(
				"%s %q carries a Pin %v but no NodeHash can be resolved for it "+
					"under this profile; a Pin with no node is not admissible. "+
					"Sector coordinates (6.2 V) carry no Pin", what, name, pin)
		}
		if existing, seen := pins[key]; seen && !sameWavePin(existing, pin) {
			return fmt.Errorf(
				"%q and %q are the same node %s but pin it differently: %v vs "+
					"%v. One node has one wave (Book I 3.2, Book II 2.3); pick "+
					"one pin. This is an annotation-profile refusal at load "+
					"time, not an eval exit: it is not a Receipt.exit and not a "+
					"DISSONANCE",
				claimedBy[key], name, key, existing, pin)
		}
		pins[key] = pin
		claimedBy[key] = name
		return nil
	}

	for _, name := range sortedKeysPin(fulls) {
		if err := admit(name, bindings[name].digest, fulls[name], "full Pin"); err != nil {
			return nil, err
		}
	}
	for _, name := range nodeNames {
		if err := admit(name, bindings[name].digest, nodePins[name].Pin,
			"node-level Pin"); err != nil {
			return nil, err
		}
	}
	for _, name := range sortedKeysAlias(table) {
		digest, err := resolve(table[name].Term, map[string]bool{})
		if err != nil {
			return nil, err
		}
		if digest != "" {
			// An alias is also a label: it cannot name a node different from
			// the one its own label is already bound to.
			if err := bindLabel(name, digest, "alias table"); err != nil {
				return nil, err
			}
		}
		if err := admit(name, digest, table[name].Pin, "alias"); err != nil {
			return nil, err
		}
	}
	return pins, nil
}

// The edition's own profile, validated once at startup and read -- never
// rebuilt -- by structuralPin.
var annotationProfile map[string]map[string]any

func requireAnnotationProfile() error {
	profile, err := loadAnnotationProfile(aliases, fullPins, nodePins)
	if err != nil {
		return err
	}
	annotationProfile = profile
	return nil
}

func sortedKeysPin(m map[string]map[string]any) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func sortedKeysAlias(m map[string]aliasDef) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func sortedKeysNodePin(m map[string]nodePin) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func sameWavePin(a, b map[string]any) bool {
	return reflect.DeepEqual(a, b)
}

// structuralPin reads the profile loaded at startup. A lookup is not the place
// to discover that the profile was never valid.
func structuralPin(term any) (map[string]any, error) {
	if annotationProfile == nil {
		return nil, fmt.Errorf("annotation profile was never loaded: call " +
			"requireAnnotationProfile() before answering wave queries (Book III §5)")
	}
	digest, ok := nodeHashOf(canonicalTerm(term))
	if !ok {
		return nil, nil
	}
	return annotationProfile[hex.EncodeToString(digest[:])], nil
}

func waveFed(term any, resolver map[string]map[string]any) (any, error) {
	if sel, ok := resolver[termKey(term)]; ok {
		if wave, decisive := selectedWave(sel); decisive {
			return wave, nil
		}
	}
	if s, ok := asString(term); ok {
		return namedWave(s, resolver)
	}
	if _, ok := asMap(term); ok {
		return nil, nil
	}
	if xs, ok := asList(term); ok && len(xs) > 0 {
		tag, _ := asString(xs[0])
		if tag == "APPLY" && len(xs) == 3 {
			return applyWave(xs, resolver)
		}
	}
	return nil, fmt.Errorf("bad term: %v", term)
}

func namedWave(name string, resolver map[string]map[string]any) (any, error) {
	if wave, ok := fullPins[name]; ok {
		return copyWave(wave), nil
	}
	alias, ok := aliases[name]
	if !ok {
		return nil, nil
	}
	subwave, err := waveFed(alias.Term, resolver)
	if err != nil {
		return nil, err
	}
	return complete(subwave, alias.Pin), nil
}

func termKey(v any) string {
	b, _ := json.Marshal(v)
	return string(b)
}

func normalizeWave(w map[string]any) map[string]any {
	ph, _ := uintValue(w["ph"], 16)
	am, _ := uintValue(w["am"], 16)
	en, _ := intValue(w["en"], 16)
	return W(uint16(ph), uint16(am), int16(en))
}

type aliasDef struct {
	Term any
	Pin  map[string]any
}

var fullPins = map[string]map[string]any{
	"I": W(0, 65535, -32768),
	"S": W(16384, 65535, -32768),
	"K": W(32768, 65535, -32768),
}

var aliases = map[string]aliasDef{
	"FALSE": {Term: []any{"APPLY", "K", "I"}, Pin: map[string]any{"ph": uint16(49152)}},
}

// A node-level Ph-only Pin: identity exists (6.3, 6.4), the wave does not (2.1).
type nodePin struct {
	NodeHash string
	Pin      map[string]any
}

// 6.4 states the forging method normatively. 6.3 does NOT follow it: SATOSHI's
// atom is the BTC genesis block hash rather than SHA-256 of its name, so its
// NodeHash is the constant the Book prints and cannot be derived from the name.
const satoshiNodeHash = "11c856acd4b6868a91c2cc2cf6331d57bf268f56adcae0c0f3070c4ec00ed3c7"

func forgeNodeHash(name string) string {
	atom := sha256.Sum256([]byte(name))
	sum := sha256.Sum256(append([]byte{0x00, 0x01}, atom[:]...))
	return hex.EncodeToString(sum[:])
}

var nodePins = func() map[string]nodePin {
	out := map[string]nodePin{
		"SATOSHI": {NodeHash: satoshiNodeHash, Pin: map[string]any{"ph": uint16(8192)}},
	}
	for name, ph := range map[string]uint16{
		"TESLA": 8192, "TURING": 20480, "BACH": 21845,
		"LEIBNIZ": 24576, "GODEL": 40960, "HEGEL": 57344,
	} {
		out[name] = nodePin{NodeHash: forgeNodeHash(name), Pin: map[string]any{"ph": ph}}
	}
	return out
}()

// 6.2's V row: a sector coordinate with no NodeHash, deliberately not a Pin.
var sectorCoordinates = map[string]uint16{"V": 16384}

func copyWave(w map[string]any) map[string]any {
	return W(w["ph"].(uint16), w["am"].(uint16), w["en"].(int16))
}

func complete(w any, pin map[string]any) any {
	out := map[string]any{}
	if wm, ok := asMap(w); ok {
		for k, v := range wm {
			out[k] = v
		}
	}
	for k, v := range pin {
		out[k] = v
	}
	if _, ok := out["ph"]; !ok {
		return nil
	}
	if _, ok := out["am"]; !ok {
		return nil
	}
	if _, ok := out["en"]; !ok {
		return nil
	}
	return normalizeWave(out)
}

func W(ph, am uint16, en int16) map[string]any {
	return map[string]any{"ph": ph, "am": am, "en": en}
}

func divRoundHalfUp(n, d int64) int64 {
	sign := int64(1)
	if n < 0 {
		sign = -1
		n = -n
	}
	q, r := n/d, n%d
	if 2*r >= d {
		q++
	}
	return sign * q
}

func clampI16(x int64) int16 {
	if x < -32768 {
		return -32768
	}
	if x > 32767 {
		return 32767
	}
	return int16(x)
}

func genLUT() []int16 {
	lut := make([]int16, 32769)
	var buf bytes.Buffer
	for d := 0; d <= 32768; d++ {
		v := 32767 * math.Cos(math.Pi*float64(d)/32768)
		rounded := int16(math.Floor(math.Abs(v) + 0.5))
		if v < 0 {
			rounded = -rounded
		}
		lut[d] = rounded
		_ = binary.Write(&buf, binary.BigEndian, rounded)
	}
	sum := sha256.Sum256(buf.Bytes())
	if hex.EncodeToString(sum[:]) != lutArbiter {
		die("LUT arbiter mismatch - FAIL FAST (Book II s4)")
	}
	return lut
}

func interfere(w1, w2 map[string]any) map[string]any {
	ph1u, _ := uintValue(w1["ph"], 16)
	ph2u, _ := uintValue(w2["ph"], 16)
	am1u, _ := uintValue(w1["am"], 16)
	am2u, _ := uintValue(w2["am"], 16)
	en1, _ := intValue(w1["en"], 16)
	en2, _ := intValue(w2["en"], 16)
	ph1, ph2 := int64(ph1u), int64(ph2u)
	x := ph1 - ph2
	if x < 0 {
		x = -x
	}
	delta := x
	if 65536-x < delta {
		delta = 65536 - x
	}
	r := int64(lutCos[delta])
	deltaEn := divRoundHalfUp(-r, 128)
	newEn := clampI16(divRoundHalfUp(en1+en2, 2) + deltaEn)
	ampFactor := divRoundHalfUp((r+32767)*65535, 65534)
	prod01 := divRoundHalfUp(int64(am1u)*int64(am2u), 65535)
	newAm := divRoundHalfUp(prod01*ampFactor, 65535)
	return W(uint16(ph1u), uint16(newAm), newEn)
}

func cmdInterfere() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	req, ok := asMap(v)
	if !ok {
		return errors.New("interfere request must be an object")
	}
	w1, ok1 := asMap(req["w1"])
	w2, ok2 := asMap(req["w2"])
	if !ok1 || !ok2 {
		return errors.New("interfere request needs w1 and w2")
	}
	return writeJSON(map[string]any{"wave": interfere(w1, w2)})
}

func cmdViewID() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	req, ok := asMap(v)
	if !ok {
		return errors.New("viewid request must be an object")
	}
	j, _ := asString(req["jurisdiction"])
	n, _ := asString(req["node"])
	p, _ := asString(req["policy_hash"])
	e, ok := uintValue(req["epoch"], 64)
	if !ok {
		return errors.New("viewid epoch must be uint64")
	}
	return writeJSON(map[string]any{"view_id": viewID(j, n, p, e)})
}

func cmdSetRoot() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	req, ok := asMap(v)
	if !ok {
		return errors.New("setroot request must be an object")
	}
	raw, ok := asList(req["warrant_ids"])
	if !ok {
		return errors.New("setroot request missing warrant_ids")
	}
	ids := make([]string, 0, len(raw))
	for _, v := range raw {
		s, _ := asString(v)
		ids = append(ids, s)
	}
	return writeJSON(map[string]any{"assertion_set_root": assertionSetRoot(ids)})
}

func cmdValidateAssertion() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	return writeJSON(map[string]any{"error": validateAssertion(v)})
}

func cmdValidatePolicy() error {
	v, err := readJSONStdin()
	if err != nil {
		return err
	}
	return writeJSON(map[string]any{"error": validatePolicy(v)})
}

func jcs(v any) []byte {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		panic(err)
	}
	return unescapeLineSeparators(bytes.TrimSuffix(buf.Bytes(), []byte("\n")))
}

// unescapeLineSeparators rewrites the   and   escapes that Go's
// encoding/json emits UNCONDITIONALLY (even with SetEscapeHTML(false)) back to
// their raw UTF-8 bytes. RFC 8785 / JCS — the anchored canonicalization (spec/
// GOV-anchors.md §2: "RFC 8785: sorted keys, no whitespace") — escapes only the
// control characters U+0000..U+001F and the two mandatory characters (" and \);
// U+2028/U+2029 are >= 0x20 and MUST appear raw, exactly as Python's
// json.dumps(ensure_ascii=False) already emits them. Without this, a governance
// record body carrying U+2028/U+2029 in a string field hashes to a DIFFERENT
// WarrantID under Go than under the Python oracle, so the two implementations
// would DISAGREE on id-soundness / canonicality — a federation-consensus split
// (Kimi full-audit, 2026-07). Escape sequences are consumed atomically so a
// literal "\\u2028" (an escaped backslash followed by the text u2028) is never
// mis-read as the line-separator escape.
func unescapeLineSeparators(b []byte) []byte {
	if !bytes.Contains(b, []byte(`\u202`)) {
		return b // fast path: nothing to rewrite
	}
	var out bytes.Buffer
	out.Grow(len(b))
	i := 0
	for i < len(b) {
		if b[i] == '\\' && i+1 < len(b) {
			if b[i+1] == 'u' && i+5 < len(b) {
				switch string(b[i+2 : i+6]) {
				case "2028":
					out.WriteRune('\u2028')
				case "2029":
					out.WriteRune('\u2029')
				default:
					out.Write(b[i : i+6]) // some other \uXXXX (e.g. a control char)
				}
				i += 6
				continue
			}
			out.Write(b[i : i+2]) // \", \\, \n, \b, ... consumed as a unit
			i += 2
			continue
		}
		out.WriteByte(b[i])
		i++
	}
	return out.Bytes()
}

func shaHex(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

func viewID(jurisdiction, node, policyHash string, epoch uint64) string {
	return shaHex(jcs(map[string]any{
		"view":         viewTag,
		"jurisdiction": jurisdiction,
		"node":         node,
		"policy":       policyHash,
		"epoch":        epoch,
	}))
}

func assertionSetRoot(ids []string) string {
	cp := append([]string{}, ids...)
	sort.Strings(cp)
	return shaHex(jcs(cp))
}

func replayVector(v map[string]any) (any, bool, error) {
	kind, _ := asString(v["kind"])
	switch kind {
	case "validate_assertion":
		return validateAssertion(v["doc"]), false, nil
	case "validate_policy":
		return validatePolicy(v["doc"]), false, nil
	case "select":
		return replaySelection(v), false, nil
	case "wave_fed":
		wave, err := replayWave(v)
		return wave, false, err
	case "view_id":
		jurisdiction, _ := asString(v["jurisdiction"])
		node, _ := asString(v["node"])
		policy, _ := asString(v["policy_hash"])
		epoch, _ := uintValue(v["epoch"], 64)
		return viewID(jurisdiction, node, policy, epoch), false, nil
	case "assertion_set_root":
		return replayAssertionSetRoot(v), false, nil
	case "fold_probe":
		w1, _ := asMap(v["w1"])
		w2, _ := asMap(v["w2"])
		w3, _ := asMap(v["w3"])
		return map[string]any{"left": interfere(interfere(w1, w2), w3),
			"right": interfere(w1, interfere(w2, w3))}, false, nil
	case "book1_unreachable":
		return nil, true, nil
	default:
		return fmt.Sprintf("unknown kind %s", kind), false, nil
	}
}

func replaySelection(v map[string]any) any {
	policy, _ := asMap(v["policy"])
	candidates, _ := asList(v["candidates"])
	jurisdiction, _ := asString(v["jurisdiction"])
	node, _ := asString(v["node"])
	epoch, _ := uintValue(v["epoch"], 64)
	return selectionSummary(selectCandidates(candidates, policy, jurisdiction, node, epoch))
}

func replayWave(v map[string]any) (any, error) {
	request := map[string]any{"term": v["term"]}
	if v["selected_wave"] != nil {
		request["selection"] = map[string]any{"status": "selected"}
		request["selected_wave"] = v["selected_wave"]
	}
	return waveFed(request["term"], waveResolver(request, request["term"]))
}

func replayAssertionSetRoot(v map[string]any) string {
	rawIDs, _ := asList(v["warrant_ids"])
	ids := make([]string, 0, len(rawIDs))
	for _, rawID := range rawIDs {
		id, _ := asString(rawID)
		ids = append(ids, id)
	}
	return assertionSetRoot(ids)
}

func replay(path string) error {
	doc, err := readJSONFile(path)
	if err != nil {
		return err
	}
	rawVectors, ok := asList(doc["vectors"])
	if !ok {
		return errors.New("vectors must be a list")
	}
	okays := 0
	var vacuous []string
	for _, raw := range rawVectors {
		v, _ := asMap(raw)
		id, _ := asString(v["id"])
		got, isVacuous, err := replayVector(v)
		if err != nil {
			return err
		}
		if isVacuous {
			// Not counted as a pass, and excluded from the denominator: this
			// implementation cannot verify it. Reporting it green inflated
			// FEDERATION-GO's tally with a vector it never checked.
			vacuous = append(vacuous, id)
			fmt.Println("VACUOUS", id,
				"- impl-go has no Book I evaluator; echoed, not verified")
			continue
		}
		if jsonEqual(got, v["expected"]) {
			okays++
			fmt.Println("OK ", id)
		} else {
			fmt.Println("FAIL", id, "got", mustJSON(got), "want", mustJSON(v["expected"]))
		}
	}
	n := len(rawVectors) - len(vacuous)
	note := ""
	if len(vacuous) > 0 {
		note = fmt.Sprintf("; %d vector(s) NOT verified by this implementation: %s",
			len(vacuous), strings.Join(vacuous, ", "))
	}
	if okays == n {
		fmt.Printf("\nFEDERATION-GO: ALL PASS (%d/%d%s)\n", okays, n, note)
		return nil
	}
	fmt.Printf("\nFEDERATION-GO: FAILURES PRESENT (%d/%d%s)\n", okays, n, note)
	return errors.New("replay failures")
}

const (
	govAnchorSetTag = "sigma-glyph.anchor-set@v1"
	govProfileTag   = "sigma-glyph.anchor-governance@v1"
	govTrustTag     = "sigma-glyph.anchor-trust@v1"
)

type GovStore struct {
	Records map[string]any
	Blobs   map[string][]byte
}

type GovThreshold struct {
	Min    int
	Actors []string
}

type GovLineage struct {
	ProfileHash   string
	ThresholdHash string
	Threshold     GovThreshold
}

type GovAccept struct {
	ID      string
	Env     map[string]any
	Body    map[string]any
	Subject any
}

func optionalString(raw any) *string {
	if raw == nil {
		return nil
	}
	value, ok := asString(raw)
	if !ok {
		return nil
	}
	return &value
}

func govReplayVector(v map[string]any) (bool, string, error) {
	store, err := govStoreFromVector(v["store"])
	if err != nil {
		return false, "", err
	}
	candidate, _ := asString(v["candidate"])
	trust, _ := asMap(v["trust"])
	gotOK, notes := govVerifyAdoption(
		store, candidate, trust, optionalString(v["prior_set"]))
	expected, _ := asMap(v["expected"])
	wantOK, _ := expected["authorized"].(bool)
	wantNote, _ := asString(expected["note"])
	joined := strings.Join(notes, "; ")
	return gotOK == wantOK && strings.Contains(joined, wantNote), joined, nil
}

func govReplay(path string) error {
	doc, err := readJSONFile(path)
	if err != nil {
		return err
	}
	if format, _ := asString(doc["format"]); format != "sigma-glyph.governance-vectors@v1" {
		return errors.New("unknown governance vector format")
	}
	rawVectors, ok := asList(doc["vectors"])
	if !ok {
		return errors.New("vectors must be a list")
	}
	okays := 0
	for _, raw := range rawVectors {
		v, _ := asMap(raw)
		id, _ := asString(v["id"])
		good, joined, err := govReplayVector(v)
		if err != nil {
			fmt.Println("FAIL", id, err)
			continue
		}
		if good {
			okays++
			fmt.Println("OK ", id)
		} else {
			fmt.Println("FAIL", id, "notes", joined)
		}
	}
	n := len(rawVectors)
	if okays == n {
		fmt.Printf("\nGOVERNANCE-GO: ALL PASS (%d/%d)\n", okays, n)
		return nil
	}
	fmt.Printf("\nGOVERNANCE-GO: FAILURES PRESENT (%d/%d)\n", okays, n)
	return errors.New("governance replay failures")
}

func govStoreFromVector(raw any) (GovStore, error) {
	m, ok := asMap(raw)
	if !ok {
		return GovStore{}, errors.New("store must be an object")
	}
	recordMap, ok := asMap(m["records"])
	if !ok {
		return GovStore{}, errors.New("store.records must be an object")
	}
	blobMap, ok := asMap(m["blobs"])
	if !ok {
		return GovStore{}, errors.New("store.blobs must be an object")
	}
	store := GovStore{Records: map[string]any{}, Blobs: map[string][]byte{}}
	for rid, env := range recordMap {
		store.Records[rid] = env
	}
	for h, rawHex := range blobMap {
		hs, ok := asString(rawHex)
		if !ok {
			return GovStore{}, fmt.Errorf("blob %s must be hex", h)
		}
		b, err := hex.DecodeString(hs)
		if err != nil {
			return GovStore{}, fmt.Errorf("blob %s: %w", h, err)
		}
		store.Blobs[h] = b
	}
	return store, nil
}

type GovContext struct {
	Closure       map[string]bool
	Profile       string
	ThresholdHash string
	Threshold     GovThreshold
}

func govCandidateJurisdiction(store GovStore, blobHash string, trust map[string]any, priorSetHash *string) (string, []string) {
	if !govValidTrust(trust) {
		return "", []string{"trust config invalid"}
	}
	doc := store.parseJSONBlob(blobHash)
	if doc == nil {
		return "", []string{fmt.Sprintf("anchor-set blob %s missing or corrupt", shortHash(blobHash))}
	}
	anchor, ok := asMap(doc)
	if !ok || !govValidAnchorSet(anchor) {
		return "", []string{fmt.Sprintf("anchor-set blob %s schema-invalid", shortHash(blobHash))}
	}
	jurisdiction, _ := asString(anchor["jurisdiction"])
	trustJurisdiction, _ := asString(trust["jurisdiction"])
	if jurisdiction != trustJurisdiction {
		return "", []string{fmt.Sprintf("jurisdiction %s != pinned root %s (foreign blob, replay refused)", shortHash(jurisdiction), shortHash(trustJurisdiction))}
	}
	if priorSetHash == nil {
		if _, exists := anchor["ancestor"]; exists {
			return "", []string{"genesis anchor-set must not carry an ancestor"}
		}
	} else {
		ancestor, ok := asString(anchor["ancestor"])
		if !ok || ancestor != *priorSetHash {
			got := "absent"
			if ok {
				got = ancestor
			}
			return "", []string{fmt.Sprintf("ancestor %s != adopted prior %s (fork, not upgrade)", shortHash(got), shortHash(*priorSetHash))}
		}
	}
	return trustJurisdiction, nil
}

func govAdoptionContext(store GovStore, trust map[string]any, trustJurisdiction string) (GovContext, []string) {
	closure := store.settlementClosure(trustJurisdiction)
	if len(closure) == 0 {
		return GovContext{}, []string{fmt.Sprintf("jurisdiction root %s not in store", shortHash(trustJurisdiction))}
	}
	curProfile, lineage, errNote := store.deriveCurrentProfile(closure, trust)
	if errNote != "" {
		return GovContext{}, []string{"ERR: " + errNote}
	}
	if store.keyStateUnderGovernance(closure, lineage, trust) {
		return GovContext{}, []string{"ERR: key-state warrants under governance policy - derive key state with the warrant CLI first"}
	}
	pDoc, _ := store.parseJSONBlob(curProfile).(map[string]any)
	tHash, _ := asString(pDoc["threshold"])
	threshold, _ := govValidThresholdPolicy(store.parseJSONBlob(tHash))
	return GovContext{Closure: closure, Profile: curProfile,
		ThresholdHash: tHash, Threshold: threshold}, nil
}

func govIsAuthorizedRival(accept GovAccept, context GovContext, blobHash string,
	trust map[string]any, priorSetHash *string, jurisdiction string) (string, bool) {
	document, ok := accept.Subject.(map[string]any)
	if !ok || !govValidAnchorSet(document) {
		return "", false
	}
	hash := subjectHash(accept.Body)
	documentJurisdiction, _ := asString(document["jurisdiction"])
	if hash == "" || hash == blobHash || documentJurisdiction != jurisdiction {
		return "", false
	}
	if !sameAncestor(document, priorSetHash) ||
		!govUnderIs(accept.Body, context.Profile, context.ThresholdHash) {
		return "", false
	}
	counted := govCountedSigs(
		accept.Env, accept.ID, context.Threshold, govTrustActors(trust))
	return hash, len(counted) >= context.Threshold.Min
}

func govAuthorizedRivals(store GovStore, context GovContext, blobHash string, trust map[string]any, priorSetHash *string, jurisdiction string) []string {
	rivals := map[string]bool{}
	for _, acc := range store.acceptsOf(context.Closure) {
		if hash, ok := govIsAuthorizedRival(
			acc, context, blobHash, trust, priorSetHash, jurisdiction); ok {
			rivals[hash] = true
		}
	}
	ids := make([]string, 0, len(rivals))
	for hash := range rivals {
		ids = append(ids, shortHash(hash))
	}
	sort.Strings(ids)
	return ids
}

func govCandidateAdoption(store GovStore, context GovContext, blobHash string, trust map[string]any) (bool, []string) {
	notes := []string{}
	for _, acc := range store.acceptsOf(context.Closure) {
		if subjectHash(acc.Body) != blobHash {
			continue
		}
		if !govUnderIs(acc.Body, context.Profile, context.ThresholdHash) {
			notes = append(notes, fmt.Sprintf("%s: under != current (profile, threshold) pair", shortHash(acc.ID)))
			continue
		}
		counted := govCountedSigs(acc.Env, acc.ID, context.Threshold, govTrustActors(trust))
		if len(counted) >= context.Threshold.Min {
			notes = append(notes, fmt.Sprintf("adopted by %s (%d/%d of %d)", shortHash(acc.ID), len(counted), context.Threshold.Min, len(context.Threshold.Actors)))
			return true, notes
		}
		notes = append(notes, fmt.Sprintf("%s: %d bound sigs < min_sigs %d", shortHash(acc.ID), len(counted), context.Threshold.Min))
	}
	notes = append(notes, "no satisfying adoption warrant in settlement closure")
	return false, notes
}

func govVerifyAdoption(store GovStore, blobHash string, trust map[string]any, priorSetHash *string) (bool, []string) {
	jurisdiction, problems := govCandidateJurisdiction(store, blobHash, trust, priorSetHash)
	if problems != nil {
		return false, problems
	}
	context, problems := govAdoptionContext(store, trust, jurisdiction)
	if problems != nil {
		return false, problems
	}
	rivals := govAuthorizedRivals(store, context, blobHash, trust, priorSetHash, jurisdiction)
	if len(rivals) > 0 {
		return false, []string{"adoption conflict: rival authorized successor(s) " + strings.Join(rivals, ", ") + " share this ancestor - chain frozen"}
	}
	return govCandidateAdoption(store, context, blobHash, trust)
}

func (s GovStore) readBlob(h string) []byte {
	b, ok := s.Blobs[h]
	if !ok {
		return nil
	}
	if shaHex(b) != h {
		return nil
	}
	return b
}

func (s GovStore) parseJSONBlob(h string) any {
	b := s.readBlob(h)
	if b == nil {
		return nil
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.UseNumber()
	var v any
	if err := dec.Decode(&v); err != nil {
		return nil
	}
	// Reject trailing content after the first JSON value: a lone Decode()
	// accepts "<object> true" that Python's json.loads() rejects, which flips
	// authorization verdicts between the two implementations. A second decode
	// must hit io.EOF (Python parity).
	if dec.Decode(new(json.RawMessage)) != io.EOF {
		return nil
	}
	// Canonicality (RFC 8785 / JCS) is a store invariant: a blob addressed by
	// sha256(canon(doc)) MUST equal canon(doc) on the wire. Demanding the raw
	// bytes equal the re-canonicalization rejects pretty-printed, duplicate-key
	// and non-minimal encodings (Python parity — parse_json_blob does the same).
	if !bytes.Equal(jcs(v), b) {
		return nil
	}
	return v
}

func govValidTrustActors(raw any) bool {
	actors, ok := asMap(raw)
	if !ok || len(actors) == 0 {
		return false
	}
	for actor, rawKeys := range actors {
		keys, ok := asList(rawKeys)
		if actor == "" || !ok || len(keys) == 0 {
			return false
		}
		for _, rawKey := range keys {
			key, ok := asString(rawKey)
			if !ok || !isHex64(key) {
				return false
			}
		}
	}
	return true
}

func govValidResolved(raw any) bool {
	items, ok := asList(raw)
	if !ok {
		return false
	}
	for _, item := range items {
		value, ok := asString(item)
		if !ok || !isHex64(value) {
			return false
		}
	}
	return true
}

func govValidTrust(doc map[string]any) bool {
	for k := range doc {
		switch k {
		case "governance_trust", "jurisdiction", "genesis_profile", "actors",
			"resolved_key_state":
		default:
			return false
		}
	}
	for _, k := range []string{"governance_trust", "jurisdiction", "genesis_profile", "actors"} {
		if _, ok := doc[k]; !ok {
			return false
		}
	}
	tag, _ := asString(doc["governance_trust"])
	j, jok := asString(doc["jurisdiction"])
	g, gok := asString(doc["genesis_profile"])
	if tag != govTrustTag || !jok || !gok || !isHex64(j) || !isHex64(g) || !govValidTrustActors(doc["actors"]) {
		return false
	}
	if raw, ok := doc["resolved_key_state"]; ok {
		return govValidResolved(raw)
	}
	return true
}

func govValidThresholdPolicy(doc any) (GovThreshold, bool) {
	m, ok := asMap(doc)
	if !ok || !sameKeys(m, []string{"warrant_policy", "threshold"}) {
		return GovThreshold{}, false
	}
	wp, _ := asString(m["warrant_policy"])
	t, ok := asMap(m["threshold"])
	if wp != "0.3" || !ok || !sameKeys(t, []string{"min_sigs", "actors"}) {
		return GovThreshold{}, false
	}
	rawActors, ok := asList(t["actors"])
	if !ok || len(rawActors) == 0 {
		return GovThreshold{}, false
	}
	actors := make([]string, 0, len(rawActors))
	seen := map[string]bool{}
	for _, rawActor := range rawActors {
		actor, ok := asString(rawActor)
		if !ok || actor == "" || seen[actor] {
			return GovThreshold{}, false
		}
		seen[actor] = true
		actors = append(actors, actor)
	}
	min, ok := jsonInt(t["min_sigs"])
	if !ok || min < 1 || min > len(actors) {
		return GovThreshold{}, false
	}
	return GovThreshold{Min: min, Actors: actors}, true
}

func govValidProfile(doc any) bool {
	m, ok := asMap(doc)
	if !ok || !sameKeys(m, []string{"governance_policy", "scope", "threshold"}) {
		return false
	}
	tag, _ := asString(m["governance_policy"])
	scope, _ := asString(m["scope"])
	th, ok := asString(m["threshold"])
	return tag == govProfileTag && scope == "spec/ANCHORS.txt" && ok && isHex64(th)
}

func govValidAnchorRows(raw any) bool {
	rows, ok := asList(raw)
	if !ok || len(rows) == 0 {
		return false
	}
	paths := make([]string, 0, len(rows))
	seenPaths := map[string]bool{}
	for _, rawRow := range rows {
		row, ok := asMap(rawRow)
		if !ok || !sameKeys(row, []string{"path", "anchor"}) {
			return false
		}
		path, pathOK := asString(row["path"])
		anchor, anchorOK := asString(row["anchor"])
		if !pathOK || path == "" || !anchorOK || !isHex64(anchor) || seenPaths[path] {
			return false
		}
		seenPaths[path] = true
		paths = append(paths, path)
	}
	return sort.StringsAreSorted(paths)
}

func govValidAnchorSet(doc map[string]any) bool {
	keys := []string{"governance", "jurisdiction", "release", "anchors"}
	if _, hasAncestor := doc["ancestor"]; hasAncestor {
		keys = append(keys, "ancestor")
	}
	if !sameKeys(doc, keys) {
		return false
	}
	tag, _ := asString(doc["governance"])
	j, jok := asString(doc["jurisdiction"])
	rel, rok := asString(doc["release"])
	if tag != govAnchorSetTag || !jok || !isHex64(j) || !rok || rel == "" {
		return false
	}
	if rawAncestor, exists := doc["ancestor"]; exists {
		ancestor, ok := asString(rawAncestor)
		if !ok || !isHex64(ancestor) {
			return false
		}
	}
	return govValidAnchorRows(doc["anchors"])
}

func (s GovStore) reachesClosure(rid string, closure map[string]bool) bool {
	_, body, ok := s.soundRecord(rid)
	if !ok {
		return false
	}
	for _, prior := range stringList(body["prior"]) {
		if closure[prior] {
			return true
		}
	}
	return false
}

func (s GovStore) settlementClosure(root string) map[string]bool {
	if _, _, ok := s.soundRecord(root); !ok {
		return map[string]bool{}
	}
	closure := map[string]bool{root: true}
	changed := true
	for changed {
		changed = false
		for rid := range s.Records {
			if !closure[rid] && s.reachesClosure(rid, closure) {
				closure[rid] = true
				changed = true
			}
		}
	}
	return closure
}

func (s GovStore) acceptsOf(closure map[string]bool) []GovAccept {
	ids := make([]string, 0, len(closure))
	for rid := range closure {
		ids = append(ids, rid)
	}
	sort.Strings(ids)
	out := []GovAccept{}
	for _, rid := range ids {
		env, body, ok := s.soundRecord(rid)
		if !ok {
			continue
		}
		decision, _ := asString(body["decision"])
		if decision != "accept" {
			continue
		}
		out = append(out, GovAccept{ID: rid, Env: env, Body: body, Subject: s.parseJSONBlob(subjectHash(body))})
	}
	return out
}

func (s GovStore) soundRecord(rid string) (map[string]any, map[string]any, bool) {
	env, ok := asMap(s.Records[rid])
	if !ok {
		return nil, nil, false
	}
	body, ok := asMap(env["body"])
	if !ok || shaHex(jcs(body)) != rid {
		return nil, nil, false
	}
	return env, body, true
}

func (s GovStore) lineageEntry(profileHash string) (GovLineage, string) {
	profileDoc := s.parseJSONBlob(profileHash)
	if !govValidProfile(profileDoc) {
		return GovLineage{}, fmt.Sprintf("current profile %s missing or schema-invalid", shortHash(profileHash))
	}
	profile, _ := asMap(profileDoc)
	thresholdHash, _ := asString(profile["threshold"])
	threshold, ok := govValidThresholdPolicy(s.parseJSONBlob(thresholdHash))
	if !ok {
		return GovLineage{}, fmt.Sprintf("threshold %s pinned by profile is invalid", shortHash(thresholdHash))
	}
	return GovLineage{ProfileHash: profileHash, ThresholdHash: thresholdHash,
		Threshold: threshold}, ""
}

func (s GovStore) profileSuccessors(closure map[string]bool, entry GovLineage, trust map[string]any, seen map[string]bool) map[string]bool {
	next := map[string]bool{}
	for _, accept := range s.acceptsOf(closure) {
		if !govValidProfile(accept.Subject) || !govUnderIs(accept.Body, entry.ProfileHash, entry.ThresholdHash) {
			continue
		}
		if len(govCountedSigs(accept.Env, accept.ID, entry.Threshold, govTrustActors(trust))) < entry.Threshold.Min {
			continue
		}
		hash := subjectHash(accept.Body)
		if hash != "" && !seen[hash] {
			next[hash] = true
		}
	}
	return next
}

func profileConflict(next map[string]bool) string {
	ids := make([]string, 0, len(next))
	for hash := range next {
		ids = append(ids, shortHash(hash))
	}
	sort.Strings(ids)
	return "profile-succession conflict: " + strings.Join(ids, ", ") + " - chain frozen, resolve by settlement"
}

func onlyHash(values map[string]bool) string {
	for hash := range values {
		return hash
	}
	return ""
}

func (s GovStore) deriveCurrentProfile(closure map[string]bool, trust map[string]any) (string, []GovLineage, string) {
	current, _ := asString(trust["genesis_profile"])
	seen := map[string]bool{current: true}
	lineage := []GovLineage{}
	for {
		entry, problem := s.lineageEntry(current)
		if problem != "" {
			return current, lineage, problem
		}
		lineage = append(lineage, entry)
		next := s.profileSuccessors(closure, entry, trust, seen)
		if len(next) == 0 {
			return current, lineage, ""
		}
		if len(next) > 1 {
			return current, lineage, profileConflict(next)
		}
		current = onlyHash(next)
		seen[current] = true
	}
}

func governanceHashes(lineage []GovLineage) (map[string]bool, map[string]GovThreshold) {
	govHashes := map[string]bool{}
	thresholdOf := map[string]GovThreshold{}
	for _, entry := range lineage {
		govHashes[entry.ProfileHash] = true
		govHashes[entry.ThresholdHash] = true
		thresholdOf[entry.ProfileHash] = entry.Threshold
		thresholdOf[entry.ThresholdHash] = entry.Threshold
	}
	return govHashes, thresholdOf
}

func (s GovStore) governedKeyState(rid string, govHashes map[string]bool, thresholdOf map[string]GovThreshold, trust map[string]any) bool {
	env, ok := asMap(s.Records[rid])
	if !ok {
		return false
	}
	body, ok := asMap(env["body"])
	if !ok {
		return false
	}
	decision, _ := asString(body["decision"])
	if decision != "accept" && decision != "supersede" {
		return false
	}
	cited := []string{}
	for _, hash := range stringList(body["under"]) {
		if govHashes[hash] {
			cited = append(cited, hash)
		}
	}
	subject, validSubject := s.parseJSONBlob(subjectHash(body)).(map[string]any)
	if len(cited) == 0 || !validSubject || !sameKeys(subject, []string{"actor", "key"}) || shaHex(jcs(body)) != rid {
		return false
	}
	for _, hash := range cited {
		threshold := thresholdOf[hash]
		if len(govCountedSigs(env, rid, threshold, govTrustActors(trust))) >= threshold.Min {
			return true
		}
	}
	return false
}

func (s GovStore) keyStateUnderGovernance(closure map[string]bool, lineage []GovLineage, trust map[string]any) bool {
	govHashes, thresholdOf := governanceHashes(lineage)
	resolved := map[string]bool{}
	for _, hash := range stringList(trust["resolved_key_state"]) {
		resolved[hash] = true
	}
	for _, rid := range sortedRecordIDs(closure) {
		if !resolved[rid] && s.governedKeyState(rid, govHashes, thresholdOf, trust) {
			return true
		}
	}
	return false
}

func govCountedSigs(env map[string]any, rid string, threshold GovThreshold, trustActors map[string][]string) map[string]bool {
	counted := map[string]bool{}
	thresholdActors := map[string]bool{}
	for _, actor := range threshold.Actors {
		thresholdActors[actor] = true
	}
	ridBytes, err := hex.DecodeString(rid)
	if err != nil {
		return counted
	}
	sigMsg := append([]byte(warrantSigDomain), ridBytes...)
	for _, rawSig := range stringListAny(env["sigs"]) {
		sigMap, ok := asMap(rawSig)
		if !ok {
			continue
		}
		actor, aok := asString(sigMap["actor"])
		key, kok := asString(sigMap["key"])
		sigHex, sok := asString(sigMap["sig"])
		if !aok || !kok || !sok || !thresholdActors[actor] || counted[actor] || !containsString(trustActors[actor], key) {
			continue
		}
		pub, err1 := hex.DecodeString(key)
		sig, err2 := hex.DecodeString(sigHex)
		if err1 != nil || err2 != nil || len(pub) != ed25519.PublicKeySize || len(sig) != ed25519.SignatureSize {
			continue
		}
		// Warrant SPEC v0.4 §5: the signed message names the protocol, so a key
		// that signs some other protocol's SHA-256 digest does not thereby sign
		// a Warrant. This is the Go half of a differential -- verifying the bare
		// WarrantID here would make the two halves disagree about what a valid
		// signature is, which is the defect class this project ranks P0. The
		// separator itself is the warrantSigDomain constant above, so the one
		// place Go states it is the one place tests/one_signing_path.py checks.
		if ed25519.Verify(ed25519.PublicKey(pub), sigMsg, sig) {
			counted[actor] = true
		}
	}
	return counted
}

func govUnderIs(body map[string]any, profileHash, thresholdHash string) bool {
	under := stringList(body["under"])
	if len(under) != 2 {
		return false
	}
	seen := map[string]bool{}
	for _, h := range under {
		seen[h] = true
	}
	return len(seen) == 2 && seen[profileHash] && seen[thresholdHash]
}

func sameAncestor(doc map[string]any, prior *string) bool {
	ancestor, has := asString(doc["ancestor"])
	if prior == nil {
		return !has
	}
	return has && ancestor == *prior
}

func subjectHash(body map[string]any) string {
	subject, ok := asMap(body["subject"])
	if !ok {
		return ""
	}
	h, _ := asString(subject["hash"])
	return h
}

func govTrustActors(trust map[string]any) map[string][]string {
	out := map[string][]string{}
	actors, _ := asMap(trust["actors"])
	for actor, rawKeys := range actors {
		out[actor] = stringList(rawKeys)
	}
	return out
}

func sortedRecordIDs(closure map[string]bool) []string {
	ids := make([]string, 0, len(closure))
	for rid := range closure {
		ids = append(ids, rid)
	}
	sort.Strings(ids)
	return ids
}

func stringList(raw any) []string {
	items, ok := asList(raw)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(items))
	for _, item := range items {
		s, ok := asString(item)
		if ok {
			out = append(out, s)
		}
	}
	return out
}

func stringListAny(raw any) []any {
	items, ok := asList(raw)
	if !ok {
		return nil
	}
	return items
}

func jsonInt(raw any) (int, bool) {
	switch x := raw.(type) {
	case json.Number:
		i, err := strconv.ParseInt(x.String(), 10, 32)
		return int(i), err == nil
	case int:
		return x, true
	case int64:
		if x < math.MinInt32 || x > math.MaxInt32 {
			return 0, false
		}
		return int(x), true
	case float64:
		if math.Trunc(x) != x || x < math.MinInt32 || x > math.MaxInt32 {
			return 0, false
		}
		return int(x), true
	default:
		return 0, false
	}
}

func containsString(xs []string, want string) bool {
	for _, x := range xs {
		if x == want {
			return true
		}
	}
	return false
}

func shortHash(h string) string {
	if len(h) < 12 {
		return h
	}
	return h[:12]
}

// book1EchoedConstantNotEvaluated returns the Book I EV-TV4-IK result as a
// LITERAL, hand-copied from tests/spec_conformance/vectors.json.
//
// impl-go contains no Book I evaluator — no deserializer, no stepper, no ATP
// accounting. Book III's criterion 1 vector FV-BOOK-I-UNREACHABLE is therefore
// VACUOUS on this side: comparing this constant against the Python oracle's
// eval proves only that the constant has not been mistyped. The name is this
// long on purpose; the old name (book1Fixture) let replay reports read as if a
// second implementation had independently verified Book I, which is exactly
// what a "three independent implementations" claim must not be built on.
//
// If Book I is ever implemented here, delete this function rather than reusing
// its name.
func book1EchoedConstantNotEvaluated() map[string]any {
	return map[string]any{
		"book1_vector":        "EV-TV4-IK",
		"result_hash":         "bc0c2fe26e44e2aed8ce500a74963bc270fd4a49ec0c2e4837ce7a64bb0a486c",
		"atp_spent":           uint64(4),
		"matches_book1_suite": true,
	}
}

func jsonEqual(a, b any) bool {
	return reflect.DeepEqual(normalizeJSON(a), normalizeJSON(b))
}

func normalizeMap(values map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range values {
		out[key] = normalizeJSON(value)
	}
	return out
}

func normalizeList(values []any) []any {
	out := make([]any, len(values))
	for index, value := range values {
		out[index] = normalizeJSON(value)
	}
	return out
}

func normalizeStrings(values []string) []any {
	out := make([]any, len(values))
	for index, value := range values {
		out[index] = value
	}
	return out
}

func normalizeJSON(v any) any {
	switch x := v.(type) {
	case *string:
		if x == nil {
			return nil
		}
		return *x
	case json.Number:
		if i, err := strconv.ParseInt(x.String(), 10, 64); err == nil {
			return i
		}
		if u, err := strconv.ParseUint(x.String(), 10, 64); err == nil {
			return u
		}
		return x.String()
	case uint16:
		return int64(x)
	case int16:
		return int64(x)
	case uint64:
		if x <= math.MaxInt64 {
			return int64(x)
		}
		return x
	case map[string]any:
		return normalizeMap(x)
	case []any:
		return normalizeList(x)
	case []string:
		return normalizeStrings(x)
	default:
		return x
	}
}

func mustJSON(v any) string {
	b, _ := json.Marshal(normalizeJSON(v))
	return string(b)
}

func drain(r io.Reader) {
	_, _ = io.Copy(io.Discard, r)
}
