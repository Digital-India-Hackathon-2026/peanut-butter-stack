"""
twiml_voice.py
--------------
VitalGuard — TwiML Voice Script Generator

Generates TwiML XML for Twilio Programmable Voice calls to doctors.
The <Say> verb reads out a clear, structured alert message.
"""

from __future__ import annotations


def build_doctor_twiml(
    patient_name: str,
    bed: str,
    diagnosis: str,
    severity: str,
    reasons: list[str],
    heart_rate: float | None = None,
    spo2: float | None = None,
) -> str:
    """
    Build a TwiML response XML string for a doctor voice call alert.

    Parameters
    ----------
    patient_name : str
        Full name of the patient (e.g. "Arjun Mehta").
    bed : str
        Bed identifier (e.g. "BED-01").
    diagnosis : str
        Primary diagnosis (e.g. "Acute Myocardial Infarction").
    severity : str
        Severity level: "warning" or "critical".
    reasons : list[str]
        List of triggered alert reasons from the severity scorer.
    heart_rate : float | None
        Latest heart rate in bpm (optional, included in message if provided).
    spo2 : float | None
        Latest SpO2 % (optional, included in message if provided).

    Returns
    -------
    str
        TwiML XML string ready to serve from a URL or pass as inline TwiML.
    """
    severity_word = "CRITICAL" if severity == "critical" else "WARNING"
    pause = '<Break time="600ms"/>'

    # Build reasons text
    reasons_text = ""
    if reasons:
        reasons_text = "Triggered alerts are: " + ". ".join(reasons) + ". "

    # Build vitals text
    vitals_text = ""
    if heart_rate is not None:
        vitals_text += f"Heart rate is {int(round(heart_rate))} beats per minute. "
    if spo2 is not None:
        vitals_text += f"Blood oxygen saturation is {spo2:.1f} percent. "

    message = (
        f"This is an automated alert from VitalGuard hospital monitoring system. "
        f"{pause}"
        f"{severity_word} alert for patient {patient_name}, "
        f"located at {bed}, diagnosed with {diagnosis}. "
        f"{pause}"
        f"{vitals_text}"
        f"{reasons_text}"
        f"{pause}"
        f"Please respond immediately. This message will repeat once. "
        f"{pause}"
        f"This is an automated alert from VitalGuard. "
        f"{severity_word} alert for patient {patient_name} at {bed}. "
        f"Please check the VitalGuard dashboard for full details."
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f'  <Say voice="Polly.Joanna" language="en-US">{message}</Say>\n'
        "  <Pause length=\"1\"/>\n"
        "</Response>"
    )
    return twiml
