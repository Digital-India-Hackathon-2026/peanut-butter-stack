"""VitalGuard unified monitoring app.

Run from the repository root:
    uvicorn main:app --reload --port 8000

This app mounts the existing video, audio, and vitals sub-applications
under `/video`, `/audio`, and `/vitals` respectively.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from audio_monitoring.main import app as audio_app
from auth import router as auth_router
from video_monitoring.main import app as video_app
from vitals_monitoring.main import app as vitals_app

app = FastAPI(
    title="VitalGuard Unified Monitoring",
    description=(
        "Combined VitalGuard live camera, audio distress, and vitals streaming "
        "service with video, audio, and ECG/SpO2 endpoints."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

app.mount("/video", video_app)
app.mount("/vitals", vitals_app)
app.mount("/audio", audio_app)

@app.get("/", summary="Root health check")
async def root() -> dict[str, object]:
    return {
        "status": "VitalGuard unified monitoring active",
        "video_service": {
            "health": "/video/health",
            "feed": "/video/video-feed",
            "events_ws": "/video/ws/video-events",
        },
        "audio_service": {
            "health": "/audio/health",
            "events_ws": "/audio/ws/audio-events",
        },
        "vitals_service": {
            "health": "/vitals/",
            "trigger_abnormal": "/vitals/trigger-abnormal",
            "ws_vitals": "/vitals/ws/vitals",
        },
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
