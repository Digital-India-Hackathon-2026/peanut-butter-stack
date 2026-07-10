# Peanut Butter Stack

Repository for Hackathon Team Peanut Butter Stack.

## VitalGuard Live Camera Monitoring

The live camera monitoring prototype lives in [video_monitoring/](video_monitoring/).

Run the camera test with a webcam:

```bash
python video_monitoring/test_camera_stream.py --source 0
```

Run the camera test with a sample video file:

```bash
python video_monitoring/test_camera_stream.py --source test_clips/fall_01.mp4
```

Run the FastAPI app with a video file source:

```bash
VIDEO_SOURCE=test_clips/fall_01.mp4 uvicorn video_monitoring.main:app --reload
```

The `VIDEO_SOURCE` environment variable accepts either a webcam index such as `0` or a file path string.

## VitalGuard Audio Distress Monitoring

The audio distress monitoring module lives in [audio_monitoring/](audio_monitoring/).

Install its requirements and start the audio websocket service:

```bash
pip install -r audio_monitoring/requirements.txt
uvicorn audio_monitoring.main:app --reload --port 8002
```

The audio websocket endpoint is:

```text
/ws/audio-events
```

This service listens on the host microphone and emits live JSON events for distress detection:

- `normal`
- `loud_vocalization`
- `distress_phrase`
- `repeated_distress`

## Unified Monitoring App

The repository root app now mounts video, audio, and vitals services under a unified FastAPI entrypoint.

Run the unified app with:

```bash
uvicorn main:app --reload --port 8000
```

Available endpoints:

- `/video/health`
- `/video/video-feed`
- `/video/ws/video-events`
- `/audio/health`
- `/audio/ws/audio-events`
- `/vitals/ws/vitals`