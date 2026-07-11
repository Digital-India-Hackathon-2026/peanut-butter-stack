// ─── VitalGuard Real Dataset ──────────────────────────────────────────────
// Sourced directly from synthetic_dataset/vitalguard_synthetic_dataset.json
// 20 patients across 4 rooms. All dashboards use this single source of truth.

export type PatientStatus = 'normal' | 'warning' | 'critical'
export type SeverityLevel = 'normal' | 'warning' | 'high-risk' | 'critical'

export interface VitalReading {
  second: number
  heart_rate: number
  spo2: number
  respiratory_rate: number
  temperature_f: number
  ecg_label: string
  torso_angle: number
  hip_velocity: number
  motion_state: string
}

export interface PatientAlert {
  second: number
  type: 'warning' | 'critical'
  message: string
}

export interface TimelineEvent {
  time: string
  label: string
  type: 'normal' | 'warning' | 'critical' | 'info'
}

export interface VGPatient {
  patient_id: string
  name: string
  age: number
  gender: string
  room: string
  bed: string
  status: PatientStatus
  severity: SeverityLevel
  risk_score: number
  diagnosis: string
  admission_date: string
  assigned_doctor: string
  assigned_nurse: string
  vitals: VitalReading[]
  alerts: PatientAlert[]
  // Derived helpers
  latestHR: number
  latestSpO2: number
  latestTemp: number
  latestRR: number
  latestEcg: string
  sparkline: number[]
  events: TimelineEvent[]
  hasFall: boolean
}

export interface NurseAlertCard {
  id: string
  patientId: string
  patientName: string
  bed: string
  room: string
  priority: 'critical' | 'warning'
  reasons: string[]
  riskScore: number
  timestamp: string
  accepted: boolean
}

