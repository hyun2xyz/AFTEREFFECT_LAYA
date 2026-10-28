# 한국어 터미널 명령

`laya-ae`는 이 저장소의 기본 명령이다. launcher를 설치하지 않아도
`.venv`의 Python으로 `scripts/terminal.py`에 같은 인자를 전달하면 된다.
아래 `laya-ae`는 설치기가 출력한 실제 실행 경로로 대신할 수 있다.
Windows PowerShell은 `& "C:\actual\path\laya-ae.cmd" ...` 형태를 쓴다.
Mac에서 기존 Laya-Mac과 선택 연결했을 때만 `laya ae ...`도 지원한다.

```sh
laya-ae --list
laya-ae 컴포지션 19201090 만들어줘
laya-ae 컴포지션 1920x1080 24fps 5초 만들어줘
laya-ae 배경 색 초록색으로 바꿔줘
laya-ae 배경색 초록색으로 만들어줘
laya-ae 배경색 빨간색으로 바꿔줘
laya-ae '배경색 #224466으로 바꿔줘'
laya-ae 텍스트 안녕하세요 추가해줘
laya-ae 널 추가해줘
laya-ae 3D 널 추가해줘
laya-ae 솔리드 하나 만들어줘
laya-ae 솔리드 빨간색으로 만들어줘
laya-ae 선택 레이어 이름 타이틀로 바꿔줘
laya-ae 선택 레이어 위치 960 540으로 바꿔줘
laya-ae 선택 레이어 크기 50 50으로 바꿔줘
laya-ae 선택 레이어 회전 45도로 바꿔줘
laya-ae 선택 레이어 불투명도 50으로 바꿔줘
laya-ae 선택 레이어 숨겨줘
laya-ae 선택 레이어 켜줘
laya-ae 선택 레이어 불투명도 0초 0 1초 100 키프레임 만들어줘
laya-ae 현재 상태 보여줘
```

실행 전에 `--dry-run`을 붙이면 앱에 명령을 보내지 않고 해석한 값만 확인한다.
컴프 생성은 아래 축약형도 지원한다. AE 앱 이름을 앞에 붙일 수 있으며,
정확한 명령과 숫자만 있는 경우 `만들어줘`를 생략할 수 있다.

```sh
laya-ae comp 1920 1080
laya-ae 애프터이펙트 컴포지션 1920 1080
laya-ae 컴포지션 19201080
```

`19201090`은1920×1090이며 `1920x1080`과 다르다. 생략한 기본값은30fps/10초다.
레이어 위치·크기는2D에서 두 수,3D에서 세 수를 쓴다. 크기는%, 회전은도,
불투명도는0~100이다. 위 자연어 키프레임은 불투명도 두 점만 지원하며,
다른 속성과 여러 점은 아래 JSON 배치로 명시한다.

배경색은 `CompItem.bgColor` 설정이다. 불투명한 렌더 배경 레이어를 만들지 않으며,
투명 격자나 화면을 덮는 레이어가 켜져 있으면 색 변화가 바로 보이지 않을 수 있다.
초록색/녹색, 빨강색/빨간색, 파랑색/파란색, 검정색/검은색, 흰색/하얀색,
노랑색/노란색을 지원한다. 띄어쓰기가 없어도 `만들어줘`와 `바꿔줘`를 인식한다.
활성 컴포지션이 없다면 AE에서 작업할 컴포지션의 타임라인이나 화면을 클릭한다.
솔리드는 현재 컴프 크기와 길이의 불투명 레이어로 추가된다. 색을 지정하지 않으면 흰색이다.
자연어는 위의 고정 문형만 지원한다. 질문·부정·지원하지 않는 요청은 실행하지 않는다.
불확실한 요청을 Laya가 인식해도 자동 조작으로 연결하지 않는다.

## 설치와 복원

저장소 최상위 폴더에서 실행한다. `python`은 이 프로젝트 `.venv`의 실행 파일이다.

```sh
python -B scripts/install_terminal.py --check
python -B scripts/install_terminal.py --install
```

Windows는 설치 결과의 `laya-ae.cmd`, Mac은 `laya-ae`를 사용한다.
출력된 bin 경로가 PATH에 없으면 실행 파일의 절대 경로를 사용한다.
Mac의 기존 Laya-Mac이 있고 그 명령을 보존하며 연결하려는 Mac에서만:

```text
python -B scripts/install_terminal.py --install --integrate-laya --legacy-script /absolute/laya-mac/laya_mac/cli.py --legacy-python /absolute/python
```

installer는 바뀌는 파일을 백업하고 복원 receipt를 출력한다. 새 터미널에서 명령을
사용한다. `--restore /absolute/receipt.json`은 설치 후 다른 편집이 없는 파일만 복원한다.
Python/AE를 설치하거나 모델을 다운로드하는 installer는 아니다.

### 기존 터미널이 시스템 상태만 보여 줄 때

`Laya-Mac 완료`, `system → get_system_stats`는 AE 컴프 생성 결과가 아니다.
이미 열린 셸에는 예전 alias가 남아 있을 수 있다. 기존 `laya`를 연결 설치한 Mac은
새 터미널을 열거나 `source ~/.zshrc`로 갱신하고 `laya ae --list`로 연결을 확인한다.
`laya-ae`의 설치 출력 경로로 직접 실행하면 예전 alias를 거치지 않는다.
지원하지 않는 AE 문장은 오류로 반환하며 시스템 상태 조회로 성공 처리하지 않는다.

## 여러 조작을 한 번에

```sh
python scripts/ae_basic.py prepare-inspect --out /absolute/jobs/inspect01
# generated run.jsx를 AE에서 실행한 뒤
python scripts/ae_basic.py result /absolute/jobs/inspect01/result.json
python scripts/ae_basic.py catalog --op set_transform
python scripts/ae_basic.py prepare --snapshot /absolute/jobs/inspect01/result.json --input /absolute/actions.json --out /absolute/jobs/batch01
```

`actions.json`의 예시:

```json
{"actions":[
  {"op":"create_comp","ref":"c","name":"Lesson","width":1920,"height":1080,"fps":24,"duration":5},
  {"op":"set_comp","comp":"@c","changes":{"background_color":[0,1,0]}},
  {"op":"add_text","comp":"@c","ref":"t","name":"Title","text":"안녕하세요","font_size":72},
  {"op":"set_transform","comp":"@c","layer":"@t","values":{"position":[960,540]}},
  {"op":"set_keyframes","comp":"@c","layer":"@t","property":"opacity","keys":[{"time":0,"value":0},{"time":1,"value":100}]}
]}
```

기존 대상은 최신 snapshot의 `active_comp.id`와 `layers[].id`를 숫자로 지정한다.
`@c/@t`는 같은 배치에서 먼저 만든 항목의 참조다. 최대32조작/속성당200키다.
`run.jsx`를 한 번만 실행하고 `result`로 native readback을 대조한다.
기존 애니메이션의 정적 덮어쓰기·분리 위치·카메라/라이트 변형은 이 starter의 범위 밖이다.

공식 근거: [Adobe 스크립트 실행](https://helpx.adobe.com/after-effects/desktop/automate-in-after-effects/automate-animation/scripts.html).
Mac의 `DoScriptFile`은 설치된 AE의 `Contents/Resources/ae.sdef`에서도 확인한다.
