#!/usr/bin/env python3
"""
verify_extraction.py (v1)
============================================================
"zips/ 의 모든 zip이 data/ 로 빠짐없이 풀렸는가"를 검증합니다.

압축 해제가 끝난 뒤 **zip 220GB를 지워 용량을 회수하기 전에** 돌리는
안전장치입니다. zip 하나하나의 중앙 디렉토리를 읽어 내부 엔트리 목록을 얻고,
그 파일들이 data/ 의 대응 폴더에 실제로 존재하는지 대조합니다.

  zips/133.../Training/01.원천데이터/TS_구연체_001.zip
    └─ 내부 엔트리: /K-A1-C-034-0001.wav   (AI Hub zip은 절대경로로 저장됨)
        ↓ 대조
  data/133.../Training/01.원천데이터/TS_구연체_001/K-A1-C-034-0001.wav

extract_zips.sh 의 목적지 규칙(zips 기준 상대경로에서 .zip 을 뗀 폴더)과
동일한 매핑을 사용합니다.

사용 예:
  # 전수 검증 (권장 — zip 삭제 전에는 반드시 이것)
  python3 verify_extraction.py --zips-dir ./zips --data-dir ./data

  # 빠른 표본 검증 (진행 도중 중간 점검용)
  python3 verify_extraction.py --sample 20

종료 코드:
  0 = 전부 정상 (zip 삭제해도 안전)
  1 = 문제 발견 (절대 삭제하지 말 것)
============================================================
"""

import argparse
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def zip_entries(zip_path: Path):
    """zip 내부의 파일 엔트리 목록. 읽기 실패 시 None."""
    # -Z1 은 중앙 디렉토리만 읽으므로 압축을 풀지 않아 빠릅니다.
    r = subprocess.run(["unzip", "-Z1", str(zip_path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    # AI Hub zip은 엔트리가 "/파일명" 형태(절대경로)라 앞의 / 를 떼야
    # unzip 이 실제로 만든 경로와 일치합니다.
    return {e.lstrip("/") for e in r.stdout.splitlines()
            if e and not e.endswith("/")}


def check_one(zip_path: Path, zips_dir: Path, data_dir: Path):
    """(zip, 상태, 엔트리수, 누락수) 반환."""
    entries = zip_entries(zip_path)
    if entries is None:
        return (zip_path, "ZIP_UNREADABLE", 0, 0)

    dest = data_dir / zip_path.relative_to(zips_dir).with_suffix("")
    if not dest.is_dir():
        return (zip_path, "DEST_MISSING", len(entries), len(entries))

    have = {p.name for p in dest.iterdir() if p.is_file()}
    missing = entries - have
    status = "OK" if not missing else "INCOMPLETE"
    return (zip_path, status, len(entries), len(missing))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zips-dir", default="./zips",
                    help="zip 보관 폴더 (기본: ./zips)")
    ap.add_argument("--data-dir", default="./data",
                    help="압축 해제된 폴더 (기본: ./data)")
    ap.add_argument("--parallel", type=int, default=16,
                    help="동시 검사 수 (기본: 16)")
    ap.add_argument("--sample", type=int, default=0,
                    help="접두어(TS/VS/TL/VL)별 표본 개수. 0이면 전수 검증 (기본: 0)")
    ap.add_argument("--seed", type=int, default=42,
                    help="표본 추출 시드 (기본: 42)")
    args = ap.parse_args()

    zips_dir = Path(args.zips_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    for d, label in ((zips_dir, "zips"), (data_dir, "data")):
        if not d.is_dir():
            print(f"[ERROR] {label} 디렉토리 없음: {d}")
            return 1

    zips = sorted(zips_dir.rglob("*.zip"))
    if not zips:
        print(f"[WARN] zip이 없습니다: {zips_dir}")
        print("       이미 삭제했거나 move_zips_to_zips_dir.sh 를 아직 안 돌렸을 수 있습니다.")
        return 1

    targets = zips
    if args.sample > 0:
        random.seed(args.seed)
        groups = {}
        for z in zips:
            groups.setdefault(z.name.split("_")[0], []).append(z)
        targets = []
        for _, v in sorted(groups.items()):
            targets += random.sample(v, min(args.sample, len(v)))

    mode = "전수" if args.sample == 0 else f"표본({args.sample}/접두어)"
    print("=" * 60)
    print("  압축 해제 완전성 검증 (verify_extraction.py)")
    print("=" * 60)
    print(f"  zips_dir : {zips_dir}")
    print(f"  data_dir : {data_dir}")
    print(f"  모드     : {mode}  —  대상 {len(targets):,} / 전체 {len(zips):,} zip")
    print(f"  parallel : {args.parallel}")
    print()
    print("검사 중... (전수 검증은 NFS에서 수 분 걸릴 수 있습니다)")

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        results = list(ex.map(
            lambda z: check_one(z, zips_dir, data_dir), targets))

    bad = [r for r in results if r[1] != "OK"]
    total_entries = sum(r[2] for r in results)

    print()
    print("-" * 60)
    print(f"  검사한 zip       : {len(results):,}")
    print(f"  zip 내부 총 파일 : {total_entries:,}")
    print(f"  문제 있는 zip    : {len(bad):,}")
    print("-" * 60)

    if bad:
        print()
        print("문제 목록 (최대 30개):")
        for z, st, n, m in bad[:30]:
            print(f"  [{st:14s}] {z.name}  (엔트리 {n:,} / 누락 {m:,})")
        if len(bad) > 30:
            print(f"  ... 외 {len(bad) - 30:,}개")
        print()
        print("조치:")
        print("  1) 압축 해제를 다시 돌리세요 (SKIP_EXISTING=1이라 이어서 진행됩니다)")
        print("       PARALLEL=8 bash preprocess/extract_zips.sh")
        print("  2) ZIP_UNREADABLE 이면 zip 자체가 깨진 것입니다")
        print("       bash verify/verify_zips.sh  →  bash verify/repair_aihub.sh")
        print()
        print("🚨 이 상태에서 zip을 삭제하면 해당 데이터를 되돌릴 수 없습니다.")
        return 1

    print()
    print("✅ 모든 zip이 빠짐없이 압축 해제되었습니다.")
    if args.sample > 0:
        print("   ⚠️ 표본 검증입니다. zip을 삭제하려면 --sample 없이 전수 검증하세요.")
    else:
        print("   zip을 삭제해 용량을 회수해도 안전합니다. (USAGE.md 3-3 참고)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
