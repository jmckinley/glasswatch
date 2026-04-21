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

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const data = await response.json();

  if (!response.ok) {
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
};

// Dashboard Stats
export const dashboardApi = {
  getStats: async () => {
    // Aggregate data from multiple endpoints
    const [vulnStats, assetList, goalsList] = await Promise.all([
      vulnerabilitiesApi.stats(),
      assetsApi.list({ limit: 100 }), // Need enough to calculate internet_exposed/critical counts
      goalsApi.list({ active_only: true }),
    ]);

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
        internet_exposed: (assetList.assets || assetList.items || []).filter(
          (a: any) => a.exposure === "internet" || a.is_internet_facing
        ).length || 0,
        critical_assets: (assetList.assets || assetList.items || []).filter(
          (a: any) => a.criticality >= 4
        ).length || 0,
      },
      goals: {
        active: goalsList.length,
        on_track: goalsList.filter(
          (g: any) => g.progress_percentage >= 50
        ).length,
        at_risk: goalsList.filter(
          (g: any) => g.progress_percentage < 50 && g.target_date
        ).length,
      },
      risk_score: {
        total: vulnStats.total_risk_score || 0,
        trend: "down" as const, // TODO: Calculate from history
        reduction_7d: 12.4, // TODO: Calculate from history
      },
      bundles: {
        scheduled: 0, // TODO: Add bundles API
        next_window: null, // TODO: Get from maintenance windows
        pending_approval: 0, // TODO: Add bundles API
      },
    };
  },
};