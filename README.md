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