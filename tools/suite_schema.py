#!/usr/bin/env python3
"""Check each conformance suite against its anchored schema.

    python3 tools/suite_schema.py
    python3 tools/suite_schema.py --selftest

A specification that declares a JSON artifact normative has to say what shape
that artifact has, or "the suite is normative" means only "the bytes we shipped
are the bytes we shipped". The Books used to gesture at `format_version`, which
names a version and defines nothing: it does not say which fields are required,
whether unknown fields are allowed, or what values an enum may take. Two
conforming checkers could disagree about whether a record was well-formed, and
therefore about whether the edition itself was conformant.

So the shape lives in `spec/schemas/*.json`, those files are anchored in
`spec/ANCHORS.txt` alongside the suites they describe, and this checks one
against the other. Closed-world throughout: `additionalProperties: false`
everywhere, so a suite cannot grow a field that means something to one reader and
nothing to another.

This implements the subset of JSON Schema the three schemas use, in the standard
library, on purpose. A validator that runs only where `pip install jsonschema`
has happened is a check whose subject can quietly become empty, which is the
defect class this repository exists to name. `--selftest` breaks each suite in a
way each rule should catch and requires every break to be caught, because a
validator nobody has seen fail is not evidence either.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SUITES = [
    ("tests/spec_conformance/vectors.json",
     "spec/schemas/book1-conformance.schema.json"),
    ("tests/spec_conformance/wave_vectors.json",
     "spec/schemas/book2-wave-conformance.schema.json"),
    ("tests/spec_conformance/federation_vectors.json",
     "spec/schemas/book3-federation-conformance.schema.json"),
]

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
         "number": (int, float), "integer": int, "null": type(None)}


def type_ok(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name in ("number",):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    expected = TYPES.get(name)
    if expected is None:
        return False
    if expected is dict or expected is list or expected is str:
        return isinstance(value, expected)
    return isinstance(value, expected)


def resolve(schema, root):
    seen = 0
    while "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"only local refs are supported, got {ref!r}")
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        schema = target
        seen += 1
        if seen > 32:
            raise ValueError("$ref cycle")
    return schema


def validate(value, schema, root, path, errors):
    schema = resolve(schema, root)

    if "oneOf" in schema:
        matches, attempts = [], []
        for index, option in enumerate(schema["oneOf"]):
            branch = []
            validate(value, option, root, path, branch)
            if not branch:
                matches.append(index)
            attempts.append((len(branch), resolve(option, root).get("title", ""),
                             option.get("$ref", ""), branch))
        if len(matches) != 1:
            errors.append(f"{path}: matches {len(matches)} of "
                          f"{len(schema['oneOf'])} alternatives, must match one")
            # Name the nearest miss, or a bare "matches 0 alternatives" sends a
            # reader back to diff the whole record against the whole schema.
            if not matches:
                _, _, ref, branch = min(attempts, key=lambda a: a[0])
                for problem in branch[:4]:
                    errors.append(f"    nearest ({ref.rsplit('/', 1)[-1]}): {problem}")
        return

    if "type" in schema:
        names = schema["type"]
        names = [names] if isinstance(names, str) else names
        if not any(type_ok(value, name) for name in names):
            errors.append(f"{path}: type is {type(value).__name__}, "
                          f"schema requires {'|'.join(names)}")
            return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: is {value!r}, schema requires {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not in the closed enum "
                      f"{schema['enum']}")
    if "pattern" in schema and isinstance(value, str):
        if re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: {value!r} does not match /{schema['pattern']}/")
    if "minLength" in schema and isinstance(value, str):
        if len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, dict):
        validate_object(value, schema, root, path, errors)
    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: {len(value)} items, minimum {schema['minItems']}")
        if "items" in schema:
            for index, item in enumerate(value):
                validate(item, schema["items"], root, f"{path}[{index}]", errors)


def validate_object(value, schema, root, path, errors):
    for name in schema.get("required", []):
        if name not in value:
            errors.append(f"{path}: required field {name!r} is missing")
    properties = schema.get("properties", {})
    for name, item in value.items():
        where = f"{path}.{name}" if path else name
        if "propertyNames" in schema:
            validate(name, schema["propertyNames"], root, f"{where} (key)", errors)
        if name in properties:
            validate(item, properties[name], root, where, errors)
            continue
        extra = schema.get("additionalProperties", True)
        if extra is False:
            errors.append(f"{where}: unknown field — this schema is closed")
        elif isinstance(extra, dict):
            validate(item, extra, root, where, errors)


def check(suite_path, schema_path):
    suite = json.loads((ROOT / suite_path).read_text())
    schema = json.loads((ROOT / schema_path).read_text())
    errors = []
    validate(suite, schema, schema, "", errors)
    return errors


def report(quiet=False):
    failures = 0
    for suite_path, schema_path in SUITES:
        errors = check(suite_path, schema_path)
        failures += len(errors)
        if not quiet:
            mark = "OK  " if not errors else "FAIL"
            print(f"  {mark}  {suite_path} against {Path(schema_path).name}"
                  + (f" — {len(errors)} problem(s)" if errors else ""))
            for problem in errors[:20]:
                print(f"        {problem}")
    return failures


# --------------------------------------------------------------------------
# The validator has to be shown failing, or it is decoration.
# --------------------------------------------------------------------------

def mutations(suite):
    """(name, mutated suite) pairs, each breaking exactly one schema rule."""
    def evals():
        return [v for v in suite["vectors"] if v.get("kind") == "eval"]

    out = []

    grown = json.loads(json.dumps(suite))
    grown["vectors"][0]["surprise"] = "an unknown field"
    out.append(("an unknown field on a vector (closed-world)", grown))

    grown = json.loads(json.dumps(suite))
    grown["surprise"] = 1
    out.append(("an unknown field at the top level", grown))

    dropped = json.loads(json.dumps(suite))
    dropped["vectors"][0].pop("note", None) or dropped["vectors"][0].pop("id", None)
    out.append(("a required field removed", dropped))

    retagged = json.loads(json.dumps(suite))
    retagged["format_version"] = 99
    out.append(("the declared format version changed", retagged))

    renamed = json.loads(json.dumps(suite))
    renamed["format"] = "something-else"
    out.append(("the declared format name changed", renamed))

    if evals():
        bad_exit = json.loads(json.dumps(suite))
        target = [v for v in bad_exit["vectors"] if v.get("kind") == "eval"][0]
        target["expected"]["exit"] = "invalid_object"
        out.append(("`invalid_object` used as a Receipt exit", bad_exit))

        bad_outcome = json.loads(json.dumps(suite))
        target = [v for v in bad_outcome["vectors"] if v.get("kind") == "eval"][0]
        target["expected"]["outcome"] = "EXHAUSTED"
        out.append(("an outcome spelling outside the enum", bad_outcome))

        bad_hash = json.loads(json.dumps(suite))
        target = [v for v in bad_hash["vectors"] if v.get("kind") == "eval"][0]
        target["expected"]["result_hash"] = target["expected"]["result_hash"].upper()
        out.append(("an uppercase result hash", bad_hash))

        bad_atp = json.loads(json.dumps(suite))
        target = [v for v in bad_atp["vectors"] if v.get("kind") == "eval"][0]
        target["expected"]["atp_spent"] = -1
        out.append(("a negative atp_spent", bad_atp))

        out_of_domain = json.loads(json.dumps(suite))
        target = [v for v in out_of_domain["vectors"] if v.get("kind") == "eval"][0]
        target["atp"] = 4294967296
        out.append(("a budget outside uint32", out_of_domain))
    return out


def selftest():
    problems = []
    for suite_path, schema_path in SUITES:
        suite = json.loads((ROOT / suite_path).read_text())
        schema = json.loads((ROOT / schema_path).read_text())
        errors = []
        validate(suite, schema, schema, "", errors)
        if errors:
            problems.append(f"{suite_path} does not validate as it stands; fix "
                            f"that before trusting any mutation result")
            continue
        for name, mutated in mutations(suite):
            broken = []
            validate(mutated, schema, schema, "", broken)
            mark = "OK  " if broken else "FAIL"
            print(f"  {mark}  {Path(suite_path).name}: {name}")
            if not broken:
                problems.append(f"{suite_path}: {name} was NOT caught")
    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    if problems:
        print(f"SUITE-SCHEMA-SELFTEST: {len(problems)} mutation(s) not caught")
        return 1
    print("SUITE-SCHEMA-SELFTEST: ALL PASS — every rule was shown rejecting "
          "something")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    failures = report()
    if failures:
        print(f"\nSUITE-SCHEMA: {failures} problem(s)")
        return 1
    print(f"\nSUITE-SCHEMA: ALL PASS ({len(SUITES)}/{len(SUITES)} suites match "
          f"their anchored schema)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
