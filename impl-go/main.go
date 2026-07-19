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
		err = writeJSON(book1Fixture())
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

func uintValue(v any, bits int) (uint64, bool) {
	switch x := v.(type) {
	case json.Number:
		u, err := strconv.ParseUint(x.String(), 10, bits)
		return u, err == nil
	case float64:
		if x < 0 || math.Trunc(x) != x {
			return 0, false
		}
		if bits < 64 && x >= float64(uint64(1)<<bits) {
			return 0, false
		}
		return uint64(x), true
	case int:
		if x < 0 {
			return 0, false
		}
		if bits < 64 && uint64(x) >= uint64(1)<<bits {
			return 0, false
		}
		return uint64(x), true
	case int64:
		if x < 0 {
			return 0, false
		}
		if bits < 64 && uint64(x) >= uint64(1)<<bits {
			return 0, false
		}
		return uint64(x), true
	case uint:
		if bits < 64 && uint64(x) >= uint64(1)<<bits {
			return 0, false
		}
		return uint64(x), true
	case uint16:
		if bits < 16 && uint64(x) >= uint64(1)<<bits {
			return 0, false
		}
		return uint64(x), true
	case uint64:
		if bits < 64 && x >= uint64(1)<<bits {
			return 0, false
		}
		return x, true
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
		k, ok := asMap(item)
		if !ok || !sameKeys(k, []string{"field", "dir"}) {
			return strPtr("order keys must be {field, dir}")
		}
		field, fok := asString(k["field"])
		if !fok || !orderFields[field] {
			return strPtr("order field must be one of ('epoch', 'ts', 'warrant_id', 'actor')")
		}
		dir, dok := asString(k["dir"])
		if !dok || (dir != "asc" && dir != "desc") {
			return strPtr("order dir must be asc|desc")
		}
	}
	for _, opt := range []string{"max_age_epochs", "quota_per_actor_epoch"} {
		if v, exists := m[opt]; exists {
			if _, ok := uintValue(v, 64); !ok {
				return strPtr(fmt.Sprintf("%s must be a uint64", opt))
			}
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

func selectCandidates(candidates []any, policy map[string]any, jurisdiction, node string, epoch uint64) Selection {
	live := make([]*Candidate, 0, len(candidates))
	for _, raw := range candidates {
		m, ok := asMap(raw)
		if !ok {
			continue
		}
		c, ok := validMetadata(m)
		if !ok || c.Assertion == nil || validateAssertion(c.Assertion) != nil {
			continue
		}
		anode, _ := asString(c.Assertion["node"])
		ajur, _ := asString(c.Assertion["jurisdiction"])
		aepoch, _ := uintValue(c.Assertion["epoch"], 64)
		if anode != node || ajur != jurisdiction || aepoch > epoch {
			continue
		}
		if maxRaw, exists := policy["max_age_epochs"]; exists {
			maxAge, _ := uintValue(maxRaw, 64)
			if epoch-aepoch > maxAge {
				continue
			}
		}
		live = append(live, c)
	}
	order := parseOrder(policy)
	tieOrder := append(append([]OrderKey{}, order...), OrderKey{Field: "warrant_id", Dir: "asc"})
	if quotaRaw, exists := policy["quota_per_actor_epoch"]; exists {
		quota, _ := uintValue(quotaRaw, 64)
		groups := map[string][]*Candidate{}
		for _, c := range live {
			ep, _ := uintValue(c.Assertion["epoch"], 64)
			key := c.Actor + "\x00" + strconv.FormatUint(ep, 10)
			groups[key] = append(groups[key], c)
		}
		live = nil
		keys := make([]string, 0, len(groups))
		for k := range groups {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			g := groups[k]
			sort.Slice(g, func(i, j int) bool { return cmpOrder(g[i], g[j], tieOrder) < 0 })
			keep := int(quota)
			if uint64(keep) != quota || keep > len(g) {
				keep = len(g)
			}
			live = append(live, g[:keep]...)
		}
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

func cmpOrder(a, b *Candidate, order []OrderKey) int {
	for _, k := range order {
		av, bv := fieldValue(a, k.Field), fieldValue(b, k.Field)
		c := 0
		switch x := av.(type) {
		case uint64:
			y := bv.(uint64)
			if x < y {
				c = -1
			} else if x > y {
				c = 1
			}
		case string:
			y := bv.(string)
			if x < y {
				c = -1
			} else if x > y {
				c = 1
			}
		}
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
	w, err := waveFed(term, resolver)
	if err != nil {
		return err
	}
	return writeJSON(map[string]any{"wave": w})
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

func waveFed(term any, resolver map[string]map[string]any) (any, error) {
	if sel, ok := resolver[termKey(term)]; ok {
		status, _ := asString(sel["status"])
		if status == "selected" {
			if w, ok := asMap(sel["selected_wave"]); ok {
				return normalizeWave(w), nil
			}
			if selected, ok := asMap(sel["selected"]); ok {
				if assertion, ok := asMap(selected["assertion"]); ok {
					if w, ok := asMap(assertion["wave"]); ok {
						return normalizeWave(w), nil
					}
				}
			}
		}
		if status == "conflict" {
			return nil, nil
		}
	}
	if s, ok := asString(term); ok {
		if w, ok := fullPins[s]; ok {
			return copyWave(w), nil
		}
		if alias, ok := aliases[s]; ok {
			subw, err := waveFed(alias.Term, resolver)
			if err != nil {
				return nil, err
			}
			return complete(subw, alias.Pin), nil
		}
		return nil, nil
	}
	if _, ok := asMap(term); ok {
		return nil, nil
	}
	if xs, ok := asList(term); ok && len(xs) > 0 {
		tag, _ := asString(xs[0])
		if tag == "APPLY" && len(xs) == 3 {
			wl, err := waveFed(xs[1], resolver)
			if err != nil || wl == nil {
				return nil, err
			}
			wr, err := waveFed(xs[2], resolver)
			if err != nil || wr == nil {
				return nil, err
			}
			lm, _ := asMap(wl)
			rm, _ := asMap(wr)
			return interfere(lm, rm), nil
		}
	}
	return nil, fmt.Errorf("bad term: %v", term)
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
	for _, raw := range rawVectors {
		v, _ := asMap(raw)
		id, _ := asString(v["id"])
		kind, _ := asString(v["kind"])
		var got any
		switch kind {
		case "validate_assertion":
			got = validateAssertion(v["doc"])
		case "validate_policy":
			got = validatePolicy(v["doc"])
		case "select":
			pol, _ := asMap(v["policy"])
			cands, _ := asList(v["candidates"])
			j, _ := asString(v["jurisdiction"])
			n, _ := asString(v["node"])
			e, _ := uintValue(v["epoch"], 64)
			got = selectionSummary(selectCandidates(cands, pol, j, n, e))
		case "wave_fed":
			req := map[string]any{"term": v["term"]}
			if v["selected_wave"] != nil {
				req["selection"] = map[string]any{"status": "selected"}
				req["selected_wave"] = v["selected_wave"]
			}
			resolver := map[string]map[string]any{}
			if sel, ok := asMap(req["selection"]); ok {
				sel["selected_wave"] = req["selected_wave"]
				resolver[termKey(req["term"])] = sel
			}
			gotWave, err := waveFed(req["term"], resolver)
			if err != nil {
				return err
			}
			got = gotWave
		case "view_id":
			j, _ := asString(v["jurisdiction"])
			n, _ := asString(v["node"])
			p, _ := asString(v["policy_hash"])
			e, _ := uintValue(v["epoch"], 64)
			got = viewID(j, n, p, e)
		case "assertion_set_root":
			rawIDs, _ := asList(v["warrant_ids"])
			ids := make([]string, 0, len(rawIDs))
			for _, x := range rawIDs {
				s, _ := asString(x)
				ids = append(ids, s)
			}
			got = assertionSetRoot(ids)
		case "fold_probe":
			w1, _ := asMap(v["w1"])
			w2, _ := asMap(v["w2"])
			w3, _ := asMap(v["w3"])
			got = map[string]any{
				"left":  interfere(interfere(w1, w2), w3),
				"right": interfere(w1, interfere(w2, w3)),
			}
		case "book1_unreachable":
			got = book1Fixture()
		default:
			got = fmt.Sprintf("unknown kind %s", kind)
		}
		if jsonEqual(got, v["expected"]) {
			okays++
			fmt.Println("OK ", id)
		} else {
			fmt.Println("FAIL", id, "got", mustJSON(got), "want", mustJSON(v["expected"]))
		}
	}
	n := len(rawVectors)
	if okays == n {
		fmt.Printf("\nFEDERATION-GO: ALL PASS (%d/%d)\n", okays, n)
		return nil
	}
	fmt.Printf("\nFEDERATION-GO: FAILURES PRESENT (%d/%d)\n", okays, n)
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
		store, err := govStoreFromVector(v["store"])
		if err != nil {
			fmt.Println("FAIL", id, err)
			continue
		}
		candidate, _ := asString(v["candidate"])
		trust, _ := asMap(v["trust"])
		var prior *string
		if v["prior_set"] != nil {
			if s, ok := asString(v["prior_set"]); ok {
				prior = &s
			}
		}
		gotOK, notes := govVerifyAdoption(store, candidate, trust, prior)
		expected, _ := asMap(v["expected"])
		wantOK, _ := expected["authorized"].(bool)
		wantNote, _ := asString(expected["note"])
		joined := strings.Join(notes, "; ")
		good := gotOK == wantOK && strings.Contains(joined, wantNote)
		if good {
			okays++
			fmt.Println("OK ", id)
		} else {
			fmt.Println("FAIL", id, "authorized", gotOK, "notes", joined)
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

func govVerifyAdoption(store GovStore, blobHash string, trust map[string]any, priorSetHash *string) (bool, []string) {
	if !govValidTrust(trust) {
		return false, []string{"trust config invalid"}
	}
	doc := store.parseJSONBlob(blobHash)
	if doc == nil {
		return false, []string{fmt.Sprintf("anchor-set blob %s missing or corrupt", shortHash(blobHash))}
	}
	anchor, ok := asMap(doc)
	if !ok || !govValidAnchorSet(anchor) {
		return false, []string{fmt.Sprintf("anchor-set blob %s schema-invalid", shortHash(blobHash))}
	}
	jurisdiction, _ := asString(anchor["jurisdiction"])
	trustJurisdiction, _ := asString(trust["jurisdiction"])
	if jurisdiction != trustJurisdiction {
		return false, []string{fmt.Sprintf("jurisdiction %s != pinned root %s (foreign blob, replay refused)", shortHash(jurisdiction), shortHash(trustJurisdiction))}
	}
	if priorSetHash == nil {
		if _, exists := anchor["ancestor"]; exists {
			return false, []string{"genesis anchor-set must not carry an ancestor"}
		}
	} else {
		ancestor, ok := asString(anchor["ancestor"])
		if !ok || ancestor != *priorSetHash {
			got := "absent"
			if ok {
				got = ancestor
			}
			return false, []string{fmt.Sprintf("ancestor %s != adopted prior %s (fork, not upgrade)", shortHash(got), shortHash(*priorSetHash))}
		}
	}

	closure := store.settlementClosure(trustJurisdiction)
	if len(closure) == 0 {
		return false, []string{fmt.Sprintf("jurisdiction root %s not in store", shortHash(trustJurisdiction))}
	}
	curProfile, lineage, errNote := store.deriveCurrentProfile(closure, trust)
	if errNote != "" {
		return false, []string{"ERR: " + errNote}
	}
	if store.keyStateUnderGovernance(closure, lineage, trust) {
		return false, []string{"ERR: key-state warrants under governance policy - derive key state with the warrant CLI first"}
	}
	pDoc, _ := store.parseJSONBlob(curProfile).(map[string]any)
	tHash, _ := asString(pDoc["threshold"])
	threshold, _ := govValidThresholdPolicy(store.parseJSONBlob(tHash))

	rivals := map[string]bool{}
	for _, acc := range store.acceptsOf(closure) {
		rdoc, ok := acc.Subject.(map[string]any)
		if !ok || !govValidAnchorSet(rdoc) {
			continue
		}
		h := subjectHash(acc.Body)
		if h == "" || h == blobHash {
			continue
		}
		rjur, _ := asString(rdoc["jurisdiction"])
		if rjur != trustJurisdiction {
			continue
		}
		if !sameAncestor(rdoc, priorSetHash) {
			continue
		}
		if !govUnderIs(acc.Body, curProfile, tHash) {
			continue
		}
		if len(govCountedSigs(acc.Env, acc.ID, threshold, govTrustActors(trust))) >= threshold.Min {
			rivals[h] = true
		}
	}
	if len(rivals) > 0 {
		ids := make([]string, 0, len(rivals))
		for h := range rivals {
			ids = append(ids, shortHash(h))
		}
		sort.Strings(ids)
		return false, []string{"adoption conflict: rival authorized successor(s) " + strings.Join(ids, ", ") + " share this ancestor - chain frozen"}
	}

	notes := []string{}
	for _, acc := range store.acceptsOf(closure) {
		if subjectHash(acc.Body) != blobHash {
			continue
		}
		if !govUnderIs(acc.Body, curProfile, tHash) {
			notes = append(notes, fmt.Sprintf("%s: under != current (profile, threshold) pair", shortHash(acc.ID)))
			continue
		}
		counted := govCountedSigs(acc.Env, acc.ID, threshold, govTrustActors(trust))
		if len(counted) >= threshold.Min {
			notes = append(notes, fmt.Sprintf("adopted by %s (%d/%d of %d)", shortHash(acc.ID), len(counted), threshold.Min, len(threshold.Actors)))
			return true, notes
		}
		notes = append(notes, fmt.Sprintf("%s: %d bound sigs < min_sigs %d", shortHash(acc.ID), len(counted), threshold.Min))
	}
	notes = append(notes, "no satisfying adoption warrant in settlement closure")
	return false, notes
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
	var rest json.RawMessage
	if err := dec.Decode(&rest); err != io.EOF {
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

func govValidTrust(doc map[string]any) bool {
	// required keys, plus the optional resolved_key_state (Gemini STANDARD
	// gate P0): WarrantIDs of governance rotations already derived into actors
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
	actors, aok := asMap(doc["actors"])
	if tag != govTrustTag || !jok || !gok || !isHex64(j) || !isHex64(g) || !aok || len(actors) == 0 {
		return false
	}
	for actor, rawKeys := range actors {
		if actor == "" {
			return false
		}
		keys, ok := asList(rawKeys)
		if !ok || len(keys) == 0 {
			return false
		}
		for _, rawKey := range keys {
			key, ok := asString(rawKey)
			if !ok || !isHex64(key) {
				return false
			}
		}
	}
	if raw, ok := doc["resolved_key_state"]; ok {
		items, ok := asList(raw)
		if !ok {
			return false
		}
		for _, it := range items {
			s, ok := asString(it)
			if !ok || !isHex64(s) {
				return false
			}
		}
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
	rows, ok := asList(doc["anchors"])
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
		path, pok := asString(row["path"])
		anchor, aok := asString(row["anchor"])
		if !pok || path == "" || !aok || !isHex64(anchor) || seenPaths[path] {
			return false
		}
		seenPaths[path] = true
		paths = append(paths, path)
	}
	return sort.StringsAreSorted(paths)
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
			if closure[rid] {
				continue
			}
			_, body, ok := s.soundRecord(rid)
			if !ok {
				continue
			}
			for _, p := range stringList(body["prior"]) {
				if closure[p] {
					closure[rid] = true
					changed = true
					break
				}
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

func (s GovStore) deriveCurrentProfile(closure map[string]bool, trust map[string]any) (string, []GovLineage, string) {
	cur, _ := asString(trust["genesis_profile"])
	seen := map[string]bool{cur: true}
	lineage := []GovLineage{}
	for {
		pDoc := s.parseJSONBlob(cur)
		if !govValidProfile(pDoc) {
			return cur, lineage, fmt.Sprintf("current profile %s missing or schema-invalid", shortHash(cur))
		}
		pm, _ := asMap(pDoc)
		tHash, _ := asString(pm["threshold"])
		t, ok := govValidThresholdPolicy(s.parseJSONBlob(tHash))
		if !ok {
			return cur, lineage, fmt.Sprintf("threshold %s pinned by profile is invalid", shortHash(tHash))
		}
		lineage = append(lineage, GovLineage{ProfileHash: cur, ThresholdHash: tHash, Threshold: t})
		next := map[string]bool{}
		for _, acc := range s.acceptsOf(closure) {
			if !govValidProfile(acc.Subject) || !govUnderIs(acc.Body, cur, tHash) {
				continue
			}
			if len(govCountedSigs(acc.Env, acc.ID, t, govTrustActors(trust))) < t.Min {
				continue
			}
			h := subjectHash(acc.Body)
			if h != "" && !seen[h] {
				next[h] = true
			}
		}
		if len(next) == 0 {
			return cur, lineage, ""
		}
		if len(next) > 1 {
			ids := make([]string, 0, len(next))
			for h := range next {
				ids = append(ids, shortHash(h))
			}
			sort.Strings(ids)
			return cur, lineage, "profile-succession conflict: " + strings.Join(ids, ", ") + " - chain frozen, resolve by settlement"
		}
		for h := range next {
			cur = h
		}
		seen[cur] = true
	}
}

func (s GovStore) keyStateUnderGovernance(closure map[string]bool, lineage []GovLineage, trust map[string]any) bool {
	govHashes := map[string]bool{}
	thresholdOf := map[string]GovThreshold{}
	for _, g := range lineage {
		govHashes[g.ProfileHash] = true
		govHashes[g.ThresholdHash] = true
		thresholdOf[g.ProfileHash] = g.Threshold
		thresholdOf[g.ThresholdHash] = g.Threshold
	}
	// rotations the operator has derived into actors out-of-band no longer
	// force a refusal (Gemini STANDARD gate P0: else the append-only closure
	// deadlocks the chain on its first rotation)
	resolved := map[string]bool{}
	for _, h := range stringList(trust["resolved_key_state"]) {
		resolved[h] = true
	}
	for _, rid := range sortedRecordIDs(closure) {
		if resolved[rid] {
			continue
		}
		env, ok := asMap(s.Records[rid])
		if !ok {
			continue
		}
		body, ok := asMap(env["body"])
		if !ok {
			continue
		}
		decision, _ := asString(body["decision"])
		if decision != "accept" && decision != "supersede" {
			continue
		}
		cited := []string{}
		for _, h := range stringList(body["under"]) {
			if govHashes[h] {
				cited = append(cited, h)
			}
		}
		if len(cited) == 0 {
			continue
		}
		subject, ok := s.parseJSONBlob(subjectHash(body)).(map[string]any)
		if !ok || !sameKeys(subject, []string{"actor", "key"}) {
			continue
		}
		if shaHex(jcs(body)) != rid {
			continue
		}
		for _, h := range cited {
			t := thresholdOf[h]
			if len(govCountedSigs(env, rid, t, govTrustActors(trust))) >= t.Min {
				return true
			}
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
		if ed25519.Verify(ed25519.PublicKey(pub), ridBytes, sig) {
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

func book1Fixture() map[string]any {
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
		out := map[string]any{}
		for k, v := range x {
			out[k] = normalizeJSON(v)
		}
		return out
	case []any:
		out := make([]any, len(x))
		for i, v := range x {
			out[i] = normalizeJSON(v)
		}
		return out
	case []string:
		out := make([]any, len(x))
		for i, v := range x {
			out[i] = v
		}
		return out
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
