#!/usr/bin/env python3
"""Prepare bounded AE JSX batches and summarize native result files; stdlib only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import uuid
from cli_output import configure_stdout

VERSION = "ae-basic.v1"
ROOT = Path(__file__).resolve().parent
TRANSFORMS = {"position", "anchor_point", "scale", "rotation", "opacity"}
CATALOG = {
    "inspect": "Read the current project and active composition; no project mutation.",
    "create_comp": "name,width,height,fps,duration; optional ref. Creates a new composition.",
    "set_comp": "comp,changes={background_color:[r,g,b]}; changes the composition background, not an opaque layer.",
    "add_null": "comp,name; optional ref,three_d. Adds a null to the target composition.",
    "add_text": "comp,name,text; optional ref,font_size,color. Adds a text layer.",
    "set_layer": "comp,layer; changes object with name and/or enabled.",
    "set_transform": "comp,layer; values object: position,anchor_point,scale,rotation,opacity.",
    "set_keyframes": "comp,layer,property,keys=[{time,value}]; optional interpolation linear|hold.",
}


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("JSON input exceeds 2 MB; use a bounded snapshot/job")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def number(value, label, low=None, high=None, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: finite number required")
    if integer and (not isinstance(value, int)):
        raise ValueError(f"{label}: integer required")
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f"{label}: outside supported range")
    return value


def text(value, label, limit=120):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError(f"{label}: nonempty text of at most {limit} characters required")
    return value


def exact(data, required, optional=()):
    if not isinstance(data, dict) or set(data) - set(required) - set(optional) or not set(required) <= set(data):
        raise ValueError(f"Expected keys {sorted(required)}; optional {sorted(optional)}")


def transform_value(prop, value, dims=None):
    if prop not in TRANSFORMS:
        raise ValueError("Unsupported transform property")
    if prop in {"rotation", "opacity"}:
        return number(value, prop, 0 if prop == "opacity" else -360000, 100 if prop == "opacity" else 360000)
    if not isinstance(value, list) or len(value) not in (2, 3) or (dims is not None and len(value) != dims):
        raise ValueError(f"{prop}: target requires {dims or '2 or 3'} vector components")
    return [number(x, prop, -1_000_000, 1_000_000) for x in value]


def check_snapshot(raw):
    if not isinstance(raw, dict) or raw.get("schema") != VERSION or raw.get("status") != "ok":
        raise ValueError("Expected a successful native AE result, not a Python plan")
    snap = raw.get("snapshot")
    if not isinstance(snap, dict) or not all(isinstance(snap.get(x), str) and snap[x] for x in ("session", "signature")):
        raise ValueError("Native result has no usable project snapshot")
    if not isinstance(snap.get("layers"), list) or not isinstance(snap.get("project_items"), int):
        raise ValueError("Invalid native snapshot")
    return snap


def validate_plan(raw, snapshot):
    exact(raw, {"actions"})
    actions = raw["actions"]
    if not isinstance(actions, list) or not 1 <= len(actions) <= 32:
        raise ValueError("Batch needs 1 to 32 actions")
    refs = {}
    active = snapshot.get("active_comp")
    native_layers = {row["id"]: dict(row) for row in snapshot["layers"]}
    validated = []

    def comp_info(target):
        if isinstance(target, str) and target.startswith("@"):
            info = refs.get(target[1:])
            if not info or info["kind"] != "comp":
                raise ValueError("Unknown or forward composition reference")
            return info
        number(target, "comp", 1, integer=True)
        if not active or target != active["id"]:
            raise ValueError("Existing target must be the inspected active composition ID")
        return {"kind": "comp", **active}

    def layer_info(target, comp):
        if isinstance(target, str) and target.startswith("@"):
            row = refs.get(target[1:])
            if not row or row["kind"] != "layer" or row["comp"] != comp:
                raise ValueError("Unknown, forward or cross-composition layer reference")
            return row
        number(target, "layer", 1, integer=True)
        if not active or comp != active["id"] or target not in native_layers:
            raise ValueError("Layer ID is absent from the inspected composition")
        row = native_layers[target]
        if row.get("locked"):
            raise ValueError("Target layer is locked")
        return row

    def add_ref(action, info):
        ref = action.get("ref")
        if ref is not None:
            if not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", ref) or ref in refs:
                raise ValueError("ref must be a unique short identifier")
            refs[ref] = info

    for original in actions:
        if not isinstance(original, dict) or original.get("op") not in CATALOG or original["op"] == "inspect":
            raise ValueError("Unknown action; use prepare-inspect for inspection")
        action = dict(original)
        op = action["op"]
        if op == "create_comp":
            exact(action, {"op", "name", "width", "height", "fps", "duration"}, {"ref"})
            text(action["name"], "name")
            for dimension in ("width", "height"):
                number(action[dimension], dimension, 4, 16000, integer=True)
            number(action["fps"], "fps", 1, 120)
            number(action["duration"], "duration", 1/120, 10800)
            add_ref(action, {"kind": "comp", **{k: action[k] for k in ("width", "height", "fps", "duration")}})
        elif op in {"add_null", "add_text"}:
            required = {"op", "comp", "name"} | ({"text"} if op == "add_text" else set())
            optional = {"ref", "three_d"} if op == "add_null" else {"ref", "font_size", "color"}
            exact(action, required, optional)
            comp_info(action["comp"])
            text(action["name"], "name")
            if op == "add_null":
                if "three_d" in action and not isinstance(action["three_d"], bool):
                    raise ValueError("three_d must be boolean")
            else:
                text(action["text"], "text", 4000)
                if "font_size" in action:
                    number(action["font_size"], "font_size", 1, 1296)
                if "color" in action:
                    color = action["color"]
                    if not isinstance(color, list) or len(color) != 3:
                        raise ValueError("color needs three RGB channels in [0,1]")
                    for x in color:
                        number(x, "color", 0, 1)
            add_ref(action, {"kind": "layer", "comp": action["comp"], "three_d": action.get("three_d", False)})
        elif op == "set_comp":
            exact(action, {"op", "comp", "changes"})
            comp_info(action["comp"])
            exact(action["changes"], {"background_color"})
            color = action["changes"]["background_color"]
            if not isinstance(color, list) or len(color) != 3:
                raise ValueError("background_color needs RGB channels in [0,1]")
            for x in color:
                number(x, "background_color", 0, 1)
        else:
            required = {"op", "comp", "layer"}
            required |= {"changes"} if op == "set_layer" else {"values"} if op == "set_transform" else {"property", "keys"}
            exact(action, required, {"interpolation"} if op == "set_keyframes" else set())
            info = comp_info(action["comp"])
            layer = layer_info(action["layer"], action["comp"])
            dims = 3 if layer.get("three_d") else 2
            if op == "set_layer":
                changes = action["changes"]
                if not isinstance(changes, dict) or not changes or set(changes)-{"name", "enabled"}:
                    raise ValueError("changes supports only name and enabled")
                if "name" in changes:
                    text(changes["name"], "name")
                if "enabled" in changes and not isinstance(changes["enabled"], bool):
                    raise ValueError("enabled must be boolean")
            elif op == "set_transform":
                values = action["values"]
                if not isinstance(values, dict) or not values or set(values)-TRANSFORMS:
                    raise ValueError("Unsupported or empty transform values")
                for prop, value in values.items():
                    transform_value(prop, value, dims)
                    if prop in layer.get("animated", []) or prop in layer.get("expressions", []):
                        raise ValueError("set_transform will not replace animation or expressions")
            else:
                prop = action["property"]
                if prop not in TRANSFORMS or prop in layer.get("expressions", []):
                    raise ValueError("Unsupported property or existing expression")
                keys = action["keys"]
                if not isinstance(keys, list) or not 1 <= len(keys) <= 200:
                    raise ValueError("keys needs 1 to 200 samples")
                previous = -1
                for key in keys:
                    exact(key, {"time", "value"})
                    t = number(key["time"], "time", 0, info["duration"])
                    if t <= previous:
                        raise ValueError("Key times must be strictly increasing")
                    previous = t
                    transform_value(prop, key["value"], dims)
                if action.get("interpolation", "linear") not in ("linear", "hold"):
                    raise ValueError("Only linear or hold interpolation is supported")
                layer["animated"] = sorted(set(layer.get("animated", [])) | {prop})
        validated.append(action)
    return validated


def emit(job, destination):
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise ValueError("Output folder must be new; each native run has its own receipt")
    payload = json.dumps(job, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    source = (ROOT/"ae_runtime.jsx").read_text(encoding="utf-8")
    if source.count("/*__AE_BASIC_JOB__*/") != 1:
        raise ValueError("Runtime template is invalid")
    source = source.replace("/*__AE_BASIC_JOB__*/", payload)
    destination.mkdir(parents=True)
    (destination/"job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (destination/"run.jsx").write_text(source, encoding="utf-8")
    return {"status": "prepared", "executed": False, "job_id": job["job_id"], "actions": len(job["actions"]),
            "jsx": str(destination/"run.jsx"), "result": str(destination/"result.json"),
            "jsx_sha256": hashlib.sha256(source.encode()).hexdigest()}


def summarize(raw):
    if not isinstance(raw, dict) or raw.get("schema") != VERSION:
        raise ValueError("Not an AE basic result")
    snap = raw.get("snapshot", {})
    layers = snap.get("layers", [])
    selected = [row for row in layers if row.get("selected")]
    rows = selected if selected else layers[:6]
    compact_actions = []
    for action in raw.get("actions", []):
        row = {k: v for k, v in action.items() if k not in {"keys", "text"}}
        if "keys" in action:
            keys = action["keys"]
            row.update(key_count=len(keys), first_key=keys[0] if keys else None, last_key=keys[-1] if keys else None)
        if "text" in action:
            row["text_length"] = len(action["text"])
        compact_actions.append(row)
    return {"status": raw.get("status"), "job_id": raw.get("job_id"), "native_AE": raw.get("ae_version"),
            "actions_completed": len(raw.get("actions", [])), "error": raw.get("error"),
            "active_comp": snap.get("active_comp"), "layer_count": len(layers),
            "layers": [{k: row[k] for k in ("id", "name", "three_d", "locked", "selected", "animated", "expressions") if k in row} for row in rows[:12]],
            "omitted_layers": len(layers)-min(len(rows), 12), "action_results": compact_actions}


def equal_value(expected, actual):
    if isinstance(expected, bool) or isinstance(expected, str):
        return type(actual) is type(expected) and expected == actual
    if isinstance(expected, (int, float)):
        return not isinstance(actual, bool) and isinstance(actual, (int, float)) and math.isfinite(actual) and abs(expected-actual) < 0.0001
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(equal_value(a, b) for a, b in zip(expected, actual))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and equal_value(v, actual[k]) for k, v in expected.items())
    return expected is None and actual is None


def verify_receipt(raw, job):
    if raw.get("schema") != VERSION or raw.get("job_id") != job.get("job_id"):
        raise ValueError("Native receipt does not match this job")
    if raw.get("status") != "ok":
        return False
    check_snapshot(raw)
    results = raw.get("actions")
    if not isinstance(results, list) or len(results) != len(job["actions"]):
        raise ValueError("Native action count differs from the plan")
    refs = {}
    for expected, actual in zip(job["actions"], results):
        op = expected["op"]
        if actual.get("op") != op:
            raise ValueError("Native operation order differs from the plan")
        wanted = {}
        if op == "create_comp":
            wanted = {k: expected[k] for k in ("name", "width", "height", "fps", "duration")}
            created_id = actual.get("comp_id")
        elif op in {"add_null", "add_text"}:
            wanted = {"name": expected["name"], "three_d": expected.get("three_d", False)}
            if op == "add_text":
                wanted["text"] = expected["text"]
                for k in ("font_size", "color"):
                    if k in expected:
                        wanted[k] = expected[k]
            created_id = actual.get("layer_id")
        elif op in {"set_comp", "set_layer"}:
            wanted = expected["changes"]
        elif op == "set_transform":
            wanted = {"values": expected["values"]}
        else:
            wanted = {"property": expected["property"], "keys": expected["keys"], "interpolation": expected.get("interpolation", "linear")}
        if op != "create_comp":
            for field, native_field in (("comp", "comp_id"), ("layer", "layer_id")):
                if field in expected:
                    target = expected[field]
                    wanted[native_field] = refs.get(target[1:]) if isinstance(target, str) else target
        if not equal_value(wanted, actual):
            raise ValueError(f"Native readback differs from requested {op}")
        if "ref" in expected:
            number(created_id, "native created ID", 1, integer=True)
            refs[expected["ref"]] = created_id
    return True


def main(argv=None):
    configure_stdout()
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    cat = sub.add_parser("catalog"); cat.add_argument("--op", choices=list(CATALOG))
    inspect = sub.add_parser("prepare-inspect"); inspect.add_argument("--out", type=Path, required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--input", type=Path, required=True); prepare.add_argument("--snapshot", type=Path, required=True); prepare.add_argument("--out", type=Path, required=True)
    result = sub.add_parser("result"); result.add_argument("path", type=Path)
    a = p.parse_args(argv)
    try:
        if a.command == "catalog":
            value = {"schema": VERSION, "operations": {a.op: CATALOG[a.op]} if a.op else CATALOG}
        elif a.command == "result":
            raw = read_json(a.path)
            verified = verify_receipt(raw, read_json(a.path.parent/"job.json"))
            value = summarize(raw)
            value["native_readback_verified"] = verified
        else:
            job = {"schema": VERSION, "job_id": uuid.uuid4().hex, "actions": []}
            if a.command == "prepare-inspect":
                job["inspect_only"] = True
            else:
                snap = check_snapshot(read_json(a.snapshot))
                job["guard"] = {"session": snap["session"], "signature": snap["signature"]}
                job["actions"] = validate_plan(read_json(a.input), snap)
            value = emit(job, a.out)
        print(json.dumps(value, ensure_ascii=False, allow_nan=False))
        return 1 if value.get("status") in {"failed", "partial"} else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "executed": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
