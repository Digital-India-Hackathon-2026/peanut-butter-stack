import { motion } from 'framer-motion'
import type { PatientOverview } from '../types'

const statusColor = {
  normal: '#22c55e',
  warning: '#eab308',
  'high-risk': '#f97316',
  critical: '#ef4444',
}

interface PatientCardProps {
  patient: PatientOverview
  active?: boolean
  onClick: () => void
}

export function PatientCard({ patient, active, onClick }: PatientCardProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className={`patient-card ${active ? 'active' : ''}`}
    >
      <div className="patient-card-head">
        <img src={patient.photo} alt={patient.name} className="patient-photo" />
        <div>
          <p className="patient-name">{patient.name}</p>
          <p className="patient-meta">{patient.bed} • {patient.id}</p>
        </div>
      </div>
      <div className="patient-card-body">
        <span className="status-pill" style={{ background: `${statusColor[patient.status]}33`, color: statusColor[patient.status] }}>
          {patient.status.replace('-', ' ').toUpperCase()}
        </span>
        <span className="risk-value">Risk {patient.riskScore}%</span>
      </div>
    </motion.button>
  )
}
