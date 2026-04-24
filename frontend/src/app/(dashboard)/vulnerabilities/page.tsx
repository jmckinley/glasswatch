"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { vulnerabilitiesApi } from "@/lib/api";
import { Tooltip } from "@/components/ui/Tooltip";

interface Vulnerability {
  id: string;
  identifier: string;
  source: string;
  title: string;
  severity: string;
  cvss_score: number;
  epss_score: number;
  kev_listed: boolean;
  published_at: string;
  exploit_available: boolean;
  patch_available: boolean;
  is_critical: boolean;
}

interface VulnStats {
  total: number;
  by_severity: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  kev_listed: number;
  patches_available: number;
  exploits_available: number;
  recent_7d: number;
  total_risk_score: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "text-destructive",
  HIGH: "text-warning",
  MEDIUM: "text-secondary",
  LOW: "text-success",
};

const SEVERITY_BG: Record<string, string> = {
  CRITICAL: "bg-destructive/10",
  HIGH: "bg-warning/10",
  MEDIUM: "bg-secondary/10",
  LOW: "bg-success/10",
};

export default function VulnerabilitiesPage() {
  const searchParams = useSearchParams();
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [stats, setStats] = useState<VulnStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pre-populate filters from URL query params (?filter=kev, ?severity=CRITICAL)
  const [filters, setFilters] = useState(() => ({
    severity: searchParams.get("severity") || "",
    kev_listed: searchParams.get("filter") === "kev",
    patch_available: searchParams.get("filter") === "patch",
    search: searchParams.get("search") || "",
  }));
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 20,
    total: 0,
  });

  useEffect(() => { document.title = 'Vulnerabilities | Glasswatch'; }, []);

  useEffect(() => {
    fetchVulnerabilities();
    fetchStats();
  }, [filters, pagination.skip]);

  const fetchVulnerabilities = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {
        skip: pagination.skip,
        limit: pagination.limit,
      };
      if (filters.severity) params.severity = filters.severity;
      if (filters.kev_listed) params.kev_listed = true;
      if (filters.patch_available) params.patch_available = true;
      if (filters.search) params.search = filters.search;

      const data = await vulnerabilitiesApi.list(params);
      setVulnerabilities(data.vulnerabilities || data.items || []);
      setPagination(prev => ({ ...prev, total: data.total || 0 }));
    } catch (err: any) {
      console.error("Failed to fetch vulnerabilities:", err);
      setError(err?.message || "Failed to load vulnerabilities. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await vulnerabilitiesApi.stats();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    }
  };

  const totalPages = Math.ceil(pagination.total / pagination.limit);
  const currentPage = Math.floor(pagination.skip / pagination.limit) + 1;

  const activeFilterCount = [filters.severity, filters.kev_listed, filters.patch_available].filter(Boolean).length;

  return (
    <>
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Vulnerabilities</h1>
          {stats && (
            <p className="text-sm text-neutral-400 mt-0.5">
              {stats.total.toLocaleString()} total · {stats.by_severity.CRITICAL} critical · {stats.kev_listed} in KEV
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/import"
            className="px-4 py-2 border border-neutral-600 hover:border-neutral-400 text-neutral-300 hover:text-white rounded-lg text-sm transition-colors"
          >
            Import CSV
          </Link>
          <Link
            href="/bundles"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg text-sm transition-colors"
          >
            Create Bundle
          </Link>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6 text-red-400 flex items-center gap-3">
          <span>⚠</span>
          <span>{error}</span>
          <button
            onClick={() => { setError(null); fetchVulnerabilities(); }}
            className="ml-auto text-xs text-red-300 hover:text-white border border-red-700 px-2 py-1 rounded"
          >Retry</button>
        </div>
      )}

      {/* Stats Cards — skeleton while loading, real data once ready */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {loading && !stats ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="h-7 bg-neutral-700 rounded w-16 mb-2" />
              <div className="h-4 bg-neutral-800 rounded w-24" />
            </div>
          ))
        ) : stats ? (
          <>
            <div className="card p-4">
              <div className="text-2xl font-bold">{stats.total.toLocaleString()}</div>
              <div className="text-sm text-neutral-400">Total Vulnerabilities</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold status-critical">{stats.by_severity.CRITICAL}</div>
              <div className="text-sm text-neutral-400">Critical</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold status-high">{stats.by_severity.HIGH}</div>
              <div className="text-sm text-neutral-400">High</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold text-destructive">{stats.kev_listed}</div>
              <div className="text-sm text-neutral-400">
                <Tooltip content="CISA Known Exploited Vulnerabilities (️KEV) — bugs actively exploited in the wild. CISA BOD 22-01 mandates federal agencies patch these promptly.">
                  <span>In KEV Catalog ⓘ</span>
                </Tooltip>
              </div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold text-success">{stats.patches_available}</div>
              <div className="text-sm text-neutral-400">Patches Available</div>
            </div>
          </>
        ) : null}
      </div>

      {/* Search + Filter Pills */}
      <div className="mb-6 space-y-3">
        {/* Search */}
        <input
          type="text"
          placeholder="Search CVE, keyword, or description..."
          className="w-full max-w-sm px-4 py-2 bg-neutral-800 border border-neutral-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white placeholder-neutral-500"
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
        />

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-2 items-center">
          {[
            { label: "All", active: !filters.severity && !filters.kev_listed && !filters.patch_available, onClick: () => setFilters({ severity: "", kev_listed: false, patch_available: false, search: filters.search }) },
            { label: `Critical${stats ? ` (${stats.by_severity.CRITICAL})` : ""}`, active: filters.severity === "CRITICAL", onClick: () => setFilters({ ...filters, severity: "CRITICAL", kev_listed: false, patch_available: false }) },
            { label: `High${stats ? ` (${stats.by_severity.HIGH})` : ""}`, active: filters.severity === "HIGH", onClick: () => setFilters({ ...filters, severity: "HIGH", kev_listed: false, patch_available: false }) },
            { label: `Medium${stats ? ` (${stats.by_severity.MEDIUM})` : ""}`, active: filters.severity === "MEDIUM", onClick: () => setFilters({ ...filters, severity: "MEDIUM", kev_listed: false, patch_available: false }) },
            { label: `Low${stats ? ` (${stats.by_severity.LOW})` : ""}`, active: filters.severity === "LOW", onClick: () => setFilters({ ...filters, severity: "LOW", kev_listed: false, patch_available: false }) },
            { label: `KEV Only${stats ? ` (${stats.kev_listed})` : ""}`, active: filters.kev_listed, onClick: () => setFilters({ ...filters, severity: "", kev_listed: true, patch_available: false }) },
            { label: `Patch Available${stats ? ` (${stats.patches_available})` : ""}`, active: filters.patch_available, onClick: () => setFilters({ ...filters, severity: "", kev_listed: false, patch_available: true }) },
          ].map(({ label, active, onClick }) => (
            <button
              key={label}
              onClick={onClick}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-600 text-white"
                  : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700 hover:text-white border border-neutral-700"
              }`}
            >
              {label}
            </button>
          ))}
          {activeFilterCount > 0 && (
            <button
              onClick={() => setFilters({ severity: "", kev_listed: false, patch_available: false, search: filters.search })}
              className="ml-2 text-xs text-neutral-500 hover:text-white transition-colors"
            >
              Clear filters ×
            </button>
          )}
        </div>
      </div>

      {/* Vulnerabilities Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-neutral-900 border-b border-border">
            <tr>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                Identifier
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                Severity
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                <Tooltip content="Common Vulnerability Scoring System (CVSS) — a 0–10 severity score based on exploitability and impact.">
                  <span>CVSS ⓘ</span>
                </Tooltip>
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                <Tooltip content="Exploit Prediction Scoring System (EPSS) — probability this CVE will be exploited in the wild in the next 30 days.">
                  <span>EPSS ⓘ</span>
                </Tooltip>
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                Status
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                Age
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className="border-b border-border">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-6 py-4">
                      <div className="h-4 bg-neutral-800 rounded animate-pulse" style={{ width: j === 0 ? "80%" : j === 6 ? "40%" : "60%" }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : vulnerabilities.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="text-center py-16">
                    {(filters.severity || filters.kev_listed || filters.patch_available || filters.search) ? (
                      <>
                        <div className="text-5xl mb-4">🔍</div>
                        <h3 className="text-lg font-medium text-white mb-2">No vulnerabilities match this filter</h3>
                        <p className="text-neutral-400 mb-4">Try broadening your search.</p>
                        <button
                          onClick={() => setFilters({ severity: "", kev_listed: false, patch_available: false, search: "" })}
                          className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-sm transition-colors"
                        >
                          Clear Filters
                        </button>
                      </>
                    ) : (
                      <>
                        <div className="text-5xl mb-4">🎉</div>
                        <h3 className="text-lg font-medium text-white mb-2">No vulnerabilities found — your environment looks clean.</h3>
                        <p className="text-neutral-400 mb-4">Connect a scanner or import a CSV to keep your data current.</p>
                        <div className="flex justify-center gap-3">
                          <Link href="/settings/connections" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm transition-colors">
                            Connect Scanner
                          </Link>
                          <Link href="/import" className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-sm transition-colors">
                            Import CSV
                          </Link>
                        </div>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              vulnerabilities.map((vuln) => (
                <VulnerabilityRow key={vuln.id} vulnerability={vuln} />
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
            className="px-3 py-1 bg-neutral-800 rounded hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-neutral-400">
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
            className="px-3 py-1 bg-neutral-800 rounded hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}

function VulnerabilityRow({ vulnerability }: { vulnerability: Vulnerability }) {
  const vuln = vulnerability;
  const ageInDays = Math.floor((Date.now() - new Date(vuln.published_at).getTime()) / (1000 * 60 * 60 * 24));
  const ageLabel = ageInDays >= 365 ? `${Math.floor(ageInDays / 365)}y ${Math.floor((ageInDays % 365) / 30)}m` : `${ageInDays}d`;

  return (
    <tr className="border-b border-border hover:bg-card-hover transition-colors">
      <td className="px-6 py-4">
        <div>
          <Link
            href={`/vulnerabilities/${vuln.id}`}
            className="font-medium hover:text-primary transition-colors"
          >
            {vuln.identifier}
          </Link>
          {vuln.kev_listed && (
            <span
              title="CISA Known Exploited Vulnerability — actively exploited in the wild, patch immediately"
              className="ml-2 text-xs px-2 py-0.5 bg-destructive/20 text-destructive rounded cursor-help"
            >
              KEV
            </span>
          )}
        </div>
        <div className="text-sm text-neutral-400 mt-1 line-clamp-1">{vuln.title}</div>
      </td>
      <td className="px-6 py-4">
        <span className={`px-2 py-1 text-xs rounded ${SEVERITY_BG[vuln.severity]} ${SEVERITY_COLORS[vuln.severity]}`}>
          {vuln.severity}
        </span>
      </td>
      <td className="px-6 py-4">
        <span className="font-mono">{vuln.cvss_score.toFixed(1)}</span>
      </td>
      <td className="px-6 py-4">
        <span className="font-mono">{(vuln.epss_score * 100).toFixed(1)}%</span>
      </td>
      <td className="px-6 py-4">
        <div className="flex gap-1">
          {vuln.exploit_available && (
            <span className="text-xs px-1.5 py-0.5 bg-warning/20 text-warning rounded">Exploit</span>
          )}
          {vuln.patch_available && (
            <span className="text-xs px-1.5 py-0.5 bg-success/20 text-success rounded">Patch</span>
          )}
        </div>
      </td>
      <td className="px-6 py-4 text-sm text-neutral-400">{ageLabel}</td>
      <td className="px-6 py-4">
        <Link
          href={`/vulnerabilities/${vuln.id}`}
          className="text-sm text-primary hover:underline"
        >
          Details
        </Link>
      </td>
    </tr>
  );
}
