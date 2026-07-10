"""Synthetic VitalGuard test dataset generator.

Creates a JSON dataset for 20 patients across 4 hospital rooms and generates
sample scream audio files for triggered distress events.

Usage:
    python dataset_generator.py --output-dir synthetic_dataset
    python dataset_generator.py --output-dir synthetic_dataset --mongodb-uri "mongodb://..."
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import struct
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

ROOM_NAMES = ["Room 101", "Room 102", "Room 103", "Room 104"]
BED_PREFIX = "BED-"
PATIENT_NAMES = [
    "Aarav Patel",
    "Isha Rao",
    "Rohan Verma",
    "Meera Singh",
    "Kavya Sharma",
    "Vikram Das",
    "Nisha Gupta",
    "Karan Joshi",
    "Ananya Bose",
    "Devika Nair",
    "Sahil Kapoor",
    "Priya Desai",
    "Arjun Iyer",
    "Leela Menon",
    "Manish Chawla",
    "Radha Nair",
    "Naveen Reddy",
    "Sana Khan",
    "Varun Rao",
    "Neha Kulkarni",
]
DIAGNOSES = [
    "Acute myocardial infarction",
    "Atrial fibrillation",
    "Post-operative recovery",
    "Sepsis monitoring",
    "Respiratory distress",
    "Stroke observation",
    "Pneumonia",
    "Hypertensive crisis",
    "COPD exacerbation",
    "Post-fall surveillance",
    "Severe dehydration",
    "Chest infection",
    "Kidney failure",
    "Diabetic ketoacidosis",
    "Cardiac arrhythmia",
    "Post-surgery observation",
    "Pulmonary embolism",
    "High-risk labor monitoring",
    "Traumatic injury",
    "Neurological evaluation",
]
GENDERS = ["Female", "Male", "Non-binary"]
STATUS_WEIGHTS = ["normal"] * 10 + ["warning"] * 6 + ["critical"] * 4
EVENT_LABELS = {
    "normal": ["Stable", "Routine check", "Vitals within range"],
    "warning": ["Irregular rhythm", "SpO₂ dip", "Elevated heart rate"],
    "critical": ["Acute distress", "Fall detected", "Severe hypoxia"],
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(min(value, maximum), minimum)


def pick_severity(status: str) -> str:
    if status == "normal":
        return "normal"
    if status == "warning":
        return random.choice(["warning", "high-risk"])
    return "critical"


def build_room_assignments(patient_count: int, rooms: list[str]) -> list[dict[str, Any]]:
    beds = [f"{BED_PREFIX}{i:02d}" for i in range(1, patient_count + 1)]
    room_size = patient_count // len(rooms)
    return [
        {
            "room": rooms[i],
            "beds": beds[i * room_size : (i + 1) * room_size],
        }
        for i in range(len(rooms))
    ]


def generate_vital_trend(status: str, second: int) -> dict[str, Any]:
    base_hr = random.uniform(62, 88)
    base_spo2 = random.uniform(94.0, 99.0)
    base_rr = random.uniform(14.0, 20.0)
    base_temp = random.uniform(97.8, 99.0)

    if status == "warning":
        if second % 5 == 0:
            base_hr += random.uniform(8, 16)
        if second % 7 == 0:
            base_spo2 -= random.uniform(2.0, 4.0)
    elif status == "critical":
        base_hr += random.uniform(12, 24)
        base_spo2 -= random.uniform(4.0, 10.0)
        base_rr += random.uniform(4.0, 8.0)
        base_temp += random.uniform(0.8, 1.4)

    heart_rate = round(clamp(base_hr + math.sin(second / 2.0) * 3.5, 40, 180), 1)
    spo2 = round(clamp(base_spo2 + math.cos(second / 3.0) * 0.8, 70.0, 100.0), 1)
    respiratory_rate = round(clamp(base_rr + math.sin(second / 3.7) * 1.5, 10.0, 40.0), 1)
    temperature = round(clamp(base_temp + math.cos(second / 4.1) * 0.35, 95.8, 105.0), 1)

    if status == "normal":
        ecg_label = random.choice(["normal", "normal", "minor_irregularity"])
    elif status == "warning":
        ecg_label = random.choice(["normal", "minor_irregularity", "minor_irregularity"])
    else:
        ecg_label = random.choice(["minor_irregularity", "arrhythmia", "arrhythmia"])

    torso_angle = clamp(15.0 + math.sin(second / 2.1) * 3.0 + (5 if status == "critical" and second % 6 == 0 else 0), 10.0, 85.0)
    hip_velocity = round(clamp(0.02 + abs(math.sin(second / 1.7)) * 0.03 + (0.05 if status != "normal" and second % 4 == 0 else 0), 0.0, 0.18), 3)
    motion_state = "stable"
    if status == "warning" and second % 6 == 0:
        motion_state = "restless"
    elif status == "critical" and second % 5 in (0, 2):
        motion_state = "agitated"

    return {
        "second": second,
        "heart_rate": heart_rate,
        "spo2": spo2,
        "respiratory_rate": respiratory_rate,
        "temperature_f": temperature,
        "ecg_label": ecg_label,
        "torso_angle": round(torso_angle, 1),
        "hip_velocity": hip_velocity,
        "motion_state": motion_state,
    }


def build_patient(index: int, room: str, bed: str) -> dict[str, Any]:
    name = PATIENT_NAMES[index]
    status = random.choice(STATUS_WEIGHTS)
    severity = pick_severity(status)
    diagnosis = DIAGNOSES[index]
    age = random.randint(42, 78)
    gender = random.choice(GENDERS)

    vitals_history: list[dict[str, Any]] = []
    alerts: list[dict[str, str]] = []
    audio_asset = None
    event_count = 0

    for second in range(10):
        row = generate_vital_trend(status, second)
        vitals_history.append(row)

        if severity != "normal" and second in (3, 7):
            alert_type = "critical" if severity == "critical" else "warning"
            alerts.append(
                {
                    "second": second,
                    "type": alert_type,
                    "message": random.choice(EVENT_LABELS[status]),
                }
            )
            event_count += 1

    if severity == "critical":
        audio_asset = f"{name.lower().replace(' ', '_')}_scream.wav"

    return {
        "patient_id": f"ICU-{index + 1:02d}",
        "name": name,
        "age": age,
        "gender": gender,
        "room": room,
        "bed": bed,
        "status": status,
        "severity": severity,
        "risk_score": random.randint(28, 92) if status != "normal" else random.randint(8, 25),
        "diagnosis": diagnosis,
        "admission_date": "2026-07-10",
        "assigned_doctor": f"Dr. {random.choice(['Aditi Sharma', 'Arjun Mehta', 'Sushma Iyer', 'Naveen Rao'])}",
        "assigned_nurse": f"Nurse {random.choice(['Priya', 'Sunita', 'Meera', 'Anjali'])}",
        "vitals": vitals_history,
        "alerts": alerts,
        "live_camera": {
            "focus": "torso and hip movement",
            "data": [
                {
                    "second": row["second"],
                    "torso_angle": row["torso_angle"],
                    "hip_velocity": row["hip_velocity"],
                    "motion_state": row["motion_state"],
                }
                for row in vitals_history
            ],
        },
        "audio_asset": audio_asset,
    }


def write_json(dataset: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        json.dump(dataset, stream, indent=2)


def write_scream_wav(path: Path, duration_secs: float = 1.2, sample_rate: int = 22050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    amplitude = 0.7
    num_samples = int(duration_secs * sample_rate)
    envelope = [
        min(1.0, (i / (num_samples * 0.12)) if i < num_samples * 0.12 else 1.0)
        for i in range(num_samples)
    ]

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            carrier = math.sin(2.0 * math.pi * 450.0 * t)
            noise = random.uniform(-1.0, 1.0) * 0.35
            tremolo = 0.8 + 0.2 * math.sin(2.0 * math.pi * 4.0 * t)
            value = amplitude * envelope[i] * tremolo * (carrier + noise)
            sample = int(clamp(value, -1.0, 1.0) * 32767)
            wav_file.writeframes(struct.pack("<h", sample))


def save_to_mongodb(dataset: dict[str, Any], mongo_uri: str) -> None:
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise RuntimeError(
            "pymongo is required to save to MongoDB. Install it with 'pip install pymongo'."
        ) from exc

    client = MongoClient(mongo_uri)
    db = client.get_default_database() or client["vitalguard"]
    collection = db["patient_vitals"]
    documents = dataset["patients"]
    for document in documents:
        document["inserted_at"] = datetime.utcnow().isoformat() + "Z"

    result = collection.insert_many(documents)
    print(f"Inserted {len(result.inserted_ids)} patient documents into MongoDB database '{db.name}'.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a synthetic VitalGuard patient dataset.")
    parser.add_argument("--output-dir", default="synthetic_dataset", help="Directory to write JSON and audio assets.")
    parser.add_argument("--mongodb-uri", default="", help="Optional MongoDB URI to store generated patient documents.")
    parser.add_argument("--patient-count", type=int, default=20, help="Number of synthetic patients to generate.")
    parser.add_argument("--duration-seconds", type=int, default=10, help="Number of seconds of per-second vitals to generate per patient.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rooms = build_room_assignments(args.patient_count, ROOM_NAMES)
    patients: list[dict[str, Any]] = []

    for index in range(args.patient_count):
        room_index = index // (args.patient_count // len(ROOM_NAMES))
        room = ROOM_NAMES[room_index]
        bed = f"{BED_PREFIX}{index + 1:02d}"
        patient = build_patient(index, room, bed)
        if patient["audio_asset"] is not None:
            patient_audio_path = output_dir / "audio" / patient["audio_asset"]
            write_scream_wav(patient_audio_path)
            patient["audio_file_path"] = str(patient_audio_path.relative_to(output_dir))
        patients.append(patient)

    dataset = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "hospital": "VitalGuard Synthetic Test Facility",
        "room_count": len(ROOM_NAMES),
        "patient_count": len(patients),
        "rooms": rooms,
        "patients": patients,
    }

    json_path = output_dir / "vitalguard_synthetic_dataset.json"
    write_json(dataset, json_path)
    print(f"Written synthetic dataset to {json_path}")

    if args.mongodb_uri:
        save_to_mongodb(dataset, args.mongodb_uri)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
