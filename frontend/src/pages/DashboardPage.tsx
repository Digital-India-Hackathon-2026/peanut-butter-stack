import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
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

const doctorLineData = [
  { time: '09:00', value: 72 },
  { time: '09:15', value: 78 },
  { time: '09:30', value: 81 },
  { time: '09:45', value: 92 },
  { time: '10:00', value: 84 },
  { time: '10:15', value: 77 },
]

const nurseTabs = ['Overview', 'Patients', 'Live Monitor', 'AI Correlation', 'Alerts', 'Analytics', 'Reports', 'Administration']

const liveStreamUrl = '/video-feed'

interface DashboardPageProps {
  role: 'nurse' | 'doctor' | 'admin'
}

export function DashboardPage({ role }: DashboardPageProps) {
  const [selectedPatient, setSelectedPatient] = useState(patientList[0].id)
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
    <div className="dashboard-layout">
      {role !== 'admin' && <Sidebar patients={patientList} selected={selectedPatient} onSelect={setSelectedPatient} />}
      <main className={`dashboard-main ${role}`}>
        <DashboardHeader
          title={role === 'nurse' ? 'Nurse Console' : role === 'doctor' ? 'Doctor Console' : 'Admin Command Center'}
          subtitle={
            role === 'nurse'
              ? 'Patient-focused ICU monitoring and rapid response'
              : role === 'doctor'
              ? 'Clinical review of high-risk patients'
              : 'Hospital overview and bed occupancy dashboard'
          }
          darkMode={false}
          onToggleTheme={() => null}
        />

        {role === 'admin' ? (
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
        ) : role === 'doctor' ? (
          <section className="doctor-grid">
            <div className="doctor-left">
              <div className="panel-header">
                <h2>Critical Patient List</h2>
                <p>Review only the active high-priority cases.</p>
              </div>
              <div className="critical-list">
                {criticalPatients.map((item) => (
                  <div key={item.id} className="critical-card" onClick={() => setSelectedPatient(item.id)}>
                    <p className="critical-name">{item.name}</p>
                    <p>{item.bed}</p>
                    <span className={`status-pill small ${item.status}`}>{item.status.replace('-', ' ')}</span>
                    <p>Risk {item.riskScore}%</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="doctor-right">
              <div className="monitor-card detail-card">
                <div className="monitor-hero">
                  <div className="monitor-badge">Review</div>
                  <div className="monitor-meta">
                    <p className="monitor-name">{patient.name}</p>
                    <p>{patient.bed} · {patient.condition}</p>
                  </div>
                </div>
                <div className="doctor-metrics">
                  <FeatureCard title="Heart Rate" value="88 bpm" detail="Moderate elevation" />
                  <FeatureCard title="SpO₂" value="92%" detail="Low oxygen saturation" />
                  <FeatureCard title="Risk Score" value={`${patient.riskScore}%`} detail="Critical care" />
                </div>
                <div className="chart-card">
                  <p className="chart-title">ECG Trend</p>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={doctorLineData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30415622" />
                      <XAxis dataKey="time" tick={{ fill: '#a8b4cf', fontSize: 12 }} />
                      <YAxis tick={{ fill: '#a8b4cf', fontSize: 12 }} />
                      <Tooltip contentStyle={{ background: '#0f172a', border: 'none', color: '#fff' }} />
                      <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={3} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="patient-summary-card">
                <div className="panel-header">
                  <h2>Medical Summary</h2>
                </div>
                <p>Patient experienced a fall and has an abnormal ECG signature. SpO₂ decreased under 94% and requires immediate medical assessment.</p>
                <div className="summary-tags">
                  <span>ECG Abnormal</span>
                  <span>SpO₂ Low</span>
                  <span>Fall Detected</span>
                </div>
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
