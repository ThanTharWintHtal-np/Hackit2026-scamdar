import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from './App.jsx'

const demoResult = {
  score: 92,
  level: 'High',
  category: 'delivery',
  signals: [
    { code: 'urgency', label: 'Urgency or threat language', points: 12, detail: 'It pressures the reader to act quickly.' },
    { code: 'payment', label: 'Payment or financial request', points: 22, detail: 'The message asks for money.' },
  ],
  recommended_action: 'High scam likelihood. Do not send money or disclose credentials until independently verified.',
  disclaimer: 'This is a warning aid.',
  similar_reports: [],
}

function jsonResponse(body, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: async () => body })
}

describe('ScamDar main flows', () => {
  afterEach(() => { cleanup(); window.history.replaceState({}, '', '/') })
  beforeEach(() => {
    localStorage.clear()
    global.fetch = vi.fn((input, options = {}) => {
      const url = String(input)
      if (url.endsWith('/api/health')) return jsonResponse({ status: 'ok' })
      if (url.includes('/api/reports?')) return jsonResponse({ items: [] })
      if (url.endsWith('/api/trends')) return jsonResponse({ reports_today: 4, reports_this_week: 15, active_campaigns: 6, by_category: { delivery: 5 }, by_region: { Central: 3 }, top_brands: { SingPost: 4 }, activity: {}, note: 'Synthetic data.' })
      if (url.endsWith('/api/analyze') && options.method === 'POST') return jsonResponse(demoResult)
      if (url.endsWith('/api/auth/login')) return jsonResponse({ token: 'demo-token', user: { id: 1, email: 'member@example.com', display_name: 'Demo Member', role: 'user' } })
      return jsonResponse({ items: [] })
    })
  })

  it('checks the demo message and renders score explanations', async () => {
    render(<App />)
    const checkButton = await screen.findByRole('button', { name: /check for scam/i })
    await waitFor(() => expect(checkButton).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: /try the demo message/i }))
    fireEvent.click(checkButton)
    expect(await screen.findByText(/here’s what scamdar noticed/i)).toBeInTheDocument()
    expect(screen.getByText('92')).toBeInTheDocument()
    expect(screen.getByText(/urgency or threat language/i)).toBeInTheDocument()
    expect(screen.getByText(/payment or financial request/i)).toBeInTheDocument()
  })

  it('opens the account form and signs a member in', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'member@example.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'a-secure-password' } })
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /sign in/i }))
    expect(await screen.findByText('Demo Member')).toBeInTheDocument()
    expect(localStorage.getItem('scamdar_token')).toBe('demo-token')
  })

  it('switches to the trends dashboard', async () => {
    render(<App />)
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('button', { name: 'Trends' }))
    expect(await screen.findByRole('heading', { name: /see the patterns, not just one message/i })).toBeInTheDocument()
    expect(await screen.findByText('Reports today')).toBeInTheDocument()
  })

  it('lets a trusted contact send a response from a private link', async () => {
    window.history.replaceState({}, '', '/?trusted=private-demo-token')
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: /do not proceed/i }))
    expect(await screen.findByText(/your response “do not proceed” was shared/i)).toBeInTheDocument()
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/trusted-contacts/private-demo-token/respond'), expect.any(Object))
  })
})
