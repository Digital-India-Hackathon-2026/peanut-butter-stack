from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from fall_detection import FallDetector, _tasks_to_landmarks

LANDMARK_PAIRS = [
    (11, 12),  # shoulders
    (23, 24),  # hips
    (11, 23),  # left side torso
    (12, 24),  # right side torso
    (15, 13),  # left wrist to left elbow
    (16, 14),  # right wrist to right elbow
    (27, 25),  # left ankle to left knee
    (28, 26),  # right ankle to right knee
]

def normalized_to_pixel(landmark, width: int, height: int) -> tuple[int, int]:
    x = int(min(max(landmark.x, 0.0), 1.0) * width)
    y = int(min(max(landmark.y, 0.0), 1.0) * height)
    return x, y


def draw_landmarks(frame: np.ndarray, landmarks: list, state: str, confidence: float, torso_angle: float | None, hip_velocity: float | None, frame_index: int) -> np.ndarray:
    h, w = frame.shape[:2]
    annotated = frame.copy()
    for idx, lm in enumerate(landmarks):
        if lm.visibility < 0.5:
            continue
        x, y = normalized_to_pixel(lm, w, h)
        cv2.circle(annotated, (x, y), 4, (255, 255, 0), -1)
        if idx in {11, 12, 23, 24, 15, 16, 27, 28}:
            cv2.putText(annotated, str(idx), (x + 3, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1, cv2.LINE_AA)
    for a, b in LANDMARK_PAIRS:
        if a < len(landmarks) and b < len(landmarks):
            la = landmarks[a]
            lb = landmarks[b]
            if la.visibility >= 0.5 and lb.visibility >= 0.5:
                pa = normalized_to_pixel(la, w, h)
                pb = normalized_to_pixel(lb, w, h)
                cv2.line(annotated, pa, pb, (144, 238, 144), 2)

    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, 0), (w, 90), (15, 23, 43), -1)
    cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, annotated)

    label = f"State: {state}  Confidence: {confidence:.2f}"
    cv2.putText(annotated, label, (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    if torso_angle is not None:
        cv2.putText(annotated, f"Torso angle: {torso_angle:.1f}°", (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1, cv2.LINE_AA)
    if hip_velocity is not None:
        cv2.putText(annotated, f"Hip vel: {hip_velocity:.5f}", (16, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1, cv2.LINE_AA)
    cv2.putText(annotated, f"Frame: {frame_index}", (w - 170, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 210, 0), 1, cv2.LINE_AA)
    return annotated


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate a fall video with detection overlays.")
    parser.add_argument("--video", required=True, help="Path to the input video file")
    parser.add_argument("--output", default="annotated_fall.mp4", help="Path to the annotated output video")
    parser.add_argument("--sample-frame", default="annotated_fall_sample.png", help="Path to save a sample annotated frame")
    args = parser.parse_args()

    video_path = Path(args.video)
    output_path = Path(args.output)
    sample_frame_path = Path(args.sample_frame)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    detector = FallDetector()
    frame_index = 0
    saved_sample = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_index += 1
        result = detector.update(frame)

        if detector._buffer and detector._buffer[-1] is not None:
            landmarks = detector._buffer[-1]
        else:
            landmarks = []

        annotated = draw_landmarks(
            frame,
            landmarks,
            result["state"],
            float(result.get("confidence", 0.0)),
            result.get("torso_angle"),
            result.get("hip_velocity"),
            frame_index,
        )

        writer.write(annotated)
        if not saved_sample and frame_index == 40:
            cv2.imwrite(str(sample_frame_path), annotated)
            saved_sample = True

    detector.close()
    cap.release()
    writer.release()
    print(f"Annotated video written to: {output_path}")
    print(f"Sample frame written to: {sample_frame_path}")


if __name__ == "__main__":
    main()
