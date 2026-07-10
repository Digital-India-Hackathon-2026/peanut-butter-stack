"""
test_fall_detection.py
======================
VitalGuard — Batch Test Script

Runs the fall_detection module against a folder of labeled video clips
and prints / saves a per-clip classification summary.

Usage
-----
    python test_fall_detection.py --video-dir ./clips
    python test_fall_detection.py --video-dir ./clips --fps 30 --output results.csv
    python test_fall_detection.py --video-dir ./clips --verbose

Clip labelling convention (optional)
--------------------------------------
If your filename contains a label keyword, the script will print a
"Expected vs Detected" comparison:
    - filenames containing "fall"      → expected state: fall_detected
    - filenames containing "exit"      → expected state: bed_exit_normal
    - filenames containing "normal"    → expected state: in_bed_normal
    - anything else                    → expected state: unknown
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import cv2

# Ensure the parent directory is on the path when running as a standalone script
sys.path.insert(0, str(Path(__file__).parent))

from fall_detection import FallDetector

# ---------------------------------------------------------------------------
# Supported video extensions
# ---------------------------------------------------------------------------
VIDEO_EXTENSIONS: set[str] = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".m4v"}

# ---------------------------------------------------------------------------
# Label inference from filename
# ---------------------------------------------------------------------------

def infer_label(filename: str) -> str:
    """Infer the expected state from the clip filename (lowercase match)."""
    name = filename.lower()
    if "fall" in name:
        return "fall_detected"
    if "exit" in name or "bed_exit" in name:
        return "bed_exit_normal"
    if "normal" in name or "inbed" in name or "in_bed" in name:
        return "in_bed_normal"
    return "unknown"


# ---------------------------------------------------------------------------
# Per-clip analysis
# ---------------------------------------------------------------------------

def analyse_clip(
    video_path: Path,
    fps_override: float | None = None,
    verbose: bool = False,
) -> dict:
    """
    Feed every frame of a video clip through FallDetector and collect stats.

    Parameters
    ----------
    video_path : Path
        Absolute or relative path to the video file.
    fps_override : float | None
        If set, used instead of the FPS reported by the video container.
    verbose : bool
        If True, print per-frame state to stdout.

    Returns
    -------
    dict
        Per-clip summary including dominant state, frame counts, and timing.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {
            "file": video_path.name,
            "error": "Could not open video file",
            "dominant_state": "error",
        }

    reported_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fps = fps_override if fps_override else reported_fps
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Create a fresh detector per clip so buffers don't bleed between clips
    detector = FallDetector()

    state_counts: dict[str, int] = {
        "in_bed_normal": 0,
        "bed_exit_normal": 0,
        "fall_detected": 0,
    }
    agitation_frames: int = 0
    no_landmark_frames: int = 0
    per_frame_log: list[dict] = []

    start_time = time.perf_counter()
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        result = detector.update(frame)
        frame_index += 1

        state = result.get("state", "in_bed_normal")
        state_counts[state] = state_counts.get(state, 0) + 1

        if result.get("agitation", {}).get("agitation_detected"):
            agitation_frames += 1

        if not result.get("landmarks_detected"):
            no_landmark_frames += 1

        if verbose:
            print(
                f"  [{frame_index:05d}] state={state:<18} "
                f"conf={result.get('confidence', 0):.2f}  "
                f"angle={result.get('torso_angle') or '—':>6}°  "
                f"vel={result.get('hip_velocity') or '—':>8}"
            )

        per_frame_log.append({
            "frame": frame_index,
            "state": state,
            "confidence": result.get("confidence"),
            "torso_angle": result.get("torso_angle"),
            "hip_velocity": result.get("hip_velocity"),
            "agitation": result.get("agitation", {}).get("agitation_detected", False),
            "landmarks_detected": result.get("landmarks_detected"),
            "timestamp": result.get("timestamp"),
        })

    cap.release()
    detector.close()

    elapsed = time.perf_counter() - start_time

    # Dominant state = the state with the most frames
    dominant_state = max(state_counts, key=lambda k: state_counts[k])

    return {
        "file": video_path.name,
        "total_frames": frame_index,
        "fps_used": fps,
        "dominant_state": dominant_state,
        "fall_detected_frames": state_counts.get("fall_detected", 0),
        "bed_exit_frames": state_counts.get("bed_exit_normal", 0),
        "in_bed_frames": state_counts.get("in_bed_normal", 0),
        "agitation_frames": agitation_frames,
        "no_landmark_frames": no_landmark_frames,
        "elapsed_seconds": round(elapsed, 2),
        "expected_state": infer_label(video_path.name),
        "per_frame_log": per_frame_log,
    }


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

