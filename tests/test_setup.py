"""Stdlib-only setup tests; no real AE, global configuration or downloads."""
import contextlib
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0, str(SCRIPTS))
import setup_environment as setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="AE setup's 한글 ")
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def mac_app(self, name="Adobe After Effects 2026.app", identifier="com.adobe.AfterEffects.application"):
        path = self.root/name
        (path/"Contents").mkdir(parents=True)
        with (path/"Contents/Info.plist").open("wb") as stream:
            plistlib.dump({"CFBundleIdentifier": identifier, "CFBundleShortVersionString": "26.0"}, stream)
        return path

    def fake_venv(self, system_packages=False):
        path = setup.venv_python(self.root)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"fixture; never executed")
        (self.root/".venv/pyvenv.cfg").write_text("include-system-site-packages = "+str(system_packages).lower()+"\n", encoding="utf-8")

    def test_check_is_read_only_and_ae_absence_is_unverified(self):
        (self.root/"student.txt").write_text("보존", encoding="utf-8")
        before = list(self.root.rglob("*"))
        with patch.object(setup, "app_path", side_effect=ValueError("AE missing")), patch.object(setup.subprocess, "run") as run:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = setup.main(["--check"], root=self.root)
        data = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(data["ready_for_dry_run"])
        self.assertFalse(data["after_effects"]["native_verified"])
        self.assertEqual(data["native_ae"], "not_verified")
        self.assertEqual(before, list(self.root.rglob("*")))
        run.assert_not_called()

    @unittest.skipUnless(sys.version_info[:2] in setup.SUPPORTED, "use Python 3.12/3.13 for the real venv fixture")
    def test_real_prepare_without_pip_reuses_venv_and_needs_no_ae(self):
        with patch.object(setup.terminal, "find_app", side_effect=AssertionError("AE must not be queried by prepare")):
            result = setup.prepare(self.root)
        self.assertTrue(result["prepared"])
        self.assertFalse(result["reused"])
        self.assertFalse(result["packages_installed_by_helper"])
        self.assertEqual(result["native_ae"], "not_verified")
        python = setup.venv_python(self.root)
        found = subprocess.run([str(python), "-I", "-B", "-c", "import importlib.util;print(importlib.util.find_spec('pip') is None)"],
                               check=True, capture_output=True, encoding="utf-8", timeout=15)
        self.assertEqual(found.stdout.strip(), "True")
        original = (self.root/".venv/pyvenv.cfg").read_bytes()
        with patch.object(setup.venv, "EnvBuilder", side_effect=AssertionError("do not recreate an existing valid environment")):
            self.assertTrue(setup.prepare(self.root)["reused"])
        self.assertEqual((self.root/".venv/pyvenv.cfg").read_bytes(), original)
        with patch.object(setup, "app_path", side_effect=ValueError("AE missing")):
            checked = setup.check(self.root)
        self.assertTrue(checked["ready_for_dry_run"])
        self.assertFalse(checked["ready"])

    def test_broken_or_foreign_existing_environment_is_preserved(self):
        self.fake_venv()
        original = (self.root/".venv/pyvenv.cfg").read_bytes()
        data = {"version": [3, 13, 7], "prefix": str(self.root/"outside"), "base_prefix": str(self.root/"outside")}
        result = subprocess.CompletedProcess([], 0, json.dumps(data), "")
        with patch.object(setup.subprocess, "run", return_value=result), patch.object(setup.venv, "EnvBuilder") as builder:
            with self.assertRaisesRegex(ValueError, "does not belong"):
                setup.prepare(self.root)
            builder.assert_not_called()
        self.assertEqual((self.root/".venv/pyvenv.cfg").read_bytes(), original)
        setup.venv_python(self.root).unlink()
        with patch.object(setup.venv, "EnvBuilder") as builder:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                setup.prepare(self.root)
            builder.assert_not_called()
        self.assertEqual((self.root/".venv/pyvenv.cfg").read_bytes(), original)

    def test_system_site_packages_and_unsupported_python_are_not_replaced(self):
        self.fake_venv(system_packages=True)
        with patch.object(setup.venv, "EnvBuilder") as builder, patch.object(setup.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "not isolated"):
                setup.prepare(self.root)
            builder.assert_not_called()
            run.assert_not_called()
        empty = self.root/"fresh folder"
        empty.mkdir()
        with patch.object(setup.sys, "version_info", (3, 11, 0)), patch.object(setup.venv, "EnvBuilder") as builder:
            with self.assertRaisesRegex(ValueError, "Python 3.13"):
                setup.prepare(empty)
            builder.assert_not_called()
        self.assertFalse((empty/".venv").exists())

    def test_linked_environment_is_refused_without_mutating_target(self):
        elsewhere = self.root/"other environment"
        elsewhere.mkdir()
        sentinel = elsewhere/"student.txt"
        sentinel.write_bytes(b"preserve")
        try:
            (self.root/".venv").symlink_to(elsewhere, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks need platform permission")
        with patch.object(setup.venv, "EnvBuilder") as builder:
            with self.assertRaisesRegex(ValueError, "linked/foreign"):
                setup.prepare(self.root)
            builder.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_mac_configuration_is_utf8_atomic_and_never_executes_ae(self):
        app = self.mac_app()
        with patch.object(setup.sys, "platform", "darwin"), patch.object(setup.terminal, "execute_job") as execute, patch.object(setup.subprocess, "run") as run:
            result = setup.configure(self.root, app)
            execute.assert_not_called()
            run.assert_not_called()
        self.assertTrue(result["configured"])
        self.assertEqual(json.loads((self.root/"tools.local.json").read_text(encoding="utf-8")), {"ae_app": str(app)})
        self.assertIn("한글".encode("utf-8"), (self.root/"tools.local.json").read_bytes())
        self.assertFalse(list(self.root.glob(".tools-local-*")))
        self.assertFalse((self.root/".git").exists())
        self.assertEqual(result["native_ae"], "not_verified")

    def test_windows_requires_actual_afterfx_exe_and_relative_paths_fail(self):
        app = self.root/"Adobe After Effects 2026/Support Files/AfterFX.exe"
        app.parent.mkdir(parents=True)
        app.write_bytes(b"MZ fixture; never executed")
        with patch.object(setup.sys, "platform", "win32"), patch.object(setup.subprocess, "run") as run:
            self.assertEqual(setup.configure(self.root, app)["ae_app"], str(app))
            run.assert_not_called()
            wrong = app.with_name("aerender.exe")
            wrong.write_bytes(b"fixture")
            original = (self.root/"tools.local.json").read_bytes()
            with self.assertRaises(ValueError):
                setup.configure(self.root, wrong)
            with self.assertRaisesRegex(ValueError, "absolute"):
                setup.configure(self.root, Path("AfterFX.exe"))
        self.assertEqual((self.root/"tools.local.json").read_bytes(), original)

    def test_wrong_app_render_engine_or_wrong_config_preserves_old_file(self):
        valid = self.mac_app()
        wrong = self.mac_app("Wrong.app", "com.adobe.Photoshop")
        render = self.mac_app("Adobe After Effects Render Engine 2026.app")
        config = self.root/"tools.local.json"
        original = json.dumps({"ae_app": "기존 앱 경로"}, ensure_ascii=False).encode("utf-8")
        config.write_bytes(original)
        with patch.object(setup.sys, "platform", "darwin"):
            for app in (wrong, render):
                with self.subTest(app=app), self.assertRaises(ValueError):
                    setup.configure(self.root, app)
                self.assertEqual(config.read_bytes(), original)
            unrelated = json.dumps({"ae_app": str(valid), "student_setting": "preserve"}).encode("utf-8")
            config.write_bytes(unrelated)
            with self.assertRaisesRegex(ValueError, "unrelated"):
                setup.configure(self.root, valid)
            self.assertEqual(config.read_bytes(), unrelated)

    def test_atomic_replace_failure_keeps_old_config_and_cleans_temporary(self):
        app = self.mac_app()
        config = self.root/"tools.local.json"
        config.write_text('{"ae_app":"old"}', encoding="utf-8")
        original = config.read_bytes()
        with patch.object(setup.sys, "platform", "darwin"), patch.object(setup.os, "replace", side_effect=OSError("simulated replacement failure")):
            with self.assertRaisesRegex(OSError, "simulated"):
                setup.configure(self.root, app)
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse(list(self.root.glob(".tools-local-*")))

    def test_no_git_source_copy_runs_without_site_and_with_legacy_stdout_codec(self):
        scripts = self.root/"scripts"
        scripts.mkdir()
        for name in ("setup_environment.py", "cli_output.py", "terminal.py", "ae_basic.py", "ae_phrases.py"):
            shutil.copy2(SCRIPTS/name, scripts/name)
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run([sys.executable, "-S", "-B", str(scripts/"setup_environment.py"), "--check"],
                                capture_output=True, env=environment, timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(data["root"], str(self.root))
        self.assertEqual(data["native_ae"], "not_verified")
        self.assertFalse((self.root/".git").exists())
        self.assertFalse(list(self.root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
