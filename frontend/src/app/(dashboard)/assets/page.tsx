"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { assetsApi } from "@/lib/api";
import TagAutocomplete from "@/components/TagAutocomplete";

interface Asset {
  id: string;
  identifier: string;
  name: string;
  type: string;
  platform: string;
  environment: string;
  criticality: number;
  exposure: string;
  location: string;
  owner_team: string;
  risk_score: number;
  is_internet_facing: boolean;
  last_scanned_at: string | null;
  created_at: string;
  tags: string[];
  patch_group: string | null;
  os_family: string | null;
  fqdn: string | null;
  business_unit: string | null;
  vulnerability_count: number;
}

interface Tag {
  name: string;
  count: number;
}

const tagColors = [
  'bg-blue-500/20 text-blue-300 border-blue-500/30',
  'bg-green-500/20 text-green-300 border-green-500/30',
  'bg-purple-500/20 text-purple-300 border-purple-500/30',
  'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  'bg-pink-500/20 text-pink-300 border-pink-500/30',
  'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  'bg-orange-500/20 text-orange-300 border-orange-500/30',
  'bg-red-500/20 text-red-300 border-red-500/30',
];

function getTagColor(tag: string) {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  }
  return tagColors[Math.abs(hash) % tagColors.length];
}

const CRITICALITY_COLORS: Record<number, string> = {
  9: "text-red-500",
  8: "text-red-400",
  7: "text-orange-500",
  6: "text-orange-400",
  5: "text-yellow-500",
  4: "text-yellow-400",
  3: "text-blue-400",
  2: "text-blue-300",
  1: "text-gray-400",
};

