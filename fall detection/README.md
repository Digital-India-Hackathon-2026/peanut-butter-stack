# VitalGuard — Fall & Bed-Exit Detection Module

Real-time fall and bed-exit detection for the VitalGuard hospital patient monitoring system.
Analyses MediaPipe Pose landmarks from video frames to classify patient state and stream
live alerts via FastAPI WebSocket.

---

## Prerequisites

- Python 3.10 or later
- A webcam or RTSP camera feed (or video files for testing)

---

## Setup

```bash
# 1. Clone / copy the project files into a directory
cd "d:\fall detection"

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be live at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/analyze-frame` | Upload a JPEG/PNG and get the detection result |
| `WS` | `/ws/fall-alerts` | Live WebSocket stream |

### WebSocket Protocol

1. Connect to `ws://localhost:8000/ws/fall-alerts`
2. Send raw JPEG/PNG frame bytes (binary message)
3. Receive JSON detection result

```json
{
  "state": "fall_detected",
  "confidence": 0.84,
  "timestamp": "2024-01-15T10:23:45.123456+00:00",
  "torso_angle": 78.3,
  "hip_velocity": 0.041,
  "agitation": {
    "agitation_detected": false,
    "variance": 0.00003
  },
  "landmarks_detected": true
}
```

---

## Running Tests Against Video Clips

```bash
# Basic run — print summary table
python test_fall_detection.py --video-dir ./clips

# Override FPS if container metadata is wrong
python test_fall_detection.py --video-dir ./clips --fps 25

# Save per-clip CSV summary
python test_fall_detection.py --video-dir ./clips --output results.csv

# Save per-clip + per-frame CSV logs
python test_fall_detection.py --video-dir ./clips --output results.csv --save-frame-logs

# Verbose: print every frame's state
python test_fall_detection.py --video-dir ./clips --verbose
```

### Clip Labelling Convention

Name your clip files with a keyword so the test script can track accuracy:

| Keyword in filename | Expected state |
|---------------------|----------------|
| `fall` | `fall_detected` |
| `exit` or `bed_exit` | `bed_exit_normal` |
| `normal` or `inbed` | `in_bed_normal` |
| anything else | `unknown` (not counted in accuracy) |

Examples: `patient01_fall_01.mp4`, `room3_bed_exit_morning.avi`, `normal_sleep.mp4`

---

## Using the Module Programmatically

```python
import cv2
from fall_detection import process_frame, FallDetector

# Option A — module-level singleton (easy, shared state)
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break
    result = process_frame(frame)
    print(result["state"], result["confidence"])

# Option B — dedicated instance (recommended for multi-camera setups)
with FallDetector() as detector:
    ret, frame = cap.read()
    result = detector.update(frame)
```

---

## Tunable Constants

All constants are at the top of `fall_detection.py`:

| Constant | Default | Description |
|---|---|---|
| `BUFFER_SIZE` | `30` | Rolling window size (frames). ~1 s at 30 fps |
| `POST_FALL_STABILITY_FRAMES` | `60` | Frames of stillness required to confirm fall (~2 s) |
| `VERTICAL_VELOCITY_THRESHOLD` | `0.03` | Normalised hip y-velocity to trigger fall candidate |
| `TORSO_ANGLE_THRESHOLD` | `45.0` | Degrees; above this = horizontal/fallen posture |
| `BED_EXIT_VELOCITY_THRESHOLD` | `0.008` | Gradual motion threshold for bed-exit classification |
| `AGITATION_VARIANCE_THRESHOLD` | `0.0005` | Position variance to flag shaking/thrashing |
| `MIN_LANDMARK_VISIBILITY` | `0.5` | MediaPipe visibility score cutoff |

> **Tip**: Start with the defaults, run the test script against your labeled clips,
> then adjust constants based on the confusion matrix.

---

## Integration Notes

- `FallDetector` is **not thread-safe by default**. For multi-threaded servers, either use
  `asyncio` (which the FastAPI WebSocket handler does), or protect with a `threading.Lock`.
- Each WebSocket connection gets its **own** `FallDetector` instance in `main.py`, so
  multiple camera streams remain independent.
- For RTSP streams, pass the URL to `cv2.VideoCapture("rtsp://...")` and feed frames
  to `process_frame()` or `detector.update()` as usual.

---

## Architecture

```
Video Source (camera / RTSP / file)
        │
        ▼
  OpenCV Frame (BGR numpy array)
        │
        ▼
  process_frame(frame)
        │
   ┌────┴────────────────────────────┐
   │         FallDetector            │
   │   MediaPipe Pose Extraction     │
   │   Rolling Buffer (30 frames)    │
   │   Hip Vertical Velocity Calc    │
   │   Torso Angle Calculation       │
   │   State Classification          │
   └─────────────────────────────────┘
        │                │
        │         detect_agitation()
        │
        ├──→  POST /analyze-frame   (REST)
        └──→  WS /ws/fall-alerts    (WebSocket broadcast)
```
