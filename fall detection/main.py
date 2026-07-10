"""
main.py
=======
VitalGuard — FastAPI Server

Exposes three endpoints:
  GET  /health           → Liveness probe
  POST /analyze-frame    → Single-frame REST analysis (JPEG/PNG bytes)
  WS   /ws/fall-alerts   → Live WebSocket stream; client sends frames, receives alerts

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import logging
from typing import Set

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from fall_detection import FallDetector, process_frame

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("vitalguard")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VitalGuard Fall Detection API",
    description=(
        "Real-time fall and bed-exit detection for hospital patient monitoring. "
        "Analyses video frames using MediaPipe Pose landmarks."
    ),
    version="1.0.0",
)


# ===========================================================================
# WebSocket connection manager
# ===========================================================================

class ConnectionManager:
    """
    Manages active WebSocket connections and provides a broadcast helper.

    Each client that connects to /ws/fall-alerts gets its own FallDetector
    instance so that rolling buffers remain per-stream and do not cross-contaminate
    between different camera feeds.
    """

    def __init__(self) -> None:
        # Maps websocket → its dedicated FallDetector
        self._connections: dict[WebSocket, FallDetector] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[websocket] = FallDetector()
        logger.info(
            "WebSocket client connected. Total connections: %d",
            len(self._connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        detector = self._connections.pop(websocket, None)
        if detector is not None:
            detector.close()
        logger.info(
            "WebSocket client disconnected. Total connections: %d",
            len(self._connections),
        )

    def get_detector(self, websocket: WebSocket) -> FallDetector:
        return self._connections[websocket]

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to ALL connected clients (used for server-push alerts)."""
        disconnected: list[WebSocket] = []
        for ws in list(self._connections.keys()):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


manager = ConnectionManager()


# ===========================================================================
# Routes
# ===========================================================================

@app.get("/health", summary="Liveness probe")
async def health() -> JSONResponse:
    """Returns 200 OK when the service is running."""
    return JSONResponse({"status": "ok", "service": "VitalGuard Fall Detection"})


@app.post(
    "/analyze-frame",
    summary="Analyse a single video frame (REST)",
    response_description="Detection result for the submitted frame",
)
async def analyze_frame(file: UploadFile = File(...)) -> JSONResponse:
    """
    Accept a JPEG or PNG image upload and return the fall detection result.

    This endpoint uses the module-level singleton detector, so state carries
    over between successive calls — treat it as a sequential frame feed.

    For isolated single-frame analysis without state, instantiate your own
    FallDetector instead.
    """
    allowed_types = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{file.content_type}'. Use JPEG or PNG.",
        )

    raw_bytes = await file.read()
    nparr = np.frombuffer(raw_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=422, detail="Could not decode the uploaded image.")

    result = process_frame(frame)
    return JSONResponse(result)


@app.websocket("/ws/fall-alerts")
async def websocket_fall_alerts(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for live fall alert streaming.

    Protocol
    --------
    1. Client connects to ws://<host>:8000/ws/fall-alerts
    2. Client sends raw JPEG or PNG frame bytes (binary message).
    3. Server responds with a JSON text message containing the detection result.
    4. Repeat for each frame.
    5. Either party may close the connection at any time.

    Each connection gets its own dedicated FallDetector so that multiple
    camera streams (e.g. Room 101, Room 102) remain independent.

    Example JSON response
    ----------------------
    {
      "state": "fall_detected",
      "confidence": 0.84,
      "timestamp": "2024-01-15T10:23:45.123456+00:00",
      "torso_angle": 78.3,
      "hip_velocity": 0.041,
      "agitation": {"agitation_detected": false, "variance": 0.00003},
      "landmarks_detected": true
    }
    """
    await manager.connect(websocket)
    detector = manager.get_detector(websocket)

    try:
        while True:
            # Receive raw image bytes from the client
            data = await websocket.receive_bytes()

            # Decode the bytes to a BGR OpenCV frame
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                await websocket.send_json({
                    "error": "Could not decode frame bytes. Send valid JPEG or PNG.",
                })
                continue

            # Run fall detection with this connection's dedicated detector
            result = detector.update(frame)

            # Send the detection result back to the client
            await websocket.send_json(result)

            # If a fall is detected, also broadcast to ALL connected dashboards
            if result.get("state") == "fall_detected":
                logger.warning("FALL DETECTED — broadcasting alert to all clients.")
                await manager.broadcast({
                    "alert_type": "fall_detected",
                    "origin": id(websocket),   # identifies which stream triggered the alert
                    **result,
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("Unexpected error in WebSocket handler: %s", exc)
        manager.disconnect(websocket)


# ===========================================================================
# Entry point (for development)
# ===========================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
