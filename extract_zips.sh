#!/bin/bash
# ============================================================
# extract_zips.sh (v3)
#
# v3 변경점:
#   - unzip exit code 0과 1 모두 성공으로 처리
#     (1 = warning만 있음, 실질적 성공)
#   - AI Hub 데이터셋은 zip 내부 파일이 절대경로(/)로 시작해서
#     unzip이 "stripped absolute path spec" warning을 내며 rc=1 반환.
#     이는 정상 동작이며 압축은 완전히 풀림.
#
# 환경변수:
#   ZIPS_DIR        기본: ./zips
#   DATA_DIR        기본: ./data
#   PARALLEL        기본: 4
#   SKIP_EXISTING   기본: 1
#   DRY_RUN         기본: 0
#   VERBOSE         기본: 0
#   MAX_FAIL_SHOW   기본: 3
# ============================================================
set -u

ZIPS_DIR="${ZIPS_DIR:-./zips}"
DATA_DIR="${DATA_DIR:-./data}"
PARALLEL="${PARALLEL:-4}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"
DRY_RUN="${DRY_RUN:-0}"
VERBOSE="${VERBOSE:-0}"
MAX_FAIL_SHOW="${MAX_FAIL_SHOW:-3}"

for cmd in unzip find xargs; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "[ERROR] missing: $cmd"; exit 1; }
done

if [ ! -d "$ZIPS_DIR" ]; then
  echo "[ERROR] zips 디렉토리 없음: $ZIPS_DIR"
  exit 1
fi

mkdir -p "$DATA_DIR"
ZIPS_DIR=$(cd "$ZIPS_DIR" && pwd)
DATA_DIR=$(cd "$DATA_DIR" && pwd)

echo "============================================"
echo "  zip 압축 해제 (v3)"
echo "============================================"
echo "  ZIPS_DIR      : $ZIPS_DIR"
echo "  DATA_DIR      : $DATA_DIR"
echo "  PARALLEL      : $PARALLEL"
echo "  SKIP_EXISTING : $SKIP_EXISTING"
echo "  DRY_RUN       : $DRY_RUN"
echo "  VERBOSE       : $VERBOSE"
echo

# === 사전 진단 ===
echo "[사전 진단]"
test_file="$DATA_DIR/.write_test_$$"
if touch "$test_file" 2>/dev/null; then
  rm -f "$test_file"
  echo "  ✓ DATA_DIR 쓰기 권한 OK"
else
  echo "  ✗ DATA_DIR 쓰기 실패: $DATA_DIR"
  exit 1
fi
echo "  디스크 공간:"
df -h "$DATA_DIR" 2>/dev/null | tail -1 | awk '{printf "    %s available\n", $4}'
echo "  inode 사용:"
df -i "$DATA_DIR" 2>/dev/null | tail -1 | awk '{printf "    %s used / %s total (%s)\n", $3, $2, $5}'
echo

total=$(find "$ZIPS_DIR" -name "*.zip" 2>/dev/null | wc -l)
echo "압축 해제 대상 zip: $total 개"
if [ "$total" -eq 0 ]; then
  echo "[WARN] zips/에 zip 파일이 없습니다."
  exit 0
fi

# === 프리플라이트 ===
echo
echo "[프리플라이트]"
first_zip=$(find "$ZIPS_DIR" -name "*.zip" 2>/dev/null | head -1)
echo "  test zip: $first_zip"

rel="${first_zip#${ZIPS_DIR}/}"
test_dst="$DATA_DIR/${rel%.zip}"
mkdir -p "$test_dst"

unzip -o "$first_zip" -d "$test_dst" > /tmp/extract_preflight.log 2>&1
pf_rc=$?

if [ "$pf_rc" -eq 0 ] || [ "$pf_rc" -eq 1 ]; then
  extracted_count=$(find "$test_dst" -type f | wc -l)
  if [ "$pf_rc" -eq 1 ]; then
    sample_warn=$(grep -m1 "^warning:" /tmp/extract_preflight.log)
    echo "  ✓ 성공 (rc=1, warning 무시): ${extracted_count}개 파일"
    [ -n "$sample_warn" ] && echo "    참고: $sample_warn"
  else
    echo "  ✓ 성공 (rc=0): ${extracted_count}개 파일"
  fi
  echo "  샘플:"
  find "$test_dst" -type f | head -3 | sed 's/^/    /'
