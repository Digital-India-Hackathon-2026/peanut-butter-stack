"""Command-line audio testing pipeline for VitalGuard."""

from __future__ import annotations

import argparse
import wave
import sys
from collections import deque
from pathlib import Path
from typing import Deque, Iterable, List, Tuple

import numpy as np
import sounddevice as sd

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from audio_monitoring.distress_detection import (
    DistressTracker,
    check_volume_spike,
    detect_distress_phrase,
    update_rolling_baseline_rms,
)
from audio_monitoring.speech_to_text import SpeechTranscriber

SAMPLE_RATE = 16000
CHUNK_SECONDS = 4.0
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_SECONDS)


def _decode_pcm_frames(frames: bytes, sample_width: int) -> np.ndarray:
    if sample_width == 1:
        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")
    return audio


def load_wav_file(file_path: Path) -> np.ndarray:
    with wave.open(str(file_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())

    audio = _decode_pcm_frames(frames, sample_width)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if sample_rate != SAMPLE_RATE:
        audio = resample_audio(audio, sample_rate, SAMPLE_RATE)
    return audio.astype(np.float32, copy=False)


def resample_audio(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if audio.size == 0 or source_rate == target_rate:
        return audio.astype(np.float32, copy=False)
    duration_seconds = audio.shape[0] / float(source_rate)
    target_length = max(1, int(duration_seconds * target_rate))
    source_positions = np.linspace(0.0, duration_seconds, num=audio.shape[0], endpoint=False)
    target_positions = np.linspace(0.0, duration_seconds, num=target_length, endpoint=False)
    return np.interp(target_positions, source_positions, audio).astype(np.float32)


def split_audio_into_chunks(audio: np.ndarray, chunk_frames: int = CHUNK_FRAMES) -> Iterable[np.ndarray]:
    for start_index in range(0, len(audio), chunk_frames):
        chunk = audio[start_index : start_index + chunk_frames]
        if chunk.size:
            yield chunk


def run_pipeline(audio_chunk: np.ndarray, transcriber: SpeechTranscriber, tracker: DistressTracker, baseline_history: Deque[float]) -> dict:
    transcript = transcriber.transcribe(audio_chunk)
    phrase_result = detect_distress_phrase(transcript)
    phrase_detected = bool(phrase_result["distress_detected"])
    repeated_result = tracker.record_detection(phrase_detected)
    repeated_distress = bool(repeated_result["repeated_distress"])
    baseline_rms = float(np.mean(baseline_history)) if baseline_history else 0.0
    volume_result = check_volume_spike(audio_chunk, baseline_rms)
    current_rms = float(volume_result["rms"])

    if not phrase_detected and not volume_result["volume_spike"]:
        update_rolling_baseline_rms(baseline_history, current_rms)

    event = "normal"
    confidence = 0.0
    matched_phrase = None

    if repeated_distress:
        event = "repeated_distress"
        confidence = 0.95
        matched_phrase = phrase_result["matched_phrase"]
    elif phrase_detected:
        event = "distress_phrase"
        confidence = 0.85
        matched_phrase = phrase_result["matched_phrase"]
    elif volume_result["volume_spike"]:
        event = "loud_vocalization"
        confidence = 0.35

    return {
        "event": event,
        "confidence": confidence,
        "matched_phrase": matched_phrase,
        "transcript": transcript,
        "rms": current_rms,
        "volume_spike": bool(volume_result["volume_spike"]),
        "repeated_distress": repeated_distress,
    }


def run_folder(folder_path: Path, transcriber: SpeechTranscriber) -> None:
    tracker = DistressTracker()
    baseline_history: Deque[float] = deque()
    wav_files = sorted(folder_path.rglob("*.wav"))
    if not wav_files:
        print(f"No .wav files found in {folder_path}")
        return

    for wav_file in wav_files:
        audio = load_wav_file(wav_file)
        for chunk_index, chunk in enumerate(split_audio_into_chunks(audio), start=1):
            result = run_pipeline(chunk, transcriber, tracker, baseline_history)
            print(
                f"{wav_file.name} [chunk {chunk_index}] -> "
                f"event={result['event']}, confidence={result['confidence']:.2f}, "
                f"matched_phrase={result['matched_phrase']}, transcript={result['transcript']!r}, "
                f"rms={result['rms']:.6f}, volume_spike={result['volume_spike']}, "
                f"repeated_distress={result['repeated_distress']}"
            )


def run_mic(transcriber: SpeechTranscriber) -> None:
    tracker = DistressTracker()
    baseline_history: Deque[float] = deque()
    print("Listening to the microphone. Press Ctrl+C to stop.")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=CHUNK_FRAMES) as stream:
        while True:
            audio, _overflowed = stream.read(CHUNK_FRAMES)
            chunk = np.asarray(audio[:, 0], dtype=np.float32)
            result = run_pipeline(chunk, transcriber, tracker, baseline_history)
            print(
                f"mic -> event={result['event']}, confidence={result['confidence']:.2f}, "
                f"matched_phrase={result['matched_phrase']}, transcript={result['transcript']!r}, "
                f"rms={result['rms']:.6f}, volume_spike={result['volume_spike']}, "
                f"repeated_distress={result['repeated_distress']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test VitalGuard audio distress detection.")
    parser.add_argument(
        "--source",
        required=True,
        help='Either "mic" for live microphone input or a folder path containing .wav clips.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    transcriber = SpeechTranscriber(model_size="base")
    source = args.source.strip()

    if source.lower() == "mic":
        run_mic(transcriber)
        return

    folder_path = Path(source)
    if not folder_path.exists() or not folder_path.is_dir():
        raise SystemExit(f"Source must be 'mic' or an existing folder path. Got: {source}")

    run_folder(folder_path, transcriber)


if __name__ == "__main__":
    main()
