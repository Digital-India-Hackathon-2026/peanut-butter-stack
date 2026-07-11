import { Search, Users } from 'lucide-react'
import type { VGPatient } from '../../lib/nurseMockData'
import { SparklineChart } from './SparklineChart'

interface PatientListSidebarProps {
  patients: VGPatient[]
  selectedId: string
  onSelect: (id: string) => void
}

const statusLabel: Record<string, string> = {
  normal: 'STABLE',
  warning: 'WARNING',
  critical: 'CRITICAL',
}

const badgeClass: Record<string, string> = {
  normal: 'ps-badge--stable',
  warning: 'ps-badge--warning',
  critical: 'ps-badge--critical',
}

const cardClass: Record<string, string> = {
  normal: 'ps-card--stable',
  warning: 'ps-card--warning',
  critical: 'ps-card--critical',
}

const riskClass: Record<string, string> = {
  normal: 'ps-risk--normal',
  warning: 'ps-risk--warning',
  critical: 'ps-risk--critical',
}

const sparkStatus: Record<string, 'stable' | 'warning' | 'high-risk' | 'critical'> = {
  normal: 'stable',
  warning: 'warning',
  critical: 'critical',
}

export function PatientListSidebar({ patients, selectedId, onSelect }: PatientListSidebarProps) {
  return (
    <aside className="ps-sidebar">
      {/* Header */}
      <div className="ps-header">
        <span className="ps-header-label">ASSIGNED PATIENTS</span>
      </div>

      {/* Search */}
      <div className="ps-search-wrap">
        <Search size={14} className="ps-search-icon" />
        <input
          className="ps-search"
          type="search"
          placeholder="Search patient..."
          aria-label="Search patients"
        />
      </div>

      {/* Patient Cards — no avatar images */}
      <div className="ps-list">
        {patients.map((p) => {
          const isSelected = p.patient_id === selectedId
          const status = p.status
          return (
            <button
              key={p.patient_id}
              className={`ps-card ${isSelected ? 'ps-card--selected' : ''} ${cardClass[status] ?? 'ps-card--stable'}`}
              onClick={() => onSelect(p.patient_id)}
              aria-label={`Select patient ${p.name}`}
            >
              {/* Pulsing dot for critical */}
              {status === 'critical' && <span className="ps-pulse" />}

              {/* Top row: name + badge */}
              <div className="ps-info-top">
                <span className="ps-name">{p.name}</span>
                <span className={`ps-badge ${badgeClass[status] ?? 'ps-badge--stable'}`}>
                  {statusLabel[status] ?? 'STABLE'}
                </span>
              </div>

              {/* ID + bed */}
              <div className="ps-id">
                {p.patient_id} · {p.bed}
              </div>

              {/* Risk + sparkline */}
              <div className="ps-info-bottom">
                <span className={`ps-risk ${riskClass[status] ?? 'ps-risk--normal'}`}>
                  Risk: <strong>{p.risk_score}%</strong>
                </span>
                <SparklineChart
                  data={p.sparkline}
                  status={sparkStatus[status] ?? 'stable'}
                  width={72}
                  height={22}
                />
              </div>
            </button>
          )
        })}
      </div>

      {/* Footer */}
      <button className="ps-footer-btn">
        <Users size={15} />
        <span>View All Patients</span>
      </button>
    </aside>
  )
}

export default PatientListSidebar
