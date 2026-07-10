"""FastAPI websocket service for VitalGuard audio distress monitoring."""

from __future__ import annotations

import asyncio
import json
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional

import numpy as np
import sounddevice as sd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from audio_monitoring.distress_detection import (
    DistressTracker,
    check_volume_spike,
    detect_distress_phrase,
    update_rolling_baseline_rms,
)
from audio_monitoring.speech_to_text import SpeechTranscriber

app = FastAPI(title="VitalGuard Audio Monitoring")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "VitalGuard Audio Monitoring",
        "description": "Live microphone distress event websocket service.",
    }


@dataclass
class AudioEventState:
    event: str = "normal"
    matched_phrase: Optional[str] = None


class MicAudioStreamer:
    def __init__(self, sample_rate: int = 16000, chunk_seconds: float = 4.0) -> None:
        self.sample_rate = sample_rate
        self.chunk_frames = int(sample_rate * chunk_seconds)
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=8)
        self._stream: Optional[sd.InputStream] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _callback(self, indata, frames, time_info, status):  # pragma: no cover - callback runs in sounddevice thread
        if status:
            return
        if self._loop is None:
            return
        chunk = np.asarray(indata[:, 0], dtype=np.float32).copy()
        try:
            self._loop.call_soon_threadsafe(self._push_chunk, chunk)
        except RuntimeError:
            return

    def _push_chunk(self, chunk: np.ndarray) -> None:
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._queue.put_nowait(chunk)

    async def __aenter__(self) -> "MicAudioStreamer":
        self._loop = asyncio.get_running_loop()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.chunk_frames,
            callback=self._callback,
        )
        self._stream.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        self._stream = None
        self._loop = None

    async def next_chunk(self) -> np.ndarray:
        return await self._queue.get()


@app.websocket("/ws/audio-events")
async def websocket_audio_events(websocket: WebSocket) -> None:
    await websocket.accept()
    transcriber = SpeechTranscriber(model_size="base")
    tracker = DistressTracker()
    quiet_rms_history: Deque[float] = deque()
    baseline_rms = 0.0
    state = AudioEventState()
    patient_id = "ICU-12"

    try:
        async with MicAudioStreamer() as mic_stream:
            while True:
                audio_chunk = await mic_stream.next_chunk()
                transcript = await asyncio.to_thread(transcriber.transcribe, audio_chunk)
                phrase_result = detect_distress_phrase(transcript)
                phrase_detected = bool(phrase_result["distress_detected"])
                repeated_result = tracker.record_detection(phrase_detected)
                repeated_distress = bool(repeated_result["repeated_distress"])
                volume_result = check_volume_spike(audio_chunk, baseline_rms)
                volume_spike = bool(volume_result["volume_spike"])
                current_rms = float(volume_result["rms"])

                if not phrase_detected and not volume_spike:
                    baseline_rms = update_rolling_baseline_rms(quiet_rms_history, current_rms)

                event = "normal"
                confidence = 0.0
                matched_phrase = None

                if repeated_distress:
                    event = "repeated_distress"
                    confidence = 0.95
                    matched_phrase = phrase_result["matched_phrase"]
                elif phrase_detected:
                    event = "distress_phrase"
                    confidence = 0.85
                    matched_phrase = phrase_result["matched_phrase"]
                elif volume_spike:
                    event = "loud_vocalization"
                    confidence = 0.35

                if event != state.event or matched_phrase != state.matched_phrase:
                    payload = {
                        "patient": patient_id,
                        "event": event,
                        "confidence": confidence,
                        "matched_phrase": matched_phrase,
                        "time": datetime.now(timezone.utc).isoformat(),
                    }
                    await websocket.send_text(json.dumps(payload))
                    state = AudioEventState(event=event, matched_phrase=matched_phrase)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover - runtime safety
        await websocket.send_text(
            json.dumps(
                {
                    "patient": patient_id,
                    "event": "normal",
                    "confidence": 0.0,
                    "matched_phrase": None,
                    "time": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc),
                }
            )
        )
        raise


def run() -> None:
    import uvicorn

    uvicorn.run("audio_monitoring.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
