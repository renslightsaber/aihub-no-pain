#!/bin/bash
# ============================================================
# move_zips_to_zips_dir.sh
# 모든 *.zip 파일을 zips/ 하위로 이동.
# filelist의 경로 구조를 그대로 유지.
#
# 예) 133.../Training/01.원천데이터/TS_구연체_001.zip
#  →  zips/133.../Training/01.원천데이터/TS_구연체_001.zip
#
# 환경변수:
#   ROOT       기본: ./133.감성_및_발화_스타일_동시_고려_음성합성_데이터
#   ZIPS_DIR   기본: ./zips
#   DRY_RUN    기본: 0 (1이면 시뮬레이션만)
#
# 사용법:
#   chmod +x move_zips_to_zips_dir.sh
#   DRY_RUN=1 ./move_zips_to_zips_dir.sh     # 미리보기
#   ./move_zips_to_zips_dir.sh
# ============================================================
set -u

ROOT="${ROOT:-./133.감성_및_발화_스타일_동시_고려_음성합성_데이터}"
ZIPS_DIR="${ZIPS_DIR:-./zips}"
DRY_RUN="${DRY_RUN:-0}"

# === 의존성/입력 검증 ===
if [ ! -d "$ROOT" ]; then
  echo "[ERROR] ROOT 디렉토리 없음: $ROOT"
  exit 1
fi

if [ ! -d "$ZIPS_DIR" ]; then
  echo "[INFO] zips 디렉토리 생성: $ZIPS_DIR"
  [ "$DRY_RUN" = "0" ] && mkdir -p "$ZIPS_DIR"
fi

# ROOT의 부모 디렉토리 (zip 이동 시 ROOT 자체 폴더명도 보존)
# 예: ROOT="./133.감성..." → 이동할 때 zips/133.감성.../... 구조 만듦
ROOT_BASENAME=$(basename "$ROOT")

echo "============================================"
echo "  zip 파일 → zips/ 이동"
echo "============================================"
echo "  ROOT       : $ROOT"
echo "  ZIPS_DIR   : $ZIPS_DIR"
echo "  DRY_RUN    : $DRY_RUN"
echo

# === zip 파일 수집 ===
total=$(find "$ROOT" -name "*.zip" 2>/dev/null | wc -l)
echo "이동할 zip 파일: $total 개"
echo

if [ "$total" -eq 0 ]; then
  echo "[WARN] zip 파일이 없습니다. 이미 옮겼나요?"
  exit 0
fi

# === 이동 실행 ===
moved=0
skipped=0
idx=0

while IFS= read -r zip; do
  idx=$((idx+1))
  # ROOT 기준 상대 경로
  rel="${zip#$ROOT/}"
  # 목적지: zips/<ROOT_BASENAME>/<상대경로>
  dst="$ZIPS_DIR/$ROOT_BASENAME/$rel"
  dst_dir=$(dirname "$dst")
  
  printf "\r  진행: %d/%d" "$idx" "$total"
  
  if [ -f "$dst" ]; then
    skipped=$((skipped+1))
    continue
  fi
  
  if [ "$DRY_RUN" = "1" ]; then
    echo
    echo "  [DRY-RUN] $zip"
    echo "         → $dst"
  else
    mkdir -p "$dst_dir"
    if mv "$zip" "$dst"; then
      moved=$((moved+1))
    else
      echo
      echo "  [ERROR] 이동 실패: $zip"
    fi
  fi
done < <(find "$ROOT" -name "*.zip" 2>/dev/null)

echo
echo
echo "=== 결과 ==="
echo "  이동 완료    : $moved"
echo "  이미 존재 skip : $skipped"
echo "  전체         : $total"

# === ROOT 하위 빈 디렉토리 정리 (DRY_RUN=0일 때만) ===
if [ "$DRY_RUN" = "0" ] && [ "$moved" -gt 0 ]; then
  echo
  echo "→ 원본 폴더의 빈 디렉토리 정리..."
  find "$ROOT" -type d -empty -delete 2>/dev/null
  
  # ROOT 자체도 비었으면 제거
  if [ -d "$ROOT" ] && [ -z "$(ls -A "$ROOT")" ]; then
    rmdir "$ROOT" 2>/dev/null
    echo "  $ROOT 자체도 비어 제거됨"
  fi
fi

echo
echo "Done."
if [ "$DRY_RUN" = "1" ]; then
  echo "DRY-RUN 모드였습니다. 실제 이동: DRY_RUN 없이 재실행."
else
  echo "다음 단계: ./extract_zips.sh 로 압축 해제"
fi
