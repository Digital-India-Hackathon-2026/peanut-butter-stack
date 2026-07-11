"""
twilio_alerts
-------------
VitalGuard — Twilio Alert Integration

Provides:
    AlertService — dispatches voice calls to doctors (critical)
                   and SMS messages to nurses (warning + critical).
"""

from twilio_alerts.alert_service import AlertService

__all__ = ["AlertService"]
