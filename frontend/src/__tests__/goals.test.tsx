/**
 * Goals page tests
 *
 * Covers:
 * - Page renders goal cards from API
 * - ?create=true search param auto-opens the create modal
 * - Create modal form is visible and has required fields
 * - Submit error shows readable text (not [object Object])
 * - Empty state renders with Create New Goal button
 * - Error state renders with retry button
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

let mockSearchParamsGet = jest.fn(() => null)

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => ({ get: mockSearchParamsGet }),
  usePathname: () => '/goals',
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

jest.mock('@/lib/api', () => ({
  goalsApi: {
    list: jest.fn(),
    create: jest.fn(),
  },
}))

// TagAutocomplete has complex deps; stub it out
jest.mock('@/components/TagAutocomplete', () => {
  return function TagAutocomplete() {
    return <div data-testid="tag-autocomplete" />
  }
})

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

import GoalsPage from '@/app/(dashboard)/goals/page'
import { goalsApi } from '@/lib/api'

const mockGoalsApi = goalsApi as { list: jest.Mock; create: jest.Mock }

const SAMPLE_GOALS = [
  {
    id: 'goal-uuid-1',
    name: 'Zero Critical Vulnerabilities',
    type: 'zero_critical',
    active: true,
    progress_percentage: 45,
    vulnerabilities_total: 20,
    vulnerabilities_addressed: 9,
    risk_score_initial: 800,
    risk_score_current: 440,
    target_date: null,
    risk_tolerance: 'balanced',
    created_at: new Date().toISOString(),
    next_bundle_date: null,
    estimated_completion_date: null,
  },
  {
    id: 'goal-uuid-2',
    name: 'KEV Elimination Sprint',
    type: 'kev_elimination',
    active: true,
    progress_percentage: 80,
    vulnerabilities_total: 5,
    vulnerabilities_addressed: 4,
    risk_score_initial: 500,
    risk_score_current: 100,
    target_date: null,
    risk_tolerance: 'aggressive',
    created_at: new Date().toISOString(),
    next_bundle_date: null,
    estimated_completion_date: null,
  },
]

beforeEach(() => {
  localStorageMock.clear()
  localStorageMock.setItem('glasswatch_token', 'test-token')
  mockGoalsApi.list.mockResolvedValue([])
  mockGoalsApi.create.mockResolvedValue({ id: 'new-goal-uuid' })
  mockSearchParamsGet = jest.fn(() => null)
})

afterEach(() => {
  jest.clearAllMocks()
})

// ---------------------------------------------------------------------------
// Page rendering
// ---------------------------------------------------------------------------

describe('GoalsPage — rendering', () => {
  it('shows page heading', async () => {
    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.getByText('Optimization Goals')).toBeInTheDocument()
    })
  })

  it('renders goal cards from API data', async () => {
    mockGoalsApi.list.mockResolvedValue(SAMPLE_GOALS)
    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.getByText('Zero Critical Vulnerabilities')).toBeInTheDocument()
      expect(screen.getByText('KEV Elimination Sprint')).toBeInTheDocument()
    })
  })

  it('shows empty state when no goals exist', async () => {
    mockGoalsApi.list.mockResolvedValue([])
    render(<GoalsPage />)
    await waitFor(() => {
      // Empty state should render something actionable — may have multiple Create Goal buttons
      const btns = screen.getAllByRole('button', { name: /create.*goal|new goal/i })
      expect(btns.length).toBeGreaterThan(0)
    })
  })

  it('shows error state with retry button when API fails', async () => {
    mockGoalsApi.list.mockRejectedValue(new Error('Network error'))
    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })
  })

  it('shows Create New Goal button in header', async () => {
    render(<GoalsPage />)
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /create new goal/i })
      ).toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Create modal
// ---------------------------------------------------------------------------

describe('GoalsPage — create modal', () => {
  it('opens create modal when Create New Goal is clicked', async () => {
    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create new goal/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /create new goal/i }))
    await waitFor(() => {
      // Modal should appear — look for the Goal Name input by placeholder
      expect(screen.getByPlaceholderText(/glasswing readiness|goal name|e\.g\./i)).toBeInTheDocument()
    })
  })

  it('auto-opens create modal when ?create=true is in the URL', async () => {
    mockSearchParamsGet = jest.fn((key: string) => (key === 'create' ? 'true' : null))

    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/glasswing readiness|goal name|e\.g\./i)).toBeInTheDocument()
    })
  })

  it('does NOT open modal when ?create param is absent', async () => {
    mockSearchParamsGet = jest.fn(() => null)
    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.queryByRole('textbox', { name: /name/i })).not.toBeInTheDocument()
    })
  })
})

// ---------------------------------------------------------------------------
// Submit error handling — the [object Object] bug
// ---------------------------------------------------------------------------

describe('GoalsPage — create modal submit error serialisation', () => {
  async function openModal() {
    render(<GoalsPage />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create new goal/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /create new goal/i }))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/glasswing readiness|goal name|e\.g\./i)).toBeInTheDocument()
    })
  }

  it('shows readable error text when API returns an Error with a message', async () => {
    mockGoalsApi.create.mockRejectedValue(new Error('Validation failed: name too short'))
    await openModal()

    const nameInput = screen.getByPlaceholderText(/glasswing readiness|goal name|e\.g\./i)
    fireEvent.change(nameInput, { target: { value: 'X' } })

    // The form submit button is type="submit" with text "Create Goal"
    const submitBtn = screen.getByRole('button', { name: /^create goal$/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      const errorEl = screen.queryByText(/validation failed|failed to create/i)
      expect(errorEl).toBeInTheDocument()
    })
  })

  it('error message is never "[object Object]"', async () => {
    // Simulate an error object without a message string
    const weirdError = { detail: [{ msg: 'bad input', loc: ['name'] }] }
    mockGoalsApi.create.mockRejectedValue(weirdError)
    await openModal()

    const nameInput = screen.getByPlaceholderText(/glasswing readiness|goal name|e\.g\./i)
    fireEvent.change(nameInput, { target: { value: 'Test Goal' } })

    const submitBtn = screen.getByRole('button', { name: /^create goal$/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
    })
  })
})
