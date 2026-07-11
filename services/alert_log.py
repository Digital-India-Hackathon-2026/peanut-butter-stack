from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AlertLogEntry:
    alert_id: str
    timestamp: str
    patient_id: str
    patient_name: str
    bed: str
    severity: str
    channel: str
    recipient_role: str
    recipient_number: str
    reasons: list[str]
    status: str
    error: str | None = None
    twilio_sid: str | None = None
    extra: dict[str, Any] | None = None
