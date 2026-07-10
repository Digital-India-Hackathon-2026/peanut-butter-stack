"""smoke_test.py — quick import and instantiation check for fall_detection.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import mediapipe
import fastapi
import uvicorn
import websockets
import numpy as np
from collections import deque

print("=== Dependency versions ===")
print(f"  cv2:       {cv2.__version__}")
print(f"  mediapipe: {mediapipe.__version__}")
print(f"  fastapi:   {fastapi.__version__}")
print(f"  numpy:     {np.__version__}")

print()
print("=== Importing fall_detection.py ===")
from fall_detection import (
    FallDetector, detect_agitation, process_frame,
    BUFFER_SIZE, VERTICAL_VELOCITY_THRESHOLD,
    TORSO_ANGLE_THRESHOLD, AGITATION_VARIANCE_THRESHOLD,
)
print("  Import OK")
print(f"  BUFFER_SIZE                 = {BUFFER_SIZE}")
print(f"  VERTICAL_VELOCITY_THRESHOLD = {VERTICAL_VELOCITY_THRESHOLD}")
print(f"  TORSO_ANGLE_THRESHOLD       = {TORSO_ANGLE_THRESHOLD}")
print(f"  AGITATION_VARIANCE_THRESHOLD= {AGITATION_VARIANCE_THRESHOLD}")

print()
print("=== Instantiating FallDetector ===")
det = FallDetector()
print("  FallDetector() ... OK")
det.close()
print("  FallDetector.close() ... OK")

print()
print("=== detect_agitation with empty buffer ===")
result = detect_agitation(deque([None, None]))
print(f"  Result: {result}")
assert result["agitation_detected"] is False

print()
print("=== process_frame with blank 480x640 frame ===")
blank = np.zeros((480, 640, 3), dtype=np.uint8)
res = process_frame(blank)
state = res["state"]
conf  = res["confidence"]
lm    = res["landmarks_detected"]
print(f"  state={state}  confidence={conf}  landmarks_detected={lm}")
assert state in ("in_bed_normal", "bed_exit_normal", "fall_detected")
assert 0.0 <= conf <= 1.0

print()
print("=== FastAPI app import ===")
from main import app
print(f"  app title: {app.title}")

print()
print("All checks passed — SMOKE TEST PASS")
