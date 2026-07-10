# VitalGuard Audio Monitoring

This folder contains a standalone audio distress detection module for VitalGuard. It is intentionally independent from the other monitoring pipelines so it can be correlated later by a separate `correlation_engine/` folder.

## Setup

Install the required packages from this folder:

```bash
pip install -r audio_monitoring/requirements.txt
```

The audio pipeline uses `faster-whisper` for transcription and `sounddevice` for live microphone capture.

## Live Microphone Test

Run the console tester against the microphone:

```bash
python audio_monitoring/test_audio.py --source mic
```

This captures rolling audio chunks, transcribes them, checks distress phrases, and evaluates the low-confidence loudness heuristic.

## Sample WAV Clips

Run the console tester against a folder of `.wav` files:

```bash
python audio_monitoring/test_audio.py --source path\to\sample_clips
```

The script prints the filename for each clip and chunk so you can compare results with your labels.

## FastAPI WebSocket Service

Start the websocket server:

```bash
uvicorn audio_monitoring.main:app --reload
```

WebSocket endpoint:

```text
/ws/audio-events
```

This endpoint captures live microphone audio on the server machine, runs the full pipeline, and only emits JSON when the detection state changes.

## Event Shape

The websocket emits events in this shape:

```json
{
  "patient": "ICU-12",
  "event": "distress_phrase",
  "confidence": 0.85,
  "matched_phrase": "help",
  "time": "2026-07-10T12:34:56.000000+00:00"
}
```

Possible event values:

- `normal`
- `loud_vocalization`
- `distress_phrase`
- `repeated_distress`

## Notes

- `distress_phrase` and `repeated_distress` are treated as high-confidence events.
- `loud_vocalization` is only a weak heuristic signal for loudness, not a distress classifier.
- `SpeechTranscriber` loads the Whisper model once at initialization for repeated chunk processing speed.
