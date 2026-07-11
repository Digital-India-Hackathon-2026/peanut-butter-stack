from __future__ import annotations

import logging
from typing import Any

from services.config import (
    DRY_RUN,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_CRITICAL_MESSAGING_SID,
    TWILIO_FROM_NUMBER,
)

logger = logging.getLogger("vitalguard.services.notification")


class NotificationService:
    def __init__(self) -> None:
        self._client = self._create_client()
        self._initialized = self._client is not None or DRY_RUN
        self._cooldowns: dict[str, dict[str, float]] = {}

    def _create_client(self) -> Any | None:
        if DRY_RUN:
            logger.warning("[NotificationService] DRY_RUN=true — Twilio notifications will not be sent.")
            return None

        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_FROM_NUMBER:
            logger.warning(
                "[NotificationService] Missing Twilio credentials. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER."
            )
            return None

        try:
            from twilio.rest import Client

            return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except ImportError:
            logger.error("[NotificationService] Twilio package is not installed. Install with 'pip install twilio'.")
            return None
        except Exception as exc:
            logger.error("[NotificationService] Failed to initialize Twilio client: %s", exc)
            return None

    def _ensure_ready(self) -> bool:
        return self._initialized

    def send_sms(
        self,
        to_number: str,
        body: str,
        use_messaging_service: bool = False,
    ) -> dict[str, Any]:
        log_payload = {
            "channel": "sms",
            "recipient_number": to_number,
            "status": "failed",
            "twilio_sid": None,
            "error": None,
        }

        if not to_number:
            log_payload["error"] = "Missing recipient phone number."
            logger.warning("[NotificationService] send_sms skipped: %s", log_payload["error"])
            return log_payload

        if not self._ensure_ready():
            log_payload["status"] = "dry_run"
            logger.info(
                "[NotificationService] DRY_RUN or uninitialized — would send SMS to %s: %s",
                to_number,
                body,
            )
            return log_payload

        try:
            if use_messaging_service and TWILIO_CRITICAL_MESSAGING_SID:
                message = self._client.messages.create(
                    to=to_number,
                    messaging_service_sid=TWILIO_CRITICAL_MESSAGING_SID,
                    body=body,
                )
            else:
                message = self._client.messages.create(
                    to=to_number,
                    from_=TWILIO_FROM_NUMBER,
                    body=body,
                )
            log_payload["status"] = "sent"
            log_payload["twilio_sid"] = getattr(message, "sid", None)
            logger.info(
                "[NotificationService] SMS sent to %s (SID=%s)",
                to_number,
                log_payload["twilio_sid"],
            )
        except Exception as exc:
            log_payload["status"] = "failed"
            log_payload["error"] = str(exc)
            logger.error("[NotificationService] send_sms failed: %s", exc)

        return log_payload

    def make_voice_call(self, to_number: str, twiml: str) -> dict[str, Any]:
        log_payload = {
            "channel": "call",
            "recipient_number": to_number,
            "status": "failed",
            "twilio_sid": None,
            "error": None,
        }

        if not to_number:
            log_payload["error"] = "Missing recipient phone number."
            logger.warning("[NotificationService] make_voice_call skipped: %s", log_payload["error"])
            return log_payload

        if not self._ensure_ready():
            log_payload["status"] = "dry_run"
            logger.info(
                "[NotificationService] DRY_RUN or uninitialized — would place voice call to %s.",
                to_number,
            )
            return log_payload

        try:
            call = self._client.calls.create(
                to=to_number,
                from_=TWILIO_FROM_NUMBER,
                twiml=twiml,
            )
            log_payload["status"] = "sent"
            log_payload["twilio_sid"] = getattr(call, "sid", None)
            logger.info(
                "[NotificationService] Voice call placed to %s (SID=%s)",
                to_number,
                log_payload["twilio_sid"],
            )
        except Exception as exc:
            log_payload["status"] = "failed"
            log_payload["error"] = str(exc)
            logger.error("[NotificationService] make_voice_call failed: %s", exc)

        return log_payload

    def send_critical_alert(
        self,
        recipient_role: str,
        to_number: str,
        body: str,
        twiml: str | None = None,
        use_messaging_service: bool = False,
    ) -> dict[str, Any]:
        if recipient_role == "doctor":
            if twiml is None:
                raise ValueError("Voice call to doctor requires TwiML payload.")
            return self.make_voice_call(to_number=to_number, twiml=twiml)
        return self.send_sms(
            to_number=to_number,
            body=body,
            use_messaging_service=use_messaging_service,
        )

    def reset_cooldown(self, patient_id: str, channel: str | None = None) -> None:
        if channel:
            self._cooldowns.get(patient_id, {}).pop(channel, None)
        else:
            self._cooldowns.pop(patient_id, None)

    def get_client_ready(self) -> bool:
        return self._initialized