interface CoverageRow {
  vulnerability_id: string;
  identifier: string;
  severity: string;
  cvss_score: number | null;
  kev_listed: boolean;
  patch_available: boolean;
  total_assets: number;
  patched_assets: number;
  unpatched_assets: number;
  coverage_pct: number;
}

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-500/20 text-red-300",
  HIGH: "bg-orange-500/20 text-orange-300",
  MEDIUM: "bg-yellow-500/20 text-yellow-300",
  LOW: "bg-blue-500/20 text-blue-300",
};

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [staleAssets, setStaleAssets] = useState<Set<string>>(new Set());
  const [staleDays, setStaleDays] = useState<Record<string, number | null>>({});
  const [coverage, setCoverage] = useState<CoverageRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [showBulkTagModal, setShowBulkTagModal] = useState(false);
  const [activeMainTab, setActiveMainTab] = useState<"assets" | "coverage">("assets");
  const [staleOnly, setStaleOnly] = useState(false);
  const [filters, setFilters] = useState({
    search: "",
    environment: "",
    type: "",
    platform: "",
    exposure: "",
    criticality: "",
    patch_group: "",
    tag: "",
    sort_by: "name",
  });
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 50,
    total: 0,
  });

  useEffect(() => { document.title = 'Assets | Glasswatch'; }, []);

  useEffect(() => {
    fetchAssets();
    fetchTags();
  }, [filters, pagination.skip, staleOnly]);

  const fetchCoverage = useCallback(async () => {
    if (coverage.length > 0) return; // already loaded
    setCoverageLoading(true);
    try {
      const data = await assetsApi.coverage(100);
      setCoverage(data.coverage || []);
    } catch (err) {
      console.error("Failed to fetch coverage:", err);
    } finally {
      setCoverageLoading(false);
    }
  }, [coverage.length]);

  const fetchStaleInfo = async () => {
    try {
      const data = await assetsApi.stale(30);
      const staleSet = new Set<string>((data.assets || []).map((a: any) => a.id as string));
      const daysMap: Record<string, number | null> = {};
      (data.assets || []).forEach((a: any) => { daysMap[a.id] = a.days_since_scan; });
      setStaleAssets(staleSet);
      setStaleDays(daysMap);
    } catch (err) {
      // stale check is best-effort
    }
  };

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const params: any = {
        skip: pagination.skip,
        limit: pagination.limit,
      };
      if (filters.search) params.search = filters.search;
      if (filters.environment) params.environment = filters.environment;
      if (filters.type) params.type = filters.type;
      if (filters.platform) params.platform = filters.platform;
      if (filters.exposure) params.exposure = filters.exposure;
      if (filters.criticality) params.criticality = parseInt(filters.criticality);
      if (filters.patch_group) params.patch_group = filters.patch_group;
      if (filters.tag) params.tag = filters.tag;
      if (filters.sort_by) params.sort_by = filters.sort_by;

      if (staleOnly) {
        // Use stale endpoint and display those assets
        const staleData = await assetsApi.stale(30);
        const staleList = staleData.assets || [];
        setAssets(staleList.map((a: any) => ({ ...a, vulnerability_count: 0, is_internet_facing: false })));
        setPagination(prev => ({ ...prev, total: staleList.length }));
        const staleSet = new Set<string>(staleList.map((a: any) => a.id as string));
        const daysMap: Record<string, number | null> = {};
        staleList.forEach((a: any) => { daysMap[a.id] = a.days_since_scan; });
        setStaleAssets(staleSet);
        setStaleDays(daysMap);
      } else {
        const data = await assetsApi.list(params);
        setAssets(data.assets || data.items || []);
        setPagination(prev => ({ ...prev, total: data.total || 0 }));
        // Also fetch stale info in background to show badges
        fetchStaleInfo();
      }
    } catch (error) {
      console.error("Failed to fetch assets:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTags = async () => {
    try {
      const data = await assetsApi.tags();
      setAllTags(data.tags || []);
    } catch (error) {
      console.error("Failed to fetch tags:", error);
    }
  };

  const toggleAssetSelection = (assetId: string) => {
    const newSelection = new Set(selectedAssets);
    if (newSelection.has(assetId)) {
      newSelection.delete(assetId);
    } else {
      newSelection.add(assetId);
    }
    setSelectedAssets(newSelection);
  };

  const toggleSelectAll = () => {
    if (selectedAssets.size === assets.length) {
      setSelectedAssets(new Set());
    } else {
      setSelectedAssets(new Set(assets.map(a => a.id)));
    }
  };

  const handleRemoveTag = async (assetId: string, tag: string) => {
    try {
      await assetsApi.updateTags(assetId, [], [tag]);
      fetchAssets();
      fetchTags();
    } catch (error) {
      console.error("Failed to remove tag:", error);
    }
  };

  const handleAddTag = async (assetId: string, tag: string) => {
    try {
      await assetsApi.updateTags(assetId, [tag], []);
      fetchAssets();
      fetchTags();
    } catch (error) {
      console.error("Failed to add tag:", error);
    }
  };

  const handleExportCSV = () => {
    // Get assets to export (selected or all visible)
    const assetsToExport = selectedAssets.size > 0 
      ? assets.filter(a => selectedAssets.has(a.id))
      : assets;

    if (assetsToExport.length === 0) {
      alert("No assets to export");
      return;
    }

    // CSV headers
    const headers = [
      "Name",
      "Identifier",
      "FQDN",
      "Environment",
      "Criticality",
      "Exposure",
      "Tags",
      "Last Scanned"
    ];

    // Build CSV rows
    const rows = assetsToExport.map(asset => [
      asset.name || "",
      asset.identifier || "",
      asset.fqdn || "",
      asset.environment || "",
      asset.criticality?.toString() || "",
      asset.exposure || "",
      (asset.tags || []).join("; ") || "",
      asset.last_scanned_at ? new Date(asset.last_scanned_at).toLocaleDateString() : "Never"
    ]);

    // Escape CSV values (handle commas, quotes, newlines)
    const escapeCSV = (value: string) => {
      if (value.includes(",") || value.includes('"') || value.includes("\n")) {
        return `"${value.replace(/"/g, '""')}"`;
      }
      return value;
    };

    // Build CSV content
    const csvContent = [
      headers.map(escapeCSV).join(","),
      ...rows.map(row => row.map(escapeCSV).join(","))
    ].join("\n");

    // Create download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const today = new Date().toISOString().split("T")[0];
    link.download = `glasswatch-assets-${today}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const stats = {
    total: pagination.total,
    internetFacing: assets.filter(a => a.is_internet_facing || a.exposure === 'internet-facing' || a.exposure === 'internet').length,
    critical: assets.filter(a => a.criticality >= 8).length,
    unscanned: assets.filter(a => !a.last_scanned_at).length,
    byEnvironment: {
      production: assets.filter(a => a.environment === 'production').length,
      staging: assets.filter(a => a.environment === 'staging').length,
      development: assets.filter(a => a.environment === 'development').length,
    },
  };

  const totalPages = Math.ceil(pagination.total / pagination.limit);
  const currentPage = Math.floor(pagination.skip / pagination.limit) + 1;

  return (
    <>
      {/* Page-level Tabs + Links */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1 border-b border-gray-700">
          {(["assets", "coverage"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => {
                setActiveMainTab(tab);
                if (tab === "coverage") fetchCoverage();
              }}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeMainTab === tab
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-400 hover:text-gray-300"
              }`}
            >
              {tab === "assets" ? "Assets" : "Patch Coverage"}
            </button>
          ))}
        </div>
        <Link
          href="/assets/groups"
          className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
        >
          📊 Asset Groups
        </Link>
      </div>

      {/* ── Coverage Tab ── */}
      {activeMainTab === "coverage" && (
        <div className="space-y-4">
          {coverageLoading ? (
            <div className="text-center py-16 text-gray-400 animate-pulse">Loading coverage…</div>
          ) : coverage.length === 0 ? (
            <div className="text-center py-16 text-gray-500">No coverage data found</div>
          ) : (
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div className="p-4 border-b border-gray-700">
                <h2 className="text-sm font-medium text-gray-300">Patch Coverage by CVE — {coverage.length} vulnerabilities</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-900 text-gray-400">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium">CVE ID</th>
                      <th className="text-left px-4 py-3 font-medium">Severity</th>
                      <th className="text-left px-4 py-3 font-medium">CVSS</th>
                      <th className="text-left px-4 py-3 font-medium">KEV</th>
                      <th className="text-left px-4 py-3 font-medium"># Affected</th>
                      <th className="text-left px-4 py-3 font-medium"># Patched</th>
                      <th className="text-left px-4 py-3 font-medium"># Unpatched</th>
                      <th className="text-left px-4 py-3 font-medium">Coverage</th>
                      <th className="text-left px-4 py-3 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coverage.map(row => (
                      <tr key={row.vulnerability_id} className="border-t border-gray-700 hover:bg-gray-700/30">
                        <td className="px-4 py-3 font-mono text-blue-400 text-xs">{row.identifier}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 text-xs rounded ${SEVERITY_BADGE[row.severity] || SEVERITY_BADGE.LOW}`}>
                            {row.severity}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-300 text-xs font-mono">
                          {row.cvss_score != null ? row.cvss_score.toFixed(1) : "—"}
                        </td>
                        <td className="px-4 py-3">
                          {row.kev_listed ? (
                            <span className="px-1.5 py-0.5 text-xs rounded bg-red-600/30 text-red-300 font-semibold">KEV</span>
                          ) : <span className="text-gray-600 text-xs">—</span>}
                        </td>
                        <td className="px-4 py-3 text-gray-300 text-xs">{row.total_assets}</td>
                        <td className="px-4 py-3 text-green-400 text-xs">{row.patched_assets}</td>
                        <td className="px-4 py-3 text-xs">
                          <span className={row.unpatched_assets > 0 ? "text-red-400" : "text-gray-500"}>
                            {row.unpatched_assets}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  row.coverage_pct >= 80 ? "bg-green-500" :
                                  row.coverage_pct >= 50 ? "bg-orange-500" : "bg-red-500"
                                }`}
                                style={{ width: `${row.coverage_pct}%` }}
                              />
                            </div>
                            <span className={`text-xs font-medium ${
                              row.coverage_pct >= 80 ? "text-green-400" :
                              row.coverage_pct >= 50 ? "text-orange-400" : "text-red-400"
                            }`}>
                              {row.coverage_pct.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {row.unpatched_assets > 0 && (
                            <Link
                              href={`/vulnerabilities/${row.vulnerability_id}`}
                              className="px-2 py-1 text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded hover:bg-blue-600/30 transition-colors"
                            >
                              View Unpatched
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Assets Tab ── */}
      {activeMainTab !== "assets" ? null : (
      <>
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-white">{stats.total.toLocaleString()}</div>
          <div className="text-sm text-gray-400">Total Assets</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-orange-400">{stats.internetFacing}</div>
          <div className="text-sm text-gray-400">Internet-Facing</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-red-400">{stats.critical}</div>
          <div className="text-sm text-gray-400">Critical (≥8)</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-yellow-400">{stats.unscanned}</div>
          <div className="text-sm text-gray-400">Unscanned</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Production</div>
          <div className="text-xl font-bold text-white">{stats.byEnvironment.production}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Staging/Dev</div>
          <div className="text-xl font-bold text-white">
            {stats.byEnvironment.staging + stats.byEnvironment.development}
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-gray-800 rounded-lg p-4 mb-4">
        <input
          type="text"
          placeholder="Search by name, identifier, or FQDN..."
          className="w-full px-4 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filters.search}
          onChange={(e) => {
            setFilters({ ...filters, search: e.target.value });
            setPagination(prev => ({ ...prev, skip: 0 }));
          }}
        />
      </div>

      {/* Filters Bar */}
      <div className="bg-gray-800 rounded-lg p-4 mb-4">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <select
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.environment}
            onChange={(e) => setFilters({ ...filters, environment: e.target.value })}
          >
            <option value="">All Environments</option>
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
          </select>

          <select
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}
          >
            <option value="">All Types</option>
            <option value="server">Server</option>
            <option value="database">Database</option>
            <option value="container">Container</option>
            <option value="load-balancer">Load Balancer</option>
            <option value="network">Network</option>
          </select>

          <select
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.platform}
            onChange={(e) => setFilters({ ...filters, platform: e.target.value })}
          >
            <option value="">All Platforms</option>
            <option value="linux">Linux</option>
            <option value="windows">Windows</option>
            <option value="macos">macOS</option>
            <option value="kubernetes">Kubernetes</option>
          </select>

          <select
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.exposure}
            onChange={(e) => setFilters({ ...filters, exposure: e.target.value })}
          >
            <option value="">All Exposure</option>
            <option value="internet-facing">Internet-Facing</option>
            <option value="internal">Internal</option>
            <option value="isolated">Isolated</option>
          </select>

          <select
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.criticality}
            onChange={(e) => setFilters({ ...filters, criticality: e.target.value })}
          >
            <option value="">All Criticality</option>
            {[9, 8, 7, 6, 5, 4, 3, 2, 1].map(c => (
              <option key={c} value={c}>Criticality {c}</option>
            ))}
          </select>

          <input
            type="text"
            placeholder="Patch group..."
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.patch_group}
            onChange={(e) => setFilters({ ...filters, patch_group: e.target.value })}
          />

          <select
            className="px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.sort_by}
            onChange={(e) => setFilters({ ...filters, sort_by: e.target.value })}
          >
            <option value="name">Sort: Name</option>
            <option value="criticality">Sort: Criticality</option>
            <option value="risk_score">Sort: Risk Score</option>
            <option value="vulnerability_count">Sort: Vuln Count</option>
          </select>
        </div>
        {/* Stale filter */}
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-700">
          <button
            onClick={() => {
              setStaleOnly(v => !v);
              setPagination(prev => ({ ...prev, skip: 0 }));
            }}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              staleOnly
                ? "bg-yellow-500/20 border-yellow-500/50 text-yellow-300"
                : "bg-gray-700 border-gray-600 text-gray-400 hover:text-gray-300"
            }`}
          >
            ⚠️ Stale Assets ({staleAssets.size > 0 ? staleAssets.size : "not scanned in 30+ days"})
          </button>
          {staleOnly && (
            <span className="text-xs text-yellow-400">Showing assets not scanned in 30+ days</span>
          )}
        </div>
      </div>

      {/* Tag Cloud */}
      {allTags.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <div className="text-sm text-gray-400 mb-2">Filter by tag:</div>
          <div className="flex flex-wrap gap-2">
            {allTags.map(tag => (
              <button
                key={tag.name}
                onClick={() => setFilters({ ...filters, tag: filters.tag === tag.name ? "" : tag.name })}
                className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                  filters.tag === tag.name
                    ? 'bg-blue-500/30 border-blue-500 text-blue-200'
                    : getTagColor(tag.name)
                }`}
              >
                {tag.name} ({tag.count})
              </button>
            ))}
            {filters.tag && (
              <button
                onClick={() => setFilters({ ...filters, tag: "" })}
                className="px-3 py-1 rounded-full text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
              >
                Clear filter
              </button>
            )}
          </div>
        </div>
      )}

      {/* Bulk Actions Bar */}
      {selectedAssets.size > 0 && (
        <div className="bg-blue-900/30 border border-blue-500/30 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <div className="text-white">
              {selectedAssets.size} asset{selectedAssets.size !== 1 ? 's' : ''} selected
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowBulkTagModal(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Tag Selected
              </button>
              <button
                onClick={handleExportCSV}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Export Selected
              </button>
              <button
                onClick={() => setSelectedAssets(new Set())}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Clear Selection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assets Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900 border-b border-gray-700">
            <tr>
              <th className="text-left px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedAssets.size === assets.length && assets.length > 0}
                  onChange={toggleSelectAll}
                  className="rounded"
                />
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Name</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Type</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Environment</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Criticality</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Exposure</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Patch Group</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Tags</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Vulns</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Risk</th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-400">Last Scanned</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={11} className="text-center py-12 text-gray-400">
                  Loading assets...
                </td>
              </tr>
            ) : assets.length === 0 ? (
              <tr>
                <td colSpan={11} className="text-center py-12 text-gray-400">
                  No assets found
                </td>
              </tr>
            ) : (
              assets.map((asset) => (
                <AssetRow
                  key={asset.id}
                  asset={asset}
                  selected={selectedAssets.has(asset.id)}
                  onToggleSelect={() => toggleAssetSelection(asset.id)}
                  onRemoveTag={(tag) => handleRemoveTag(asset.id, tag)}
                  onAddTag={(tag) => handleAddTag(asset.id, tag)}
                  availableTags={allTags.map(t => t.name)}
                  isStale={staleAssets.has(asset.id)}
                  daysSinceScan={staleDays[asset.id]}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-6">
          <button
            onClick={() =>
              setPagination((prev) => ({
                ...prev,
                skip: Math.max(0, prev.skip - prev.limit),
              }))
            }
            disabled={currentPage === 1}
            className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-gray-400">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() =>
              setPagination((prev) => ({
                ...prev,
                skip: prev.skip + prev.limit,
              }))
            }
            disabled={currentPage === totalPages}
            className="px-4 py-2 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {/* Bulk Tag Modal */}
      {showBulkTagModal && (
        <BulkTagModal
          assetIds={Array.from(selectedAssets)}
          onClose={() => setShowBulkTagModal(false)}
          onComplete={() => {
            setShowBulkTagModal(false);
            setSelectedAssets(new Set());
            fetchAssets();
            fetchTags();
          }}
          availableTags={allTags.map(t => t.name)}
        />
      )}
      </> /* end assets tab */
      )}
    </>
  );
}

