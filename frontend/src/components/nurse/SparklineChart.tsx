interface SparklineProps {
  data: number[]
  status: 'stable' | 'warning' | 'high-risk' | 'critical'
  width?: number
  height?: number
}

const statusColors: Record<string, string> = {
  stable: '#22c55e',
  warning: '#f59e0b',
  'high-risk': '#f97316',
  critical: '#ef4444',
}

export function SparklineChart({ data, status, width = 80, height = 28 }: SparklineProps) {
  if (!data || data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((val - min) / range) * (height - 4) - 2
    return `${x},${y}`
  })

  const color = statusColors[status] ?? '#94a3b8'

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block', overflow: 'visible' }}>
      <defs>
        <linearGradient id={`spark-grad-${status}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default SparklineChart