// ── Raw dataset (all 20 patients) ──────────────────────────────────────────
const RAW_PATIENTS = [
  {
    patient_id: 'ICU-01', name: 'Aarav Patel', age: 64, gender: 'Male',
    room: 'Room 101', bed: 'BED-01', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 9,
    diagnosis: 'Acute myocardial infarction', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Naveen Rao', assigned_nurse: 'Nurse Sunita',
    latestHR: 59.6, latestSpO2: 97.2, latestTemp: 98.7, latestRR: 16.4, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-02', name: 'Isha Rao', age: 61, gender: 'Male',
    room: 'Room 101', bed: 'BED-02', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 22,
    diagnosis: 'Atrial fibrillation', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Sunita',
    latestHR: 62.3, latestSpO2: 94.4, latestTemp: 98.7, latestRR: 16.3, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-03', name: 'Rohan Verma', age: 44, gender: 'Female',
    room: 'Room 101', bed: 'BED-03', status: 'warning' as PatientStatus,
    severity: 'high-risk' as SeverityLevel, risk_score: 37,
    diagnosis: 'Post-operative recovery', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Naveen Rao', assigned_nurse: 'Nurse Sunita',
    latestHR: 75.7, latestSpO2: 96.5, latestTemp: 98.6, latestRR: 18.2, latestEcg: 'minor_irregularity',
    alerts: [
      { second: 3, type: 'warning' as const, message: 'Elevated heart rate' },
      { second: 7, type: 'warning' as const, message: 'Elevated heart rate' },
    ],
    hasFall: false,
  },
  {
    patient_id: 'ICU-04', name: 'Meera Singh', age: 69, gender: 'Non-binary',
    room: 'Room 101', bed: 'BED-04', status: 'warning' as PatientStatus,
    severity: 'high-risk' as SeverityLevel, risk_score: 60,
    diagnosis: 'Sepsis monitoring', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Priya',
    latestHR: 65.5, latestSpO2: 97.4, latestTemp: 97.8, latestRR: 17.1, latestEcg: 'normal',
    alerts: [
      { second: 4, type: 'warning' as const, message: 'SpO₂ dip' },
      { second: 8, type: 'warning' as const, message: 'SpO₂ dip' },
    ],
    hasFall: false,
  },
  {
    patient_id: 'ICU-05', name: 'Kavya Sharma', age: 65, gender: 'Non-binary',
    room: 'Room 101', bed: 'BED-05', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 16,
    diagnosis: 'Respiratory distress', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Meera',
    latestHR: 71.5, latestSpO2: 95.7, latestTemp: 98.7, latestRR: 17.0, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-06', name: 'Vikram Das', age: 52, gender: 'Male',
    room: 'Room 102', bed: 'BED-06', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 17,
    diagnosis: 'Stroke observation', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Naveen Rao', assigned_nurse: 'Nurse Anjali',
    latestHR: 62.9, latestSpO2: 94.3, latestTemp: 98.6, latestRR: 17.4, latestEcg: 'minor_irregularity',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-07', name: 'Nisha Gupta', age: 52, gender: 'Non-binary',
    room: 'Room 102', bed: 'BED-07', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 22,
    diagnosis: 'Pneumonia', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Meera',
    latestHR: 65.0, latestSpO2: 93.3, latestTemp: 98.1, latestRR: 16.0, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-08', name: 'Karan Joshi', age: 44, gender: 'Non-binary',
    room: 'Room 102', bed: 'BED-08', status: 'warning' as PatientStatus,
    severity: 'warning' as SeverityLevel, risk_score: 85,
    diagnosis: 'Hypertensive crisis', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Naveen Rao', assigned_nurse: 'Nurse Meera',
    latestHR: 76.5, latestSpO2: 97.8, latestTemp: 98.6, latestRR: 17.8, latestEcg: 'normal',
    alerts: [
      { second: 2, type: 'warning' as const, message: 'Irregular rhythm' },
      { second: 6, type: 'warning' as const, message: 'Irregular rhythm' },
    ],
    hasFall: false,
  },
  {
    patient_id: 'ICU-09', name: 'Ananya Bose', age: 46, gender: 'Male',
    room: 'Room 102', bed: 'BED-09', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 12,
    diagnosis: 'COPD exacerbation', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Priya',
    latestHR: 64.2, latestSpO2: 93.7, latestTemp: 97.7, latestRR: 16.4, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-10', name: 'Devika Nair', age: 63, gender: 'Male',
    room: 'Room 102', bed: 'BED-10', status: 'critical' as PatientStatus,
    severity: 'critical' as SeverityLevel, risk_score: 89,
    diagnosis: 'Post-fall surveillance', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Meera',
    latestHR: 80.4, latestSpO2: 89.4, latestTemp: 99.6, latestRR: 24.1, latestEcg: 'minor_irregularity',
    alerts: [
      { second: 1, type: 'critical' as const, message: 'Fall detected' },
      { second: 5, type: 'critical' as const, message: 'Acute distress' },
    ],
    hasFall: true,
  },
  {
    patient_id: 'ICU-11', name: 'Sahil Kapoor', age: 48, gender: 'Female',
    room: 'Room 103', bed: 'BED-11', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 20,
    diagnosis: 'Severe dehydration', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Meera',
    latestHR: 63.4, latestSpO2: 94.1, latestTemp: 98.4, latestRR: 16.4, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-12', name: 'Priya Desai', age: 59, gender: 'Male',
    room: 'Room 103', bed: 'BED-12', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 13,
    diagnosis: 'Chest infection', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Meera',
    latestHR: 82.6, latestSpO2: 96.0, latestTemp: 98.1, latestRR: 16.3, latestEcg: 'minor_irregularity',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-13', name: 'Arjun Iyer', age: 44, gender: 'Male',
    room: 'Room 103', bed: 'BED-13', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 10,
    diagnosis: 'Kidney failure', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Aditi Sharma', assigned_nurse: 'Nurse Meera',
    latestHR: 70.9, latestSpO2: 94.0, latestTemp: 97.9, latestRR: 15.9, latestEcg: 'minor_irregularity',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-14', name: 'Leela Menon', age: 46, gender: 'Male',
    room: 'Room 103', bed: 'BED-14', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 19,
    diagnosis: 'Diabetic ketoacidosis', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Meera',
    latestHR: 58.9, latestSpO2: 93.7, latestTemp: 98.3, latestRR: 17.8, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-15', name: 'Manish Chawla', age: 52, gender: 'Non-binary',
    room: 'Room 103', bed: 'BED-15', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 16,
    diagnosis: 'Cardiac arrhythmia', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Priya',
    latestHR: 67.8, latestSpO2: 94.3, latestTemp: 98.5, latestRR: 16.0, latestEcg: 'minor_irregularity',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-16', name: 'Radha Nair', age: 75, gender: 'Female',
    room: 'Room 104', bed: 'BED-16', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 10,
    diagnosis: 'Post-surgery observation', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Sunita',
    latestHR: 72.2, latestSpO2: 93.9, latestTemp: 97.8, latestRR: 15.7, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-17', name: 'Naveen Reddy', age: 48, gender: 'Male',
    room: 'Room 104', bed: 'BED-17', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 18,
    diagnosis: 'Pulmonary embolism', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Meera',
    latestHR: 64.4, latestSpO2: 95.2, latestTemp: 98.5, latestRR: 16.3, latestEcg: 'minor_irregularity',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-18', name: 'Sana Khan', age: 49, gender: 'Male',
    room: 'Room 104', bed: 'BED-18', status: 'normal' as PatientStatus,
    severity: 'normal' as SeverityLevel, risk_score: 22,
    diagnosis: 'High-risk labor monitoring', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Arjun Mehta', assigned_nurse: 'Nurse Priya',
    latestHR: 70.5, latestSpO2: 97.3, latestTemp: 98.7, latestRR: 15.5, latestEcg: 'normal',
    alerts: [] as PatientAlert[], hasFall: false,
  },
  {
    patient_id: 'ICU-19', name: 'Varun Rao', age: 55, gender: 'Female',
    room: 'Room 104', bed: 'BED-19', status: 'critical' as PatientStatus,
    severity: 'critical' as SeverityLevel, risk_score: 77,
    diagnosis: 'Traumatic injury', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Priya',
    latestHR: 76.4, latestSpO2: 89.8, latestTemp: 99.6, latestRR: 22.7, latestEcg: 'minor_irregularity',
    alerts: [
      { second: 2, type: 'critical' as const, message: 'Severe hypoxia' },
      { second: 6, type: 'critical' as const, message: 'Acute distress' },
    ],
    hasFall: false,
  },
  {
    patient_id: 'ICU-20', name: 'Neha Kulkarni', age: 46, gender: 'Male',
    room: 'Room 104', bed: 'BED-20', status: 'warning' as PatientStatus,
    severity: 'warning' as SeverityLevel, risk_score: 76,
    diagnosis: 'Neurological evaluation', admission_date: '2026-07-10',
    assigned_doctor: 'Dr. Sushma Iyer', assigned_nurse: 'Nurse Priya',
    latestHR: 63.6, latestSpO2: 93.4, latestTemp: 98.2, latestRR: 17.3, latestEcg: 'normal',
    alerts: [
      { second: 3, type: 'warning' as const, message: 'SpO₂ dip' },
      { second: 7, type: 'warning' as const, message: 'Irregular rhythm' },
    ],
    hasFall: false,
  },
]

