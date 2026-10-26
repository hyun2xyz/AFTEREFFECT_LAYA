#!/usr/bin/env python3
"""Reversible user-local laya-ae launcher; zsh Laya integration is opt-in.

Default/--check only inspect a plan. --install backs up every changed file before
writing. --restore RECEIPT reverses that exact installation without losing edits.
No package/model download, global PATH changes, legacy source edits or AE calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import sys
import tempfile
import uuid
from cli_output import configure_stdout

SCRIPT_DIR = Path(__file__).resolve().parent
BEGIN = b"# >>> ae-basic-laya terminal integration >>>"
END = b"# <<< ae-basic-laya terminal integration <<<"
RECEIPT_SCHEMA = "ae-basic-laya.terminal-install.v1"


def absolute(value):
    return Path(os.path.abspath(Path(value).expanduser()))


def executable(value):
    path = absolute(shutil.which(str(value)) or value)
    if (not path.is_file() or path.suffix.lower() in {".bat", ".cmd"}
            or (os.name != "nt" and not os.access(path, os.X_OK))):
        raise ValueError(f"Use an actual existing Python executable: {path}")
    return path


def script(value, label):
    path = Path(value).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"{label} must be an existing absolute script path")
    return absolute(path)


def cmd_quote(value):
    value = str(value)
    if any(char in value for char in ('"', "\r", "\n", "\0")):
        raise ValueError("Windows launcher paths cannot contain quotes or newlines")
    return '"'+value.replace("%", "%%")+'"'


def launcher(python, terminal, windows=False):
    if windows:
        # Decode Unicode paths as UTF-8, then restore the caller's code page.
        return ("@echo off\r\nsetlocal DisableDelayedExpansion\r\n"
                +"for /f \"tokens=2 delims=:\" %%C in ('chcp') do set \"LAYA_AE_OLD_CP=%%C\"\r\n"
                +"chcp 65001 >nul\r\n"+cmd_quote(python)+" -B "+cmd_quote(terminal)+" %*\r\n"
                +"set \"LAYA_AE_EXIT=%errorlevel%\"\r\n"
                +"if defined LAYA_AE_OLD_CP chcp %LAYA_AE_OLD_CP% >nul\r\n"
                +"exit /b %LAYA_AE_EXIT%\r\n").encode("utf-8")
    return ("#!/bin/sh\nexec "+shlex.quote(str(python))+" -B "+shlex.quote(str(terminal))+" \"$@\"\n").encode("utf-8")


def shell_content(original, python, dispatcher, config):
    """Replace only one complete managed block, preserving all other bytes."""
    lines = original.splitlines(keepends=True)
    starts, ends = [], []
    for i, line in enumerate(lines):
        plain = line.rstrip(b"\r\n")
        if b">>> ae-basic-laya" in line or b"<<< ae-basic-laya" in line:
            if plain == BEGIN:
                starts.append(i)
            elif plain == END:
                ends.append(i)
            else:
                raise ValueError("Malformed ae-basic-laya shell marker; no file changed")
    if len(starts) != len(ends) or len(starts) > 1 or (starts and starts[0] >= ends[0]):
        raise ValueError("Duplicate or incomplete ae-basic-laya shell markers; no file changed")
    invocation = " ".join(shlex.quote(str(value)) for value in (python, "-B", dispatcher, "--config", config))
    block = BEGIN+b"\nunalias laya 2>/dev/null || true\nfunction laya() {\n  "+invocation.encode("utf-8")+b' -- "$@"\n}\n'+END+b"\n"
    if starts:
        return b"".join(lines[:starts[0]])+block+b"".join(lines[ends[0]+1:])
    return original+(b"\n" if original and not original.endswith(b"\n") else b"")+block


def snapshot(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Refusing to replace a symlink or non-file: {path}")
    return (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else (None, None)


def digest(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".laya-ae-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_plan(args, scripts=SCRIPT_DIR, windows=None):
    windows = os.name == "nt" if windows is None else windows
    python = executable(args.python)
    terminal = script(scripts/"terminal.py", "terminal.py")
    target = absolute(args.bin_dir)/("laya-ae.cmd" if windows else "laya-ae")
    files = {target: (launcher(python, terminal, windows), 0o755)}
    if args.integrate_laya:
        if windows:
            raise ValueError("Laya shell integration requires Unix zsh; use laya-ae.cmd on Windows")
        if not args.legacy_script or not args.legacy_python:
            raise ValueError("--integrate-laya requires --legacy-script ABS and --legacy-python PATH")
        legacy = [str(executable(args.legacy_python)), str(script(args.legacy_script, "legacy script"))]
        dispatcher = script(scripts/"laya_dispatch.py", "laya_dispatch.py")
        config = absolute(args.config_dir)/"laya-dispatch.json"
        payload = {"schema": "ae-basic-laya.dispatch.v1", "ae_argv": [str(python), "-B", str(terminal)], "legacy_argv": legacy}
        files[config] = ((json.dumps(payload, ensure_ascii=False, indent=2)+"\n").encode("utf-8"), 0o600)
        shell = absolute(args.shell_file)
        if shell in files:
            raise ValueError("Installer target paths must be distinct")
        original, mode = snapshot(shell)
        files[shell] = (shell_content(original or b"", python, dispatcher, config), mode if mode is not None else 0o600)
    elif args.legacy_script or args.legacy_python:
        raise ValueError("Legacy options require --integrate-laya")
    plan = []
    for path, (data, mode) in files.items():
        original, old_mode = snapshot(path)
        plan.append({"path": path, "data": data, "mode": mode, "original": original, "old_mode": old_mode,
                     "changed": original != data or (not windows and old_mode != mode)})
    if len({entry["path"].resolve() for entry in plan}) != len(plan):
        raise ValueError("Installer target paths must be distinct")
    return plan


def apply(plan, backup_dir):
    changes = [entry for entry in plan if entry["changed"]]
    if not changes:
        return {"status": "unchanged", "paths": [str(entry["path"]) for entry in plan]}
    folder = absolute(backup_dir)/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, mode=0o700)
    entries = []
    for i, item in enumerate(changes):
        backup = None
        if item["original"] is not None:
            backup = f"{i:02d}.bak"
            atomic_write(folder/backup, item["original"], 0o600)
        entries.append({"path": str(item["path"]), "backup": backup, "before_sha256": digest(item["original"]),
                        "after_sha256": digest(item["data"]), "before_mode": item["old_mode"], "after_mode": item["mode"]})
    receipt = folder/"receipt.json"
    atomic_write(receipt, (json.dumps({"schema": RECEIPT_SCHEMA, "entries": entries}, indent=2)+"\n").encode("utf-8"), 0o600)
    written = []
    try:
        for item in changes:
            if snapshot(item["path"]) != (item["original"], item["old_mode"]):
                raise ValueError(f"File changed during installation: {item['path']}")
            atomic_write(item["path"], item["data"], item["mode"])
            written.append(item)
    except Exception:
        for item in reversed(written):
            if digest(snapshot(item["path"])[0]) == digest(item["data"]):
                if item["original"] is None:
                    item["path"].unlink()
                else:
                    atomic_write(item["path"], item["original"], item["old_mode"])
        raise
    return {"status": "installed", "paths": [str(item["path"]) for item in changes], "receipt": str(receipt)}


def restore(receipt):
    receipt = absolute(receipt)
    data = json.loads(receipt.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema") != RECEIPT_SCHEMA or not isinstance(data.get("entries"), list):
        raise ValueError("Unsupported installer receipt")
    plan = []
    for entry in data["entries"]:
        path = Path(entry["path"])
        if not path.is_absolute():
            raise ValueError("Receipt target must be absolute")
        current, mode = snapshot(path)
        if digest(current) != entry["after_sha256"] or (os.name != "nt" and mode != entry["after_mode"]):
            raise ValueError(f"Target changed since installation; restore refused: {path}")
        backup = entry["backup"]
        if backup is not None and (not isinstance(backup, str) or Path(backup).name != backup):
            raise ValueError("Receipt backup must stay in its receipt directory")
        if backup is not None and (receipt.parent/backup).is_symlink():
            raise ValueError("Refusing a symlinked backup")
        original = (receipt.parent/backup).read_bytes() if backup is not None else None
        if digest(original) != entry["before_sha256"]:
            raise ValueError("Backup checksum mismatch; no file changed")
        if original is not None and (not isinstance(entry["before_mode"], int) or not 0 <= entry["before_mode"] <= 0o7777):
            raise ValueError("Invalid original file mode in receipt")
        plan.append((path, original, entry["before_mode"]))
    for path, original, mode in plan:
        if original is None:
            path.unlink()
        else:
            atomic_write(path, original, mode)
    return {"status": "restored", "paths": [str(path) for path, _, _ in plan], "receipt": str(receipt)}


def parser():
    config_home = Path(os.environ.get("LOCALAPPDATA", Path.home()/"AppData/Local")) if os.name == "nt" else Path(os.environ.get("XDG_CONFIG_HOME", Path.home()/".config"))
    config = config_home/"ae-basic-laya"
    result = argparse.ArgumentParser(description=__doc__)
    action = result.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="read-only plan (also the default)")
    action.add_argument("--install", action="store_true", help="back up and apply the plan")
    action.add_argument("--restore", type=Path, metavar="RECEIPT", help="restore exact unchanged targets from one receipt")
    result.add_argument("--python", default=sys.executable)
    result.add_argument("--bin-dir", type=Path, default=config/"bin" if os.name == "nt" else Path.home()/".local/bin")
    result.add_argument("--shell-file", type=Path, default=Path.home()/".zshrc")
    result.add_argument("--config-dir", type=Path, default=config)
    result.add_argument("--backup-dir", type=Path)
    result.add_argument("--integrate-laya", action="store_true")
    result.add_argument("--legacy-script", type=Path)
    result.add_argument("--legacy-python")
    return result


def main(argv=None):
    configure_stdout()
    args = parser().parse_args(argv)
    try:
        if args.restore:
            if args.integrate_laya or args.legacy_script or args.legacy_python:
                raise ValueError("Do not combine restore with integration options")
            result = restore(args.restore)
        else:
            plan = build_plan(args)
            result = apply(plan, args.backup_dir or absolute(args.config_dir)/"backups") if args.install else {
                "status": "check", "read_only": True,
                "paths": [{"path": str(item["path"]), "would_change": item["changed"]} for item in plan]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Terminal installer error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
