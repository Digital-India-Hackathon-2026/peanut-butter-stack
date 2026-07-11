from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_CRITICAL_MESSAGING_SID = os.getenv("TWILIO_CRITICAL_MESSAGING_SID", "")
TWILIO_ALERT_COOLDOWN_SECONDS = int(os.getenv("TWILIO_ALERT_COOLDOWN_SECONDS", "60"))
TWILIO_VOICE_ESCALATION_SECONDS = int(os.getenv("TWILIO_VOICE_ESCALATION_SECONDS", "60"))
TWILIO_DRY_RUN = os.getenv("TWILIO_DRY_RUN", "false").lower() == "true"
MONGODB_URL = os.getenv("MONGODB_URL", "")
