#!/usr/bin/env python3
"""Small Korean AE command vocabulary; deterministic parsing, native JSX execution."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import time
import uuid

# Keep an installed skill tree unchanged when launched directly as a script.
sys.dont_write_bytecode = True
import ae_basic as core
from cli_output import configure_stdout

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COLORS = {"초록": [0,1,0], "빨강": [1,0,0], "파랑": [0,0,1], "검정": [0,0,0], "흰": [1,1,1], "노랑": [1,1,0]}
EXAMPLES = [
    "컴포지션 1920x1090 만들어줘", "컴포지션 1920x1080 24fps 5초 만들어줘",
    "배경 색 초록색으로 바꿔줘", "배경색 #224466으로 바꿔줘",
    "텍스트 안녕하세요 추가해줘", "널 추가해줘", "3D 널 추가해줘",
    "선택 레이어 이름 타이틀로 바꿔줘", "선택 레이어 위치 960 540으로 바꿔줘",
    "선택 레이어 크기 50 50으로 바꿔줘", "선택 레이어 회전 45도로 바꿔줘",
    "선택 레이어 불투명도 50으로 바꿔줘", "선택 레이어 숨겨줘", "선택 레이어 켜줘",
    "선택 레이어 불투명도 0초 0 1초 100 키프레임 만들어줘", "현재 상태 보여줘",
]
NUMBER = r"-?\d+(?:\.\d+)?"
MAC_SCRIPT = '''on run argv
    set targetApp to item 1 of argv
    set jsxFile to POSIX file (item 2 of argv)
    using terms from application id "com.adobe.AfterEffects.application"
        tell application targetApp
            DoScriptFile jsxFile
        end tell
    end using terms from
end run'''


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_request(request):
    s = request.strip()
    if not s or len(s) > 600:
        raise ValueError("Use one short supported command (up to 600 characters)")
    if s in {"명령어", "명령어 목록", "도움말", "help"}:
        return {"kind": "help", "actions": []}
    if s in {"현재 상태 보여줘", "현재 상태 확인해줘", "컴포지션 정보 보여줘"}:
        return {"kind": "inspect", "actions": []}
    # The whole command must match; negations, questions and quoted instructions
    # are never converted into executable operations by a substring search.
    m = re.fullmatch(r"컴포지션\s+(?:(\d{2,5})\s*[xX×*]\s*(\d{2,5})|(\d{4})(\d{4}))(?:\s+(\d+(?:\.\d+)?)fps)?(?:\s+(\d+(?:\.\d+)?)초)?\s+(?:만들어줘|생성해줘)", s)
    if m:
        width,height = (m[1],m[2]) if m[1] else (m[3],m[4])
        return {"kind":"mutate", "actions":[{"op":"create_comp","name":"Laya AE","width":int(width),"height":int(height),"fps":float(m[5] or 30),"duration":float(m[6] or 10)}]}
    m = re.fullmatch(r"배경\s*색\s+(초록색?|빨강색?|파랑색?|검정색?|흰색|노랑색?|#[0-9a-fA-F]{6})(?:으로|로)?\s+(?:바꿔줘|변경해줘)", s)
    if m:
        value=m[1]
        color=[int(value[i:i+2],16)/255 for i in (1,3,5)] if value.startswith("#") else COLORS[value.removesuffix("색")]
        return {"kind":"mutate","actions":[{"op":"set_comp","comp":"$active","changes":{"background_color":color}}]}
    m = re.fullmatch(r"텍스트\s+(.+?)\s+(?:추가해줘|만들어줘)", s)
    if m:
        value=unquote(m[1])
        return {"kind":"mutate","actions":[{"op":"add_text","comp":"$active","name":value[:80],"text":value,"font_size":72}]}
    m = re.fullmatch(r"(3[Dd]\s+)?널\s+(?:추가해줘|만들어줘)", s)
    if m:
        return {"kind":"mutate","actions":[{"op":"add_null","comp":"$active","name":"Laya Null","three_d":bool(m[1])}]}
    m = re.fullmatch(r"선택 레이어 이름\s+(.+?)(?:으로|로)\s+바꿔줘", s)
    if m:
        return {"kind":"mutate","actions":[{"op":"set_layer","comp":"$active","layer":"$selected","changes":{"name":unquote(m[1])}}]}
    m = re.fullmatch(r"선택 레이어\s+(숨겨줘|켜줘)", s)
    if m:
        return {"kind":"mutate","actions":[{"op":"set_layer","comp":"$active","layer":"$selected","changes":{"enabled":m[1]=="켜줘"}}]}
    m = re.fullmatch(rf"선택 레이어\s+(위치|크기|회전|불투명도)\s+({NUMBER}(?:\s+{NUMBER}){{0,2}})(?:으로|로|도로)?\s+바꿔줘", s)
    if m:
        prop={"위치":"position","크기":"scale","회전":"rotation","불투명도":"opacity"}[m[1]]
        values=[float(x) for x in m[2].split()]
        if (prop in {"rotation","opacity"} and len(values)!=1) or (prop in {"position","scale"} and len(values) not in (2,3)):
            raise ValueError("Vector transforms need 2 or 3 numbers; opacity/rotation need one")
        return {"kind":"mutate","actions":[{"op":"set_transform","comp":"$active","layer":"$selected","values":{prop:values[0] if len(values)==1 else values}}]}
    m = re.fullmatch(rf"선택 레이어 불투명도\s+({NUMBER})초\s+({NUMBER})\s+({NUMBER})초\s+({NUMBER})\s+키프레임 만들어줘", s)
    if m:
        return {"kind":"mutate","actions":[{"op":"set_keyframes","comp":"$active","layer":"$selected","property":"opacity","keys":[{"time":float(m[1]),"value":float(m[2])},{"time":float(m[3]),"value":float(m[4])}]}]}
    raise ValueError("Unsupported or ambiguous command; use --list or let Codex clarify. No AE command was sent")


def resolve_actions(parsed, snapshot):
    actions=json.loads(json.dumps(parsed["actions"]))
    active=snapshot.get("active_comp")
    selected=[x for x in snapshot["layers"] if x.get("selected")]
    for action in actions:
        if action.get("comp")=="$active":
            if not active:
                raise ValueError("Activate the intended composition first")
            action["comp"]=active["id"]
        if action.get("layer")=="$selected":
            if len(selected)!=1:
                raise ValueError("Select exactly one intended layer first")
            action["layer"]=selected[0]["id"]
    return core.validate_plan({"actions":actions},snapshot)


def find_app(explicit=None):
    if explicit is None:
        configured = os.environ.get("AE_APP", "").strip()
        if not configured and (PROJECT_ROOT/"tools.local.json").is_file():
            data = core.read_json(PROJECT_ROOT/"tools.local.json")
            if not isinstance(data, dict) or not isinstance(data.get("ae_app"), str) or not data["ae_app"].strip():
                raise ValueError("tools.local.json needs a nonempty ae_app path")
            configured = data["ae_app"]
        if configured:
            if not Path(configured).expanduser().is_absolute():
                raise ValueError("AE_APP/tools.local.json ae_app must be an absolute path")
            explicit = Path(configured)
    if explicit:
        choices=[Path(explicit).expanduser().resolve()]
    elif sys.platform=="darwin":
        choices=list(Path("/Applications").glob("Adobe After Effects */Adobe After Effects *.app"))
    elif sys.platform=="win32":
        choices=list((Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"Adobe").glob("Adobe After Effects */Support Files/AfterFX.exe"))
    else:
        raise ValueError("Native execution supports macOS/Windows; prepare JSX with ae_basic.py on other hosts")
    valid=[]
    for path in choices:
        if sys.platform=="darwin":
            info=path/"Contents/Info.plist"
            if info.is_file():
                with info.open("rb") as f:
                    data=plistlib.load(f)
                if data.get("CFBundleIdentifier")=="com.adobe.AfterEffects.application":
                    valid.append(path)
        elif path.is_file() and path.name.lower()=="afterfx.exe":
            valid.append(path)
    if len(valid)!=1:
        raise ValueError("Specify exactly one real AE app with --app; candidates: "+str([str(x) for x in valid]))
    return valid[0]


def execute_job(job, app, timeout=30):
    jsx=Path(job["jsx"]); receipt=Path(job["result"])
    if receipt.exists() or (jsx.parent/"started.json").exists():
        raise ValueError("Job already started; inspect its receipt instead of resending")
    if sys.platform=="darwin":
        argv=["/usr/bin/osascript","-e",MAC_SCRIPT,str(app),str(jsx)]
    elif sys.platform=="win32":
        argv=[str(app),"-r",str(jsx)]
    else:
        raise ValueError("Unsupported native host")
    started=time.monotonic()
    try:
        command=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Native call timed out; execution may still be pending. Do not resend this job: "+str(jsx.parent)) from exc
    if command.returncode:
        raise ValueError("Native call failed (do not automatically retry): "+command.stderr.strip()[:500])
    # This local file wait does not call the LLM or repeat an AE operation.
    while not receipt.exists() and time.monotonic()-started<timeout:
        time.sleep(.1)
    if not receipt.exists():
        raise ValueError("Native command returned without a receipt; result unknown. Inspect job: "+str(jsx.parent))
    raw=core.read_json(receipt)
    verified=core.verify_receipt(raw,core.read_json(jsx.parent/"job.json"))
    if not verified:
        raise ValueError("Native "+str(raw.get("status"))+": "+str(raw.get("error"))+"; inspect before preparing another job: "+str(jsx.parent))
    return raw


def job_root(explicit=None):
    if explicit:
        root=Path(explicit).expanduser().resolve()
    elif sys.platform=="win32":
        root=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"AE Basic Laya/jobs"
    else:
        root=Path.home()/"Library/Application Support/AE Basic Laya/jobs"
    return root/uuid.uuid4().hex


def main(argv=None):
    configure_stdout()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("request",nargs="*")
    p.add_argument("--list",action="store_true")
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--app",type=Path)
    p.add_argument("--out-root",type=Path)
    a=p.parse_args(argv)
    try:
        parsed=parse_request("명령어" if a.list else " ".join(a.request))
        if parsed["kind"]=="help":
            value={"status":"commands","examples":EXAMPLES,"defaults":{"fps":30,"duration_seconds":10},"note":"Background color is a composition setting, not an opaque render background"}
        elif a.dry_run:
            # Validate all explicit numbers before even a read-only app query.
            fake={"session":"preview","signature":"preview","project_items":0,"active_comp":{"id":1,"duration":10800},"layers":[{"id":1,"selected":True,"three_d":False}]}
            if parsed["kind"]=="mutate":
                try: resolve_actions(parsed,fake)
                except ValueError as exc:
                    if "vector components" not in str(exc): raise
            value={"status":"preview","executed":False,"engine":"deterministic_rules","model_called":False,"plan":parsed}
        else:
            app=find_app(a.app); destination=job_root(a.out_root)
            inspect=core.emit({"schema":core.VERSION,"job_id":uuid.uuid4().hex,"inspect_only":True,"actions":[]},destination/"inspect")
            native=execute_job(inspect,app)
            if parsed["kind"]=="inspect":
                value=core.summarize(native)
            else:
                snap=core.check_snapshot(native)
                actions=resolve_actions(parsed,snap)
                prepared=core.emit({"schema":core.VERSION,"job_id":uuid.uuid4().hex,"actions":actions,"guard":{"session":snap["session"],"signature":snap["signature"]}},destination/"apply")
                native=execute_job(prepared,app)
                value=core.summarize(native)
            value.update(native_readback_verified=True,engine="deterministic_rules",model_called=False,job_directory=str(destination))
        print(json.dumps(value,ensure_ascii=False,allow_nan=False))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({"status":"error","error":str(exc),"automatic_retry":False},ensure_ascii=False))
        return 2


if __name__=="__main__":
    sys.exit(main())
