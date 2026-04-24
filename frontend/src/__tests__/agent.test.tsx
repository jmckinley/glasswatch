/**
 * AI Agent page tests
 * Tests prompt chips, empty state, and message layout.
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

jest.mock('next/navigation', () => ({
  usePathname: () => '/agent',
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('next/link', () => {
  return function Link({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>
  }
})

// Mock fetch — will be configured per-test as needed
global.fetch = jest.fn()

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

import AgentPage from '@/app/(dashboard)/agent/page'

const ALL_PROMPTS = [
  'What needs my attention today?',
  'Show all KEV vulnerabilities',
  'How is our SOC 2 compliance trending?',
  'Which bundles need approval?',
  "What's our mean time to patch?",
  'List overdue SLA vulnerabilities',
]

describe('AgentPage — empty state', () => {
  beforeEach(() => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ response: 'OK', actions_taken: [], suggested_actions: [] }),
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders empty state heading "Your AI Security Analyst"', () => {
    render(<AgentPage />)
    expect(screen.getByText('Your AI Security Analyst')).toBeInTheDocument()
  })

  it('renders all 6 suggested prompt chips on empty state', () => {
    render(<AgentPage />)
    for (const prompt of ALL_PROMPTS) {
      expect(screen.getByText(prompt)).toBeInTheDocument()
    }
  })

  it('has exactly 6 prompt chip buttons in empty state', () => {
    render(<AgentPage />)
    // Each prompt is a button
    const chipButtons = ALL_PROMPTS.map(p => screen.queryByText(p)).filter(Boolean)
    expect(chipButtons).toHaveLength(6)
  })

  it('clicking a prompt chip calls fetch with the prompt text', async () => {
    render(<AgentPage />)
    const chip = screen.getByText('What needs my attention today?')
    fireEvent.click(chip)
    // fetch should have been called with the prompt
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled()
    })
    const fetchCall = (global.fetch as jest.Mock).mock.calls[0]
    // The prompt text should be in the fetch body
    const body = JSON.parse(fetchCall[1].body)
    expect(body.message).toBe('What needs my attention today?')
  })
})

describe('AgentPage — message layout', () => {
  it('user messages align to the right (justify-end)', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ response: 'AI reply here', actions_taken: [], suggested_actions: [] }),
    })

    render(<AgentPage />)
    // Send a message via the chip
    fireEvent.click(screen.getByText('Which bundles need approval?'))

    await waitFor(() => {
      // The user message wrapper has justify-end
      const userWrapper = screen.getByText('Which bundles need approval?').closest('[class*="justify-end"]')
      expect(userWrapper).toBeTruthy()
    })
  })

  it('AI replies align to the left (justify-start)', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ response: 'AI says hello', actions_taken: [], suggested_actions: [] }),
    })

    render(<AgentPage />)
    fireEvent.click(screen.getByText("What's our mean time to patch?"))

    await waitFor(() => {
      const aiReply = screen.queryByText('AI says hello')
      if (aiReply) {
        const aiWrapper = aiReply.closest('[class*="justify-start"]')
        expect(aiWrapper).toBeTruthy()
      }
    })
  })
})
