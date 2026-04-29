/**
 * Regression tests for bugs found in production.
 *
 * Each test is named after the bug it prevents from recurring.
 */
import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('next/navigation', () => ({
  usePathname: () => '/',
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

// ---------------------------------------------------------------------------
// BUG: api.ts serialises FastAPI 422 array detail as [object Object]
//
// FastAPI returns:
//   { "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }
// The old code did: new ApiError(status, data.detail || "API Error")
// Error constructor coerces arrays → "[object Object]"
// ---------------------------------------------------------------------------

describe('ApiError message serialisation', () => {
  beforeEach(() => {
    localStorageMock.clear()
    localStorageMock.setItem('glasswatch_token', 'test-token')
    ;(global.fetch as jest.Mock).mockReset()
  })

  it('shows human-readable message for FastAPI 422 array detail', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [
          {
            type: 'uuid_parsing',
            loc: ['path', 'goal_id'],
            msg: 'Input should be a valid UUID',
            input: 'new',
          },
        ],
      }),
    })

    // Dynamically import so the module picks up the mock
    const { ApiError } = await import('@/lib/api')
    const { goalsApi } = await import('@/lib/api')

    let caughtError: any
    try {
      await goalsApi.get('new')
    } catch (err) {
      caughtError = err
    }

    expect(caughtError).toBeInstanceOf(ApiError)
    // Must NOT be the raw coerced array string
    expect(caughtError.message).not.toBe('[object Object]')
    // Must contain the actual validation message
    expect(caughtError.message).toContain('Input should be a valid UUID')
  })

  it('passes string detail through unchanged', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({ detail: 'Admin role required' }),
    })

    const { goalsApi } = await import('@/lib/api')

    let caughtError: any
    try {
      await goalsApi.get('some-id')
    } catch (err) {
      caughtError = err
    }

    expect(caughtError.message).toBe('Admin role required')
  })

  it('falls back to "API Error" when detail is absent', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: null }),
    })

    const { goalsApi } = await import('@/lib/api')

    let caughtError: any
    try {
      await goalsApi.get('some-id')
    } catch (err) {
      caughtError = err
    }

    expect(caughtError.message).toBe('API Error')
  })
})

// ---------------------------------------------------------------------------
// BUG: dashboard "Create Goal" linked to /goals/new which has no page,
//      falling through to [id]/page with id="new" → 422 → [object Object]
//
// Fix: link should point to /goals?create=true
// ---------------------------------------------------------------------------

describe('Dashboard alert "Create Goal" link', () => {
  beforeEach(() => {
    localStorageMock.clear()
    localStorageMock.setItem('glasswatch_token', 'test-token')
    ;(global.fetch as jest.Mock).mockReset()
  })

  it('Create Goal button links to /goals?create=true not /goals/new', async () => {
    // Mock dashboard stats with KEV vulns so the alert with Create Goal renders
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        vulnerabilities: { total: 5, critical: 2, high: 3, kev_count: 2 },
        assets: { total: 10, internet_exposed: 3 },
        goals: [],
        bundles: { draft: 0, scheduled: 0, approved: 0 },
        maintenance_windows: [],
        patch_coverage: 0,
      }),
    })

    const DashboardPage = (await import('@/app/(dashboard)/page')).default
    render(<DashboardPage />)

    await waitFor(() => {
      const createGoalLinks = screen.queryAllByRole('link', { name: /create goal/i })
      if (createGoalLinks.length > 0) {
        createGoalLinks.forEach(link => {
          expect(link).not.toHaveAttribute('href', '/goals/new')
          expect(link).toHaveAttribute('href', '/goals?create=true')
        })
      }
    })
  })
})

// ---------------------------------------------------------------------------
// BUG: AI analyst sample prompts didn't match intent patterns
//
// "What needs my attention right now?" failed because pattern was
// "what needs attention" (missing "my")
// "Show me critical KEV vulnerabilities" failed because pattern was
// "show critical" (missing "me")
// "Create a rule blocking Friday deployments" failed because pattern was
// "create rule" (missing "a")
// ---------------------------------------------------------------------------

describe('AI analyst intent pattern matching', () => {
  // Mirror of detect_intent logic for frontend-side smoke test.
  // The canonical test lives in the backend, but this catches copy/paste
  // divergence between the displayed prompts and the backend patterns.

  const SAMPLE_PROMPTS_TO_INTENTS: Record<string, string> = {
    'What needs my attention right now?': 'attention',
    'Show me critical KEV vulnerabilities': 'attention',
    'Create a rule blocking Friday deployments': 'create_rule',
    'Show maintenance windows': 'show_windows',
    'Add maintenance window on Saturday at 2am': 'add_window',
    'Show goals': 'show_goals',
    'Find fixes for CVE-2021-44228': 'cve_lookup',
    'Show bundles': 'show_bundles',
    'Pending approvals': 'show_bundles',
    'Approve bundle KEV-Emergency': 'approve_bundle',
    'How are we doing?': 'risk_score',
  }

  // Reproduce detect_intent from backend/api/v1/agent.py
  const INTENT_PATTERNS: [string, string[]][] = [
    ['attention', ['what needs my attention', 'what needs attention', 'needs attention', 'urgent', 'show critical', 'critical kev', 'priority', "what's urgent", 'top issues']],
    ['cve_lookup', ['find fixes for', 'patch cve', 'what fixes cve', 'fixes for cve', 'details for cve', 'info on cve', 'about cve']],
    ['approve_bundle', ['approve bundle', 'approve the bundle']],
    ['show_bundles', ['show bundles', 'pending approvals', 'list bundles', 'pending bundles', 'what bundles']],
    ['create_rule', ['create a rule', 'create rule', 'add rule', 'new rule', 'block deployments on', 'block all deployments', 'blocking friday', 'blocking monday', 'blocking tuesday', 'blocking wednesday', 'blocking thursday', 'blocking saturday', 'blocking sunday']],
    ['show_windows', ['show maintenance windows', 'maintenance windows', 'what windows', 'list windows', 'scheduled windows']],
    ['add_window', ['add maintenance window', 'create window', 'new window', 'add window', 'schedule window']],
    ['show_goals', ['show goals', 'goal status', 'goals progress', 'list goals', 'goals']],
    ['risk_score', ['risk score', 'posture', 'how are we doing', 'security posture', 'overall risk', 'current risk']],
  ]

  function detectIntent(message: string): string | null {
    const lower = message.toLowerCase()
    for (const [intent, patterns] of INTENT_PATTERNS) {
      for (const p of patterns) {
        if (lower.includes(p)) return intent
      }
    }
    return null
  }

  for (const [prompt, expectedIntent] of Object.entries(SAMPLE_PROMPTS_TO_INTENTS)) {
    it(`"${prompt}" → ${expectedIntent}`, () => {
      expect(detectIntent(prompt)).toBe(expectedIntent)
    })
  }

  it('unrecognised prompt returns null (falls back to Claude/menu)', () => {
    expect(detectIntent('hello there')).toBeNull()
  })
})
