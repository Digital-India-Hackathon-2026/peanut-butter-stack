from __future__ import annotations

from pathlib import Path

import cv2

from fall_detection import FallDetector
from annotate_fall_video import draw_landmarks


def make_label_text(state: str, confidence: float, source: str) -> str:
    return f"{source}: {state} ({confidence:.2f})"


def main() -> None:
    sample_path = Path("fall.mp4")

    live_cap = cv2.VideoCapture(0)
    sample_cap = cv2.VideoCapture(str(sample_path))

    if not live_cap.isOpened():
        raise SystemExit("Could not open live webcam (camera index 0).")
    if not sample_cap.isOpened():
        raise SystemExit(f"Could not open sample video: {sample_path}")

    with FallDetector() as live_detector, FallDetector() as sample_detector:
        cv2.namedWindow("Live Cam", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Fall Sample", cv2.WINDOW_NORMAL)

        frame_index = 0
        while True:
            frame_index += 1
            ret_live, live_frame = live_cap.read()
            ret_sample, sample_frame = sample_cap.read()

            if not ret_live and not ret_sample:
                break

            if ret_live:
                live_result = live_detector.update(live_frame)
                live_overlay = draw_landmarks(
                    live_frame,
                    live_detector._buffer[-1] if live_detector._buffer and live_detector._buffer[-1] is not None else [],
                    live_result["state"],
                    float(live_result.get("confidence", 0.0)),
                    live_result.get("torso_angle"),
                    live_result.get("hip_velocity"),
                    frame_index,
                )
                cv2.putText(
                    live_overlay,
                    make_label_text(live_result["state"], float(live_result.get("confidence", 0.0)), "LIVE"),
                    (16, live_overlay.shape[0] - 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Live Cam", live_overlay)

            if not ret_sample:
                sample_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_sample, sample_frame = sample_cap.read()

            if ret_sample:
                sample_result = sample_detector.update(sample_frame)
                sample_overlay = draw_landmarks(
                    sample_frame,
                    sample_detector._buffer[-1] if sample_detector._buffer and sample_detector._buffer[-1] is not None else [],
                    sample_result["state"],
                    float(sample_result.get("confidence", 0.0)),
                    sample_result.get("torso_angle"),
                    sample_result.get("hip_velocity"),
                    frame_index,
                )
                if sample_result["state"] == "fall_detected":
                    cv2.rectangle(
                        sample_overlay,
                        (0, 0),
                        (sample_overlay.shape[1], sample_overlay.shape[0]),
                        (0, 0, 255),
                        6,
                    )
                cv2.putText(
                    sample_overlay,
                    make_label_text(sample_result["state"], float(sample_result.get("confidence", 0.0)), "SAMPLE"),
                    (16, sample_overlay.shape[0] - 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("Fall Sample", sample_overlay)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC to quit
                break

    live_cap.release()
    sample_cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