// ── Build sparkline from latest HR values (simulated trend) ────────────────
function makeSparkline(hr: number, status: PatientStatus): number[] {
  const base = hr
  if (status === 'critical') {
    return [base * 0.7, base * 0.8, base * 0.95, base * 1.1, base * 1.2, base * 1.15, base * 1.1, base]
  }
  if (status === 'warning') {
    return [base * 0.9, base * 0.95, base, base * 1.05, base * 1.08, base * 1.05, base * 1.02, base]
  }
  return [base * 0.98, base, base * 1.01, base * 0.99, base, base * 1.01, base, base * 0.99]
}

// ── Derive timeline events from alerts ─────────────────────────────────────
function buildEvents(p: typeof RAW_PATIENTS[0]): TimelineEvent[] {
  const events: TimelineEvent[] = [
    { time: '08:00 AM', label: 'Admitted', type: 'info' },
    { time: '08:30 AM', label: 'Vitals Normal', type: 'normal' },
  ]
  for (const a of p.alerts) {
    const t = 8 + Math.floor(a.second / 6)
    const min = (a.second * 10) % 60
    const ts = `0${t}:${min.toString().padStart(2, '0')} AM`
    events.push({
      time: ts,
      label: a.message.charAt(0).toUpperCase() + a.message.slice(1),
      type: a.type === 'critical' ? 'critical' : 'warning',
    })
  }
  if (p.status === 'critical') {
    events.push({ time: '09:44 AM', label: 'Critical Alert Generated', type: 'critical' })
  }
  return events
}

// ── Export: all 20 patients as VGPatient objects ───────────────────────────
export const allPatients: VGPatient[] = RAW_PATIENTS.map((p) => ({
  ...p,
  vitals: [],
  sparkline: makeSparkline(p.latestHR, p.status),
  events: buildEvents(p),
}))

// ── Filtered views ─────────────────────────────────────────────────────────
export const criticalPatients = allPatients.filter(
  (p) => p.status === 'critical' || p.severity === 'critical',
)

export const warningPatients = allPatients.filter(
  (p) => p.status === 'warning' || p.severity === 'high-risk' || p.severity === 'warning',
)

export const stablePatients = allPatients.filter(
  (p) => p.status === 'normal' && p.severity === 'normal',
)

// ── Alert cards (for nurse/doctor sidebars) ────────────────────────────────
export const alertCards: NurseAlertCard[] = allPatients
  .filter((p) => p.alerts.length > 0)
  .map((p) => ({
    id: `alert-${p.patient_id}`,
    patientId: p.patient_id,
    patientName: p.name,
    bed: p.bed,
    room: p.room,
    priority: (p.status === 'critical' ? 'critical' : 'warning') as 'critical' | 'warning',
    reasons: [...new Set(p.alerts.map((a) => a.message))],
    riskScore: p.risk_score,
    timestamp: p.status === 'critical' ? '09:44 AM' : '09:30 AM',
    accepted: false,
  }))
  .sort((a, b) => (a.priority === 'critical' ? -1 : 1) - (b.priority === 'critical' ? -1 : 1))

// ── Admin stats ────────────────────────────────────────────────────────────
export const adminStats = {
  total: allPatients.length,
  critical: criticalPatients.length,
  warning: warningPatients.length,
  stable: stablePatients.length,
  activeAlerts: alertCards.length,
}

// ── Room occupancy for admin ───────────────────────────────────────────────
export const roomSummary = ['Room 101', 'Room 102', 'Room 103', 'Room 104'].map((room) => {
  const roomPatients = allPatients.filter((p) => p.room === room)
  const criticalCount = roomPatients.filter((p) => p.status === 'critical').length
  const warningCount = roomPatients.filter((p) => p.status === 'warning').length
  return {
    room,
    total: roomPatients.length,
    critical: criticalCount,
    warning: warningCount,
    stable: roomPatients.length - criticalCount - warningCount,
    occupancy: `${roomPatients.length}/5`,
    occupancyPct: Math.round((roomPatients.length / 5) * 100),
  }
})
