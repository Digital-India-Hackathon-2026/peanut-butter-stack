"""
main.py
-------
VitalGuard — Vitals Monitoring FastAPI App

Standalone FastAPI application for testing the vitals_monitoring module
in isolation.  Does NOT import from any other folder in this project.

Endpoints
---------
GET  /                         Health check
POST /trigger-abnormal         Jump simulator to the first annotated abnormal segment
WS   /ws/vitals                Stream live vitals + severity score to connected clients
POST /alerts/test-call         Manually trigger a test Twilio voice call to a doctor
POST /alerts/test-sms          Manually trigger a test Twilio SMS to a nurse
GET  /alerts/history           Return recent alert dispatch log
POST /alerts/reset-cooldown    Reset alert cooldown for a patient (testing)

Run with:
    cd vitals_monitoring
    uvicorn main:app --reload --port 8001

Twilio environment variables:
    TWILIO_ACCOUNT_SID        — Twilio Account SID
    TWILIO_AUTH_TOKEN         — Twilio Auth Token
    TWILIO_FROM_NUMBER        — Your Twilio phone number (e.g. +1XXXXXXXXXX)
    TWILIO_ALERT_COOLDOWN_SECONDS — seconds between repeated alerts (default: 300)
    TWILIO_DRY_RUN            — set to "true" to log alerts without sending (default: false)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Load environment variables from a .env file in the repo root or twilio_alerts folder.
env_path = find_dotenv(filename=".env", raise_error_if_not_found=False)
if not env_path:
    env_path = Path(__file__).resolve().parent.parent / "twilio_alerts" / ".env"
load_dotenv(env_path, override=False)

from vitals_monitoring.severity_scorer import score_vitals
from vitals_monitoring.vitals_simulator import VitalsSimulator
from twilio_alerts.alert_service import AlertService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

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
        "patient_id": "BED-01",
        "name": "Arjun Mehta",
        "age": 58,
        "gender": "Male",
        "diagnosis": "Acute Myocardial Infarction",
        "admitted": "2026-07-08",
        "record": "100",
        "assigned_doctor": "Dr. Naveen Rao",
        "assigned_nurse": "Nurse Sunita",
        # Replace with real phone numbers; loaded from env vars if set
        "doctor_phone": os.environ.get("DOCTOR_PHONE_BED01", os.environ.get("DOCTOR_PHONE_NUMBER", "")),
        "nurse_phone": os.environ.get("NURSE_PHONE_BED01", os.environ.get("NURSE_PHONE_NUMBER", "")),
    },
    "BED-02": {
        "patient_id": "BED-02",
        "name": "Priya Nair",
        "age": 45,
        "gender": "Female",
        "diagnosis": "Atrial Fibrillation",
        "admitted": "2026-07-09",
        "record": "109",
        "assigned_doctor": "Dr. Ananya Krishnan",
        "assigned_nurse": "Nurse Pooja",
        "doctor_phone": os.environ.get("DOCTOR_PHONE_BED02", os.environ.get("DOCTOR_PHONE_NUMBER", "")),
        "nurse_phone": os.environ.get("NURSE_PHONE_BED02", os.environ.get("NURSE_PHONE_NUMBER", "")),
    },
    "BED-03": {
        "patient_id": "BED-03",
        "name": "Rajesh Kumar",
        "age": 63,
        "gender": "Male",
        "diagnosis": "Congestive Heart Failure",
        "admitted": "2026-07-07",
        "record": "100",
        "assigned_doctor": "Dr. Suresh Iyer",
        "assigned_nurse": "Nurse Deepa",
        "doctor_phone": os.environ.get("DOCTOR_PHONE_BED03", os.environ.get("DOCTOR_PHONE_NUMBER", "")),
        "nurse_phone": os.environ.get("NURSE_PHONE_BED03", os.environ.get("NURSE_PHONE_NUMBER", "")),
    },
    "BED-04": {
        "patient_id": "BED-04",
        "name": "Sushma Iyer",
        "age": 52,
        "gender": "Female",
        "diagnosis": "Ventricular Tachycardia",
        "admitted": "2026-07-10",
        "record": "109",
        "assigned_doctor": "Dr. Pradeep Mehta",
        "assigned_nurse": "Nurse Kavitha",
        "doctor_phone": os.environ.get("DOCTOR_PHONE_BED04", os.environ.get("DOCTOR_PHONE_NUMBER", "")),
        "nurse_phone": os.environ.get("NURSE_PHONE_BED04", os.environ.get("NURSE_PHONE_NUMBER", "")),
    },
    "BED-05": {
        "patient_id": "BED-05",
        "name": "Mohammed Farhan",
        "age": 71,
        "gender": "Male",
        "diagnosis": "Complete Heart Block",
        "admitted": "2026-07-06",
        "record": "100",
        "assigned_doctor": "Dr. Ramesh Gupta",
        "assigned_nurse": "Nurse Meena",
        "doctor_phone": os.environ.get("DOCTOR_PHONE_BED05", os.environ.get("DOCTOR_PHONE_NUMBER", "")),
        "nurse_phone": os.environ.get("NURSE_PHONE_BED05", os.environ.get("NURSE_PHONE_NUMBER", "")),
    },
    "BED-10": {
        "patient_id": "BED-10",
        "name": "Devika Nair",
        "age": 37,
        "gender": "Female",
        "diagnosis": "Fall risk monitoring",
        "admitted": "2026-07-11",
        "record": "109",
        "assigned_doctor": "Dr. Kavya Sharma",
        "assigned_nurse": "Nurse Leela",
        "doctor_phone": os.environ.get("DOCTOR_PHONE_BED10", os.environ.get("DOCTOR_PHONE_NUMBER", "")),
        "nurse_phone": os.environ.get("NURSE_PHONE_BED10", os.environ.get("NURSE_PHONE_NUMBER", "")),
    },
}

# Active bed being monitored via WebSocket (default: BED-01)
ACTIVE_BED: str = os.environ.get(
    "VITALGUARD_BED",
    os.environ.get("ACTIVE_BED", "BED-01"),
).upper()

# ---------------------------------------------------------------------------
# Global instances (created at startup)
# ---------------------------------------------------------------------------

simulator: VitalsSimulator | None = None
alert_service: AlertService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the simulator and alert service on startup; clean up on shutdown."""
    global simulator, alert_service
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

    # Initialize Twilio AlertService
    alert_service = AlertService()
    print("[VitalGuard] Twilio AlertService initialized.")

    yield
    # Nothing to clean up for the simulator or alert service


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


