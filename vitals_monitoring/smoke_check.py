"""Smoke check — run from vitals_monitoring/ directory."""
import sys, pathlib, random
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from vitals_monitoring.vitals_simulator import VitalsSimulator
from vitals_monitoring.severity_scorer import score_vitals

# ---------------------------------------------------------------------------
# Patient pool — random names + details assigned per test run
# ---------------------------------------------------------------------------

PATIENT_POOL = [
    {"name": "Arjun Mehta",      "age": 58, "gender": "Male",   "diagnosis": "Acute Myocardial Infarction"},
    {"name": "Priya Nair",       "age": 45, "gender": "Female", "diagnosis": "Atrial Fibrillation"},
    {"name": "Rajesh Kumar",     "age": 63, "gender": "Male",   "diagnosis": "Congestive Heart Failure"},
    {"name": "Sushma Iyer",      "age": 52, "gender": "Female", "diagnosis": "Ventricular Tachycardia"},
    {"name": "Mohammed Farhan",  "age": 71, "gender": "Male",   "diagnosis": "Complete Heart Block"},
    {"name": "Kavitha Reddy",    "age": 39, "gender": "Female", "diagnosis": "Hypertensive Crisis"},
    {"name": "Suresh Pillai",    "age": 66, "gender": "Male",   "diagnosis": "Bradycardia"},
    {"name": "Ananya Sharma",    "age": 48, "gender": "Female", "diagnosis": "Pulmonary Embolism"},
    {"name": "Dinesh Patel",     "age": 55, "gender": "Male",   "diagnosis": "Cardiomyopathy"},
    {"name": "Lakshmi Venkat",   "age": 60, "gender": "Female", "diagnosis": "Hypoxemia"},
]

# Shuffle and pick 5 unique patients for 5 beds
random.shuffle(PATIENT_POOL)
selected = PATIENT_POOL[:5]

# ---------------------------------------------------------------------------
# Load ECG records
# ---------------------------------------------------------------------------
print("=" * 70)
print("  VITALGUARD — SMOKE CHECK")
print("=" * 70)

for record in ["100", "109"]:
    sim = VitalsSimulator(
        record_path=f"data/{record}",
        hr_values=[72, 73, 74],
        spo2_values=[98.0, 97.5],
    )
    triggered = sim.trigger_abnormal_segment()
    print(
        f"  Record {record}: fs={sim.sampling_frequency}Hz  "
        f"samples={sim.n_samples}  units={sim.signal_units}  "
        f"abnormal_trigger={triggered}"
    )

print()

# ---------------------------------------------------------------------------
# Vitals test cases — paired with random patients + bed numbers
# ---------------------------------------------------------------------------

cases = [
    (72,  98.0, "normal",             "All Normal"),
    (55,  97.0, "normal",             "Mild Bradycardia"),
    (110, 93.0, "minor_irregularity", "Warning Combo"),
    (45,  88.0, "arrhythmia",         "Critical"),
    (140, 85.0, "arrhythmia",         "Max Critical"),
]

print(f"  {'BED':<8}  {'PATIENT':<20}  {'AGE':>3}  {'GENDER':<7}  {'DIAGNOSIS':<30}  {'SCENARIO':<18}  {'HR':>3}  {'SpO2':>5}  {'ECG':<22}  {'SEVERITY':<8}  {'SCORE'}  TRIGGERED REASONS")
print("  " + "-" * 185)

for (hr, spo2, ecg, scenario), patient in zip(cases, selected):
    bed_num = selected.index(patient) + 1
    bed_id  = f"BED-0{bed_num}"
    r       = score_vitals(hr, spo2, ecg)
    sev     = r["severity"].upper()
    score   = r["score"]
    reasons = r["reasons"] if r["reasons"] else ["—"]

    print(
        f"  {bed_id:<8}  {patient['name']:<20}  {patient['age']:>3}  "
        f"{patient['gender']:<7}  {patient['diagnosis']:<30}  "
        f"{scenario:<18}  {hr:>3}  {spo2:>4.1f}%  {ecg:<22}  "
        f"{sev:<8}  {score:>5}  {', '.join(reasons)}"
    )

print()
print("  Smoke check complete.")
print("=" * 70)
