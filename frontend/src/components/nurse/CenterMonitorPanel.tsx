import { useEffect, useRef, useState } from 'react'
import {
  Heart, Droplets, Activity, AlertTriangle, Shield, Camera,
} from 'lucide-react'
import type { VGPatient } from '../../lib/nurseMockData'
import { VitalStatCard } from './VitalStatCard'
import { EcgGraph } from './EcgGraph'

interface CenterMonitorPanelProps {
  patient: VGPatient | null
}

const VITALS_API = 'http://localhost:8001'

function NoCriticalPlaceholder() {
  return (
    <div className="cm-placeholder">
      <div className="cm-placeholder-icon">
        <svg viewBox="0 0 120 120" width="110" height="110" fill="none">
          <circle cx="60" cy="60" r="56" stroke="rgba(37,99,235,0.15)" strokeWidth="2" />
          <circle cx="60" cy="60" r="44" stroke="rgba(37,99,235,0.1)" strokeWidth="1.5" />
          <rect x="25" y="30" width="70" height="48" rx="5" stroke="#2563eb" strokeWidth="1.5"
            fill="rgba(37,99,235,0.05)" />
          <path d="M33 54 L43 54 L46 44 L50 64 L54 40 L58 68 L62 54 L68 54 L71 48 L74 60 L77 54 L87 54"
            stroke="#16a34a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          <rect x="54" y="78" width="12" height="8" rx="2" fill="rgba(37,99,235,0.15)" />
          <rect x="44" y="86" width="32" height="4" rx="2" fill="rgba(37,99,235,0.1)" />
          <circle cx="88" cy="32" r="12" fill="rgba(22,163,74,0.12)" stroke="#16a34a" strokeWidth="1.5" />
          <path d="M83 32 L87 36 L93 28" stroke="#16a34a" strokeWidth="2" strokeLinecap="round"
            strokeLinejoin="round" />
        </svg>
      </div>
      <h3 className="cm-placeholder-title">No Critical Patients</h3>
      <p className="cm-placeholder-sub">
        All assigned patients are currently stable.<br />
        Live monitoring appears automatically when a critical event is detected.
      </p>
      <div className="cm-placeholder-stats">
        <div className="cm-placeholder-stat">
          <span className="cm-stat-dot cm-stat-dot--green" />
          <span>All vitals normal</span>
        </div>
        <div className="cm-placeholder-stat">
          <span className="cm-stat-dot cm-stat-dot--blue" />
          <span>AI monitoring active</span>
        </div>
        <div className="cm-placeholder-stat">
          <span className="cm-stat-dot cm-stat-dot--cyan" />
          <span>Camera feeds online</span>
        </div>
      </div>
    </div>
  )
}

function tlDotClass(type: string) {
  if (type === 'critical') return 'cm-tl-dot--critical'
  if (type === 'warning') return 'cm-tl-dot--warning'
  if (type === 'normal') return 'cm-tl-dot--normal'
  return 'cm-tl-dot--info'
}

function tlTextClass(type: string) {
  if (type === 'critical') return 'tl-text--critical'
  if (type === 'warning') return 'tl-text--warning'
  if (type === 'normal') return 'tl-text--normal'
  return 'tl-text--info'
}

