# AFTEREFFECT_LAYA

**빈 Mac·Windows에서 설치 안내부터 첫 After Effects 명령까지.**
Codex·Claude Code와 함께 작은 스크립트를 읽고 바꾸며 배우는 수업용 출발점입니다.

[소스 ZIP 받기](https://github.com/hyun2xyz/AFTEREFFECT_LAYA/archive/refs/heads/main.zip)
→ 압축 해제 → 로컬 Codex에서 폴더 열기 → **[START-HERE.md](START-HERE.md)**.
Git과 전역 스킬 설치는 필요하지 않습니다.

첫 실습은 **Python3.13(또는3.12) + 정식 AE24 이상**만 준비합니다.
기본 조작은 Python 표준 라이브러리와 고정 JSX로 실행하며, pip 패키지·모델 가중치·
MCP·서버·Homebrew를 설치하지 않아도 됩니다. Adobe 앱/라이선스는 별도입니다.

```sh
# Mac 예시: 설치 안내를 마친 뒤, 이 폴더에서
.venv/bin/python -B scripts/terminal.py 컴포지션 19201090 만들어줘
.venv/bin/python -B scripts/terminal.py 배경 색 초록색으로 바꿔줘
```

Windows에서는 `.\.venv\Scripts\python.exe`로 같은 스크립트를 실행합니다.
선택 설치한 `laya-ae`/`laya-ae.cmd`로도 같은 문장을 쓸 수 있습니다.
이미 Laya-Mac이 있는 Mac만 기존 `laya`와 연결할 수 있습니다.

| 순서 | 지금 읽을 문서 |
| --- | --- |
| 1. 설치·시작 문장 | [START-HERE](START-HERE.md) |
| 2. 현재 OS 준비 | [Mac](docs/setup-macos.md) · [Windows](docs/setup-windows.md) |
| 3. 첫 컴프와 초록 배경 | [첫 수업](docs/first-lesson.md) |
| 4. 필요한 명령 하나 | [명령어 목록](docs/commands.md) |
| 5. 요청했을 때만 로컬 분류 | [선택 Laya](docs/laya.md) |
| 실제로 확인한 범위 | [validation](docs/validation.md) |

`19201090`은 **1920×1090**, 생략한 값은30fps/10초입니다. 명령은 현재 활성 컴프와
선택 레이어를 대상으로 하며 `--dry-run`은 앱을 바꾸지 않습니다. 배경색 명령은
컴포지션 설정을 바꿉니다. 불투명한 렌더 배경 레이어를 자동으로 만들지 않습니다.

Laya는 Jev와 비슷한 구조화된 판단을 제공하는 독립 오픈 모델입니다. 이 starter에서는
애매한 짧은 요청의 분류에만 선택적으로 씁니다. 명확한 지원 명령은 모델을 호출하지
않으며, 자유로운 한국어로 AE의 모든 기능을 조작하는 도구는 아닙니다.
토큰 절감률을 약속하거나 Laya 추천을 실행 승인으로 사용하지 않습니다.

Mac은 AE의 `DoScriptFile`, Windows는 `AfterFX.exe -r`로 고정 JSX를 전달하고 native
결과 파일을 읽습니다. 자동 저장·닫기·삭제·렌더는 제공하지 않습니다. 실패·부분 실행·
결과 미확인에는 같은 job을 재전송하지 않습니다.

공용 Python 코드와 Mac AE의 실제 확인을 구분합니다. Windows AE 앱은 수강생 컴퓨터에서
첫 native 검수를 합니다. 원본·개인 작업·모델은 Git에 올리지 않습니다.

새 기능은 한 번에 하나씩, 학생의 실제 요청과 검수 결과를 바탕으로 추가하세요.
이 폴더 전체가 프로젝트 스킬이며 다른 개인 하네스를 설치하지 않습니다.
