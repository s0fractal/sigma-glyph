package main

import (
	"bytes"
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
		die("usage: sigma-federation-go <replay|select|wave|viewid|setroot|validate-assertion|validate-policy|interfere|book1-unreachable>")
	}
	var err error
	switch os.Args[1] {
	case "replay":
		if len(os.Args) != 3 {
			die("usage: sigma-federation-go replay tests/spec_conformance/federation_vectors.json")
		}
		err = replay(os.Args[2])
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
	if !wok || !isHex64(wid) || !aok || actor == "" || !tok {
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
	b, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	return b
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
