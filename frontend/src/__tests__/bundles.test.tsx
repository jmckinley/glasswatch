/**
 * Bundles page UX tests
 * Tests explainer banner, dismissal, status badges, empty state, skeleton, and new bundle button.
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

jest.mock('next/navigation', () => ({
  usePathname: () => '/bundles',
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('next/link', () => {
  return function Link({ children, href, className }: {
    children: React.ReactNode
    href: string
    className?: string
  }) {
    return <a href={href} className={className}>{children}</a>
  }
})

// Mock the bundlesApi module
jest.mock('@/lib/api', () => ({
  bundlesApi: {
    list: jest.fn(),
  },
}))

import BundlesPage from '@/app/(dashboard)/bundles/page'
import { bundlesApi } from '@/lib/api'

const mockBundlesApi = bundlesApi as { list: jest.Mock }

// localStorage mock
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

beforeEach(() => {
  localStorageMock.clear()
  // Return empty bundles by default
  mockBundlesApi.list.mockResolvedValue({ items: [], total: 0 })
})

afterEach(() => {
  jest.clearAllMocks()
})

describe('BundlesPage — explainer banner', () => {
  it('renders the explainer banner when not dismissed', async () => {
    // Ensure banner not dismissed
    render(<BundlesPage />)
    await waitFor(() => {
      expect(screen.getByText(/patch bundle groups related vulnerabilities/i)).toBeInTheDocument()
    })
  })

  it('banner contains the workflow steps text', async () => {
    render(<BundlesPage />)
    await waitFor(() => {
      expect(screen.getByText(/Draft.*Pending Approval.*Approved.*In Progress.*Completed/i)).toBeInTheDocument()
    })
  })

  it('banner is dismissible — clicking ✕ hides it', async () => {
    render(<BundlesPage />)
    await waitFor(() => {
      expect(screen.getByText(/patch bundle groups related vulnerabilities/i)).toBeInTheDocument()
    })
    const dismissBtn = screen.getByRole('button', { name: /dismiss/i })
    fireEvent.click(dismissBtn)
    await waitFor(() => {
      expect(screen.queryByText(/patch bundle groups related vulnerabilities/i)).not.toBeInTheDocument()
    })
  })

  it('banner stays dismissed after clicking ✕ (localStorage set)', async () => {
    render(<BundlesPage />)
    await waitFor(() => screen.getByRole('button', { name: /dismiss/i }))
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(localStorageMock.getItem('glasswatch_bundles_banner_dismissed')).toBe('1')
  })

  it('banner does not render when already dismissed in localStorage', async () => {
    localStorageMock.setItem('glasswatch_bundles_banner_dismissed', '1')
    render(<BundlesPage />)
    await waitFor(() => {
      expect(screen.queryByText(/patch bundle groups related vulnerabilities/i)).not.toBeInTheDocument()
    })
  })
})

describe('BundlesPage — empty state', () => {
  it('renders "No patch bundles yet" when bundles array is empty', async () => {
    mockBundlesApi.list.mockResolvedValue({ items: [], total: 0 })
    render(<BundlesPage />)
    await waitFor(() => {
      // The h3 heading has exact text "No patch bundles yet"
      const headings = screen.getAllByText(/no patch bundles yet/i)
      expect(headings.length).toBeGreaterThan(0)
      expect(headings[0]).toBeInTheDocument()
    })
  })
})

describe('BundlesPage — skeleton', () => {
  it('renders skeleton rows while loading', () => {
    // Keep the promise pending so loading stays true
    mockBundlesApi.list.mockReturnValue(new Promise(() => {}))
    render(<BundlesPage />)
    // Skeleton rows have animate-pulse cells
    const pulseCells = document.querySelectorAll('.animate-pulse')
    expect(pulseCells.length).toBeGreaterThan(0)
  })
})

describe('BundlesPage — New Bundle button', () => {
  it('renders a "New Bundle" link/button with indigo styling', async () => {
    render(<BundlesPage />)
    const newBundleLink = screen.getByText(/\+ new bundle/i)
    expect(newBundleLink).toBeInTheDocument()
    // It should link somewhere (goals page creates bundles)
    expect(newBundleLink.closest('a')).toHaveAttribute('href')
    // Should have indigo styling
    const el = newBundleLink.closest('[class*="indigo"]') || newBundleLink
    expect(el.className || '').toMatch(/indigo/)
  })
})

describe('BundlesPage — status badge colors', () => {
  const makeBundles = (status: string) => ({
    items: [{
      id: '1',
      name: 'Test Bundle',
      status,
      risk_level: 'HIGH',
      vulnerability_count: 3,
      scheduled_for: null,
      goal_name: null,
      goal_id: null,
    }],
    total: 1,
  })

  const STATUS_CLASS_MAP: Record<string, string> = {
    approved:    'emerald',
    in_progress: 'indigo',
    completed:   'gray',
    cancelled:   'red',
    draft:       'gray',
  }

  for (const [status, colorKeyword] of Object.entries(STATUS_CLASS_MAP)) {
    it(`status "${status}" badge has "${colorKeyword}" color class`, async () => {
      mockBundlesApi.list.mockResolvedValue(makeBundles(status))
      const { unmount } = render(<BundlesPage />)
      await waitFor(() => {
        // The status badge text (capitalized/formatted)
        const badge = document.querySelector(`[class*="${colorKeyword}"]`)
        expect(badge).toBeTruthy()
      })
      unmount()
    })
  }
})
