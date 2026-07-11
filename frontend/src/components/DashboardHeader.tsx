import { Bell, Moon, SunMedium } from 'lucide-react'

interface DashboardHeaderProps {
  title: string
  subtitle: string
  onToggleTheme: () => void
  darkMode: boolean
}

export function DashboardHeader({ title, subtitle, onToggleTheme, darkMode }: DashboardHeaderProps) {
  return (
    <header className="dashboard-header">
      <div>
        <p className="dashboard-label">ICU Monitoring</p>
        <h1>{title}</h1>
        <p className="dashboard-subtitle">{subtitle}</p>
      </div>
      <div className="header-actions">
        <button type="button" className="icon-btn" onClick={onToggleTheme} aria-label="Toggle theme">
          {darkMode ? <SunMedium size={18} /> : <Moon size={18} />}
        </button>
        <button type="button" className="icon-btn" aria-label="Notifications">
          <Bell size={18} />
        </button>
      </div>
    </header>
  )
}