export function CenterMonitorPanel({ patient }: CenterMonitorPanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [webcamActive, setWebcamActive] = useState(false)
  const [webcamError, setWebcamError] = useState<string | null>(null)
  const [videoMode, setVideoMode] = useState<'none' | 'demo' | 'live'>('none')
  const [sendingAlert, setSendingAlert] = useState(false)
  const [alertStatus, setAlertStatus] = useState<string | null>(null)

  if (!patient) {
    return (
      <section className="cm-panel">
        <NoCriticalPlaceholder />
      </section>
    )
  }

  const isSamplePatient = patient.name === 'Devika Nair'
  const isCritical = patient.status === 'critical'
  const isWarning = patient.status === 'warning'
  const showMonitor = isCritical || isWarning

  useEffect(() => {
    setVideoMode('none')
    setWebcamActive(false)
    setWebcamError(null)
  }, [patient.patient_id])

  useEffect(() => {
    if (!webcamActive || videoMode !== 'live') return

    const videoEl = videoRef.current
    if (!videoEl) return

    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      .then((stream) => {
        videoEl.srcObject = stream
        videoEl.play().catch(() => {
          setWebcamError('Unable to play webcam stream.')
        })
      })
      .catch((err) => {
        console.error('Webcam error:', err)
        setWebcamError('Unable to access webcam. Please enable camera permissions.')
      })

    return () => {
      if (videoEl?.srcObject instanceof MediaStream) {
        videoEl.srcObject.getTracks().forEach((track) => track.stop())
        videoEl.srcObject = null
      }
    }
  }, [webcamActive, videoMode])

  if (!showMonitor) {
    return (
      <section className="cm-panel">
        <NoCriticalPlaceholder />
      </section>
    )
  }

  const statusLabel = isCritical ? 'CRITICAL' : 'WARNING'
  const statusCls = isCritical ? 'cm-status--critical' : 'cm-status--warning'
  const ecgAbnormal = patient.latestEcg !== 'normal'

  const handleSendAlert = async () => {
    if (!patient) return
    setSendingAlert(true)
    setAlertStatus(null)

    try {
      const response = await fetch(`${VITALS_API}/alerts/doctor-sms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bed_id: patient.bed,
          severity: 'critical',
          reset_cooldown: true,
          doctor_number: '9346156382',
        }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        setAlertStatus(`Alert failed: ${data?.error ?? response.statusText}`)
      } else {
        setAlertStatus('Alert sent successfully. Check your phone.')
      }
    } catch (error) {
      setAlertStatus(`Unable to send alert: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setSendingAlert(false)
    }
  }

  // Severity label
  const severityStr = isCritical ? 'CRITICAL' : patient.severity === 'high-risk' ? 'HIGH' : 'MODERATE'
  const severityVariant = isCritical ? 'critical' : 'warning'

  return (
    <section className="cm-panel">
      {/* Monitor Header */}
      <div className="cm-monitor-header">
        <div className="cm-monitor-title-group">
          <span className="cm-monitor-label">
            LIVE MONITORING — {patient.room} / {patient.bed}
          </span>
          <span className={`cm-status-badge ${statusCls}`}>{statusLabel}</span>
        </div>
      </div>

      {/* Video Feed */}
      <div className="cm-video-wrap">
        {patient.hasFall && (
          <div className="cm-overlay-fall">
            <AlertTriangle size={14} />
            <div>
              <span className="cm-fall-label">FALL DETECTED</span>
              <span className="cm-fall-time">09:42:15 AM</span>
            </div>
          </div>
        )}
        <div className="cm-overlay-live">
          <span className="cm-live-dot" />
          <span>{videoMode === 'demo' ? 'SAMPLE' : 'LIVE'}</span>
        </div>
        {isCritical && (
          <div className="cm-overlay-ai">
            <div className="cm-ai-status">
              <span className="cm-ai-label-text">AI Status</span>
              <span className={`cm-ai-value ${isCritical ? 'cm-ai-value--critical' : ''}`}>
                {patient.hasFall ? 'Fall Detected' : 'Acute Distress'}
              </span>
            </div>
            <div className="cm-ai-confidence">
              <span className="cm-ai-label-text">Confidence</span>
              <span className="cm-ai-conf-val">91.{patient.risk_score % 10}%</span>
            </div>
          </div>
        )}

        {videoMode === 'demo' ? (
          <video
            className="cm-video"
            src="/fall.mp4"
            autoPlay
            loop
            muted
            playsInline
          />
        ) : (
          <video
            ref={videoRef}
            className="cm-video"
            autoPlay
            playsInline
            muted
            controls={false}
          />
        )}
        {videoMode === 'none' && (
          <div className="cm-video-fallback" style={{ display: 'flex' }}>
            <Camera size={40} opacity={0.25} />
            <span>{isSamplePatient ? 'Click to view Devika Nair sample video.' : 'Click to start the live webcam.'}</span>
            <button
              className="cm-video-action-btn"
              type="button"
              onClick={() => {
                setWebcamError(null)
                if (isSamplePatient) {
                  setVideoMode('demo')
                } else {
                  setVideoMode('live')
                  setWebcamActive(true)
                }
              }}
            >
              View Video
            </button>
          </div>
        )}
        {videoMode === 'live' && !webcamActive && (
          <div className="cm-video-fallback" style={{ display: 'flex' }}>
            <Camera size={40} opacity={0.25} />
            <span>Starting webcam…</span>
          </div>
        )}
        {videoMode === 'live' && webcamActive && webcamError && (
          <div className="cm-video-fallback" style={{ display: 'flex' }}>
            <Camera size={40} opacity={0.25} />
            <span>{webcamError}</span>
          </div>
        )}
      </div>

      {/* Vital Stat Cards */}
      <div className="cm-vitals-row">
        <VitalStatCard
          icon={<Heart size={15} />}
          label="Heart Rate"
          value={String(Math.round(patient.latestHR))}
          unit="BPM"
          subLabel={patient.latestHR > 100 ? 'High' : patient.latestHR < 60 ? 'Low' : 'Normal'}
          trend={patient.latestHR > 100 ? 'up' : 'stable'}
          variant={patient.latestHR > 120 ? 'critical' : patient.latestHR > 100 ? 'warning' : 'normal'}
        />
        <VitalStatCard
          icon={<Droplets size={15} />}
          label="SpO₂"
          value={String(Math.round(patient.latestSpO2))}
          unit="%"
          subLabel={patient.latestSpO2 < 90 ? 'Low' : patient.latestSpO2 < 94 ? 'Borderline' : 'Normal'}
          trend={patient.latestSpO2 < 94 ? 'down' : 'stable'}
          variant={patient.latestSpO2 < 90 ? 'critical' : patient.latestSpO2 < 94 ? 'warning' : 'normal'}
        />
        <VitalStatCard
          icon={<Activity size={15} />}
          label="ECG Status"
          value={ecgAbnormal ? 'Abnormal' : 'Normal'}
          subLabel={ecgAbnormal ? 'Irregular Rhythm' : 'Sinus Rhythm'}
          variant={ecgAbnormal ? (isCritical ? 'critical' : 'warning') : 'normal'}
        />
        <VitalStatCard
          icon={<AlertTriangle size={15} />}
          label="Severity"
          value={severityStr}
          subLabel={`Risk ${patient.risk_score}%`}
          variant={severityVariant}
        />
        <VitalStatCard
          icon={<Shield size={15} />}
          label="Risk Score"
          value={String(patient.risk_score)}
          unit="%"
          variant={patient.risk_score >= 75 ? 'critical' : patient.risk_score >= 50 ? 'warning' : 'normal'}
        >
          <div className="cm-risk-gauge-wrap">
            <svg viewBox="0 0 44 44" width="44" height="44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="#e2e8f0" strokeWidth="4" />
              <circle
                cx="22" cy="22" r="18" fill="none"
                stroke={patient.risk_score >= 75 ? '#dc2626' : patient.risk_score >= 50 ? '#ea580c' : '#16a34a'}
                strokeWidth="4"
                strokeDasharray={`${(patient.risk_score / 100) * 113} 113`}
                strokeLinecap="round"
                transform="rotate(-90 22 22)"
              />
            </svg>
          </div>
        </VitalStatCard>
      </div>

      {/* ECG Graph */}
      <EcgGraph heartRate={Math.round(patient.latestHR)} isAbnormal={ecgAbnormal} />

      {/* Patient Details + Timeline */}
      <div className="cm-bottom-row">
        <div className="cm-details-card">
          <span className="cm-section-label">PATIENT DETAILS</span>
          <div className="cm-details-grid">
            {[
              ['Patient Name', patient.name],
              ['Medical Condition', patient.diagnosis],
              ['Age / Gender', `${patient.age} Y / ${patient.gender}`],
              ['Diagnosis', patient.diagnosis],
              ['Room / Bed', `${patient.room} / ${patient.bed}`],
              ['Admission', patient.admission_date],
              ['Assigned Doctor', patient.assigned_doctor],
              ['Resp. Rate', `${Math.round(patient.latestRR)} /min`],
              ['Assigned Nurse', patient.assigned_nurse],
              ['Temperature', `${patient.latestTemp.toFixed(1)}°F`],
            ].map(([key, val]) => (
              <div key={key} className="cm-detail-row">
                <span className="cm-detail-key">{key}</span>
                <span className="cm-detail-val">{val}</span>
              </div>
            ))}
          </div>
          {isCritical && (
            <div className="cm-send-alert-row">
              <button
                className="cm-send-alert-btn"
                type="button"
                disabled={sendingAlert}
                onClick={handleSendAlert}
              >
                {sendingAlert ? 'Sending alert…' : 'Send Alert to Doctor'}
              </button>
              {alertStatus && <span className="cm-send-alert-note">{alertStatus}</span>}
            </div>
          )}
        </div>

        <div className="cm-timeline-card">
          <span className="cm-section-label">RECENT EVENTS TIMELINE</span>
          <div className="cm-timeline">
            {patient.events.map((ev, idx) => (
              <div key={idx} className="cm-tl-row">
                <div className="cm-tl-time">{ev.time}</div>
                <div className="cm-tl-line-col">
                  <span className={`cm-tl-dot ${tlDotClass(ev.type)}`} />
                  {idx < patient.events.length - 1 && <span className="cm-tl-line" />}
                </div>
                <div className={`cm-tl-label ${tlTextClass(ev.type)}`}>{ev.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default CenterMonitorPanel