else
  echo "  ✗ 압축 해제 실패 (rc=$pf_rc)"
  cat /tmp/extract_preflight.log | head -20 | sed 's/^/    /'
  exit 1
fi
echo

# === SKIP_EXISTING ===
todo=$(mktemp)
FAIL_LOG_DIR=$(mktemp -d)
trap "rm -rf $FAIL_LOG_DIR /tmp/extract_*.log; rm -f $todo" EXIT

skipped=0
while IFS= read -r zip; do
  rel="${zip#${ZIPS_DIR}/}"
  dst_dir="${DATA_DIR}/${rel%.zip}"
  if [ "$SKIP_EXISTING" = "1" ] && [ -d "$dst_dir" ] && [ -n "$(ls -A "$dst_dir" 2>/dev/null)" ]; then
    skipped=$((skipped+1))
  else
    echo "$zip" >> "$todo"
  fi
done < <(find "$ZIPS_DIR" -name "*.zip" 2>/dev/null)

to_extract=$(wc -l < "$todo")
echo "  - 이미 풀린 것 skip: $skipped"
echo "  - 압축 해제 진행 : $to_extract"
echo

if [ "$to_extract" -eq 0 ]; then
  echo "✓ 모든 zip이 이미 풀려 있습니다."
  exit 0
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "[DRY-RUN] 처음 5개:"
  head -5 "$todo" | while IFS= read -r zip; do
    rel="${zip#${ZIPS_DIR}/}"
    echo "  $zip → $DATA_DIR/${rel%.zip}/"
  done
  [ "$to_extract" -gt 5 ] && echo "  ... 외 $((to_extract-5))개"
  exit 0
fi

# === 본 압축 해제 ===
echo "압축 해제 시작 (병렬 $PARALLEL)..."
echo

export ZIPS_DIR DATA_DIR FAIL_LOG_DIR VERBOSE

start_ts=$(date +%s)

cat "$todo" | xargs -P "$PARALLEL" -I {} bash -c '
  zip="$1"
  rel="${zip#${ZIPS_DIR}/}"
  dst_dir="${DATA_DIR}/${rel%.zip}"
  log_file="${FAIL_LOG_DIR}/$(echo "${rel%.zip}" | tr "/" "_").log"

  mkdir -p "$dst_dir" 2>"$log_file"

  if [ "$VERBOSE" = "1" ]; then
    unzip -o "$zip" -d "$dst_dir"
    rc=$?
  else
    unzip -q -o "$zip" -d "$dst_dir" 2>>"$log_file"
    rc=$?
  fi

  # 핵심: rc=0(정상)과 rc=1(warning만)을 모두 성공으로 처리
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
    echo "  ✓ ${rel%.zip}"
    rm -f "$log_file"
  else
    echo "  ✗ FAILED (rc=$rc): ${rel%.zip}"
  fi
' _ {}

end_ts=$(date +%s)
elapsed=$((end_ts - start_ts))

# === 결과 ===
fail_count=$(ls "$FAIL_LOG_DIR" 2>/dev/null | wc -l)
ok_count=$((to_extract - fail_count))

echo
echo "=== 결과 ==="
echo "  소요 시간 : ${elapsed}초"
echo "  성공     : $ok_count"
echo "  실패     : $fail_count"

if [ "$fail_count" -gt 0 ]; then
  echo
  echo "=== 실패 원인 (첫 $MAX_FAIL_SHOW건) ==="
  ls "$FAIL_LOG_DIR" | head -"$MAX_FAIL_SHOW" | while IFS= read -r logname; do
    echo "--- $logname ---"
    head -10 "$FAIL_LOG_DIR/$logname"
    echo
  done
  trap - EXIT
  echo "[로그 디렉토리 보존됨: $FAIL_LOG_DIR]"
  exit 1
fi

echo
echo "✓ 모든 zip 압축 해제 완료"
echo "다음 단계: python3 build_metadata.py"