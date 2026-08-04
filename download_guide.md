# 📥 다운로드 가이드 (datasetkey=71349)

AI Hub 「감성 및 발화스타일 동시 고려 음성합성 데이터」를 **끊김 없이 전량 내려받고, 받은 게 온전한지 확인하는 것**까지만 다루는 문서입니다.

- 압축 해제 이후(메타데이터·탐색)는 → **[USAGE.md](USAGE.md)**
- 프로젝트 전체 개요는 → **[README.md](README.md)**

> 이 문서의 명령은 **컨테이너·원격 서버(sudo 없음, 로케일 최소 설치, NFS 스토리지)** 환경을 기본 가정으로 작성했습니다.
> 데스크톱 리눅스라면 더 쉽게 진행됩니다.

---

## 📑 목차

- [0. 5줄 요약](#0-5줄-요약)
- [1. 준비물 체크리스트](#1-준비물-체크리스트)
- [2. 용량·소요 시간 예상](#2-용량소요-시간-예상)
- [3. aihubshell 설치](#3-aihubshell-설치)
- [4. 로케일 확인 (한글 폴더명)](#4-로케일-확인-한글-폴더명)
- [5. 작업 디렉토리 준비](#5-작업-디렉토리-준비)
- [6. 다운로드 실행](#6-다운로드-실행)
- [7. ROOT 잡기](#7-root-잡기)
- [8. 검증 → 복구 루프](#8-검증--복구-루프)
- [9. 부분 다운로드 (원하는 것만 받기)](#9-부분-다운로드-원하는-것만-받기)
- [10. 중단·재개](#10-중단재개)
- [11. 완료 체크리스트](#11-완료-체크리스트)
- [12. 다운로드 단계 트러블슈팅](#12-다운로드-단계-트러블슈팅)

---

## 0. 5줄 요약

```bash
export REPO=~/aihub-no-pain-71349            # 이 레포를 클론한 경로
export DSET=/data/aihub_71349                # 데이터셋을 받을 경로
export AIHUB_APIKEY='<your_api_key>'
export LANG=C.UTF-8 LC_ALL=C.UTF-8           # locale -a 에 있는 이름으로!

mkdir -p "$DSET" && cd "$DSET" && cp "$REPO/verify/filelist_71349.txt" .
aihubshell -mode d -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY"
export ROOT="$(find . -maxdepth 1 -type d -name '133.*' | head -1)"
bash "$REPO/verify/check_aihub.sh" && PARALLEL=8 bash "$REPO/verify/verify_zips.sh"
```

이상이 나오면 [8장](#8-검증--복구-루프)으로. 정상이면 [USAGE.md 3장(압축 해제)](USAGE.md#3-압축-해제)으로.

---

## 1. 준비물 체크리스트

| # | 항목 | 확인 명령 | 통과 기준 |
|---|---|---|---|
| 1 | AI Hub 계정 + **71349 다운로드 승인** | 마이페이지 | 신청 후 보통 1~3일 |
| 2 | **API Key** 발급 | 마이페이지 → API Key | ID/PW가 **아님** |
| 3 | `aihubshell` | `command -v aihubshell` | 경로 출력 ([3장](#3-aihubshell-설치)) |
| 4 | `curl`, `unzip`, `find`, `xargs`, `awk`, `sed`, `tr` | `for c in curl unzip find xargs awk sed tr; do command -v $c \|\| echo "missing: $c"; done` | 전부 출력 |
| 5 | bash 4.0+ | `echo $BASH_VERSION` | 4.x 이상 |
| 6 | 디스크 여유 **600GB+** | `df -BG "$DSET"` | Available ≥ 600 |
| 7 | inode 여유 | `df -i "$DSET"` | IUse% < 80 |
| 8 | UTF-8 로케일 | `locale charmap` | `UTF-8` ([4장](#4-로케일-확인-한글-폴더명)) |
| 9 | Python 3.8+ (5단계에서 사용) | `python3 -V` | 3.8 이상 |

> **`AIHUB_ID`/`AIHUB_PW`는 이 레포에서 쓰지 않습니다.** `repair_aihub.sh`는 `AIHUB_APIKEY`가 없으면 즉시 종료합니다.

---

## 2. 용량·소요 시간 예상

`verify/filelist_71349.txt`(AI Hub 제공 파일 목록)의 크기를 합산한 실측값입니다.

| 구분 | 내용 | zip 개수 | 용량 |
|---|---|---:|---:|
| `TS_*` | Training 원천데이터 (wav) | 353 | **192.9 GB** |
| `VS_*` | Validation 원천데이터 (wav) | 353 | **24.3 GB** |
| `TL_*` | Training 라벨데이터 (JSON) | 353 | 0.1 GB |
| `VL_*` | Validation 라벨데이터 (JSON) | 353 | 0.02 GB |
| **합계** | | **1,412** | **약 217 GB** |

### 📊 실측값 (2026-08 전량 다운로드 완료 기준)

위 표는 filelist의 표기 용량을 합산한 값이고, 아래는 **실제로 끝까지 받아서 풀어 본 결과**입니다.

| 항목 | 실측 | 비고 |
|---|---:|---|
| zip 개수 | **1,412개** | filelist와 정확히 일치 |
| zip 실제 점유 | **220 GB** | `du -sh` (표기 합산 217GB보다 약간 큼 — 블록 단위 점유) |
| 압축 해제 후 | **293 GB** | 추정치 320GB보다 작음 |
| **동시 보관 최대치** | **약 513 GB** | zip 220 + 해제 293 |
| zip 삭제 후 최종 | **293 GB** | → [zip 삭제 절차](USAGE.md#3-3-zip-삭제로-용량-회수하기) |
| 풀린 파일 총 개수 | **636,045개** | wav 622,905 + JSON 13,140 |
| ├ Training | wav 559,887 / JSON 11,875 | |
| └ Validation | wav 63,018 / JSON 1,265 | |

> 💡 **디스크는 600GB 이상**을 권장합니다. 압축 해제 중에는 zip과 해제본을 동시에 들고 있어야 해서
> 순간 최대 513GB가 필요하고, 파일시스템 여유와 메타데이터(`meta/` 1.3GB)까지 감안한 값입니다.
> 압축 해제가 끝나면 zip을 지워 220GB를 회수할 수 있습니다.

> ⚠️ **inode도 함께 확인하세요.** 63만 개의 작은 파일이 생성됩니다. `df -i "$DSET"` 의 `IFree`가
> 70만 이상이어야 안전합니다.

직접 합산해서 확인하려면:

```bash
sed -e 's/[─├└│]/ /g' "$REPO/verify/filelist_71349.txt" \
 | grep -oE '[A-Z]{2}_[^ |]+\.zip *\| *[0-9.]+ ?(KB|MB|GB)' \
 | awk -F'|' '{split($2,s," "); v=s[1]; u=s[2];
     b = (u=="KB")? v/1048576 : (u=="MB")? v/1024 : v;
     n=substr($1,1,2); t[n]+=b; c[n]++; all+=b}
   END{for(k in t) printf "%-3s %4d개 %8.1f GB\n",k,c[k],t[k]; printf "TOTAL %8.1f GB\n", all}'
```

**소요 시간**은 회선·AI Hub 서버 상태에 좌우됩니다. 100Mbps에서 약 5시간, 1Gbps에서 약 40분이 이론치이며 실제로는 더 걸립니다. `nohup`/`tmux`로 띄워 두세요.

---

## 3. aihubshell 설치

`aihubshell version 25.09.19 v0.6` 이상에서 검증했습니다.

**sudo 가 있는 경우**

```bash
curl -o aihubshell https://api.aihub.or.kr/api/aihubshell.do
chmod +x aihubshell
sudo mv aihubshell /usr/bin/
```

**sudo 가 없는 경우 (컨테이너 등)**

```bash
mkdir -p ~/bin && cd ~/bin
curl -o aihubshell https://api.aihub.or.kr/api/aihubshell.do
chmod +x aihubshell
export PATH="$HOME/bin:$PATH"
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc     # 다음 로그인에도 유지
```

확인:

```bash
command -v aihubshell && aihubshell -help
```

> 배포 URL과 최신 설치 절차는 AI Hub 공식 안내를 한 번 확인하세요. 내려받은 파일이 HTML(에러 페이지)이면
> `head -3 ~/bin/aihubshell` 로 확인 후 다시 받으세요.

---

## 4. 로케일 확인 (한글 폴더명)

데이터셋 폴더명이 한글이라 **문자셋이 UTF-8**이어야 합니다. 로케일 *이름*은 무엇이든 상관없습니다.

```bash
locale charmap        # → UTF-8 이면 통과
```

`ANSI_X3.4-1968`(ASCII)이 나오면 **설치돼 있는 로케일 중에서** UTF-8 계열을 지정하세요:

```bash
locale -a                       # 예: C, C.utf8, POSIX 만 있는 경우가 흔함
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
```

> ⚠️ 설치되지 않은 이름(`en_US.UTF-8` 등)을 지정하면
> `-bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)` 경고와 함께
> **로케일이 ASCII로 떨어질 수 있습니다.** `locale -a`에 있는 이름만 쓰세요.
> `C.UTF-8`이면 한글 경로, `find`, `basename`, 스크립트의 파일명 정규화 모두 정상 동작합니다.
> `en_US.UTF-8`이 꼭 필요하면 root 권한으로 `sudo locale-gen en_US.UTF-8 && sudo update-locale`.

---

## 5. 작업 디렉토리 준비

```bash
export REPO=~/aihub-no-pain-71349
export DSET=/data/aihub_71349            # 원하는 경로로
export AIHUB_APIKEY='<your_api_key>'

mkdir -p "$DSET"
cd "$DSET"

# 검증 스크립트의 기본 탐색 위치(./filelist_71349.txt)에 맞춰 복사
cp "$REPO/verify/filelist_71349.txt" .
```

`filelist_71349.txt`에는 zip 1,412개의 **이름 · 용량 · filekey**가 들어 있습니다.
`check_aihub.sh`·`verify_zips.sh`·`repair_aihub.sh`가 모두 이 파일을 기준값으로 씁니다.

**(선택) filelist 최신화** — AI Hub가 파일 구성을 바꿨을 때:

```bash
aihubshell -mode l -datasetkey 71349 > filelist_71349.txt
head -20 filelist_71349.txt          # 트리 + "이름 | 용량 | filekey" 형식인지 확인
```

---

## 6. 다운로드 실행

```bash
cd "$DSET"
aihubshell -mode d -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY"
```

**장시간 실행이므로 세션이 끊겨도 살아남게 띄우세요:**

```bash
# tmux 권장
tmux new -s aihub
#   (안에서) aihubshell -mode d -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY"
#   Ctrl+b d 로 분리, tmux attach -t aihub 로 복귀

# 또는 nohup
nohup aihubshell -mode d -datasetkey 71349 -aihubapikey "$AIHUB_APIKEY" > download.log 2>&1 &
tail -f download.log
```

**진행 상황 모니터링 (다른 터미널)**

```bash
watch -n 60 'find "$DSET" -name "*.zip" | wc -l; du -sh "$DSET"'
# 1412개 / 약 220GB 에 수렴하면 완료
```

완료 후 구조:

```
$DSET/
├── filelist_71349.txt
└── 133.감성 및 발화 스타일 동시 고려 음성합성 데이터/
    └── 01-1.정식개방데이터/
        ├── Training/
        │   ├── 01.원천데이터/     ← TS_*.zip (wav)
        │   └── 02.라벨링데이터/   ← TL_*.zip (JSON)
        └── Validation/
            ├── 01.원천데이터/     ← VS_*.zip
            └── 02.라벨링데이터/   ← VL_*.zip
```

---

## 7. ROOT 잡기

셸 스크립트들은 다운로드 루트를 **`ROOT` 환경변수**로 받습니다. (`BASE_DIR`이 아닙니다.)

기본값은 밑줄이 들어간 `./133.감성_및_발화_스타일_동시_고려_음성합성_데이터`입니다.
그런데 **aihubshell 버전·로케일에 따라 폴더명이 두 가지로 갈립니다:**

| 실제 생성되는 이름 | 기본값과 | 조치 |
|---|---|---|
| `133.감성_및_발화_스타일_동시_고려_음성합성_데이터` (밑줄) | 일치 ✅ | `ROOT` 안 잡아도 동작 |
| `133.감성 및 발화 스타일 동시 고려 음성합성 데이터` (공백) | 불일치 ❌ | `ROOT`를 반드시 지정 |

**어느 쪽이든 아래 한 줄이면 안전합니다.** 습관적으로 실행하세요:

```bash
cd "$DSET"
export ROOT="$(find . -maxdepth 1 -type d -name '133.*' | head -1)"
echo "ROOT=[$ROOT]"        # 비어 있으면 다운로드 위치부터 재확인
```

> 📌 2026-08 실측 환경(`aihubshell v0.6`, `LANG=C.UTF-8`, Ubuntu 22.04)에서는
> **밑줄 버전**이 생성되어 기본값과 그대로 맞았습니다. 그래도 위 한 줄을 넣어 두면
> 두 경우 모두 커버되므로, 스크립트나 문서를 남길 때는 항상 포함하세요.

새 셸을 열 때마다 다시 설정해야 합니다. 자주 쓴다면:

```bash
cat >> ~/.bashrc <<'EOF'
export REPO=~/aihub-no-pain-71349
export DSET=/data/aihub_71349
export LANG=C.UTF-8 LC_ALL=C.UTF-8
EOF
```

> `AIHUB_APIKEY`는 `.bashrc`에 평문으로 남기지 마세요. 필요할 때만 `export` 하거나 권한 600인 별도 파일에 두고 `source` 하세요.

---

## 8. 검증 → 복구 루프

**"이상 없음"이 나올 때까지 이 루프를 반복**하는 게 이 단계의 목표입니다.

```
check_aihub.sh   →  누락·잔재 있나?  (수 분)
      ↓
verify_zips.sh   →  받은 zip이 온전한가?  (약 30분, 선택이지만 권장)
      ↓
repair_aihub.sh  →  깨진 것·안 받은 것 재다운로드
      ↓
check_aihub.sh   →  수렴 확인 (여기서 "✓ 모든 zip 파일이 정상" 이 나와야 끝)
```

### 8-1. 빠른 진단

```bash
cd "$DSET"
bash "$REPO/verify/check_aihub.sh"
```

filelist와 디스크를 대조해 **누락 zip / `.part` 잔재 / `download.tar` 잔재**를 보고하고,
누락 파일의 filekey CSV까지 출력합니다. 정상 exit 0, 이상 exit 1.

### 8-2. zip 무결성 검증

```bash
PARALLEL=8 bash "$REPO/verify/verify_zips.sh"      # 로컬 NVMe면 16
```

1,412개 CRC 병렬 검사 (NFS + PARALLEL 8 기준 약 30분).
깨진 파일은 filekey와 함께 **화면에 표로** 출력됩니다(별도 파일 기록 없음).

### 8-3. 자동 복구

```bash
DRY_RUN=1 bash "$REPO/verify/repair_aihub.sh"      # 먼저 계획 확인 (필수 습관)
bash "$REPO/verify/repair_aihub.sh"                # 실제 복구
```

`ok / broken / missing / residue_only / never_downloaded` 5가지로 분류하고,
`download.tar`·`.part` 잔재를 정리한 뒤 filekey를 50개씩 묶어 재다운로드합니다.

> ⚠️ **`DRY_RUN=0`이면 깨진 zip과 잔재를 실제로 삭제합니다.** 항상 `DRY_RUN=1`을 먼저 돌리세요.
> ⚠️ 일부러 일부만 받은 상태라면 반드시 `INCLUDE_NEVER_DOWNLOADED=0`을 함께 주세요. ([9장](#9-부분-다운로드-원하는-것만-받기))

### 8-4. 수렴 확인

```bash
bash "$REPO/verify/check_aihub.sh"
# ✓ 모든 zip 파일이 정상적으로 다운로드되었습니다.
```

같은 파일이 2~3회 반복해도 계속 깨진다면 회선/서버 문제일 수 있습니다.
`BATCH=10`으로 낮춰 소량씩 재시도해 보세요.

---

## 9. 부분 다운로드 (원하는 것만 받기)

디스크가 부족하거나 특정 발화 스타일만 필요할 때 씁니다. filelist의 **filekey**를 골라 받습니다.

```bash
# 예: 애니체 Training 원천데이터의 filekey만 추출
sed -e 's/[─├└│]/ /g' filelist_71349.txt \
 | grep -E 'TS_애니체_[0-9]+\.zip' \
 | grep -oE '[0-9]{4,}$' | paste -sd, -
# → 560421,560422,...

aihubshell -mode d -datasetkey 71349 \
  -filekey '560421,560422,...' -aihubapikey "$AIHUB_APIKEY"
```

**라벨(JSON)은 용량이 0.1GB에 불과하니 전량 받아 두는 것을 권장합니다.** 원천 wav만 골라 받으세요.

```bash
# 라벨 전체(TL_*, VL_*) filekey
sed -e 's/[─├└│]/ /g' filelist_71349.txt \
 | grep -E '[TV]L_[^ ]+\.zip' | grep -oE '[0-9]{4,}$' | paste -sd, -
```

> 🚨 **부분 다운로드 상태에서 `repair_aihub.sh`를 기본값으로 돌리면 안 됩니다.**
> 안 받은 파일 전체가 `never_downloaded`로 분류돼 재다운로드 대상이 됩니다. 반드시:
> ```bash
> INCLUDE_NEVER_DOWNLOADED=0 bash "$REPO/verify/repair_aihub.sh"
> ```
> (미다운로드 비율이 50%를 넘으면 스크립트가 경고를 출력합니다.)
>
> `check_aihub.sh`도 "누락 N건"을 보고하는데, 부분 다운로드에서는 **정상**입니다.

---

## 10. 중단·재개

`Ctrl+C`, 네트워크 끊김, 세션 종료 — **처음부터 다시 받을 필요 없습니다.**

| 증상 | 남는 흔적 | 조치 |
|---|---|---|
| 중간에 끊김 | `download.tar` | `repair_aihub.sh`가 자동 삭제 |
| 파일 일부만 받음 | `*.zip.part*` | `repair_aihub.sh`가 정리 후 재다운로드 |
| zip은 있는데 손상 | 크기만 맞는 zip | `verify_zips.sh`가 검출 → `repair_aihub.sh`가 삭제 후 재다운로드 |
| 아예 안 받은 파일 | 없음 | `repair_aihub.sh`가 filekey로 다운로드 |

```bash
cd "$DSET"
export ROOT="$(find . -maxdepth 1 -type d -name '133.*' | head -1)"
bash "$REPO/verify/check_aihub.sh"
DRY_RUN=1 bash "$REPO/verify/repair_aihub.sh"
bash "$REPO/verify/repair_aihub.sh"
```

---

## 11. 완료 체크리스트

```bash
cd "$DSET"

# 1) 개수
find "$ROOT" -name "*.zip" | wc -l            # → 1412

# 2) 용량
du -sh "$ROOT"                                # → 약 220G

# 3) 잔재 없음
find "$ROOT" \( -name "*.part*" -o -name "download.tar" \) | wc -l   # → 0

# 4) 최종 진단
bash "$REPO/verify/check_aihub.sh"            # → ✓ 모든 zip 파일이 정상

# 5) 무결성 (아직 안 돌렸다면)
PARALLEL=8 bash "$REPO/verify/verify_zips.sh" # → ✓ 모든 zip 무결성 통과
```

**4번의 정상 출력은 이렇게 생겼습니다:**

```
📊 개수 비교
  filelist 등록 zip : 1412
  디스크 zip        : 1412
  part 잔재         : 0
  download.tar 잔재 : 0

✓ 모든 zip 파일이 정상적으로 다운로드되었습니다.
```

전부 통과했다면 → **[USAGE.md 3장: 압축 해제](USAGE.md#3-압축-해제)** 로 이동하세요.

압축 해제까지 끝낸 뒤에는 zip 220GB를 지워 용량을 회수할 수 있습니다.
→ **[USAGE.md 3-3: zip 삭제로 용량 회수하기](USAGE.md#3-3-zip-삭제로-용량-회수하기)**
(단, 반드시 전수 검증을 먼저 통과해야 합니다.)

---

## 12. 다운로드 단계 트러블슈팅

### Q1. `setlocale: LC_ALL: cannot change locale (en_US.UTF-8)` 경고

해당 로케일이 설치돼 있지 않습니다. `locale -a`로 확인 후 존재하는 이름(대개 `C.UTF-8`)을 쓰세요. → [4장](#4-로케일-확인-한글-폴더명)

### Q2. `[ERROR] ROOT 없음: ./133.감성_및_발화_...`

`ROOT` 기본값(밑줄)과 실제 폴더명(공백)이 달라서입니다. → [7장](#7-root-잡기)

### Q3. `[ERROR] filelist 없음: filelist_71349.txt`

현재 디렉토리에 filelist가 없습니다. 복사하거나 경로를 명시하세요:

```bash
FILELIST="$REPO/verify/filelist_71349.txt" bash "$REPO/verify/check_aihub.sh"
```

### Q4. `filelist 파싱 0건` 에러

filelist 포맷이 예상과 다릅니다. 진단:

```bash
head -20 filelist_71349.txt
DEBUG=1 bash "$REPO/verify/check_aihub.sh"
```

`aihubshell -mode l` 출력을 리다이렉트할 때 색상 코드나 개행이 섞이면 파싱이 깨질 수 있습니다.
레포에 포함된 `verify/filelist_71349.txt`를 그대로 쓰는 게 가장 안전합니다.

### Q5. `AIHUB_APIKEY를 먼저 설정하세요`

`repair_aihub.sh`는 API Key 없이는 동작하지 않습니다.

```bash
export AIHUB_APIKEY='<your_api_key>'
```

ID/PW로는 동작하지 않습니다. AI Hub 마이페이지에서 Key를 발급하세요.

### Q6. 인증은 되는데 파일이 0바이트거나 HTML이 받아짐

데이터셋 **승인 대기 중**이거나 API Key가 만료된 경우입니다. 마이페이지에서 71349 승인 상태와 Key 유효기간을 확인하세요.

### Q7. 다운로드가 너무 느립니다

AI Hub 서버 측 속도 제한이 있어 회선 대비 느린 게 정상입니다. 새벽 시간대가 빠른 편입니다.
`tmux`로 띄워 두고 기다리세요. 중간에 끊겨도 [10장](#10-중단재개)으로 이어받을 수 있습니다.

### Q8. `No space left on device`

```bash
df -BG "$DSET"; df -i "$DSET"
```

용량 부족이면 [9장 부분 다운로드](#9-부분-다운로드-원하는-것만-받기)를,
inode 부족이면 작은 파일 정리(`__pycache__`, 캐시)를 먼저 하세요.
컨테이너에서는 여러 마운트가 **같은 쿼터를 공유**할 수 있으니, 다른 경로의 사용량도 함께 확인하세요.

### Q9. 같은 파일이 계속 깨져서 받아집니다

```bash
BATCH=10 bash "$REPO/verify/repair_aihub.sh"    # 한 번에 적게 요청
```

그래도 반복되면 시간을 두고 재시도하거나 AI Hub에 문의하세요.

### Q10. 압축 해제 때 `stripped absolute path spec` 경고가 쏟아집니다

**정상입니다.** 이 데이터셋 zip은 내부 경로가 절대경로(`/K-...wav`)라 `unzip`이 경고와 함께 exit 1을 반환하는데,
`extract_zips.sh`가 0과 1을 모두 성공으로 처리합니다. → [USAGE.md FAQ 4](USAGE.md#faq-4-unzip-warning-stripped-absolute-path-spec-가-무수히-출력돼요)

---

## 🔗 다음 단계

| 단계 | 문서 |
|---|---|
| 압축 해제 | [USAGE.md 3장](USAGE.md#3-압축-해제) |
| **zip 삭제로 용량 회수 (220GB)** | [USAGE.md 3-3](USAGE.md#3-3-zip-삭제로-용량-회수하기) |
| 메타데이터 생성 | [USAGE.md 4장](USAGE.md#4-메타데이터-생성) |
| 데이터 탐색 | [USAGE.md 5장](USAGE.md#5-데이터-탐색) |
| CSV 컬럼 레퍼런스 | [USAGE.md 6장](USAGE.md#6-csv-컬럼-레퍼런스) |
