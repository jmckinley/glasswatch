"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { assetsApi } from "@/lib/api";

// ─── Interfaces ─────────────────────────────────────────────────────────────

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
  owner_email: string | null;
  risk_score: number;
  is_internet_facing: boolean;
  last_scanned_at: string | null;
  last_patched_at: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
  patch_group: string | null;
  os_family: string | null;
  os_version: string | null;
  fqdn: string | null;
  business_unit: string | null;
  ip_addresses: string[];
  cloud_provider: string | null;
  cloud_account_id: string | null;
  cloud_region: string | null;
  cloud_instance_type: string | null;
  cloud_tags: Record<string, string>;
  installed_packages: Array<{ name: string; version: string }>;
  running_services: string[];
  open_ports: number[];
  maintenance_window: string | null;
  compliance_frameworks: string[];
  compensating_controls: string[];
  cmdb_id: string | null;
  monitoring_id: string | null;
  uptime_days: number | null;
}

interface VulnDetail {
  id: string;
  vulnerability_id: string;
  identifier: string;
  title: string;
  severity: string;
  cvss_score: number | null;
  epss_score: number | null;
  kev_listed: boolean;
  exploit_available: boolean;
  patch_available: boolean;
  risk_score: number;
  status: string;
  recommended_action: string;
  days_open: number | null;
  discovered_at: string | null;
  bundle: { bundle_id: string; bundle_name: string; bundle_status: string } | null;
}

interface RiskBreakdown {
  risk_score: number;
  kev_count: number;
  critical_count: number;
  high_count: number;
  exploit_count: number;
  total_active_vulns: number;
  internet_exposed: boolean;
  uptime_days: number | null;
  top_risk_drivers: string[];
}

interface PatchHistoryItem {
  id: string;
  date: string;
  cve_identifier: string;
  vulnerability_title: string;
  severity: string;
  status: string;
  bundle_id: string;
  bundle_name: string;
  patch_identifier: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  completed_at: string | null;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-500/20 text-red-300 border border-red-500/30",
  HIGH: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
  MEDIUM: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
  LOW: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
};

const CRITICALITY_COLOR = (c: number) => {
  if (c >= 5) return "text-red-400";
  if (c >= 4) return "text-orange-400";
  if (c >= 3) return "text-yellow-400";
  return "text-green-400";
};

const CRITICALITY_LABEL = (c: number) => {
  if (c >= 5) return "Critical";
  if (c >= 4) return "High";
  if (c >= 3) return "Medium";
  return "Low";
};

const CRITICALITY_BG = (c: number) => {
  if (c >= 5) return "bg-red-500/20 text-red-300 border-red-500/30";
  if (c >= 4) return "bg-orange-500/20 text-orange-300 border-orange-500/30";
  if (c >= 3) return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
  return "bg-green-500/20 text-green-300 border-green-500/30";
};

const RISK_COLOR = (score: number) => {
  if (score >= 80) return "text-red-400";
  if (score >= 60) return "text-orange-400";
  if (score >= 40) return "text-yellow-400";
  return "text-green-400";
};

const PATCH_STATUS_BADGE: Record<string, string> = {
  success: "bg-green-500/20 text-green-300",
  failed: "bg-red-500/20 text-red-300",
  rolled_back: "bg-purple-500/20 text-purple-300",
  in_progress: "bg-blue-500/20 text-blue-300",
  skipped: "bg-gray-500/20 text-gray-400",
};

const tagColors = [
  "bg-blue-500/20 text-blue-300 border-blue-500/30",
  "bg-green-500/20 text-green-300 border-green-500/30",
  "bg-purple-500/20 text-purple-300 border-purple-500/30",
  "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  "bg-pink-500/20 text-pink-300 border-pink-500/30",
  "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
];

