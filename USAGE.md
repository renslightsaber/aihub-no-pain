# aihub-repair 상세 사용 가이드

> AI Hub 데이터셋 다운로드 검증·복구 스크립트의 완전한 사용 가이드.
> 빠른 시작은 [README.md](./README.md)를, 깊은 내용은 이 문서를 참고하세요.

---

## 📋 목차

1. [배경 — `aihubshell`의 한계와 이 도구가 필요한 이유](#1-배경)
2. [전체 워크플로우](#2-전체-워크플로우)
3. [사전 준비](#3-사전-준비)
4. [`check_aihub.sh` 상세](#4-check_aihubsh-상세)
5. [`verify_zips.sh` 상세](#5-verify_zipssh-상세)
6. [`repair_aihub.sh` 상세](#6-repair_aihubsh-상세)
7. [환경변수 완전 레퍼런스](#7-환경변수-완전-레퍼런스)
8. [실전 시나리오](#8-실전-시나리오)
9. [트러블슈팅](#9-트러블슈팅)
10. [FAQ](#10-faq)

---

## 1. 배경

### 🔬 `aihubshell`의 동작 방식과 한계

AI Hub의 `aihubshell -mode d`는 대용량 데이터셋을 다운로드할 때 다음 단계를 거칩니다:

```
1. 서버에서 download.tar로 한 덩어리 받기
2. tar를 풀면 *.zip.part0, *.zip.part1073741824, ... 가 나옴
3. 같은 prefix끼리 cat으로 병합 → *.zip 생성
4. 중간 산출물(*.part*, download.tar) 정리
```

이 과정에서 자주 발생하는 문제:

| 문제 | 원인 | 결과 |
|---|---|---|
| **byte-level resume 미지원** | aihubshell이 이어받기 옵션 없음 | 네트워크 1초만 끊겨도 그 부분부터 끝까지 잘림 |
| **디스크 부족** | 다운로드 + 병합 시 일시적으로 2배 공간 필요 | tar 풀다가 또는 병합 단계에서 실패 |
| **`Ctrl+C` 무시** | Java 기반 자식 프로세스가 시그널 핸들링 | 강제 종료 후 잔재만 남고 상태 불명 |
| **자동 정리 실패** | 위 문제들로 part·tar 잔재가 남음 | 어떤 파일이 정상인지 수동 확인 어려움 |
| **filelist 파싱 오류** | aihubshell -mode l 출력에 트리 문자(`│`, `├`, `─`) 포함 | 단순 파싱 시 파일명 앞에 트리 문자가 붙어 매칭 실패 |

`aihub-repair`는 이 5가지 문제를 자동으로 진단·복구합니다.

### 📦 다섯 가지 파일 상태

`repair_aihub.sh`는 모든 화자 파일을 다음 5가지 상태로 분류합니다:

| 상태 | 의미 | 조치 |
|---|---|---|
| `ok` | zip 정상, 잔재 없음 | 그대로 둠 |
| `broken` | zip 있지만 `unzip -tq` 실패 | 잔재 정리 + 재다운로드 |
| `missing` | zip 없고 `.part*` 잔재만 있음 | 잔재 정리 + 재다운로드 |
| `residue_only` | zip 정상 + `.part*` 잔재 남음 | part만 정리 |
| `never_downloaded` | filelist에 있지만 디스크에 흔적 0 | 재다운로드 |

여기에 추가로 `download.tar` 잔재도 별도 식별·제거합니다.

---

## 2. 전체 워크플로우

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 0: 사전 준비                                                 │
│    - aihubshell 설치                                                │
│    - export AIHUB_APIKEY='...'                                     │
│    - filelist 생성 (한 번만)                                         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Step 1: 풀 다운로드 (처음 받는 경우만)                              │
│    $ aihubshell -mode d -datasetkey 71349 -aihubapikey "$AIHUB_..."  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Step 2: 빠른 진단 (check_aihub.sh) — 수 초                          │
│    $ ./check_aihub.sh                                                │
│    → filelist vs 디스크 비교, 누락·잔재 식별                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
              모든 ✓ ?                  이상 발견 ?
                  │                       │
                  ▼                       ▼
            Step 3로 진행          Step 4 (복구) →
                                       Step 2 재실행
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Step 3: 무결성 검증 (verify_zips.sh) — 수 분~수십 분                │
│    $ ./verify_zips.sh                                                │
│    → 모든 zip 병렬 unzip -tq                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
              모든 ✓ ?                  깨진 파일 발견
                  │                       │
                  ▼                       ▼
            학습 시작 OK            Step 4 (복구)
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Step 4: 자동 복구 (repair_aihub.sh)                                 │
│    $ DRY_RUN=1 ./repair_aihub.sh   # 먼저 미리보기                   │
│    $ ./repair_aihub.sh             # 실제 실행                       │
│    → 잔재 정리 + filekey batch 재다운로드                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         Step 2로 복귀 (수렴 확인)
```

**원칙**: 가벼운 도구부터 시작해서 무거운 도구로 escalation. `check` → `verify` → `repair` 순서.

---

## 3. 사전 준비

### 3-1. `aihubshell` 설치 확인

```bash
command -v aihubshell
aihubshell -help
```

설치가 안 됐다면 [AI Hub 공식 가이드](https://aihub.or.kr/devsport/apishell/list.do)를 참고하세요.

### 3-2. API 키 등록

```bash
# 일회용
export AIHUB_APIKEY='발급받은-API-키'

# 영구 등록 (~/.bashrc 또는 ~/.zshrc)
echo "export AIHUB_APIKEY='...'" >> ~/.bashrc
chmod 600 ~/.bashrc           # 공용 서버라면 권한 잠그기
source ~/.bashrc
```

### 3-3. filelist 한 번 떠두기 (필수)

세 스크립트 모두 filelist를 기준으로 동작하므로 **반드시 먼저 생성**해야 합니다.

```bash
cd /data1/your_dataset_dir/
aihubshell -mode l -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY" > filelist_71349.txt
```

생성된 파일 확인:
```bash
head -20 filelist_71349.txt
wc -l filelist_71349.txt
```

> 💡 **filelist 포맷 예시**:
> ```
>             │  │  ├─TS_구연체_001.zip | 560 MB | 559997
>             │  │  ├─TS_구연체_005.zip | 657 MB | 559998
>             │  │  ├─TS_낭독체_001.zip | 127 MB | 560047
> ```
> 트리 문자 `│`, `├`, `─`와 들여쓰기 공백이 들어있어도 v2 스크립트가 자동 처리합니다.

### 3-4. 스크립트 배치

```bash
cd /data1/your_dataset_dir/
cp /path/to/aihub-repair/*.sh .
chmod +x check_aihub.sh verify_zips.sh repair_aihub.sh
```

**중요**: 스크립트는 데이터셋 폴더(`133.감성_및_발화_스타일_...`)가 위치한 **상위 디렉토리**에서 실행하세요. `ROOT` 기본값이 `./133.감성_...`이라서요.

### 3-5. 디스크 공간 확인

데이터셋 명목 크기의 **최소 2.5배** 여유 공간이 필요합니다:
- 원본 zip × 1
- 다운로드 중 part 잔재 × 1
- 병합 시 임시 공간 × 0.5

```bash
df -h .
# Available 항목 확인
```

---

## 4. `check_aihub.sh` 상세

### 역할
filelist와 디스크를 빠르게 비교해서 표면적 이상을 식별합니다.

### 실행

```bash
./check_aihub.sh

# 옵션
DEBUG=1 ./check_aihub.sh              # 파싱 결과 출력 (디버깅용)
SHOW_DETAILS=0 ./check_aihub.sh       # 통계만 (CI/스크립트용)
USE_COLOR=0 ./check_aihub.sh          # 색깔 끄기
```

### 출력 해석

**정상 케이스**:
```
📊 개수 비교
  filelist 등록 zip : 1412
  디스크 zip        : 1412
  part 잔재         : 0
  download.tar 잔재 : 0

✓ 모든 zip 파일이 정상적으로 다운로드되었습니다.
  (단, zip 내부 무결성은 별도 검증 필요: ./verify_zips.sh)
```

**이상 발견 케이스**:
```
✗ 이상 발견:
  - 누락 파일: 3건
  - part 잔재: 2건

📋 누락된 파일 상세
─────────────────────────────────────────────────────────────────────
파일명(정규화)                            용량       filekey
─────────────────────────────────────────────────────────────────────
VS_애니체_043.zip                         5.2 GB     84751
VL_낭독체_012.zip                         1.8 GB     84823
TS_중계체_007.zip                         3.4 GB     84802
─────────────────────────────────────────────────────────────────────

💡 복구 방법
  (A) 자동 복구:    ./repair_aihub.sh
  (B) 수동 명령:    aihubshell -mode d -datasetkey 71349 \
                                -filekey '84751,84823,84802' \
                                -aihubapikey "$AIHUB_APIKEY"
```

### DEBUG 모드 활용

처음 실행 시 또는 매칭이 안 될 때 한 번 돌려보세요:

```bash
DEBUG=1 ./check_aihub.sh 2>&1 | head -30
```

기대 출력:
```
[DEBUG] L1: name=[TS_구연체_001.zip] size=[560 MB] key=[559997]
[DEBUG] L2: name=[TS_구연체_005.zip] size=[657 MB] key=[559998]
...
[DEBUG] disk=[TS_구연체_001.zip] norm=[TS_구연체_001.zip] → filelist 매칭 ✓
[DEBUG] disk=[TS_구연체_005.zip] norm=[TS_구연체_005.zip] → filelist 매칭 ✓
```

`매칭 ✓`이 떠야 정상. `매칭 ✗`이면 filelist 포맷 또는 인코딩 문제 → [트러블슈팅](#9-트러블슈팅) 참고.

### 종료 코드
- `0`: 모든 검증 통과
- `1`: 이상 발견 (누락 파일 또는 잔재)

---

## 5. `verify_zips.sh` 상세

### 역할
모든 zip 파일을 병렬로 `unzip -tq` 검증합니다. zip 내부의 CRC까지 확인.

### 실행

```bash
./verify_zips.sh                       # 기본 (PARALLEL=8)
PARALLEL=16 ./verify_zips.sh           # 16개 병렬
SHOW_DETAILS=0 ./verify_zips.sh        # 통계만
```

### 소요 시간 예상

| 디스크 | PARALLEL=8 | PARALLEL=16 | 비고 |
|---|---|---|---|
| 로컬 NVMe SSD | 5~10분 | 3~7분 | I/O 매우 빠름 |
| 로컬 SATA SSD | 15~25분 | 12~20분 | |
| NFS | 20~40분 | 15~30분 | 네트워크 대역폭 병목 |
| HDD | 40분~1시간+ | 거의 동일 | 디스크 병목 |

**기준**: 1412개 zip, 평균 600MB (총 약 850GB).

### 출력 해석

**정상**:
```
🔍 검증 시작 (1412개, 병렬 8)

📊 검증 결과 (47초)
  정상 : 1412건
  깨짐 : 0건

✓ 모든 zip 무결성 통과
```

**깨진 파일 발견**:
```
✗ 깨진 zip 발견

📋 깨진 파일 상세
─────────────────────────────────────────────────────────────────────
파일명(정규화)                            용량       filekey
─────────────────────────────────────────────────────────────────────
VS_애니체_004.zip                         3.1 GB     84751
TS_중계체_012.zip                         4.5 GB     84823
─────────────────────────────────────────────────────────────────────

💡 복구 방법
  (A) 자동 복구:    ./repair_aihub.sh
  (B) 수동 명령:    aihubshell -mode d -datasetkey 71349 \
                                -filekey '84751,84823' \
                                -aihubapikey "$AIHUB_APIKEY"
```

### 종료 코드
- `0`: 모든 zip 정상
- `1`: 깨진 zip 발견 또는 검증 불가

---

## 6. `repair_aihub.sh` 상세

### 역할
검증·정리·재다운로드를 한 번에 수행. 5가지 상태를 모두 처리합니다.

### 실행

```bash
# 검증만 (디스크 변경 X)
DRY_RUN=1 ./repair_aihub.sh

# 실제 실행
./repair_aihub.sh

# 일부 화자만 받은 상태에서 그것만 복구
INCLUDE_NEVER_DOWNLOADED=0 ./repair_aihub.sh

# 작은 batch로 부담 분산
BATCH=20 ./repair_aihub.sh
```

### 동작 단계

```
[1/3] 데이터셋 상태 점검
   ├─ (1-A) 모든 zip 무결성 검증 (순차)
   ├─ (1-B) part 잔재 식별 (.part0, .part1073741824 등)
   ├─ (1-C) download.tar 잔재 식별
   ├─ (1-D) filelist 파싱 → ground truth 구축
   ├─ (1-E) never_downloaded 식별 (filelist vs 디스크)
   ├─ (1-F) 5가지 상태 통계 출력
   └─ (1-G) 잔재 정리 (DRY_RUN=0일 때만)
            ├─ download.tar 제거
            ├─ broken/missing/never_downloaded → zip + part 모두 제거
            └─ residue_only → part만 제거 (zip 보존)

[2/3] filekey 매핑
   └─ unhealthy 파일들의 filekey 추출

[3/3] batch 재다운로드
   └─ filekey를 BATCH 크기씩 묶어 aihubshell -filekey 호출
```

### 권장 실행 패턴

```bash
# 1) 항상 dry-run으로 먼저 확인
DRY_RUN=1 ./repair_aihub.sh

# 출력을 보고 합리적이면 실제 실행
./repair_aihub.sh 2>&1 | tee repair_$(date +%Y%m%d_%H%M%S).log

# 수렴 확인 (깨진 파일이 0건이 될 때까지 반복)
./repair_aihub.sh
./repair_aihub.sh
```

보통 2~3회 안에 수렴합니다. 매 반복마다 일부 batch가 재실패할 수 있어서 (네트워크 일시 끊김 등) 0건 될 때까지 돌리세요.

### 50% 이상 누락 경고

만약 filelist 전체의 50% 이상이 `never_downloaded`로 잡히면 다음 경고가 출력됩니다:

```
[WARN] 706/1412 (50%)가 다운로드 시도조차 안 된 상태입니다.
       만약 일부만 의도적으로 받으셨다면 INCLUDE_NEVER_DOWNLOADED=0 로 실행하세요.
```

의도된 부분 다운로드라면 `INCLUDE_NEVER_DOWNLOADED=0`으로 실행해서 디스크에 있는 것만 복구하세요.

---

## 7. 환경변수 완전 레퍼런스

### 공통 (세 스크립트 모두)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `AIHUB_APIKEY` | (필수, repair만) | AI Hub API 키. `export` 권장 |
| `DATASET_KEY` | `71349` | AI Hub 데이터셋 번호 |
| `ROOT` | `./133.감성_및_발화_스타일_...` | 데이터 루트 디렉토리 |
| `FILELIST` | `filelist_${DATASET_KEY}.txt` | filelist 파일 경로 |
| `SHOW_DETAILS` | `1` | `0`이면 통계만 출력 |
| `USE_COLOR` | `auto` | `0`/`1`로 강제 가능 |
| `DEBUG` | `0` | `1`이면 파싱 디버그 정보 |

### `verify_zips.sh` 전용

| 변수 | 기본값 | 설명 |
|---|---|---|
| `PARALLEL` | `8` | 병렬 작업 수. CPU 코어 수만큼 권장 |

### `repair_aihub.sh` 전용

| 변수 | 기본값 | 설명 |
|---|---|---|
| `BATCH` | `50` | filekey batch 크기 |
| `DRY_RUN` | `0` | `1`이면 디스크 변경 없이 시뮬레이션 |
| `INCLUDE_NEVER_DOWNLOADED` | `1` | `0`이면 디스크 흔적 있는 것만 복구 |

### 환경변수 한 번에 export

자주 쓰는 데이터셋이라면 셸 함수로:

```bash
# ~/.bashrc 또는 ~/.zshrc
aihub_133() {
  export DATASET_KEY=71349
  export ROOT='/data1/aihub/kor_senti_style_tts_dataset/133.감성_및_발화_스타일_동시_고려_음성합성_데이터'
  export FILELIST='/data1/aihub/kor_senti_style_tts_dataset/filelist_71349.txt'
  cd /data1/aihub/kor_senti_style_tts_dataset
}

aihub_464() {
  export DATASET_KEY=464
  export ROOT='/data1/aihub/multilingual/464.다국어_통번역_음성_데이터'
  export FILELIST='/data1/aihub/multilingual/filelist_464.txt'
  cd /data1/aihub/multilingual
}
```

사용:
```bash
aihub_133            # 환경 세팅 + cd
./check_aihub.sh     # 바로 실행 가능
```

---

## 8. 실전 시나리오

### 시나리오 A: 처음 받는 데이터셋

```bash
# 1) 환경 준비
export AIHUB_APIKEY='...'
mkdir -p /data1/aihub/new_dataset
cd /data1/aihub/new_dataset

# 2) filelist 미리 떠보고 포맷 확인
aihubshell -mode l -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY" > filelist_71349.txt
head -20 filelist_71349.txt
grep -oE '\.[a-z0-9]+ \|' filelist_71349.txt | sort -u   # zip만 있는지 확인

# 3) 풀 다운로드
aihubshell -mode d -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY" 2>&1 | tee download.log

# 4) 스크립트 복사 + 검증
cp ~/aihub-repair/*.sh .
chmod +x *.sh

./check_aihub.sh                 # 표면 점검
./verify_zips.sh                 # 무결성 검증

# 5) 이상 있으면 복구 반복
DRY_RUN=1 ./repair_aihub.sh
./repair_aihub.sh
./check_aihub.sh && ./verify_zips.sh   # 0건 될 때까지
```

### 시나리오 B: 다운로드 중 디스크 부족으로 멈춤

```bash
# 1) 좀비 프로세스 정리
ps -ef | grep -E "aihubshell|java" | grep -v grep
pkill -9 -f aihubshell

# 2) 디스크 정리 후 더 큰 볼륨으로 이동
df -h
mv /home/user/aihub_data /data1/aihub_data
cd /data1/aihub_data

# 3) 상태 점검
./check_aihub.sh        # 어떤 파일이 깨졌는지/누락됐는지 확인

# 4) 복구
DRY_RUN=1 ./repair_aihub.sh    # 미리보기 (어떤 filekey가 재다운로드될지)
./repair_aihub.sh              # 실제 실행
```

### 시나리오 C: 일부 화자만 받기로 한 경우

```bash
# 처음부터 -filekey로 일부만 받음
aihubshell -mode d -datasetkey 71349 -filekey '12345,12346,12347' -aihubapikey "$AIHUB_APIKEY"

# 받은 것만 검증 (누락은 의도된 것이므로 제외)
INCLUDE_NEVER_DOWNLOADED=0 ./check_aihub.sh
INCLUDE_NEVER_DOWNLOADED=0 ./repair_aihub.sh
```

### 시나리오 D: 학습 직전 최종 검증

```bash
# 매일 학습 시작 전
./check_aihub.sh

# 주 1회 (또는 데이터 의심될 때)
./verify_zips.sh

# 둘 다 ✓ 나오면 학습 시작
python train.py --data_root /data1/aihub/...
```

### 시나리오 E: 여러 데이터셋 동시 관리

```bash
# ~/.bashrc에 등록한 함수 활용
aihub_133 && ./check_aihub.sh
aihub_464 && ./check_aihub.sh
aihub_595 && ./check_aihub.sh
```

---

## 9. 트러블슈팅

### 9-1. "filelist 파싱 실패" 에러

```
[ERROR] filelist 파싱 0건. 포맷 확인:
        head -20 filelist_71349.txt
```

**원인**: filelist에 `.zip` 라인이 없거나 포맷이 예상과 다름.

**진단**:
```bash
# 보이지 않는 문자 포함해서 첫 5줄 보기
head -5 filelist_71349.txt | cat -A

# 인코딩 확인
file filelist_71349.txt
# → UTF-8이어야 함

# 한 라인의 hex 덤프
grep -m1 ".zip" filelist_71349.txt | hexdump -C | head -3
```

**해결**:
- `file` 결과가 UTF-8이 아니면: `iconv`로 변환
- 라인에 `.zip`이 없으면: aihubshell 출력 형식이 변경됐을 수 있음, AI Hub 문의

### 9-2. "멀쩡한 파일을 누락이라고 표시함"

**증상**: 디스크에 분명히 있는 파일이 `누락 파일` 목록에 나옴.

**원인** (가능성 순):
1. filelist의 트리 문자(`│`, `├`) 또는 들여쓰기 공백
2. 디스크와 filelist 인코딩 차이 (UTF-8 NFC vs NFD)
3. 한글 자모 분리 (macOS HFS+)

**진단**:
```bash
DEBUG=1 ./check_aihub.sh 2>&1 | head -40
```

`매칭 ✓`이 떠야 정상. `매칭 ✗`이면:

```bash
# filelist의 파일명 한 줄 hex
grep -m1 "TS_구연체_001" filelist_71349.txt | hexdump -C | head -3

# 디스크 파일의 hex
find . -name "TS_구연체_001.zip" -printf "%f\n" | head -1 | hexdump -C
```

두 hex가 다르면 인코딩 또는 정규화 문제. v2 스크립트는 공백 정규화는 자동 처리하지만, NFC/NFD 차이는 별도 처리 필요. 발생 시 이슈 등록 부탁.

### 9-3. `Ctrl+C`로 aihubshell이 안 죽음

**원인**: aihubshell이 Java 자식 프로세스를 띄우는데, 자식이 SIGINT를 무시.

**해결**:
```bash
# 다른 터미널에서
pkill -TERM -f aihubshell    # 부드럽게
sleep 5
pkill -KILL -f aihubshell    # 강제

# 또는 SIGQUIT (Ctrl+\)
# WezTerm을 쓰면 Ctrl+Shift+\ 매핑 추천
```

종료 후:
```bash
./repair_aihub.sh    # 잔재 자동 정리
```

### 9-4. 디스크 부족으로 다운로드 실패

**증상**: `aihubshell` 로그에 `No space left on device`.

**원인**: 다운로드 + 병합 시 일시적으로 데이터셋 명목 크기의 2배 공간 필요.

**해결**:
```bash
# 더 큰 볼륨 찾기
df -h | sort -k4 -h

# 데이터셋 옮기기 (받다 만 잔재 포함)
mv 133.감성_* /data1/aihub/

# /data1에서 재시도
cd /data1/aihub
./repair_aihub.sh    # 잔재 정리 후 재다운로드
```

### 9-5. NFS/원격 디스크에서 `verify_zips.sh` 너무 느림

**원인**: 네트워크 대역폭 병목.

**해결**:
- 로컬 디스크로 데이터셋 이동
- 또는 `PARALLEL`을 늘려보기 (어차피 대역폭 한계지만 미세하게는 빨라짐)
- 또는 검증을 야간에 백그라운드로:
  ```bash
  nohup ./verify_zips.sh > verify_$(date +%Y%m%d).log 2>&1 &
  ```

### 9-6. `bash 4.0+` 에러 (macOS)

**증상**: `[ERROR] bash 4.0+ 필요`

**해결**: macOS 기본 bash는 3.2 (라이선스 문제). `brew install bash`로 4+ 설치:
```bash
brew install bash
which bash                    # /usr/local/bin/bash 또는 /opt/homebrew/bin/bash
/opt/homebrew/bin/bash --version
/opt/homebrew/bin/bash ./check_aihub.sh
```

### 9-7. 50%+ 누락 경고가 부정확함

**증상**: 일부만 의도적으로 받았는데 50%+ 누락 경고가 뜸.

**해결**:
```bash
INCLUDE_NEVER_DOWNLOADED=0 ./repair_aihub.sh
```
이러면 디스크에 있는 것만 복구 대상으로 처리됩니다.

---

## 10. FAQ

**Q1. 데이터셋이 너무 커서 `verify_zips.sh`가 1시간 이상 걸려요.**

A. 정상입니다. 다음을 시도해 보세요:
- 데이터셋을 로컬 NVMe SSD로 이동 (10배 빠름)
- `PARALLEL=16` 또는 `32`로 늘림 (단, 디스크 대역폭이 상한선)
- 매일 돌리지 말고 학습 직전 1회만

**Q2. 같은 데이터셋을 두 곳에 두고 비교하고 싶어요.**

A. `ROOT` 환경변수만 바꿔서 두 번 실행하면 됩니다:
```bash
ROOT='/data1/aihub_a/133.감성_...' ./check_aihub.sh
ROOT='/data2/aihub_b/133.감성_...' ./check_aihub.sh
```

**Q3. 부분 다운로드 진행률 표시는 어떻게 보나요?**

A. `aihubshell` 자체가 출력하는 진행률을 보세요. `repair_aihub.sh`의 `[3/3]` 단계에서 `aihubshell`이 호출될 때 그 stdout이 그대로 표시됩니다. 로그 저장:
```bash
./repair_aihub.sh 2>&1 | tee repair.log
```

**Q4. `Ctrl+C`로 `verify_zips.sh`를 중단하면 안전한가요?**

A. 안전합니다. `verify_zips.sh`는 디스크에 쓰지 않고 읽기만 합니다. 중단해도 데이터 손상 없습니다. `repair_aihub.sh`는 잔재 정리 단계 직전이라면 안전하지만, 정리 도중 중단하면 부분 정리 상태가 될 수 있어요. 그래도 다시 돌리면 자동으로 마무리됩니다.

**Q5. zip이 아닌 다른 형식의 데이터셋도 처리할 수 있나요?**

A. 현재는 `.zip`만 지원합니다 (`unzip -tq`로 검증). `.tar.gz`나 `.7z`는 별도 스크립트가 필요해요. 거의 모든 AI Hub 데이터셋이 zip 기반이라 일반적인 경우엔 문제 없습니다.

**Q6. CI/자동화에 통합하고 싶어요.**

A. `SHOW_DETAILS=0 USE_COLOR=0`으로 깔끔한 출력을, 종료 코드로 결과 판정:
```bash
#!/bin/bash
SHOW_DETAILS=0 USE_COLOR=0 ./check_aihub.sh
if [ $? -eq 0 ]; then
    echo "OK"
else
    # 알림 보내기
    curl -X POST https://hooks.slack.com/...
fi
```

**Q7. 검증 결과를 저장해 두고 다음에 변경된 파일만 검증할 수 있나요?**

A. 현재 버전은 매번 전체 검증입니다. 캐싱 기능은 미구현. 필요하시면 이슈로 알려주세요.

**Q8. 다른 데이터셋 번호의 filelist도 같은 디렉토리에 두고 싶어요.**

A. `FILELIST` 환경변수를 다르게 지정하면 됩니다:
```bash
FILELIST=filelist_71349.txt ./check_aihub.sh
FILELIST=filelist_464.txt ./check_aihub.sh
```

**Q9. 스크립트 안에 데이터셋 별 default를 박아두고 싶어요.**

A. 권장하지 않습니다. 환경변수로 외부에서 지정하는 패턴이 재활용성이 높아요. 자주 쓰는 데이터셋이면 셸 함수로 등록하세요 ([7-3 환경변수 한 번에 export](#환경변수-한-번에-export) 참고).

**Q10. 학습 데이터 무결성을 매번 확인해야 할까요?**

A. 일반적으로 한 번 통과하면 안 깨집니다. 다만 디스크 이동, 백업/복원, 네트워크 전송 후엔 한 번 더 검증하는 게 안전합니다. 학습 결과가 이상하면 데이터 무결성부터 의심하세요.

---

## 📚 참고 자료

- [AI Hub 공식 사이트](https://aihub.or.kr/)
- [aihubshell 가이드](https://aihub.or.kr/devsport/apishell/list.do)
- [README.md (요약)](./README.md)

---

## 🐛 이슈 등록

문제 발생 시 다음 정보와 함께 이슈를 등록해주세요:

1. 실행한 명령어
2. 출력 (특히 에러 메시지)
3. `DEBUG=1` 모드 출력
4. 환경: `bash --version`, `locale`, `file filelist_*.txt`
5. filelist 첫 5줄 (`head -5 filelist_*.txt`)

이 정보가 있으면 디버깅이 훨씬 빨라집니다.