function AssetRow({
  asset,
  selected,
  onToggleSelect,
  onRemoveTag,
  onAddTag,
  availableTags,
  isStale,
  daysSinceScan,
}: {
  asset: Asset;
  selected: boolean;
  onToggleSelect: () => void;
  onRemoveTag: (tag: string) => void;
  onAddTag: (tag: string) => void;
  availableTags: string[];
  isStale?: boolean;
  daysSinceScan?: number | null;
}) {
  const [showTagPopover, setShowTagPopover] = useState(false);
  const [tagSearchInput, setTagSearchInput] = useState("");
  const criticalityColor = CRITICALITY_COLORS[asset.criticality] || "text-gray-400";
  const lastScanned = asset.last_scanned_at
    ? new Date(asset.last_scanned_at).toLocaleDateString()
    : "Never";

  const riskBarWidth = Math.min(100, (asset.risk_score / 1000) * 100);
  const riskColor = asset.risk_score > 700 ? 'bg-red-500' : asset.risk_score > 400 ? 'bg-orange-500' : 'bg-yellow-500';

  const filteredTags = availableTags.filter(tag => 
    !asset.tags.includes(tag) && 
    tag.toLowerCase().includes(tagSearchInput.toLowerCase())
  );

  const handleAddTag = (tag: string) => {
    onAddTag(tag);
    setShowTagPopover(false);
    setTagSearchInput("");
  };

  const handleCreateNewTag = () => {
    if (tagSearchInput.trim()) {
      onAddTag(tagSearchInput.trim());
      setShowTagPopover(false);
      setTagSearchInput("");
    }
  };

  return (
    <tr className="border-b border-gray-700 hover:bg-gray-700/30 transition-colors">
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
          className="rounded"
        />
      </td>
      <td className="px-4 py-3">
        <Link
          href={`/assets/${asset.id}`}
          className="text-white font-medium hover:text-blue-400 transition-colors"
        >
          {asset.name}
        </Link>
        <div className="text-sm text-gray-400">{asset.identifier}</div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-300">{asset.type}</td>
      <td className="px-4 py-3">
        <span className={`px-2 py-1 text-xs rounded ${
          asset.environment === 'production'
            ? 'bg-red-500/20 text-red-300'
            : asset.environment === 'staging'
            ? 'bg-yellow-500/20 text-yellow-300'
            : 'bg-blue-500/20 text-blue-300'
        }`}>
          {asset.environment}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`text-lg font-bold ${criticalityColor}`}>
          {'★'.repeat(asset.criticality)}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`px-2 py-1 text-xs rounded ${
          asset.is_internet_facing || asset.exposure === 'internet-facing'
            ? 'bg-orange-500/20 text-orange-300'
            : 'bg-gray-600 text-gray-300'
        }`}>
          {asset.exposure}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-300">
        {asset.patch_group || '-'}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1 items-center relative">
          {asset.tags && asset.tags.length > 0 ? (
            asset.tags.map(tag => (
              <span
                key={tag}
                className={`px-2 py-0.5 text-xs rounded border ${getTagColor(tag)} flex items-center gap-1`}
              >
                {tag}
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    onRemoveTag(tag);
                  }}
                  aria-label={`Remove tag ${tag}`}
                  className="hover:text-white"
                >
                  ×
                </button>
              </span>
            ))
          ) : (
            <span className="text-gray-500 text-xs">-</span>
          )}
          <button
            onClick={(e) => {
              e.preventDefault();
              setShowTagPopover(!showTagPopover);
            }}
            aria-label="Add tag"
            className="w-5 h-5 flex items-center justify-center rounded bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white text-xs transition-colors"
          >
            +
          </button>
          
          {/* Inline tag add popover */}
          {showTagPopover && (
            <>
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setShowTagPopover(false)}
              />
              <div className="absolute left-0 top-full mt-1 z-50 bg-gray-800 border border-gray-600 rounded-lg shadow-xl w-64">
                <div className="p-2">
                  <input
                    type="text"
                    value={tagSearchInput}
                    onChange={(e) => setTagSearchInput(e.target.value)}
                    placeholder="Search or create tag..."
                    className="w-full px-3 py-1.5 bg-gray-900 text-gray-300 text-sm rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {filteredTags.length > 0 ? (
                    filteredTags.slice(0, 8).map(tag => (
                      <button
                        key={tag}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAddTag(tag);
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                      >
                        <span className={`px-2 py-0.5 rounded border text-xs ${getTagColor(tag)}`}>
                          {tag}
                        </span>
                      </button>
                    ))
                  ) : tagSearchInput.trim() ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCreateNewTag();
                      }}
                      className="w-full px-3 py-2 text-left text-sm text-blue-400 hover:bg-gray-700 transition-colors"
                    >
                      + Create &quot;{tagSearchInput}&quot;
                    </button>
                  ) : (
                    <div className="px-3 py-2 text-sm text-gray-500">
                      No tags found
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {asset.vulnerability_count > 0 ? (
          <span className={`font-medium ${
            asset.vulnerability_count > 10 ? 'text-red-400' : 
            asset.vulnerability_count > 5 ? 'text-orange-400' : 'text-yellow-400'
          }`}>
            {asset.vulnerability_count}
          </span>
        ) : (
          <span className="text-gray-500">0</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="w-20">
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${riskColor}`}
              style={{ width: `${riskBarWidth}%` }}
            />
          </div>
          <div className="text-xs text-gray-400 mt-1">{asset.risk_score.toFixed(0)}</div>
        </div>
      </td>
      <td className="px-4 py-3 text-sm">
        <div className="text-gray-400">{lastScanned}</div>
        {isStale && (
          <div className="text-xs text-yellow-400 mt-0.5">
            ⚠️ {daysSinceScan != null ? `Not scanned in ${daysSinceScan}d` : 'Never scanned'}
          </div>
        )}
      </td>
    </tr>
  );
}

function BulkTagModal({
  assetIds,
  onClose,
  onComplete,
  availableTags,
}: {
  assetIds: string[];
  onClose: () => void;
  onComplete: () => void;
  availableTags: string[];
}) {
  const [tagsToAdd, setTagsToAdd] = useState<string[]>([]);
  const [tagsToRemove, setTagsToRemove] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      await assetsApi.bulkTag(assetIds, tagsToAdd, tagsToRemove);
      onComplete();
    } catch (error) {
      console.error("Failed to bulk tag assets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleTagsChange = (tags: string[]) => {
    setTagsToAdd(tags);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full">
        <h2 className="text-xl font-bold text-white mb-4">
          Bulk Tag {assetIds.length} Asset{assetIds.length !== 1 ? 's' : ''}
        </h2>

        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">Add Tags</label>
          <TagAutocomplete
            value={tagsToAdd}
            onChange={handleTagsChange}
            placeholder="Search and add tags..."
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm text-gray-400 mb-2">Remove Tags</label>
          <select
            className="w-full px-3 py-2 bg-gray-900 text-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            onChange={(e) => {
              const tag = e.target.value;
              if (tag && !tagsToRemove.includes(tag)) {
                setTagsToRemove([...tagsToRemove, tag]);
              }
              e.target.value = "";
            }}
          >
            <option value="">Select tag to remove...</option>
            {availableTags.map(tag => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
          <div className="flex flex-wrap gap-2 mt-2">
            {tagsToRemove.map(tag => (
              <span
                key={tag}
                className="px-2 py-1 text-sm rounded bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1"
              >
                {tag}
                <button
                  onClick={() => setTagsToRemove(tagsToRemove.filter(t => t !== tag))}
                  className="hover:text-white"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={loading || (tagsToAdd.length === 0 && tagsToRemove.length === 0)}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Applying..." : "Apply Changes"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
