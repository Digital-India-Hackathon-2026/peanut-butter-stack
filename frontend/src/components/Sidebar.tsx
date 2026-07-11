import type { PatientOverview } from '../types'
import { PatientCard } from './PatientCard'

interface SidebarProps {
  patients: PatientOverview[]
  selected: string
  onSelect: (id: string) => void
}

export function Sidebar({ patients, selected, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">VG</div>
        <div>
          <p className="brand-title">VitalGuard</p>
          <p className="brand-subtitle">ICU Command</p>
        </div>
      </div>
      <div className="sidebar-section">
        <p className="section-title">Assigned Patients</p>
        <div className="patient-list">
          {patients.map((patient) => (
            <PatientCard
              key={patient.id}
              patient={patient}
              active={patient.id === selected}
              onClick={() => onSelect(patient.id)}
            />
          ))}
        </div>
      </div>
    </aside>
  )
}
