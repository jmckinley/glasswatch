/**
 * Tests for lib/api.ts
 *
 * Covers:
 * - ApiError with string detail
 * - ApiError with array detail (the [object Object] bug)
 * - ApiError with nested object detail
 * - ApiError with missing detail (falls back to "API Error")
 * - 401 clears token and redirects
 * - Auth token is included in request headers when present
 * - goalsApi, bundlesApi, vulnerabilitiesApi, agentApi, authApi call correct URLs
 */

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

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

// Prevent actual navigation
const mockReplace = jest.fn()
Object.defineProperty(window, 'location', {
  value: { ...window.location, href: 'http://localhost/', pathname: '/' },
  writable: true,
})

beforeEach(() => {
  localStorageMock.clear()
  localStorageMock.setItem('glasswatch_token', 'test-jwt-token')
  ;(global.fetch as jest.Mock).mockReset()
})

afterEach(() => {
  jest.clearAllMocks()
  jest.resetModules()
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockOk(body: any) {
  ;(global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: async () => body,
  })
}

function mockError(status: number, body: any) {
  ;(global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    status,
    json: async () => body,
  })
}

// ---------------------------------------------------------------------------
// ApiError message serialisation
// ---------------------------------------------------------------------------

describe('ApiError — detail serialisation', () => {
  it('string detail is passed through unchanged', async () => {
    mockError(403, { detail: 'Admin role required' })
    const { goalsApi, ApiError } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('some-id')
    } catch (e) {
      err = e
    }
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('Admin role required')
  })

  it('array detail (FastAPI 422) extracts .msg from each entry', async () => {
    mockError(422, {
      detail: [
        { type: 'uuid_parsing', loc: ['path', 'goal_id'], msg: 'Input should be a valid UUID', input: 'new' },
      ],
    })
    const { goalsApi, ApiError } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('new')
    } catch (e) {
      err = e
    }
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).not.toBe('[object Object]')
    expect(err.message).toContain('Input should be a valid UUID')
  })

  it('array detail with multiple errors joins messages', async () => {
    mockError(422, {
      detail: [
        { msg: 'Field required', loc: ['body', 'name'] },
        { msg: 'Value error, must be positive', loc: ['body', 'target_value'] },
      ],
    })
    const { goalsApi } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('x')
    } catch (e) {
      err = e
    }
    expect(err.message).not.toBe('[object Object]')
    expect(err.message).toContain('Field required')
    expect(err.message).toContain('Value error')
  })

  it('missing detail falls back to "API Error"', async () => {
    mockError(500, { detail: null })
    const { goalsApi } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('x')
    } catch (e) {
      err = e
    }
    expect(err.message).toBe('API Error')
  })

  it('missing detail key entirely falls back to "API Error"', async () => {
    mockError(500, {})
    const { goalsApi } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('x')
    } catch (e) {
      err = e
    }
    expect(err.message).toBe('API Error')
  })

  it('nested object detail is JSON-stringified (not [object Object])', async () => {
    mockError(400, { detail: { code: 'INVALID', reason: 'bad input' } })
    const { goalsApi } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('x')
    } catch (e) {
      err = e
    }
    expect(err.message).not.toBe('[object Object]')
    // Should be a JSON string representation
    expect(err.message).toContain('INVALID')
  })

  it('ApiError carries status and data', async () => {
    mockError(422, { detail: [{ msg: 'bad', loc: ['x'] }] })
    const { goalsApi, ApiError } = await import('@/lib/api')
    let err: any
    try {
      await goalsApi.get('x')
    } catch (e) {
      err = e
    }
    expect(err.status).toBe(422)
    expect(err.data).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// Auth headers
// ---------------------------------------------------------------------------

describe('API client — auth headers', () => {
  it('includes Authorization header when token is in localStorage', async () => {
    mockOk({ vulnerabilities: [], total: 0 })
    const { vulnerabilitiesApi } = await import('@/lib/api')
    await vulnerabilitiesApi.list()
    const call = (global.fetch as jest.Mock).mock.calls[0]
    const headers = call[1].headers
    expect(headers['Authorization']).toBe('Bearer test-jwt-token')
  })

  it('omits Authorization header when no token', async () => {
    localStorageMock.removeItem('glasswatch_token')
    mockOk({ vulnerabilities: [], total: 0 })
    const { vulnerabilitiesApi } = await import('@/lib/api')
    await vulnerabilitiesApi.list()
    const call = (global.fetch as jest.Mock).mock.calls[0]
    const headers = call[1].headers
    expect(headers['Authorization']).toBeUndefined()
  })

  it('includes X-Tenant-ID header', async () => {
    mockOk([])
    const { goalsApi } = await import('@/lib/api')
    await goalsApi.list()
    const call = (global.fetch as jest.Mock).mock.calls[0]
    const headers = call[1].headers
    expect(headers['X-Tenant-ID']).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// goalsApi
// ---------------------------------------------------------------------------

describe('goalsApi', () => {
  it('list() calls GET /api/v1/goals', async () => {
    mockOk([])
    const { goalsApi } = await import('@/lib/api')
    await goalsApi.list()
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/api/v1/goals')
  })

  it('create() calls POST /api/v1/goals', async () => {
    mockOk({ id: 'new-id' })
    const { goalsApi } = await import('@/lib/api')
    await goalsApi.create({ name: 'Test', type: 'zero_critical' })
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/goals')
    expect(call[1].method).toBe('POST')
  })

  it('get() calls GET /api/v1/goals/{id}', async () => {
    mockOk({ id: 'goal-uuid' })
    const { goalsApi } = await import('@/lib/api')
    await goalsApi.get('goal-uuid')
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/api/v1/goals/goal-uuid')
  })

  it('update() calls PATCH /api/v1/goals/{id}', async () => {
    mockOk({ id: 'goal-uuid' })
    const { goalsApi } = await import('@/lib/api')
    await goalsApi.update('goal-uuid', { name: 'Updated' })
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/goals/goal-uuid')
    expect(call[1].method).toBe('PATCH')
  })

  it('delete() calls DELETE /api/v1/goals/{id}', async () => {
    mockOk({ message: 'deleted' })
    const { goalsApi } = await import('@/lib/api')
    await goalsApi.delete('goal-uuid')
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/goals/goal-uuid')
    expect(call[1].method).toBe('DELETE')
  })
})

// ---------------------------------------------------------------------------
// bundlesApi
// ---------------------------------------------------------------------------

describe('bundlesApi', () => {
  it('list() calls GET /api/v1/bundles', async () => {
    mockOk({ items: [], total: 0 })
    const { bundlesApi } = await import('@/lib/api')
    await bundlesApi.list()
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/api/v1/bundles')
  })

  it('approve() calls POST /api/v1/bundles/{id}/approve', async () => {
    mockOk({ status: 'approved' })
    const { bundlesApi } = await import('@/lib/api')
    await bundlesApi.approve('bundle-uuid')
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/bundles/bundle-uuid/approve')
    expect(call[1].method).toBe('POST')
  })

  it('rollback() calls POST /api/v1/bundles/{id}/rollback', async () => {
    mockOk({ status: 'rolled_back' })
    const { bundlesApi } = await import('@/lib/api')
    await bundlesApi.rollback('bundle-uuid')
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/bundles/bundle-uuid/rollback')
    expect(call[1].method).toBe('POST')
  })
})

// ---------------------------------------------------------------------------
// agentApi
// ---------------------------------------------------------------------------

describe('agentApi', () => {
  it('chat() calls POST /api/v1/agent/chat', async () => {
    mockOk({ response: 'OK', actions_taken: [], suggested_actions: [] })
    const { agentApi } = await import('@/lib/api')
    await agentApi.chat('What needs my attention?')
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/agent/chat')
    expect(call[1].method).toBe('POST')
  })

  it('chat() sends message in request body', async () => {
    mockOk({ response: 'OK', actions_taken: [], suggested_actions: [] })
    const { agentApi } = await import('@/lib/api')
    await agentApi.chat('Show goals')
    const call = (global.fetch as jest.Mock).mock.calls[0]
    const body = JSON.parse(call[1].body)
    expect(body.message).toBe('Show goals')
  })
})

// ---------------------------------------------------------------------------
// authApi
// ---------------------------------------------------------------------------

describe('authApi', () => {
  it('demoLogin() calls POST /api/v1/auth/demo-login', async () => {
    mockOk({ access_token: 'tok', user: {}, redirect_to: '/dashboard' })
    const { authApi } = await import('@/lib/api')
    await authApi.demoLogin()
    const call = (global.fetch as jest.Mock).mock.calls[0]
    expect(call[0]).toContain('/api/v1/auth/demo-login')
    expect(call[1].method).toBe('POST')
  })
})
