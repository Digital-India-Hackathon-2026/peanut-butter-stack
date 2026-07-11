import React from 'react'

interface VitalStatCardProps {
  icon: React.ReactNode
  label: string
  value: string
  unit?: string
  subLabel?: string
  trend?: 'up' | 'down' | 'stable'
  variant?: 'default' | 'warning' | 'critical' | 'normal'
  children?: React.ReactNode
}

export function VitalStatCard({
  icon,
  label,
  value,
  unit,
  subLabel,
  trend,
  variant = 'default',
  children,
}: VitalStatCardProps) {
  const trendIcon = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'
  const trendClass = trend === 'up' ? 'vsc-trend-up' : trend === 'down' ? 'vsc-trend-down' : ''

  return (
    <div className={`vsc-card vsc-card--${variant}`}>
      <div className="vsc-header">
        <span className="vsc-icon">{icon}</span>
        <span className="vsc-label">{label}</span>
      </div>
      <div className="vsc-value-row">
        <span className="vsc-value">{value}</span>
        {unit && <span className="vsc-unit">{unit}</span>}
      </div>
      {subLabel && (
        <div className="vsc-sub">
          {trend && <span className={`vsc-trend ${trendClass}`}>{trendIcon}</span>}
          <span className="vsc-sub-label">{subLabel}</span>
        </div>
      )}
      {children}
    </div>
  )
}

export default VitalStatCard