function tagColor(tag: string) {
  let h = 0;
  for (let i = 0; i < tag.length; i++) h = tag.charCodeAt(i) + ((h << 5) - h);
  return tagColors[Math.abs(h) % tagColors.length];
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AssetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const assetId = params?.id as string;

  const [asset, setAsset] = useState<Asset | null>(null);
  const [vulns, setVulns] = useState<VulnDetail[]>([]);
  const [riskBreakdown, setRiskBreakdown] = useState<RiskBreakdown | null>(null);
  const [patchHistory, setPatchHistory] = useState<PatchHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [patchingBundle, setPatchingBundle] = useState(false);
  const [bundleResult, setBundleResult] = useState<{ bundle_id: string; bundle_name: string; vuln_count: number } | null>(null);

  const [vulnFilter, setVulnFilter] = useState("");
  const [newTag, setNewTag] = useState("");
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"vulns" | "history" | "metadata">("vulns");

  const fetchAll = useCallback(async () => {
    if (!assetId) return;
    setLoading(true);
    try {
      const [assetData, vulnData, riskData, historyData, tagsData] = await Promise.allSettled([
        assetsApi.get(assetId),
        assetsApi.getVulnerabilities(assetId, { status: "ACTIVE" }),
        assetsApi.getRiskBreakdown(assetId),
        assetsApi.getPatchHistory(assetId),
        assetsApi.tags(),
      ]);

      if (assetData.status === "fulfilled") setAsset(assetData.value?.asset || assetData.value);
      if (vulnData.status === "fulfilled") setVulns(vulnData.value?.vulnerabilities || []);
      if (riskData.status === "fulfilled") setRiskBreakdown(riskData.value);
      if (historyData.status === "fulfilled") setPatchHistory(historyData.value?.history || []);
      if (tagsData.status === "fulfilled") setAvailableTags((tagsData.value?.tags || []).map((t: any) => t.name));
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleAddTag = async () => {
    if (!asset || !newTag.trim()) return;
    await assetsApi.updateTags(asset.id, [newTag.trim()], []);
    setNewTag("");
    fetchAll();
  };

  const handleRemoveTag = async (tag: string) => {
    if (!asset) return;
    await assetsApi.updateTags(asset.id, [], [tag]);
    fetchAll();
  };

  const handleCreatePatchBundle = async () => {
    if (!asset) return;
    setPatchingBundle(true);
    try {
      const res = await assetsApi.createPatchBundle(asset.id);
      setBundleResult(res);
    } catch (err: any) {
      alert(err?.message || "Failed to create bundle");
    } finally {
      setPatchingBundle(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400 animate-pulse">Loading asset…</div>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-gray-400">Asset not found</div>
        <Link href="/assets" className="text-blue-400 hover:underline">← Back to Assets</Link>
      </div>
    );
  }

  const filteredVulns = vulns.filter(v =>
    !vulnFilter ||
    v.identifier.toLowerCase().includes(vulnFilter.toLowerCase()) ||
    (v.severity || "").toLowerCase() === vulnFilter.toLowerCase()
  );

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link href="/assets" className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1">
        ← Back to Assets
      </Link>

      {/* ── Header ── */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          {/* Left: name + badges */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <h1 className="text-2xl font-bold text-white truncate">{asset.name}</h1>
              {/* Type badge */}
              <span className="px-2 py-0.5 text-xs rounded bg-gray-700 text-gray-300 border border-gray-600">
                {asset.type}
              </span>
              {/* Environment badge */}
              <span className={`px-2 py-0.5 text-xs rounded border ${
                asset.environment === "production"
                  ? "bg-red-500/20 text-red-300 border-red-500/30"
                  : asset.environment === "staging"
                  ? "bg-yellow-500/20 text-yellow-300 border-yellow-500/30"
                  : "bg-blue-500/20 text-blue-300 border-blue-500/30"
              }`}>
                {asset.environment}
              </span>
              {/* Criticality badge */}
              <span className={`px-2 py-0.5 text-xs rounded border ${CRITICALITY_BG(asset.criticality)}`}>
                {CRITICALITY_LABEL(asset.criticality)} Criticality ({asset.criticality}/5)
              </span>
              {/* Internet-exposed badge */}
              {asset.is_internet_facing && (
                <span className="px-2 py-0.5 text-xs rounded bg-orange-500/20 text-orange-300 border border-orange-500/30">
                  🌐 Internet-Exposed
                </span>
              )}
            </div>
            <div className="text-sm text-gray-400">{asset.identifier}</div>

            {/* Key facts row */}
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <span className="text-gray-500">IP(s): </span>
                <span className="text-gray-300">{asset.ip_addresses?.join(", ") || "—"}</span>
              </div>
              <div>
                <span className="text-gray-500">FQDN: </span>
                <span className="text-gray-300">{asset.fqdn || "—"}</span>
              </div>
              <div>
                <span className="text-gray-500">Last Scanned: </span>
                <span className="text-gray-300">
                  {asset.last_scanned_at ? new Date(asset.last_scanned_at).toLocaleDateString() : "Never"}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Last Patched: </span>
                <span className="text-gray-300">
                  {asset.last_patched_at ? new Date(asset.last_patched_at).toLocaleDateString() : "Unknown"}
                </span>
              </div>
            </div>
          </div>

          {/* Right: Risk Score */}
          <div className="flex-shrink-0 text-center bg-gray-900 rounded-lg p-4 min-w-[100px]">
            <div className={`text-4xl font-bold ${RISK_COLOR(asset.risk_score)}`}>
              {asset.risk_score.toFixed(0)}
            </div>
            <div className="text-xs text-gray-400 mt-1">Risk Score</div>
            <div className="mt-2 h-1.5 bg-gray-700 rounded-full overflow-hidden w-20 mx-auto">
              <div
                className={`h-full rounded-full ${
                  asset.risk_score >= 80 ? "bg-red-500" : asset.risk_score >= 60 ? "bg-orange-500" : "bg-yellow-500"
                }`}
                style={{ width: `${Math.min(100, asset.risk_score)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Risk Breakdown Panel ── */}
      {riskBreakdown && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-4">Risk Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-5">
            <RiskStat label="KEV Vulns" value={riskBreakdown.kev_count} color="text-red-400" danger={riskBreakdown.kev_count > 0} />
            <RiskStat label="Critical" value={riskBreakdown.critical_count} color="text-red-300" danger={riskBreakdown.critical_count > 0} />
            <RiskStat label="High" value={riskBreakdown.high_count} color="text-orange-400" danger={riskBreakdown.high_count > 0} />
            <RiskStat label="Exploitable" value={riskBreakdown.exploit_count} color="text-orange-300" danger={riskBreakdown.exploit_count > 0} />
            <RiskStat label="Total Active" value={riskBreakdown.total_active_vulns} color="text-yellow-400" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5 text-sm">
            <div className="bg-gray-900 rounded-lg p-3">
              <span className="text-gray-400">Internet-Exposed: </span>
              <span className={riskBreakdown.internet_exposed ? "text-orange-400 font-semibold" : "text-green-400"}>
                {riskBreakdown.internet_exposed ? "Yes ⚠️" : "No ✓"}
              </span>
            </div>
            <div className="bg-gray-900 rounded-lg p-3">
              <span className="text-gray-400">Uptime: </span>
              <span className={riskBreakdown.uptime_days && riskBreakdown.uptime_days > 365 ? "text-orange-400" : "text-gray-300"}>
                {riskBreakdown.uptime_days !== null ? `${riskBreakdown.uptime_days} days` : "Unknown"}
              </span>
            </div>
            <div className="bg-gray-900 rounded-lg p-3">
              <span className="text-gray-400">Environment: </span>
              <span className="text-gray-300">{asset.environment || "—"}</span>
            </div>
          </div>
          {riskBreakdown.top_risk_drivers.length > 0 && (
            <div>
              <div className="text-sm font-medium text-gray-400 mb-2">Top Risk Drivers:</div>
              <ul className="space-y-1.5">
                {riskBreakdown.top_risk_drivers.map((d, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <span className="text-red-400 mt-0.5 flex-shrink-0">
                      {i === 0 ? "🔴" : i === 1 ? "🟠" : "🟡"}
                    </span>
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="border-b border-gray-700">
        <div className="flex gap-0">
          {(["vulns", "history", "metadata"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-400 hover:text-gray-300"
              }`}
            >
              {tab === "vulns" && `Vulnerabilities (${vulns.length})`}
              {tab === "history" && `Patch History (${patchHistory.length})`}
              {tab === "metadata" && "Asset Metadata"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Vulnerabilities Tab ── */}
      {activeTab === "vulns" && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
            <div className="flex gap-2 flex-1">
              <input
                type="text"
                placeholder="Filter by CVE or severity…"
                value={vulnFilter}
                onChange={e => setVulnFilter(e.target.value)}
                className="px-3 py-1.5 bg-gray-900 text-gray-300 text-sm rounded-lg border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 w-56"
              />
              <select
                value={vulnFilter}
                onChange={e => setVulnFilter(e.target.value)}
                className="px-3 py-1.5 bg-gray-900 text-gray-300 text-sm rounded-lg border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
            <div className="flex gap-2 items-center">
              {bundleResult ? (
                <Link
                  href={`/bundles/${bundleResult.bundle_id}`}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                >
                  ✓ Bundle created ({bundleResult.vuln_count} vulns) — View →
                </Link>
              ) : (
                <button
                  onClick={handleCreatePatchBundle}
                  disabled={patchingBundle || vulns.length === 0}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
                >
                  {patchingBundle ? "Creating…" : "🩹 Patch This Asset"}
                </button>
              )}
            </div>
          </div>

          {filteredVulns.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No vulnerabilities found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-900 text-gray-400">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium">CVE ID</th>
                    <th className="text-left px-4 py-3 font-medium">Severity</th>
                    <th className="text-left px-4 py-3 font-medium">CVSS</th>
                    <th className="text-left px-4 py-3 font-medium">EPSS %</th>
                    <th className="text-left px-4 py-3 font-medium">KEV</th>
                    <th className="text-left px-4 py-3 font-medium">Patch</th>
                    <th className="text-left px-4 py-3 font-medium">Status</th>
                    <th className="text-left px-4 py-3 font-medium">Days Open</th>
                    <th className="text-left px-4 py-3 font-medium">Bundle</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVulns.map(v => (
                    <tr key={v.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                      <td className="px-4 py-3">
                        <Link href={`/vulnerabilities/${v.vulnerability_id}`} className="text-blue-400 hover:text-blue-300 font-mono text-xs">
                          {v.identifier}
                        </Link>
                        {v.title && (
                          <div className="text-gray-500 text-xs mt-0.5 max-w-xs truncate">{v.title}</div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded ${SEVERITY_BADGE[v.severity] || SEVERITY_BADGE.LOW}`}>
                          {v.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-gray-300 text-xs">
                        {v.cvss_score != null ? v.cvss_score.toFixed(1) : "—"}
                      </td>
                      <td className="px-4 py-3 font-mono text-gray-300 text-xs">
                        {v.epss_score != null ? (v.epss_score * 100).toFixed(2) + "%" : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {v.kev_listed ? (
                          <span className="px-1.5 py-0.5 text-xs rounded bg-red-600/30 text-red-300 font-semibold">KEV</span>
                        ) : (
                          <span className="text-gray-600 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {v.patch_available ? (
                          <span className="text-xs text-green-400">✓ Available</span>
                        ) : (
                          <span className="text-xs text-gray-500">None</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          v.status === "ACTIVE" ? "bg-red-500/10 text-red-300" :
                          v.status === "PATCHED" ? "bg-green-500/10 text-green-300" :
                          "bg-gray-600/30 text-gray-400"
                        }`}>
                          {v.status?.toLowerCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {v.days_open != null ? (
                          <span className={v.days_open > 90 ? "text-red-400" : v.days_open > 30 ? "text-orange-400" : "text-gray-400"}>
                            {v.days_open}d
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {v.bundle ? (
                          <Link href={`/bundles/${v.bundle.bundle_id}`} className="text-blue-400 hover:text-blue-300 truncate max-w-[120px] block">
                            {v.bundle.bundle_name}
                          </Link>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Patch History Tab ── */}
      {activeTab === "history" && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-sm font-medium text-gray-300">Patch History Timeline</h2>
          </div>
          {patchHistory.length === 0 ? (
            <div className="text-center py-12 text-gray-500">No patch history found</div>
          ) : (
            <div className="p-4 space-y-3">
              {patchHistory.map(h => (
                <div key={h.id} className="flex gap-4 items-start">
                  {/* Timeline dot */}
                  <div className="flex-shrink-0 mt-1.5">
                    <div className={`w-2.5 h-2.5 rounded-full ${
                      h.status === "success" ? "bg-green-500" :
                      h.status === "failed" ? "bg-red-500" :
                      h.status === "rolled_back" ? "bg-purple-500" :
                      "bg-gray-500"
                    }`} />
                  </div>
                  <div className="flex-1 bg-gray-900 rounded-lg p-3 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-blue-400">{h.cve_identifier}</span>
                      <span className={`px-1.5 py-0.5 text-xs rounded ${SEVERITY_BADGE[h.severity] || SEVERITY_BADGE.LOW}`}>
                        {h.severity}
                      </span>
                      <span className={`px-2 py-0.5 text-xs rounded ${PATCH_STATUS_BADGE[h.status] || "bg-gray-600 text-gray-300"}`}>
                        {h.status.replace("_", " ")}
                      </span>
                      {h.patch_identifier && (
                        <span className="text-xs text-gray-500 font-mono">{h.patch_identifier}</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 truncate">{h.vulnerability_title}</div>
                    <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-gray-500">
                      <span>{new Date(h.date).toLocaleString()}</span>
                      <Link href={`/bundles/${h.bundle_id}`} className="text-blue-400 hover:text-blue-300">
                        {h.bundle_name}
                      </Link>
                      {h.duration_seconds && <span>{h.duration_seconds}s</span>}
                    </div>
                    {h.error_message && (
                      <div className="mt-1.5 text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">
                        {h.error_message}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Metadata Tab ── */}
      {activeTab === "metadata" && (
        <div className="space-y-4">
          {/* Ownership */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Ownership</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <InfoField label="Owner Team" value={asset.owner_team} />
              <InfoField label="Owner Email" value={asset.owner_email} />
              <InfoField label="Business Unit" value={asset.business_unit} />
              <InfoField label="Location" value={asset.location} />
              <InfoField label="Patch Group" value={asset.patch_group} />
              <InfoField label="Maintenance Window" value={asset.maintenance_window} />
            </div>
          </div>

          {/* OS & Platform */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">OS & Platform</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <InfoField label="OS Family" value={asset.os_family} />
              <InfoField label="OS Version" value={asset.os_version} />
              <InfoField label="Platform" value={asset.platform} />
              <InfoField label="FQDN" value={asset.fqdn} />
              <InfoField label="IP Addresses" value={asset.ip_addresses?.join(", ")} />
              <InfoField label="Uptime" value={asset.uptime_days != null ? `${asset.uptime_days} days` : undefined} />
            </div>
          </div>

          {/* Cloud */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Cloud</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-3">
              <InfoField label="Cloud Provider" value={asset.cloud_provider || asset.platform} />
              <InfoField label="Account ID" value={asset.cloud_account_id} />
              <InfoField label="Region" value={asset.cloud_region} />
              <InfoField label="Instance Type" value={asset.cloud_instance_type} />
            </div>
            {asset.cloud_tags && Object.keys(asset.cloud_tags).length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-1.5">Cloud Tags</div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(asset.cloud_tags).map(([k, v]) => (
                    <span key={k} className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded">
                      {k}: {v}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Compliance */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Compliance & Controls</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
              <div>
                <div className="text-xs text-gray-500 mb-1.5">Compliance Frameworks</div>
                <div className="flex flex-wrap gap-1.5">
                  {asset.compliance_frameworks?.length ? (
                    asset.compliance_frameworks.map(f => (
                      <span key={f} className="px-2 py-0.5 text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded">
                        {f}
                      </span>
                    ))
                  ) : <span className="text-gray-600 text-sm">—</span>}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1.5">Compensating Controls</div>
                <div className="flex flex-wrap gap-1.5">
                  {asset.compensating_controls?.length ? (
                    asset.compensating_controls.map(c => (
                      <span key={c} className="px-2 py-0.5 text-xs bg-green-500/20 text-green-300 border border-green-500/30 rounded">
                        {c}
                      </span>
                    ))
                  ) : <span className="text-gray-600 text-sm">—</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Tags */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Tags</h3>
            <div className="flex flex-wrap gap-2 mb-3">
              {asset.tags?.map(tag => (
                <span key={tag} className={`px-2 py-0.5 text-xs rounded border ${tagColor(tag)} flex items-center gap-1`}>
                  {tag}
                  <button onClick={() => handleRemoveTag(tag)} className="hover:text-white ml-1">×</button>
                </span>
              ))}
              {!asset.tags?.length && <span className="text-gray-600 text-sm">No tags</span>}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newTag}
                onChange={e => setNewTag(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleAddTag()}
                placeholder="Add tag…"
                className="px-3 py-1.5 bg-gray-900 text-gray-300 text-sm rounded-lg border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 w-48"
                list="tag-datalist"
              />
              <datalist id="tag-datalist">
                {availableTags.map(t => <option key={t} value={t} />)}
              </datalist>
              <button
                onClick={handleAddTag}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg"
              >
                Add
              </button>
            </div>
          </div>

          {/* Integrations */}
          {(asset.cmdb_id || asset.monitoring_id) && (
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Integrations</h3>
              <div className="grid grid-cols-2 gap-4">
                <InfoField label="CMDB ID" value={asset.cmdb_id} />
                <InfoField label="Monitoring ID" value={asset.monitoring_id} />
              </div>
            </div>
          )}

          {/* Software */}
          {(asset.installed_packages?.length > 0 || asset.running_services?.length > 0 || asset.open_ports?.length > 0) && (
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Software Inventory</h3>
              {asset.running_services?.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-gray-500 mb-1.5">Running Services</div>
                  <div className="flex flex-wrap gap-1.5">
                    {asset.running_services.map(s => (
                      <span key={s} className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded">{s}</span>
                    ))}
                  </div>
                </div>
              )}
              {asset.open_ports?.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-gray-500 mb-1.5">Open Ports</div>
                  <div className="flex flex-wrap gap-1.5">
                    {asset.open_ports.map(p => (
                      <span key={p} className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded font-mono">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {asset.installed_packages?.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-1.5">Installed Packages ({asset.installed_packages.length})</div>
                  <div className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead><tr className="text-gray-500 border-b border-gray-700">
                        <th className="text-left py-1">Package</th>
                        <th className="text-left py-1">Version</th>
                      </tr></thead>
                      <tbody>
                        {asset.installed_packages.map((pkg, i) => (
                          <tr key={i} className="border-b border-gray-800">
                            <td className="py-1 text-gray-300">{pkg.name}</td>
                            <td className="py-1 text-gray-500 font-mono">{pkg.version}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Helper Components ────────────────────────────────────────────────────────

function RiskStat({
  label,
  value,
  color,
  danger,
}: {
  label: string;
  value: number;
  color: string;
  danger?: boolean;
}) {
  return (
    <div className={`bg-gray-900 rounded-lg p-3 text-center ${danger && value > 0 ? "ring-1 ring-red-500/30" : ""}`}>
      <div className={`text-2xl font-bold ${danger && value > 0 ? color : "text-white"}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      <div className="text-sm text-gray-300">{value || "—"}</div>
    </div>
  );
}
