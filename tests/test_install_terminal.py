"""Isolated terminal install/routing tests; no real shell config, legacy CLI or AE."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0, str(SCRIPTS))
import install_terminal as installer
import laya_dispatch as dispatch


class TerminalInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="laya's 한글 install ")
        self.root = Path(self.temp.name)
        self.scripts = self.root/"skill's scripts"
        self.scripts.mkdir()
        for filename, route in (("terminal.py", "ae"), ("legacy.py", "legacy")):
            (self.scripts/filename).write_text(
                "import json,sys\nprint(json.dumps({'route':"+repr(route)+",'args':sys.argv[1:]}))\n"
                "raise SystemExit(7 if '--fail' in sys.argv[1:] else 0)\n", encoding="utf-8")
        shutil.copy2(SCRIPTS/"laya_dispatch.py", self.scripts/"laya_dispatch.py")
        shutil.copy2(SCRIPTS/"cli_output.py", self.scripts/"cli_output.py")
        self.bin = self.root/"bin with spaces"
        self.config = self.root/"config with spaces"
        self.backups = self.root/"backups"
        self.shell = self.root/"shell's .zshrc"

    def tearDown(self):
        self.temp.cleanup()

    def args(self, integrate=True):
        values = ["--install", "--python", sys.executable, "--bin-dir", str(self.bin),
                  "--config-dir", str(self.config), "--shell-file", str(self.shell), "--backup-dir", str(self.backups)]
        if integrate:
            values += ["--integrate-laya", "--legacy-script", str(self.scripts/"legacy.py"), "--legacy-python", sys.executable]
        return installer.parser().parse_args(values)

    def plan(self):
        return installer.build_plan(self.args(), scripts=self.scripts)

    def config_file(self):
        path = self.root/"dispatch config 한글.json"
        payload = {"schema": dispatch.SCHEMA, "ae_argv": [sys.executable, "-B", str(self.scripts/"terminal.py")],
                   "legacy_argv": [sys.executable, str(self.scripts/"legacy.py")]}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def run_dispatch(self, arguments):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS/"laya_dispatch.py"), "--config", str(self.config_file()), "--", *arguments],
                                capture_output=True, encoding="utf-8", timeout=10)
        return result, json.loads(result.stdout)

    @unittest.skipIf(os.name == "nt", "Unix sh launcher")
    def test_unix_launcher_preserves_spaces_quotes_and_unicode_argv(self):
        (self.scripts/"cache_probe.py").write_text("value = 1\n", encoding="utf-8")
        terminal = self.scripts/"terminal.py"
        terminal.write_text("import cache_probe\n"+terminal.read_text(encoding="utf-8"), encoding="utf-8")
        python = self.root/"python's interpreter"
        python.symlink_to(sys.executable)
        target = self.root/"laya-ae"
        target.write_bytes(installer.launcher(python, self.scripts/"terminal.py"))
        target.chmod(0o755)
        arguments = ["--list", "한 글", "single'quote", 'double"quote', ""]
        result = subprocess.run([str(target), *arguments], capture_output=True, encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"route": "ae", "args": arguments})
        self.assertFalse((self.scripts/"__pycache__").exists())

    def test_windows_launcher_quotes_paths_and_preserves_codepage_exit(self):
        python = "C:\\한 글\\100% python\\python.exe"
        terminal = "C:\\skill's folder\\terminal.py"
        text = installer.launcher(python, terminal, windows=True).decode("utf-8")
        self.assertIn('"C:\\한 글\\100%% python\\python.exe" -B "C:\\skill\'s folder\\terminal.py" %*', text)
        self.assertIn("DisableDelayedExpansion", text)
        self.assertIn("chcp 65001", text)
        self.assertIn("chcp %LAYA_AE_OLD_CP%", text)
        self.assertIn("exit /b %LAYA_AE_EXIT%", text)
        with self.assertRaises(ValueError):
            installer.cmd_quote('C:\\invalid"path\\python.exe')

    def test_check_is_read_only_and_integration_defaults_off(self):
        self.shell.write_bytes(b"# preserve this file\n")
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = installer.main(["--check", "--bin-dir", str(self.bin), "--config-dir", str(self.config), "--shell-file", str(self.shell)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["read_only"])
        self.assertEqual(len(json.loads(output.getvalue())["paths"]), 1)
        self.assertEqual(self.shell.read_bytes(), b"# preserve this file\n")
        self.assertEqual(before, sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*")))

    @unittest.skipIf(os.name == "nt", "Unix zsh integration")
    def test_backup_idempotence_and_restore_preserve_all_original_bytes(self):
        self.bin.mkdir()
        self.config.mkdir()
        original = {self.bin/"laya-ae": b"old launcher\n", self.config/"laya-dispatch.json": b"old config\n",
                    self.shell: b"# user's bytes \xff\r\nalias laya='old alias'\n# final line"}
        for path, data in original.items():
            path.write_bytes(data)
            path.chmod(0o700)
        result = installer.apply(self.plan(), self.backups)
        installed_shell = self.shell.read_bytes()
        self.assertTrue(installed_shell.startswith(original[self.shell]))
        self.assertEqual(installed_shell.count(installer.BEGIN), 1)
        receipt = Path(result["receipt"])
        config = json.loads((self.config/"laya-dispatch.json").read_text(encoding="utf-8"))
        self.assertEqual(config["ae_argv"], [str(installer.executable(sys.executable)), "-B", str(self.scripts/"terminal.py")])
        self.assertEqual(config["legacy_argv"], [str(installer.executable(sys.executable)), str(self.scripts/"legacy.py")])
        entries = json.loads(receipt.read_text(encoding="utf-8"))["entries"]
        for entry in entries:
            self.assertEqual((receipt.parent/entry["backup"]).read_bytes(), original[Path(entry["path"])])
        before = list(self.backups.iterdir())
        self.assertEqual(installer.apply(self.plan(), self.backups)["status"], "unchanged")
        self.assertEqual(list(self.backups.iterdir()), before)
        self.assertEqual(installer.restore(receipt)["status"], "restored")
        for path, data in original.items():
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)

    def test_malformed_duplicate_or_reversed_markers_are_refused(self):
        examples = [installer.BEGIN+b"\n", installer.END+b"\n", installer.END+b"\n"+installer.BEGIN+b"\n",
                    installer.BEGIN+b"\n"+installer.END+b"\n"+installer.BEGIN+b"\n"+installer.END+b"\n",
                    b"# >>> ae-basic-laya terminal integration\n"]
        for original in examples:
            with self.subTest(original=original), self.assertRaisesRegex(ValueError, "marker"):
                installer.shell_content(original, Path(sys.executable), SCRIPTS/"laya_dispatch.py", self.config/"laya-dispatch.json")

    def test_replacing_managed_block_keeps_prefix_and_suffix_bytes(self):
        prefix, suffix = b"# user's prefix \xff\r\n", b"# user's trailing config\r\n"
        original = prefix+installer.BEGIN+b"\nold managed content\n"+installer.END+b"\n"+suffix
        changed = installer.shell_content(original, Path(sys.executable), self.scripts/"laya_dispatch.py", self.config/"laya-dispatch.json")
        self.assertTrue(changed.startswith(prefix))
        self.assertTrue(changed.endswith(suffix))
        self.assertNotIn(b"old managed content", changed)
        self.assertEqual(changed.count(installer.BEGIN), 1)

    def test_legacy_passthrough_keeps_every_original_argument_and_flag(self):
        examples = [[], ["--help"], ["status"], ["apps"], ["--list"],
                    ["run", "메모 열어 줘", "--dry-run", "--json", "--config", "user's config 한글.json"]]
        for arguments in examples:
            with self.subTest(arguments=arguments):
                result, output = self.run_dispatch(arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, {"route": "legacy", "args": arguments})

    def test_explicit_ae_and_direct_korean_prefixes_route_to_terminal(self):
        examples = [["ae", "--list"], ["ae", "텍스트", "한 글"], ["컴포지션 만들기"], ["배경 검정"],
                    ["텍스트", "안녕하세요"], ["널 추가"], ["3D", "널", "추가"], ["선택 레이어 이름"], ["현재 상태"]]
        for arguments in examples:
            with self.subTest(arguments=arguments):
                result, output = self.run_dispatch(arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, {"route": "ae", "args": arguments[1:] if arguments[0] == "ae" else arguments})

    def test_unknown_explicit_ae_error_never_falls_back_to_legacy(self):
        result, output = self.run_dispatch(["ae", "unknown request", "--fail"])
        self.assertEqual(result.returncode, 7)
        self.assertEqual(output, {"route": "ae", "args": ["unknown request", "--fail"]})

    @unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
    @unittest.skipIf(os.name == "nt", "Unix zsh integration")
    def test_managed_zsh_function_unaliases_and_preserves_arguments(self):
        self.shell.write_text("# keep\nalias laya='old-alias'\n", encoding="utf-8")
        installer.apply(self.plan(), self.backups)
        self.assertIn(b" -B ", self.shell.read_bytes())
        for arguments, route in ((["ae", "텍스트", "quote' 한 글"], "ae"), (["--help"], "legacy")):
            result = subprocess.run([shutil.which("zsh"), "-f", "-c", 'source "$1"; shift; laya "$@"',
                                     "test-shell", str(self.shell), *arguments], capture_output=True, encoding="utf-8", timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"route": route, "args": arguments[1:] if route == "ae" else arguments})

    @unittest.skipIf(os.name == "nt", "Unix zsh integration")
    def test_restore_refuses_later_edits_before_touching_any_target(self):
        self.shell.write_bytes(b"# user shell\n")
        plan = self.plan()
        result = installer.apply(plan, self.backups)
        self.shell.write_bytes(self.shell.read_bytes()+b"# later edit\n")
        before = {entry["path"]: entry["path"].read_bytes() for entry in plan}
        with self.assertRaisesRegex(ValueError, "changed since installation"):
            installer.restore(Path(result["receipt"]))
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    @unittest.skipIf(os.name == "nt", "Unix zsh integration")
    def test_restore_removes_new_files_and_preserves_later_mode_edits(self):
        plan = self.plan()
        result = installer.apply(plan, self.backups)
        target = self.bin/"laya-ae"
        target.chmod(0o700)
        with self.assertRaisesRegex(ValueError, "changed since installation"):
            installer.restore(Path(result["receipt"]))
        self.assertTrue(all(entry["path"].is_file() for entry in plan))
        target.chmod(0o755)
        installer.restore(Path(result["receipt"]))
        self.assertTrue(all(not entry["path"].exists() for entry in plan))

    @unittest.skipIf(os.name == "nt", "Unix zsh integration")
    def test_failed_install_rolls_back_completed_writes(self):
        self.bin.mkdir()
        target = self.bin/"laya-ae"
        target.write_bytes(b"original launcher\n")
        self.shell.write_bytes(b"# original shell\n")
        plan = self.plan()
        atomic = installer.atomic_write
        failed = False
        def fail_second_target(path, data, mode):
            nonlocal failed
            if path == self.config/"laya-dispatch.json" and not failed:
                failed = True
                receipts = list(self.backups.rglob("receipt.json"))
                self.assertEqual(len(receipts), 1)
                entries = json.loads(receipts[0].read_text(encoding="utf-8"))["entries"]
                self.assertTrue(all(entry["backup"] is None or (receipts[0].parent/entry["backup"]).is_file() for entry in entries))
                raise OSError("simulated target write failure")
            return atomic(path, data, mode)
        with patch.object(installer, "atomic_write", side_effect=fail_second_target), self.assertRaisesRegex(OSError, "simulated"):
            installer.apply(plan, self.backups)
        self.assertEqual(target.read_bytes(), b"original launcher\n")
        self.assertEqual(self.shell.read_bytes(), b"# original shell\n")
        self.assertFalse((self.config/"laya-dispatch.json").exists())


if __name__ == "__main__":
    unittest.main()
