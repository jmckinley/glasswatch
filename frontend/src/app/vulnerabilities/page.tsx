"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { vulnerabilitiesApi } from "@/lib/api";

interface Vulnerability {
  id: string;
  identifier: string;
  source: string;
  severity: string;
  cvss_score: number;
  epss_score: number;
  kev_listed: boolean;
  published_at: string;
  description: string;
  affected_assets_count: number;
  patch_available: boolean;
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
  with_patches: number;
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
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
  const [stats, setStats] = useState<VulnStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    severity: "",
    kev_listed: false,
    search: "",
  });
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 20,
    total: 0,
  });

  useEffect(() => {
    fetchVulnerabilities();
    fetchStats();
  }, [filters, pagination.skip]);

  const fetchVulnerabilities = async () => {
    try {
      setLoading(true);
      const params: any = {
        skip: pagination.skip,
        limit: pagination.limit,
      };
      if (filters.severity) params.severity = filters.severity;
      if (filters.kev_listed) params.kev_listed = true;
      if (filters.search) params.search = filters.search;

      const data = await vulnerabilitiesApi.list(params);
      setVulnerabilities(data.items || []);
      setPagination(prev => ({ ...prev, total: data.total || 0 }));
    } catch (error) {
      console.error("Failed to fetch vulnerabilities:", error);
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-primary">
                Glasswatch
              </Link>
              <span className="ml-3 text-sm text-neutral-400">
                Patch Decision Platform
              </span>
            </div>
            <nav className="flex space-x-6">
              <Link href="/" className="text-neutral-400 hover:text-foreground">
                Dashboard
              </Link>
              <Link href="/vulnerabilities" className="text-foreground hover:text-primary">
                Vulnerabilities
              </Link>
              <Link href="/goals" className="text-neutral-400 hover:text-foreground">
                Goals
              </Link>
              <Link href="/schedule" className="text-neutral-400 hover:text-foreground">
                Schedule
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="card p-4">
              <div className="text-2xl font-bold">{stats.total.toLocaleString()}</div>
              <div className="text-sm text-neutral-400">Total Vulnerabilities</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold status-critical">
                {stats.by_severity.CRITICAL}
              </div>
              <div className="text-sm text-neutral-400">Critical</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold status-high">{stats.by_severity.HIGH}</div>
              <div className="text-sm text-neutral-400">High</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold text-destructive">{stats.kev_listed}</div>
              <div className="text-sm text-neutral-400">In KEV Catalog</div>
            </div>
            <div className="card p-4">
              <div className="text-2xl font-bold text-success">{stats.with_patches}</div>
              <div className="text-sm text-neutral-400">Patches Available</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="card p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm text-neutral-400 mb-1">Search</label>
              <input
                type="text"
                placeholder="CVE, keyword, or description..."
                className="px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm text-neutral-400 mb-1">Severity</label>
              <select
                className="px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                value={filters.severity}
                onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.kev_listed}
                  onChange={(e) => setFilters({ ...filters, kev_listed: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">KEV Listed Only</span>
              </label>
            </div>
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
                  CVSS
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                  EPSS
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                  Affected Assets
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                  Published
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-neutral-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-neutral-400">
                    Loading vulnerabilities...
                  </td>
                </tr>
              ) : vulnerabilities.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-neutral-400">
                    No vulnerabilities found
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
      </main>
    </div>
  );
}

function VulnerabilityRow({ vulnerability }: { vulnerability: Vulnerability }) {
  const vuln = vulnerability;
  const publishedDate = new Date(vuln.published_at).toLocaleDateString();

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
            <span className="ml-2 text-xs px-2 py-0.5 bg-destructive/20 text-destructive rounded">
              KEV
            </span>
          )}
        </div>
        <div className="text-sm text-neutral-400 mt-1 line-clamp-1">{vuln.description}</div>
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
        <span className={vuln.affected_assets_count > 0 ? "font-medium" : "text-neutral-400"}>
          {vuln.affected_assets_count}
        </span>
      </td>
      <td className="px-6 py-4 text-sm text-neutral-400">{publishedDate}</td>
      <td className="px-6 py-4">
        <div className="flex gap-2">
          <Link
            href={`/vulnerabilities/${vuln.id}`}
            className="text-sm text-primary hover:underline"
          >
            Details
          </Link>
          {vuln.patch_available && (
            <span className="text-sm text-success">Patch Available</span>
          )}
        </div>
      </td>
    </tr>
  );
}