interface StatusCardProps {
  label: string
  value: string
  accent: string
}

export function StatusCard({ label, value, accent }: StatusCardProps) {
  return (
    <div className={`status-card status-${accent}`}>
      <p className="status-card-label">{label}</p>
      <p className="status-card-value">{value}</p>
    </div>
  )
}
