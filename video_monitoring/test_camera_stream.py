"""Manual test harness for the VitalGuard camera stream."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
FALL_DETECTION_DIR = ROOT_DIR / "fall detection"

if str(FALL_DETECTION_DIR) not in sys.path:
    sys.path.insert(0, str(FALL_DETECTION_DIR))

from camera_stream import CameraStream, resolve_video_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the VitalGuard camera stream.")
    parser.add_argument(
        "--source",
        default="0",
        help="Webcam device index or video file path (default: 0)",
    )
    args = parser.parse_args()

    source = resolve_video_source(args.source)
    stream = CameraStream(source)
    window_name = "VitalGuard Camera Monitoring"
    last_state_change_id = -1

    try:
        while True:
            snapshot = stream.snapshot()
            frame = snapshot["frame"]
            result = snapshot["result"] or {}

            if frame is None:
                time.sleep(0.02)
                continue

            state_change_id = int(snapshot["state_change_id"])
            if state_change_id != last_state_change_id:
                print(
                    f"[{result.get('timestamp', 'n/a')}] "
                    f"state={result.get('state', 'unknown')} "
                    f"confidence={result.get('confidence', 0.0):.2f} "
                    f"source={snapshot['source']}"
                )
                last_state_change_id = state_change_id

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        stream.close()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
