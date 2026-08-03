#!/bin/bash
# ============================================================
# verify_zips.sh (v2)
# AI Hub 데이터셋의 zip 무결성을 병렬로 검증.
#
# v2 변경점:
#   - filelist 파싱 로직 정규화 (check_aihub.sh v2와 동일)
#   - 디스크 파일명도 정규화 후 매칭
#   - DEBUG=1 모드
#
# 환경변수:
#   DATASET_KEY     기본: 71349
#   FILELIST        기본: filelist_${DATASET_KEY}.txt
#   ROOT            기본: ./133.감성_및_발화_스타일_동시_고려_음성합성_데이터
#   PARALLEL        기본: 8
#   SHOW_DETAILS    기본: 1
#   USE_COLOR       기본: auto
#   DEBUG           기본: 0
# ============================================================
set -u

DATASET_KEY="${DATASET_KEY:-71349}"
FILELIST="${FILELIST:-filelist_${DATASET_KEY}.txt}"
ROOT="${ROOT:-./133.감성_및_발화_스타일_동시_고려_음성합성_데이터}"
PARALLEL="${PARALLEL:-8}"
SHOW_DETAILS="${SHOW_DETAILS:-1}"
USE_COLOR="${USE_COLOR:-auto}"
DEBUG="${DEBUG:-0}"

# 색상
if [ "$USE_COLOR" = "auto" ]; then
  [ -t 1 ] && USE_COLOR=1 || USE_COLOR=0
