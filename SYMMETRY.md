# Symmetry — what must change in both implementations at once

**Why this file exists.** Across four review rounds in one day, the same mistake
recurred: a defect was fixed where the reviewer pointed, and its mirror in the
other implementation was left. Not once — four times, twice in the same function.

| round | fixed | missed |
|---|---|---|
| 1 | blank repertoire, both sides | — |
| 2 | `_is_uint` narrowed | `view_id()` never called it |
| 3 | `view_id()` in Python | `cmdViewID` in Go |
| 4 | — | (caught before commit) |

Each was found by an external reviewer, not by the suite, and each was cheap to
find once someone looked in the obvious second place. The pattern is not
carelessness about correctness; it is a blind spot about *scope*: after fixing a
thing, the mind treats the thing as fixed. A checklist beats a resolution.

This file is that checklist. It is prose, not a gate — an honest label, since a
Markdown file cannot enforce anything and pretending otherwise would be the same
defect one level up.

---

## The paired surfaces

Any change to one column must be considered for the other, in the same commit.

| concern | Python | Go |
|---|---|---|
| blank repertoire | `BLANK_CODE_POINTS`, `_is_blank` | `blankCodePoints`, `isBlank` |
| integer domain | `JCS_SAFE_INT_MAX`, `_is_uint` | `jcsSafeIntMax`, `uintValue` |
| assertion schema | `validate_assertion` | `validateAssertion` |
| policy schema | `validate_policy` | `validatePolicy` |
| candidate liveness | `_valid_metadata` | `validMetadata` |
| selection | `select` | `selectCandidates`, `cmdSelect` |
| **identity** | `view_id` | `viewID`, `cmdViewID` |
| set commitment | `assertion_set_root` | `cmdSetRoot` |
| I-JSON boundary | `parse_request`, `non_ijson` | `rejectNonIJSON`, `rejectDuplicateNames` |
| ordering | `_cmp_order` | `compareOrder` |

`view_id` is bolded because it is the one that broke twice. It is the identity
function: whatever domain it accepts *is* the domain, whatever the validators say.

## Before committing a cross-implementation fix

1. **Is there a mirror?** Find the row above. If the change touches one column and
   not the other, say why in the commit message — "not needed" is an acceptable
   answer, "did not look" is what this list exists to prevent.
2. **Does a test go red with the fix removed from Python only?**
3. **Does a test go red with the fix removed from Go only?**
   Both, separately. A suite that can only fail for one of the two
   implementations it covers is half a suite — `tests/ijson_raw_bytes.py` was
   exactly that for one commit.
4. **Can both sides be given the same input?** If the test constructs objects for
   one and bytes for the other, it is not testing that they agree; it is testing
   two things. `parse_request` exists so this is possible for requests.
5. **Did a normative rule change?** Then `spec/ANCHORS.txt` no longer matches, and
   adoption is a threshold warrant under GOV-anchors — not an agent's commit.
6. **Does the new rule compile?** A MUST that no check enforces is the defect this
   project is about. If nothing can go red, the rule is a wish.

## What this does not cover

Rust (`impl-rs`) implements Book I only — no federation, no selection, no
identity coordinates — so it has no row here. If that changes, this table does.

The list is maintained by hand and will drift. Its value is the habit, not the
completeness; when a row is found missing, the finding belongs in a commit
message before it belongs here.
