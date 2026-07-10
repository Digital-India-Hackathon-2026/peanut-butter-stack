"""
fall_detection.py
=================
VitalGuard — Fall & Bed-Exit Detection Module

Analyses video frames using MediaPipe PoseLandmarker (Tasks API, mediapipe >= 0.10)
to detect:
  - Normal in-bed patient state
  - Gradual bed-exit
  - Sudden falls

Designed to run inside a FastAPI backend for real-time processing.
All thresholds are configurable constants at the top of this file.

Model
-----
MediaPipe Tasks API requires a .task model bundle.  On first run this module
will automatically download pose_landmarker_full.task (~7 MB) from the
MediaPipe CDN into the same directory as this file.  Set the environment
variable MEDIAPIPE_MODEL_PATH to override the download location/filename.

Author : VitalGuard Engineering
"""

from __future__ import annotations

import math
import os
import time
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ---------------------------------------------------------------------------
# CONFIGURABLE CONSTANTS — tune these against labeled test videos
# ---------------------------------------------------------------------------

# Number of frames to keep in the rolling landmark buffer (~1 s at 30 fps)
BUFFER_SIZE: int = 30

# Frames of post-event stillness required to confirm a fall (~2 s at 30 fps)
POST_FALL_STABILITY_FRAMES: int = 60

# Normalized y-change per frame that triggers a fall candidate.
# MediaPipe y increases downward (0 = top of frame, 1 = bottom).
# 0.03 = hip moved 3 % of frame height downward in one frame.
VERTICAL_VELOCITY_THRESHOLD: float = 0.03

# Degrees from vertical; torso angle >= this value indicates horizontal/fallen posture.
# 0° = perfectly upright, 90° = fully horizontal.
TORSO_ANGLE_THRESHOLD: float = 45.0

# Gradual downward hip velocity threshold that characterises bed-exit
# (smaller than the fall threshold).
BED_EXIT_VELOCITY_THRESHOLD: float = 0.008

# Normalized landmark position variance over the rolling window.
# Exceeding this flags "agitation_detected" (shaking/thrashing behaviour).
AGITATION_VARIANCE_THRESHOLD: float = 0.0005

# Minimum MediaPipe visibility score (0–1) to trust a landmark value.
MIN_LANDMARK_VISIBILITY: float = 0.5

# ---------------------------------------------------------------------------
# MediaPipe PoseLandmarker landmark indices (33 body keypoints)
# https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#pose_landmarker_model
# ---------------------------------------------------------------------------
IDX_LEFT_SHOULDER  = 11
IDX_RIGHT_SHOULDER = 12
IDX_LEFT_HIP       = 23
IDX_RIGHT_HIP      = 24
IDX_LEFT_WRIST     = 15
IDX_RIGHT_WRIST    = 16
IDX_LEFT_ANKLE     = 27
IDX_RIGHT_ANKLE    = 28

# Landmark indices used for agitation detection
AGITATION_LANDMARK_INDICES: list[int] = [
    IDX_LEFT_WRIST, IDX_RIGHT_WRIST,
    IDX_LEFT_SHOULDER, IDX_RIGHT_SHOULDER,
    IDX_LEFT_HIP, IDX_RIGHT_HIP,
]

# ---------------------------------------------------------------------------
# Model download helpers
# ---------------------------------------------------------------------------
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
_DEFAULT_MODEL_PATH = Path(__file__).parent / "pose_landmarker_full.task"


def _ensure_model(model_path: Path) -> Path:
    """
    Download the MediaPipe PoseLandmarker model bundle if it is not already present.
    The download location can be overridden via the MEDIAPIPE_MODEL_PATH env variable.
    """
    env_override = os.environ.get("MEDIAPIPE_MODEL_PATH")
    if env_override:
        model_path = Path(env_override)

    if not model_path.exists():
        print(
            f"[VitalGuard] Downloading PoseLandmarker model to {model_path} …"
            f"\n  Source: {_MODEL_URL}"
        )
        model_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_MODEL_URL, model_path)
        print("[VitalGuard] Model download complete.")

    return model_path


# ===========================================================================
# NormalizedLandmark-like wrapper for the Tasks API result
# ===========================================================================

class _Landmark:
    """
    Thin wrapper so the rest of the code can use lm.x / lm.y / lm.visibility
    uniformly, whether the source is the legacy API or the Tasks API.
    """
    __slots__ = ("x", "y", "z", "visibility")

    def __init__(self, x: float, y: float, z: float = 0.0, visibility: float = 1.0):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


