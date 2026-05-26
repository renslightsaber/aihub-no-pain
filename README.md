# aihub-no-pain-71349

> **AI Hub 「감성 및 발화스타일 동시 고려 음성합성 데이터」(datasetkey=71349)** 를
> 다운로드 → 검증 → 복구 → 압축 해제 → 메타데이터 생성 → 화자 단위 탐색까지
> **한 번에 처리하는 종합 툴킷**입니다.

대용량(1.7TB) 한국어 TTS 데이터셋을 처음 받아 보는 사람도, 중간에 다운로드가 끊겨 골치 아픈 사람도, 시행착오 없이 학습용 메타데이터까지 안전하게 만들 수 있도록 만들어졌습니다.

---

## 📋 데이터셋 소개

| 항목 | 내용 |
|---|---|
| **이름** | 감성 및 발화스타일 동시 고려 음성합성 데이터 |
| **AI Hub datasetkey** | `71349` |
| **공식 페이지** | [AI Hub](https://www.aihub.or.kr) — "감성 및 발화스타일" 검색 |
| **데이터 규모** | 음성 **1,012시간**, 약 **56만 발화**, **89명 화자** |
| **발화 스타일** | 독백체, 대화체, 구연체, 중계체, 친절체, 애니체, 낭독체 (7가지) |
| **감정** | 기쁨, 슬픔, 분노, 무감정 (4가지) |
| **감정 강도** | 약(1) / 중(2) / 강(3) |
| **음성 포맷** | WAV / 44.1kHz / Mono / Peak ≤ -1dB / Noise Floor ≤ -60dB |
| **라벨 포맷** | JSON (대본·발화·스타일 태그·검수 투표 포함) |
| **압축 상태 용량** | 약 1.5TB (zip 1,412개) |
| **압축 해제 후 용량** | 약 1.7TB+ (wav 56만 + JSON 12만) |

자세한 데이터셋 사양은 [`docs/`](docs/) 폴더의 공식 PDF를 참고하세요.

---

## 🎯 이 레포가 해결하는 문제

AI Hub의 대용량 음성 데이터셋은 다음과 같은 함정이 있습니다:

- **다운로드 중단**: `aihubshell`이 종종 일부 파일만 받고 멈춤 (`download.tar`, `.part` 잔여물 발생)
- **무결성 의문**: zip 1,412개가 다 멀쩡한지 일일이 확인 어려움
- **압축 해제 함정**: zip 내부 파일이 절대경로(`/`)로 저장되어 있어 `unzip`이 warning과 함께 exit code 1을 반환 → 정상인데 스크립트가 실패로 오판
- **메타데이터 구조 복잡**: 라벨(JSON)과 원천(wav)이 분리된 폴더(`02.라벨링데이터` vs `01.원천데이터`)에 있어 매핑이 까다로움
- **학습 활용까지 추가 작업**: CSV 만들고, 통계 뽑고, 화자별로 분리하고...

이 툴킷은 **모든 함정을 해결한 검증된 스크립트**와 **한국어 인터랙티브 노트북**을 제공합니다.

---

## 🚀 Quick Start

### 사전 준비

1. AI Hub 가입 후 datasetkey=71349 다운로드 권한 신청·승인
2. [aihubshell 설치](https://www.aihub.or.kr) (공식 사이트 안내 참조)
3. 충분한 디스크 (최소 3.5TB 권장 — zip + 압축해제 + 여유)
4. Linux/macOS (bash 4.0+, Python 3.8+, `unzip`)

### 5분 요약 워크플로우

```bash
# 0) 레포 클론
git clone https://github.com/renslightsaber/aihub-no-pain-71349.git
cd aihub-no-pain-71349

# 1) AI Hub에서 다운로드
mkdir -p ~/aihub_71349 && cd ~/aihub_71349
aihubshell -mode d -datasetkey 71349 -aihubid <your_id> -aihubpw <your_pw>

# 2) 다운로드 검증
bash ~/aihub-no-pain-71349/verify/check_aihub.sh

# 3) (필요 시) 누락 파일 자동 복구
bash ~/aihub-no-pain-71349/verify/repair_aihub.sh

# 4) zip 무결성 검증 (선택, 시간 소요)
bash ~/aihub-no-pain-71349/verify/verify_zips.sh

# 5) zip 정리 → 압축 해제
bash ~/aihub-no-pain-71349/preprocess/move_zips_to_zips_dir.sh
bash ~/aihub-no-pain-71349/preprocess/extract_zips.sh

# 6) 메타데이터 생성
python3 ~/aihub-no-pain-71349/preprocess/build_metadata.py \
  --data-dir ./data \
  --base-dir "$PWD/.." \
  --output-dir ./meta

# 7) 노트북으로 탐색
jupyter notebook ~/aihub-no-pain-71349/notebooks/explore_dataset.ipynb
```

자세한 단계별 설명·옵션·기대 출력·트러블슈팅은 → **[USAGE.md](USAGE.md)**

---

## 📂 디렉토리 구조

```
aihub-no-pain-71349/
├── README.md                    # 이 파일
├── USAGE.md                     # 단계별 상세 가이드
├── LICENSE                      # MIT
│
├── docs/                        # 공식 데이터셋 문서 (AI Hub 제공)
│   ├── 감성및발화스타일동시고려음성합성데이터_구축활용_가이드라인.pdf
│   └── 2-012-133_데이터설명서_감성_및_발화스타일_음성합성_데이터.pdf
│
├── verify/                      # 📥 1단계: 다운로드 검증 + 복구
│   ├── filelist_71349.txt       # AI Hub 공식 파일 리스트 (기준값)
│   ├── check_aihub.sh           # 빠른 진단 — 누락 파일 식별
│   ├── verify_zips.sh           # zip 무결성 검증 (병렬 CRC)
│   └── repair_aihub.sh          # 자동 복구 (5가지 케이스 처리)
│
├── preprocess/                  # ⚙️ 2단계: 압축 해제 + 메타 생성
│   ├── move_zips_to_zips_dir.sh # zip → zips/ 폴더로 이동
│   ├── extract_zips.sh          # 병렬 압축 해제 (절대경로 warning 자동 처리)
│   └── build_metadata.py        # metadata.csv + 통계 txt + 화자별 CSV
│
└── notebooks/                   # 🔍 3단계: 화자 중심 탐색
    └── explore_dataset.ipynb    # ipywidgets 인터랙티브 탐색
```

---

## 🔄 파이프라인 개요

```
       ┌──────────────────┐
       │  AI Hub 다운로드  │ aihubshell
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │   1. 다운로드 검증  │ verify/  check_aihub.sh → verify_zips.sh → repair_aihub.sh
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │  2. 압축 해제      │ preprocess/  move_zips_to_zips_dir.sh → extract_zips.sh
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │  3. 메타데이터 생성 │ preprocess/  build_metadata.py
       │   - metadata.csv  │   → 화자/성별/전체 통계 txt 3종
       │   - 화자별 CSV    │   → metadatas_per_speaker/speaker_XXX.csv
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │   4. 데이터 탐색  │ notebooks/  explore_dataset.ipynb
       │  (화자 ID 입력)   │   → 샘플 청취 + tr/ptr/감정/스타일 표시
       └──────────────────┘
```

---

## ✨ 핵심 기능

### `verify/` — 다운로드 검증·복구
- **`check_aihub.sh`**: filelist 기준 누락 파일·잔여물 식별 (수분 내)
- **`verify_zips.sh`**: 병렬로 모든 zip의 CRC 검증 (NFS 기준 약 30분 / 1,412개)
- **`repair_aihub.sh`**: 5가지 케이스 자동 처리
  - `ok` — 정상
  - `broken` — 깨진 파일 재다운로드
  - `missing` — 누락 파일 다운로드
  - `residue_only` — `.part` 등 잔여물만 있음 (정리 후 재시도)
  - `never_downloaded` — 한 번도 받지 않음
  - + `download.tar` 잔여물 자동 정리

### `preprocess/` — 압축 해제·메타 생성
- **`extract_zips.sh`**: 병렬 압축 해제
  - **절대경로 warning 자동 처리** (AI Hub zip의 내부 절대경로 이슈)
  - 사전 진단 + 프리플라이트 + 실패 로그 보존
- **`build_metadata.py`**: 라벨↔원천 폴더 매핑 자동 추적
  - `audio_path` + `base_dir` 분리 컬럼 (서버 이전 대응)
  - 전체/화자별/성별별 통계 txt 자동 생성
  - 화자별 CSV 분리 저장

### `notebooks/` — 화자 중심 탐색
- 화자 ID 드롭다운 선택 → 정보 카드 + 샘플 청취
- 감정·스타일·강도·텍스트 검색 필터
- tr(철자 전사), ptr(발음 전사) 동시 표시
- ipywidgets 인터랙티브 UI

---

## 💡 활용 예시

이 데이터셋과 툴킷은 다음과 같은 음성 AI 연구·개발에 활용 가능합니다:

- **다화자·다감정 한국어 TTS**: 89명 화자 × 4감정 × 7스타일
- **감정 강도 조절 TTS**: intensity 1~3 라벨 활용
- **Style Transfer TTS**: 발화체 간 스타일 전이
- **Acting TTS·Paraverbal 표현 연구**: 비언어적 표현(웃음·울음·강세)
- **음성합성 평가 (MOS)**: 검증자 투표 5점 척도 (`votes_avg` 컬럼)

---

## 📜 라이선스

### 이 레포의 코드
[MIT License](LICENSE)

### 데이터셋 자체
AI Hub의 「감성 및 발화스타일 동시 고려 음성합성 데이터」는 **AI Hub의 이용 약관**을 따릅니다.
이 레포는 데이터셋 자체를 배포하지 않으며, AI Hub에서 정식으로 다운로드받은 사용자만을 대상으로 합니다.

- 데이터 출처: AI Hub (한국지능정보사회진흥원, NIA)
- 구축 주관: 커뮤니케이션북스(주)
- 구축 협력: ㈜나라지식정보, ㈜셀바스에이아이, ㈜바이칼에이아이

---

## 🤝 기여

이슈와 PR을 환영합니다. 다음과 같은 기여가 특히 유용해요:

- 다른 AI Hub 데이터셋에 대한 동일 구조 포팅
- Windows 환경 호환성 (WSL2 기준 동작 검증 PR)
- 추가 데이터 분석 노트북
- 다국어 번역 (영문 README 등)

---

## 🙏 감사의 글

- 데이터셋 제공: **AI Hub (NIA)** 및 구축 기관들
- 압축 해제·라벨 매핑·통계 분석 로직 정립에 도움을 준 모든 시행착오들

문의: 이슈로 등록해주세요.
