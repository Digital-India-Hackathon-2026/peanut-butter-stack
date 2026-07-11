interface AlertCardProps {
  patientName: string
  bed: string
  priority: 'critical' | 'warning' | 'normal'
  riskScore: number
  reasons: string[]
  onView?: () => void
}

const priorityLabel = {
  normal: 'Normal',
  warning: 'Warning',
  critical: 'Critical',
}

export function AlertCard({ patientName, bed, priority, riskScore, reasons, onView }: AlertCardProps) {
  return (
    <article className={`alert-card alert-${priority}`}>
      <div className="alert-card-head">
        <div>
          <p className="alert-card-title">{patientName}</p>
          <p className="alert-card-meta">Bed {bed}</p>
        </div>
        <span className="alert-priority">{priorityLabel[priority]}</span>
      </div>
      <div className="alert-card-body">
        <p className="alert-risk">Risk Score {riskScore}%</p>
        <ul className="alert-reasons">
          {reasons.map((reason) => (
            <li key={reason}>✓ {reason}</li>
          ))}
        </ul>
      </div>
      <button type="button" className="alert-view-btn" onClick={onView}>
        View Live Camera
      </button>
    </article>
  )
}
