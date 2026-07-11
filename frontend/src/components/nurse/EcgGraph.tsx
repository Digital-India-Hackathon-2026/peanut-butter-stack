import { useEffect, useRef } from 'react'

interface EcgGraphProps {
  heartRate?: number
  isAbnormal?: boolean
}

export function EcgGraph({ heartRate = 72, isAbnormal = false }: EcgGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const offsetRef = useRef(0)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Build one full ECG cycle template
    function buildCycle(bpm: number): number[] {
      // Samples per beat at 60fps approximation
      const samplesPerBeat = Math.round(3600 / bpm)
      const cycle: number[] = new Array(samplesPerBeat).fill(0)
      const baseline = 0

      // P wave (small bump at ~10% of cycle)
      const pStart = Math.floor(samplesPerBeat * 0.05)
      const pLen = Math.floor(samplesPerBeat * 0.08)
      for (let i = 0; i < pLen; i++) {
        cycle[pStart + i] = baseline + 0.12 * Math.sin((i / pLen) * Math.PI)
      }

      // Q dip
      const qStart = Math.floor(samplesPerBeat * 0.2)
      cycle[qStart] = baseline - 0.08
      cycle[qStart + 1] = baseline - 0.1

      // R spike (sharp)
      const rStart = Math.floor(samplesPerBeat * 0.23)
      const rLen = isAbnormal ? 5 : 4
      cycle[rStart] = baseline + (isAbnormal ? 0.95 : 1.0)
      cycle[rStart + 1] = baseline + (isAbnormal ? 0.7 : 0.5)
      cycle[rStart + 2] = baseline - 0.2
      for (let i = 3; i < rLen; i++) cycle[rStart + i] = baseline - 0.15

      // S wave recovery
      const sEnd = Math.floor(samplesPerBeat * 0.35)
      for (let i = rStart + rLen; i < sEnd; i++) {
        const t = (i - (rStart + rLen)) / (sEnd - (rStart + rLen))
        cycle[i] = baseline - 0.15 * (1 - t)
      }

      // T wave
      const tStart = Math.floor(samplesPerBeat * 0.42)
      const tLen = Math.floor(samplesPerBeat * 0.14)
      for (let i = 0; i < tLen; i++) {
        cycle[tStart + i] = baseline + (isAbnormal ? 0.28 : 0.18) * Math.sin((i / tLen) * Math.PI)
      }

      return cycle
    }

    let cycle = buildCycle(heartRate)
    let noisePhase = 0

    function draw() {
      const w = canvas!.width
      const h = canvas!.height
      ctx!.clearRect(0, 0, w, h)

      // Background
      ctx!.fillStyle = '#0d1220'
      ctx!.fillRect(0, 0, w, h)

      // Subtle grid lines
      ctx!.strokeStyle = 'rgba(34,197,94,0.06)'
      ctx!.lineWidth = 1
      const gridCols = 20
      const gridRows = 6
      for (let c = 0; c <= gridCols; c++) {
        ctx!.beginPath()
        ctx!.moveTo((c / gridCols) * w, 0)
        ctx!.lineTo((c / gridCols) * w, h)
        ctx!.stroke()
      }
      for (let r = 0; r <= gridRows; r++) {
        ctx!.beginPath()
        ctx!.moveTo(0, (r / gridRows) * h)
        ctx!.lineTo(w, (r / gridRows) * h)
        ctx!.stroke()
      }

      // Baseline center
      const cy = h / 2
      const amplitude = h * 0.38

      // Draw ECG line
      ctx!.beginPath()
      ctx!.strokeStyle = isAbnormal ? '#ef4444' : '#22c55e'
      ctx!.lineWidth = 2
      ctx!.shadowColor = isAbnormal ? '#ef4444' : '#22c55e'
      ctx!.shadowBlur = 6

      const offset = offsetRef.current
      for (let x = 0; x < w; x++) {
        const sampleIdx = Math.floor((x + offset) % cycle.length)
        const noise = Math.sin(noisePhase + x * 0.3) * 0.008
        const y = cy - (cycle[sampleIdx] + noise) * amplitude
        if (x === 0) ctx!.moveTo(x, y)
        else ctx!.lineTo(x, y)
      }
      ctx!.stroke()
      ctx!.shadowBlur = 0

      // Leading sweep dot
      const frontSample = Math.floor((w - 1 + offset) % cycle.length)
      const dotNoise = Math.sin(noisePhase + (w - 1) * 0.3) * 0.008
      const dotY = cy - (cycle[frontSample] + dotNoise) * amplitude
      ctx!.beginPath()
      ctx!.arc(w - 1, dotY, 3, 0, Math.PI * 2)
      ctx!.fillStyle = isAbnormal ? '#ef4444' : '#4ade80'
      ctx!.shadowColor = isAbnormal ? '#ef4444' : '#4ade80'
      ctx!.shadowBlur = 10
      ctx!.fill()
      ctx!.shadowBlur = 0

      offsetRef.current = (offsetRef.current + 2.2) % cycle.length
      noisePhase += 0.04

      rafRef.current = requestAnimationFrame(draw)
    }

    // Resize canvas to match DOM size
    const resize = () => {
      if (!canvas) return
      canvas!.width = canvas!.offsetWidth * window.devicePixelRatio
      canvas!.height = canvas!.offsetHeight * window.devicePixelRatio
      ctx!.scale(window.devicePixelRatio, window.devicePixelRatio)
      cycle = buildCycle(heartRate)
    }

    resize()
    rafRef.current = requestAnimationFrame(draw)

    const observer = new ResizeObserver(resize)
    observer.observe(canvas)

    return () => {
      cancelAnimationFrame(rafRef.current)
      observer.disconnect()
    }
  }, [heartRate, isAbnormal])

  return (
    <div className="ecg-wrapper">
      <div className="ecg-header-bar">
        <span className="ecg-title">LIVE ECG</span>
        <div className="ecg-meta-right">
          <span className="ecg-lead">Lead II</span>
          <span className="ecg-scale">10 mm/mV</span>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        className="ecg-canvas"
        style={{ width: '100%', height: '96px', display: 'block' }}
      />
    </div>
  )
}

export default EcgGraph
