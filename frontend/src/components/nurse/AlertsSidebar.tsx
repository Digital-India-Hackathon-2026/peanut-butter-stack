import { useState } from 'react'
import type { NurseAlertCard } from '../../lib/nurseMockData'
import { Filter, Users, Activity } from 'lucide-react'

interface AlertsSidebarProps {
  alerts: NurseAlertCard[]
  onViewCamera?: (patientId: string) => void
  onViewDetails?: (patientId: string) => void
  onAcceptAlert?: (alertId: string) => void
}

const priorityLabel: Record<NurseAlertCard['priority'], string> = {
  critical: 'CRITICAL',
  warning: 'WARNING',
}

const priorityBadgeClass: Record<NurseAlertCard['priority'], string> = {
  critical: 'al-badge--critical',
  warning: 'al-badge--warning',
}

function ReasonIcon({ reason }: { reason: string }) {
  const lower = reason.toLowerCase()
  if (lower.includes('fall')) return <span className="al-reason-icon al-reason-icon--red">⚡</span>
  if (lower.includes('distress') || lower.includes('hypoxia'))
    return <span className="al-reason-icon al-reason-icon--red">⚠</span>
  if (lower.includes('rhythm') || lower.includes('ecg'))
    return <span className="al-reason-icon al-reason-icon--orange">⚠</span>
  return <span className="al-reason-icon al-reason-icon--yellow">⚠</span>
}

export function AlertsSidebar({ alerts, onViewCamera, onViewDetails, onAcceptAlert }: AlertsSidebarProps) {
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set())

  const handleAccept = (id: string) => {
    setAcceptedIds((prev) => new Set(prev).add(id))
    onAcceptAlert?.(id)
  }

  return (
    <aside className="al-sidebar">
      {/* Header */}
      <div className="al-header">
        <div className="al-header-left">
          <span className="al-header-title">CURRENT ALERTS</span>
          <span className="al-count-badge">{alerts.length}</span>
        </div>
        <button className="al-filter-btn" aria-label="Filter alerts">
          <Filter size={14} />
        </button>
      </div>

      {/* Alert Cards */}
      <div className="al-list">
        {alerts.map((alert) => {
          const accepted = acceptedIds.has(alert.id)
          return (
            <div
              key={alert.id}
              className={`al-card al-card--${alert.priority} ${accepted ? 'al-card--accepted' : ''}`}
            >
              {/* Top */}
              <div className="al-card-top">
                <div className="al-card-identity">
                  <span className="al-patient-name">{alert.patientName}</span>
                  <span className="al-bed">{alert.room} · {alert.bed}</span>
                </div>
                <span className={`al-badge ${priorityBadgeClass[alert.priority]}`}>
                  {priorityLabel[alert.priority]}
                </span>
              </div>

              {/* Reasons */}
              <div className="al-reasons">
                {alert.reasons.map((r) => (
                  <div key={r} className="al-reason-row">
                    <ReasonIcon reason={r} />
                    <span className="al-reason-text">{r}</span>
                  </div>
                ))}
              </div>

              {/* Risk + timestamp */}
              <div className="al-card-meta">
                <span className="al-risk">
                  Risk Score:{' '}
                  <strong className={`al-risk-val--${alert.priority}`}>{alert.riskScore}%</strong>
                </span>
                <span className="al-time">{alert.timestamp}</span>
              </div>

              {/* Actions */}
              {accepted ? (
                <div className="al-accepted-strip">
                  <Activity size={13} />
                  <span>Being Handled</span>
                </div>
              ) : (
                <div className="al-actions">
                  {alert.priority === 'critical' && (
                    <button
                      className="al-btn al-btn--camera"
                      onClick={() => onViewCamera?.(alert.patientId)}
                    >
                      View Camera
                    </button>
                  )}
                  <button
                    className="al-btn al-btn--details"
                    onClick={() => onViewDetails?.(alert.patientId)}
                  >
                    View Details
                  </button>
                  <button className="al-btn al-btn--accept" onClick={() => handleAccept(alert.id)}>
                    Accept Alert
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <button className="al-footer-btn">
        <Users size={15} />
        <span>View All Alerts</span>
      </button>
    </aside>
  )
}

export default AlertsSidebar