def _tasks_to_landmarks(tasks_result) -> Optional[list[_Landmark]]:
    """
    Convert a mediapipe.tasks PoseLandmarkerResult to a list of _Landmark
    objects (first detected person only).

    Returns None if no pose was found.
    """
    if not tasks_result or not tasks_result.pose_landmarks:
        return None

    # tasks_result.pose_landmarks is List[List[NormalizedLandmark]]
    # (outer = person, inner = 33 keypoints)
    raw = tasks_result.pose_landmarks[0]
    out: list[_Landmark] = []
    for lm in raw:
        # Tasks API NormalizedLandmark has .x .y .z and .visibility
        vis = getattr(lm, "visibility", 1.0) or 1.0
        out.append(_Landmark(lm.x, lm.y, getattr(lm, "z", 0.0), float(vis)))
    return out


# ===========================================================================
# Standalone helper — agitation detection
# ===========================================================================

def detect_agitation(landmark_buffer: deque) -> dict:
    """
    Analyse the rolling landmark buffer for high-frequency movement that
    indicates patient shaking or thrashing (agitation), rather than a fall.

    Parameters
    ----------
    landmark_buffer : deque
        Each element is either a list of _Landmark objects (one per frame)
        or None if pose was not detected for that frame.

    Returns
    -------
    dict
        {
          "agitation_detected": bool,
          "variance": float   # mean positional variance across key landmarks
        }
    """
    # Collect (x, y) series for each agitation landmark across all frames
    # where landmarks were successfully detected.
    series: dict[int, list[tuple[float, float]]] = {
        idx: [] for idx in AGITATION_LANDMARK_INDICES
    }

    for frame_landmarks in landmark_buffer:
        if frame_landmarks is None:
            continue
        for idx in AGITATION_LANDMARK_INDICES:
            if idx >= len(frame_landmarks):
                continue
            lm = frame_landmarks[idx]
            if lm.visibility >= MIN_LANDMARK_VISIBILITY:
                series[idx].append((lm.x, lm.y))

    if not any(series.values()):
        return {"agitation_detected": False, "variance": 0.0}

    variances: list[float] = []
    for idx, positions in series.items():
        if len(positions) < 2:
            continue
        arr = np.array(positions, dtype=np.float32)  # shape (N, 2)
        var_x = float(np.var(arr[:, 0]))
        var_y = float(np.var(arr[:, 1]))
        variances.append((var_x + var_y) / 2.0)

    mean_variance = float(np.mean(variances)) if variances else 0.0
    detected = mean_variance > AGITATION_VARIANCE_THRESHOLD

    return {"agitation_detected": detected, "variance": round(mean_variance, 6)}


# ===========================================================================
# FallDetector — core detection class
# ===========================================================================

