import type { PatientOverview } from '../types'

type AlertPriority = 'normal' | 'warning' | 'critical'

export const patientList: PatientOverview[] = [
  {
    id: 'ICU-01',
    name: 'Hansika',
    bed: 'BED-03',
    photo: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&q=80',
    status: 'normal',
    riskScore: 12,
    age: 58,
    gender: 'Male',
    ward: 'ICU',
    doctor: 'Dr. Aditi Sharma',
    nurse: 'Nurse Priya',
    condition: 'Post-operative monitoring',
    diagnosis: 'Stable after abdominal surgery',
    medications: ['Antibiotics', 'Pain management', 'IV fluids'],
    allergies: ['Penicillin'],
    emergencyContact: 'Karan Mehta — +91 98765 43210',
    vitals: {
      heartRate: 76,
      spo2: 98,
      ecg: [72, 74, 74, 76, 75, 77],
      severity: 'normal',
      riskScore: 12,
      status: 'normal',
    },
    icuId: 'P001',
    bp: '120/80',
    respiratoryRate: '16',
    temperature: '98.6°F',
    currentAlert: 'None',
    events: [
      { time: '09:15', label: 'Normal', details: 'Stable vitals' },
      { time: '09:42', label: 'Position Check', details: 'Patient repositioned after rest' },
      { time: '09:58', label: 'Vitals Normal', details: 'All readings within range' },
    ],
  },
  {
    id: 'ICU-02',
    name: 'Maheshwari',
    bed: 'BED-05',
    photo: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=120&q=80',
    status: 'warning',
    riskScore: 34,
    age: 45,
    gender: 'Male',
    ward: 'ICU',
    doctor: 'Dr. Arjun Mehta',
    nurse: 'Nurse Sunita',
    condition: 'Cardiac monitoring',
    diagnosis: 'Atrial fibrillation',
    medications: ['Beta blockers', 'Anticoagulants'],
    allergies: ['None'],
    emergencyContact: 'Rahul Nair — +91 91234 56789',
    icuId: 'P002',
    bp: '130/88',
    respiratoryRate: '18',
    temperature: '99.2°F',
    currentAlert: 'Arrhythmia detected',
    vitals: {
      heartRate: 89,
      spo2: 94,
      ecg: [86, 88, 92, 90, 89, 91],
      severity: 'warning',
      riskScore: 34,
      status: 'warning',
    },
    events: [
      { time: '08:50', label: 'Stable', details: 'Routine check' },
      { time: '10:10', label: 'ECG Warning', details: 'Minor irregularity' },
    ],
  },
  {
    id: 'ICU-03',
    name: 'Pavan',
    bed: 'BED-07',
    photo: 'https://images.unsplash.com/photo-1541233349642-6e425fe6190e?auto=format&fit=crop&w=120&q=80',
    status: 'critical',
    riskScore: 78,
    age: 63,
    gender: 'Female',
    ward: 'ICU',
    doctor: 'Dr. Sushma Iyer',
    nurse: 'Nurse Meera',
    condition: 'Acute cardiac distress',
    diagnosis: 'Potential myocardial infarction',
    medications: ['Aspirin', 'Nitroglycerin', 'Statins'],
    allergies: ['Sulfa drugs'],
    emergencyContact: 'Anita Kumar — +91 99876 54321',
    vitals: {
      heartRate: 118,
      spo2: 88,
      ecg: [106, 112, 121, 118, 124, 130],
      severity: 'critical',
      riskScore: 78,
      status: 'critical',
    },
    videoUrl: '/fall.mp4',
    icuId: 'P003',
    bp: '90/60',
    respiratoryRate: '24',
    temperature: '100.8°F',
    currentAlert: 'SpO₂ dropped to 82%',
    events: [
      { time: '09:00', label: 'Critical', details: 'ECG abnormality detected' },
      { time: '09:12', label: 'SpO₂ Low', details: 'SpO₂ dropped to 89%' },
      { time: '09:20', label: 'Fall Detected', details: 'Patient fell in bed during repositioning' },
    ],
  },
]

interface AlertItem {
  patientId: string
  patientName: string
  bed: string
  priority: AlertPriority
  riskScore: number
  reasons: string[]
}

export const alerts: AlertItem[] = [
  {
    patientId: 'ICU-03',
    patientName: 'Pavan',
    bed: 'BED-07',
    priority: 'critical',
    riskScore: 78,
    reasons: ['Fall Detected', 'ECG Abnormal', 'SpO₂ Low'],
  },
  {
    patientId: 'ICU-02',
    patientName: 'Maheshwari',
    bed: 'BED-05',
    priority: 'warning',
    riskScore: 34,
    reasons: ['ECG Irregularity'],
  },
]

export const summaryCards = [
  { label: 'Total Patients', value: 42, accent: 'blue' },
  { label: 'Critical Patients', value: 5, accent: 'rose' },
  { label: 'Occupied Beds', value: 38, accent: 'cyan' },
  { label: 'Available Beds', value: 4, accent: 'emerald' },
]

export const adminOverviewCards = [
  { label: 'Critical Patients', value: 28, accent: 'rose' },
  { label: 'Under Observation', value: 146, accent: 'blue' },
  { label: 'Stable Patients', value: 1074, accent: 'emerald' },
  { label: 'Active Alerts', value: 12, accent: 'cyan' },
  { label: 'Staff On Duty', value: 456, accent: 'blue' },
]

export const wardStatus = [
  { ward: 'ICU', occupancy: '91%', patients: '22/24', alerts: 5, trend: 'up' },
  { ward: 'Emergency', occupancy: '82%', patients: '18/22', alerts: 4, trend: 'up' },
  { ward: 'Neurology', occupancy: '68%', patients: '26/40', alerts: 0, trend: 'stable' },
  { ward: 'General', occupancy: '54%', patients: '32/60', alerts: 1, trend: 'stable' },
  { ward: 'Orthopedics', occupancy: '48%', patients: '19/40', alerts: 2, trend: 'down' },
]

export const adminCriticalAlerts = [
  { patient: '#103', message: 'SpO₂ dropped to 82%', severity: 'High', time: '10:26 AM' },
  { patient: '#227', message: 'Fall Detected', severity: 'High', time: '10:23 AM' },
  { patient: '#145', message: 'Arrhythmia Detected', severity: 'Medium', time: '10:18 AM' },
  { patient: '#312', message: 'High Heart Rate', severity: 'Medium', time: '10:15 AM' },
  { patient: '#408', message: 'Nurse Call Pending', severity: 'Low', time: '10:10 AM' },
]

export const adminCorrelationItems = [
  { label: 'Speech Abnormality', value: 'Detected', status: 'High' },
  { label: 'Cough Frequency', value: 'High', status: 'Medium' },
  { label: 'Heart Rate Spike', value: '120 bpm', status: 'High' },
  { label: 'SpO₂ Drop', value: '82%', status: 'High' },
  { label: 'ECG Abnormality', value: 'Irregular Rhythm', status: 'High' },
]

export const adminQuickActions = [
  { label: 'Add New Patient' },
  { label: 'Bed Management' },
  { label: 'Emergency Broadcast' },
  { label: 'Code Blue' },
  { label: 'View All Alerts' },
]
