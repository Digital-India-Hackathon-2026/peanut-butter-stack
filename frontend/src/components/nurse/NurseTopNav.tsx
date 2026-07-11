import { useState } from 'react'
import { Bell, Sun, Moon, LogOut, Shield, ChevronDown, AlertTriangle } from 'lucide-react'
import type { VGPatient } from '../../lib/nurseMockData'

interface NurseTopNavProps {
  criticalPatient?: VGPatient | null
  onViewAlert?: () => void
  darkMode?: boolean
  onToggleDark?: () => void
  onLogout?: () => void
  alertCount?: number
}

export function NurseTopNav({
  criticalPatient,
  onViewAlert,
  darkMode = false,
  onToggleDark,
  onLogout,
  alertCount = 0,
}: NurseTopNavProps) {
  const [showProfile, setShowProfile] = useState(false)

  return (
    <header className="nt-nav">
      {/* Brand */}
      <div className="nt-brand">
        <div className="nt-logo">
          <Shield size={18} color="#fff" strokeWidth={2.5} />
        </div>
        <div className="nt-brand-text">
          <span className="nt-brand-name">VitalGuard</span>
          <span className="nt-brand-sub">Smart Patient Monitoring</span>
        </div>
      </div>

      {/* Critical Alert Banner */}
      {criticalPatient ? (
        <div className="nt-critical-banner">
          <div className="nt-banner-left">
            <AlertTriangle size={16} className="nt-banner-icon" />
            <div>
              <span className="nt-banner-title">Critical Alert</span>
              <span className="nt-banner-msg">
                {criticalPatient.name} ({criticalPatient.patient_id} · {criticalPatient.bed})
                {criticalPatient.hasFall ? ' • Fall Detected' : ' • Acute Distress'}
                {' • '}SpO₂ {Math.round(criticalPatient.latestSpO2)}%
              </span>
            </div>
          </div>
          <button className="nt-banner-btn" onClick={onViewAlert}>
            View Alert
          </button>
        </div>
      ) : (
        <div className="nt-title-center">
          <span className="nt-dashboard-title">Nurse Dashboard</span>
        </div>
      )}

      {/* Right Actions */}
      <div className="nt-actions">
        <button className="nt-icon-btn" aria-label="Notifications">
          <Bell size={17} />
          {alertCount > 0 && <span className="nt-badge">{alertCount}</span>}
        </button>
        <button className="nt-icon-btn" onClick={onToggleDark} aria-label="Toggle theme">
          {darkMode ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <button
          className="nt-profile"
          onClick={() => setShowProfile((p) => !p)}
        >
          <div className="nt-avatar">
            <img
              src="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=80&q=80"
              alt="Nurse Priya"
            />
          </div>
          <div className="nt-profile-text">
            <span className="nt-profile-name">Nurse Priya</span>
            <span className="nt-profile-role">Nurse</span>
          </div>
          <ChevronDown size={13} className={`nt-chevron ${showProfile ? 'open' : ''}`} />
        </button>
        <button className="nt-logout-btn" onClick={onLogout} aria-label="Logout">
          <LogOut size={15} />
        </button>
      </div>
    </header>
  )
}

export default NurseTopNav