class SetActiveBedRequest(BaseModel):
    bed_id: str


@app.post("/patients/active", summary="Set the active bed for streaming and alerting")
async def set_active_bed(req: SetActiveBedRequest) -> JSONResponse:
    """Update the currently monitored bed used for the WebSocket stream and Twilio alerts."""
    global ACTIVE_BED
    bed_id = req.bed_id.upper()
    if bed_id not in PATIENTS:
        return JSONResponse(
            status_code=404,
            content={"error": f"Bed '{req.bed_id}' not found.", "available_beds": list(PATIENTS.keys())},
        )
    ACTIVE_BED = bed_id
    return JSONResponse(content={"active_bed": ACTIVE_BED, "active_patient": PATIENTS[ACTIVE_BED]})


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


# ---------------------------------------------------------------------------
# Alert REST endpoints
# ---------------------------------------------------------------------------


class TestAlertRequest(BaseModel):
    bed_id: str = "BED-01"
    severity: str = "critical"
    reset_cooldown: bool = True
    doctor_number: str | None = None


class ResetCooldownRequest(BaseModel):
    patient_id: str
    channel: str | None = None  # "call" | "sms" | None (both)


@app.post("/alerts/test-call", summary="Manually trigger a test voice call to the doctor")
async def test_doctor_call(req: TestAlertRequest) -> JSONResponse:
    """
    Manually dispatch a Twilio voice call to the doctor assigned to the given bed.
    Useful for testing Twilio credentials and verifying the alert flow.
    """
    if alert_service is None:
        return JSONResponse(status_code=503, content={"error": "AlertService not initialized."})

    patient = PATIENTS.get(req.bed_id.upper())
    if patient is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Bed '{req.bed_id}' not found.", "available_beds": list(PATIENTS.keys())},
        )

    if req.reset_cooldown:
        alert_service.reset_cooldown(patient.get("patient_id", req.bed_id), "call")

    reasons = ["Manual test call from VitalGuard API"]
    import asyncio as _asyncio
    entry = await _asyncio.to_thread(
        alert_service.send_doctor_call,
        patient,
        reasons,
        req.severity,
    )
    return JSONResponse(content={
        "alert_id": entry.alert_id,
        "status": entry.status,
        "channel": entry.channel,
        "recipient_role": entry.recipient_role,
        "bed": entry.bed,
        "patient_name": entry.patient_name,
        "error": entry.error,
        "twilio_sid": entry.twilio_sid,
    })


