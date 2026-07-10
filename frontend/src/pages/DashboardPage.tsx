import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { patientList, alerts, summaryCards } from '../lib/mockData'
import { Sidebar } from '../components/Sidebar'
import { DashboardHeader } from '../components/DashboardHeader'
import { StatusCard } from '../components/StatusCard'
import { AlertCard } from '../components/AlertCard'
import { FeatureCard } from '../components/FeatureCard'

interface AudioEvent {
  patient: string
  event: string
  confidence: number
  matched_phrase: string | null
  time: string
  error?: string
}

const patientDetails = patientList[0]

const doctorLineData = [
  { time: '09:00', value: 72 },
  { time: '09:15', value: 78 },
  { time: '09:30', value: 81 },
  { time: '09:45', value: 92 },
  { time: '10:00', value: 84 },
  { time: '10:15', value: 77 },
]

const liveStreamUrl = 'http://127.0.0.1:8000/video-feed'

interface DashboardPageProps {
  role: 'nurse' | 'doctor' | 'admin'
}

export function DashboardPage({ role }: DashboardPageProps) {
  const [selectedPatient, setSelectedPatient] = useState(patientList[0].id)
  const [audioEvent, setAudioEvent] = useState<AudioEvent>({
    patient: 'ICU-12',
    event: 'normal',
    confidence: 0,
    matched_phrase: null,
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
          patient: payload.patient ?? 'ICU-12',
          event: payload.event ?? 'normal',
          confidence: payload.confidence ?? 0,
          matched_phrase: payload.matched_phrase ?? null,
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
            <div className="dashboard-summary admin-summary">
              {summaryCards.map((card) => (
                <StatusCard key={card.label} label={card.label} value={String(card.value)} accent={card.accent} />
              ))}
            </div>
            <div className="admin-body">
              <section className="admin-table-card">
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
              <section className="admin-statistics">
                <div className="panel-header">
                  <h2>Hospital Statistics</h2>
                  <p>Operational metrics in real time.</p>
                </div>
                <div className="stats-grid">
                  <FeatureCard title="Critical Cases" value="5" detail="Urgent attention required" />
                  <FeatureCard title="Falls Detected" value="12" detail="Since morning shift" />
                  <FeatureCard title="Avg. Response Time" value="4m 12s" detail="From alert to action" />
                  <FeatureCard title="Bed Occupancy" value="90%" detail="Occupied vs available" />
                </div>
              </section>
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
          <section className="nurse-grid">
            <div className="monitor-panel">
              <div className="monitor-top">
                <div className="monitor-status-panel">
                  <h2>Dynamic Monitoring</h2>
                  <p>Active patient alerts and live observation.</p>
                </div>
                <div className="monitor-actions">
                  <button onClick={() => navigate('/login')} className="secondary-button">Switch Account</button>
                </div>
              </div>
              <div className="monitor-card live-card">
                <div className="monitor-hero">
                  <div className="monitor-badge">Live</div>
                  <div className="monitor-meta">
                    <p className="monitor-name">{patient.name}</p>
                    <p>{patient.bed} · {patient.condition}</p>
                  </div>
                </div>
                {patient.videoUrl ? (
                  <video
                    className="monitor-stream"
                    src={patient.videoUrl}
                    controls
                    autoPlay
                    muted
                    playsInline
                    poster="https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&w=900&q=80"
                  />
                ) : (
                  <img
                    className="monitor-stream"
                    src={liveStreamUrl}
                    alt="Live camera stream"
                  />
                )}
              </div>
              <div className="vitals-summary">
                <FeatureCard title="Heart Rate" value={`${patient.vitals.heartRate} bpm`} detail="Current pulse" />
                <FeatureCard title="SpO₂" value={`${patient.vitals.spo2}%`} detail="Oxygen saturation" />
                <FeatureCard title="ECG Severity" value={patient.vitals.severity.toUpperCase()} detail="Cardiac alert level" />
              </div>
              <div className="audio-status-card">
                <div className="panel-header">
                  <h2>Audio Distress Status</h2>
                  <p>Live microphone detection for the connected room.</p>
                </div>
                <div className="audio-status-body">
                  <span className={`status-pill ${audioEvent.event === 'normal' ? 'normal' : audioEvent.event === 'distress_phrase' || audioEvent.event === 'repeated_distress' ? 'critical' : 'warning'}`}>
                    {audioEvent.event.replace(/_/g, ' ')}
                  </span>
                  <p><strong>Patient:</strong> {audioEvent.patient}</p>
                  <p><strong>Phrase:</strong> {audioEvent.matched_phrase ?? 'None detected'}</p>
                  <p><strong>Confidence:</strong> {(audioEvent.confidence * 100).toFixed(0)}%</p>
                  <p><strong>Updated:</strong> {audioEvent.time}</p>
                  {audioEvent.error ? <p className="error-text">{audioEvent.error}</p> : null}
                </div>
              </div>
            </div>
            <aside className="alerts-panel">
              <div className="panel-header">
                <h2>Current Alerts</h2>
                <p>Respond to critical events and review alert history.</p>
              </div>
              {alerts.map((alert) => (
                <AlertCard
                  key={alert.patientId}
                  patientName={alert.patientName}
                  bed={alert.bed}
                  priority={alert.priority}
                  riskScore={alert.riskScore}
                  reasons={alert.reasons}
                  onView={() => setSelectedPatient(alert.patientId)}
                />
              ))}
            </aside>
            <section className="patient-details-panel">
              <div className="panel-header">
                <h2>Patient Details</h2>
                <p>Comprehensive profile and event timeline.</p>
              </div>
              <div className="patient-details-grid">
                <div className="profile-card">
                  <p className="profile-title">{patient.name}</p>
                  <p>{patient.age} years · {patient.gender}</p>
                  <p>{patient.ward} · Assigned Doctor: {patient.doctor}</p>
                  <p>{patient.condition}</p>
                </div>
                <div className="profile-card">
                  <p className="profile-title">Medications</p>
                  <ul>
                    {patient.medications.map((med) => <li key={med}>{med}</li>)}
                  </ul>
                </div>
                <div className="profile-card">
                  <p className="profile-title">Allergies</p>
                  <p>{patient.allergies.join(', ')}</p>
                </div>
                <div className="profile-card">
                  <p className="profile-title">Emergency Contact</p>
                  <p>{patient.emergencyContact}</p>
                </div>
              </div>
              <div className="timeline-card">
                <p className="profile-title">Recent Events</p>
                <div className="timeline-list">
                  {patient.events.map((event) => (
                    <div key={event.time} className="timeline-item">
                      <span>{event.time}</span>
                      <div>
                        <p>{event.label}</p>
                        <p>{event.details}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </section>
        )}
      </main>
    </div>
  )
}
