"""FastAPI app for the VitalGuard live video monitoring prototype."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
FALL_DETECTION_DIR = ROOT_DIR / "fall detection"

if str(FALL_DETECTION_DIR) not in sys.path:
    sys.path.insert(0, str(FALL_DETECTION_DIR))

try:
    from .camera_stream import CameraStream, resolve_video_source
except ImportError:  # pragma: no cover - allows direct execution during debugging
    from camera_stream import CameraStream, resolve_video_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("vitalguard.video_monitoring")


@asynccontextmanager
async def lifespan(app: FastAPI):
    raw_source = os.getenv("VIDEO_SOURCE", "0")
    source = resolve_video_source(raw_source)
    logger.info("Starting CameraStream with VIDEO_SOURCE=%r resolved to %r", raw_source, source)
    app.state.camera_stream = CameraStream(source)
    try:
        yield
    finally:
        app.state.camera_stream.close()


app = FastAPI(
    title="VitalGuard Video Monitoring",
    description="Centralized live patient camera monitoring and event streaming.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_camera_stream() -> CameraStream:
    return app.state.camera_stream


def mjpeg_frame_generator():
    stream = get_camera_stream()
    while True:
        snapshot = stream.snapshot()
        frame = snapshot["frame"]

        if frame is None:
            time.sleep(0.02)
            continue

        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            time.sleep(0.02)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )
        time.sleep(0.03)


@app.get("/health")
async def health() -> dict[str, str]:
    stream = get_camera_stream()
    return {
        "status": "ok",
        "service": "VitalGuard Video Monitoring",
        "source": str(stream.source),
    }


@app.get("/video-feed")
async def video_feed() -> StreamingResponse:
    return StreamingResponse(
        mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.websocket("/ws/video-events")
async def video_events(websocket: WebSocket) -> None:
    await websocket.accept()
    stream = get_camera_stream()
    last_seen_state_change_id = -1

    try:
        while True:
            snapshot = stream.snapshot()
            result = snapshot["result"]
            state_change_id = int(snapshot["state_change_id"])

            if result is not None and state_change_id != last_seen_state_change_id:
                await websocket.send_json(
                    {
                        "event_type": "state_change",
                        "source": snapshot["source"],
                        "frame_id": snapshot["frame_id"],
                        "state_change_id": state_change_id,
                        "state": result.get("state"),
                        "confidence": result.get("confidence"),
                        "timestamp": result.get("timestamp"),
                        "torso_angle": result.get("torso_angle"),
                        "hip_velocity": result.get("hip_velocity"),
                        "agitation": result.get("agitation"),
                        "landmarks_detected": result.get("landmarks_detected"),
                    }
                )
                last_seen_state_change_id = state_change_id

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("Video events websocket disconnected")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("video_monitoring.main:app", host="0.0.0.0", port=8000, reload=True)
