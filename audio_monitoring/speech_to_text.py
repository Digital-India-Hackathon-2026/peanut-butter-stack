"""Speech transcription helpers for VitalGuard audio monitoring."""

from __future__ import annotations

from typing import Any, Iterable


class SpeechTranscriber:
    """Transcribe short audio chunks with a single loaded Whisper model."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8") -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - dependency installation issue
            raise ImportError(
                "faster-whisper is required for SpeechTranscriber. Install the package from requirements.txt."
            ) from exc

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_chunk: Any) -> str:
        """Return the transcript for a short mono audio chunk.

        The input is expected to be a 16 kHz mono numpy array or array-like object.
        """

        audio = self._normalize_audio(audio_chunk)
        if audio.size == 0:
            return ""

        segments, _info = self._model.transcribe(
            audio,
            beam_size=1,
            language="en",
            condition_on_previous_text=False,
            vad_filter=True,
        )
        transcript_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(transcript_parts).strip()

    @staticmethod
    def _normalize_audio(audio_chunk: Any):
        import numpy as np

        audio = np.asarray(audio_chunk)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        if audio.dtype.kind in {"i", "u"}:
            max_value = float(np.iinfo(audio.dtype).max)
            audio = audio.astype(np.float32) / max_value
        else:
            audio = audio.astype(np.float32, copy=False)
        return audio
