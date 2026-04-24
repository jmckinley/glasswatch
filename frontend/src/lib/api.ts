/**
 * API client for Glasswatch backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEMO_TENANT = "550e8400-e29b-41d4-a716-446655440000"; // Demo tenant UUID - will use real auth later

interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: any;
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
  }
}

async function apiCall<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint}`;
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Tenant-ID": DEMO_TENANT,
    ...options.headers,
  };
  
  // Add auth token if available (Sprint 13: OAuth support)
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("glasswatch_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const data = await response.json();

  if (!response.ok) {
    // TODO Sprint 13: Implement token refresh on 401
    // For now, clear token and redirect to login
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("glasswatch_token");
      if (!window.location.pathname.includes("/auth/login")) {
        window.location.href = "/auth/login";
      }
    }
    throw new ApiError(response.status, data.detail || "API Error", data);
  }

  return data;
}

// Vulnerability API
export const vulnerabilitiesApi = {
  list: (params?: {
    severity?: string;
    kev_listed?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/vulnerabilities?${query}`);
  },

  get: (id: string) => apiCall<any>(`/vulnerabilities/${id}`),

  stats: () => apiCall<any>("/vulnerabilities/stats"),
};

// Assets API
export const assetsApi = {
  list: (params?: {
    type?: string;
    platform?: string;
    environment?: string;
    criticality?: number;
    exposure?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/assets?${query}`);
  },

  get: (id: string) => apiCall<any>(`/assets/${id}`),

  create: (asset: any) =>
    apiCall<any>("/assets", {
      method: "POST",
      body: asset,
    }),

  update: (id: string, updates: any) =>
    apiCall<any>(`/assets/${id}`, {
      method: "PATCH",
      body: updates,
    }),

  delete: (id: string) =>
    apiCall<any>(`/assets/${id}`, {
      method: "DELETE",
    }),

  bulkImport: (data: any) =>
    apiCall<any>("/assets/bulk-import", {
      method: "POST",
      body: data,
    }),

  tags: () => apiCall<{tags: {name: string, count: number}[]}>('/assets/tags'),

  updateTags: (id: string, add: string[], remove: string[]) =>
    apiCall<any>(`/assets/${id}/tags`, { method: 'PATCH', body: { add, remove } }),

  bulkTag: (assetIds: string[], add: string[], remove: string[]) =>
    apiCall<any>('/assets/bulk-tag', { method: 'POST', body: { asset_ids: assetIds, add, remove } }),

  enrich: (matchBy: string, assets: any[]) =>
    apiCall<any>('/assets/enrich', { method: 'POST', body: { match_by: matchBy, assets } }),

  exportAssets: (params?: any) => {
    const query = new URLSearchParams(params || {}).toString();
    return apiCall<any[]>(`/assets/export${query ? '?' + query : ''}`);
  },

  getVulnerabilities: (id: string, params?: { status?: string; severity?: string; min_score?: number }) => {
    const query = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && query.append(k, String(v)));
    return apiCall<any>(`/assets/${id}/vulnerabilities${query.toString() ? '?' + query : ''}`);
  },

  getPatchHistory: (id: string) => apiCall<any>(`/assets/${id}/patch-history`),

  getRiskBreakdown: (id: string) => apiCall<any>(`/assets/${id}/risk-breakdown`),

  createPatchBundle: (id: string) =>
    apiCall<any>(`/assets/${id}/create-patch-bundle`, { method: 'POST' }),

  stale: (days?: number) => {
    const query = days ? `?days=${days}` : '';
    return apiCall<any>(`/assets/stale${query}`);
  },

  groups: (groupBy?: string) => {
    const query = groupBy ? `?group_by=${groupBy}` : '';
    return apiCall<any>(`/assets/groups${query}`);
  },

  coverage: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : '';
    return apiCall<any>(`/assets/coverage${query}`);
  },
};

// Goals API
export const goalsApi = {
  list: (params?: { active_only?: boolean; type?: string }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/goals?${query}`);
  },

  get: (id: string) => apiCall<any>(`/goals/${id}`),

  create: (goal: any) =>
    apiCall<any>("/goals", {
      method: "POST",
      body: goal,
    }),

  update: (id: string, updates: any) =>
    apiCall<any>(`/goals/${id}`, {
      method: "PATCH",
      body: updates,
    }),

  delete: (id: string) =>
    apiCall<any>(`/goals/${id}`, {
      method: "DELETE",
    }),

  optimize: (
    id: string,
    options: {
      force_reoptimize?: boolean;
      preview_only?: boolean;
      max_future_windows?: number;
    } = {}
  ) =>
    apiCall<any>(`/goals/${id}/optimize`, {
      method: "POST",
      body: options,
    }),

  recommend: (id: string) =>
    apiCall<any>(`/goals/${id}/recommend`, {
      method: "POST",
    }),
};

// Bundles API
export const bundlesApi = {
  list: (params?: {
    status?: string;
    goal_id?: string;
    maintenance_window_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/bundles?${query}`);
  },

  get: (id: string) => apiCall<any>(`/bundles/${id}`),

  assignToWindow: (bundleId: string, windowId: string | null) =>
    apiCall<any>(`/bundles/${bundleId}/assign-window`, {
      method: "PATCH",
      body: { maintenance_window_id: windowId },
    }),

  execute: (id: string) => apiCall<any>(`/bundles/${id}/execute`, { method: 'POST' }),
  approve: (id: string) => apiCall<any>(`/bundles/${id}/approve`, { method: 'POST' }),
  rollback: (id: string) => apiCall<any>(`/bundles/${id}/rollback`, { method: 'POST' }),
  getItems: (id: string) => apiCall<any>(`/bundles/${id}/items`),
  getExecutionLog: (id: string) => apiCall<any>(`/bundles/${id}/execution-log`),
  update: (id: string, data: any) => apiCall<any>(`/bundles/${id}`, { method: 'PATCH', body: data }),
  addItem: (id: string, item: any) => apiCall<any>(`/bundles/${id}/items`, { method: 'POST', body: item }),
  removeItem: (bundleId: string, itemId: string) => apiCall<any>(`/bundles/${bundleId}/items/${itemId}`, { method: 'DELETE' }),
  updateItem: (bundleId: string, itemId: string, data: any) => apiCall<any>(`/bundles/${bundleId}/items/${itemId}`, { method: 'PATCH', body: data }),
};


// Dashboard Stats
export const dashboardApi = {
  getStats: async () => {
    // Aggregate data from multiple endpoints
    const [vulnStats, assetList, goalsList, windowsList, bundlesList] = await Promise.all([
      vulnerabilitiesApi.stats(),
      assetsApi.list({ limit: 200 }), // Need enough to calculate internet_exposed/critical counts
      goalsApi.list({ active_only: true }),
      maintenanceWindowsApi.list({ active: true, limit: 5 }),
      bundlesApi.list({ limit: 100 }),
    ]);

    const assets = assetList.assets || assetList.items || [];
    const windows = windowsList.items || windowsList || [];
    const bundles = bundlesList.items || bundlesList || [];

    // Find next maintenance window
    const upcomingWindows = windows
      .filter((w: any) => new Date(w.start_time) > new Date())
      .sort((a: any, b: any) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
    const nextWindow = upcomingWindows[0];

    // Transform into dashboard format
    return {
      vulnerabilities: {
        total: vulnStats.total,
        critical: vulnStats.by_severity.CRITICAL || 0,
        high: vulnStats.by_severity.HIGH || 0,
        medium: vulnStats.by_severity.MEDIUM || 0,
        low: vulnStats.by_severity.LOW || 0,
        kev_listed: vulnStats.kev_listed || 0,
      },
      assets: {
        total: assetList.total || 0,
        internet_exposed: assets.filter(
          (a: any) => a.exposure === "internet-facing" || a.exposure === "internet" || a.is_internet_facing
        ).length || 0,
        critical_assets: assets.filter(
          (a: any) => a.criticality >= 8
        ).length || 0,
      },
      goals: goalsList,
      risk_score: {
        total: vulnStats.total_risk_score || 0,
        // No historical data available yet - show stable trend
        // Future: Calculate from time-series vulnerability stats
        trend: "stable" as const,
        reduction_7d: 0,
      },
      bundles: {
        scheduled: bundles.filter((b: any) => b.status === "scheduled" || b.status === "approved").length,
        next_window: nextWindow ? nextWindow.start_time : null,
        pending_approval: bundles.filter((b: any) => b.status === "draft" && b.approval_required).length,
      },
      windows: upcomingWindows.slice(0, 2),
    };
  },

  getTopRiskPairs: async (limit: number = 5) => {
    // Call the dedicated backend endpoint that queries asset_vulnerabilities directly
    return apiCall<any[]>(`/dashboard/top-risk-pairs?limit=${limit}`);
  },
};

// Maintenance Windows API
export const maintenanceWindowsApi = {
  list: (params?: {
    active?: boolean;
    environment?: string;
    asset_group?: string;
    service_name?: string;
    skip?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/maintenance-windows?${query}`);
  },

  get: (id: string) => apiCall<any>(`/maintenance-windows/${id}`),

  optimize: () => apiCall<any>("/maintenance-windows/optimize", {
    method: "POST",
  }),

  getBundlesForWindow: (windowId: string) => 
    apiCall<any>(`/maintenance-windows/${windowId}/bundles`),
  
  // Sprint 13: New endpoints
  resolve: (params: { asset_id?: string; environment?: string }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        query.append(key, String(value));
      }
    });
    return apiCall<any>(`/maintenance-windows/resolve?${query}`);
  },
  
  listEnvironments: () => apiCall<{environments: string[]}>("/maintenance-windows/environments"),
  
  listAssetGroups: () => apiCall<{asset_groups: string[]}>("/maintenance-windows/asset-groups"),
  
  create: (window: any) => apiCall<any>("/maintenance-windows", { method: "POST", body: window }),
  
  update: (id: string, updates: any) => apiCall<any>(`/maintenance-windows/${id}`, { method: "PATCH", body: updates }),
  
  delete: (id: string) => apiCall<any>(`/maintenance-windows/${id}`, { method: "DELETE" }),
};

// Tags API
export const tagsApi = {
  list: (params?: { namespace?: string; search?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/tags?${query}`);
  },

  suggest: (params: { q: string; namespace?: string; limit?: number }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        query.append(key, String(value));
      }
    });
    return apiCall<any[]>(`/tags/suggest?${query}`);
  },

  namespaces: () => apiCall<Record<string, number>>("/tags/namespaces"),

  create: (tag: { name: string; namespace: string; description?: string; color?: string; aliases?: string[] }) =>
    apiCall<any>("/tags", { method: "POST", body: tag }),

  update: (id: string, updates: any) =>
    apiCall<any>(`/tags/${id}`, { method: "PATCH", body: updates }),

  delete: (id: string) =>
    apiCall<any>(`/tags/${id}`, { method: "DELETE" }),

  merge: (sourceId: string, targetId: string) =>
    apiCall<any>("/tags/merge", { method: "POST", body: { source_id: sourceId, target_id: targetId } }),
};

// Rules API
export const rulesApi = {
  list: (params?: { scope_type?: string; enabled?: boolean; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          query.append(key, String(value));
        }
      });
    }
    return apiCall<any>(`/rules?${query}`);
  },

  defaults: () => apiCall<any[]>("/rules/defaults"),

  get: (id: string) => apiCall<any>(`/rules/${id}`),

  create: (rule: any) =>
    apiCall<any>("/rules", { method: "POST", body: rule }),

  update: (id: string, updates: any) =>
    apiCall<any>(`/rules/${id}`, { method: "PATCH", body: updates }),

  delete: (id: string) =>
    apiCall<any>(`/rules/${id}`, { method: "DELETE" }),

  evaluate: (request: {
    asset_ids?: string[];
    asset_tags?: string[];
    environment?: string;
    window_id?: string;
    bundle_id?: string;
  }) =>
    apiCall<any>("/rules/evaluate", { method: "POST", body: request }),

  parseNlp: (text: string) =>
    apiCall<any>("/rules/parse-nlp", { method: "POST", body: { text } }),
};

export const settingsApi = {
  get: () => apiCall<any>("/settings"),
  update: (settings: any) => apiCall<any>("/settings", { method: "PATCH", body: { settings } }),
  testConnection: (integration: string, config: Record<string, string>) =>
    apiCall<any>("/settings/test-connection", { method: "POST", body: { integration, config } }),
};

// Agent API
export const agentApi = {
  chat: (message: string, context?: any) =>
    apiCall<{
      response: string;
      actions_taken: string[];
      suggested_actions: string[];
    }>('/agent/chat', { method: 'POST', body: { message, context } }),
};

export const authApi = {
  demoLogin: () => apiCall<any>('/auth/demo-login', { method: 'POST' }),
  login: (email: string, password: string) =>
    apiCall<any>('/auth/email-login', { method: 'POST', body: { email, password } }),
  register: (data: { email: string; password: string; name: string; company_name: string }) =>
    apiCall<any>('/auth/register', { method: 'POST', body: data }),
};

// Reporting & Compliance API
export const reportingApi = {
  getComplianceSummary: () => apiCall<any>('/reporting/compliance-summary'),
  getMttp: () => apiCall<any>('/reporting/mttp'),
  getSlaTracking: (params?: { severity?: string; status?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) query.append(key, String(value));
      });
    }
    return apiCall<any>(`/reporting/sla-tracking${query.toString() ? '?' + query.toString() : ''}`);
  },
  getExecutiveSummary: () => apiCall<any>('/reporting/executive-summary'),
};

export { apiCall };