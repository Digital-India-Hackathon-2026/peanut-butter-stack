import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, LogOut, Bell, Search, Grid2x2, Users, FileText, BarChart3, Building2, ArrowUpRight, AlertTriangle, Phone, MessageSquare, RefreshCw, CheckCircle, XCircle, Clock } from 'lucide-react'
import { allPatients, adminStats, roomSummary, alertCards } from '../lib/nurseMockData'
import { logout } from '../lib/auth'

function statusPillClass(status: string) {
  if (status === 'critical') return 'admin-status-pill--critical'
  if (status === 'warning') return 'admin-status-pill--warning'
  return 'admin-status-pill--normal'
}

function riskFillClass(risk: number) {
  if (risk >= 75) return 'admin-risk-fill--critical'
  if (risk >= 40) return 'admin-risk-fill--warning'
  return 'admin-risk-fill--normal'
}

function riskValClass(risk: number) {
  if (risk >= 75) return 'admin-risk-val--critical'
  if (risk >= 40) return 'admin-risk-val--warning'
  return 'admin-risk-val--normal'
}

// ── Twilio API base ───────────────────────────────────────────────────────
const VITALS_API = 'http://localhost:8001'

interface DispatchEntry {
  alert_id: string
  timestamp: string
  patient_id: string
  patient_name: string
  bed: string
  severity: string
  channel: 'call' | 'sms'
  recipient_role: 'doctor' | 'nurse'
  recipient_number: string
  reasons: string[]
  status: 'sent' | 'failed' | 'cooldown' | 'dry_run'
  error: string | null
  twilio_sid: string | null
}

