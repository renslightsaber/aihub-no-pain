# aihub-repair

> **AI Hub 데이터셋 다운로드 검증 + 자동 복구 스크립트 모음**
> 깨진 zip, 누락 파일, 잔재 파일을 자동으로 찾아 정리하고 재다운로드합니다.

[![Bash](https://img.shields.io/badge/Bash-4.0+-1f425f?logo=gnu-bash&logoColor=white)](https://www.gnu.org/software/bash/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20WSL2-blue)]()

---

## 🎯 이게 왜 필요한가요?

AI Hub의 `aihubshell`로 대용량 데이터셋을 다운로드하다 보면 다음과 같은 문제가 자주 발생합니다:

- **디스크 부족 / 네트워크 끊김**으로 일부 zip이 깨지거나 `.part0`, `.part1073741824` 같은 잔재 파일이 남음
- **`Ctrl+C`가 안 먹혀** 다운로드를 강제 종료한 후 어느 파일이 정상인지 모름
- **`aihubshell`이 byte-level resume을 지원하지 않아** 처음부터 다시 받아야 함
- 수백 개 zip 중 어떤 게 누락됐는지 찾기 어려움

`aihub-repair`는 위 문제들을 **세 가지 스크립트의 조합**으로 해결합니다.

---

## ✨ 핵심 기능

### 🔍 [`check_aihub.sh`](./check_aihub.sh) — 빠른 진단 (수 초)
filelist와 디스크를 비교해서 누락 파일, part 잔재, `download.tar` 잔재를 식별합니다.
누락된 파일의 **이름·용량·filekey**를 한눈에 보여주고 복구 명령어까지 자동 생성합니다.

### 🔬 [`verify_zips.sh`](./verify_zips.sh) — 병렬 무결성 검증
모든 zip 파일을 병렬로 `unzip -tq` 검증합니다.
깨진 zip의 **이름·용량·filekey**를 출력하고 정확히 어떤 filekey를 재다운로드하면 되는지 알려줍니다.

### 🔧 [`repair_aihub.sh`](./repair_aihub.sh) — 자동 복구
검증과 정리, 재다운로드를 한 번에 수행합니다. 5가지 케이스 모두 처리:
- `broken` (zip 깨짐) → 재다운로드
- `missing` (part만 있고 zip 없음) → 잔재 정리 + 재다운로드
- `residue_only` (zip 정상 + part 잔재) → part만 정리
- `never_downloaded` (filelist에 있는데 디스크에 없음) → 재다운로드
- `download.tar` 잔재 → 정리

---

## 🚀 빠른 시작

### 1) 사전 준비
```bash
# aihubshell 설치 (AI Hub 공식 가이드 참고)
# https://aihub.or.kr/devsport/apishell/list.do

# API 키 환경변수 등록
export AIHUB_APIKEY='발급받은-API-키'
```

### 2) Repo clone + 권한 부여
```bash
git clone https://github.com/<your-username>/aihub-repair.git
cd aihub-repair
chmod +x check_aihub.sh verify_zips.sh repair_aihub.sh
```

### 3) 작업 디렉토리로 스크립트 복사
```bash
# 데이터셋이 있는 디렉토리로 이동 (또는 스크립트를 그곳으로 복사)
cp check_aihub.sh verify_zips.sh repair_aihub.sh /data1/your_dataset_dir/
cd /data1/your_dataset_dir/
```

### 4) filelist 한 번 떠두기 (필수)
```bash
# 데이터셋 번호(예: 71349)에 맞춰 filelist 생성
aihubshell -mode l -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY" > filelist_71349.txt
```

### 5) 진단 → 검증 → 복구
```bash
# 빠른 진단 (누락/잔재 확인)
./check_aihub.sh

# 무결성 검증 (깨진 zip 찾기)
./verify_zips.sh

# 이상 있으면 자동 복구 (먼저 dry-run으로 확인)
DRY_RUN=1 ./repair_aihub.sh
./repair_aihub.sh
```

> 📖 **상세 가이드**: [USAGE.md](./USAGE.md)에서 환경변수, 시나리오별 사용법, 트러블슈팅을 확인하세요.

---

## 🛠️ 주요 환경변수

세 스크립트 모두 동일한 환경변수 인터페이스를 사용합니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AIHUB_APIKEY` | (필수) | AI Hub API 키 |
| `DATASET_KEY` | `71349` | 데이터셋 번호 |
| `ROOT` | `./133.감성_및_발화_스타일_...` | 데이터 루트 디렉토리 |
| `FILELIST` | `filelist_${DATASET_KEY}.txt` | filelist 파일 경로 |
| `DRY_RUN` | `0` | `1`이면 검증만 (디스크 변경 X) |
| `PARALLEL` | `8` | (verify) 병렬 작업 수 |
| `BATCH` | `50` | (repair) 재다운로드 batch 크기 |
| `DEBUG` | `0` | `1`이면 파싱 진단 정보 출력 |

다른 데이터셋에 재활용:
```bash
DATASET_KEY=464 \
ROOT='/data1/.../464.다국어_통번역_음성_데이터' \
FILELIST='filelist_464.txt' \
./check_aihub.sh
```

---

## 📁 디렉토리 구조

```
aihub-repair/
├── README.md              # 이 파일
├── USAGE.md               # 상세 사용 가이드
├── check_aihub.sh         # 빠른 진단
├── verify_zips.sh         # 병렬 무결성 검증
├── repair_aihub.sh        # 자동 복구
└── LICENSE                # MIT
```

---

## 🧪 동작 원리 한눈에

```
   ┌─────────────────────────────────────────────────────────────┐
   │  매일 작업 전 → check_aihub.sh (수 초)                       │
   │       └─ filelist vs 디스크 비교 + 잔재 확인                  │
   └─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (이상 발견 시)
   ┌─────────────────────────────────────────────────────────────┐
   │  학습 시작 전 → verify_zips.sh (수 분~수십 분)                │
   │       └─ 모든 zip 병렬 무결성 검증                            │
   └─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (깨진 파일 발견 시)
   ┌─────────────────────────────────────────────────────────────┐
   │  복구 → repair_aihub.sh                                      │
   │       └─ 잔재 정리 + filekey batch 재다운로드                 │
   └─────────────────────────────────────────────────────────────┘
                          │
                          ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  재검증 → check_aihub.sh && verify_zips.sh                   │
   │       └─ 모두 ✓ 나오면 학습 시작 OK                          │
   └─────────────────────────────────────────────────────────────┘
```

---

## 🚧 요구사항

- **Bash 4.0+** (associative array 사용 — Ubuntu 18.04+, macOS는 `brew install bash` 필요)
- **UTF-8 로케일** (한글 파일명 처리)
- **`aihubshell`** ([AI Hub 공식 도구](https://aihub.or.kr/devsport/apishell/list.do))
- **`unzip`, `awk`, `grep`, `find`, `sed`, `xargs`** (대부분 Linux/macOS 기본 설치)

확인:
```bash
bash --version | head -1            # GNU bash, version 4.0+
locale | grep -E 'LANG|LC_ALL'       # UTF-8 포함
command -v aihubshell                # 경로 표시
```

---

## ❓ 자주 묻는 질문

**Q. 다른 AI Hub 데이터셋에도 쓸 수 있나요?**
A. 네. `DATASET_KEY`, `ROOT`, `FILELIST` 환경변수만 바꾸면 됩니다. zip 기반 데이터셋이면 거의 모두 호환.

**Q. 멀쩡한 데이터를 누락이라고 표시해요.**
A. v2부터는 filelist의 트리 문자(`│`, `├`, `─`)와 한글 사이 공백을 정규화로 처리합니다. `DEBUG=1 ./check_aihub.sh`로 파싱 결과를 확인하세요.

**Q. `Ctrl+C`로 aihubshell이 안 죽어요.**
A. `aihubshell`은 종종 SIGINT를 무시합니다. 다른 터미널에서 `pkill -9 -f aihubshell`로 강제 종료한 후 `./repair_aihub.sh`로 잔재 정리하세요.

**Q. `verify_zips.sh`가 오래 걸려요.**
A. 데이터셋 크기와 디스크 종류에 따라 5분~1시간. NFS는 NVMe보다 느려요. `PARALLEL=16`으로 늘리면 조금 빨라집니다.

> 더 자세한 트러블슈팅은 [USAGE.md의 트러블슈팅 섹션](./USAGE.md#-트러블슈팅)을 참고하세요.

---

## 🤝 기여

이슈와 PR을 환영합니다. 특히 다음 영역의 기여가 유용해요:
- 다른 AI Hub 데이터셋에서의 동작 검증 결과
- filelist 포맷이 다른 케이스 대응
- 검증 결과 캐싱 기능
- 진행률 표시 개선

---

## 📄 라이선스

MIT License — 자유롭게 사용/수정/배포 가능합니다. [LICENSE](./LICENSE) 파일 참조.

---

## 📚 참고

- [AI Hub 공식 사이트](https://aihub.or.kr/)
- [aihubshell 가이드](https://aihub.or.kr/devsport/apishell/list.do)
- [상세 사용 가이드 (USAGE.md)](./USAGE.md)
