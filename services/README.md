# VitalGuard Notification Services

This folder contains the new Twilio notification service modules for VitalGuard.

## Components

- `config.py` — Loads Twilio and database configuration from environment variables.
- `database.py` — Provides a patient repository that reads patient contact information from MongoDB.
- `notification_service.py` — Lightweight Twilio wrapper with `send_sms`, `make_voice_call`, and `send_critical_alert`.
- `alert_manager.py` — Handles critical alert validation, staff lookup, dashboard synchronization support, and escalation scheduling.

## Notes

- Twilio credentials are read from environment variables.
- The notification layer is intentionally independent of monitoring modules.
- Existing monitoring modules should not call Twilio directly.
- The Alert Manager is ready for integration with the event correlation engine.
