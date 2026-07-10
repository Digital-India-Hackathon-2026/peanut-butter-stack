"""
main.py
-------
VitalGuard — Vitals Monitoring FastAPI App

Standalone FastAPI application for testing the vitals_monitoring module
in isolation.  Does NOT import from any other folder in this project.

Endpoints
---------
GET  /                  Health check
POST /trigger-abnormal  Jump simulator to the first annotated abnormal segment
WS   /ws/vitals         Stream live vitals + severity score to connected clients

Run with:
    cd vitals_monitoring
    uvicorn main:app --reload --port 8001
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from vitals_monitoring.severity_scorer import score_vitals
from vitals_monitoring.vitals_simulator import VitalsSimulator

# ---------------------------------------------------------------------------
# Configuration — edit these or set via environment variables
# ---------------------------------------------------------------------------

# Path to the PhysioNet record (without extension).
# Relative paths are resolved from the vitals_monitoring/ directory.
RECORD_PATH: str = os.environ.get(
    "VITALGUARD_RECORD_PATH",
    str(Path(__file__).parent / "data" / "100"),
)

# Injected HR values (bpm) — cycled over time, one per second
HR_VALUES: list[float] = [72, 73, 74, 75, 74, 73, 72, 71, 70, 71, 72]

# Injected SpO2 values (%) — cycled over time, one per second
SPO2_VALUES: list[float] = [98.0, 97.5, 98.0, 98.5, 99.0, 98.0, 97.0]

# ECG channel index (0 = first lead in the record)
ECG_CHANNEL: int = int(os.environ.get("VITALGUARD_CHANNEL", "0"))

# ---------------------------------------------------------------------------
# Patient Registry — bed number → patient details
# ---------------------------------------------------------------------------

PATIENTS: dict[str, dict] = {
    "BED-01": {
        "name": "Arjun Mehta",
        "age": 58,
        "gender": "Male",
        "diagnosis": "Acute Myocardial Infarction",
        "admitted": "2026-07-08",
        "record": "100",
    },
    "BED-02": {
        "name": "Priya Nair",
        "age": 45,
        "gender": "Female",
        "diagnosis": "Atrial Fibrillation",
        "admitted": "2026-07-09",
        "record": "109",
    },
    "BED-03": {
        "name": "Rajesh Kumar",
        "age": 63,
        "gender": "Male",
        "diagnosis": "Congestive Heart Failure",
        "admitted": "2026-07-07",
        "record": "100",
    },
    "BED-04": {
        "name": "Sushma Iyer",
        "age": 52,
        "gender": "Female",
        "diagnosis": "Ventricular Tachycardia",
        "admitted": "2026-07-10",
        "record": "109",
    },
    "BED-05": {
        "name": "Mohammed Farhan",
        "age": 71,
        "gender": "Male",
        "diagnosis": "Complete Heart Block",
        "admitted": "2026-07-06",
        "record": "100",
    },
}

# Active bed being monitored via WebSocket (default: BED-01)
ACTIVE_BED: str = os.environ.get("VITALGUARD_BED", "BED-01")

# ---------------------------------------------------------------------------
# Global simulator instance (created at startup)
# ---------------------------------------------------------------------------

simulator: VitalsSimulator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the simulator on startup; clean up on shutdown."""
    global simulator
    try:
        simulator = VitalsSimulator(
            record_path=RECORD_PATH,
            hr_values=HR_VALUES,
            spo2_values=SPO2_VALUES,
            channel=ECG_CHANNEL,
        )
        print(
            f"[VitalGuard] Simulator loaded: {RECORD_PATH} | "
            f"fs={simulator.sampling_frequency:.1f} Hz | "
            f"samples={simulator.n_samples}"
        )
    except Exception as exc:
        print(f"[VitalGuard] WARNING: Could not load record '{RECORD_PATH}': {exc}")
        print(
            "[VitalGuard] Set VITALGUARD_RECORD_PATH or place data files at "
            "vitals_monitoring/data/mitdb/100.*"
        )
        simulator = None
    yield
    # Nothing to clean up for the simulator


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VitalGuard — Vitals Monitoring Module",
    description=(
        "Standalone FastAPI service for real-time ECG / HR / SpO2 streaming "
        "and severity scoring. Part of the VitalGuard patient monitoring system."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@app.get("/", summary="Health check")
async def health_check() -> dict:
    """Return the service status and simulator state."""
    loaded = simulator is not None
    return {
        "status": "VitalGuard vitals module running",
        "simulator_loaded": loaded,
        "active_bed": ACTIVE_BED,
        "active_patient": PATIENTS.get(ACTIVE_BED, {}),
        "record_path": RECORD_PATH if loaded else None,
        "sampling_frequency_hz": simulator.sampling_frequency if loaded else None,
        "n_samples": simulator.n_samples if loaded else None,
    }


@app.get("/patients", summary="List all patients with bed assignments")
async def list_patients() -> dict:
    """Return the full patient registry with bed numbers."""
    return {
        "total_beds": len(PATIENTS),
        "active_bed": ACTIVE_BED,
        "patients": [
            {"bed": bed, **info}
            for bed, info in PATIENTS.items()
        ],
    }


@app.get("/patients/{bed_id}", summary="Get patient details by bed number")
async def get_patient(bed_id: str) -> JSONResponse:
    """Return details for a specific bed (e.g. BED-01)."""
    patient = PATIENTS.get(bed_id.upper())
    if patient is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Bed '{bed_id}' not found.", "available_beds": list(PATIENTS.keys())},
        )
    return JSONResponse(content={"bed": bed_id.upper(), **patient})


