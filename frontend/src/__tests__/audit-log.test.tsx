/**
 * Audit Log page tests
 *
 * Covers:
 * - Page renders with heading "Audit Log"
 * - Export CSV button is present
 * - Filter selects and apply button are present
 * - Table renders when data is returned from API
 * - Error state renders when fetch fails
 * - Empty state renders when no events exist
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('next/navigation', () => ({
  usePathname: () => '/audit-log',
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => ({ get: () => null }),
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

// Audit log uses raw fetch (not the api.ts helpers)
global.fetch = jest.fn()

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

// window.open used by export button
const mockWindowOpen = jest.fn()
Object.defineProperty(window, 'open', { value: mockWindowOpen, writable: true })

import AuditLogPage from '@/app/(dashboard)/audit-log/page'

const SAMPLE_ENTRY = {
  id: 'log-uuid-1',
  action: 'bundle.approved',
  resource_type: 'bundle',
  resource_id: 'bundle-uuid-1',
  resource_name: 'KEV Emergency Bundle',
  details: {},
  ip_address: '10.0.0.1',
  user_agent: null,
  success: true,
  error_message: null,
  created_at: new Date().toISOString(),
  user: { id: 'user-1', email: 'admin@example.com', name: 'Admin User' },
}

function mockFetchSuccess(logs = [SAMPLE_ENTRY], total = 1) {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    json: async () => ({ logs, total, limit: 50, offset: 0 }),
  })
}

function mockFetchError() {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: false,
    status: 500,
    json: async () => ({ detail: 'Internal server error' }),
  })
}

beforeEach(() => {
  localStorageMock.clear()
  localStorageMock.setItem('glasswatch_token', 'test-token')
  ;(global.fetch as jest.Mock).mockReset()
  mockWindowOpen.mockReset()
})

afterEach(() => {
  jest.clearAllMocks()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AuditLogPage — structure', () => {
  it('renders the "Audit Log" heading', async () => {
    mockFetchSuccess([])
    render(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getByText('Audit Log')).toBeInTheDocument()
    })
  })

  it('has an Export CSV button', async () => {
    mockFetchSuccess([])
    render(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
    })
  })

  it('Export CSV button opens a window (no navigation error)', async () => {
    mockFetchSuccess([])
    render(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /export csv/i }))
    expect(mockWindowOpen).toHaveBeenCalledTimes(1)
    // Should open the audit-log export endpoint
    const url = mockWindowOpen.mock.calls[0][0] as string
    expect(url).toContain('audit-log')
  })

  it('has Action Type and Resource Type filter selects', async () => {
    mockFetchSuccess([])
    render(<AuditLogPage />)
    await waitFor(() => {
      // Labels exist in the filter bar (not necessarily aria-linked)
      expect(screen.getByText(/action type/i)).toBeInTheDocument()
      expect(screen.getByText(/resource type/i)).toBeInTheDocument()
    })
  })

  it('has an Apply button for filters', async () => {
    mockFetchSuccess([])
    render(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /apply/i })).toBeInTheDocument()
    })
  })
})

describe('AuditLogPage — data rendering', () => {
  it('renders audit log entries from API', async () => {
    mockFetchSuccess([SAMPLE_ENTRY])
    render(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getByText('bundle.approved')).toBeInTheDocument()
    })
  })

  it('renders resource name when present', async () => {
    mockFetchSuccess([SAMPLE_ENTRY])
    render(<AuditLogPage />)
    await waitFor(() => {
      expect(screen.getByText('KEV Emergency Bundle')).toBeInTheDocument()
    })
  })

  it('renders user email or name in the entry', async () => {
    mockFetchSuccess([SAMPLE_ENTRY])
    render(<AuditLogPage />)
    await waitFor(() => {
      // The page shows either user email or name
      const hasUser = screen.queryByText(/admin@example\.com/i) ||
                      screen.queryByText(/admin user/i)
      expect(hasUser).not.toBeNull()
    })
  })
})

describe('AuditLogPage — empty state', () => {
  it('shows something informative when no events exist', async () => {
    mockFetchSuccess([], 0)
    render(<AuditLogPage />)
    await waitFor(() => {
      // Either empty state text or a "0 events" indicator
      const page = document.body.textContent || ''
      expect(
        page.includes('0') ||
        page.toLowerCase().includes('no') ||
        page.toLowerCase().includes('empty')
      ).toBe(true)
    })
  })
})

describe('AuditLogPage — error state', () => {
  it('shows an error message when fetch fails', async () => {
    mockFetchError()
    render(<AuditLogPage />)
    await waitFor(() => {
      // Some error indication must appear (audit log sets error to "HTTP 500" or similar)
      const page = document.body.textContent || ''
      expect(
        page.toLowerCase().includes('error') ||
        page.toLowerCase().includes('failed') ||
        page.includes('HTTP') ||
        page.toLowerCase().includes('something went wrong')
      ).toBe(true)
    })
  })
})

describe('AuditLogPage — filters', () => {
  it('includes action filter in fetch URL after Apply', async () => {
    mockFetchSuccess([])
    render(<AuditLogPage />)
    await waitFor(() => screen.getByText(/action type/i))

    // Get the action select (first select in the filter bar)
    const selects = document.querySelectorAll('select')
    const actionSelect = selects[0]
    expect(actionSelect).toBeTruthy()

    // Set a value
    fireEvent.change(actionSelect, { target: { value: 'bundle' } })

    // Click Apply
    fireEvent.click(screen.getByRole('button', { name: /apply/i }))

    await waitFor(() => {
      const calls = (global.fetch as jest.Mock).mock.calls
      const urls = calls.map(([url]: [string]) => url as string)
      const filtered = urls.some((u) => u.includes('action=bundle') || u.includes('action%3Dbundle'))
      expect(filtered).toBe(true)
    })
  })
})
