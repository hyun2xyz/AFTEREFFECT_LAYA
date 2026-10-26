# Mac에서 처음 준비하기

[START-HERE](../START-HERE.md)대로 포크해서 받은 저장소 폴더를 Codex/Claude Code에
엽니다. 모든 명령은 그 폴더에서 실행합니다. 기본 과정은 Python 표준 라이브러리만 쓰며
MCP·COLMAP·FFmpeg·모델 가중치가 필요하지 않습니다.

## 1. Python 3.13 준비

지원·테스트 버전은 **3.12와 3.13**, 처음 설치할 때는 **3.13**을 권장합니다.
[Python 공식 macOS 다운로드](https://www.python.org/downloads/macos/)에서 3.13 출시를
선택하고 **macOS 64-bit universal2 전체 설치기 `.pkg`**를 받습니다. source 압축 파일을
고르지 않습니다. 설치 화면의 OS 권한·확인은 학생이 직접 진행합니다.
[공식 설치 설명](https://docs.python.org/3.13/using/mac.html)은 Apple Silicon/Intel용
universal2와 설치기 서명 확인 방법을 안내합니다.

```sh
python3.13 --version
```

명령이 없으면 설치한 실행 파일의 실제 경로를 사용합니다. python.org 기본 설치의 예는
`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13`입니다. 공통강의에서
Homebrew를 설치했다면 [python@3.13](https://formulae.brew.sh/formula/python@3.13) 설치를 선택할 수
있습니다. 이 수업을 위해 Homebrew를 따로 설치할 필요는 없습니다.

## 2. 이 폴더의 가상환경

```sh
python3.13 -B scripts/setup_environment.py --check
python3.13 -B scripts/setup_environment.py --prepare
```

`--check`는 읽기 전용입니다. AE나 가상환경이 아직 없으면 종료 코드 `1`과 빠진 항목을
보여 줍니다. `--prepare`는 이 폴더의 `.venv`만 만들며 pip와 패키지를 설치하지 않습니다.
AE가 없어도 준비할 수 있습니다. 기존 환경이 손상되었거나 다른 경로/버전이면 자동으로
지우거나 덮어쓰지 않습니다. 다른 컴퓨터의 `.venv`를 복사해 배포하지 않습니다.
이후 `python`은 **`.venv/bin/python`**이며 activation은 필요하지 않습니다.

## 3. After Effects 설치와 경로 선택

[Adobe 공식 Creative Cloud 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)에서
학생의 계정·라이선스로 **AE 24 이상**을 준비합니다. 로그인·결제·약관 동의와 최초 실행은
학생이 직접 합니다. 빈 컴퓨터에서 이 절차까지 모두 무인 설치된다고 약속하지 않습니다.

`--check`의 후보 경로를 확인하고 의도한 버전의 **전체 AE `.app`**을 선택합니다.
아래 경로는 예시입니다. Render Engine을 선택하지 않습니다.

```sh
.venv/bin/python -B scripts/setup_environment.py --configure \
  --app '/Applications/Adobe After Effects 2026/Adobe After Effects 2026.app'
.venv/bin/python -B scripts/setup_environment.py --check
```

설정은 gitignored `tools.local.json`의 `ae_app`에만 UTF-8로 저장됩니다.
경로 우선순위는 `--app` → `AE_APP` 환경변수 → 이 설정 파일 → OS 기본 후보입니다.
기존 `AE_APP`가 다른 버전을 가리키면 먼저 확인합니다. 경로 검사는 AE를 실행하지 않으며
라이선스·버전·권한·실제 조작까지 검증한 것은 아닙니다.

## 4. 미리보기 → 상태 확인 → 첫 컴프

먼저 앱을 호출하지 않는 미리보기를 실행합니다.

```sh
.venv/bin/python -B scripts/terminal.py --list
.venv/bin/python -B scripts/terminal.py --dry-run '컴포지션 1920x1080 24fps 5초 만들어줘'
```

실제 상태 확인은 로컬 결과 JSON을 기록합니다. AE 설정의 **스크립팅 및 표현식**에서
**Allow Scripts to Write Files and Access Network** 항목을 학생이 확인·허용해야 합니다.
이 starter는 그 권한으로 로컬 결과 파일을 쓰며 네트워크 통신을 하지 않습니다.
[Adobe 스크립트 설정](https://helpx.adobe.com/after-effects/desktop/automate-in-after-effects/automate-animation/scripts.html).
첫 호출에서 macOS가 요청하면 실제 실행 주체인 Codex/Terminal 등의 AE 제어를 학생이
승인합니다. 위치는 **시스템 설정 → 개인정보 보호 및 보안 → 자동화**입니다.
[Apple 자동화 권한](https://support.apple.com/en-au/guide/mac-help/mchl07817563/mac).
helper가 이 권한들을 바꾸지는 않습니다.

Codex처럼 샌드박스 안에서 명령을 실행하는 에이전트에서는 AE로 보내는 Apple 이벤트가 막힙니다.
AE를 실제로 조작하는 명령은 에이전트가 승인을 요청해 **샌드박스 밖에서** 실행하고, 학생은 어떤
문장을 보내는 명령인지 확인한 뒤 승인합니다. 보안 설정 자체를 끄지 않습니다. 승인 전에 막혀
실패한 명령은 AE에 닿지 않았으므로 승인 후 같은 문장으로 한 번 다시 실행하면 됩니다.

```sh
.venv/bin/python -B scripts/terminal.py --out-root "$PWD/work/lesson01" '현재 상태 보여줘'
.venv/bin/python -B scripts/terminal.py --out-root "$PWD/work/lesson01" '컴포지션 19201090 만들어줘'
```

첫 명령은 프로젝트를 바꾸지 않는 상태 확인, 둘째는 1920×1090 컴프 생성(기본 30fps/10초)입니다. 요청 값과
native readback·실제 화면이 일치할 때 완료입니다. 자동 저장·닫기·렌더는 하지 않습니다.
결과가 `unknown/partial`이면 job 경로를 먼저 보고 무작정 재실행하지 않습니다.

원할 때만 `.venv/bin/python -B scripts/install_terminal.py --install`로 `laya-ae` 실행기를
추가합니다. 출력된 절대 경로로 실행할 수 있으며 기본 설치는 기존 `laya`를 바꾸지 않습니다.
명령과 백업 복구는 [commands](commands.md), 선택 Laya는 [laya](laya.md)를 따릅니다.
