import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Lock, ShieldCheck, CheckCircle2, ArrowRight } from 'lucide-react'
import { setToken, setUser, signin } from '../lib/auth'
import type { Role } from '../types'

const roleOptions: Array<{ value: Role; label: string }> = [
  { value: 'nurse', label: 'Nurse' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'admin', label: 'Admin' },
]

export function LoginPage() {
  const [role, setRole] = useState<Role>('nurse')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await signin(email, role)
      setToken(response.access_token)
      setUser(response.email, response.role)
      navigate(`/${response.role}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const title = 'Sign in to VitalGuard'
  const submitLabel = 'Sign in'

  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="auth-brand auth-brand--hero">
          <div className="auth-logo">VG</div>
          <div>
            <p className="auth-title">VitalGuard</p>
            <p className="auth-subtitle">Clinical command workspace</p>
          </div>
        </div>
        <div className="auth-kicker">ENTERPRISE ICU MONITORING</div>
        <h1 className="auth-headline">A calm, precise workspace for critical care teams.</h1>
        <p className="auth-welcome">
          Monitor live vitals, review speech-to-text alerts, detect falls, and coordinate emergency response from one trusted interface.
        </p>
        <div className="auth-feature-list">
          <div className="auth-feature-item">
            <CheckCircle2 size={18} />
            <span>Live vital monitoring</span>
          </div>
          <div className="auth-feature-item">
            <CheckCircle2 size={18} />
            <span>AI Fall Detection</span>
          </div>
          <div className="auth-feature-item">
            <CheckCircle2 size={18} />
            <span>Voice distress alerts</span>
          </div>
          <div className="auth-feature-item">
            <CheckCircle2 size={18} />
            <span>Role-based dashboards</span>
          </div>
        </div>
        <div className="auth-metrics auth-metrics--wide">
          <div className="auth-metric">
            <div className="metric-icon">24/7</div>
            <div>
              <strong>Monitoring</strong>
            </div>
          </div>
          <div className="auth-metric">
            <div className="metric-icon">Secure</div>
            <div>
              <strong>Role access</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-card">
        <div className="auth-card-inner">
          <div className="auth-brand auth-brand--card">
            <div className="auth-logo">VG</div>
            <div>
              <p className="auth-title">{title}</p>
              <p className="auth-subtitle">Hospital Operations Dashboard</p>
            </div>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label>
              Email
              <div className="input-group input-group--large">
                <User size={18} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="hospital@vitalguard.com"
                  required
                />
              </div>
            </label>
            <label>
              Password
              <div className="input-group input-group--large">
                <Lock size={18} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  minLength={6}
                  required
                />
              </div>
            </label>
            <label>
              Role
              <div className="select-group select-group--large">
                <ShieldCheck size={18} />
                <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                  {roleOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
            </label>

            {error && <p className="auth-error">{error}</p>}

            <button type="submit" className="primary-button" disabled={loading}>
              <span>{loading ? 'Please wait...' : submitLabel}</span>
              <ArrowRight size={18} />
            </button>
          </form>

          <div className="auth-divider">Protected Access</div>
          <p className="auth-footer-text">Use your hospital credentials to securely access your dashboard.</p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
