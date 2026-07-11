interface FeatureCardProps {
  title: string
  value: string
  detail: string
}

export function FeatureCard({ title, value, detail }: FeatureCardProps) {
  return (
    <div className="feature-card">
      <p className="feature-card-label">{title}</p>
      <p className="feature-card-value">{value}</p>
      <p className="feature-card-detail">{detail}</p>
    </div>
  )
}