export function AdminDashboardPage() {
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // ── Alert dispatch state ────────────────────────────────────────────────
  const [dispatchLog, setDispatchLog] = useState<DispatchEntry[]>([])
  const [sending, setSending] = useState<Record<string, boolean>>({})
  const [logLoading, setLogLoading] = useState(false)

  // Fetch alert history from backend on mount and every 30s
  const fetchHistory = useCallback(async () => {
    setLogLoading(true)
    try {
      const res = await fetch(`${VITALS_API}/alerts/history?limit=20`)
      if (res.ok) {
        const data = await res.json()
        setDispatchLog(data.alerts ?? [])
      }
    } catch {
      // Backend not running — silently ignore
    } finally {
      setLogLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 30_000)
    return () => clearInterval(interval)
  }, [fetchHistory])

  // Dispatch a test call or SMS from the table
  const handleDispatch = useCallback(async (
    bedId: string,
    channel: 'call' | 'sms',
    severity: string,
  ) => {
    const key = `${bedId}-${channel}`
    setSending(prev => ({ ...prev, [key]: true }))
    try {
      const endpoint = channel === 'call' ? '/alerts/test-call' : '/alerts/test-sms'
      const res = await fetch(`${VITALS_API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bed_id: bedId, severity, reset_cooldown: true }),
      })
      if (res.ok) {
        // Refresh log after dispatch
        setTimeout(fetchHistory, 600)
      }
    } catch {
      // Backend not running
    } finally {
      setSending(prev => ({ ...prev, [key]: false }))
    }
  }, [fetchHistory])

  const callsSent = dispatchLog.filter(e => e.channel === 'call' && e.status === 'sent').length
  const smsSent   = dispatchLog.filter(e => e.channel === 'sms'  && e.status === 'sent').length

  return (
    <div className="admin-shell">
      <header className="admin-topnav">
        <div className="admin-brand-block">
          <div className="admin-brand-mark">
            <Shield size={18} strokeWidth={2.5} />
          </div>
          <div>
            <p className="admin-brand-name">VitalGuard</p>
            <p className="admin-brand-sub">Administration</p>
          </div>
        </div>

        <nav className="admin-nav-tabs" aria-label="Administrative navigation">
          <span className="admin-nav-tab active">
            <Grid2x2 size={14} />
            Dashboard
          </span>
          <span className="admin-nav-tab">
            <Users size={14} />
            Patients
          </span>
          <span className="admin-nav-tab">
            <AlertTriangle size={14} />
            Alerts
          </span>
          <span className="admin-nav-tab">
            <BarChart3 size={14} />
            Analytics
          </span>
          <span className="admin-nav-tab">
            <FileText size={14} />
            Reports
          </span>
          <span className="admin-nav-tab">
            <Building2 size={14} />
            Administration
          </span>
        </nav>

        <div className="admin-topnav-actions">
          <div className="admin-search-chip">
            <Search size={14} />
            <span>Search patients, rooms, alerts</span>
          </div>
          <button type="button" className="admin-icon-button" aria-label="Notifications">
            <Bell size={16} />
          </button>
          <button type="button" className="admin-icon-button" onClick={handleLogout} aria-label="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <main className="admin-page">
        <section className="admin-hero">
          <div>
            <p className="admin-breadcrumb">Administration / Dashboard</p>
            <h1>Hospital command center</h1>
            <p className="admin-subtitle">
              Oversee occupancy, risk levels, and active alerts across every ward from one premium control surface.
            </p>
          </div>
          <div className="admin-hero-actions">
            <button type="button" className="secondary-button small" onClick={() => navigate('/nurse')}>
              Nurse View
            </button>
            <button type="button" className="primary-button admin-primary-action" onClick={handleLogout}>
              <LogOut size={15} />
              Logout
            </button>
          </div>
        </section>

        <section className="admin-metrics-grid">
          <article className="admin-metric-card">
            <div className="admin-metric-top">
              <span className="admin-metric-label">Total Patients</span>
              <span className="admin-metric-trend up">+4.2%</span>
            </div>
            <strong className="admin-metric-value admin-metric-value--blue">{adminStats.total}</strong>
            <span className="admin-metric-caption">Across all wards</span>
            <div className="admin-mini-bars">
              <span style={{ height: '30%' }} />
              <span style={{ height: '48%' }} />
              <span style={{ height: '38%' }} />
              <span style={{ height: '62%' }} />
              <span style={{ height: '76%' }} />
              <span style={{ height: '54%' }} />
            </div>
          </article>

          <article className="admin-metric-card">
            <div className="admin-metric-top">
              <span className="admin-metric-label">Critical</span>
              <span className="admin-metric-trend danger">Immediate</span>
            </div>
            <strong className="admin-metric-value admin-metric-value--danger">{adminStats.critical}</strong>
            <span className="admin-metric-caption">Requires escalation</span>
            <div className="admin-mini-bars admin-mini-bars--danger">
              <span style={{ height: '22%' }} />
              <span style={{ height: '44%' }} />
              <span style={{ height: '58%' }} />
              <span style={{ height: '72%' }} />
              <span style={{ height: '64%' }} />
              <span style={{ height: '84%' }} />
            </div>
          </article>

          <article className="admin-metric-card">
            <div className="admin-metric-top">
              <span className="admin-metric-label">Warning</span>
              <span className="admin-metric-trend amber">Watch</span>
            </div>
            <strong className="admin-metric-value admin-metric-value--amber">{adminStats.warning}</strong>
            <span className="admin-metric-caption">Under observation</span>
            <div className="admin-mini-bars admin-mini-bars--amber">
              <span style={{ height: '26%' }} />
              <span style={{ height: '42%' }} />
              <span style={{ height: '32%' }} />
              <span style={{ height: '58%' }} />
              <span style={{ height: '48%' }} />
              <span style={{ height: '66%' }} />
            </div>
          </article>

          <article className="admin-metric-card">
            <div className="admin-metric-top">
              <span className="admin-metric-label">Stable</span>
              <span className="admin-metric-trend up">Healthy</span>
            </div>
            <strong className="admin-metric-value admin-metric-value--green">{adminStats.stable}</strong>
            <span className="admin-metric-caption">Clinically stable</span>
            <div className="admin-mini-bars admin-mini-bars--green">
              <span style={{ height: '40%' }} />
              <span style={{ height: '52%' }} />
              <span style={{ height: '46%' }} />
              <span style={{ height: '56%' }} />
              <span style={{ height: '50%' }} />
              <span style={{ height: '60%' }} />
            </div>
          </article>

          <article className="admin-metric-card">
            <div className="admin-metric-top">
              <span className="admin-metric-label">Active Alerts</span>
              <span className="admin-metric-trend danger">Priority</span>
            </div>
            <strong className="admin-metric-value admin-metric-value--purple">{adminStats.activeAlerts}</strong>
            <span className="admin-metric-caption">Pending review</span>
            <div className="admin-mini-bars admin-mini-bars--purple">
              <span style={{ height: '20%' }} />
              <span style={{ height: '34%' }} />
              <span style={{ height: '44%' }} />
              <span style={{ height: '60%' }} />
              <span style={{ height: '72%' }} />
              <span style={{ height: '78%' }} />
            </div>
          </article>
        </section>

        <section className="admin-content-grid">
          <div className="admin-column">
            <section className="admin-panel">
              <div className="panel-header admin-panel-header">
                <div>
                  <h2>Ward occupancy</h2>
                  <p>Room utilization and patient mix across the facility.</p>
                </div>
                <span className="panel-header-meta">Live facility view</span>
              </div>
              <div className="admin-room-grid">
                {roomSummary.map((r) => (
                  <article key={r.room} className="admin-room-card">
                    <div className="admin-room-card-top">
                      <div>
                        <p className="admin-room-name">{r.room}</p>
                        <p className="admin-room-subtitle">{r.total} patients currently assigned</p>
                      </div>
                      <span className="admin-room-occ">{r.occupancy}</span>
                    </div>
                    <div className="admin-room-bar-row">
                      <div className="admin-room-bar">
                        <div className="admin-room-fill" style={{ width: `${r.occupancyPct}%` }} />
                      </div>
                    </div>
                    <div className="admin-room-chips">
                      {r.critical > 0 && <span className="admin-room-chip admin-room-chip--critical">{r.critical} Critical</span>}
                      {r.warning > 0 && <span className="admin-room-chip admin-room-chip--warning">{r.warning} Warning</span>}
                      <span className="admin-room-chip admin-room-chip--stable">{r.stable} Stable</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="admin-panel">
              <div className="panel-header admin-panel-header">
                <div>
                  <h2>Recent alerts</h2>
                  <p>Priority issues derived from active patient conditions.</p>
                </div>
                <span className="panel-header-meta">{alertCards.length} open alerts</span>
              </div>
              <div className="admin-alert-list">
                {alertCards.slice(0, 5).map((alert) => (
                  <article key={alert.id} className={`admin-alert-card admin-alert-card--${alert.priority}`}>
                    <div className="admin-alert-card-top">
                      <div>
                        <p className="admin-alert-patient">{alert.patientName}</p>
                        <p className="admin-alert-meta">{alert.room} · {alert.bed}</p>
                      </div>
                      <span className={`admin-status-pill ${statusPillClass(alert.priority)}`}>
                        {alert.priority.toUpperCase()}
                      </span>
                    </div>
                    <div className="admin-alert-reasons">
                      {alert.reasons.map((reason) => (
                        <span key={reason} className="admin-alert-reason">{reason}</span>
                      ))}
                    </div>
                    <div className="admin-alert-card-bottom">
                      <span className="admin-alert-risk">Risk {alert.riskScore}%</span>
                      <span className="admin-alert-time">{alert.timestamp}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <div className="admin-column admin-column--wide">
            <section className="admin-panel admin-table-panel">
              <div className="panel-header admin-panel-header">
                <div>
                  <h2>All patient records</h2>
                  <p>{allPatients.length} patients · VitalGuard Synthetic Test Facility</p>
                </div>
                <div className="admin-table-actions">
                  <button type="button" className="secondary-button small">Export</button>
                  <button type="button" className="primary-button admin-primary-action small">
                    <ArrowUpRight size={15} />
                    Add Patient
                  </button>
                </div>
              </div>
              <div className="admin-table-wrap">
                <table className="admin-data-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Patient Name</th>
                      <th>Age / Gender</th>
                      <th>Room / Bed</th>
                      <th>Diagnosis</th>
                      <th>Assigned Doctor</th>
                      <th>Nurse</th>
                      <th>HR (bpm)</th>
                      <th>SpO₂ %</th>
                      <th>ECG</th>
                      <th>Status</th>
                      <th>Risk Score</th>
                      <th>Alert Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allPatients.map((p) => (
                      <tr
                        key={p.patient_id}
                        className={
                          p.status === 'critical'
                            ? 'admin-row--critical'
                            : p.status === 'warning'
                            ? 'admin-row--warning'
                            : ''
                        }
                      >
                        <td>
                          <strong className="admin-id">{p.patient_id}</strong>
                        </td>
                        <td>
                          <strong>{p.name}</strong>
                        </td>
                        <td className="admin-cell-muted">
                          {p.age}y · {p.gender}
                        </td>
                        <td className="admin-cell-muted">
                          {p.room}
                          <br />
                          <span>{p.bed}</span>
                        </td>
                        <td className="admin-diagnosis-cell">{p.diagnosis}</td>
                        <td className="admin-cell-muted">{p.assigned_doctor}</td>
                        <td className="admin-cell-muted">{p.assigned_nurse}</td>
                        <td>
                          <strong>{Math.round(p.latestHR)}</strong>
                        </td>
                        <td>
                          <strong className={p.latestSpO2 < 90 ? 'admin-spo2--danger' : p.latestSpO2 < 94 ? 'admin-spo2--warning' : 'admin-spo2--normal'}>
                            {p.latestSpO2.toFixed(1)}
                          </strong>
                        </td>
                        <td className={p.latestEcg !== 'normal' ? 'admin-ecg--warning' : 'admin-ecg--normal'}>
                          {p.latestEcg === 'normal' ? 'Normal' : 'Irregular'}
                        </td>
                        <td>
                          <span className={`admin-status-pill ${statusPillClass(p.status)}`}>
                            {p.status.charAt(0).toUpperCase() + p.status.slice(1)}
                          </span>
                        </td>
                        <td>
                          <div className="admin-risk-bar-wrap">
                            <div className="admin-risk-bar">
                              <div className={`admin-risk-fill ${riskFillClass(p.risk_score)}`} style={{ width: `${p.risk_score}%` }} />
                            </div>
                            <span className={`admin-risk-val ${riskValClass(p.risk_score)}`}>{p.risk_score}%</span>
                          </div>
                        </td>
                        <td>
                          <div className="admin-actions-cell">
                            <button
                              id={`alert-call-${p.patient_id}`}
                              type="button"
                              className="admin-alert-btn admin-alert-btn--call"
                              title={`Call doctor for ${p.name}`}
                              disabled={sending[`${p.bed}-call`] || (p.status === 'normal')}
                              onClick={() => handleDispatch(p.bed, 'call', p.status)}
                            >
                              {sending[`${p.bed}-call`]
                                ? <span className="dispatch-sending-dot" />
                                : <Phone size={11} />}
                              Call Dr.
                            </button>
                            <button
                              id={`alert-sms-${p.patient_id}`}
                              type="button"
                              className="admin-alert-btn admin-alert-btn--sms"
                              title={`SMS nurse for ${p.name}`}
                              disabled={sending[`${p.bed}-sms`]}
                              onClick={() => handleDispatch(p.bed, 'sms', p.status)}
                            >
                              {sending[`${p.bed}-sms`]
                                ? <span className="dispatch-sending-dot" />
                                : <MessageSquare size={11} />}
                              SMS Nurse
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </section>

        {/* ── Twilio Alert Dispatch Log ──────────────────────────────────── */}
        <section className="admin-panel admin-dispatch-panel">
          <div className="panel-header admin-panel-header">
            <div>
              <h2>Twilio alert dispatch log</h2>
              <p>Recent voice calls to doctors and SMS messages to nurses dispatched by VitalGuard.</p>
            </div>
            <button
              id="refresh-dispatch-log"
              type="button"
              className="secondary-button small"
              onClick={fetchHistory}
              disabled={logLoading}
              aria-label="Refresh alert log"
            >
              <RefreshCw size={13} style={{ marginRight: 4, animation: logLoading ? 'spin 1s linear infinite' : 'none' }} />
              Refresh
            </button>
          </div>

          {/* Summary strip */}
          <div className="admin-dispatch-summary">
            <div className="admin-dispatch-summary-item">
              <Phone size={14} color="#7c3aed" />
              <strong>{callsSent}</strong>
              <span>doctor calls dispatched</span>
            </div>
            <div className="admin-dispatch-summary-item">
              <MessageSquare size={14} color="#059669" />
              <strong>{smsSent}</strong>
              <span>nurse SMS dispatched</span>
            </div>
            <div className="admin-dispatch-summary-item" style={{ marginLeft: 'auto' }}>
              <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>
                Cooldown: 5 min · Auto-triggered on critical/warning vitals
              </span>
            </div>
          </div>

          {dispatchLog.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: '0.86rem', padding: '12px 0' }}>
              {logLoading
                ? 'Loading alert history…'
                : 'No alerts dispatched yet. Alerts fire automatically when patient vitals hit critical or warning thresholds.'}
            </p>
          ) : (
            <div className="admin-table-wrap">
              <table className="dispatch-log-table">
                <thead>
                  <tr>
                    <th>Alert ID</th>
                    <th>Time</th>
                    <th>Patient</th>
                    <th>Bed</th>
                    <th>Severity</th>
                    <th>Channel</th>
                    <th>Recipient</th>
                    <th>Status</th>
                    <th>Triggers</th>
                    <th>Twilio SID</th>
                  </tr>
                </thead>
                <tbody>
                  {dispatchLog.map(entry => (
                    <tr key={entry.alert_id}>
                      <td><strong style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{entry.alert_id}</strong></td>
                      <td style={{ color: 'var(--muted)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>{entry.timestamp}</td>
                      <td><strong>{entry.patient_name}</strong></td>
                      <td style={{ color: 'var(--muted)' }}>{entry.bed}</td>
                      <td>
                        <span className={`admin-status-pill ${statusPillClass(entry.severity)}`}>
                          {entry.severity.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span className={`admin-dispatch-badge admin-dispatch-badge--${entry.channel}`}>
                          {entry.channel === 'call'
                            ? <><Phone size={10} /> Call</>  
                            : <><MessageSquare size={10} /> SMS</>}
                        </span>
                      </td>
                      <td style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>
                        {entry.recipient_role === 'doctor' ? '🩺 Doctor' : '🏥 Nurse'}
                        {entry.recipient_number && <><br /><span style={{ fontSize: '0.72rem' }}>{entry.recipient_number}</span></>}
                      </td>
                      <td>
                        <span className={`admin-dispatch-badge admin-dispatch-badge--${entry.status}`}>
                          {entry.status === 'sent' && <CheckCircle size={10} />}
                          {entry.status === 'failed' && <XCircle size={10} />}
                          {entry.status === 'cooldown' && <Clock size={10} />}
                          {entry.status}
                        </span>
                        {entry.error && (
                          <div style={{ color: '#dc2626', fontSize: '0.7rem', marginTop: 2 }}>{entry.error}</div>
                        )}
                      </td>
                      <td style={{ fontSize: '0.76rem', color: 'var(--muted)', maxWidth: 200 }}>
                        {entry.reasons.join('; ') || '—'}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'var(--muted)' }}>
                        {entry.twilio_sid ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default AdminDashboardPage
