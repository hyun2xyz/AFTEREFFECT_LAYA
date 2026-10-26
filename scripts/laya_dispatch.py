#!/usr/bin/env python3
"""Keep explicit AE requests separate from the existing Laya CLI. No shell/eval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import unicodedata
from cli_output import configure_stdout

SCHEMA = "ae-basic-laya.dispatch.v1"
AE_PREFIXES = ("컴포지션", "배경", "텍스트", "널", "3D 널", "선택 레이어", "현재 상태")


def read_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Unsupported Laya dispatch config")
    for key in ("ae_argv", "legacy_argv"):
        argv = data.get(key)
        if (not isinstance(argv, list) or len(argv) < 2
                or any(not isinstance(value, str) or not value or "\0" in value for value in argv)
                or not Path(argv[0]).is_absolute()):
            raise ValueError(f"{key} must be an argv list starting with an absolute executable")
    return data


def command(config, arguments):
    arguments = list(arguments)
    if arguments and arguments[0] == "ae":
        return [*config["ae_argv"], *arguments[1:]]
    text = unicodedata.normalize("NFC", " ".join(" ".join(arguments).split()))
    if any(text.startswith(prefix) for prefix in AE_PREFIXES):
        return [*config["ae_argv"], *arguments]
    return [*config["legacy_argv"], *arguments]


def main(argv=None):
    configure_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="-- followed by the original Laya arguments")
    args = parser.parse_args(argv)
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    try:
        # A terminal error remains a terminal error; never retry it through legacy.
        return subprocess.run(command(read_config(args.config), arguments), check=False).returncode
    except (OSError, ValueError) as exc:
        print(f"Laya dispatch error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
