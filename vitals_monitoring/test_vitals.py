"""
test_vitals.py
--------------
VitalGuard — Standalone Console Test Script

Run this script to verify severity scoring logic without FastAPI or WebSocket.
It instantiates VitalsSimulator directly, replays the ECG for a configurable
duration, prints a formatted table of scores to the console, and at t=10 s
automatically triggers the abnormal segment so you can see score changes.

Usage
-----
    cd vitals_monitoring
    python test_vitals.py

    # Use a different record:
    VITALGUARD_RECORD_PATH=data/mitdb/108 python test_vitals.py

    # Run for a custom duration (seconds):
    VITALGUARD_DURATION=60 python test_vitals.py

No external network calls are made; the record files must already be present
under vitals_monitoring/data/.  See README.md for download instructions.
"""

from __future__ import annotations

import asyncio
import os
from collections import Counter
from pathlib import Path

from vitals_monitoring.severity_scorer import score_vitals
from vitals_monitoring.vitals_simulator import VitalsSimulator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RECORD_PATH: str = os.environ.get(
    "VITALGUARD_RECORD_PATH",
    str(Path(__file__).parent / "data" / "100"),
)

# Total playback duration in seconds
DURATION: float = float(os.environ.get("VITALGUARD_DURATION", "30"))

# At this elapsed time, trigger_abnormal_segment() is called automatically
TRIGGER_AT: float = float(os.environ.get("VITALGUARD_TRIGGER_AT", "10"))

# Injected HR / SpO2 value lists (same as used by main.py for consistency)
HR_VALUES: list[float] = [72, 73, 74, 75, 74, 73, 72, 71, 70, 71, 72]
SPO2_VALUES: list[float] = [98.0, 97.5, 98.0, 98.5, 99.0, 98.0, 97.0]

# ---------------------------------------------------------------------------
# ANSI colour codes for terminal output
# ---------------------------------------------------------------------------
_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_GREY = "\033[90m"

SEVERITY_COLOUR = {
    "normal": _GREEN,
    "warning": _YELLOW,
    "critical": _RED,
}


def _fmt_severity(severity: str, score: int) -> str:
    colour = SEVERITY_COLOUR.get(severity, _RESET)
    label = severity.upper().ljust(8)
    return f"{colour}{_BOLD}{label}{_RESET}{_GREY}(score={score}){_RESET}"


# ---------------------------------------------------------------------------
# Main test coroutine
# ---------------------------------------------------------------------------


async def run_test() -> None:
    print(f"\n{_BOLD}{_CYAN}╔══════════════════════════════════════════════════════╗")
    print(f"║   VitalGuard — Vitals Simulator Console Test          ║")
    print(f"╚══════════════════════════════════════════════════════╝{_RESET}\n")
    print(f"  Record   : {RECORD_PATH}")
    print(f"  Duration : {DURATION:.0f} s")
    print(f"  Trigger  : abnormal segment injected at t={TRIGGER_AT:.0f} s\n")

    print(
        f"  {'Time':>7}  {'HR':>5}  {'SpO2':>6}  {'ECG Label':<22}  Severity"
    )
    print("  " + "─" * 65)

    try:
        sim = VitalsSimulator(
            record_path=RECORD_PATH,
            hr_values=HR_VALUES,
            spo2_values=SPO2_VALUES,
        )
    except Exception as exc:
        print(f"\n{_RED}ERROR: Could not load record '{RECORD_PATH}': {exc}{_RESET}")
        print(
            f"\nMake sure you have downloaded the data files.  "
            f"See README.md for instructions.\n"
        )
        return

    triggered = False
    severity_counts: Counter[str] = Counter()
    last_printed_second: int = -1
    elapsed: float = 0.0
    start_time: float | None = None

    import time as _time
    start_wall = _time.perf_counter()

    async for sample in sim.stream():
        now = _time.perf_counter()
        elapsed = now - start_wall

        # Trigger abnormal segment at the configured time
        if not triggered and elapsed >= TRIGGER_AT:
            triggered = True
            ok = sim.trigger_abnormal_segment()
            flag = "✓ triggered" if ok else "✗ no abnormal annotations found"
            print(
                f"\n  {_YELLOW}[t={elapsed:>5.1f}s]  ⚡  trigger_abnormal_segment() — {flag}{_RESET}\n"
            )

        # Print one row per second
        current_second = int(elapsed)
        if current_second != last_printed_second:
            last_printed_second = current_second

            score_result = score_vitals(
                heart_rate=sample["heart_rate"],
                spo2=sample["spo2"],
                ecg_label=sample["ecg_label"],
            )
            sev = score_result["severity"]
            severity_counts[sev] += 1

            reasons_str = ""
            if score_result["reasons"]:
                reasons_str = f"  ← {'; '.join(score_result['reasons'])}"

            print(
                f"  t={elapsed:>5.1f}s  "
                f"HR={sample['heart_rate']:>5.0f}  "
                f"SpO2={sample['spo2']:>5.1f}%  "
                f"{sample['ecg_label']:<22}  "
                f"{_fmt_severity(sev, score_result['score'])}"
                f"{_GREY}{reasons_str}{_RESET}"
            )

        if elapsed >= DURATION:
            break

    # Summary
    total = sum(severity_counts.values())
    print(f"\n{'  ' + '─' * 65}")
    print(f"\n  {_BOLD}Summary over {DURATION:.0f} s ({total} windows printed):{_RESET}")
    for sev in ("normal", "warning", "critical"):
        count = severity_counts[sev]
        pct = (count / total * 100) if total else 0
        colour = SEVERITY_COLOUR.get(sev, _RESET)
        bar = "█" * int(pct / 5)
        print(f"  {colour}{sev.upper():<8}{_RESET}  {count:>4} windows  {bar} {pct:.1f}%")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    asyncio.run(run_test())
