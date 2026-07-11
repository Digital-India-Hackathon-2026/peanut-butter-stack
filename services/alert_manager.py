from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any

from services.alert_log import AlertLogEntry
from services.config import TWILIO_VOICE_ESCALATION_SECONDS
from services.database import PatientRepository
from services.notification_service import NotificationService
from twilio_alerts.twiml_voice import build_doctor_twiml

logger = logging.getLogger("vitalguard.services.alert_manager")


class AlertManager:
    def __init__(
        self,
        notification_service: NotificationService | None = None,
        patient_repository: PatientRepository | None = None,
    ) -> None:
        self.notification_service = notification_service or NotificationService()
        self.patient_repository = patient_repository or PatientRepository()
        self._pending_escalations: dict[str, threading.Timer] = {}

    def _new_alert_id(self) -> str:
        return f"ALT-{uuid.uuid4().hex[:8].upper()}"

    def _now(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    def _merge_patient_contacts(self, patient: dict[str, Any]) -> dict[str, Any]:
        patient_id = patient.get("patient_id") or patient.get("bed")
        bed = patient.get("bed")
        record = self.patient_repository.find_patient(patient_id=patient_id, bed=bed)
        merged = {
            "patient_id": patient_id or "UNKNOWN",
            "name": patient.get("name", "Unknown Patient"),
            "bed": bed or "UNKNOWN",
            "diagnosis": patient.get("diagnosis", "Unknown Diagnosis"),
            "assigned_doctor": patient.get("assigned_doctor", "Unknown Doctor"),
            "assigned_nurse": patient.get("assigned_nurse", "Unknown Nurse"),
            "doctor_phone": "",
            "nurse_phone": "",
            "ward": patient.get("ward", ""),
            "risk_score": patient.get("risk_score"),
        }
        if record:
            merged.update({
                "assigned_doctor": record.get("assigned_doctor", merged["assigned_doctor"]),
                "assigned_nurse": record.get("assigned_nurse", merged["assigned_nurse"]),
                "doctor_phone": record.get("doctor_phone", merged["doctor_phone"]),
                "nurse_phone": record.get("nurse_phone", merged["nurse_phone"]),
                "ward": record.get("ward", merged["ward"]),
            })
        merged["doctor_phone"] = merged["doctor_phone"] or patient.get("doctor_phone", "")
        merged["nurse_phone"] = merged["nurse_phone"] or patient.get("nurse_phone", "")
        return merged

    def _format_sms_body(
        self,
        patient: dict[str, Any],
        reasons: list[str],
        score: int | None = None,
    ) -> str:
        lines = ["🚨 VitalGuard Critical Alert", "", "Patient:", patient["name"], "", "Bed:", patient["bed"], "", "Reason:"]
        lines.extend([f"• {reason}" for reason in reasons])
        if score is not None:
            lines.extend(["", "Risk Score:", f"{score}%"])
        lines.extend(["", "Please attend immediately."])
        return "\n".join(lines)

    def _build_voice_twiml(self, patient: dict[str, Any], reasons: list[str]) -> str:
        return build_doctor_twiml(
            patient_name=patient["name"],
            bed=patient["bed"],
            diagnosis=patient["diagnosis"],
            severity="critical",
            reasons=reasons,
            heart_rate=patient.get("heart_rate"),
            spo2=patient.get("spo2"),
        )

    def _log_entry(
        self,
        alert_id: str,
        patient: dict[str, Any],
        severity: str,
        channel: str,
        recipient_role: str,
        recipient_number: str,
        reasons: list[str],
        status: str,
        error: str | None = None,
        twilio_sid: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AlertLogEntry:
        return AlertLogEntry(
            alert_id=alert_id,
            timestamp=self._now(),
            patient_id=patient.get("patient_id", patient.get("bed", "UNKNOWN")),
            patient_name=patient.get("name", "Unknown Patient"),
            bed=patient.get("bed", "UNKNOWN"),
            severity=severity,
            channel=channel,
            recipient_role=recipient_role,
            recipient_number=recipient_number,
            reasons=reasons,
            status=status,
            error=error,
            twilio_sid=twilio_sid,
            extra=extra,
        )

    def _dispatch_sms(
        self,
        patient: dict[str, Any],
        recipient_role: str,
        phone: str,
        reasons: list[str],
        score: int | None,
    ) -> AlertLogEntry:
        alert_id = self._new_alert_id()
        body = self._format_sms_body(patient=patient, reasons=reasons, score=score)
        result = self.notification_service.send_sms(
            to_number=phone,
            body=body,
            use_messaging_service=True,
        )
        return self._log_entry(
            alert_id=alert_id,
            patient=patient,
            severity="critical",
            channel="sms",
            recipient_role=recipient_role,
            recipient_number=phone,
            reasons=reasons,
            status=result.get("status", "failed"),
            error=result.get("error"),
            twilio_sid=result.get("twilio_sid"),
            extra={"body": body},
        )

    def _dispatch_voice_call(
        self,
        patient: dict[str, Any],
        phone: str,
        reasons: list[str],
    ) -> AlertLogEntry:
        alert_id = self._new_alert_id()
        twiml = self._build_voice_twiml(patient=patient, reasons=reasons)
        result = self.notification_service.make_voice_call(
            to_number=phone,
            twiml=twiml,
        )
        return self._log_entry(
            alert_id=alert_id,
            patient=patient,
            severity="critical",
            channel="call",
            recipient_role="doctor",
            recipient_number=phone,
            reasons=reasons,
            status=result.get("status", "failed"),
            error=result.get("error"),
            twilio_sid=result.get("twilio_sid"),
            extra={"twiml": twiml},
        )

    def _schedule_escalation(
        self,
        patient: dict[str, Any],
        phone: str,
        reasons: list[str],
    ) -> None:
        if TWILIO_VOICE_ESCALATION_SECONDS <= 0:
            return

        alert_key = str(uuid.uuid4())

        def escalate() -> None:
            if alert_key not in self._pending_escalations:
                return
            logger.info(
                "[AlertManager] Escalating critical alert for %s after %s seconds.",
                patient.get("patient_id", patient.get("bed", "UNKNOWN")),
                TWILIO_VOICE_ESCALATION_SECONDS,
            )
            self._dispatch_voice_call(patient=patient, phone=phone, reasons=reasons)
            self._pending_escalations.pop(alert_key, None)

        timer = threading.Timer(TWILIO_VOICE_ESCALATION_SECONDS, escalate)
        self._pending_escalations[alert_key] = timer
        timer.daemon = True
        timer.start()

    def acknowledge_alert(self, alert_key: str) -> bool:
        timer = self._pending_escalations.pop(alert_key, None)
        if timer is None:
            return False
        timer.cancel()
        logger.info("[AlertManager] Alert acknowledgment received, escalation cancelled (%s).", alert_key)
        return True

    def process_alert(
        self,
        patient: dict[str, Any],
        severity: str,
        score: int | None,
        reasons: list[str],
    ) -> list[AlertLogEntry]:
        if severity.lower() != "critical":
            logger.debug(
                "[AlertManager] Skipping Twilio dispatch for severity '%s'.", severity
            )
            return []

        patient_context = self._merge_patient_contacts(patient)
        nurse_phone = patient_context.get("nurse_phone", "")
        doctor_phone = patient_context.get("doctor_phone", "")
        entries: list[AlertLogEntry] = []

        if nurse_phone:
            entries.append(
                self._dispatch_sms(
                    patient=patient_context,
                    recipient_role="nurse",
                    phone=nurse_phone,
                    reasons=reasons,
                    score=score,
                )
            )
        else:
            logger.warning(
                "[AlertManager] Critical alert for %s missing nurse_phone; SMS skipped.",
                patient_context.get("patient_id"),
            )

        if doctor_phone:
            entries.append(
                self._dispatch_sms(
                    patient=patient_context,
                    recipient_role="doctor",
                    phone=doctor_phone,
                    reasons=reasons,
                    score=score,
                )
            )
            self._schedule_escalation(
                patient=patient_context,
                phone=doctor_phone,
                reasons=reasons,
            )
        else:
            logger.warning(
                "[AlertManager] Critical alert for %s missing doctor_phone; doctor SMS/voice skipped.",
                patient_context.get("patient_id"),
            )

        return entries
