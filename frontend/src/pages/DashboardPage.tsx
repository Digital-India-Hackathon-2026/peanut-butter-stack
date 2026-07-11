import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { ArrowUpRight, ShieldCheck, Search } from 'lucide-react'
import { logout } from '../lib/auth'
import { patientList, adminOverviewCards, wardStatus, adminCriticalAlerts, adminCorrelationItems, adminQuickActions } from '../lib/mockData'
import { Sidebar } from '../components/Sidebar'
import { DashboardHeader } from '../components/DashboardHeader'
import { StatusCard } from '../components/StatusCard'
import { FeatureCard } from '../components/FeatureCard'

interface AudioEvent {
  patient: string
  patient_name: string | null
  doctor: string | null
  doctor_notified: boolean
  event: string
  severity: 'normal' | 'warning' | 'critical'
  confidence: number
  matched_phrase: string | null
  transcript: string | null
  time: string
  error?: string
}

const patientDetails = patientList[0]
const defaultAudioPatient = {
  id: 'ICU-10',
  name: 'Devika Nair',
  doctor: 'Dr. Sushma Iyer',
}

const devikaDefaultPatientId = patientList.find((item) => item.name === 'Devika Nair')?.id ?? patientList[0].id

const doctorLineData = [
  { time: '09:00', value: 72 },
  { time: '09:15', value: 78 },
  { time: '09:30', value: 81 },
  { time: '09:45', value: 92 },
  { time: '10:00', value: 84 },
  { time: '10:15', value: 77 },
]

const nurseTabs = ['Overview', 'Patients', 'Live Monitor', 'AI Correlation', 'Alerts', 'Analytics', 'Reports', 'Administration']
const doctorTabs = ['Dashboard', 'Patients', 'Live Monitor', 'Reports', 'Settings']

const liveStreamUrl = '/video-feed'

interface DashboardPageProps {
  role: 'nurse' | 'doctor' | 'admin'
}