class FallDetector:
    """
    Real-time fall and bed-exit detector using MediaPipe PoseLandmarker (Tasks API).

    Usage
    -----
    detector = FallDetector()
    result = detector.update(frame)   # frame is a BGR numpy array from OpenCV
    print(result)
    # -> {"state": "fall_detected", "confidence": 0.87, "timestamp": "...", "agitation": {...}}

    Or as a context manager:
    with FallDetector() as detector:
        result = detector.update(frame)
    """

    def __init__(self, model_path: Optional[Path] = None) -> None:
        # Resolve and download model if needed
        resolved = _ensure_model(model_path or _DEFAULT_MODEL_PATH)

        # Build PoseLandmarker options for VIDEO mode (stateful frame-by-frame)
        base_options = mp_python.BaseOptions(model_asset_path=str(resolved))
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)

        # Rolling buffer of landmark lists (None if pose not detected that frame)
        self._buffer: deque[Optional[list]] = deque(maxlen=BUFFER_SIZE)

        # Internal state machine for fall confirmation
        self._fall_candidate_frame: Optional[int] = None
        self._frame_index: int = 0
        self._start_time_ms: int = int(time.time() * 1000)  # epoch ms at creation

        # Track the last emitted state for continuity
        self._last_state: str = "in_bed_normal"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_landmarks(
        self, frame: np.ndarray, timestamp_ms: int
    ) -> Optional[list]:
        """
        Run MediaPipe PoseLandmarker on a BGR frame.

        Returns a list of _Landmark objects, or None if no pose found.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        return _tasks_to_landmarks(result)

    def _hip_center(self, landmarks: list) -> tuple[float, float]:
        """Return the (x, y) midpoint between left and right hips."""
        left  = landmarks[IDX_LEFT_HIP]
        right = landmarks[IDX_RIGHT_HIP]
        lv = left.visibility  >= MIN_LANDMARK_VISIBILITY
        rv = right.visibility >= MIN_LANDMARK_VISIBILITY
        if lv and rv:
            return ((left.x + right.x) / 2.0, (left.y + right.y) / 2.0)
        elif lv:
            return (left.x, left.y)
        elif rv:
            return (right.x, right.y)
        return (0.5, 0.5)

    def _shoulder_center(self, landmarks: list) -> tuple[float, float]:
        """Return the (x, y) midpoint between left and right shoulders."""
        left  = landmarks[IDX_LEFT_SHOULDER]
        right = landmarks[IDX_RIGHT_SHOULDER]
        lv = left.visibility  >= MIN_LANDMARK_VISIBILITY
        rv = right.visibility >= MIN_LANDMARK_VISIBILITY
        if lv and rv:
            return ((left.x + right.x) / 2.0, (left.y + right.y) / 2.0)
        elif lv:
            return (left.x, left.y)
        elif rv:
            return (right.x, right.y)
        return (0.5, 0.5)

    def _torso_angle(self, landmarks: list) -> float:
        """
        Angle (degrees) between the shoulder→hip vector and the downward vertical.

        0° = upright (standing/sitting), 90° = horizontal (lying/fallen).
        Uses atan2 so it is camera-facing direction agnostic.
        """
        sx, sy = self._shoulder_center(landmarks)
        hx, hy = self._hip_center(landmarks)
        dx = hx - sx
        dy = hy - sy  # positive = downward in MediaPipe coords
        angle_rad = math.atan2(abs(dx), abs(dy)) if abs(dy) > 1e-6 else math.pi / 2
        return math.degrees(angle_rad)

    def _vertical_velocity(self) -> float:
        """
        Mean downward velocity (Δy / frame) of the hip center over the buffer.
        Positive = hip moving downward (falling / sitting / standing up from bed).
        """
        hip_y_series: list[float] = []
        for frame_landmarks in self._buffer:
            if frame_landmarks is None:
                continue
            _, hy = self._hip_center(frame_landmarks)
            hip_y_series.append(hy)
        if len(hip_y_series) < 2:
            return 0.0
        deltas = [
            hip_y_series[i] - hip_y_series[i - 1]
            for i in range(1, len(hip_y_series))
        ]
        return float(np.mean(deltas))

    def _feet_near_floor(self, landmarks: list) -> bool:
        """
        Return True if ankle landmarks are near the bottom of the frame (y > 0.85),
        characteristic of someone standing after a bed-exit.
        """
        ankles: list[float] = []
        for idx in (IDX_LEFT_ANKLE, IDX_RIGHT_ANKLE):
            lm = landmarks[idx]
            if lm.visibility >= MIN_LANDMARK_VISIBILITY:
                ankles.append(lm.y)
        return bool(ankles) and max(ankles) > 0.85

    def _post_fall_stillness(self) -> bool:
        """
        True when enough still frames have accumulated after the fall candidate —
        distinguishes a genuine fall from a fast sit-down.
        """
        if self._fall_candidate_frame is None:
            return False
        frames_since = self._frame_index - self._fall_candidate_frame
        if frames_since < POST_FALL_STABILITY_FRAMES:
            return False
        return abs(self._vertical_velocity()) < BED_EXIT_VELOCITY_THRESHOLD

    def _compute_confidence(
        self, state: str, torso_angle: float, velocity: float
    ) -> float:
        """Compute a 0.0–1.0 confidence score for the classified state."""
        if state == "fall_detected":
            angle_score    = min(torso_angle / 90.0, 1.0)
            velocity_score = min(abs(velocity) / (VERTICAL_VELOCITY_THRESHOLD * 3), 1.0)
            return round(angle_score * 0.6 + velocity_score * 0.4, 3)
        elif state == "bed_exit_normal":
            vel_score   = min(abs(velocity) / VERTICAL_VELOCITY_THRESHOLD, 1.0)
            angle_score = max(0.0, 1.0 - torso_angle / TORSO_ANGLE_THRESHOLD)
            return round(vel_score * 0.5 + angle_score * 0.5, 3)
        else:  # in_bed_normal
            vel_score = max(0.0, 1.0 - abs(velocity) / BED_EXIT_VELOCITY_THRESHOLD)
            return round(vel_score * 0.8 + 0.2, 3)

    def _classify_state(self, landmarks: list) -> tuple[str, float]:
        """
        State machine:
          in_bed_normal  ──(rapid drop + horizontal torso)──► fall_candidate
                                                               ──(stillness confirmed)──► fall_detected
          in_bed_normal  ──(gradual drop + feet on floor)───► bed_exit_normal
          everything else ────────────────────────────────► in_bed_normal
        """
        torso_angle = self._torso_angle(landmarks)
        velocity    = self._vertical_velocity()

        # --- Wait for fall confirmation ---
        if self._fall_candidate_frame is not None:
            if self._post_fall_stillness():
                return (
                    "fall_detected",
                    self._compute_confidence("fall_detected", torso_angle, velocity),
                )
            # Still in candidate window — emit warning state at reduced confidence
            return (
                "fall_detected",
                self._compute_confidence("fall_detected", torso_angle, velocity) * 0.7,
            )

        # --- New fall candidate? ---
        if (velocity > VERTICAL_VELOCITY_THRESHOLD and
                torso_angle > TORSO_ANGLE_THRESHOLD):
            self._fall_candidate_frame = self._frame_index
            return (
                "fall_detected",
                self._compute_confidence("fall_detected", torso_angle, velocity) * 0.6,
            )

        # --- Bed-exit? ---
        if (BED_EXIT_VELOCITY_THRESHOLD < velocity <= VERTICAL_VELOCITY_THRESHOLD and
                self._feet_near_floor(landmarks) and
                torso_angle < TORSO_ANGLE_THRESHOLD):
            return (
                "bed_exit_normal",
                self._compute_confidence("bed_exit_normal", torso_angle, velocity),
            )

        # --- Default: normal in-bed ---
        if torso_angle < TORSO_ANGLE_THRESHOLD:
            # Torso is upright — safe to reset any stale fall candidate
            self._fall_candidate_frame = None

        return (
            "in_bed_normal",
            self._compute_confidence("in_bed_normal", torso_angle, velocity),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, frame: np.ndarray) -> dict:
        """
        Process a single BGR video frame and return the detection result.

        Parameters
        ----------
        frame : np.ndarray
            BGR image from OpenCV (e.g. from cv2.VideoCapture.read()).

        Returns
        -------
        dict
            {
              "state"             : str,   # "in_bed_normal" | "bed_exit_normal" | "fall_detected"
              "confidence"        : float, # 0.0 – 1.0
              "timestamp"         : str,   # ISO-8601 UTC
              "torso_angle"       : float | None,
              "hip_velocity"      : float | None,
              "agitation"         : dict,
              "landmarks_detected": bool
            }
        """
        self._frame_index += 1

        # Monotonically increasing timestamp required by VIDEO mode
        timestamp_ms = self._start_time_ms + self._frame_index * 33  # ~30 fps

        landmarks = self._extract_landmarks(frame, timestamp_ms)
        self._buffer.append(landmarks)
        iso_ts = datetime.now(timezone.utc).isoformat()

        if landmarks is None:
            return {
                "state": self._last_state,
                "confidence": 0.1,
                "timestamp": iso_ts,
                "torso_angle": None,
                "hip_velocity": None,
                "agitation": detect_agitation(self._buffer),
                "landmarks_detected": False,
            }

        state, confidence = self._classify_state(landmarks)
        self._last_state = state

        return {
            "state": state,
            "confidence": round(confidence, 3),
            "timestamp": iso_ts,
            "torso_angle": round(self._torso_angle(landmarks), 2),
            "hip_velocity": round(self._vertical_velocity(), 5),
            "agitation": detect_agitation(self._buffer),
            "landmarks_detected": True,
        }

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ===========================================================================
# Module-level singleton + convenience function
# ===========================================================================

_detector: Optional[FallDetector] = None


def _get_detector() -> FallDetector:
    """Lazy-initialise and return the module-level FallDetector singleton."""
    global _detector
    if _detector is None:
        _detector = FallDetector()
    return _detector


def process_frame(frame: np.ndarray) -> dict:
    """
    Top-level convenience function for processing a single BGR video frame.

    Uses a module-level FallDetector singleton so callers do not need to
    manage the detector lifecycle explicitly.

    Parameters
    ----------
    frame : np.ndarray
        BGR image (e.g., from cv2.VideoCapture.read()).

    Returns
    -------
    dict
        Detection result with keys: state, confidence, timestamp,
        torso_angle, hip_velocity, agitation, landmarks_detected.

    Example
    -------
    >>> import cv2
    >>> from fall_detection import process_frame
    >>> cap = cv2.VideoCapture(0)
    >>> ret, frame = cap.read()
    >>> result = process_frame(frame)
    >>> print(result["state"])
    'in_bed_normal'
    """
    return _get_detector().update(frame)
