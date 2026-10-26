import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import terminal
import laya_dispatch as dispatch


class PhraseTests(unittest.TestCase):
    def test_observed_short_requests_create_the_same_dimensions(self):
        requests=["comp 1920 1080","애프터이펙트 컴포지션 1920 1080","컴포지션 19201080",
                  "컴프 1920x1080","After Effects comp 1920 1080", "컴포지션 19201080 만들어줘"]
        for request in requests:
            with self.subTest(request=request):
                action=terminal.parse_request(request)["actions"][0]
                self.assertEqual((action["op"],action["width"],action["height"]),("create_comp",1920,1080))

    def test_ae_requests_never_reach_generic_system_fallback(self):
        config={"ae_argv":["python","ae.py"],"legacy_argv":["python","legacy.py"]}
        for args in [["comp","1920","1080"],["애프터이펙트","컴포지션","1920","1080"],
                     ["컴포지션","19201080"],["run","comp 1920 1080"],["애프터이펙트","지원하지않는기능"],
                     ["레이어","정리하지마"]]:
            with self.subTest(args=args):self.assertEqual(dispatch.command(config,args)[:2],config["ae_argv"])
        for args in [["status"],["apps"],["애프터이펙트","열어줘"],["애프터이펙트","종료해줘"],["run","메모 열어줘"]]:
            with self.subTest(args=args):self.assertEqual(dispatch.command(config,args),[*config["legacy_argv"],*args])

    def test_short_forms_do_not_turn_negation_or_questions_into_actions(self):
        for request in ["comp 1920 1080 만들지마","애프터이펙트 컴포지션 1920 1080 설명해줘",
                        '"컴포지션 19201080"라는 말의 뜻',"컴포지션 1920 1080; 삭제"]:
            with self.subTest(request=request),self.assertRaises(ValueError):terminal.parse_request(request)
        with patch.object(terminal,"find_app",side_effect=AssertionError("App was queried")),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(terminal.main(["애프터이펙트","컴포지션","1920","1080","설명해줘"]),2)


if __name__=="__main__":unittest.main()
