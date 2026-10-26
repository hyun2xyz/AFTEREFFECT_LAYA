import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import ae_basic as core
import terminal


def snapshot():
    return {"session":"native-session", "signature":"native-signature", "project_items":3,
            "active_comp":{"id":11,"name":"Lesson","duration":5,"width":1920,"height":1090,"fps":30},
            "layers":[{"id":51,"name":"Title","three_d":False,"selected":True,"locked":False,"animated":[],"expressions":[]}]}


def receipt(job_id="j", actions=None):
    return {"schema":core.VERSION,"job_id":job_id,"status":"ok","ae_version":"26.3",
            "actions":actions or [],"snapshot":snapshot()}


class BasicTests(unittest.TestCase):
    def test_korean_dimensions_and_defaults_preserve_1090(self):
        a=terminal.parse_request("컴포지션 19201090 만들어줘")["actions"][0]
        self.assertEqual((a["width"],a["height"],a["fps"],a["duration"]),(1920,1090,30,10))
        a=terminal.parse_request("컴포지션 1920x1080 24fps 5초 만들어줘")["actions"][0]
        self.assertEqual((a["height"],a["fps"],a["duration"]),(1080,24,5))

    def test_negation_quoted_instructions_and_unknown_are_not_commands(self):
        for request in ["배경 색 초록색으로 바꾸지 마", '"배경 색 초록색으로 바꿔줘"라는 말이 무슨 뜻이죠?',
                        "컴포지션 19201090 만들어줘; 삭제해줘", "전체 프로젝트 저장해줘", "레이어를 알아서 정리해줘"]:
            with self.subTest(request=request), self.assertRaises(ValueError):
                terminal.parse_request(request)

    def test_dry_run_never_calls_app_or_model(self):
        out=io.StringIO()
        with patch.object(terminal,"find_app",side_effect=AssertionError("app queried")), contextlib.redirect_stdout(out):
            self.assertEqual(terminal.main(["배경","색","초록색으로","바꿔줘","--dry-run"]),0)
        value=json.loads(out.getvalue())
        self.assertFalse(value["executed"])
        self.assertFalse(value["model_called"])

    def test_selected_target_is_exactly_one_and_locked_is_rejected(self):
        parsed=terminal.parse_request("선택 레이어 위치 960 545으로 바꿔줘")
        self.assertEqual(terminal.resolve_actions(parsed,snapshot())[0]["layer"],51)
        for change in ("none","two","locked"):
            s=snapshot()
            if change=="none":s["layers"][0]["selected"]=False
            elif change=="two":s["layers"].append({**s["layers"][0],"id":52})
            else:s["layers"][0]["locked"]=True
            with self.subTest(change=change),self.assertRaises(ValueError):
                terminal.resolve_actions(parsed,s)

    def test_fixed_registry_rejects_code_nan_unknown_and_bad_dimension(self):
        good={"op":"set_transform","comp":11,"layer":51,"values":{"opacity":50}}
        invalid=[{**good,"code":"alert(1)"},{**good,"values":{"opacity":True}},
                 {**good,"values":{"opacity":float("nan")}},{**good,"values":{"position":[1,2,3]}},
                 {**good,"values":{"expression":"wiggle(1,1)"}},{**good,"op":"delete_layer"}]
        for action in invalid:
            with self.subTest(action=action),self.assertRaises(ValueError):
                core.validate_plan({"actions":[action]},snapshot())

    def test_animation_expression_and_in_batch_overwrite_are_protected(self):
        action={"op":"set_transform","comp":11,"layer":51,"values":{"opacity":50}}
        for field in ("animated","expressions"):
            s=snapshot();s["layers"][0][field]=["opacity"]
            with self.subTest(field=field),self.assertRaises(ValueError):core.validate_plan({"actions":[action]},s)
        keys={"op":"set_keyframes","comp":11,"layer":51,"property":"opacity","keys":[{"time":0,"value":0},{"time":1,"value":100}]}
        with self.assertRaises(ValueError):core.validate_plan({"actions":[keys,action]},snapshot())

    def test_references_are_ordered_typed_and_same_composition(self):
        c={"op":"create_comp","ref":"c","name":"Lesson","width":1920,"height":1090,"fps":30,"duration":5}
        n={"op":"add_null","comp":"@c","ref":"n","name":"Null","three_d":True}
        t={"op":"set_transform","comp":"@c","layer":"@n","values":{"position":[1,2,3]}}
        self.assertEqual(len(core.validate_plan({"actions":[c,n,t]},snapshot())),3)
        for actions in ([n,c],[c,n,{**t,"comp":11}],[c,{**n,"ref":"c"}]):
            with self.assertRaises(ValueError):core.validate_plan({"actions":actions},snapshot())

    def test_key_times_must_be_finite_ordered_and_within_comp(self):
        action={"op":"set_keyframes","comp":11,"layer":51,"property":"opacity"}
        for times in ([1,1],[2,1],[-1,1],[0,6],[0,float("inf")]):
            with self.subTest(times=times),self.assertRaises(ValueError):
                core.validate_plan({"actions":[{**action,"keys":[{"time":t,"value":50} for t in times]}]},snapshot())

    def test_native_readback_must_match_job_id_values_and_targets(self):
        action={"op":"set_transform","comp":11,"layer":51,"values":{"position":[960,545]}}
        job={"job_id":"j","actions":[action]}
        result=receipt(actions=[{"op":"set_transform","comp_id":11,"layer_id":51,"values":{"position":[960,545]}}])
        self.assertTrue(core.verify_receipt(result,job))
        for change in ("job","value","target"):
            bad=copy.deepcopy(result)
            if change=="job":bad["job_id"]="other"
            elif change=="value":bad["actions"][0]["values"]["position"]=[0,0]
            else:bad["actions"][0]["layer_id"]=999
            with self.subTest(change=change),self.assertRaises(ValueError):core.verify_receipt(bad,job)
        result["status"]="partial"
        self.assertFalse(core.verify_receipt(result,job))

    def test_summary_omits_bulk_keyframes_and_text(self):
        value=core.summarize(receipt(actions=[{"op":"set_keyframes","keys":[{"time":i,"value":i} for i in range(200)]},{"op":"add_text","text":"가"*4000}]))
        self.assertNotIn("keys",value["action_results"][0])
        self.assertEqual(value["action_results"][0]["key_count"],200)
        self.assertEqual(value["action_results"][1]["text_length"],4000)
        self.assertLess(len(json.dumps(value)),1500)

    def test_payload_is_data_and_existing_job_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            job={"schema":core.VERSION,"job_id":"j","inspect_only":True,"actions":[],"data":'"; throw Error("bad"); //\u2028한글'}
            result=core.emit(job,Path(temp)/"job with spaces")
            code=Path(result["jsx"]).read_text()
            encoded=code.split("var job = ",1)[1]
            decoded,_=json.JSONDecoder().raw_decode(encoded)
            self.assertEqual(decoded,job)
            self.assertNotIn("\u2028",code)
            before=Path(result["jsx"]).read_bytes()
            with self.assertRaises(ValueError):core.emit(job,Path(result["jsx"]).parent)
            self.assertEqual(before,Path(result["jsx"]).read_bytes())

    def test_duplicate_job_is_refused_before_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);(directory/"result.json").write_text("{}")
            with patch.object(terminal.subprocess,"run",side_effect=AssertionError("resent")),self.assertRaises(ValueError):
                terminal.execute_job({"jsx":str(directory/"run.jsx"),"result":str(directory/"result.json")},Path("AE"))

    def test_windows_transport_preserves_argv_and_checks_native_receipt(self):
        with tempfile.TemporaryDirectory(prefix="AE space ") as temp:
            job={"schema":core.VERSION,"job_id":"j","inspect_only":True,"actions":[]}
            prepared=core.emit(job,Path(temp)/"job")
            def fake_run(argv,**kwargs):
                Path(prepared["result"]).write_text(json.dumps(receipt()))
                return subprocess_result()
            with patch.object(terminal.sys,"platform","win32"),patch.object(terminal.subprocess,"run",side_effect=fake_run) as run:
                self.assertEqual(terminal.execute_job(prepared,Path("C:/Adobe/AfterFX.exe"))["status"],"ok")
            argv=run.call_args.args[0]
            self.assertEqual(argv,[str(Path("C:/Adobe/AfterFX.exe")),"-r",prepared["jsx"]])
            self.assertFalse(run.call_args.kwargs.get("shell",False))


class subprocess_result:
    returncode=0
    stderr=""


if __name__=="__main__":unittest.main()