@app.post("/trigger-abnormal", summary="Jump to first abnormal ECG segment")
async def trigger_abnormal() -> JSONResponse:
    """
    Switch the simulator to replay from the first annotated abnormal
    ECG segment.  Returns immediately; the WebSocket stream will reflect
    the change on the next yielded sample.
    """
    if simulator is None:
        return JSONResponse(
            status_code=503,
            content={"error": "Simulator not loaded. Check server logs."},
        )
    triggered = simulator.trigger_abnormal_segment()
    return JSONResponse(
        content={
            "triggered": triggered,
            "message": (
                "Switched to abnormal ECG segment."
                if triggered
                else "No annotated abnormal segments found in this record."
            ),
        }
    )


@app.get("/synthetic-dataset", summary="Download synthetic patient dataset JSON")
async def synthetic_dataset() -> FileResponse:
    """Return the generated synthetic dataset JSON if available."""
    dataset_path = Path(__file__).parent.parent / "synthetic_dataset" / "vitalguard_synthetic_dataset.json"
    if not dataset_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "Synthetic dataset not found. Run dataset_generator.py first."},
        )
    return FileResponse(dataset_path, media_type="application/json", filename="vitalguard_synthetic_dataset.json")


@app.get("/synthetic-audio/{filename}", summary="Retrieve synthetic distress audio asset")
async def synthetic_audio(filename: str) -> FileResponse:
    """Serve a generated synthetic audio scream file by name."""
    audio_dir = Path(__file__).parent.parent / "synthetic_dataset" / "audio"
    audio_path = audio_dir / filename
    if not audio_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "Audio file not found.", "requested": filename},
        )
    return FileResponse(audio_path, media_type="audio/wav", filename=filename)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/vitals")
async def ws_vitals(websocket: WebSocket) -> None:
    """
    Stream live vitals data + severity score to the connected WebSocket client.

    Message format (JSON, sent every ECG sample):
    {
        "ecg_sample":   float,   # ECG amplitude in mV
        "ecg_label":    str,     # "normal" | "minor_irregularity" | "arrhythmia"
        "heart_rate":   float,   # HR in bpm (updated once per second)
        "spo2":         float,   # SpO2 % (updated once per second)
        "timestamp":    float,   # Unix epoch
        "sample_idx":   int,     # sample index in record
        "abnormal_mode": bool,   # true after trigger_abnormal_segment()
        "severity":     str,     # "normal" | "warning" | "critical"
        "score":        int,     # composite score 0–6
        "reasons":      [str]    # list of triggered reasons
    }
    """
    await websocket.accept()

    if simulator is None:
        await websocket.send_text(
            json.dumps({"error": "Simulator not loaded. Check server logs."})
        )
        await websocket.close(code=1011)
        return

    try:
        async for sample in simulator.stream():
            # Compute severity score for the current sample
            score_result = score_vitals(
                heart_rate=sample["heart_rate"],
                spo2=sample["spo2"],
                ecg_label=sample["ecg_label"],
            )

            patient = PATIENTS.get(ACTIVE_BED, {})
            message: dict[str, Any] = {
                # --- Patient context ---
                "bed": ACTIVE_BED,
                "patient_name": patient.get("name", "Unknown"),
                "age": patient.get("age"),
                "gender": patient.get("gender"),
                "diagnosis": patient.get("diagnosis"),
                # --- Vitals ---
                "ecg_sample": round(sample["ecg"], 6),
                "ecg_label": sample["ecg_label"],
                "heart_rate": sample["heart_rate"],
                "spo2": sample["spo2"],
                "timestamp": sample["timestamp"],
                "sample_idx": sample["sample_idx"],
                "abnormal_mode": simulator.is_abnormal_mode,
                **score_result,
            }

            await websocket.send_text(json.dumps(message))

    except WebSocketDisconnect:
        print("[VitalGuard] WebSocket client disconnected.")
    except Exception as exc:
        print(f"[VitalGuard] WebSocket error: {exc}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
