package main

import (
	"encoding/json"
	"testing"
)

// jcs() MUST emit U+2028 / U+2029 as raw UTF-8, matching RFC 8785 (the anchored
// canonicalization, spec/GOV-anchors.md section 2) and the Python oracle's
// json.dumps(ensure_ascii=False). Go's encoding/json escapes them to   /
//   even with SetEscapeHTML(false); without the fix a governance record
// body carrying either character hashes to a different WarrantID under Go than
// under Python — a federation-consensus split (Kimi full-audit, 2026-07).
func TestJCSLineSeparatorsRaw(t *testing.T) {
	cases := []struct {
		name string
		in   map[string]any
		want string // exactly the JCS bytes Python json.dumps(ensure_ascii=False) yields
	}{
		{"u2028", map[string]any{"x": "a b"}, "{\"x\":\"a b\"}"},
		{"u2029", map[string]any{"x": "a b"}, "{\"x\":\"a b\"}"},
		{"both", map[string]any{"x": "  "}, "{\"x\":\"  \"}"},
		// control chars MUST stay escaped (RFC 8785 escapes U+0000..U+001F)
		{"tab_kept", map[string]any{"x": "a\tb"}, "{\"x\":\"a\\tb\"}"},
		{"backspace_kept", map[string]any{"x": "a\bb"}, "{\"x\":\"a\\bb\"}"},
		// an escaped backslash followed by the literal text u2028 MUST NOT be
		// mis-rewritten into the line separator: the atomic escape walk keeps it.
		{"literal_backslash_u2028", map[string]any{"x": "\\u2028"}, "{\"x\":\"\\\\u2028\"}"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := string(jcs(c.in))
			if got != c.want {
				t.Fatalf("jcs mismatch\n got: %q\nwant: %q", got, c.want)
			}
			var round map[string]any
			if err := json.Unmarshal([]byte(got), &round); err != nil {
				t.Fatalf("jcs output does not round-trip: %v", err)
			}
			if round["x"] != c.in["x"] {
				t.Fatalf("round-trip changed value: got %q want %q", round["x"], c.in["x"])
			}
		})
	}
}

// A body WITHOUT line separators must be byte-identical before and after the
// unescape pass (the fast path), so no existing vector shifts.
func TestJCSUnaffectedBodiesUnchanged(t *testing.T) {
	in := map[string]any{"warrant_id": "ab", "actor": "x@y", "note": "hello <&> world"}
	got := string(jcs(in))
	want := "{\"actor\":\"x@y\",\"note\":\"hello <&> world\",\"warrant_id\":\"ab\"}"
	if got != want {
		t.Fatalf("jcs mismatch\n got: %q\nwant: %q", got, want)
	}
}
