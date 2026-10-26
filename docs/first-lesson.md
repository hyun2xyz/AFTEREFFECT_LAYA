# 첫 수업: 새 컴프와 초록 배경

현재 OS setup을 마친 뒤 저장소 최상위에서 실행합니다. 아래 `python`은 Mac의
`.venv/bin/python`, Windows의 `.\.venv\Scripts\python.exe`입니다. 환경 activation은
필요하지 않습니다. 에이전트가 실제 경로를 채워 실행할 수 있습니다.

## 1. 명령을 보내기 전에

```sh
python -B scripts/terminal.py 컴포지션 19201090 만들어줘 --dry-run
```

`status: preview`, `executed: false`, `model_called: false`와 **1920×1090**을
확인합니다. 이 단계는 AE를 열거나 조작하지 않습니다.

## 2. 실제 AE 상태 확인

학생의 AE를 열고 사용할 프로젝트를 확인합니다. 다른 미저장 프로젝트가 있다면
그대로 보존합니다. 여러 AE 버전이 있으면 setup에서 정확한 앱 경로 하나를 설정합니다.

```sh
python -B scripts/terminal.py 현재 상태 보여줘
```

Mac 자동화 권한 또는 AE 스크립트 파일 쓰기 권한이 막히면 OS setup의 설명대로
처리합니다. 종료 코드0만 보지 말고 `status: ok`, 실제 `native_AE`와
`native_readback_verified: true`를 확인합니다. 활성 컴프가 없으면 null일 수 있습니다.

## 3. 새 항목 두 단계

```sh
python -B scripts/terminal.py 컴포지션 19201090 만들어줘
python -B scripts/terminal.py 배경 색 초록색으로 바꿔줘
```

새 `Laya AE` 컴프는1920×1090/30fps/10초입니다. 매번 새 항목을 만들며 같은 이름의
이전 컴프를 덮어쓰지 않습니다. 배경 명령은 **현재 활성 컴프**를 바꾸므로 학생이
그사이에 다른 컴프를 골랐다면 현재 대상을 먼저 확인합니다.

두 명령 모두 native 결과를 읽고 요청 값과 대조합니다. 컴프 패널을 실제로 보고 크기와
초록색을 확인합니다. 투명 격자 또는 화면을 덮는 레이어가 있으면 배경색이 보이지 않을
수 있습니다. 이 설정은 불투명한 배경 솔리드 레이어를 만드는 기능과 구분합니다.

`job_directory`에 명령·고정 JSX·실제 결과가 남습니다. `partial`, timeout 또는
receipt 누락은 성공이 아니며 이미 일부 변경이 있을 수 있습니다. 재실행하기 전에
기존 job과 현재 상태를 읽습니다. undo group은 일괄 롤백을 보장하지 않습니다.

기본 경로는 프로젝트를 저장·닫거나 렌더하지 않습니다. 학생은 실제 결과를 확인한 뒤
원하는 위치에 직접 저장할 수 있습니다. 다음 수업에서는 텍스트나 널 중 하나만 골라
추가하고, 레이어 선택·속성·키프레임의 차이를 배웁니다.
