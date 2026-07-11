"""
severity_scorer.py
------------------
VitalGuard — Vitals Severity Scoring

Computes a composite severity score from heart rate, SpO2, and ECG label.
All thresholds are configurable constants at the top of this file.
"""

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

# Heart-rate thresholds (bpm)
HR_NORMAL_LOW: int = 60      # lower bound of normal range (inclusive)
HR_NORMAL_HIGH: int = 100    # upper bound of normal range (inclusive)
HR_WARN_LOW: int = 50        # lower bound of warning range (inclusive)
HR_WARN_HIGH: int = 130      # upper bound of warning range (inclusive)
# score 0 : HR_NORMAL_LOW  <= hr <= HR_NORMAL_HIGH
# score 1 : HR_WARN_LOW    <= hr <  HR_NORMAL_LOW   OR  HR_NORMAL_HIGH < hr <= HR_WARN_HIGH
# score 2 : hr < HR_WARN_LOW   OR  hr > HR_WARN_HIGH

# SpO2 thresholds (%)
SPO2_NORMAL: float = 95.0    # >= this → score 0
SPO2_WARN: float = 90.0      # >= this → score 1  (90–94.9%)
# < SPO2_WARN → score 2

# ECG label constants (must match labels emitted by VitalsSimulator)
ECG_LABEL_NORMAL: str = "normal"
ECG_LABEL_MINOR: str = "minor_irregularity"
ECG_LABEL_ARRHYTHMIA: str = "arrhythmia"

# Severity thresholds (total score)
SEVERITY_NORMAL_MAX: int = 1   # total 0–1 → "normal"
SEVERITY_WARNING_MAX: int = 3  # total 2–3 → "warning"
# total >= 4 → "critical"

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _score_heart_rate(heart_rate: float) -> tuple[int, str | None]:
    """Return (score, reason_string_or_None) for the given heart rate."""
    if HR_NORMAL_LOW <= heart_rate <= HR_NORMAL_HIGH:
        return 0, None
    if HR_WARN_LOW <= heart_rate < HR_NORMAL_LOW:
        return 1, f"Heart rate low ({heart_rate:.0f} bpm)"
    if HR_NORMAL_HIGH < heart_rate <= HR_WARN_HIGH:
        return 1, f"Heart rate elevated ({heart_rate:.0f} bpm)"
    if heart_rate < HR_WARN_LOW:
        return 2, f"Heart rate critically low ({heart_rate:.0f} bpm)"
    # heart_rate > HR_WARN_HIGH
    return 2, f"Heart rate critically high ({heart_rate:.0f} bpm)"


def _score_spo2(spo2: float) -> tuple[int, str | None]:
    """Return (score, reason_string_or_None) for the given SpO2 value."""
    if spo2 >= SPO2_NORMAL:
        return 0, None
    if spo2 >= SPO2_WARN:
        return 1, f"SpO2 low ({spo2:.1f}%)"
    return 2, f"SpO2 critically low ({spo2:.1f}%)"


def _score_ecg(ecg_label: str) -> tuple[int, str | None]:
    """Return (score, reason_string_or_None) for the given ECG label."""
    label = ecg_label.lower().strip()
    if label == ECG_LABEL_NORMAL:
        return 0, None
    if label == ECG_LABEL_MINOR:
        return 1, "ECG minor irregularity detected"
    if label == ECG_LABEL_ARRHYTHMIA:
        return 2, "ECG arrhythmia detected"
    # Unknown label — treat as minor irregularity (fail-safe)
    return 1, f"ECG unknown label '{ecg_label}'"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_vitals(heart_rate: float, spo2: float, ecg_label: str) -> dict:
    """
    Compute a composite severity score from the three vital signs.

    Parameters
    ----------
    heart_rate : float
        Heart rate in beats per minute.
    spo2 : float
        Blood oxygen saturation percentage (0–100).
    ecg_label : str
        ECG rhythm label: one of "normal", "minor_irregularity", "arrhythmia".

    Returns
    -------
    dict with keys:
        "severity" : str   — "normal" | "warning" | "critical"
        "score"    : int   — raw composite score (0–6)
        "reasons"  : list  — human-readable strings for each triggered vital
    """
    hr_score, hr_reason = _score_heart_rate(heart_rate)
    spo2_score, spo2_reason = _score_spo2(spo2)
    ecg_score, ecg_reason = _score_ecg(ecg_label)

    total_score = hr_score + spo2_score + ecg_score

    if total_score <= SEVERITY_NORMAL_MAX:
        severity = "normal"
    elif total_score <= SEVERITY_WARNING_MAX:
        severity = "warning"
    else:
        severity = "critical"

    reasons = [r for r in (hr_reason, spo2_reason, ecg_reason) if r is not None]

    return {
        "severity": severity,
        "score": total_score,
        "reasons": reasons,
    }
