import json
import os
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import terminal


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="AE 한글 paths ")
        self.root=Path(self.tmp.name).resolve()

    def tearDown(self):self.tmp.cleanup()

    def app(self,name):
        app=self.root/(name+".app")
        info=app/"Contents/Info.plist";info.parent.mkdir(parents=True)
        with info.open("wb") as f:plistlib.dump({"CFBundleIdentifier":"com.adobe.AfterEffects.application"},f)
        return app

    def test_explicit_then_environment_then_persistent_config(self):
        arg,env,config=[self.app(name) for name in ("argument","environment","설정 앱")]
        (self.root/"tools.local.json").write_text(json.dumps({"ae_app":str(config)},ensure_ascii=False),encoding="utf-8")
        with patch.object(terminal,"PROJECT_ROOT",self.root),patch.object(terminal.sys,"platform","darwin"),patch.dict(os.environ,{"AE_APP":str(env)},clear=True):
            self.assertEqual(terminal.find_app(arg),arg)
            self.assertEqual(terminal.find_app(),env)
        with patch.object(terminal,"PROJECT_ROOT",self.root),patch.object(terminal.sys,"platform","darwin"),patch.dict(os.environ,{},clear=True):
            self.assertEqual(terminal.find_app(),config)

    def test_broken_explicit_config_is_not_silently_ignored(self):
        app=self.app("valid")
        (self.root/"tools.local.json").write_text(json.dumps({"ae_app":"relative/path.app"}),encoding="utf-8")
        with patch.object(terminal,"PROJECT_ROOT",self.root),patch.object(terminal.sys,"platform","darwin"),patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,"absolute"):terminal.find_app()
            self.assertEqual(terminal.find_app(app),app)


if __name__=="__main__":unittest.main()
