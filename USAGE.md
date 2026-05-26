# 📖 USAGE 가이드

이 문서는 **처음 사용하는 사람이 단계별로 따라 할 수 있도록** 작성되었습니다.
각 단계마다 **실행할 명령**, **기대 출력**, **트러블슈팅**을 포함합니다.

---

## 📑 목차

- [0. 사전 준비](#0-사전-준비)
- [1. AI Hub 다운로드](#1-ai-hub-다운로드)
- [2. 다운로드 검증 (`verify/`)](#2-다운로드-검증)
  - [2-1. 빠른 진단 — `check_aihub.sh`](#2-1-빠른-진단--check_aihubsh)
  - [2-2. zip 무결성 검증 — `verify_zips.sh`](#2-2-zip-무결성-검증--verify_zipssh)
  - [2-3. 자동 복구 — `repair_aihub.sh`](#2-3-자동-복구--repair_aihubsh)
- [3. 압축 해제 (`preprocess/`)](#3-압축-해제)
  - [3-1. zip 정리 — `move_zips_to_zips_dir.sh`](#3-1-zip-정리--move_zips_to_zips_dirsh)
  - [3-2. 압축 해제 — `extract_zips.sh`](#3-2-압축-해제--extract_zipssh)
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
| **디스크** | 최소 3.5TB 여유 (zip 1.5TB + 해제 1.7TB + 작업 여유) |
| **메모리** | 8GB 이상 (메타데이터 생성 시 4GB 정도 사용) |

### 0-2. 디스크 공간 미리 확인

```bash
# 사용 가능 공간 (GB)
df -BG /path/to/storage

# inode 여유 (작은 파일 56만 개 생성 예정)
df -i /path/to/storage
```

inode 사용률이 90%를 넘으면 압축 해제 중 `No space left on device` 에러가 날 수 있어요. 자세한 설명은 [FAQ #1](#faq-1-inode란-무엇인가요)을 참고하세요.

### 0-3. AI Hub 가입 및 권한

1. [AI Hub](https://www.aihub.or.kr) 회원가입
2. "감성 및 발화스타일 동시 고려 음성합성 데이터" 검색 (또는 datasetkey=71349)
3. 다운로드 신청 → 승인 대기 (보통 1~3일)
4. 승인 완료 후 진행 가능

### 0-4. 레포 클론 및 권한 설정

```bash
git clone https://github.com/renslightsaber/aihub-no-pain-71349.git
cd aihub-no-pain-71349

# 셸 스크립트 실행 권한
chmod +x verify/*.sh preprocess/*.sh
```

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

aihubshell -mode d \
  -datasetkey 71349 \
  -aihubid <your_id> \
  -aihubpw <your_pw>
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

# filelist 위치 명시 (레포의 verify/filelist_71349.txt 사용)
FILELIST=~/aihub-no-pain-71349/verify/filelist_71349.txt \
  bash ~/aihub-no-pain-71349/verify/check_aihub.sh
```

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `FILELIST` | `./filelist_71349.txt` | AI Hub filelist 파일 경로 |
| `BASE_DIR` | `.` | 검사할 다운로드 루트 |
| `DEBUG` | `0` | 1이면 상세 매칭 로그 출력 |

### 기대 출력

```
============================================
  AI Hub 데이터셋 다운로드 진단
============================================
filelist 기준 파일 수    : 1412
실제 디스크 파일 수      : 1410
누락된 파일             : 2
download.tar 잔여물    : 1개 발견
.part 잔여물          : 0개

--- 누락 파일 목록 ---
  - TS_애니체_098.zip
  - VL_친절체_021.zip

다음 단계: bash repair_aihub.sh
```

### 2-2. zip 무결성 검증 — `verify_zips.sh`

모든 zip의 CRC 체크섬을 병렬로 검증합니다. 시간이 걸리지만 학습 전에 한 번은 돌리는 게 안전해요.

```bash
PARALLEL=8 bash ~/aihub-no-pain-71349/verify/verify_zips.sh
```

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `PARALLEL` | `4` | 병렬 작업 수. NFS는 8, 로컬 NVMe는 16+ 권장 |
| `BASE_DIR` | `.` | 검사 대상 디렉토리 |

### 기대 출력

```
============================================
  zip 무결성 검증
============================================
대상 zip: 1412개, 병렬: 8

[1/1412] ✓ TS_구연체_001.zip
[2/1412] ✓ TS_구연체_005.zip
...

=== 결과 ===
  소요 시간: 1733초 (28.8분)
  정상     : 1412
  손상     : 0

✓ 모든 zip 무결성 통과
```

손상된 zip이 있으면 자동으로 `damaged_zips.txt`에 기록됩니다.

### 2-3. 자동 복구 — `repair_aihub.sh`

`check_aihub.sh`와 `verify_zips.sh` 결과를 종합해 누락·손상 파일을 **자동 재다운로드**합니다.

```bash
# AI Hub 계정 정보 환경변수로 전달
AIHUB_ID=<your_id> AIHUB_PW=<your_pw> \
  bash ~/aihub-no-pain-71349/verify/repair_aihub.sh
```

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
[케이스 분류 중...]
  ok               : 1410
  broken           : 0
  missing          : 2
  residue_only     : 0
  never_downloaded : 0
  download.tar     : 1개 → 정리됨

[복구 시작]
  Downloading: TS_애니체_098.zip ... ✓
  Downloading: VL_친절체_021.zip ... ✓

[복구 후 재검증]
  모든 케이스 정상

✓ 복구 완료. 다음 단계: preprocess/
```

---

## 3. 압축 해제

### 3-1. zip 정리 — `move_zips_to_zips_dir.sh`

AI Hub 다운로드 폴더 구조는 깊고 복잡합니다. 이 스크립트는 **모든 zip을 `zips/`라는 한 폴더로 모으되, 원래 경로 구조는 보존**합니다.

```bash
cd /data/aihub_71349/

bash ~/aihub-no-pain-71349/preprocess/move_zips_to_zips_dir.sh
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
| `BASE_DIR` | `.` | 검색 시작 디렉토리 |
| `ZIPS_DIR` | `./zips` | zip을 모을 대상 디렉토리 |
| `DRY_RUN` | `0` | 1이면 실제 이동 없이 시뮬레이션만 |

### 3-2. 압축 해제 — `extract_zips.sh`

`zips/`의 모든 zip을 `data/`로 병렬 압축 해제합니다.

```bash
PARALLEL=8 bash ~/aihub-no-pain-71349/preprocess/extract_zips.sh
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

---

## 4. 메타데이터 생성

`build_metadata.py`는 모든 JSON 라벨을 파싱해 **학습 가능한 메타데이터 CSV**를 만들고, 통계 txt와 화자별 CSV까지 자동 생성합니다.

### 4-1. 기본 실행

```bash
cd /data/aihub_71349/

python3 ~/aihub-no-pain-71349/preprocess/build_metadata.py \
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
| `--label-pattern` | `**/T[LV]_*/*.json` | JSON 검색 패턴 |
| `--use-index` | `False` | wav 인덱스 미리 생성 (NFS stat 비용 절약) |

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

```
data_dir   : /data/aihub_71349/data
base_dir   : /data/aihub_71349
output_dir : /data/aihub_71349/meta

JSON 라벨 파일 검색 중...
  → 12,150개 JSON 발견
  진행: 12150/12150
  파싱 완료: 575,432개 row

[1/4] metadata.csv      : ./meta/metadata.csv
[2/4] stats_overall     : ./meta/stats_overall.txt
[3/4] stats_per_speaker : ./meta/stats_per_speaker.txt
      stats_per_gender  : ./meta/stats_per_gender.txt
[4/4] 화자별 CSV        : ./meta/metadatas_per_speaker/ (89개)

==================================================
총 row 수    : 575,432
고유 화자    : 89명
split 분포   : {'train': 560624, 'valid': 14808}
성별 분포    : {'FEMALE': 290000, 'MALE': 285432}
audio 누락   : 0건 (0.00%)
```

> ⚠️ `audio 누락`이 많이 나오면 압축 해제가 미완료된 경우가 대부분입니다. `extract_zips.sh`를 다시 돌려서 완료 후 재실행하세요.

---

## 5. 데이터 탐색

`explore_dataset.ipynb`는 **화자 ID를 선택하면 그 화자의 발화 샘플과 메타데이터를 함께 보여주는** 인터랙티브 노트북입니다.

### 5-1. 노트북 실행

```bash
# 필수 패키지
pip install pandas jupyter ipywidgets

# 노트북 실행
jupyter notebook ~/aihub-no-pain-71349/notebooks/explore_dataset.ipynb
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
# 1) 전체 wav 개수 (50만+여야 정상)
find ./data -name "*.wav" | wc -l

# 2) Validation 폴더도 풀렸는지
find ./data -path "*/Validation/*" -name "*.wav" | wc -l

# 3) 풀리지 않은 zip이 있다면 재실행 (이어서)
bash ~/aihub-no-pain-71349/preprocess/extract_zips.sh
```

압축 해제가 완료됐는데도 누락이 나오면 `--use-index` 옵션을 추가해보세요:

```bash
python3 build_metadata.py --data-dir ./data --output-dir ./meta --use-index
```

### FAQ 4. `unzip: warning: stripped absolute path spec` 가 무수히 출력돼요

이건 **정상**입니다. 데이터셋의 zip 내부 파일이 절대경로로 저장되어 있어서 unzip이 보안 메시지를 출력하는 거예요. 압축 해제는 완벽히 정상적으로 진행되고, `extract_zips.sh`가 이를 자동으로 처리합니다.

자세한 설명: [README #핵심 기능](README.md#-핵심-기능)

### FAQ 5. 한국어 폴더명 때문에 깨져요

UTF-8 로케일을 사용하는지 확인하세요:

```bash
locale
# LANG=en_US.UTF-8 또는 ko_KR.UTF-8 이어야 정상

# 만약 C 로케일이면 변경
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

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
bash ~/aihub-no-pain-71349/verify/check_aihub.sh   # 진단
bash ~/aihub-no-pain-71349/verify/repair_aihub.sh  # 복구
```

### FAQ 9. WSL2에서 사용 가능한가요?

네, 검증되었습니다. 다만 다음에 주의:
- WSL2의 기본 디스크는 `/mnt/c/`(Windows 드라이브)인데 매우 느립니다. WSL2 네이티브 파일시스템(`/home/user/...`) 또는 별도 Linux 디스크 사용 권장
- 한국어 폴더명을 위해 UTF-8 로케일 설정

### FAQ 10. 데이터셋 라이선스가 어떻게 되나요?

AI Hub의 이용약관을 따릅니다. 이 레포는 도구만 제공하며 데이터셋 자체를 배포하지 않습니다. 상업적 사용·재배포 관련은 AI Hub 공식 문서를 확인하세요.

---

## 🔗 관련 자료

- [데이터셋 구축 가이드라인 PDF](docs/감성및발화스타일동시고려음성합성데이터_구축활용_가이드라인.pdf) — JSON 스키마, 발화 스타일 정의, 라벨링 기준
- [데이터 설명서 PDF](docs/2-012-133_데이터설명서_감성_및_발화스타일_음성합성_데이터.pdf) — 통계, 분포, 활용 분야
- [AI Hub 공식 페이지](https://www.aihub.or.kr)
- 메인 [README.md](README.md)

---

문의 사항이나 버그는 GitHub Issues에 등록해주세요!
