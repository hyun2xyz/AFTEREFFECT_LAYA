#!/usr/bin/env python3
"""Stdlib-only project preparation and AE path checks; never launches AE.

--check is read-only. --prepare creates only ROOT/.venv, without pip/packages.
--configure --app ABS writes only ROOT/tools.local.json after static validation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os
import venv

# Importing the local terminal must not create project caches during --check.
sys.dont_write_bytecode = True
from cli_output import configure_stdout
import terminal

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {(3, 12), (3, 13)}


def venv_python(root):
    return Path(root)/".venv"/("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_status(root):
    root = Path(root).expanduser().resolve()
    directory, python = root/".venv", venv_python(root)
    result = {"path": str(directory), "python": str(python), "exists": directory.exists(), "ready": False}
    if directory.is_symlink() or directory.resolve() != directory:
        return {**result, "error": "A linked/foreign .venv is preserved; use a project-owned environment"}
    if not directory.exists():
        return {**result, "error": "Project .venv is missing; use --prepare with Python 3.13 or 3.12"}
    if not (directory/"pyvenv.cfg").is_file() or not python.is_file():
        return {**result, "error": "Existing .venv is incomplete; preserve and inspect it before retrying"}
    try:
        config = dict(line.split("=", 1) for line in (directory/"pyvenv.cfg").read_text(encoding="utf-8-sig").splitlines() if "=" in line)
        config = {key.strip(): value.strip() for key, value in config.items()}
        if config.get("include-system-site-packages", "").lower() != "false":
            raise ValueError("Existing .venv is not isolated from system packages")
        code = "import json,sys;print(json.dumps({'version':list(sys.version_info[:3]),'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"
        completed = subprocess.run([str(python), "-I", "-B", "-c", code], check=True, capture_output=True,
                                   encoding="utf-8", errors="strict", timeout=15)
        data = json.loads(completed.stdout)
        if Path(data["prefix"]).resolve() != directory or data["prefix"] == data["base_prefix"]:
            raise ValueError("Interpreter does not belong to this project's .venv")
        supported = tuple(data["version"][:2]) in SUPPORTED
        result.update(version=data["version"], supported_python=supported, ready=supported)
        if not supported:
            result["error"] = "Existing .venv uses unsupported Python; preserve it and select Python 3.13 or 3.12"
        return result
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        return {**result, "error": str(exc)}


def app_path(explicit=None):
    if sys.platform not in {"darwin", "win32"}:
        raise ValueError("Native AE needs macOS or native Windows Python/PowerShell, not WSL")
    if explicit is not None and not Path(explicit).expanduser().is_absolute():
        raise ValueError("--app must be an absolute native AE application path")
    path = Path(terminal.find_app(explicit))
    if "render engine" in path.name.casefold():
        raise ValueError("Select the full After Effects app, not Render Engine")
    return path


def check(root=ROOT, app=None):
    environment = venv_status(root)
    ae = {"native_verified": False}
    try:
        ae.update(path=str(app_path(app)), path_checked=True)
    except (OSError, ValueError, TypeError) as exc:
        ae.update(path=None, path_checked=False, error=str(exc))
    return {"schema": "aftereffect-laya.setup.v1", "root": str(Path(root).resolve()),
            "os": {"name": sys.platform, "native_supported": sys.platform in {"darwin", "win32"}},
            "python": {"path": sys.executable, "version": ".".join(map(str, sys.version_info[:3])), "supported": sys.version_info[:2] in SUPPORTED},
            "venv": environment, "after_effects": ae, "base_dependencies": "Python standard library only; no pip packages",
            "ready_for_dry_run": environment["ready"], "ready": environment["ready"] and ae["path_checked"],
            "native_ae": "not_verified", "note": "App path detection does not verify license, version, permissions or native execution"}


def prepare(root=ROOT):
    root = Path(root).expanduser().resolve()
    directory = root/".venv"
    existed = directory.exists() or directory.is_symlink()
    if not existed:
        if sys.version_info[:2] not in SUPPORTED:
            raise ValueError("Use Python 3.13 (recommended) or 3.12 before creating this environment")
        venv.EnvBuilder(with_pip=False).create(directory)
    state = venv_status(root)
    if not state["ready"]:
        raise ValueError("Environment preserved; no clear/upgrade attempted: "+state.get("error", "unknown environment state"))
    return {"prepared": True, "reused": existed, "venv": state, "packages_installed_by_helper": False, "native_ae": "not_verified"}


def configure(root, app):
    root = Path(root).expanduser().resolve()
    selected = app_path(app)  # Validate first; invalid input must not replace config.
    path = root/"tools.local.json"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Existing tools.local.json is not a regular file; preserve and inspect it")
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(old, dict) or set(old)-{"ae_app"} or ("ae_app" in old and not isinstance(old["ae_app"], str)):
            raise ValueError("Existing tools.local.json has unrelated/invalid settings; no file changed")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, prefix=".tools-local-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({"ae_app": str(selected)}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"configured": True, "config": str(path), "ae_app": str(selected), "native_ae": "not_verified"}


def main(argv=None, root=ROOT):
    configure_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="read-only inspection (default)")
    action.add_argument("--prepare", action="store_true", help="create/reuse only this folder's .venv, without pip")
    action.add_argument("--configure", action="store_true", help="write a validated native app path")
    parser.add_argument("--app", type=Path, help="absolute .app path on Mac or actual AfterFX.exe on Windows")
    args = parser.parse_args(argv)
    if args.configure and args.app is None:
        parser.error("--configure requires --app ABS")
    if args.prepare and args.app is not None:
        parser.error("Use --configure --app ABS separately from --prepare")
    try:
        result = prepare(root) if args.prepare else configure(root, args.app) if args.configure else check(root, args.app)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("prepared") or result.get("configured") or result.get("ready") else 1
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        # Escaped JSON remains readable even if stderr has a legacy Windows codec.
        print(json.dumps({"error": str(exc), "native_ae": "not_verified"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
