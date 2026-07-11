import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { NurseDashboardPage } from './pages/NurseDashboardPage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'
import { getCurrentUser, getToken, getUserRole, isAuthenticated, logout } from './lib/auth'
import type { Role } from './types'
import './App.css'

function AuthGuard({
  children,
  allowedRole,
}: {
  children: React.ReactNode
  allowedRole?: Role
}) {
  const [verified, setVerified] = useState(false)
  const [userRole, setUserRole] = useState<Role | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setVerified(false)
      return
    }

    getCurrentUser()
      .then((user) => {
        if (user) {
          setUserRole(user.role)
          setVerified(true)
        } else {
          logout()
          setVerified(false)
        }
      })
      .catch(() => {
        logout()
        setVerified(false)
      })
  }, [])

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }

  if (!verified && !userRole) {
    return null
  }

  const effectiveRole = userRole ?? getUserRole()

  if (allowedRole && effectiveRole !== allowedRole) {
    const target = effectiveRole ? `/${effectiveRole}` : '/login'
    return <Navigate to={target} replace />
  }

  return <>{children}</>
}

function App() {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    // Trigger a quick auth check so the first render is informed about the token state
    getCurrentUser().finally(() => setReady(true))
  }, [])

  if (!ready) {
    return null
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/nurse"
          element={
            <AuthGuard allowedRole="nurse">
              <NurseDashboardPage />
            </AuthGuard>
          }
        />
        <Route
          path="/doctor"
          element={
            <AuthGuard allowedRole="doctor">
              <DashboardPage role="doctor" />
            </AuthGuard>
          }
        />
        <Route
          path="/admin"
          element={
            <AuthGuard allowedRole="admin">
              <AdminDashboardPage />
            </AuthGuard>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