export function DashboardPage({ role }: DashboardPageProps) {
  const [selectedPatient, setSelectedPatient] = useState(devikaDefaultPatientId)
  const [activeDoctorTab, setActiveDoctorTab] = useState('Live Monitor')
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [userEmail] = useState('doctor@example.com')
  const [audioEvent, setAudioEvent] = useState<AudioEvent>({
    patient: defaultAudioPatient.id,
    patient_name: defaultAudioPatient.name,
    doctor: defaultAudioPatient.doctor,
    doctor_notified: false,
    event: 'normal',
    severity: 'normal',
    confidence: 0,
    matched_phrase: null,
    transcript: null,
    time: '--',
  })
  const navigate = useNavigate()
  const patient = useMemo(
    () => patientList.find((item) => item.id === selectedPatient) ?? patientDetails,
    [selectedPatient],
  )
  const criticalPatients = useMemo(
    () => patientList.filter((item) => item.status === 'critical' || item.status === 'high-risk'),
    [],
  )

  const filteredPatientList = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) {
      return patientList
    }
    return patientList.filter((item) =>
      [item.name, item.condition, item.ward, item.bed].some((field) =>
        field.toLowerCase().includes(query),
      ),
    )
  }, [searchQuery])

  const userInitials = useMemo(() => {
    const prefix = userEmail.split('@')[0]
    const pieces = prefix.replace(/[^a-zA-Z0-9]+/g, ' ').trim().split(' ').filter(Boolean)
    if (pieces.length === 0) return 'DR'
    if (pieces.length === 1) return pieces[0].slice(0, 2).toUpperCase()
    return `${pieces[0][0]}${pieces[1][0]}`.toUpperCase()
  }, [userEmail])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const renderDoctorTabContent = () => {
    if (activeDoctorTab === 'Patients') {
      return (
        <section className="doctor-panel doctor-list-panel">
          <div className="panel-header doctor-panel-header">
            <div>
              <h2>Patient directory</h2>
              <p>Browse all patients assigned to the hospital.</p>
            </div>
          </div>
          <div className="critical-list">
            {filteredPatientList.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`critical-card ${selectedPatient === item.id ? 'active' : ''}`}
                onClick={() => setSelectedPatient(item.id)}
              >
                <div className="critical-card-top">
                  <div>
                    <p className="critical-name">{item.name}</p>
                    <p className="critical-meta">{item.bed} · {item.ward}</p>
                  </div>
                  <span className={`status-pill small ${item.status}`}>{item.status.replace('-', ' ')}</span>
                </div>
                <div className="critical-card-bottom">
                  <span>Risk {item.riskScore}%</span>
                  <span>{item.condition}</span>
                </div>
              </button>
            ))}
          </div>
        </section>
      )
    }

    if (activeDoctorTab === 'Live Monitor') {
      return (
        <section className="doctor-grid">
          <div className="doctor-left">
            <section className="doctor-panel doctor-monitor-panel">
              <div className="monitor-hero">
                <div className="monitor-badge">Live Monitor</div>
                <div className="monitor-meta">
                  <p className="monitor-name">{patient.name}</p>
                  <p>{patient.bed} · {patient.condition}</p>
                </div>
              </div>
              <div className="doctor-metrics">
                <FeatureCard title="Heart Rate" value={`${patient.latestHR ?? patient.vitals.heartRate} bpm`} detail="Current bedside reading" />
                <FeatureCard title="SpO₂" value={`${patient.latestSpO2 ?? patient.vitals.spo2}%`} detail="Oxygen saturation" />
                <FeatureCard title="Risk Score" value={`${patient.riskScore}%`} detail="Critical care" />
              </div>
              <div className="doctor-video-card">
                <div className="panel-header doctor-panel-header">
                  <div>
                    <h2>Live monitoring video</h2>
                    <p>Watch the selected patient's bedside feed.</p>
                  </div>
                  <span className="live-pill">Live</span>
                </div>
                {patient.videoUrl ? (
                  <video className="feed-video" src={patient.videoUrl} controls autoPlay muted playsInline />
                ) : (
                  <img className="feed-video" src={liveStreamUrl} alt="Live feed" />
                )}
              </div>
              <div className="chart-card">
                <p className="chart-title">Live Trend</p>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={doctorLineData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ef" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', color: '#0f172a' }} />
                    <Line type="monotone" dataKey="value" stroke="#0f4c81" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>

          <div className="doctor-right">
            <section className="doctor-panel doctor-summary-panel">
              <div className="panel-header doctor-panel-header">
                <div>
                  <h2>Patient overview</h2>
                  <p>Live vital stats and current condition for the selected patient.</p>
                </div>
              </div>
              <div className="doctor-notes-grid">
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Last update</span>
                  <strong>1 min ago</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Primary doctor</span>
                  <strong>{patient.doctor}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Nurse</span>
                  <strong>{patient.nurse}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Bed</span>
                  <strong>{patient.bed}</strong>
                </div>
              </div>
            </section>
          </div>
        </section>
      )
    }

    if (activeDoctorTab === 'Reports') {
      return (
        <section className="doctor-grid">
          <div className="doctor-left">
            <section className="doctor-panel doctor-summary-panel">
              <div className="panel-header doctor-panel-header">
                <div>
                  <h2>Clinical reports</h2>
                  <p>Summary of recent findings and performance indicators.</p>
                </div>
              </div>
              <div className="doctor-notes-grid">
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Risk assessment</span>
                  <strong>{patient.riskScore}%</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">ECG status</span>
                  <strong>{patient.status === 'critical' ? 'Review needed' : 'Stable'}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Oxygen trend</span>
                  <strong>{(patient.latestSpO2 ?? patient.vitals.spo2) < 94 ? 'Declining' : 'Stable'}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Respiratory rate</span>
                  <strong>{patient.respiratoryRate ?? '16 rpm'}</strong>
                </div>
              </div>
            </section>
          </div>

          <div className="doctor-right">
            <section className="doctor-panel doctor-monitor-panel">
              <div className="monitor-hero">
                <div className="monitor-badge">Report</div>
                <div className="monitor-meta">
                  <p className="monitor-name">Report overview</p>
                  <p>Data snapshot and trends</p>
                </div>
              </div>
              <div className="doctor-metrics">
                <FeatureCard title="Avg. SpO₂" value="97%" detail="Past 24 hours" />
                <FeatureCard title="Avg. HR" value="78 bpm" detail="Past 24 hours" />
                <FeatureCard title="Alerts" value="2" detail="Critical incidents" />
              </div>
              <div className="chart-card">
                <p className="chart-title">Recovery trend</p>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={doctorLineData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ef" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', color: '#0f172a' }} />
                    <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>
        </section>
      )
    }

    if (activeDoctorTab === 'Settings') {
      return (
        <section className="doctor-grid">
          <div className="doctor-left">
            <section className="doctor-panel doctor-summary-panel">
              <div className="panel-header doctor-panel-header">
                <div>
                  <h2>Workspace settings</h2>
                  <p>Configure your doctor console preferences.</p>
                </div>
              </div>
              <div className="doctor-settings-grid">
                <button type="button" className="doctor-settings-card">Notification preferences</button>
                <button type="button" className="doctor-settings-card">Display theme</button>
                <button type="button" className="doctor-settings-card">Search filters</button>
                <button type="button" className="doctor-settings-card">Patient grouping</button>
              </div>
            </section>
          </div>

          <div className="doctor-right">
            <section className="doctor-panel doctor-monitor-panel">
              <div className="monitor-hero">
                <div className="monitor-badge">Settings</div>
                <div className="monitor-meta">
                  <p className="monitor-name">Console preferences</p>
                  <p>Tune your dashboard controls.</p>
                </div>
              </div>
              <div className="doctor-metrics">
                <FeatureCard title="Auto-refresh" value="On" detail="Live patient data" />
                <FeatureCard title="Alerts" value="Enabled" detail="High-priority only" />
                <FeatureCard title="Dark mode" value="Off" detail="Switch theme" />
              </div>
              <div className="chart-card">
                <p className="chart-title">Recent activity</p>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={doctorLineData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ef" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', color: '#0f172a' }} />
                    <Line type="monotone" dataKey="value" stroke="#0f4c81" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>
        </section>
      )
    }

    return (
      <>
        <section className="doctor-hero">
          <div>
            <p className="doctor-breadcrumb">Doctor Console / Critical Review</p>
            <h1>High-acuity patient review</h1>
            <p className="doctor-subtitle">
              Review critical cases, follow live ECG trends, and act on the latest bedside alerts from one clear workspace.
            </p>
          </div>
          <div className="doctor-hero-actions">
            <button type="button" className="secondary-button small">Export Summary</button>
            <button type="button" className="primary-button admin-primary-action">
              <ArrowUpRight size={15} />
              Review Alerts
            </button>
          </div>
        </section>

        <section className="doctor-metrics-grid">
          <article className="doctor-metric-card">
            <span className="doctor-metric-label">Critical Cases</span>
            <strong>{criticalPatients.length}</strong>
            <p>Active patients requiring direct review.</p>
          </article>
          <article className="doctor-metric-card">
            <span className="doctor-metric-label">Selected Risk</span>
            <strong>{patient.riskScore}%</strong>
            <p>{patient.condition}</p>
          </article>
          <article className="doctor-metric-card">
            <span className="doctor-metric-label">SpO₂</span>
            <strong>{patient.latestSpO2 ?? patient.vitals.spo2}%</strong>
            <p>{(patient.latestSpO2 ?? patient.vitals.spo2) < 94 ? 'Needs attention' : 'Within range'}</p>
          </article>
          <article className="doctor-metric-card">
            <span className="doctor-metric-label">Heart Rate</span>
            <strong>{patient.latestHR ?? patient.vitals.heartRate} bpm</strong>
            <p>Latest recorded value</p>
          </article>
        </section>

        <section className="doctor-grid">
          <div className="doctor-left">
            <section className="doctor-panel doctor-list-panel">
              <div className="panel-header doctor-panel-header">
                <div>
                  <h2>Critical patient list</h2>
                  <p>Review only the active high-priority cases.</p>
                </div>
                <span className="panel-header-meta">{criticalPatients.length} cases</span>
              </div>
              <div className="critical-list">
                {criticalPatients.map((item) => (
                  <button key={item.id} type="button" className={`critical-card ${selectedPatient === item.id ? 'active' : ''}`} onClick={() => setSelectedPatient(item.id)}>
                    <div className="critical-card-top">
                      <div>
                        <p className="critical-name">{item.name}</p>
                        <p className="critical-meta">{item.bed} · {item.ward}</p>
                      </div>
                      <span className={`status-pill small ${item.status}`}>{item.status.replace('-', ' ')}</span>
                    </div>
                    <div className="critical-card-bottom">
                      <span>Risk {item.riskScore}%</span>
                      <span>{item.condition}</span>
                    </div>
                  </button>
                ))}
              </div>
            </section>

            <section className="doctor-panel doctor-summary-panel">
              <div className="panel-header doctor-panel-header">
                <div>
                  <h2>Medical summary</h2>
                  <p>Clinical context for the selected patient.</p>
                </div>
              </div>
              <p className="doctor-summary-text">
                {patient.name} is under close observation for {patient.condition.toLowerCase()}. SpO₂, ECG, and risk signals remain the priority for the current review cycle.
              </p>
              <div className="summary-tags doctor-summary-tags">
                <span>ECG Abnormal</span>
                <span>SpO₂ Low</span>
                <span>Risk {patient.riskScore}%</span>
              </div>
            </section>
          </div>

          <div className="doctor-right">
            <section className="doctor-panel doctor-monitor-panel">
              <div className="monitor-hero">
                <div className="monitor-badge">Review</div>
                <div className="monitor-meta">
                  <p className="monitor-name">{patient.name}</p>
                  <p>{patient.bed} · {patient.condition}</p>
                </div>
              </div>
              <div className="doctor-metrics">
                <FeatureCard title="Heart Rate" value={`${patient.latestHR ?? patient.vitals.heartRate} bpm`} detail="Current bedside reading" />
                <FeatureCard title="SpO₂" value={`${patient.latestSpO2 ?? patient.vitals.spo2}%`} detail="Oxygen saturation" />
                <FeatureCard title="Risk Score" value={`${patient.riskScore}%`} detail="Critical care" />
              </div>
              <div className="chart-card">
                <p className="chart-title">ECG Trend</p>
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={doctorLineData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ef" />
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', color: '#0f172a' }} />
                    <Line type="monotone" dataKey="value" stroke="#0f4c81" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="doctor-panel doctor-notes-panel">
              <div className="panel-header doctor-panel-header">
                <div>
                  <h2>Clinical notes</h2>
                  <p>Most recent findings and recommended attention areas.</p>
                </div>
              </div>
              <div className="doctor-notes-grid">
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Doctor</span>
                  <strong>{patient.doctor}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Nurse</span>
                  <strong>{patient.nurse}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Ward</span>
                  <strong>{patient.ward}</strong>
                </div>
                <div className="doctor-note-item">
                  <span className="doctor-note-label">Latest Alert</span>
                  <strong>{patient.currentAlert ?? 'No active alert'}</strong>
                </div>
              </div>
            </section>
          </div>
        </section>
      </>
    )
  }

  useEffect(() => {
    if (role !== 'nurse') {
      return
    }

    const socket = new WebSocket('ws://127.0.0.1:8000/audio/ws/audio-events')
    
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        setAudioEvent({
          patient: payload.patient ?? defaultAudioPatient.id,
          patient_name: payload.patient_name ?? defaultAudioPatient.name,
          doctor: payload.doctor ?? defaultAudioPatient.doctor,
          doctor_notified: Boolean(payload.doctor_notified),
          event: payload.event ?? 'normal',
          severity: payload.severity ?? (payload.event?.includes('distress') ? 'critical' : payload.event === 'loud_vocalization' ? 'warning' : 'normal'),
          confidence: payload.confidence ?? 0,
          matched_phrase: payload.matched_phrase ?? null,
          transcript: payload.transcript ?? null,
          time: payload.time ?? '--',
          error: payload.error,
        })
      } catch {
        setAudioEvent((previous) => ({
          ...previous,
          error: 'Invalid audio websocket message',
        }))
      }
    }

    socket.onerror = () => {
      setAudioEvent((previous) => ({
        ...previous,
        error: 'Audio websocket connection failed',
      }))
    }

    return () => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }
  }, [role])

  return (
    <div className={`dashboard-layout ${role !== 'nurse' ? 'dashboard-layout--wide' : ''}`}>
      {role === 'nurse' && <Sidebar patients={patientList} selected={selectedPatient} onSelect={setSelectedPatient} />}
      <main className={`dashboard-main ${role}`}>
        {role !== 'doctor' && (
          <DashboardHeader
            title={role === 'nurse' ? 'Nurse Console' : role === 'admin' ? 'Admin Command Center' : 'Doctor Console'}
            subtitle={
              role === 'nurse'
                ? 'Patient-focused ICU monitoring and rapid response'
                : role === 'admin'
                ? 'Hospital overview and bed occupancy dashboard'
                : 'Clinical review of high-risk patients'
            }
            darkMode={false}
            onToggleTheme={() => null}
          />
        )}
        {role === 'doctor' ? (
          <section className="doctor-shell">
            <header className="doctor-topnav">
              <div className="doctor-brand-block">
                <div className="doctor-brand-mark">
                  <ShieldCheck size={18} strokeWidth={2.5} />
                </div>
                <div>
                  <p className="doctor-brand-name">VitalGuard</p>
                  <p className="doctor-brand-sub">Doctor Console</p>
                </div>
              </div>
              <nav className="doctor-nav-tabs" aria-label="Doctor navigation">
                {doctorTabs.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    className={`doctor-nav-tab ${activeDoctorTab === tab ? 'active' : ''}`}
                    onClick={() => setActiveDoctorTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </nav>
              <div className="doctor-topnav-actions">
                {showSearch ? (
                  <div className="doctor-search-panel">
                    <div className="doctor-search-field">
                      <Search size={16} />
                      <input
                        type="search"
                        placeholder="Search patients, condition"
                        value={searchQuery}
                        onChange={(event) => setSearchQuery(event.target.value)}
                        autoFocus
                      />
                      <button type="button" className="doctor-search-clear" onClick={() => setSearchQuery('')}>
                        Clear
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="doctor-search-button"
                    onClick={() => {
                      setShowSearch(true)
                      setShowProfileMenu(false)
                    }}
                    aria-label="Open search"
                  >
                    <Search size={18} />
                  </button>
                )}
                <button
                  type="button"
                  className="doctor-profile-summary"
                  onClick={() => {
                    setShowProfileMenu((prev) => !prev)
                    setShowSearch(false)
                  }}
                  aria-label="Open profile menu"
                >
                  <div>
                    <p className="doctor-profile-name">Hanna Kenter</p>
                    <p className="doctor-profile-location">Kansas</p>
                  </div>
                  <span className="doctor-profile-avatar">{userInitials}</span>
                </button>
                {showProfileMenu && (
                  <div className="doctor-profile-menu">
                    <button type="button" className="doctor-profile-menu-item">Profile</button>
                    <button type="button" className="doctor-profile-menu-item" onClick={handleLogout}>
                      Logout
                    </button>
                  </div>
                )}
              </div>
            </header>

            {renderDoctorTabContent()}
          </section>
        ) : role === 'admin' ? (
          <section className="admin-overview">
            <div className="admin-dashboard-grid">
              <div className="admin-overview-cards">
                {adminOverviewCards.map((card) => (
                  <StatusCard key={card.label} label={card.label} value={String(card.value)} accent={card.accent} />
                ))}
              </div>
              <div className="admin-main-grid">
                <section className="admin-top-panel">
                  <div className="panel-header top-panel-header">
                    <div>
                      <h2>Dashboard Overview</h2>
                      <p>High-level status across wards, patient alerts, and AI insights.</p>
                    </div>
                    <div className="dashboard-meta">
                      <span>May 21, 2025</span>
                      <span>Morning Shift 07:00 - 15:00</span>
                    </div>
                  </div>
                  <div className="overview-panels">
                    <div className="ward-status-card">
                      <div className="panel-header">
                        <h2>Live Ward Status</h2>
                        <p>Occupancy and current alerts by ward.</p>
                      </div>
                      <div className="ward-table">
                        {wardStatus.map((ward) => (
                          <div key={ward.ward} className="ward-row">
                            <div>
                              <p className="ward-name">{ward.ward}</p>
                              <p className="ward-detail">{ward.patients} patients</p>
                            </div>
                            <div className="ward-progress-bar">
                              <div className="ward-progress" style={{ width: ward.occupancy }} />
                            </div>
                            <span className={`ward-alerts ${ward.trend}`}>{ward.alerts} alerts</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="alerts-card">
                      <div className="panel-header">
                        <h2>Recent Critical Alerts</h2>
                        <p>Quick access to the most urgent patient issues.</p>
                      </div>
                      <div className="alert-list-card">
                        {adminCriticalAlerts.map((item) => (
                          <div key={item.patient} className="alert-row">
                            <div>
                              <p className="alert-patient">Patient {item.patient}</p>
                              <p className="alert-message">{item.message}</p>
                            </div>
                            <div className="alert-meta">
                              <span className={`status-pill small ${item.severity === 'High' ? 'critical' : item.severity === 'Medium' ? 'warning' : 'normal'}`}>{item.severity}</span>
                              <p>{item.time}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="correlation-card">
                      <div className="panel-header">
                        <h2>AI Correlation Engine</h2>
                        <p>Alerts derived from speech, vitals, and patient behavior.</p>
                      </div>
                      <div className="correlation-list">
                        {adminCorrelationItems.map((item) => (
                          <div key={item.label} className="correlation-row">
                            <div>
                              <p className="correlation-label">{item.label}</p>
                              <p className="correlation-value">{item.value}</p>
                            </div>
                            <span className={`status-pill small ${item.status === 'High' ? 'critical' : item.status === 'Medium' ? 'warning' : 'normal'}`}>{item.status}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </section>
                <section className="admin-actions-grid">
                  <div className="quick-actions-card">
                    <div className="panel-header">
                      <h2>Quick Actions</h2>
                    </div>
                    <div className="quick-actions-list">
                      {adminQuickActions.map((item) => (
                        <button key={item.label} className="action-pill">{item.label}</button>
                      ))}
                    </div>
                  </div>
                  <section className="admin-table-card admin-table-card-wide">
                    <div className="panel-header">
                      <h2>Patient Monitoring Table</h2>
                      <p>Track bed status, assigned staff, and risk levels.</p>
                    </div>
                    <div className="data-table">
                      <div className="table-row header-row">
                        <span>Patient</span>
                        <span>Bed</span>
                        <span>Ward</span>
                        <span>Doctor</span>
                        <span>Nurse</span>
                        <span>Status</span>
                        <span>Risk</span>
                        <span>Updated</span>
                      </div>
                      {patientList.map((row) => (
                        <div key={row.id} className="table-row body-row">
                          <span>{row.name}</span>
                          <span>{row.bed}</span>
                          <span>{row.ward}</span>
                          <span>{row.doctor}</span>
                          <span>{row.nurse}</span>
                          <span className={`status-pill small ${row.status}`}>{row.status.replace('-', ' ')}</span>
                          <span>{row.riskScore}%</span>
                          <span>2m ago</span>
                        </div>
                      ))}
                    </div>
                  </section>
                </section>
              </div>
            </div>
          </section>
        ) : (
          <section className="nurse-dashboard">
            <div className="nurse-header-row">
              <div className="nurse-tabs">
                {nurseTabs.map((tab) => (
                  <button key={tab} className={`tab-pill ${tab === 'Live Monitor' ? 'active' : ''}`}>
                    {tab}
                  </button>
                ))}
              </div>
              <button onClick={() => navigate('/login')} className="secondary-button small">Switch Account</button>
            </div>
            <div className="nurse-grid">
              <aside className="nurse-sidebar">
                <div className="panel-header">
                  <h2>Select Patient</h2>
                  <p>Choose a monitored room to review live vitals.</p>
                </div>
                <div className="patient-search">
                  <input type="search" placeholder="Search patient, bed, staff..." />
                </div>
                <div className="patient-list-card">
                  {patientList.map((item) => (
                    <button
                      key={item.id}
                      className={`patient-list-item ${selectedPatient === item.id ? 'active' : ''}`}
                      onClick={() => setSelectedPatient(item.id)}
                    >
                      <div>
                        <p className="patient-name">{item.name}</p>
                        <p className="patient-meta">{item.icuId ?? item.id} · {item.bed}</p>
                      </div>
                      <span className={`status-pill small ${item.status}`}>{item.status === 'high-risk' ? 'High Risk' : item.status.replace('-', ' ')}</span>
                    </button>
                  ))}
                </div>
                <button className="view-all-button">View all patients</button>
              </aside>

              <main className="nurse-main">
                <div className="live-summary-card">
                  <div className="live-summary-meta">
                    <div>
                      <p className="eyebrow">Live Monitor</p>
                      <h2>{patient.name}</h2>
                      <p className="patient-detail-text">{patient.icuId ?? patient.id} · {patient.bed} · {patient.condition}</p>
                    </div>
                    <span className={`status-pill ${patient.status}`}>{patient.status.replace('-', ' ')}</span>
                  </div>
                  <div className="live-vitals-row">
                    <div className="vitals-stat">
                      <p>HR</p>
                      <strong>{patient.vitals.heartRate} bpm</strong>
                    </div>
                    <div className="vitals-stat">
                      <p>SpO₂</p>
                      <strong>{patient.vitals.spo2}%</strong>
                    </div>
                    <div className="vitals-stat">
                      <p>BP</p>
                      <strong>{patient.bp ?? 'N/A'}</strong>
                    </div>
                    <div className="vitals-stat">
                      <p>Temp</p>
                      <strong>{patient.temperature ?? 'N/A'}</strong>
                    </div>
                  </div>
                </div>

                <div className="live-ecg-card">
                  <div className="panel-header">
                    <h2>Live ECG</h2>
                    <div className="ecg-header-right">
                      <span>130 bpm</span>
                    </div>
                  </div>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={doctorLineData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30415622" />
                      <XAxis dataKey="time" tick={{ fill: '#a8b4cf', fontSize: 12 }} />
                      <YAxis tick={{ fill: '#a8b4cf', fontSize: 12 }} />
                      <Tooltip contentStyle={{ background: '#0f172a', border: 'none', color: '#fff' }} />
                      <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={3} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="nurse-feed-grid">
                  <div className="feed-card">
                    <div className="panel-header">
                      <h2>Camera Feed</h2>
                      <span className="live-pill">Live</span>
                    </div>
                    {patient.videoUrl ? (
                      <video className="feed-video" src={patient.videoUrl} controls autoPlay muted playsInline />
                    ) : (
                      <img className="feed-video" src={liveStreamUrl} alt="Live feed" />
                    )}
                  </div>
                  <div className="feed-card audio-feed-card">
                    <div className="panel-header">
                      <h2>Audio Feed</h2>
                      <span className="live-pill">Live</span>
                    </div>
                    <div className="audio-waveform">
                      <div />
                      <div />
                      <div />
                      <div />
                      <div />
                      <div />
                    </div>
                  </div>
                </div>
              </main>

              <aside className="nurse-sidepanel">
                <div className="vitals-card">
                  <div className="panel-header">
                    <h2>Live Vitals</h2>
                  </div>
                  <div className="vitals-panel">
                    <div className="vitals-row">
                      <div>
                        <p>Heart Rate</p>
                        <strong>{patient.vitals.heartRate} bpm</strong>
                      </div>
                      <div>
                        <p>SpO₂</p>
                        <strong>{patient.vitals.spo2}%</strong>
                      </div>
                    </div>
                    <div className="vitals-row">
                      <div>
                        <p>Blood Pressure</p>
                        <strong>{patient.bp ?? 'N/A'}</strong>
                      </div>
                      <div>
                        <p>Respiratory Rate</p>
                        <strong>{patient.respiratoryRate ?? 'N/A'} /min</strong>
                      </div>
                    </div>
                    <div className="vitals-row">
                      <div>
                        <p>Temperature</p>
                        <strong>{patient.temperature ?? 'N/A'}</strong>
                      </div>
                    </div>
                  </div>
                </div>
                <div className={`audio-status-card ${audioEvent.severity === 'critical' ? 'audio-status-card--critical' : ''}`}>
                  <div className="panel-header">
                    <h2>Audio Status</h2>
                  </div>
                  <div className="audio-status-body">
                    <div className="audio-status-hero">
                      <div>
                        <span className={`status-pill ${audioEvent.severity}`}>
                          {audioEvent.severity.toUpperCase()}
                        </span>
                        <p className="audio-status-target">Critical patient focus</p>
                        <h3>{audioEvent.patient_name ?? defaultAudioPatient.name}</h3>
                        <p className="audio-status-id">{audioEvent.patient} · doctor {audioEvent.doctor ?? defaultAudioPatient.doctor}</p>
                      </div>
                      <div className="audio-status-score">
                        <span>Confidence</span>
                        <strong>{(audioEvent.confidence * 100).toFixed(0)}%</strong>
                      </div>
                    </div>
                    <div className="audio-status-transcript">
                      <span className="audio-status-label">Speech to text</span>
                      <p>{audioEvent.transcript ?? 'Waiting for live speech input...'}</p>
                    </div>
                    <div className="audio-status-meta">
                      <p><strong>Assigned audio patient:</strong> {audioEvent.patient_name ?? 'Unknown'} ({audioEvent.patient})</p>
                      <p><strong>Notified doctor:</strong> {audioEvent.doctor ?? 'Unknown'} {audioEvent.doctor_notified ? '(sent)' : '(pending)'}</p>
                      <p><strong>Detected phrase:</strong> {audioEvent.matched_phrase ?? 'None'}</p>
                      <p><strong>Last update:</strong> {audioEvent.time}</p>
                    </div>
                    {audioEvent.error ? <p className="error-text">{audioEvent.error}</p> : null}
                  </div>
                </div>
                <div className="alert-panel">
                  <div className="panel-header">
                    <h2>Current Alert</h2>
                  </div>
                  <div className="alert-status-card">
                    <p>{patient.currentAlert ?? 'No active alert'}</p>
                    <span className="status-pill critical">High</span>
                    <p className="alert-timestamp">10:20 AM</p>
                  </div>
                  <button className="primary-button full-width">Acknowledge Alert</button>
                </div>
              </aside>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
