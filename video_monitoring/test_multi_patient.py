"""Test harness for multi-patient videos using three FallDetector instances.

This script does NOT modify `fall_detection.py`. It creates three
independent `FallDetector` instances and runs them on three ROIs per frame.

Usage:
    python video_monitoring/test_multi_patient.py --source "fall detection/fall.mp4"
    python video_monitoring/test_multi_patient.py --source 0

Options:
    --source : webcam index or video file path (default: 0)
    --rois   : optional custom ROIs as semicolon-separated x,y,w,h triples
               e.g. "0,0,320,480;320,0,320,480;640,0,320,480"
               If omitted, the frame is split into three vertical slices.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
FALL_DETECTION_DIR = ROOT_DIR / "fall detection"

if str(FALL_DETECTION_DIR) not in sys.path:
    sys.path.insert(0, str(FALL_DETECTION_DIR))

from fall_detection import FallDetector


def parse_rois(arg: str) -> List[Tuple[int, int, int, int]]:
    rois: List[Tuple[int, int, int, int]] = []
    parts = [p.strip() for p in arg.split(";") if p.strip()]
    for part in parts:
        nums = [int(x) for x in part.split(",")]
        if len(nums) != 4:
            raise ValueError("Each ROI must be x,y,w,h")
        rois.append((nums[0], nums[1], nums[2], nums[3]))
    return rois


def make_default_rois(frame_w: int, frame_h: int) -> List[Tuple[int, int, int, int]]:
    # Split into 3 vertical slices
    w = frame_w // 3
    rois = []
    for i in range(3):
        x = i * w
        # For the last slice, include remaining width
        width = w if i < 2 else frame_w - x
        rois.append((x, 0, width, frame_h))
    return rois


def draw_roi_boxes(frame: np.ndarray, rois: List[Tuple[int, int, int, int]], labels: List[str]) -> None:
    colors = [(0, 200, 0), (0, 180, 220), (0, 120, 255)]
    for i, (x, y, w, h) in enumerate(rois):
        cv2.rectangle(frame, (x, y), (x + w, y + h), colors[i % len(colors)], 2)
        cv2.putText(frame, labels[i], (x + 8, y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colors[i % len(colors)], 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-patient fall detection test")
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument(
        "--rois",
        default=None,
        help="Optional semicolon-separated list of x,y,w,h triples for ROIs",
    )
    args = parser.parse_args()

    source = args.source
    # allow numeric string
    if str(source).lstrip("-").isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Could not open source: {source}")
        return 1

    ret, frame = cap.read()
    if not ret:
        print("Could not read initial frame")
        cap.release()
        return 1

    frame_h, frame_w = frame.shape[:2]

    if args.rois:
        rois = parse_rois(args.rois)
    else:
        rois = make_default_rois(frame_w, frame_h)

    # Create one detector per ROI
    detectors = [FallDetector() for _ in rois]

    window = "VitalGuard — Multi-patient Test"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    try:
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                # loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                time.sleep(0.1)
                continue

            labels = []
            for i, (x, y, w, h) in enumerate(rois):
                crop = frame[y : y + h, x : x + w]
                result = detectors[i].update(crop)
                state = result.get("state", "unknown")
                conf = result.get("confidence", 0.0)
                labels.append(f"Bed{i+1}: {state} ({conf:.2f})")

            # Draw ROI boxes and labels on frame
            draw_roi_boxes(frame, rois, labels)

            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

            frame_idx += 1
    finally:
        for d in detectors:
            try:
                d.close()
            except Exception:
                pass
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
