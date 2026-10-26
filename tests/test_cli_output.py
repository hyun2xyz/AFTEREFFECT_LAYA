import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


class OutputTests(unittest.TestCase):
    def test_korean_command_emits_utf8_even_with_legacy_pipe_encoding(self):
        result=subprocess.run([sys.executable,"-S","-B",str(ROOT/"scripts/terminal.py"),"텍스트","안녕하세요","추가해줘","--dry-run"],
                              env={**os.environ,"PYTHONIOENCODING":"cp1252"},capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        data=json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(data["plan"]["actions"][0]["text"],"안녕하세요")
        self.assertFalse(data["model_called"])


if __name__=="__main__":unittest.main()
