const API = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export function getToken() { return localStorage.getItem('scamdar_token') || '' }
export function setSession(token, user) {
  localStorage.setItem('scamdar_token', token)
  localStorage.setItem('scamdar_user', JSON.stringify(user))
}
export function clearSession() {
  localStorage.removeItem('scamdar_token')
  localStorage.removeItem('scamdar_user')
}
export function getUser() {
  try { return JSON.parse(localStorage.getItem('scamdar_user') || 'null') } catch { return null }
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (getToken()) headers.set('Authorization', `Bearer ${getToken()}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API}${path}`, { ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.detail || data.message || `Request failed (${response.status})`)
    error.status = response.status
    error.data = data
    throw error
  }
  return data
}
