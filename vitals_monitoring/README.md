# VitalGuard — `vitals_monitoring/` Module

Standalone vitals monitoring and severity scoring module for the **VitalGuard** hospital patient monitoring system.

This module is fully self-contained — it does not import from or depend on any other folder in the project.

---

## Folder Structure

```
vitals_monitoring/
├── vitals_simulator.py   # ECG + vitals replay via async generator
├── severity_scorer.py    # Composite severity scoring logic
├── main.py               # Standalone FastAPI server (WebSocket + REST)
├── test_vitals.py        # Console test script (no server required)
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── data/
    └── mitdb/            # ← place PhysioNet record files here
        ├── 100.hea
        ├── 100.dat
        └── 100.atr
```

---

## 1. Prerequisites

- Python **3.10** or newer
- `pip` (or your preferred virtual-environment manager)

---

## 2. Install Dependencies

```bash
# From inside vitals_monitoring/
pip install -r requirements.txt
```

---

## 3. Download PhysioNet Data Files

The simulator requires a PhysioNet ECG record in wfdb format.  
The default is **MIT-BIH Arrhythmia Database, record 100** — a freely available public dataset.

**Option A — Download via Python (recommended):**

```python
import wfdb, pathlib
pathlib.Path("data/mitdb").mkdir(parents=True, exist_ok=True)
wfdb.dl_database("mitdb", dl_dir="data/mitdb", records=["100"])
```

Run this one-liner from inside `vitals_monitoring/`:

```bash
python -c "import wfdb, pathlib; pathlib.Path('data/mitdb').mkdir(parents=True, exist_ok=True); wfdb.dl_database('mitdb', dl_dir='data/mitdb', records=['100'])"
```

**Option B — Manual download:**

Visit [https://physionet.org/content/mitdb/1.0.0/](https://physionet.org/content/mitdb/1.0.0/)  
and download `100.hea`, `100.dat`, and `100.atr` into `vitals_monitoring/data/mitdb/`.

**Using a different record:**  
Set the `VITALGUARD_RECORD_PATH` environment variable to the path of the record (without extension):

```bash
set VITALGUARD_RECORD_PATH=data/mitdb/108   # Windows
export VITALGUARD_RECORD_PATH=data/mitdb/108  # macOS / Linux
```

---

## 4. Run the Console Test Script

Verifies severity scoring logic without starting the server.

```bash
# From inside vitals_monitoring/
python test_vitals.py
```

The script runs for **30 seconds** by default, prints a colour-coded severity row every second, automatically triggers the abnormal ECG segment at **t = 10 s**, and prints a summary table at the end.

**Environment variables for test_vitals.py:**

| Variable | Default | Description |
|---|---|---|
| `VITALGUARD_RECORD_PATH` | `data/mitdb/100` | Path to wfdb record (no extension) |
| `VITALGUARD_DURATION` | `30` | Total test duration in seconds |
| `VITALGUARD_TRIGGER_AT` | `10` | Seconds before `trigger_abnormal_segment()` fires |

Example (custom duration):

```bash
set VITALGUARD_DURATION=60 && python test_vitals.py
```

---

## 5. Run the FastAPI Server

Starts the WebSocket streaming server and REST endpoints.

```bash
# From inside vitals_monitoring/
uvicorn main:app --reload --port 8001
```

The server will be available at `http://localhost:8001`.

**Environment variables for main.py:**

| Variable | Default | Description |
|---|---|---|
| `VITALGUARD_RECORD_PATH` | `data/mitdb/100` | Path to wfdb record (no extension) |
| `VITALGUARD_CHANNEL` | `0` | ECG signal channel index |

---

## 6. API Reference

### `GET /`
Health check — returns server status and simulator metadata.

```bash
curl http://localhost:8001/
```

### `POST /trigger-abnormal`
Instantly jumps the simulator to the first annotated abnormal ECG segment.  
Useful for live demos.

```bash
curl -X POST http://localhost:8001/trigger-abnormal
```

### `WebSocket /ws/vitals`
Connect and receive a stream of JSON messages — one per ECG sample.

**Quick test with a browser console:**
```js
const ws = new WebSocket("ws://localhost:8001/ws/vitals");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

**Quick test with `wscat`:**
```bash
npm install -g wscat
wscat -c ws://localhost:8001/ws/vitals
```

**Message schema:**
```json
{
  "ecg_sample":    -0.145,
  "ecg_label":     "normal",
  "heart_rate":    72.0,
  "spo2":          98.0,
  "timestamp":     1720556461.234,
  "sample_idx":    3600,
  "abnormal_mode": false,
  "severity":      "normal",
  "score":         0,
  "reasons":       []
}
```

---

## 7. Severity Score Reference

| Vital | Score 0 | Score 1 | Score 2 |
|---|---|---|---|
| Heart Rate | 60–100 bpm | 50–60 or 100–130 | < 50 or > 130 |
| SpO2 | ≥ 95% | 90–94% | < 90% |
| ECG label | `normal` | `minor_irregularity` | `arrhythmia` |

| Total score | Severity |
|---|---|
| 0–1 | **normal** |
| 2–3 | **warning** |
| ≥ 4 | **critical** |

All thresholds are configurable constants at the top of `severity_scorer.py`.

---

## 8. Integration Notes

The `score_vitals()` function in `severity_scorer.py` returns a plain `dict` and has no I/O dependencies.  
It can be imported and called directly from the upcoming `correlation_engine/` module without any changes.
