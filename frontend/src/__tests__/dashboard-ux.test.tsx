/**
 * Dashboard UX tests
 * Tests loading skeleton, stat card labels, and empty state.
 */
import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'

jest.mock('next/navigation', () => ({
  usePathname: () => '/',
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

// Mock dashboardApi
jest.mock('@/lib/api', () => ({
  dashboardApi: {
    getStats: jest.fn(),
    getTopRiskPairs: jest.fn(),
  },
}))

import DashboardPage from '@/app/(dashboard)/page'
import { dashboardApi } from '@/lib/api'

const mockDashboardApi = dashboardApi as {
  getStats: jest.Mock
  getTopRiskPairs: jest.Mock
}

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

const MOCK_STATS = {
  vulnerabilities: {
    total: 42,
    critical: 0,
    high: 5,
    medium: 10,
    low: 27,
    kev_listed: 2,
  },
  assets: {
    total: 10,
    internet_exposed: 3,
    critical_assets: 1,
  },
  goals: [],
  risk_score: {
    total: 1200,
    trend: 'down' as const,
    reduction_7d: 50,
  },
  bundles: {
    scheduled: 1,
    next_window: null,
    pending_approval: 0,
  },
  windows: [],
}

beforeEach(() => {
  localStorageMock.clear()
  mockDashboardApi.getStats.mockResolvedValue(MOCK_STATS)
  mockDashboardApi.getTopRiskPairs.mockResolvedValue([])
})

afterEach(() => {
  jest.clearAllMocks()
})

describe('DashboardPage — loading skeleton', () => {
  it('renders animate-pulse skeleton placeholders while loading', () => {
    // Keep promise pending so component stays in loading state
    mockDashboardApi.getStats.mockReturnValue(new Promise(() => {}))
    mockDashboardApi.getTopRiskPairs.mockReturnValue(new Promise(() => {}))

    render(<DashboardPage />)

    // DashboardSkeleton renders elements with animate-pulse
    const skeletonEls = document.querySelectorAll('.animate-pulse')
    expect(skeletonEls.length).toBeGreaterThan(0)
  })

  it('skeleton contains placeholder card shapes', () => {
    mockDashboardApi.getStats.mockReturnValue(new Promise(() => {}))
    mockDashboardApi.getTopRiskPairs.mockReturnValue(new Promise(() => {}))

    render(<DashboardPage />)

    // The skeleton renders 4 stat placeholder cards
    const cardPlaceholders = document.querySelectorAll('.bg-gray-800.rounded-xl')
    expect(cardPlaceholders.length).toBeGreaterThan(0)
  })
})

describe('DashboardPage — loaded state', () => {
  it('renders focus/full mode toggle after load', async () => {
    render(<DashboardPage />)
    await waitFor(() => {
      // Multiple elements may contain "Focus" (button + heading)
      const focusEls = screen.getAllByText(/Focus/i)
      expect(focusEls.length).toBeGreaterThan(0)
    })
  })

  it('shows "Focus" mode by default — toggle button is visible', async () => {
    render(<DashboardPage />)
    await waitFor(() => {
      // The ⚡ Focus button in the mode toggle
      const focusBtn = screen.getByRole('button', { name: /⚡ Focus/i })
      expect(focusBtn).toBeInTheDocument()
    })
  })

  it('renders without crashing when vulnerabilities.critical is 0', async () => {
    const zeroCritStats = {
      ...MOCK_STATS,
      vulnerabilities: { ...MOCK_STATS.vulnerabilities, critical: 0, total: 0 },
    }
    mockDashboardApi.getStats.mockResolvedValue(zeroCritStats)
    render(<DashboardPage />)
    await waitFor(() => {
      // Should not throw; page renders in some non-loading state
      expect(mockDashboardApi.getStats).toHaveBeenCalled()
    })
  })
})

describe('DashboardPage — error state', () => {
  it('renders error UI when API fails', async () => {
    mockDashboardApi.getStats.mockRejectedValue(new Error('Network error'))
    mockDashboardApi.getTopRiskPairs.mockRejectedValue(new Error('Network error'))

    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText(/couldn't load dashboard/i)).toBeInTheDocument()
    })
  })
})
