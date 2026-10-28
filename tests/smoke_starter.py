#!/usr/bin/env python3
"""Run the source-folder starter with no Git, packages, model or native AE call."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def command(argv, cwd, expected=(0,)):
    run=subprocess.run([str(x) for x in argv],cwd=cwd,capture_output=True,encoding="utf-8",timeout=60,
                       env={**os.environ,"PYTHONIOENCODING":"utf-8"})
    if run.returncode not in expected:
        raise RuntimeError(f"command exited {run.returncode}: {run.stdout}\n{run.stderr}")
    return json.loads(run.stdout)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    if out.exists():raise ValueError("Use a new smoke folder; previous logs are preserved")
    out.mkdir(parents=True)
    source=out/"student's 한글 starter"
    source.mkdir()
    for name in ("scripts","docs","tests",".agents"):
        shutil.copytree(ROOT/name,source/name,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    for name in ("README.md","START-HERE.md","AGENTS.md","LICENSE","THIRD_PARTY_NOTICES.md",".gitignore"):
        shutil.copy2(ROOT/name,source/name)
    assert not (source/".git").exists()
    prepared=command([sys.executable,"-S","-B","scripts/setup_environment.py","--prepare"],source)
    assert prepared["prepared"] and not prepared["packages_installed_by_helper"]
    python=Path(prepared["venv"]["python"])
    probe=command([python,"-I","-B","-c","import json,importlib.util; print(json.dumps({x:importlib.util.find_spec(x) is not None for x in ['pip','laya_mlx','torch','PIL']}))"],source)
    assert not any(probe.values()),probe
    state=command([python,"-S","-B","scripts/setup_environment.py","--check"],source,(0,1))
    assert state["ready_for_dry_run"] and state["native_ae"]=="not_verified"
    preview=command([python,"-S","-B","scripts/terminal.py","컴포지션","19201090","만들어줘","--dry-run"],source)
    assert preview["status"]=="preview" and not preview["executed"] and not preview["model_called"]
    assert preview["plan"]["actions"][0]["height"]==1090
    config,bin_dir,backups=out/"local config",out/"local bin",out/"local backups"
    install=command([python,"-S","-B","scripts/install_terminal.py","--install","--python",python,
                     "--bin-dir",bin_dir,"--config-dir",config,"--backup-dir",backups],source)
    assert install["status"]=="installed"
    launcher=bin_dir/("laya-ae.cmd" if os.name=="nt" else "laya-ae")
    listing=command([launcher,"--list"],source)
    assert listing["status"]=="commands"
    assert {"배경색 초록색으로 만들어줘", "배경색 빨간색으로 바꿔줘", "솔리드 하나 만들어줘"} <= set(listing["examples"])
    unicode_preview=command([launcher,"텍스트","안녕하세요","추가해줘","--dry-run"],source)
    assert unicode_preview["plan"]["actions"][0]["text"]=="안녕하세요"
    color_preview=command([launcher,"배경색","빨간색으로","바꿔줘","--dry-run"],source)
    assert color_preview["plan"]["actions"][0]["changes"]["background_color"]==[1,0,0]
    solid_preview=command([launcher,"솔리드","하나","만들어줘","--dry-run"],source)
    assert solid_preview["plan"]["actions"][0]["op"]=="add_solid"
    report={"source_zip_style":"passed","git_required":False,"pip_required":False,"model_required":False,
            "venv_isolated":True,"local_launcher_executed":True,"korean_args":"passed",
            "native_AE":"not_run","os_installers":"not_run","python":sys.version.split()[0]}
    (out/"smoke-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))


if __name__=="__main__":main()
