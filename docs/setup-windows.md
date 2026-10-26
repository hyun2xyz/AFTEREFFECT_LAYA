# Windows에서 처음 준비하기

[START-HERE](../START-HERE.md)대로 포크해서 받은 저장소 폴더를 에이전트와
**Windows PowerShell**의 작업 폴더로 선택합니다. 로컬 AE 조작에는 Windows Python을
사용합니다. WSL/Linux나 원격 서버에서 학생의 AE를 조작하는 과정이 아닙니다.
기본 과정에는 MCP·COLMAP·FFmpeg·모델·추가 pip 패키지가 필요하지 않습니다.

## 1. Python 3.13 x64 준비

지원·테스트 버전은 **3.12와 3.13**, 처음 설치할 때는 **3.13**을 권장합니다.
[Python 공식 Windows 다운로드](https://www.python.org/downloads/windows/)에서 3.13의
**Windows installer (64-bit)** 전체 설치기를 선택합니다. embeddable/source ZIP을
고르지 않습니다. 설치 화면과 OS 권한·약관 확인은 학생이 직접 진행합니다.
설치 후 새 터미널에서 버전을 확인합니다.

```powershell
py -3.13 --version
```

`py`가 없으면 설치한 `python.exe`의 실제 절대 경로를 `& 'C:\actual\python.exe'`처럼
실행합니다. 이후의 `py -3.13`을 그 경로로 바꾸면 됩니다. 에이전트 프로세스가 설치 전
환경을 유지하고 있다면 새 터미널을 열거나 정확한 실행 파일 경로를 사용합니다.

## 2. 이 폴더의 가상환경

```powershell
py -3.13 -B scripts\setup_environment.py --check
py -3.13 -B scripts\setup_environment.py --prepare
```

`--check`는 읽기 전용이며 빠진 항목이 있으면 종료 코드 `1`과 현재 상태를 보여 줍니다.
`--prepare`는 이 폴더의 `.venv`만 만들고 pip나 패키지를 설치하지 않습니다.
AE가 없어도 이 단계와 미리보기는 가능합니다. 기존 가상환경이 손상되었거나 다른 경로/
버전이면 보존하고 오류를 알립니다. 자동 삭제·업그레이드하지 않습니다.
다른 컴퓨터에서 복사한 `.venv` 대신 현재 컴퓨터에서 새로 준비합니다.
이후 실행 파일은 **`.\.venv\Scripts\python.exe`**이며 activation이나 실행 정책 변경은 필요하지 않습니다.

## 3. After Effects 설치와 경로 선택

[Adobe 공식 Creative Cloud 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)에
따라 학생의 계정·라이선스로 **AE 24 이상**을 준비합니다. 로그인·유료 계약·EULA와
최초 실행은 학생이 직접 처리합니다. 모든 OS 설치 단계를 무인 진행한다고 보장하지 않습니다.

`--check`의 후보를 확인하고 의도한 버전의 **실제 `AfterFX.exe`**를 선택합니다.
아래는 기본 설치의 예시이며 버전과 실제 위치로 바꿉니다. `.cmd`나 `aerender.exe`가 아닙니다.

```powershell
& .\.venv\Scripts\python.exe -B scripts\setup_environment.py --configure `
  --app 'C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.exe'
& .\.venv\Scripts\python.exe -B scripts\setup_environment.py --check
```

경로는 gitignored `tools.local.json`의 `ae_app`에만 UTF-8로 저장됩니다.
선택 순서는 `--app` → `AE_APP` 환경변수 → 이 설정 파일 → OS 기본 후보입니다.
오래된 `AE_APP`가 있으면 값을 확인합니다. 경로 검사는 AE를 실행하지 않으며
라이선스·버전·실제 조작의 통과를 뜻하지 않습니다.

## 4. 미리보기 → 상태 확인 → 첫 컴프

```powershell
& .\.venv\Scripts\python.exe -B scripts\terminal.py --list
& .\.venv\Scripts\python.exe -B scripts\terminal.py --dry-run '컴포지션 1920x1080 24fps 5초 만들어줘'
```

위 두 명령은 AE를 호출하지 않습니다. 실제 실행 전에 AE의 **편집 → 환경설정 →
스크립팅 및 표현식**에서 **Allow Scripts to Write Files and Access Network** 항목을
학생이 확인·허용합니다. 상태 확인도 로컬 결과 JSON을 쓰므로 파일 쓰기 권한이 필요합니다.
이 starter는 네트워크 통신에 이 권한을 사용하지 않습니다.
[Adobe 스크립트 설정](https://helpx.adobe.com/after-effects/desktop/automate-in-after-effects/automate-animation/scripts.html).
helper가 AE 설정이나 Windows 보안 설정을 바꾸지는 않습니다.

Codex처럼 샌드박스 안에서 명령을 실행하는 에이전트에서는 `AfterFX.exe -r` 호출이 막힙니다.
AE를 실제로 조작하는 명령은 에이전트가 승인을 요청해 **샌드박스 밖에서** 실행하고, 학생은 어떤
문장을 보내는 명령인지 확인한 뒤 승인합니다. 보안 설정 자체를 끄지 않습니다. 승인 전에 막혀
실패한 명령은 AE에 닿지 않았으므로 승인 후 같은 문장으로 한 번 다시 실행하면 됩니다.

```powershell
& .\.venv\Scripts\python.exe -B scripts\terminal.py --out-root "$PWD\work\lesson01" '현재 상태 보여줘'
& .\.venv\Scripts\python.exe -B scripts\terminal.py --out-root "$PWD\work\lesson01" '컴포지션 19201090 만들어줘'
```

첫 명령은 프로젝트를 바꾸지 않는 조회, 둘째는 1920×1090 컴프 생성(기본 30fps/10초)입니다. native readback과
실제 화면을 확인해야 완료입니다. 자동 저장·닫기·렌더하지 않습니다. Windows AE의
실제 조작은 이 컴퓨터에서 따로 검증하며 미검증/부분 결과를 성공으로 해석하지 않습니다.

원할 때만 다음 명령으로 `laya-ae.cmd` 실행기를 추가합니다. 기본 설치는 기존 `laya`를 바꾸지 않습니다.

```powershell
& .\.venv\Scripts\python.exe -B scripts\install_terminal.py --install
& 'C:\actual\output-bin\laya-ae.cmd' --list
```

마지막 경로는 설치 출력으로 바꿉니다. **`.cmd`는 Python 파일이 아니므로 `python laya-ae.cmd`로
실행하지 않습니다.** PowerShell에서는 위처럼 `&`와 경로로 호출합니다.
명령·복구는 [commands](commands.md), 선택 Laya는 [laya](laya.md)를 따릅니다.
