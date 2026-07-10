"""Heuristics for detecting spoken distress and loud vocalizations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from time import time
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np

DISTRESS_PHRASES = [
    "help",
    "i can't breathe",
    "chest pain",
    "call the nurse",
    "it hurts",
]


def _normalize_text(text: str) -> str:
    normalized = text.lower().strip()
    for character in ["'", '"', "?", "!", ".", ",", ";", ":", "(", ")", "[", "]", "{", "}", "-"]:
        normalized = normalized.replace(character, " ")
    normalized = " ".join(normalized.split())
    normalized = normalized.replace("can t", "cant")
    normalized = normalized.replace("i m", "im")
    normalized = normalized.replace("it s", "its")
    return normalized


def _candidate_windows(tokens: List[str], phrase_tokens: List[str]) -> Iterable[str]:
    phrase_length = len(phrase_tokens)
    if phrase_length == 0:
        return []

    for window_size in {max(1, phrase_length - 1), phrase_length, phrase_length + 1}:
        if window_size > len(tokens):
            continue
        for start_index in range(0, len(tokens) - window_size + 1):
            yield " ".join(tokens[start_index : start_index + window_size])


def _fuzzy_substring_match(text: str, phrase: str, threshold: float = 0.82) -> bool:
    normalized_text = _normalize_text(text)
    normalized_phrase = _normalize_text(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    if normalized_phrase in normalized_text:
        return True

    text_tokens = normalized_text.split()
    phrase_tokens = normalized_phrase.split()
    if not text_tokens or not phrase_tokens:
        return False

    for candidate in _candidate_windows(text_tokens, phrase_tokens):
        ratio = SequenceMatcher(None, candidate, normalized_phrase).ratio()
        if ratio >= threshold:
            return True
    return False


def detect_distress_phrase(text: str) -> Dict[str, Optional[str]]:
    """Check a transcript for distress phrases using a case-insensitive fuzzy match."""

    for phrase in DISTRESS_PHRASES:
        if _fuzzy_substring_match(text, phrase):
            return {"distress_detected": True, "matched_phrase": phrase}
    return {"distress_detected": False, "matched_phrase": None}


@dataclass
class DistressTracker:
    """Track repeated distress calls within a rolling time window."""

    time_window_seconds: int = 30

    def __post_init__(self) -> None:
        self._events: Deque[float] = deque()

    def record_detection(self, detected: bool, timestamp: Optional[float] = None) -> Dict[str, bool]:
        current_time = time() if timestamp is None else timestamp
        self._prune(current_time)
        if detected:
            self._events.append(current_time)
        self._prune(current_time)
        repeated_distress = len(self._events) >= 2
        return {"repeated_distress": repeated_distress}

    def _prune(self, current_time: float) -> None:
        while self._events and current_time - self._events[0] > self.time_window_seconds:
            self._events.popleft()


def calculate_rms(audio_chunk: np.ndarray) -> float:
    audio = np.asarray(audio_chunk, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio), dtype=np.float32)))


# This is a low-confidence heuristic signal. It detects loudness, not distress specifically.
def check_volume_spike(audio_chunk: np.ndarray, baseline_rms: float, threshold_multiplier: float = 3.0) -> Dict[str, float | bool]:
    rms = calculate_rms(audio_chunk)
    spike_threshold = float(baseline_rms) * float(threshold_multiplier)
    volume_spike = baseline_rms > 0.0 and rms > spike_threshold
    return {"volume_spike": volume_spike, "rms": rms}


def update_rolling_baseline_rms(
    quiet_rms_history: Deque[float],
    new_rms: float,
    max_history: int = 20,
    quiet_multiplier: float = 1.2,
) -> float:
    """Maintain a rolling baseline from recent quiet chunks only."""

    if new_rms < 0:
        return float(np.mean(quiet_rms_history)) if quiet_rms_history else 0.0

    current_baseline = float(np.mean(quiet_rms_history)) if quiet_rms_history else 0.0
    if current_baseline == 0.0 or new_rms <= current_baseline * quiet_multiplier:
        quiet_rms_history.append(float(new_rms))
        while len(quiet_rms_history) > max_history:
            quiet_rms_history.popleft()
    return float(np.mean(quiet_rms_history)) if quiet_rms_history else 0.0