fi
if [ "$USE_COLOR" = "1" ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
  BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' BLUE='' BOLD='' NC=''
fi

# 의존성
for cmd in awk grep find xargs unzip basename sort sed tr; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "[ERROR] missing: $cmd"; exit 1; }
done
if [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
  echo "[ERROR] bash 4.0+ 필요"; exit 1
fi
[ -f "$FILELIST" ] || { echo "[ERROR] filelist 없음: $FILELIST"; exit 1; }
[ -d "$ROOT" ] || { echo "[ERROR] ROOT 없음: $ROOT"; exit 1; }

normalize_name() {
  echo "$1" | tr -d '[:space:]'
}

parse_filelist_line() {
  local line="$1"
  local clean=$(echo "$line" | sed -e 's/[─├└│|]/ /g' -e 's/\r//g')
  local zip_part=$(echo "$clean" | grep -oE '.*\.zip' | head -1)
  [ -z "$zip_part" ] && return 1
  local name_norm=$(echo "$zip_part" | sed 's/^[[:space:]]*//' | tr -d '[:space:]')
  local key=$(echo "$clean" | grep -oE '[0-9]{4,}' | tail -1)
  local size=$(echo "$clean" | grep -oE '[0-9.]+ ?(KB|MB|GB|TB)' | head -1)
  [ -z "$name_norm" ] || [ -z "$key" ] && return 1
  echo "${name_norm}|${size:-?}|${key}"
}

printf "${BOLD}============================================${NC}\n"
printf "${BOLD}  AI Hub zip 무결성 병렬 검증 (v2)${NC}\n"
printf "${BOLD}============================================${NC}\n"
echo "  DATASET_KEY : $DATASET_KEY"
echo "  ROOT        : $ROOT"
echo "  FILELIST    : $FILELIST"
echo "  PARALLEL    : $PARALLEL"
[ "$DEBUG" = "1" ] && echo "  DEBUG       : ON"
echo

# === filelist 파싱 ===
declare -A filelist_info
filelist_count=0
debug_shown=0

while IFS= read -r line || [ -n "$line" ]; do
  parsed=$(parse_filelist_line "$line") || continue
  IFS='|' read -r name size key <<< "$parsed"
  filelist_info["$name"]="${size}|${key}"
  filelist_count=$((filelist_count+1))
  if [ "$DEBUG" = "1" ] && [ "$debug_shown" -lt 5 ]; then
    printf "${BLUE}[DEBUG] name=[%s] size=[%s] key=[%s]${NC}\n" "$name" "$size" "$key"
    debug_shown=$((debug_shown+1))
  fi
done < "$FILELIST"

if [ "$filelist_count" -eq 0 ]; then
  printf "${RED}[ERROR] filelist 파싱 0건. DEBUG=1 로 재시도하세요.${NC}\n"
  exit 1
fi

[ "$DEBUG" = "1" ] && echo "[DEBUG] filelist 파싱: ${filelist_count}건" && echo

# === 병렬 무결성 검증 ===
total_zip=$(find "$ROOT" -name "*.zip" 2>/dev/null | wc -l)
if [ "$total_zip" -eq 0 ]; then
  printf "${YELLOW}[WARN] zip 파일 없음.${NC}\n"
  exit 1
fi

printf "🔍 검증 시작 (${BOLD}%d개${NC}, 병렬 ${BOLD}%d${NC})\n" "$total_zip" "$PARALLEL"
echo

TMPFILE=$(mktemp); trap "rm -f $TMPFILE" EXIT

start_ts=$(date +%s)
find "$ROOT" -name "*.zip" -print0 \
  | xargs -0 -P "$PARALLEL" -I {} sh -c '
      if ! unzip -tq "$1" >/dev/null 2>&1; then
        basename "$1"
      fi
    ' _ {} > "$TMPFILE"
end_ts=$(date +%s)
elapsed=$((end_ts - start_ts))

broken_count=$(wc -l < "$TMPFILE")
ok_count=$((total_zip - broken_count))

printf "${BOLD}📊 검증 결과${NC} (${elapsed}초)\n"
printf "  정상 : ${GREEN}%d건${NC}\n" "$ok_count"
if [ "$broken_count" -eq 0 ]; then
  printf "  깨짐 : ${GREEN}%d건${NC}\n" "$broken_count"
else
  printf "  깨짐 : ${RED}%d건${NC}\n" "$broken_count"
fi
echo

if [ "$broken_count" -eq 0 ]; then
  printf "${GREEN}${BOLD}✓ 모든 zip 무결성 통과${NC}\n"
  exit 0
fi

printf "${RED}${BOLD}✗ 깨진 zip 발견${NC}\n"

if [ "$SHOW_DETAILS" = "1" ]; then
  echo
  printf "${BOLD}📋 깨진 파일 상세${NC}\n"
  printf -- "─────────────────────────────────────────────────────────────────────\n"
  printf "%-50s %-12s %-10s\n" "파일명(정규화)" "용량" "filekey"
  printf -- "─────────────────────────────────────────────────────────────────────\n"

  TMPSORT=$(mktemp); sort "$TMPFILE" > "$TMPSORT"

  unmatched=()
  filekeys_csv=""
  while IFS= read -r raw_name; do
    norm_name=$(normalize_name "$raw_name")
    info="${filelist_info[$norm_name]:-}"
    if [ -n "$info" ]; then
      size="${info%|*}"; key="${info#*|}"
      printf "%-50s %-12s %-10s\n" "$norm_name" "$size" "$key"
      [ -z "$filekeys_csv" ] && filekeys_csv="$key" || filekeys_csv="${filekeys_csv},${key}"
    else
      unmatched+=("$raw_name")
    fi
  done < "$TMPSORT"
  rm -f "$TMPSORT"

  printf -- "─────────────────────────────────────────────────────────────────────\n"

  if [ "${#unmatched[@]}" -gt 0 ]; then
    echo
    printf "${YELLOW}[WARN] filelist에서 매칭 안 된 깨진 파일:${NC}\n"
    printf '  - %s\n' "${unmatched[@]}"
  fi

  echo
  printf "${BOLD}💡 복구 방법${NC}\n"
  echo "  (A) 자동 복구:    ./repair_aihub.sh"
  echo "  (B) 수동 명령:    aihubshell -mode d -datasetkey $DATASET_KEY \\"
  echo "                                -filekey '$filekeys_csv' \\"
  echo "                                -aihubapikey \"\$AIHUB_APIKEY\""
fi

exit 1
