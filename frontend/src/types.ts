export type Role = 'nurse' | 'doctor' | 'admin'

export type PatientStatus = 'normal' | 'warning' | 'high-risk' | 'critical'

export interface PatientOverview {
  id: string
  name: string
  bed: string
  photo: string
  status: PatientStatus
  riskScore: number
  age: number
  gender: string
  ward: string
  doctor: string
  nurse: string
  condition: string
  diagnosis: string
  medications: string[]
  allergies: string[]
  emergencyContact: string
  vitals: VitalsSnapshot
  videoUrl?: string
  icuId?: string
  bp?: string
  respiratoryRate?: string
  temperature?: string
  latestSpO2?: number
  latestHR?: number
  currentAlert?: string
  events: Array<{ time: string; label: string; details: string }>
}

export interface VitalsSnapshot {
  heartRate: number
  spo2: number
  ecg: number[]
  severity: 'normal' | 'warning' | 'critical'
  riskScore: number
  status: PatientStatus
}
