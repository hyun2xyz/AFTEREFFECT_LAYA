# 선택 수업: 로컬 Laya 분류

**첫 AE 실습은 이 문서 없이 완료한다.** 지원하는 명령은 고정 규칙으로 처리한다.
짧지만 애매한 분류 요청을 여러 번 비교하려는 학생이 선택했을 때만 준비한다.
Laya는 Jev의 공식 가중치 공개판이 아니라 비슷한 typed-decision 용도의 독립 모델이다.

이 starter의 분류기는 **Apple Silicon Mac / macOS14+ / Python3.12·3.13**의
`laya-mlx==0.1.0` 경로를 기준으로 한다. Windows·Intel Mac·Metal이 없는 호스트는
기본 명령과 주 에이전트 판단을 계속 사용한다. Windows MLX 추론을 보장하지 않는다.

## 학생이 선택한 경우에만 설치

기본 `.venv`는 그대로 두고 별도 환경을 만든다. 아래 `python3.13`은 setup에서 찾은
실제 설치 Python으로 대체할 수 있다. 모델은 Git 밖의 충분한 저장 위치를 정한다.

```sh
python3.13 -m venv .venv-laya
.venv-laya/bin/python -m pip --isolated --require-virtualenv install --no-user laya-mlx==0.1.0
```

이 선택 과정은 pip 패키지와 모델을 다운로드한다. 기본 설치기가 자동 실행하지 않는다.
런타임은 `mlx>=0.32.2,<0.33` 등의 별도 의존성을 갖는다. API 키는 기본 AE 명령에 필요 없다.

에이전트는 다음을 `work/download_laya.py` 같은 별도 파일로 저장하고,
`.venv-laya/bin/python`으로 실행할 수 있다. 기존 폴더는 덮어쓰지 않는다.

```python
from pathlib import Path
import hashlib
import shutil
from huggingface_hub import snapshot_download

root = Path("models/laya").resolve()  # ignored; use the student's chosen volume
pristine, runtime = root / "pristine", root / "runtime"
if pristine.exists() or runtime.exists():
    raise SystemExit("Choose new folders; preserve the existing snapshot")
snapshot_download(
    repo_id="aac6fef/laya-multilingual-mlx",
    revision="f2b4faf51023039425946074e2cf1361d2db11d5",
    local_dir=pristine,
)  # preserve the complete snapshot, including LICENSE/NOTICE/model card
required = ["model.safetensors", "rl_agent_config.json", "encoder/config.json",
            "tokenizer/tokenizer.json", "tokenizer/tokenizer_config.json",
            "LICENSE", "NOTICE", "README.md"]
missing = [name for name in required if not (pristine / name).is_file()]
if missing:
    raise SystemExit("Incomplete snapshot: " + str(missing))
with (pristine / "model.safetensors").open("rb") as f:
    print("model SHA256:", hashlib.file_digest(f, "sha256").hexdigest())
shutil.copytree(pristine, runtime)
print("runtime:", runtime)
```

원본과 실행 사본을 두므로 모델 두 벌의 디스크 여유가 필요하다. 모델 카드·고지와
revision을 보존한다. Git에 가중치나 계정 토큰을 넣지 않는다. 다운로드가 실패하면
기본 AE 실습으로 돌아갈 수 있으며 다른 모델/원격 API로 몰래 전환하지 않는다.

## 준비 확인과 짧은 분류

```sh
.venv-laya/bin/python -B scripts/laya_route.py --doctor --model /absolute/models/laya/runtime
```

`doctor`는 런타임/필수 파일만 확인하며 실제 추론 성공을 뜻하지 않는다.
짧은 요청1~8개, 각400자 이하를 `work/requests.json`에 저장한다.

```json
["현재 컴포지션을 확인해 줘", "텍스트 레이어를 넣는 방법을 설명해 줘"]
```

```sh
.venv-laya/bin/python -B scripts/laya_route.py --requests /absolute/work/requests.json --model /absolute/models/laya/runtime --device gpu
```

모델은 고정 작업 종류와 `run/explain/cancel`을 **조언만** 한다. 인자·경로·JSX·권한은
만들지 않는다. 명확한 터미널 명령은 이 모델을 부르지 않는다. 긴 문서/영상/개인 정보를
넣지 않고 필요한 짧은 사실만 사용한다. 토큰 초과·잘림·잘못된 확률·백엔드 오류는 기권이다.
`concentration`은 엔트로피 기반 집중도이며 정답률이 아니다. 실제 모델의 인용문/분류 오판
사례가 있어 실행 여부는 원문과 사용자 의사로 확인한다. 모델 추천만으로 앱을 변경하지 않는다.

원본 출처: [Laya](https://github.com/NandhaKishorM/laya),
[Laya-MLX0.1.0](https://pypi.org/project/laya-mlx/0.1.0/),
[런타임 코드](https://github.com/mizorewww/laya-mlx),
[고정 모델 snapshot](https://huggingface.co/aac6fef/laya-multilingual-mlx/tree/f2b4faf51023039425946074e2cf1361d2db11d5).
코드·모델의 Apache-2.0 고지를 각각 보존한다. 새 환경에서 이 설치/추론 경로를 실행한
범위와 기존 Mac 검수 결과는 [검증 기록](validation.md)으로 구분한다.