@app.post("/alerts/test-sms", summary="Manually trigger a test SMS to the nurse")
async def test_nurse_sms(req: TestAlertRequest) -> JSONResponse:
    """
    Manually dispatch a Twilio SMS to the nurse assigned to the given bed.
    Useful for testing Twilio credentials and verifying the alert flow.
    """
    if alert_service is None:
        return JSONResponse(status_code=503, content={"error": "AlertService not initialized."})

    patient = PATIENTS.get(req.bed_id.upper())
    if patient is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Bed '{req.bed_id}' not found.", "available_beds": list(PATIENTS.keys())},
        )

    if req.reset_cooldown:
        alert_service.reset_cooldown(patient.get("patient_id", req.bed_id), "sms")

    reasons = ["Manual test SMS from VitalGuard API"]
    import asyncio as _asyncio
    entry = await _asyncio.to_thread(
        alert_service.send_nurse_sms,
        patient,
        reasons,
        req.severity,
    )
    return JSONResponse(content={
        "alert_id": entry.alert_id,
        "status": entry.status,
        "channel": entry.channel,
        "recipient_role": entry.recipient_role,
        "bed": entry.bed,
        "patient_name": entry.patient_name,
        "error": entry.error,
        "twilio_sid": entry.twilio_sid,
    })


@app.post("/alerts/doctor-sms", summary="Manually trigger a doctor SMS alert")
async def test_doctor_sms(req: TestAlertRequest) -> JSONResponse:
    """
    Manually dispatch a Twilio SMS to a doctor.
    """
    if alert_service is None:
        return JSONResponse(status_code=503, content={"error": "AlertService not initialized."})

    patient = PATIENTS.get(req.bed_id.upper())
    if patient is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Bed '{req.bed_id}' not found.", "available_beds": list(PATIENTS.keys())},
        )

    if req.reset_cooldown:
        alert_service.reset_cooldown(patient.get("patient_id", req.bed_id), "sms")

    reasons = ["Manual critical nurse alert"]
    doctor_number = req.doctor_number or "9346156382"
    import asyncio as _asyncio
    entry = await _asyncio.to_thread(
        alert_service.send_doctor_sms,
        patient,
        doctor_number,
        reasons,
        req.severity,
    )
    return JSONResponse(content={
        "alert_id": entry.alert_id,
        "status": entry.status,
        "channel": entry.channel,
        "recipient_role": entry.recipient_role,
        "bed": entry.bed,
        "patient_name": entry.patient_name,
        "recipient_number": entry.recipient_number,
        "error": entry.error,
        "twilio_sid": entry.twilio_sid,
    })


@app.get("/alerts/history", summary="Return recent Twilio alert dispatch log")
async def alert_history(limit: int = 50) -> JSONResponse:
    """
    Return the most recent Twilio alert dispatches (calls + SMS).
    Recipient numbers are partially masked for privacy.
    """
    if alert_service is None:
        return JSONResponse(status_code=503, content={"error": "AlertService not initialized."})
    history = alert_service.get_alert_history(limit=min(limit, 200))
    return JSONResponse(content={"total": len(history), "alerts": history})


@app.post("/alerts/reset-cooldown", summary="Reset alert cooldown for a patient")
async def reset_alert_cooldown(req: ResetCooldownRequest) -> JSONResponse:
    """
    Reset the alert cooldown for a specific patient so the next severity
    event triggers a fresh call/SMS immediately. Intended for testing.
    """
    if alert_service is None:
        return JSONResponse(status_code=503, content={"error": "AlertService not initialized."})
    alert_service.reset_cooldown(req.patient_id, req.channel)
    return JSONResponse(content={
        "reset": True,
        "patient_id": req.patient_id,
        "channel": req.channel or "all",
    })


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

            # ── Twilio alert dispatch ──────────────────────────────────
            # Attach live vitals to patient dict for richer alert messages
            if alert_service is not None and score_result.get("severity") != "normal":
                patient_with_vitals = {
                    **patient,
                    "heart_rate": sample["heart_rate"],
                    "spo2": sample["spo2"],
                }
                # Run in background to avoid blocking the stream
                asyncio.create_task(
                    asyncio.to_thread(
                        alert_service.trigger_alert,
                        patient_with_vitals,
                        score_result,
                    )
                )

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
