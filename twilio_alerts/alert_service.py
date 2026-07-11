"""
alert_service.py
----------------
VitalGuard — Twilio Alert Service

Dispatches:
  • Voice calls  → doctors   (severity: "critical")
  • SMS messages → nurses    (severity: "warning" OR "critical")
    — Critical SMS is routed through a Twilio Messaging Service for
      higher deliverability and sender reputation management.
    — Warning SMS uses the standard Twilio from-number.

Environment variables required:
    TWILIO_ACCOUNT_SID             — Twilio Account SID
    TWILIO_AUTH_TOKEN              — Twilio Auth Token
    TWILIO_FROM_NUMBER             — Twilio phone number (e.g. +1XXXXXXXXXX)

Optional:
    TWILIO_CRITICAL_MESSAGING_SID  — Messaging Service SID (MG...) used for
                                     critical-severity SMS to nurses.
                                     Defaults to MGa1bdc49eb0a438973a8e2f09ed6f0fd3.
    TWILIO_ALERT_COOLDOWN_SECONDS  — seconds between repeated alerts for the
                                     same patient (default: 300 = 5 minutes)
    TWILIO_DRY_RUN                 — if "true", log alerts but don't actually
                                     call Twilio APIs (useful for dev/testing)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("vitalguard.twilio_alerts")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER: str = os.environ.get(
    "TWILIO_FROM_NUMBER",
    os.environ.get("TWILIO_PHONE_NUMBER", ""),
)

# Messaging Service SID used for CRITICAL-severity SMS to nurses.
# Using a Messaging Service gives higher deliverability, opt-out compliance,
# and better sender reputation than a raw phone number.
TWILIO_CRITICAL_MESSAGING_SID: str = os.environ.get(
    "TWILIO_CRITICAL_MESSAGING_SID",
    "MGa1bdc49eb0a438973a8e2f09ed6f0fd3",  # VitalGuard critical-alert messaging service
)

ALERT_COOLDOWN_SECONDS: int = int(os.environ.get("TWILIO_ALERT_COOLDOWN_SECONDS", "300"))
DRY_RUN: bool = os.environ.get("TWILIO_DRY_RUN", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Alert log entry
# ---------------------------------------------------------------------------


@dataclass
class AlertLogEntry:
    """A single dispatched alert record."""

    alert_id: str
    timestamp: str
    patient_id: str
    patient_name: str
    bed: str
    severity: str
    channel: str          # "call" | "sms"
    recipient_role: str   # "doctor" | "nurse"
    recipient_number: str
    reasons: list[str]
    status: str           # "sent" | "failed" | "dry_run" | "cooldown"
    error: str | None = None
    twilio_sid: str | None = None


# ---------------------------------------------------------------------------
# AlertService
# ---------------------------------------------------------------------------


class AlertService:
    """
    Manages Twilio voice call and SMS dispatch for VitalGuard alerts.

    Usage
    -----
    service = AlertService()
    service.trigger_alert(patient_dict, score_result_dict)

    The patient_dict should contain:
        name, bed, diagnosis, doctor_phone, nurse_phone
        (and optionally: patient_id, heart_rate, spo2)

    The score_result_dict is the output of score_vitals():
        severity, score, reasons
    """

    def __init__(self) -> None:
        self._cooldowns: dict[str, dict[str, float]] = {}
        # { patient_id: { "call": last_sent_ts, "sms": last_sent_ts } }
        self._alert_log: list[AlertLogEntry] = []
        self._alert_counter: int = 0
        self._client = None
        self._initialized = False
        self._init_twilio()

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def _init_twilio(self) -> None:
        """Lazy-initialize the Twilio REST client."""
        if DRY_RUN:
            logger.warning(
                "[TwilioAlerts] DRY_RUN=true — alerts will be logged but NOT sent."
            )
            self._initialized = True
            return

        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_FROM_NUMBER:
            logger.warning(
                "[TwilioAlerts] Missing Twilio credentials. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER. "
                "Running in dry-run mode."
            )
            self._initialized = False
            return

        try:
            from twilio.rest import Client  # type: ignore
            self._client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            self._initialized = True
            logger.info("[TwilioAlerts] Twilio client initialized successfully.")
        except ImportError:
            logger.error(
                "[TwilioAlerts] 'twilio' package not installed. "
                "Run: pip install twilio"
            )
            self._initialized = False
        except Exception as exc:
            logger.error(f"[TwilioAlerts] Failed to initialize Twilio client: {exc}")
            self._initialized = False

    # ------------------------------------------------------------------
    # Cooldown helpers
    # ------------------------------------------------------------------

    def _is_on_cooldown(self, patient_id: str, channel: str) -> bool:
        """Return True if this patient+channel is still within the cooldown window."""
        last_sent = self._cooldowns.get(patient_id, {}).get(channel, 0.0)
        return (time.time() - last_sent) < ALERT_COOLDOWN_SECONDS

    def _record_sent(self, patient_id: str, channel: str) -> None:
        """Mark a channel as just dispatched for a patient."""
        if patient_id not in self._cooldowns:
            self._cooldowns[patient_id] = {}
        self._cooldowns[patient_id][channel] = time.time()

    def _reset_cooldown(self, patient_id: str, channel: str | None = None) -> None:
        """Reset cooldown for testing or manual override."""
        if channel:
            self._cooldowns.get(patient_id, {}).pop(channel, None)
        else:
            self._cooldowns.pop(patient_id, None)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _new_alert_id(self) -> str:
        self._alert_counter += 1
        return f"ALT-{self._alert_counter:04d}"

    def _log_entry(self, **kwargs: Any) -> AlertLogEntry:
        entry = AlertLogEntry(**kwargs)
        self._alert_log.append(entry)
        # Keep only the last 500 entries
        if len(self._alert_log) > 500:
            self._alert_log = self._alert_log[-500:]
        return entry

    # ------------------------------------------------------------------
    # Public API — trigger alerts
    # ------------------------------------------------------------------

    def trigger_alert(self, patient: dict, score_result: dict) -> list[AlertLogEntry]:
        """
        Main entry point called from the WebSocket vitals stream.

        Dispatches:
          - Voice call to doctor  if severity == "critical"
          - SMS to nurse          if severity == "warning" or "critical"

        Parameters
        ----------
        patient : dict
            Patient info dict (from PATIENTS registry or synthetic data).
            Must contain: name, bed, diagnosis, doctor_phone, nurse_phone
        score_result : dict
            Output of score_vitals(): {severity, score, reasons}

        Returns
        -------
        list[AlertLogEntry]
            Log entries for each dispatched (or skipped) alert.
        """
        severity = score_result.get("severity", "normal")
        reasons = score_result.get("reasons", [])
        entries: list[AlertLogEntry] = []

        if severity == "normal":
            return entries

        # Voice call to doctor — critical only
        if severity == "critical":
            entry = self.send_doctor_call(
                patient=patient,
                reasons=reasons,
                severity=severity,
            )
            entries.append(entry)

        # SMS to nurse — warning + critical
        entry = self.send_nurse_sms(
            patient=patient,
            reasons=reasons,
            severity=severity,
        )
        entries.append(entry)

        return entries

    def send_doctor_call(
        self,
        patient: dict,
        reasons: list[str],
        severity: str = "critical",
    ) -> AlertLogEntry:
        """
        Trigger a voice call to the doctor assigned to the patient.

        Uses TwiML <Say> to read out the alert details.
        """
        from twilio_alerts.twiml_voice import build_doctor_twiml

        patient_id = patient.get("patient_id", patient.get("bed", "UNKNOWN"))
        patient_name = patient.get("name", "Unknown Patient")
        bed = patient.get("bed", "N/A")
        diagnosis = patient.get("diagnosis", "Unknown Diagnosis")
        doctor_phone = patient.get("doctor_phone", "")
        heart_rate = patient.get("heart_rate")
        spo2 = patient.get("spo2")

        alert_id = self._new_alert_id()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not doctor_phone:
            logger.warning(f"[TwilioAlerts] {alert_id}: No doctor_phone for {patient_id}, skipping call.")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="call",
                recipient_role="doctor", recipient_number="",
                reasons=reasons, status="failed",
                error="No doctor_phone configured",
            )

        # Cooldown check
        if self._is_on_cooldown(patient_id, "call"):
            remaining = int(
                ALERT_COOLDOWN_SECONDS
                - (time.time() - self._cooldowns[patient_id]["call"])
            )
            logger.debug(
                f"[TwilioAlerts] {alert_id}: Call to doctor for {patient_id} "
                f"on cooldown ({remaining}s remaining)."
            )
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="call",
                recipient_role="doctor", recipient_number=doctor_phone,
                reasons=reasons, status="cooldown",
            )

        twiml = build_doctor_twiml(
            patient_name=patient_name,
            bed=bed,
            diagnosis=diagnosis,
            severity=severity,
            reasons=reasons,
            heart_rate=heart_rate,
            spo2=spo2,
        )

        if DRY_RUN or not self._initialized:
            mode = "dry_run" if DRY_RUN else "failed"
            logger.info(
                f"[TwilioAlerts] [{mode.upper()}] Would call {doctor_phone} "
                f"for {patient_name} ({bed}) — {severity.upper()}: {reasons}"
            )
            self._record_sent(patient_id, "call")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="call",
                recipient_role="doctor", recipient_number=doctor_phone,
                reasons=reasons, status=mode,
            )

        # Real Twilio call
        try:
            call = self._client.calls.create(
                to=doctor_phone,
                from_=TWILIO_FROM_NUMBER,
                twiml=twiml,
            )
            self._record_sent(patient_id, "call")
            logger.info(
                f"[TwilioAlerts] {alert_id}: Voice call dispatched → {doctor_phone} "
                f"(SID: {call.sid}) | {patient_name} | {severity.upper()}"
            )
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="call",
                recipient_role="doctor", recipient_number=doctor_phone,
                reasons=reasons, status="sent", twilio_sid=call.sid,
            )
        except Exception as exc:
            logger.error(f"[TwilioAlerts] {alert_id}: Call failed — {exc}")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="call",
                recipient_role="doctor", recipient_number=doctor_phone,
                reasons=reasons, status="failed", error=str(exc),
            )

    def send_doctor_sms(
        self,
        patient: dict,
        to_number: str,
        reasons: list[str],
        severity: str = "critical",
    ) -> AlertLogEntry:
        """
        Send a critical SMS alert directly to the doctor.
        """
        patient_id = patient.get("patient_id", patient.get("bed", "UNKNOWN"))
        patient_name = patient.get("name", "Unknown Patient")
        bed = patient.get("bed", "N/A")
        diagnosis = patient.get("diagnosis", "Unknown Diagnosis")

        alert_id = self._new_alert_id()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = self._format_sms_body(patient=patient, reasons=reasons, score=None)

        if not to_number:
            logger.warning(f"[TwilioAlerts] {alert_id}: Missing doctor phone number, skipping SMS.")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="doctor", recipient_number="",
                reasons=reasons, status="failed",
                error="Missing doctor phone number",
            )

        if DRY_RUN or not self._initialized:
            mode = "dry_run" if DRY_RUN else "failed"
            logger.info(
                f"[TwilioAlerts] [{mode.upper()}] Would SMS {to_number} "
                f"for {patient_name} ({bed}) — {severity.upper()}: {reasons}"
            )
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="doctor", recipient_number=to_number,
                reasons=reasons, status=mode,
            )

        result = self.notification_service.send_sms(
            to_number=to_number,
            body=body,
            use_messaging_service=True,
        )

        return self._log_entry(
            alert_id=alert_id, timestamp=ts,
            patient_id=patient_id, patient_name=patient_name,
            bed=bed, severity=severity, channel="sms",
            recipient_role="doctor", recipient_number=to_number,
            reasons=reasons, status=result.get("status", "failed"),
            error=result.get("error"), twilio_sid=result.get("twilio_sid"),
        )

    def send_nurse_sms(
        self,
        patient: dict,
        reasons: list[str],
        severity: str = "warning",
    ) -> AlertLogEntry:
        """
        Send an SMS alert to the nurse assigned to the patient.

        The SMS body includes patient name, bed, severity, and trigger reasons.
        """
        patient_id = patient.get("patient_id", patient.get("bed", "UNKNOWN"))
        patient_name = patient.get("name", "Unknown Patient")
        bed = patient.get("bed", "N/A")
        diagnosis = patient.get("diagnosis", "Unknown Diagnosis")
        nurse_phone = patient.get("nurse_phone", "")
        heart_rate = patient.get("heart_rate")
        spo2 = patient.get("spo2")

        alert_id = self._new_alert_id()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not nurse_phone:
            logger.warning(f"[TwilioAlerts] {alert_id}: No nurse_phone for {patient_id}, skipping SMS.")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="nurse", recipient_number="",
                reasons=reasons, status="failed",
                error="No nurse_phone configured",
            )

        # Cooldown check
        if self._is_on_cooldown(patient_id, "sms"):
            remaining = int(
                ALERT_COOLDOWN_SECONDS
                - (time.time() - self._cooldowns[patient_id]["sms"])
            )
            logger.debug(
                f"[TwilioAlerts] {alert_id}: SMS to nurse for {patient_id} "
                f"on cooldown ({remaining}s remaining)."
            )
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="nurse", recipient_number=nurse_phone,
                reasons=reasons, status="cooldown",
            )

        # Build SMS body
        severity_tag = "🚨 CRITICAL" if severity == "critical" else "⚠️ WARNING"
        vitals_line = ""
        if heart_rate is not None:
            vitals_line += f"HR: {int(round(heart_rate))} bpm"
        if spo2 is not None:
            vitals_line += f" | SpO2: {spo2:.1f}%"

        body_lines = [
            f"{severity_tag} — VitalGuard Alert",
            f"Patient: {patient_name}",
            f"Bed: {bed} | Dx: {diagnosis}",
        ]
        if vitals_line:
            body_lines.append(f"Vitals: {vitals_line}")
        if reasons:
            body_lines.append("Triggers: " + "; ".join(reasons))
        body_lines.append("⟶ Check VitalGuard dashboard immediately.")

        sms_body = "\n".join(body_lines)

        if DRY_RUN or not self._initialized:
            mode = "dry_run" if DRY_RUN else "failed"
            logger.info(
                f"[TwilioAlerts] [{mode.upper()}] Would SMS {nurse_phone} "
                f"for {patient_name} ({bed}) — {severity.upper()}\n{sms_body}"
            )
            self._record_sent(patient_id, "sms")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="nurse", recipient_number=nurse_phone,
                reasons=reasons, status=mode,
            )

        # Real Twilio SMS
        # ── Routing logic ────────────────────────────────────────────────
        # CRITICAL  → Messaging Service SID (higher priority / deliverability)
        # WARNING   → standard from-number
        use_messaging_service = severity == "critical" and TWILIO_CRITICAL_MESSAGING_SID
        try:
            if use_messaging_service:
                message = self._client.messages.create(
                    to=nurse_phone,
                    messaging_service_sid=TWILIO_CRITICAL_MESSAGING_SID,
                    body=sms_body,
                )
                logger.info(
                    f"[TwilioAlerts] {alert_id}: CRITICAL SMS via Messaging Service "
                    f"({TWILIO_CRITICAL_MESSAGING_SID}) → {nurse_phone} "
                    f"(SID: {message.sid}) | {patient_name}"
                )
            else:
                message = self._client.messages.create(
                    to=nurse_phone,
                    from_=TWILIO_FROM_NUMBER,
                    body=sms_body,
                )
                logger.info(
                    f"[TwilioAlerts] {alert_id}: WARNING SMS via from-number "
                    f"→ {nurse_phone} (SID: {message.sid}) | {patient_name}"
                )
            self._record_sent(patient_id, "sms")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="nurse", recipient_number=nurse_phone,
                reasons=reasons, status="sent", twilio_sid=message.sid,
            )
        except Exception as exc:
            logger.error(f"[TwilioAlerts] {alert_id}: SMS failed — {exc}")
            return self._log_entry(
                alert_id=alert_id, timestamp=ts,
                patient_id=patient_id, patient_name=patient_name,
                bed=bed, severity=severity, channel="sms",
                recipient_role="nurse", recipient_number=nurse_phone,
                reasons=reasons, status="failed", error=str(exc),
            )

    # ------------------------------------------------------------------
    # Alert history
    # ------------------------------------------------------------------

    def get_alert_history(self, limit: int = 50) -> list[dict]:
        """Return the most recent alert log entries as dicts."""
        entries = self._alert_log[-limit:][::-1]  # newest first
        return [
            {
                "alert_id": e.alert_id,
                "timestamp": e.timestamp,
                "patient_id": e.patient_id,
                "patient_name": e.patient_name,
                "bed": e.bed,
                "severity": e.severity,
                "channel": e.channel,
                "recipient_role": e.recipient_role,
                "recipient_number": _mask_phone(e.recipient_number),
                "reasons": e.reasons,
                "status": e.status,
                "error": e.error,
                "twilio_sid": e.twilio_sid,
            }
            for e in entries
        ]

    def reset_cooldown(self, patient_id: str, channel: str | None = None) -> None:
        """Public method to reset cooldown (for test endpoints)."""
        self._reset_cooldown(patient_id, channel)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_phone(phone: str) -> str:
    """Partially mask a phone number for safe logging/display (e.g. +1XXXXX5678)."""
    if len(phone) < 7:
        return phone
    return phone[:3] + "X" * (len(phone) - 7) + phone[-4:]
