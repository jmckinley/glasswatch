"use client";

import { useEffect, useState } from "react";
import { reportingApi } from "@/lib/api";
import { PrintReport } from "@/components/PrintReport";
import { Tooltip } from "@/components/ui/Tooltip";

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    COMPLIANT: "bg-green-900 text-green-300 border border-green-700",
    AT_RISK: "bg-yellow-900 text-yellow-300 border border-yellow-700",
    NON_COMPLIANT: "bg-red-900 text-red-300 border border-red-700",
  };
  const label: Record<string, string> = {
    COMPLIANT: "Compliant",
    AT_RISK: "At Risk",
    NON_COMPLIANT: "Non-Compliant",
  };
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${map[status] ?? "bg-gray-700 text-gray-300"}`}>
      {label[status] ?? status}
    </span>
  );
}

// ─── Progress bar ─────────────────────────────────────────────────────────────
function ProgressBar({ pct, color = "blue" }: { pct: number; color?: string }) {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
  };
  const barColor =
    pct >= 90 ? colorMap.green : pct >= 70 ? colorMap.yellow : colorMap.red;

  return (
    <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
      <div
        className={`h-2 rounded-full transition-all ${barColor}`}
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  );
}

// ─── SLA status pill ──────────────────────────────────────────────────────────
function SlaPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    ON_TRACK: "bg-green-900 text-green-300",
    AT_RISK: "bg-yellow-900 text-yellow-300",
    BREACHED: "bg-red-900 text-red-300",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${map[status] ?? "bg-gray-700 text-gray-400"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

// ─── Severity badge ───────────────────────────────────────────────────────────
function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    CRITICAL: "bg-red-900 text-red-300",
    HIGH: "bg-orange-900 text-orange-300",
    MEDIUM: "bg-yellow-900 text-yellow-300",
    LOW: "bg-blue-900 text-blue-300",
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${map[severity] ?? "bg-gray-700 text-gray-400"}`}>
      {severity}
    </span>
  );
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-700 rounded ${className}`} />;
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function CompliancePage() {
  const [compliance, setCompliance] = useState<any>(null);
  const [mttp, setMttp] = useState<any>(null);
  const [sla, setSla] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPrint, setShowPrint] = useState(false);
  const [execSummary, setExecSummary] = useState<any>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [slaFilter, setSlaFilter] = useState<string>("ALL");
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => { document.title = 'Compliance | Glasswatch'; }, []);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [compData, mttpData, slaData] = await Promise.all([
          reportingApi.getComplianceSummary(),
          reportingApi.getMttp(),
          reportingApi.getSlaTracking({ limit: 200 }),
        ]);
        setCompliance(compData);
        setMttp(mttpData);
        setSla(slaData);
        setUpdatedAt(new Date().toLocaleString());
      } catch (e: any) {
        setError(e?.message || "Failed to load compliance data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleExportPdf = async () => {
    try {
      setExportLoading(true);
      setError(null);
      const data = await reportingApi.getExecutiveSummary();
      setExecSummary(data);
      setShowPrint(true);
    } catch (e: any) {
      setError("Failed to load executive summary: " + (e?.message || "Unknown error"));
    } finally {
      setExportLoading(false);
    }
  };

  const frameworks = compliance?.frameworks || {};
  const bod = frameworks.bod_22_01;
  const soc2 = frameworks.soc2;
  const pci = frameworks.pci_dss;

  const filteredSla = (() => {
    const items = sla?.items || [];
    if (slaFilter === "ALL") return items;
    return items.filter((i: any) => i.sla_status === slaFilter);
  })();

  return (
    <div className="space-y-8">
      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Compliance & Reporting</h1>
          {updatedAt && (
            <p className="text-sm text-gray-400 mt-1">Last updated: {updatedAt}</p>
          )}
        </div>
        <button
          onClick={handleExportPdf}
          disabled={exportLoading || loading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors shadow-lg"
        >
          {exportLoading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Loading…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export Audit Report
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg p-4 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* ── Framework Cards ── */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4">Framework Status</h2>
        {!loading && Object.keys(frameworks).length === 0 && (
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center">
            <p className="text-gray-400 text-sm">Connect a vulnerability scanner to start tracking compliance posture.</p>
          </div>
        )}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* BOD 22-01 */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-2 w-full" />
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">
                      <Tooltip content="CISA Binding Operational Directive 22-01 requires federal agencies to patch all Known Exploited Vulnerabilities (KEV) within specific deadlines. Use as a best-practice benchmark even outside federal scope.">
                        <span>CISA BOD 22-01 ⓘ</span>
                      </Tooltip>
                    </p>
                    <p className="text-sm text-gray-300 mt-0.5">Known Exploited Vulnerabilities</p>
                  </div>
                  <StatusBadge status={bod?.status || "COMPLIANT"} />
                </div>
                {/* Large % metric */}
                {(() => {
                  const pct = bod?.patch_rate_pct ?? 100;
                  const color = pct >= 90 ? "text-emerald-400" : pct >= 70 ? "text-amber-400" : "text-red-400";
                  const arrow = pct >= 90 ? "↑" : pct >= 70 ? "→" : "↓";
                  const arrowColor = pct >= 90 ? "text-emerald-400" : pct >= 70 ? "text-gray-400" : "text-red-400";
                  return (
                    <div className="flex items-end gap-2 mb-1">
                      <span className={`text-5xl font-bold ${color}`}>{pct}%</span>
                      <span className={`text-xl mb-1 ${arrowColor}`}>{arrow}</span>
                    </div>
                  );
                })()}
                <p className="text-xs text-gray-400 mt-1">KEV patch rate · {bod?.kev_patched ?? 0} / {bod?.kev_total ?? 0} patched</p>
                <ProgressBar pct={bod?.patch_rate_pct ?? 100} />
                <p className="text-xs text-gray-400 mt-2">{bod?.patch_rate_pct ?? 100}% patch rate</p>
                {(bod?.unpatched_items?.length ?? 0) > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <p className="text-xs text-gray-400 mb-2">Unpatched KEV items:</p>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {bod.unpatched_items.slice(0, 5).map((item: any) => (
                        <div key={item.cve_id} className="flex items-center justify-between text-xs">
                          <span className="text-gray-300 font-mono">{item.cve_id}</span>
                          <span className={`${item.days_overdue > 0 ? "text-red-400" : "text-yellow-400"}`}>
                            {item.days_overdue > 0 ? `${item.days_overdue}d overdue` : "due soon"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* SOC 2 */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-2 w-full" />
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">SOC 2 Type II</p>
                    <p className="text-sm text-gray-300 mt-0.5">Patch Management Controls</p>
                  </div>
                  <StatusBadge status={soc2?.status || "COMPLIANT"} />
                </div>
                {/* Large % metric */}
                {(() => {
                  const pct = soc2?.critical_patched_within_30d_pct ?? 100;
                  const color = pct >= 90 ? "text-emerald-400" : pct >= 70 ? "text-amber-400" : "text-red-400";
                  const arrow = pct >= 90 ? "↑" : pct >= 70 ? "→" : "↓";
                  const arrowColor = pct >= 90 ? "text-emerald-400" : pct >= 70 ? "text-gray-400" : "text-red-400";
                  return (
                    <div className="flex items-end gap-2 mb-3">
                      <span className={`text-5xl font-bold ${color}`}>{pct}%</span>
                      <span className={`text-xl mb-1 ${arrowColor}`}>{arrow}</span>
                    </div>
                  );
                })()}
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>Critical patched ≤ 30 days</span>
                      <span className="text-white font-medium">{soc2?.critical_patched_within_30d_pct ?? 100}%</span>
                    </div>
                    <ProgressBar pct={soc2?.critical_patched_within_30d_pct ?? 100} />
                    <p className="text-xs text-gray-500 mt-1">{soc2?.critical_total ?? 0} critical vulns tracked</p>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>High patched ≤ 90 days</span>
                      <span className="text-white font-medium">{soc2?.high_patched_within_90d_pct ?? 100}%</span>
                    </div>
                    <ProgressBar pct={soc2?.high_patched_within_90d_pct ?? 100} />
                    <p className="text-xs text-gray-500 mt-1">{soc2?.high_total ?? 0} high vulns tracked</p>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* PCI DSS */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-2 w-full" />
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">PCI DSS</p>
                    <p className="text-sm text-gray-300 mt-0.5">Internet-facing asset hygiene</p>
                  </div>
                  <StatusBadge status={pci?.status || "COMPLIANT"} />
                </div>
                {/* Large % metric */}
                {(() => {
                  const pct = pci?.clean_pct ?? 100;
                  const color = pct >= 90 ? "text-emerald-400" : pct >= 70 ? "text-amber-400" : "text-red-400";
                  const arrow = pct >= 90 ? "↑" : pct >= 70 ? "→" : "↓";
                  const arrowColor = pct >= 90 ? "text-emerald-400" : pct >= 70 ? "text-gray-400" : "text-red-400";
                  return (
                    <div className="flex items-end gap-2 mb-1">
                      <span className={`text-5xl font-bold ${color}`}>{pct}%</span>
                      <span className={`text-xl mb-1 ${arrowColor}`}>{arrow}</span>
                    </div>
                  );
                })()}
                <p className="text-xs text-gray-400 mt-1">of internet-facing assets with no critical vulns</p>
                <ProgressBar pct={pci?.clean_pct ?? 100} />
                <p className="text-xs text-gray-400 mt-2">
                  {pci?.clean_assets ?? 0} clean / {pci?.internet_assets_total ?? 0} total internet assets
                </p>
                {(pci?.assets_with_critical_vulns ?? 0) > 0 && (
                  <p className="text-xs text-red-400 mt-1">
                    {pci.assets_with_critical_vulns} assets with critical vulns
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      {/* ── MTTP Metrics ── */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-1">Mean Time To Patch (MTTP)</h2>
        <p className="text-sm text-gray-400 mb-4">Mean Time To Patch (MTTP) — average days from vulnerability discovery to confirmed remediation</p>
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                <Skeleton className="h-4 w-1/2 mb-3" />
                <Skeleton className="h-8 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* By Severity */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h3 className="text-sm font-medium text-gray-300 mb-4">By Severity</h3>
              <div className="space-y-3">
                {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => {
                  const d = mttp?.by_severity?.[sev];
                  return (
                    <div key={sev} className="flex items-center justify-between">
                      <SeverityBadge severity={sev} />
                      <span className="text-white font-medium text-sm">
                        {d?.avg_days != null ? `${d.avg_days}d` : "—"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* By Environment */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h3 className="text-sm font-medium text-gray-300 mb-4">By Environment</h3>
              <div className="space-y-3">
                {Object.entries(mttp?.by_environment || {}).length > 0 ? (
                  Object.entries(mttp.by_environment).map(([env, d]: [string, any]) => (
                    <div key={env} className="flex items-center justify-between">
                      <span className="text-xs text-gray-400 capitalize">{env}</span>
                      <span className="text-white font-medium text-sm">
                        {d?.avg_days != null ? `${d.avg_days}d` : "—"}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500">No patched vulns yet</p>
                )}
              </div>
            </div>

            {/* By Team */}
            <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
              <h3 className="text-sm font-medium text-gray-300 mb-4">By Team</h3>
              {(mttp?.by_team || []).length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-gray-400 border-b border-gray-700">
                        <th className="text-left pb-2">Team</th>
                        <th className="text-right pb-2">Avg MTTP</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {mttp.by_team.map((t: any) => {
                        const improving = t.target_days != null && t.avg_days != null && t.avg_days < t.target_days;
                        const worsening = t.target_days != null && t.avg_days != null && t.avg_days > t.target_days;
                        return (
                          <tr key={t.team}>
                            <td className="py-1.5 text-gray-300 text-xs">{t.team}</td>
                            <td className="py-1.5 text-right font-medium text-xs">
                              <span className="text-white">{t.avg_days != null ? `${t.avg_days}d` : "—"}</span>
                              {improving && <span className="ml-1 text-emerald-400">↓</span>}
                              {worsening && <span className="ml-1 text-red-400">↑</span>}
                              {!improving && !worsening && t.avg_days != null && <span className="ml-1 text-gray-500">→</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-gray-500">No patched vulns yet</p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── SLA Tracking ── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-white">SLA Tracking</h2>
            {sla?.counts && (
              <p className="text-sm text-gray-400 mt-0.5">
                {sla.counts.breached} breached · {sla.counts.at_risk} at risk · {sla.counts.on_track} on track
              </p>
            )}
          </div>
          <div className="flex gap-2">
            {(["ALL", "BREACHED", "AT_RISK", "ON_TRACK"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setSlaFilter(f)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  slaFilter === f
                    ? "bg-blue-600 text-white"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                {f.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex gap-4 p-4 border-b border-gray-700">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        ) : filteredSla.length === 0 ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-8 text-center">
            <p className="text-gray-400 text-sm">No items matching this filter.</p>
          </div>
        ) : (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-400 border-b border-gray-700 bg-gray-900/50">
                    <th className="text-left px-4 py-3">CVE ID</th>
                    <th className="text-left px-4 py-3">Severity</th>
                    <th className="text-left px-4 py-3">Asset</th>
                    <th className="text-left px-4 py-3">Discovered</th>
                    <th className="text-left px-4 py-3">SLA Deadline</th>
                    <th className="text-right px-4 py-3">Days Remaining</th>
                    <th className="text-left px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {filteredSla.slice(0, 100).map((item: any) => (
                    <tr key={item.id} className="hover:bg-gray-750 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs text-blue-400">{item.cve_id}</span>
                        {item.kev_listed && (
                          <span className="ml-2 text-xs bg-red-900 text-red-300 px-1.5 py-0.5 rounded">KEV</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <SeverityBadge severity={item.severity} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-gray-300 text-xs">{item.asset_name}</span>
                        {item.asset_environment && (
                          <span className="ml-2 text-xs text-gray-500">{item.asset_environment}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {item.discovered_at ? new Date(item.discovered_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {item.sla_deadline ? new Date(item.sla_deadline).toLocaleDateString() : "—"}
                        <span className="ml-1 text-gray-600">({item.sla_days}d SLA)</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`text-xs font-medium ${
                          item.days_remaining < 0 ? "text-red-400" :
                          item.days_remaining <= 3 ? "text-yellow-400" : "text-green-400"
                        }`}>
                          {item.days_remaining < 0
                            ? `${Math.abs(item.days_remaining)}d overdue`
                            : `${item.days_remaining}d`}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <SlaPill status={item.sla_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredSla.length > 100 && (
              <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-400 text-center">
                Showing 100 of {filteredSla.length} items
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── Print Modal ── */}
      {showPrint && execSummary && (
        <PrintReport data={execSummary} onClose={() => setShowPrint(false)} />
      )}
    </div>
  );
}
