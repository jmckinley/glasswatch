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
        trend: "down" as const, // TODO: Calculate from history
        reduction_7d: 12.4, // TODO: Calculate from history
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
    // Get vulnerabilities with their affected assets, sorted by risk
    const vulns = await vulnerabilitiesApi.list({ limit: 50 });
    const vulnItems = vulns.items || vulns.vulnerabilities || [];
    
    // Build asset-vulnerability pairs with risk scores
    const pairs: any[] = [];
    for (const vuln of vulnItems) {
      if (vuln.affected_assets && vuln.affected_assets.length > 0) {
        for (const asset of vuln.affected_assets) {
          pairs.push({
            vulnerability_id: vuln.id,
            vulnerability_identifier: vuln.identifier,
            vulnerability_title: vuln.title,
            vulnerability_severity: vuln.severity,
            asset_id: asset.id || asset.asset_id,
            asset_name: asset.name || asset.asset_name,
            asset_environment: asset.environment,
            risk_score: asset.risk_score || vuln.cvss_score * 10,
            risk_factors: {
              severity: vuln.severity,
              kev_listed: vuln.kev_listed,
              epss_score: vuln.epss_score,
              exploit_available: vuln.exploit_available,
              asset_exposure: asset.exposure,
              asset_criticality: asset.criticality,
            },
          });
        }
      }
    }
    
    // Sort by risk score and return top N
    return pairs.sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, limit);
  },
};

// Maintenance Windows API
export const maintenanceWindowsApi = {
  list: (params?: {
    active?: boolean;
    environment?: string;
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
};

export { apiCall };