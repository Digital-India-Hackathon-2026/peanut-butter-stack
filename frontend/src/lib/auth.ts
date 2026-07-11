import type { Role } from '../types'

const TOKEN_KEY = 'vg_access_token'
const USER_ROLE_KEY = 'vg_user_role'
const USER_EMAIL_KEY = 'vg_user_email'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_ROLE_KEY)
  localStorage.removeItem(USER_EMAIL_KEY)
}

export function setUser(email: string, role: Role): void {
  localStorage.setItem(USER_EMAIL_KEY, email)
  localStorage.setItem(USER_ROLE_KEY, role)
}

export function getUserRole(): Role | null {
  const role = localStorage.getItem(USER_ROLE_KEY)
  if (role === 'nurse' || role === 'doctor' || role === 'admin') {
    return role
  }
  return null
}

export function getUserEmail(): string | null {
  return localStorage.getItem(USER_EMAIL_KEY)
}

export interface AuthResponse {
  access_token: string
  token_type: string
  email: string
  role: Role
}

function createDemoToken(email: string, role: Role): string {
  return btoa(`${email}:${role}:${Date.now()}`)
}

export async function signin(email: string, role: Role): Promise<AuthResponse> {
  const token = createDemoToken(email, role)
  setToken(token)
  setUser(email, role)
  return {
    access_token: token,
    token_type: 'bearer',
    email,
    role,
  }
}

export async function getCurrentUser(): Promise<{ email: string; role: Role } | null> {
  const token = getToken()
  const role = getUserRole()
  const email = getUserEmail()

  if (!token || !role || !email) {
    return null
  }

  return { email, role }
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export function logout(): void {
  clearToken()
}
