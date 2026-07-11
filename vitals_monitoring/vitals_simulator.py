"""
vitals_simulator.py
-------------------
VitalGuard — Vitals Simulator

Reads a PhysioNet-format ECG record via `wfdb` and replays it sample-by-sample
at real playback speed through an async generator.

Supports:
  - Multi-lead ECG replay (configurable channel)
  - HR / SpO2 injection as separate value lists (cycled over time)
  - Annotation-driven ECG labelling (MIT-BIH symbol table)
  - On-demand switch to the first annotated abnormal segment via
    trigger_abnormal_segment()

Expected data layout
--------------------
  <record_path>.hea   — wfdb header
  <record_path>.dat   — signal samples
  <record_path>.atr   — beat annotations  (optional; if absent, label = "normal")

Usage
-----
  sim = VitalsSimulator(
      record_path="data/mitdb/100",
      hr_values=[72, 73, 71, 74],
      spo2_values=[98.0, 97.5, 98.0],
  )
  async for sample in sim.stream():
      print(sample)
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator

import numpy as np

try:
    import wfdb
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "wfdb is required: pip install wfdb"
    ) from exc

# ---------------------------------------------------------------------------
# MIT-BIH annotation symbol → ECG label mapping
# ---------------------------------------------------------------------------
# Reference: https://physionet.org/physiobank/annotations.shtml

# Symbols that map to "normal" sinus rhythm
_NORMAL_SYMBOLS: frozenset[str] = frozenset({"N", "·", "~"})

# Symbols that map to "minor_irregularity" (ectopic / aberrant but not dangerous)
_MINOR_SYMBOLS: frozenset[str] = frozenset({
    "L",  # Left bundle branch block beat
    "R",  # Right bundle branch block beat
    "B",  # Bundle branch block beat (unspecified)
    "A",  # Atrial premature beat
    "a",  # Aberrated atrial premature beat
    "J",  # Nodal (junctional) premature beat
    "S",  # Supraventricular premature or ectopic beat
    "j",  # Nodal (junctional) escape beat
    "n",  # Supraventricular escape beat (atrial or nodal)
    "e",  # Atrial escape beat
})

# Symbols that map to "arrhythmia" (clinically significant)
_ARRHYTHMIA_SYMBOLS: frozenset[str] = frozenset({
    "V",  # Premature ventricular contraction
    "r",  # R-on-T premature ventricular contraction
    "F",  # Fusion of ventricular and normal beat
    "E",  # Ventricular escape beat
    "/",  # Paced beat
    "f",  # Fusion of paced and normal beat
    "Q",  # Unclassifiable beat
    "!",  # Ventricular flutter wave
    "[",  # Start of ventricular flutter/fibrillation
    "]",  # End of ventricular flutter/fibrillation
    "+",  # Rhythm change (non-sinus)
    "p",  # Non-conducted P-wave (blocked APC)
    "x",  # Non-conducted P-wave (blocked PAC variant)
})

ECG_LABEL_NORMAL = "normal"
ECG_LABEL_MINOR = "minor_irregularity"
ECG_LABEL_ARRHYTHMIA = "arrhythmia"


def _symbol_to_label(symbol: str) -> str:
    """Map a single wfdb annotation symbol to a VitalGuard ECG label."""
    if symbol in _NORMAL_SYMBOLS:
        return ECG_LABEL_NORMAL
    if symbol in _MINOR_SYMBOLS:
        return ECG_LABEL_MINOR
    if symbol in _ARRHYTHMIA_SYMBOLS:
        return ECG_LABEL_ARRHYTHMIA
    # Unknown symbol — default to minor irregularity (fail-safe)
    return ECG_LABEL_MINOR


# ---------------------------------------------------------------------------
# VitalsSimulator
# ---------------------------------------------------------------------------


class VitalsSimulator:
    """
    Replays a PhysioNet ECG record at real-time speed via an async generator.

    Parameters
    ----------
    record_path : str
        Path to the wfdb record without extension
        (e.g. ``"vitals_monitoring/data/mitdb/100"``).
    hr_values : list[float]
        Heart-rate values (bpm) to cycle through — updated once per second.
    spo2_values : list[float]
        SpO2 values (%) to cycle through — updated once per second.
    channel : int
        Which signal channel to stream (default 0 = first lead).
    loop : bool
        If True (default), wrap around to the beginning when the record ends.
    """

    def __init__(
        self,
        record_path: str,
        hr_values: list[float],
        spo2_values: list[float],
        channel: int = 0,
        loop: bool = True,
    ) -> None:
        self._record_path = str(record_path)
        self._hr_values = list(hr_values)
        self._spo2_values = list(spo2_values)
        self._channel = channel
        self._loop = loop

        # Load wfdb record ------------------------------------------------
        record = wfdb.rdrecord(self._record_path)
        self._fs: float = float(record.fs)
        # Extract the chosen channel as a flat float64 array
        self._signal: np.ndarray = record.p_signal[:, channel].astype(np.float64)
        self._n_samples: int = len(self._signal)
        self._signal_units: str = record.units[channel] if record.units else "mV"

        # Load annotations (optional) -------------------------------------
        self._ann_sample: np.ndarray = np.array([], dtype=np.int64)
        self._ann_symbol: list[str] = []
        try:
            ann = wfdb.rdann(self._record_path, "atr")
            self._ann_sample = np.array(ann.sample, dtype=np.int64)
            self._ann_symbol = list(ann.symbol)
        except Exception:
            # If no annotation file exists, all samples are labelled "normal"
            pass

        # Build a sample-indexed label lookup (label at each annotation onset,
        # carried forward until the next annotation)
        self._build_label_index()

        # Find the first genuinely abnormal annotation sample index
        self._first_abnormal_sample: int | None = self._find_first_abnormal()

        # Playback state --------------------------------------------------
        self._current_sample: int = 0
        self._abnormal_mode: bool = False
        self._trigger_event: asyncio.Event = asyncio.Event()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_label_index(self) -> None:
        """
        Build a sorted list of (sample_index, label) pairs for fast lookup.
        Between annotation markers the previous label is carried forward.
        """
        self._label_changes: list[tuple[int, str]] = []
        for samp, sym in zip(self._ann_sample, self._ann_symbol):
            label = _symbol_to_label(sym)
            self._label_changes.append((int(samp), label))
        # Ensure sorted by sample
        self._label_changes.sort(key=lambda x: x[0])

    def _label_at(self, sample_idx: int) -> str:
        """Return the ECG label that applies at `sample_idx`."""
        if not self._label_changes:
            return ECG_LABEL_NORMAL
        # Binary-search: find the last annotation whose sample <= sample_idx
        lo, hi = 0, len(self._label_changes) - 1
        result_label = ECG_LABEL_NORMAL  # default before first annotation
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._label_changes[mid][0] <= sample_idx:
                result_label = self._label_changes[mid][1]
                lo = mid + 1
            else:
                hi = mid - 1
        return result_label

    def _find_first_abnormal(self) -> int | None:
        """Return the sample index of the first non-normal annotation, or None."""
        for samp, sym in zip(self._ann_sample, self._ann_symbol):
            if _symbol_to_label(sym) != ECG_LABEL_NORMAL:
                return int(samp)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def trigger_abnormal_segment(self) -> bool:
        """
        Jump playback to the first annotated abnormal ECG segment.

        Returns True if an abnormal segment was found and the jump was applied,
        False if the record has no non-normal annotations.

        This method is safe to call from any async context or a REST handler.
        """
        if self._first_abnormal_sample is None:
            return False
        self._current_sample = self._first_abnormal_sample
        self._abnormal_mode = True
        # Signal the streaming loop to pick up the new position on next tick
        self._trigger_event.set()
        return True

    @property
    def sampling_frequency(self) -> float:
        """Sampling frequency of the loaded record in Hz."""
        return self._fs

    @property
    def signal_units(self) -> str:
        """Physical units of the ECG channel (e.g. 'mV')."""
        return self._signal_units

    @property
    def n_samples(self) -> int:
        """Total number of samples in the record."""
        return self._n_samples

    @property
    def is_abnormal_mode(self) -> bool:
        """True if currently replaying from an abnormal segment."""
        return self._abnormal_mode

    async def stream(self) -> AsyncGenerator[dict, None]:
        """
        Async generator that yields one ECG sample per iteration at real-time speed.

        Yields
        ------
        dict with keys:
            "ecg"        : float  — ECG amplitude in signal_units
            "ecg_label"  : str    — "normal" | "minor_irregularity" | "arrhythmia"
            "heart_rate" : float  — current HR value from the injected list
            "spo2"       : float  — current SpO2 value from the injected list
            "timestamp"  : float  — Unix epoch seconds at the time of yield
            "sample_idx" : int    — absolute sample index in the record
        """
        interval: float = 1.0 / self._fs  # seconds between samples
        hr_idx: int = 0
        spo2_idx: int = 0
        samples_since_update: int = 0
        samples_per_second: int = max(1, int(self._fs))

        # Current HR / SpO2 values (updated once per second)
        current_hr = float(self._hr_values[hr_idx % len(self._hr_values)])
        current_spo2 = float(self._spo2_values[spo2_idx % len(self._spo2_values)])

        while True:
            # Check if trigger_abnormal_segment() was called
            if self._trigger_event.is_set():
                self._trigger_event.clear()
                # Reset per-second counter so HR/SpO2 update is re-aligned
                samples_since_update = 0

            idx = self._current_sample

            # Wrap around if looping is enabled
            if idx >= self._n_samples:
                if self._loop:
                    self._current_sample = 0
                    self._abnormal_mode = False
                    idx = 0
                else:
                    return  # End of record

            ecg_val = float(self._signal[idx])
            ecg_label = self._label_at(idx)

            yield {
                "ecg": ecg_val,
                "ecg_label": ecg_label,
                "heart_rate": current_hr,
                "spo2": current_spo2,
                "timestamp": time.time(),
                "sample_idx": idx,
            }

            self._current_sample += 1
            samples_since_update += 1

            # Update HR / SpO2 once per second
            if samples_since_update >= samples_per_second:
                samples_since_update = 0
                hr_idx += 1
                spo2_idx += 1
                current_hr = float(self._hr_values[hr_idx % len(self._hr_values)])
                current_spo2 = float(
                    self._spo2_values[spo2_idx % len(self._spo2_values)]
                )

            await asyncio.sleep(interval)
