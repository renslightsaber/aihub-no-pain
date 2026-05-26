#!/usr/bin/env python3
"""
build_metadata.py (v3)
============================================================
v3 변경점:
  - audio_path + base_dir 컬럼 분리 (서버 이전 시 base_dir만 갈아끼우면 됨)
  - 출력물 4종:
      1) metadata.csv
      2) stats_overall.txt        — 전체 통계
      3) stats_per_speaker.txt    — 화자별 통계
      4) stats_per_gender.txt     — 성별별 통계
      5) metadatas_per_speaker/   — 화자별 CSV 분리 저장
  - 모두 --output-dir 한 곳에 모임

컬럼 변화:
  v2:  audio_relpath (data_dir 기준)
  v3:  audio_relpath (data_dir 기준, 호환성 유지)
       + base_dir    (공통 base 절대 경로)
       + audio_path  (base_dir 기준 상대 경로) ★

사용 예:
  python3 build_metadata.py \\
    --data-dir ./data \\
    --base-dir /AN202_data12t/tts_datasets/aihub/ \\
    --output-dir ./meta
============================================================
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Optional
import pandas as pd


_src_parent_cache: Dict[Path, Optional[Path]] = {}
_wav_index: Dict[str, Path] = {}


# ============================================================
# 경로 매핑 (v2와 동일)
# ============================================================
def find_src_parent(label_parent: Path) -> Optional[Path]:
    if label_parent in _src_parent_cache:
        return _src_parent_cache[label_parent]
    result = None
    try:
        for sibling in label_parent.parent.iterdir():
            if sibling.is_dir() and ('원천' in sibling.name or 'source' in sibling.name.lower()):
                result = sibling
                break
    except OSError:
        pass
    _src_parent_cache[label_parent] = result
    return result


def find_audio_relpath(json_path: Path, wav_filename: str, data_dir: Path,
                       use_index: bool = False) -> str:
    if not wav_filename:
        return ""
    if use_index:
        wav_path = _wav_index.get(wav_filename)
        if wav_path:
            try:
                return str(wav_path.relative_to(data_dir))
            except ValueError:
                pass

    label_dir = json_path.parent
    label_dir_name = label_dir.name
    if label_dir_name.startswith('TL_'):
        src_dir_name = 'TS_' + label_dir_name[3:]
    elif label_dir_name.startswith('VL_'):
        src_dir_name = 'VS_' + label_dir_name[3:]
    else:
        return ""

    src_parent = find_src_parent(label_dir.parent)
    if src_parent is None:
        return ""

    candidate = src_parent / src_dir_name / wav_filename
    if candidate.exists():
        try:
            return str(candidate.relative_to(data_dir))
        except ValueError:
            return str(candidate)
    return ""


# ============================================================
# JSON → row
# ============================================================
def parse_label_json(json_path: Path, data_dir: Path, base_dir: Path,
                     use_index: bool = False):
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] JSON 파싱 실패: {json_path}: {e}")
        return []

    rows = []
    records = data if isinstance(data, list) else [data]
    for rec in records:
        reciter = rec.get("reciter") or {}
        script = rec.get("script") or {}
        studio = rec.get("studio") or {}
        voice = rec.get("voice") or {}

        rel = json_path.relative_to(data_dir)
        parts = rel.parts
        split = "train" if any("Training" in p for p in parts) else \
                ("valid" if any("Validation" in p for p in parts) else "unknown")
        zip_basename = parts[-2] if len(parts) >= 2 else ""

        for sent in rec.get("sentences", []):
            style = sent.get("style") or {}
            vp = sent.get("voice_piece") or {}
            votes = sent.get("votes") or []

            duration = vp.get("duration")
            file_duration = vp.get("file_duration")
            duration_valid = (
                duration is not None and file_duration is not None
                and duration <= file_duration + 1e-3
            )
            duration_effective = max(duration, file_duration) \
                if (duration is not None and file_duration is not None) else None

            wav_filename = vp.get("filename", "")
            audio_relpath = find_audio_relpath(json_path, wav_filename, data_dir, use_index=use_index)

            # audio_path: base_dir 기준 상대 경로
            audio_path = ""
            if audio_relpath:
                abs_path = (data_dir / audio_relpath).resolve()
                try:
                    audio_path = str(abs_path.relative_to(base_dir))
                except ValueError:
                    # base_dir이 abs_path의 prefix가 아니면 절대 경로 그대로
                    audio_path = str(abs_path)

            scales = [v.get("likert_scale") for v in votes
                      if isinstance(v.get("likert_scale"), (int, float))]
            votes_avg = sum(scales) / len(scales) if scales else None

            rows.append({
                "file_id": sent.get("id"),
                "script_id": script.get("id"),
                "part_no": script.get("part_no"),
                "reciter_id": reciter.get("id"),
                "reciter_age": reciter.get("age"),
                "reciter_gender": reciter.get("gender"),
                "style": style.get("style"),
                "sub_style": style.get("sub_style"),
                "emotion": style.get("emotion"),
                "intensity": style.get("intensity"),
                "duration": duration,
                "file_duration": file_duration,
                "duration_valid": duration_valid,
                "duration_effective": duration_effective,
                "text_origin": sent.get("origin_text"),
                "text_tr": vp.get("tr"),
                "text_ptr": vp.get("ptr"),
                "wav_filename": wav_filename,
                "base_dir": str(base_dir),         # ★ 공통 base
                "audio_path": audio_path,           # ★ base_dir 기준 상대 경로
                "audio_relpath": audio_relpath,     # data_dir 기준 (호환성)
                "audio_exists": bool(audio_relpath),
                "label_relpath": str(rel),
                "votes_avg": votes_avg,
                "votes_count": len(votes),
                "src_type": rec.get("src_type"),
                "studio_id": studio.get("id"),
                "studio_name": studio.get("name"),
                "sample_rate": voice.get("sample_rate"),
                "recorded_at": voice.get("recorded_at"),
                "split": split,
                "zip_basename": zip_basename,
            })
    return rows


# ============================================================
# 통계 txt 생성
# ============================================================
def fmt_sec(total_sec: float) -> str:
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def write_stats_overall(df: pd.DataFrame, output_path: Path):
    lines = []
    lines.append("=" * 60)
    lines.append("  전체 오디오 통계")
    lines.append("=" * 60)
    lines.append(f"총 row 수    : {len(df):,}")
    lines.append(f"고유 화자    : {df['reciter_id'].nunique()}명")
    lines.append(f"고유 스크립트: {df['script_id'].nunique()}개")
    total_sec = df['duration'].dropna().sum()
    lines.append(f"총 duration : {fmt_sec(total_sec)} ({total_sec/3600:.1f}시간)")

    lines.append("\n--- split 분포 ---")
    lines.append(df["split"].value_counts().to_string())

    lines.append("\n--- 성별 분포 (발화 수) ---")
    lines.append(df["reciter_gender"].value_counts().to_string())

    lines.append("\n--- 연령 분포 ---")
    lines.append(df["reciter_age"].value_counts().sort_index().to_string())

    lines.append("\n--- 발화 스타일 분포 ---")
    lines.append(df["style"].value_counts().to_string())

    lines.append("\n--- 감정 분포 ---")
    lines.append(df["emotion"].value_counts().to_string())

    lines.append("\n--- 감정 강도 분포 ---")
    lines.append(df["intensity"].value_counts().sort_index().to_string())

    lines.append("\n--- duration 통계 (초) ---")
    lines.append(df["duration"].describe().to_string())

    lines.append("\n--- 이상치 ---")
    invalid = (~df["duration_valid"]).sum()
    lines.append(f"  duration > file_duration : {invalid:,}건 ({invalid/len(df)*100:.2f}%)")
    audio_missing = (~df["audio_exists"]).sum()
    lines.append(f"  audio 파일 누락          : {audio_missing:,}건 ({audio_missing/len(df)*100:.2f}%)")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stats_per_speaker(df: pd.DataFrame, output_path: Path):
    lines = []
    lines.append("=" * 60)
    lines.append("  화자별 오디오 통계")
    lines.append("=" * 60)

    speakers = sorted([sp for sp in df["reciter_id"].dropna().unique()])
    lines.append(f"총 화자 수: {len(speakers)}명\n")

    # 요약표
    summary = []
    for sp in speakers:
        sub = df[df["reciter_id"] == sp]
        info = sub.iloc[0]
        total_sec = sub["duration"].dropna().sum()
        summary.append({
            "speaker": int(sp) if pd.notna(sp) else sp,
            "gender": info["reciter_gender"],
            "age": int(info["reciter_age"]) if pd.notna(info["reciter_age"]) else "",
            "samples": len(sub),
            "duration(min)": f"{total_sec/60:.1f}",
            "avg(s)": f"{sub['duration'].mean():.2f}",
            "styles": sub["style"].nunique(),
            "emotions": sub["emotion"].nunique(),
        })
    summary_df = pd.DataFrame(summary)
    lines.append("--- 요약 ---")
    lines.append(summary_df.to_string(index=False))

    lines.append("\n\n--- 화자별 상세 ---")
    for sp in speakers:
        sub = df[df["reciter_id"] == sp]
        info = sub.iloc[0]
        sp_disp = int(sp) if pd.notna(sp) else sp
        total_sec = sub["duration"].dropna().sum()
        lines.append(f"\n[화자 {sp_disp}] {info['reciter_gender']}, {info['reciter_age']}세")
        lines.append(f"  발화 수    : {len(sub):,}")
        lines.append(f"  총 duration: {fmt_sec(total_sec)} ({total_sec/60:.1f}분)")
        lines.append(f"  평균 길이  : {sub['duration'].mean():.2f}s")
        lines.append(f"  스타일 분포:")
        for k, v in sub["style"].value_counts().items():
            lines.append(f"    {k}: {v:,}")
        lines.append(f"  감정 분포  :")
        for k, v in sub["emotion"].value_counts().items():
            lines.append(f"    {k}: {v:,}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stats_per_gender(df: pd.DataFrame, output_path: Path):
    lines = []
    lines.append("=" * 60)
    lines.append("  성별별 오디오 통계")
    lines.append("=" * 60)

    for gender in sorted(df["reciter_gender"].dropna().unique()):
        sub = df[df["reciter_gender"] == gender]
        total_sec = sub["duration"].dropna().sum()
        lines.append(f"\n[{gender}]")
        lines.append(f"  화자 수    : {sub['reciter_id'].nunique()}명")
        lines.append(f"  발화 수    : {len(sub):,}건")
        lines.append(f"  총 duration: {fmt_sec(total_sec)} ({total_sec/3600:.1f}시간)")
        lines.append(f"  평균 길이  : {sub['duration'].mean():.2f}s")
        lines.append(f"  중앙값     : {sub['duration'].median():.2f}s")

        lines.append(f"  연령 분포  :")
        for k, v in sub["reciter_age"].value_counts().sort_index().items():
            lines.append(f"    {int(k) if pd.notna(k) else 'N/A'}세: {v:,}")

        lines.append(f"  스타일 분포:")
        for k, v in sub["style"].value_counts().items():
            lines.append(f"    {k}: {v:,}")

        lines.append(f"  감정 분포  :")
        for k, v in sub["emotion"].value_counts().items():
            lines.append(f"    {k}: {v:,}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def split_per_speaker(df: pd.DataFrame, output_dir: Path) -> int:
    """화자별 CSV 분리. speaker_009.csv 형태."""
    output_dir.mkdir(parents=True, exist_ok=True)
    speakers = sorted([sp for sp in df["reciter_id"].dropna().unique()])
    for sp in speakers:
        sub = df[df["reciter_id"] == sp]
        try:
            sp_int = int(sp)
            fname = f"speaker_{sp_int:03d}.csv"
        except (ValueError, TypeError):
            fname = f"speaker_{sp}.csv"
        sub.to_csv(output_dir / fname, index=False, encoding="utf-8")
    return len(speakers)


def build_wav_index(data_dir: Path):
    print("wav 파일 인덱스 생성 중...")
    count = 0
    for wav in data_dir.rglob('*.wav'):
        _wav_index[wav.name] = wav
        count += 1
        if count % 10000 == 0:
            print(f"  진행: {count}개", end="\r")
    print(f"  → {count:,}개 wav 인덱싱 완료")


# ============================================================
# main
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="./data",
                    help="압축 해제된 데이터 폴더 (기본: ./data)")
    ap.add_argument("--base-dir", default=None,
                    help="audio_path 기준이 될 base 디렉토리 (예: /AN202_data12t/tts_datasets/aihub/). "
                         "미지정 시 data-dir의 부모의 부모로 자동 설정")
    ap.add_argument("--output-dir", default="./meta",
                    help="모든 출력물의 저장 디렉토리 (기본: ./meta)")
    ap.add_argument("--label-pattern", default="**/T[LV]_*/*.json")
    ap.add_argument("--use-index", action="store_true",
                    help="wav 파일 인덱스 미리 생성 (NFS stat 비용 절약)")
    args = ap.parse_args()

    data_dir = Path(args.data_dir).resolve()
    if not data_dir.exists():
        print(f"[ERROR] data 디렉토리 없음: {data_dir}")
        return 1

    if args.base_dir:
        base_dir = Path(args.base_dir).resolve()
    else:
        base_dir = data_dir.parent.parent
        print(f"[INFO] --base-dir 미지정. 자동 추정: {base_dir}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"data_dir   : {data_dir}")
    print(f"base_dir   : {base_dir}")
    print(f"output_dir : {output_dir}")
    print()

    if args.use_index:
        build_wav_index(data_dir)

    print("JSON 라벨 파일 검색 중...")
    json_files = sorted(data_dir.glob(args.label_pattern))
    print(f"  → {len(json_files):,}개 JSON 발견")
    if not json_files:
        print("[ERROR] JSON 라벨이 없습니다.")
        return 1

    all_rows = []
    for i, jp in enumerate(json_files, 1):
        if i % 100 == 0 or i == len(json_files):
            print(f"  진행: {i}/{len(json_files)}", end="\r")
        try:
            all_rows.extend(parse_label_json(jp, data_dir, base_dir, use_index=args.use_index))
        except Exception as e:
            print(f"\n[WARN] {jp}: {e}")
    print()
    print(f"  파싱 완료: {len(all_rows):,}개 row")

    df = pd.DataFrame(all_rows)

    # === 출력물 생성 ===
    print()
    meta_path = output_dir / "metadata.csv"
    df.to_csv(meta_path, index=False, encoding="utf-8")
    print(f"[1/4] metadata.csv      : {meta_path}")

    write_stats_overall(df, output_dir / "stats_overall.txt")
    print(f"[2/4] stats_overall     : {output_dir / 'stats_overall.txt'}")

    write_stats_per_speaker(df, output_dir / "stats_per_speaker.txt")
    print(f"[3/4] stats_per_speaker : {output_dir / 'stats_per_speaker.txt'}")

    write_stats_per_gender(df, output_dir / "stats_per_gender.txt")
    print(f"      stats_per_gender  : {output_dir / 'stats_per_gender.txt'}")

    per_speaker_dir = output_dir / "metadatas_per_speaker"
    speaker_count = split_per_speaker(df, per_speaker_dir)
    print(f"[4/4] 화자별 CSV        : {per_speaker_dir}/ ({speaker_count}개)")

    # 콘솔 요약
    print()
    print("=" * 50)
    print(f"총 row 수    : {len(df):,}")
    print(f"고유 화자    : {df['reciter_id'].nunique()}명")
    print(f"split 분포   :", dict(df['split'].value_counts()))
    print(f"성별 분포    :", dict(df['reciter_gender'].value_counts()))
    audio_missing = (~df["audio_exists"]).sum()
    print(f"audio 누락   : {audio_missing:,}건 ({audio_missing/len(df)*100:.2f}%)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())