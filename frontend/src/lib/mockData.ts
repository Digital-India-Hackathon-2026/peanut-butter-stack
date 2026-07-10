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
    videoUrl: 'http://127.0.0.1:8001/fall.mp4',
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