_STATE_SYMBOL = {
    "fall_detected":  "🔴 FALL",
    "bed_exit_normal": "🟡 EXIT",
    "in_bed_normal":  "🟢 NORM",
    "error":          "⚪ ERR ",
}

_MATCH_SYMBOL = {True: "✅", False: "❌", None: "—"}


def print_summary_table(summaries: list[dict]) -> None:
    """Pretty-print a table of per-clip results to stdout."""
    col_widths = [40, 10, 10, 10, 10, 10, 10, 8]
    headers = [
        "File", "Expected", "Detected", "Falls", "Exits", "Agit.", "NoLM", "Match"
    ]

    def row(cells: list[str]) -> str:
        return "  ".join(str(c).ljust(w) for c, w in zip(cells, col_widths))

    separator = "─" * (sum(col_widths) + len(col_widths) * 2)
    print()
    print("  VitalGuard — Clip Analysis Results")
    print(f"  {separator}")
    print(row(headers))
    print(f"  {separator}")

    correct = 0
    tested = 0

    for s in summaries:
        expected = s.get("expected_state", "unknown")
        detected = s.get("dominant_state", "error")
        match: bool | None = None
        if expected != "unknown":
            match = expected == detected
            tested += 1
            if match:
                correct += 1

        print(row([
            s["file"][:38],
            expected[:10],
            _STATE_SYMBOL.get(detected, detected)[:10],
            s.get("fall_detected_frames", "—"),
            s.get("bed_exit_frames", "—"),
            s.get("agitation_frames", "—"),
            s.get("no_landmark_frames", "—"),
            _MATCH_SYMBOL[match],
        ]))

    print(f"  {separator}")
    if tested > 0:
        acc = correct / tested * 100
        print(f"\n  Accuracy on labeled clips: {correct}/{tested} ({acc:.1f}%)\n")
    else:
        print("\n  (No labeled clips — rename files with 'fall', 'exit', or 'normal' for accuracy tracking)\n")


def save_csv(summaries: list[dict], output_path: Path) -> None:
    """Save per-clip summary (without per-frame log) to a CSV file."""
    if not summaries:
        return

    keys = [k for k in summaries[0].keys() if k != "per_frame_log"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for s in summaries:
            row = {k: v for k, v in s.items() if k != "per_frame_log"}
            writer.writerow(row)

    print(f"  Results saved to: {output_path}")


def save_frame_log_csv(summaries: list[dict], output_dir: Path) -> None:
    """Save a detailed per-frame CSV for each clip."""
    for s in summaries:
        log = s.get("per_frame_log", [])
        if not log:
            continue
        stem = Path(s["file"]).stem
        out_path = output_dir / f"{stem}_frames.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=log[0].keys())
            writer.writeheader()
            writer.writerows(log)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VitalGuard — batch fall detection test against video clips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--video-dir",
        required=True,
        metavar="DIR",
        help="Path to the folder containing test video clips.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        metavar="N",
        help="Override the video FPS (use when container FPS metadata is wrong).",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Optional path to save per-clip summary as a CSV file.",
    )
    parser.add_argument(
        "--save-frame-logs",
        action="store_true",
        help="Also save per-frame CSV logs alongside --output.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-frame state to stdout (slow for long clips).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    video_dir = Path(args.video_dir).resolve()
    if not video_dir.is_dir():
        print(f"ERROR: '{video_dir}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    # Collect all video files recursively
    video_files = sorted(
        p for p in video_dir.rglob("*")
        if p.suffix.lower() in VIDEO_EXTENSIONS
    )

    if not video_files:
        print(f"No video files found in '{video_dir}'.", file=sys.stderr)
        sys.exit(1)

    print(f"\n  Found {len(video_files)} video clip(s) in {video_dir}\n")

    summaries: list[dict] = []

    for i, vpath in enumerate(video_files, 1):
        print(f"  [{i}/{len(video_files)}] Processing: {vpath.name} ...", end="", flush=True)
        summary = analyse_clip(vpath, fps_override=args.fps, verbose=args.verbose)
        summaries.append(summary)

        if "error" in summary:
            print(f"  ERROR: {summary['error']}")
        else:
            print(
                f"  done ({summary['total_frames']} frames, "
                f"{summary['elapsed_seconds']}s) → {summary['dominant_state']}"
            )

    print_summary_table(summaries)

    if args.output:
        out_path = Path(args.output).resolve()
        save_csv(summaries, out_path)

        if args.save_frame_logs:
            save_frame_log_csv(summaries, out_path.parent)


if __name__ == "__main__":
    main()
