# 📖 USAGE 가이드

이 문서는 **처음 사용하는 사람이 단계별로 따라 할 수 있도록** 작성되었습니다.
각 단계마다 **실행할 명령**, **기대 출력**, **트러블슈팅**을 포함합니다.

> 📥 **다운로드(1~2장)는 별도 문서에 더 자세히 정리돼 있습니다 → [download_guide.md](download_guide.md)**
> aihubshell 설치, API Key, 로케일 문제, 부분 다운로드, 중단·재개, 검증→복구 루프를 다룹니다.
> 이 문서의 1~2장은 요약이며, 막히면 `download_guide.md`를 보세요.

---

## 📑 목차

- [0. 사전 준비](#0-사전-준비)
- [1. AI Hub 다운로드](#1-ai-hub-다운로드) — 상세: [download_guide.md](download_guide.md)
- [2. 다운로드 검증 (`verify/`)](#2-다운로드-검증)
  - [2-1. 빠른 진단 — `check_aihub.sh`](#2-1-빠른-진단--check_aihubsh)
  - [2-2. zip 무결성 검증 — `verify_zips.sh`](#2-2-zip-무결성-검증--verify_zipssh)
  - [2-3. 자동 복구 — `repair_aihub.sh`](#2-3-자동-복구--repair_aihubsh)
- [3. 압축 해제 (`preprocess/`)](#3-압축-해제)
  - [3-1. zip 정리 — `move_zips_to_zips_dir.sh`](#3-1-zip-정리--move_zips_to_zips_dirsh)
  - [3-2. 압축 해제 — `extract_zips.sh`](#3-2-압축-해제--extract_zipssh)
  - [3-3. zip 삭제로 용량 회수하기 ⚠️](#3-3-zip-삭제로-용량-회수하기)
- [4. 메타데이터 생성 (`build_metadata.py`)](#4-메타데이터-생성)
- [5. 데이터 탐색 (`explore_dataset.ipynb`)](#5-데이터-탐색)
- [6. CSV 컬럼 레퍼런스](#6-csv-컬럼-레퍼런스)
- [7. 트러블슈팅 FAQ](#7-트러블슈팅-faq)

---

## 0. 사전 준비

### 0-1. 필수 환경

| 항목 | 요구사항 |
|---|---|
| **OS** | Linux (Ubuntu 20.04+), macOS, 또는 WSL2 |
| **bash** | 4.0 이상 |
| **Python** | 3.8 이상 |
| **필수 명령어** | `unzip`, `find`, `xargs`, `awk`, `sed` |
| **Python 패키지** | `pandas`, `jupyter`, `ipywidgets` |
| **디스크** | 최소 600GB 여유 (zip 220GB + 해제 293GB + 작업 여유) |
| **메모리** | 8GB 이상 (메타데이터 생성 시 4GB 정도 사용) |

### 0-2. 디스크 공간 미리 확인

```bash
# 사용 가능 공간 (GB)
df -BG /path/to/storage

# inode 여유 (작은 파일 63만 개 생성 예정)
df -i /path/to/storage
```

**실측 기준 용량 곡선** (2026-08 전량 처리 완료 기준):

| 시점 | zip | 해제본 | 합계 |
|---|---:|---:|---:|
| 다운로드 완료 | 220 GB | — | **220 GB** |
| 압축 해제 완료 | 220 GB | 293 GB | **513 GB** ← 최대 |
| zip 삭제 후 | — | 293 GB | **293 GB** |
| + 메타데이터 (`meta/` 1.3GB) | — | 293 GB + 1.3 GB | **294 GB** |

→ **순간 최대 513GB**가 필요합니다. 압축 해제가 끝나면 [3-3](#3-3-zip-삭제로-용량-회수하기)에서 220GB를 회수하세요.

inode 사용률이 90%를 넘으면 압축 해제 중 `No space left on device` 에러가 날 수 있어요. 자세한 설명은 [FAQ #1](#faq-1-inode란-무엇인가요)을 참고하세요.

### 0-3. AI Hub 가입 및 권한

1. [AI Hub](https://www.aihub.or.kr) 회원가입
2. "감성 및 발화스타일 동시 고려 음성합성 데이터" 검색 (또는 datasetkey=71349)
3. 다운로드 신청 → 승인 대기 (보통 1~3일)
4. 승인 완료 후 **마이페이지 → API Key 발급**
   `aihubshell`과 이 레포의 복구 스크립트는 ID/PW가 아니라 **API Key**로 인증합니다.

### 0-4. 레포 클론 및 권한 설정

```bash
git clone https://github.com/renslightsaber/aihub-no-pain-71349.git ~/aihub-no-pain-71349
export REPO=~/aihub-no-pain-71349

# 셸 스크립트 실행 권한
chmod +x "$REPO"/verify/*.sh "$REPO"/preprocess/*.sh
```

### 0-5. 공통 환경변수

이 문서의 모든 명령은 아래 변수를 기준으로 합니다. 셸을 새로 열 때마다 다시 설정하세요.

| 변수 | 의미 | 예시 |
|---|---|---|
| `REPO` | 이 레포를 클론한 경로 | `~/aihub-no-pain-71349` |
| `AIHUB_APIKEY` | AI Hub API Key | `export AIHUB_APIKEY='xxxx'` |
| `ROOT` | 다운로드된 데이터셋 최상위 폴더 | `./133.감성 및 발화 스타일 동시 고려 음성합성 데이터` |
| `FILELIST` | filelist 경로 (기본값 `./filelist_71349.txt`) | `$REPO/verify/filelist_71349.txt` |

> ⚠️ **`BASE_DIR`이 아니라 `ROOT`입니다.** `verify/`·`move_zips_to_zips_dir.sh`의 셸 스크립트는
> 다운로드 루트를 `ROOT`로 읽습니다. (`--base-dir`은 4단계 `build_metadata.py` 전용 옵션으로, 별개입니다.)

---

## 1. AI Hub 다운로드

### 1-1. aihubshell 설치

AI Hub 공식 안내에 따라 `aihubshell`을 설치합니다. 이 레포는 `aihubshell version 25.09.19 v0.6` 이상에서 검증되었어요.

### 1-2. 다운로드 실행

데이터셋을 받을 작업 디렉토리를 정해 그곳에서 실행합니다:

```bash
# 예: /data/aihub_71349 디렉토리에 다운로드
mkdir -p /data/aihub_71349
cd /data/aihub_71349

# 검증 스크립트가 기본으로 찾는 위치에 filelist 복사
cp "$REPO/verify/filelist_71349.txt" .

aihubshell -mode d \
  -datasetkey 71349 \
  -aihubapikey "$AIHUB_APIKEY"
```

### 1-3. 다운로드 완료 시 디렉토리 구조

다운로드가 끝나면 다음과 같은 폴더가 생깁니다:

```
/data/aihub_71349/
└── 133.감성 및 발화 스타일 동시 고려 음성합성 데이터/
    └── 01-1.정식개방데이터/
        ├── Training/
        │   ├── 01.원천데이터/        ← TS_xxx.zip (wav 들어있음)
        │   └── 02.라벨링데이터/      ← TL_xxx.zip (JSON 들어있음)
        └── Validation/
            ├── 01.원천데이터/        ← VS_xxx.zip
            └── 02.라벨링데이터/      ← VL_xxx.zip
```

### ⚠️ 다운로드 중단 시

`Ctrl+C`로 끊었거나 네트워크 오류로 중단되면:
- `download.tar` 잔여물이 남음
- 일부 zip 파일이 `.part` 형태로 남음
- 또는 zip 일부만 받힘 (깨진 상태)

당황하지 말고 **다음 단계 (`verify/`)** 로 넘어가세요. 자동으로 진단·복구됩니다.

### 1-4. `ROOT` 잡기 (이후 모든 단계에서 사용)

스크립트의 `ROOT` 기본값은 밑줄이 들어간 `./133.감성_및_발화_스타일_동시_고려_음성합성_데이터`인데,
aihubshell이 실제로 만드는 폴더명은 **공백**이 들어간 이름일 수 있습니다. 실제 폴더명으로 잡아 두세요:

```bash
cd /data/aihub_71349
export ROOT="$(find . -maxdepth 1 -type d -name '133.*' | head -1)"
echo "$ROOT"     # 비어 있으면 다운로드 위치부터 다시 확인
```

---

## 2. 다운로드 검증

다운로드가 1,412개 zip을 모두 받았는지, 깨진 파일은 없는지 검증하는 단계입니다.

> 💡 **세 스크립트는 항상 같은 순서로 실행하세요**:
> `check_aihub.sh` → `verify_zips.sh` (선택) → `repair_aihub.sh`

### 2-1. 빠른 진단 — `check_aihub.sh`

filelist와 실제 다운로드를 비교해 **누락 파일·잔여물**을 식별합니다. 수 분 내 완료.

```bash
# 다운로드한 디렉토리에서 실행
cd /data/aihub_71349/

# filelist를 복사해 두지 않았다면 위치를 명시
FILELIST="$REPO/verify/filelist_71349.txt" \
  bash "$REPO/verify/check_aihub.sh"
```

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DATASET_KEY` | `71349` | 데이터셋 키 |
| `FILELIST` | `filelist_${DATASET_KEY}.txt` | AI Hub filelist 파일 경로 |
| `ROOT` | `./133.감성_및_발화_스타일_동시_고려_음성합성_데이터` | 검사할 다운로드 루트 |
| `SHOW_DETAILS` | `1` | 0이면 개수만 출력 |
| `USE_COLOR` | `auto` | 색상 출력 |
| `DEBUG` | `0` | 1이면 filelist 파싱·매칭 진단 로그 출력 |

### 기대 출력

```
============================================
  AI Hub 다운로드 빠른 진단 (v2)
============================================
  DATASET_KEY : 71349
  ROOT        : ./133.감성 및 발화 스타일 동시 고려 음성합성 데이터
  FILELIST    : ./filelist_71349.txt

📊 개수 비교
  filelist 등록 zip : 1412
  디스크 zip        : 1410
  part 잔재         : 0
  download.tar 잔재 : 1   (0이어야 정상)

✗ 이상 발견:
  - 누락 파일: 2건
  - tar 잔재 : 1건

📋 누락된 파일 상세
─────────────────────────────────────────────────────────────────────
파일명(정규화)                                     용량         filekey
─────────────────────────────────────────────────────────────────────
TS_애니체_098.zip                                  612 MB       560421
VL_친절체_021.zip                                  31 KB        561102
─────────────────────────────────────────────────────────────────────

💡 복구 방법
  (A) 자동 복구:    ./repair_aihub.sh
  (B) 수동 명령:    aihubshell -mode d -datasetkey 71349 \
                                -filekey '560421,561102' \
                                -aihubapikey "$AIHUB_APIKEY"
```

정상이면 exit 0, 이상이 있으면 exit 1을 반환합니다.
`filelist 파싱 0건` 에러가 나면 `DEBUG=1`을 붙여 파싱 결과를 확인하세요.

### 2-2. zip 무결성 검증 — `verify_zips.sh`

모든 zip의 CRC 체크섬을 병렬로 검증합니다. 시간이 걸리지만 학습 전에 한 번은 돌리는 게 안전해요.

```bash
PARALLEL=8 bash "$REPO/verify/verify_zips.sh"
```

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DATASET_KEY` | `71349` | 데이터셋 키 |
| `FILELIST` | `filelist_${DATASET_KEY}.txt` | filekey 조회용 filelist |
| `ROOT` | `./133.감성_및_발화_스타일_동시_고려_음성합성_데이터` | 검사 대상 디렉토리 |
| `PARALLEL` | `8` | 병렬 작업 수. NFS는 8, 로컬 NVMe는 16+ 권장 |
| `SHOW_DETAILS` | `1` | 0이면 깨진 파일 상세 생략 |
| `DEBUG` | `0` | 1이면 파싱 진단 로그 |

### 기대 출력

```
🔍 검증 시작 (1412개, 병렬 8)

📊 검증 결과 (1733초)
  정상 : 1412건
  깨짐 : 0건

✓ 모든 zip 무결성 통과
```

깨진 zip이 있으면 **파일명·용량·filekey 표와 복구 명령을 화면에 출력**하고 exit 1을 반환합니다
(별도 파일로 기록하지는 않습니다). 그대로 `repair_aihub.sh`로 넘어가면 됩니다.

### 2-3. 자동 복구 — `repair_aihub.sh`

모든 zip을 직접 재검사해 누락·손상 파일을 **자동 재다운로드**합니다.
(`check_aihub.sh`/`verify_zips.sh`의 결과 파일을 읽는 게 아니라 스스로 다시 검사합니다.)

```bash
export AIHUB_APIKEY='<your_api_key>'     # 없으면 즉시 종료됩니다

# 무엇을 지우고 무엇을 받을지 먼저 확인
DRY_RUN=1 bash "$REPO/verify/repair_aihub.sh"

# 실제 복구
bash "$REPO/verify/repair_aihub.sh"
```

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AIHUB_APIKEY` | **(필수)** | 미설정 시 즉시 종료 |
| `DATASET_KEY` | `71349` | 데이터셋 키 |
| `ROOT` | `./133.감성_및_발화_스타일_동시_고려_음성합성_데이터` | 복구 대상 루트 |
| `FILELIST` | `filelist_${DATASET_KEY}.txt` | filekey 조회용 |
| `BATCH` | `50` | 한 번의 `aihubshell` 호출에 넣을 filekey 개수 |
| `DRY_RUN` | `0` | 1이면 잔재 정리·다운로드 없이 계획만 출력 |
| `INCLUDE_NEVER_DOWNLOADED` | `1` | 0이면 "한 번도 받지 않은 파일"은 건드리지 않음 (의도적 부분 다운로드용) |
| `DEBUG` | `0` | 1이면 파싱 진단 로그 |

> ⚠️ `DRY_RUN=0`일 때 이 스크립트는 **깨진 zip과 `.part` 잔재를 먼저 삭제**한 뒤 다시 받습니다.
> 부분 다운로드가 의도된 상황이라면 반드시 `INCLUDE_NEVER_DOWNLOADED=0`을 함께 주세요.
> (미다운로드 비율이 50%를 넘으면 스크립트가 경고를 출력합니다.)

### 처리되는 5가지 케이스

| 케이스 | 의미 | 조치 |
|---|---|---|
| `ok` | 정상 zip | 건너뜀 |
| `broken` | 깨진 zip | 삭제 후 재다운로드 |
| `missing` | filelist에는 있는데 파일 없음 | 다운로드 |
| `residue_only` | `.part`만 있음 | 잔여물 정리 후 다운로드 |
| `never_downloaded` | 한 번도 받지 않음 | 다운로드 |

추가로 `download.tar` 잔여물도 자동 정리합니다.

### 기대 출력

```
[1/3] 데이터셋 상태 점검 중...
    (1-A) zip 무결성 검증 (1410개)...
          진행: 1410/1410
    (1-B) part 잔재 식별...
    (1-C) download.tar 잔재 1개
    (1-D) filelist 파싱... filelist 등록: 1412개
    (1-E) 다운로드 시도 안 됨: 2개

    === 점검 결과 ===
    정상 zip              : 1410건
    깨진 zip              : 0건
    → 재다운로드 대상     : 2건
    → 잔재 정리 완료

[2/3] filekey 매핑...  매칭: 2건 / 실패: 0건

[3/3] 재다운로드 batch (총 2개, batch=50)
  >> batch 1 (2개): 560421,561102

Done.
복구 완료. 다시 ./repair_aihub.sh 로 수렴 확인.
```

복구 후에는 `repair_aihub.sh`(또는 `check_aihub.sh`)를 한 번 더 돌려
"재다운로드 필요 없음"이 나오는지 확인하세요.

---

## 3. 압축 해제

### 3-1. zip 정리 — `move_zips_to_zips_dir.sh`

AI Hub 다운로드 폴더 구조는 깊고 복잡합니다. 이 스크립트는 **모든 zip을 `zips/`라는 한 폴더로 모으되, 원래 경로 구조는 보존**합니다.

```bash
cd /data/aihub_71349/

DRY_RUN=1 bash "$REPO/preprocess/move_zips_to_zips_dir.sh"   # 미리보기
bash "$REPO/preprocess/move_zips_to_zips_dir.sh"
```

### 변환 예시

```
변환 전:
  ./133.감성.../01-1.정식개방데이터/Training/01.원천데이터/TS_구연체_001.zip

변환 후:
  ./zips/133.감성.../01-1.정식개방데이터/Training/01.원천데이터/TS_구연체_001.zip
```

원래 깊은 구조를 유지하기 때문에, 압축 해제 시에도 라벨↔원천 매핑이 자동으로 보존됩니다.

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `ROOT` | `./133.감성_및_발화_스타일_동시_고려_음성합성_데이터` | 검색 시작 디렉토리 |
| `ZIPS_DIR` | `./zips` | zip을 모을 대상 디렉토리 |
| `DRY_RUN` | `0` | 1이면 실제 이동 없이 시뮬레이션만 |

> 이동이 끝나면 `ROOT` 아래 빈 디렉토리는 자동 삭제되고, `ROOT` 자체도 비면 제거됩니다.
> 즉 이 단계 이후에는 zip이 `./zips/` 아래에만 존재합니다.

### 3-2. 압축 해제 — `extract_zips.sh`

`zips/`의 모든 zip을 `data/`로 병렬 압축 해제합니다.

```bash
DRY_RUN=1 bash "$REPO/preprocess/extract_zips.sh"      # 계획만 확인
PARALLEL=8 bash "$REPO/preprocess/extract_zips.sh"
```

### ⚠️ 알아두면 좋은 점 — 절대경로 Warning

이 데이터셋의 zip은 내부 파일이 **절대경로(`/`)** 로 저장되어 있습니다:

```
zip 내부: /K-S1-C-034-0075.wav   (← 슬래시로 시작)
```

`unzip`은 보안상 `/`를 자동 제거하면서 다음과 같이 출력합니다:

```
warning: stripped absolute path spec from /K-S1-C-034-0075.wav
  inflating: ./data/.../K-S1-C-034-0075.wav    ← 실제로는 정상 압축 해제됨
```

그리고 **exit code 1**을 반환해요. 압축은 완벽히 정상이지만, 이걸 모르면 모든 zip이 실패한 것처럼 보입니다.

**이 스크립트는 exit code 0과 1을 모두 성공으로 처리**합니다. 별도 조치 불필요.

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `ZIPS_DIR` | `./zips` | 입력 zip 폴더 |
| `DATA_DIR` | `./data` | 출력 폴더 |
| `PARALLEL` | `4` | 병렬 작업 수 |
| `SKIP_EXISTING` | `1` | 이미 풀린 폴더는 건너뜀 |
| `DRY_RUN` | `0` | 1이면 실제 실행 없이 계획만 표시 |
| `VERBOSE` | `0` | 1이면 unzip 출력 그대로 표시 |
| `MAX_FAIL_SHOW` | `3` | 실패 로그를 화면에 보여줄 최대 개수 |

### 기대 소요 시간

| 환경 | PARALLEL | 예상 시간 |
|---|---|---|
| NFS | 4 | 2~3시간 |
| NFS | 8 | 1.5~2시간 |
| 로컬 NVMe | 8 | 30~60분 |
| 로컬 NVMe | 16 | 20~40분 |

### 진행 상황 모니터링 (다른 터미널에서)

```bash
# 풀린 zip 폴더 개수
watch -n 60 'find ./data -mindepth 4 -type d -not -empty | wc -l'

# 또는 풀린 파일 총 개수
watch -n 60 'find ./data -name "*.wav" | wc -l; df -i ./data | tail -1'
```

### 압축 해제 후 디렉토리

```
data/
├── 133.../Training/
│   ├── 01.원천데이터/
│   │   ├── TS_구연체_001/
│   │   │   ├── K-A1-C-034-0001.wav
│   │   │   └── ...
│   │   └── ...
│   └── 02.라벨링데이터/
│       ├── TL_구연체_001/
│       │   ├── ...P03-A-009.json
│       │   └── ...
│       └── ...
└── 133.../Validation/
    ├── 01.원천데이터/  (VS_xxx/)
    └── 02.라벨링데이터/  (VL_xxx/)
```

### 압축 해제 완료 시 기대값 (실측)

```bash
find ./data -name "*.wav"  | wc -l     # → 622,905
find ./data -name "*.json" | wc -l     # →  13,140
du -sh ./data                          # → 293G
```

| 구분 | wav | JSON |
|---|---:|---:|
| Training | 559,887 | 11,875 |
| Validation | 63,018 | 1,265 |
| **합계** | **622,905** | **13,140** |

숫자가 크게 모자라면 압축 해제가 덜 끝난 것입니다. `extract_zips.sh`는 `SKIP_EXISTING=1`이라
**그냥 다시 돌리면 이어서 진행**됩니다.

---

### 3-3. zip 삭제로 용량 회수하기

압축 해제가 끝나면 `zips/`의 **220GB는 더 이상 필요 없습니다.** 지우면 점유가 513GB → 293GB로 떨어집니다.

> 🚨 **되돌릴 수 없는 작업입니다.** 다시 받으려면 AI Hub에서 220GB를 처음부터 내려받아야 하고,
> 회선에 따라 수 시간~하루가 걸립니다. **반드시 아래 검증을 먼저 통과시키세요.**

#### ① 전수 검증 (필수)

`verify_extraction.py`는 zip 1,412개의 내부 목록을 하나씩 읽어, 그 파일들이 `data/`에
**실제로 존재하는지 전부 대조**합니다. 압축을 다시 풀지 않으므로 빠릅니다.

```bash
cd /data/aihub_71349

python3 "$REPO/preprocess/verify_extraction.py" \
  --zips-dir ./zips \
  --data-dir ./data
```

**통과 출력:**

```
  검사한 zip       : 1,412
  zip 내부 총 파일 : 636,045
  문제 있는 zip    : 0
------------------------------------------------------------

✅ 모든 zip이 빠짐없이 압축 해제되었습니다.
   zip을 삭제해 용량을 회수해도 안전합니다.
```

**실패 출력이면 절대 지우지 마세요.** 스크립트가 조치 방법을 함께 알려 줍니다.

| 상태 | 의미 | 조치 |
|---|---|---|
| `INCOMPLETE` | 폴더는 있는데 파일이 덜 풀림 | `extract_zips.sh` 재실행 (이어서 진행) |
| `DEST_MISSING` | 대상 폴더 자체가 없음 | `extract_zips.sh` 재실행 |
| `ZIP_UNREADABLE` | zip이 깨짐 | `verify_zips.sh` → `repair_aihub.sh` |

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--zips-dir` | `./zips` | zip 보관 폴더 |
| `--data-dir` | `./data` | 압축 해제된 폴더 |
| `--parallel` | `16` | 동시 검사 수 |
| `--sample N` | `0`(전수) | 접두어(TS/VS/TL/VL)별 N개만 빠르게 확인 |

> 💡 압축 해제 **도중** 중간 점검만 하고 싶다면 `--sample 5`가 편합니다.
> 다만 **삭제 직전에는 반드시 `--sample` 없이 전수 검증**하세요.

#### ② 삭제 전 최종 확인

지우기 전에 한 번 더 눈으로 확인하는 걸 권합니다:

```bash
# 지울 대상과 확보될 용량
du -sh ./zips                                  # → 220G
find ./zips -name "*.zip" | wc -l              # → 1412

# 남을 데이터
du -sh ./data                                  # → 293G
find ./data -name "*.wav" | wc -l              # → 622905
```

#### ③ 삭제

```bash
rm -rf ./zips
df -h .          # 220GB 확보 확인
```

> 📌 **메타데이터는 zip 없이도 언제든 다시 만들 수 있습니다.** `build_metadata.py`는 `data/`만
> 읽으므로, zip을 지운 뒤에도 [4장](#4-메타데이터-생성)을 몇 번이든 재실행할 수 있습니다.

> 📌 **`filelist_71349.txt`는 지우지 마세요.** 나중에 검증·부분 재다운로드를 할 때 기준값으로 필요합니다.
> 용량은 93KB에 불과합니다.

---

## 4. 메타데이터 생성

`build_metadata.py`는 모든 JSON 라벨을 파싱해 **학습 가능한 메타데이터 CSV**를 만들고, 통계 txt와 화자별 CSV까지 자동 생성합니다.

### 4-1. 기본 실행

```bash
cd /data/aihub_71349/

python3 "$REPO/preprocess/build_metadata.py" \
  --data-dir ./data \
  --base-dir "$PWD" \
  --output-dir ./meta
```

### 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--data-dir` | `./data` | 압축 해제된 데이터 폴더 |
| `--base-dir` | `data-dir.parent.parent` | `audio_path`의 기준 절대 경로 |
| `--output-dir` | `./meta` | 출력 폴더 |
| `--label-pattern` | `**/[TV]L_*/*.json` | JSON 검색 패턴 (`TL_`+`VL_` 모두 매칭) |
| `--use-index` | `False` | wav 인덱스 미리 생성 (NFS stat 비용 절약) |

> 💾 **NFS/네트워크 스토리지라면 `--use-index`를 켜세요.** wav 하나하나 `stat`을 날리는 대신
> 인덱스를 한 번에 만들어 쓰기 때문에 체감 속도 차이가 큽니다.

> ⚠️ **v3 이하로 만든 `metadata.csv`가 있다면 다시 만드세요.**
> v3의 기본 패턴 `**/T[LV]_*/*.json`은 `TL_`(Training)만 매칭하고 **`VL_`(Validation)을 통째로
> 놓쳤습니다.** 그 결과 CSV에 Validation 63,018개 wav가 들어가지 않았습니다.
> 자가 진단은 간단합니다 — `stats_overall.txt`의 `split 분포`에 **`valid`가 없으면 구버전 산출물**입니다.
>
> ```bash
> grep -A3 "split 분포" ./meta/stats_overall.txt
> # train 만 있으면 → 재생성 필요
> ```

### `base_dir`이 중요한 이유

CSV의 audio 경로는 두 컬럼으로 분리됩니다:

```
base_dir   : /data/aihub_71349
audio_path : 133.../Training/01.원천데이터/TS_구연체_001/K-A1-C-034-0001.wav
```

이렇게 분리하면 데이터셋을 다른 서버로 옮길 때 `base_dir`만 갈아끼우면 끝납니다:

```python
df['base_dir'] = '/new/path/aihub_71349'
df.to_csv('metadata.csv', index=False)
```

### 4-2. 생성되는 출력물

```
meta/
├── metadata.csv                       # 전체 메타데이터 (모든 컬럼)
├── stats_overall.txt                  # 전체 통계 (split·성별·스타일·감정·duration)
├── stats_per_speaker.txt              # 화자별 통계 (요약표 + 화자별 상세)
├── stats_per_gender.txt               # 성별별 통계 (FEMALE/MALE 각각)
└── metadatas_per_speaker/             # 화자별 CSV 분리
    ├── speaker_001.csv
    ├── speaker_002.csv
    ├── ...
    └── speaker_159.csv
```

### 4-3. 콘솔 출력 예시

전량 처리 시의 **실제 출력**입니다. 이 숫자와 맞으면 정상입니다.

```
data_dir   : /data/aihub_71349/data
base_dir   : /data/aihub_71349
output_dir : /data/aihub_71349/meta

wav 파일 인덱스 생성 중...
  → 622,905개 wav 인덱싱 완료
JSON 라벨 파일 검색 중...
  → 13,140개 JSON 발견
  진행: 13140/13140
  파싱 완료: 623,642개 row

[1/4] metadata.csv      : ./meta/metadata.csv
[2/4] stats_overall     : ./meta/stats_overall.txt
[3/4] stats_per_speaker : ./meta/stats_per_speaker.txt
      stats_per_gender  : ./meta/stats_per_gender.txt
[4/4] 화자별 CSV        : ./meta/metadatas_per_speaker/ (89개)

==================================================
총 row 수    : 623,642
고유 화자    : 89명
split 분포   : {'train': 560624, 'valid': 63018}
성별 분포    : {'MALE': 314751, 'FEMALE': 308891}
audio 누락   : 0건 (0.00%)
```

**핵심 체크포인트 3가지:**

| 확인 항목 | 정상값 | 어긋나면 |
|---|---|---|
| JSON 발견 개수 | **13,140개** | 11,875개면 `VL_`을 못 찾은 것 → [FAQ 3-1](#faq-3-1-csv에-valid-split이-아예-없어요-validation-누락) |
| `split` 분포 | `train` **+** `valid` 둘 다 | `valid`가 없으면 위와 동일 |
| `audio 누락` | **0건** | 압축 해제 미완료 → [FAQ 3](#faq-3-audio-파일-누락-nnnnnn건-이라고-나와요) |

> ⚠️ `audio 누락`이 많이 나오면 압축 해제가 미완료된 경우가 대부분입니다. `extract_zips.sh`를 다시 돌려서 완료 후 재실행하세요.

> ⏱️ **소요 시간**: NFS + `--use-index` 기준 약 25분 (wav 62만 개 인덱싱 10분 + JSON 13,140개 파싱 15분).
>
> 💾 **산출물 용량**: `meta/` 전체 **1.3GB** — `metadata.csv` 623MB + 화자별 CSV 89개 623MB + 통계 txt.
> 화자별 CSV는 `metadata.csv`를 화자 단위로 나눈 것이라 사실상 같은 데이터를 두 벌 갖게 됩니다.
> 용량이 아깝다면 `metadatas_per_speaker/`는 지워도 되고, 필요할 때 다시 만들면 됩니다.

---

## 5. 데이터 탐색

`explore_dataset.ipynb`는 **화자 ID를 선택하면 그 화자의 발화 샘플과 메타데이터를 함께 보여주는** 인터랙티브 노트북입니다.

### 5-1. 노트북 실행

```bash
# 필수 패키지
pip install pandas jupyter ipywidgets

# 노트북 실행
jupyter notebook "$REPO/notebooks/explore_dataset.ipynb"
```

또는 VSCode에서 `.ipynb` 파일을 직접 열어도 됩니다.

### 5-2. 노트북 셀 구성

| 셀 | 내용 |
|---|---|
| 1 | 환경 설정, metadata.csv 로드 |
| 2 | 절대 경로 헬퍼 (`base_dir + audio_path`) |
| 3 | 화자 정보 카드 출력 함수 |
| 4 | 샘플 청취 함수 (필터·재생) |
| 5 | 다양한 필터 조합 예시 (감정·스타일·강도·텍스트 검색) |
| **6** | **인터랙티브 위젯** (드롭다운으로 화자 선택) |
| 7 | 화자별 CSV 직접 로드 |
| 8 | 학습용 데이터 필터링 체크리스트 |

### 5-3. 인터랙티브 위젯 UI

```
┌────────────────────────────────────────────────────────────────┐
│ 화자 ID: [9 ▼]  발화체: [(전체) ▼]  감정: [분노 ▼]  강도: [3 ▼] │
│ 샘플 수: ━●━━━━━━━━━ 5    seed: [42]   텍스트: [엄마      ] │
│ [ℹ️ 화자 정보만]  [🔍 검색 + 재생]                              │
├────────────────────────────────────────────────────────────────┤
│ 🎤 화자 9                                                      │
│ 성별: FEMALE  나이: 20세  총 발화: 1,234건  총 30.5분          │
│                                                                │
│ #1  A-A2-A-009-0101  |  애니체/남아  |  분노(강도 3)  |  3.4초 │
│ tr:  지금 싸움을 외면하라는 겁니까, 동료들의 죽음에서 ...      │
│ ptr: 지금 싸움을 외면하라는 겁니까 / 동료들의 죽음에서 / ...   │
│ 📁 133.../TS_애니체_001/A-A2-A-009-0101.wav                    │
│ [▶ ━━━━●━━━━ 0:02 / 0:03]                                    │
│                                                                │
│ #2 ... (다음 샘플 계속)                                        │
└────────────────────────────────────────────────────────────────┘
```

### 5-4. 프로그래밍 인터페이스로 사용하기

위젯 외에도 직접 함수를 호출할 수 있어요:

```python
# 화자 9번의 분노 감정 발화 3개
play_samples_for_speaker(df, speaker_id=9, emotion="분노", n=3)

# 남성 화자 중 친절체 발화
samples = df[(df['reciter_gender']=='MALE') & (df['style']=='친절체')]

# 특정 검수 점수 이상만
clean = df[df['votes_avg'] >= 4.0]
```

---

## 6. CSV 컬럼 레퍼런스

`metadata.csv`의 모든 컬럼:

| 컬럼 | 타입 | 의미 | 예시 |
|---|---|---|---|
| `file_id` | str | 발화 고유 ID | `A-A2-A-009-0101` |
| `script_id` | str | 대본 ID | `A-A201` |
| `part_no` | int | 대본 파트 번호 | 3 |
| `reciter_id` | int | 화자 번호 | 9 |
| `reciter_age` | int | 화자 나이 | 20 |
| `reciter_gender` | str | 화자 성별 | `FEMALE` / `MALE` |
| `style` | str | 발화 스타일 | `애니체` |
| `sub_style` | str | 서브 스타일 | `남아` |
| `emotion` | str | 감정 | `분노` |
| `intensity` | int | 감정 강도 | 1~3 |
| `duration` | float | 실제 발화 길이 (초) | 3.42 |
| `file_duration` | float | wav 전체 길이 (앞뒤 0.25s 묵음 포함) | 3.92 |
| `duration_valid` | bool | `duration <= file_duration` 인지 | True |
| `duration_effective` | float | `max(duration, file_duration)` | 3.92 |
| `text_origin` | str | 원문 텍스트 | "..." |
| `text_tr` | str | **철자 전사** (TTS 입력용) | "지금 싸움을..." |
| `text_ptr` | str | **발음 전사** (끊어 읽기 `/` 표시, 프로소디용) | "지금 싸움을 외면하라는 겁니까 /..." |
| `wav_filename` | str | wav 파일명 | `A-A2-A-009-0101.wav` |
| `base_dir` | str | 공통 base 절대 경로 | `/data/aihub_71349` |
| `audio_path` | str | **base_dir 기준 상대 경로** ⭐ | `133.../TS_애니체_001/A-A2-A-009-0101.wav` |
| `audio_relpath` | str | `data_dir` 기준 상대 경로 (호환성) | `133.../TS_애니체_001/A-A2-A-009-0101.wav` |
| `audio_exists` | bool | wav 파일 실제 존재 여부 | True |
| `label_relpath` | str | JSON 라벨 상대 경로 | `133.../TL_애니체_001/A-A201-P03-A-009.json` |
| `votes_avg` | float | 검수자 평가 평균 (1~5 Likert) | 4.67 |
| `votes_count` | int | 검수자 수 | 3 |
| `src_type` | str | 출처 유형 | `작품` |
| `studio_id` | str | 녹음실 ID | `A` |
| `studio_name` | str | 녹음실 이름 | `스튜디오1` |
| `sample_rate` | int | 샘플 레이트 | 44100 |
| `recorded_at` | str | 녹음 일시 | `2022-10-18 04:44:21` |
| `split` | str | 학습/검증 분할 | `train` / `valid` |
| `zip_basename` | str | 원본 zip 폴더명 | `TL_애니체_001` |

### 학습용 절대 경로 만들기

```python
from pathlib import Path
import pandas as pd

df = pd.read_csv('./meta/metadata.csv')

# 한 행의 wav 절대 경로
row = df.iloc[0]
audio_abspath = Path(row['base_dir']) / row['audio_path']
print(audio_abspath)
# /data/aihub_71349/133.../TS_애니체_001/A-A2-A-009-0101.wav
```

---

## 7. 트러블슈팅 FAQ

### FAQ 1. inode란 무엇인가요?

inode는 파일시스템에서 **파일 1개의 메타데이터를 담는 자료구조**입니다. 파일시스템 생성 시 inode 개수가 고정되어 있어요. AI Hub 데이터셋은 작은 파일을 56만 개 생성하므로 inode가 부족하면 압축 해제가 실패할 수 있습니다.

```bash
# inode 사용 현황 확인
df -i /your/path

# IUse%가 80% 미만이면 안전, 95% 이상이면 위험
```

대처법:
- 불필요한 작은 파일(캐시, `__pycache__`, `.git`) 삭제
- 다른 파일시스템(inode 여유 있는)으로 이동
- 미사용 파일은 zip으로 보관

### FAQ 2. 압축 해제 중 멈춘 것처럼 보여요

NFS 환경에서 1~3시간 걸리는 게 정상입니다. 다음 명령으로 진행 여부 확인:

```bash
# 다른 터미널에서
find ./data -name "*.wav" | wc -l
# 숫자가 증가 중이면 정상 진행 중
```

5분 안에 새 파일이 0개라면 stuck일 수 있어요. 이때는 Ctrl+C로 중단 후 재시작 (SKIP_EXISTING=1 기본이라 이어서 진행됨).

### FAQ 3. `audio 파일 누락: NNNNNN건` 이라고 나와요

대부분 압축 해제가 완료되지 않은 경우입니다. 다음 순서로 확인:

```bash
# 1) 전체 wav 개수 (622,905개여야 정상)
find ./data -name "*.wav" | wc -l

# 2) Validation 폴더도 풀렸는지 (63,018개여야 정상)
find ./data -path "*/Validation/*" -name "*.wav" | wc -l

# 3) 풀리지 않은 zip이 있다면 재실행 (이어서)
bash "$REPO/preprocess/extract_zips.sh"
```

**가장 확실한 진단은 전수 검증입니다.** 어떤 zip이 덜 풀렸는지 이름까지 찍어 줍니다:

```bash
python3 "$REPO/preprocess/verify_extraction.py"
```

압축 해제가 완료됐는데도 누락이 나오면 `--use-index` 옵션을 추가해보세요:

```bash
python3 build_metadata.py --data-dir ./data --output-dir ./meta --use-index
```

---

### FAQ 3-1. CSV에 `valid` split이 아예 없어요 (Validation 누락)

`stats_overall.txt`의 `split 분포`에 `train`만 있고 `valid`가 없다면,
**`build_metadata.py` v3 이하로 만든 산출물**입니다.

원인은 `--label-pattern` 기본값의 오타 한 글자였습니다:

```
v3 (버그): **/T[LV]_*/*.json   →  TL_ , TV_ 매칭  →  VL_ 을 못 찾음 ❌
v4 (수정): **/[TV]L_*/*.json   →  TL_ , VL_ 매칭  →  정상 ✅
```

`VL_`(Validation Label) 폴더가 전혀 매칭되지 않아 **Validation 63,018개 wav가 통째로
CSV에서 빠졌습니다.** 에러 없이 조용히 누락되기 때문에 눈치채기 어렵습니다.

**해결:** 최신 `build_metadata.py`로 그대로 재실행하면 됩니다. 원본 데이터는 멀쩡하므로
zip을 이미 지웠어도 문제없습니다.

```bash
python3 "$REPO/preprocess/build_metadata.py" \
  --data-dir ./data --base-dir "$PWD" --output-dir ./meta --use-index

# 확인
grep -A3 "split 분포" ./meta/stats_overall.txt   # train, valid 둘 다 나와야 정상
```

### FAQ 4. `unzip: warning: stripped absolute path spec` 가 무수히 출력돼요

이건 **정상**입니다. 데이터셋의 zip 내부 파일이 절대경로로 저장되어 있어서 unzip이 보안 메시지를 출력하는 거예요. 압축 해제는 완벽히 정상적으로 진행되고, `extract_zips.sh`가 이를 자동으로 처리합니다.

자세한 설명: [README #핵심 기능](README.md#-핵심-기능)

### FAQ 5. 한국어 폴더명 때문에 깨져요

**로케일 이름이 아니라 문자셋이 UTF-8인지**가 핵심입니다. 다음이 `UTF-8`을 출력하면 정상입니다:

```bash
locale charmap        # → UTF-8 이면 OK
```

`ANSI_X3.4-1968`(= ASCII)이 나오면 설치된 로케일 중 UTF-8 계열로 바꾸세요:

```bash
locale -a             # 설치된 로케일 목록 확인

export LANG=C.UTF-8   # 또는 en_US.UTF-8 / ko_KR.UTF-8 (설치돼 있는 것으로)
export LC_ALL=C.UTF-8
```

> ⚠️ 도커/컨테이너 환경에는 `C.utf8` 하나만 설치된 경우가 많습니다.
> 이때 `export LC_ALL=en_US.UTF-8`을 하면
> `-bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)` 경고가 뜨고
> 오히려 로케일이 ASCII로 떨어질 수 있습니다. **`locale -a`에 있는 이름만 지정하세요.**
> `C.UTF-8`이면 한글 파일명·`find`·`basename` 모두 문제없이 동작합니다.
>
> `en_US.UTF-8`이 꼭 필요하다면 root 권한으로 생성해야 합니다:
> `sudo locale-gen en_US.UTF-8 && sudo update-locale`

### FAQ 6. 학습용으로 추천하는 필터링 기준은?

데이터셋 자체에 품질 라벨(`votes_avg`)이 있어요. 권장 필터:

```python
df_clean = df[
    df['audio_exists'] &           # wav 실제 존재
    df['duration_valid'] &         # duration ≤ file_duration
    df['text_tr'].notna() &        # 전사 텍스트 존재
    df['duration'].between(0.5, 20) &  # 너무 짧거나 긴 거 제외
    df['votes_avg'] >= 3.5         # 검수자 평균 평가 보통 이상
]
```

### FAQ 7. 화자 ID 1~159 중 89명만 있어요

정상입니다. 데이터셋 가이드라인에 따르면 ID는 1~159 범위에서 부여되지만 실제 참여 화자는 89명(성우 73명 + 일반인 16명)입니다. ID에 빈 번호가 있는 게 정상이에요.

### FAQ 8. 다운로드 도중 끊었어요. 처음부터 다시 해야 하나요?

아니요. `aihubshell`이 받다 만 파일은 `verify/repair_aihub.sh`가 자동으로 식별·재다운로드합니다:

```bash
# 다운로드 재개
bash "$REPO/verify/check_aihub.sh"                      # 진단
DRY_RUN=1 bash "$REPO/verify/repair_aihub.sh"           # 복구 계획 확인
bash "$REPO/verify/repair_aihub.sh"                     # 복구 (AIHUB_APIKEY 필요)
```

의도적으로 일부만 받은 상태라면 `INCLUDE_NEVER_DOWNLOADED=0`을 함께 주세요.
그러지 않으면 아직 안 받은 파일 전체가 재다운로드 대상이 됩니다.

### FAQ 9. WSL2에서 사용 가능한가요?

네, 검증되었습니다. 다만 다음에 주의:
- WSL2의 기본 디스크는 `/mnt/c/`(Windows 드라이브)인데 매우 느립니다. WSL2 네이티브 파일시스템(`/home/user/...`) 또는 별도 Linux 디스크 사용 권장
- 한국어 폴더명을 위해 UTF-8 로케일 설정

### FAQ 10. 데이터셋 라이선스가 어떻게 되나요?

AI Hub의 이용약관을 따릅니다. 이 레포는 도구만 제공하며 데이터셋 자체를 배포하지 않습니다. 상업적 사용·재배포 관련은 AI Hub 공식 문서를 확인하세요.

---

## 🔗 관련 자료

- [데이터셋 구축 가이드라인 PDF](docs/감성및발화스타일동시고려음성합성데이터_구축활용_가이드라인.pdf) — JSON 스키마, 발화 스타일 정의, 라벨링 기준
- [데이터 설명서 PDF](docs/2-012-133%20데이터설명서_감성%20및%20발화스타일%20음성합성%20데이터.pdf) — 통계, 분포, 활용 분야
- [AI Hub 공식 페이지](https://www.aihub.or.kr)
- 📥 [download_guide.md](download_guide.md) — 다운로드 전용 상세 가이드
- 메인 [README.md](README.md)

---

문의 사항이나 버그는 GitHub Issues에 등록해주세요!
