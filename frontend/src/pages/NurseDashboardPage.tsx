import '../nurse-dashboard.css'
import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { allPatients, criticalPatients, alertCards } from '../lib/nurseMockData'
import { NurseTopNav } from '../components/nurse/NurseTopNav'
import { PatientListSidebar } from '../components/nurse/PatientListSidebar'
import { CenterMonitorPanel } from '../components/nurse/CenterMonitorPanel'
import { AlertsSidebar } from '../components/nurse/AlertsSidebar'
import { logout } from '../lib/auth'

export function NurseDashboardPage() {
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = useState<string>(allPatients[0].patient_id)
  const [darkMode, setDarkMode] = useState(false)

  // Auto-select first critical patient on load
  useEffect(() => {
    const critical = criticalPatients[0]
    if (critical) setSelectedId(critical.patient_id)
  }, [])

  const selectedPatient = useMemo(
    () => allPatients.find((p) => p.patient_id === selectedId) ?? allPatients[0],
    [selectedId],
  )

  const firstCritical = useMemo(() => criticalPatients[0] ?? null, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="nd-layout">
      <NurseTopNav
        criticalPatient={firstCritical}
        onViewAlert={() => firstCritical && setSelectedId(firstCritical.patient_id)}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode((d) => !d)}
        onLogout={handleLogout}
        alertCount={alertCards.length}
      />
      <div className="nd-body">
        <PatientListSidebar
          patients={allPatients}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <CenterMonitorPanel patient={selectedPatient} />
        <AlertsSidebar
          alerts={alertCards}
          onViewCamera={(id) => {
            const p = allPatients.find((x) => x.patient_id === id)
            if (p) setSelectedId(p.patient_id)
          }}
          onViewDetails={(id) => {
            const p = allPatients.find((x) => x.patient_id === id)
            if (p) setSelectedId(p.patient_id)
          }}
        />
      </div>
    </div>
  )
}

export default NurseDashboardPage
