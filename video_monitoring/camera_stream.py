"""Live camera/file video stream wrapper for VitalGuard."""

from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
FALL_DETECTION_DIR = ROOT_DIR / "fall detection"

if str(FALL_DETECTION_DIR) not in sys.path:
    sys.path.insert(0, str(FALL_DETECTION_DIR))

from fall_detection import FallDetector

logger = logging.getLogger(__name__)


def resolve_video_source(raw_source: int | str) -> int | str:
    """Convert numeric strings to camera indices; leave file paths untouched."""
    if isinstance(raw_source, int):
        return raw_source

    source_text = str(raw_source).strip()
    if source_text.lstrip("-").isdigit():
        return int(source_text)
    return source_text


class CameraStream:
    """Capture frames from a webcam or video file and annotate them in real time."""

    def __init__(self, source: int | str = 0) -> None:
        self.source = source
        self._source_label = f"webcam {source}" if isinstance(source, int) else str(source)
        self._should_loop = isinstance(source, str)
        self._capture = cv2.VideoCapture(source)
        if not self._capture.isOpened():
            raise RuntimeError(f"Could not open video source: {source!r}")

        self._detector = FallDetector()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)

        self._latest_frame: np.ndarray | None = None
        self._latest_result: dict[str, Any] | None = None
        self._frame_id = 0
        self._state_change_id = 0
        self._last_state: str | None = None

        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)
        self._frame_interval = 1.0 / fps if self._should_loop and fps > 0 else 0.0

        self._thread.start()
        logger.info("CameraStream started with source=%r", source)

    @staticmethod
    def _state_color(state: str) -> tuple[int, int, int]:
        mapping = {
            "in_bed_normal": (46, 204, 113),
            "bed_exit_normal": (241, 196, 15),
            "fall_detected": (231, 76, 60),
        }
        return mapping.get(state, (149, 165, 166))

    def _annotate_frame(self, frame: np.ndarray, result: dict[str, Any]) -> np.ndarray:
        annotated = frame.copy()
        height, width = annotated.shape[:2]

        state = str(result.get("state", "unknown"))
        color = self._state_color(state)
        state_text = state.replace("_", " ").title()
        confidence = result.get("confidence")
        torso_angle = result.get("torso_angle")
        hip_velocity = result.get("hip_velocity")
        landmarks_detected = result.get("landmarks_detected")
        agitation = result.get("agitation", {})
        agitation_flag = bool(agitation.get("agitation_detected"))

        cv2.rectangle(annotated, (0, 0), (width, 72), (18, 18, 18), -1)
        cv2.rectangle(annotated, (0, height - 96), (width, height), (18, 18, 18), -1)
        cv2.rectangle(annotated, (18, 16), (26, 56), color, -1)

        cv2.putText(
            annotated,
            "VitalGuard Live Camera Monitoring",
            (40, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.82,
            (245, 245, 245),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            annotated,
            f"Source: {self._source_label}",
            (40, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (190, 190, 190),
            1,
            cv2.LINE_AA,
        )

        cv2.putText(
            annotated,
            f"State: {state_text}",
            (24, height - 62),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.78,
            color,
            2,
            cv2.LINE_AA,
        )

        details = [
            f"Confidence: {confidence:.2f}" if isinstance(confidence, (int, float)) else "Confidence: n/a",
            f"Torso angle: {torso_angle:.2f}°" if isinstance(torso_angle, (int, float)) else "Torso angle: n/a",
            f"Hip velocity: {hip_velocity:.5f}" if isinstance(hip_velocity, (int, float)) else "Hip velocity: n/a",
            f"Landmarks: {'yes' if landmarks_detected else 'no'}",
            f"Agitation: {'yes' if agitation_flag else 'no'}",
        ]

        for index, text in enumerate(details):
            y = height - 36 + (index // 3) * 22
            x = 24 + (index % 3) * max(220, width // 3)
            cv2.putText(
                annotated,
                text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (230, 230, 230),
                1,
                cv2.LINE_AA,
            )

        return annotated

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            ret, frame = self._capture.read()
            if not ret:
                if self._should_loop:
                    self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._capture.read()
                    if not ret:
                        time.sleep(0.05)
                        continue
                else:
                    time.sleep(0.01)
                    continue

            result = self._detector.update(frame)
            annotated = self._annotate_frame(frame, result)
            state = str(result.get("state", "unknown"))

            with self._lock:
                self._latest_frame = annotated
                self._latest_result = result
                self._frame_id += 1
                if state != self._last_state:
                    self._state_change_id += 1
                    self._last_state = state

            if self._frame_interval > 0:
                time.sleep(self._frame_interval)

    def snapshot(self) -> dict[str, Any]:
        """Return a thread-safe copy of the latest annotated frame and metadata."""
        with self._lock:
            frame = None if self._latest_frame is None else self._latest_frame.copy()
            result = None if self._latest_result is None else dict(self._latest_result)
            return {
                "frame": frame,
                "result": result,
                "frame_id": self._frame_id,
                "state_change_id": self._state_change_id,
                "source": self._source_label,
            }

    def close(self) -> None:
        """Stop capturing and release OpenCV/MediaPipe resources."""
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._capture.release()
        self._detector.close()
        logger.info("CameraStream stopped for source=%r", self.source)

    def __enter__(self) -> "CameraStream":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
