"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { dashboardApi } from "@/lib/api";

interface Goal {
  id: string;
  name: string;
  goal_type: string;
  target_completion_date: string | null;
  vulnerabilities_addressed: number;
  vulnerabilities_total: number;
  current_risk_score: number;
  target_risk_score: number | null;
}

interface MaintenanceWindow {
  id: string;
  name: string;
  start_time: string;
  duration_hours: number;
  environment: string;
  type: string;
  max_assets: number;
  scheduled_bundles?: any[];
}

interface RiskPair {
  vulnerability_id: string;
  vulnerability_identifier: string;
  vulnerability_title: string;
  vulnerability_severity: string;
  asset_id: string;
  asset_name: string;
  asset_environment: string;
  risk_score: number;
  risk_factors: {
    severity: string;
    kev_listed: boolean;
    epss_score: number;
    exploit_available: boolean;
    asset_exposure: string;
    asset_criticality: number;
  };
}

interface DashboardStats {
  vulnerabilities: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    kev_listed: number;
  };
  assets: {
    total: number;
    internet_exposed: number;
    critical_assets: number;
  };
  goals: Goal[];
  risk_score: {
    total: number;
    trend: "up" | "down" | "stable";
    reduction_7d: number;
  };
  bundles: {
    scheduled: number;
    next_window: string | null;
    pending_approval: number;
  };
  windows: MaintenanceWindow[];
}

type DashboardMode = "focus" | "full";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [riskPairs, setRiskPairs] = useState<RiskPair[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<DashboardMode>("focus");

  useEffect(() => {
    const saved = localStorage.getItem("glasswatch-dashboard-mode") as DashboardMode | null;
    if (saved === "full" || saved === "focus") setMode(saved);
  }, []);

  const setModeAndSave = (m: DashboardMode) => {
    setMode(m);
    localStorage.setItem("glasswatch-dashboard-mode", m);
  };

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, topRisks] = await Promise.all([
          dashboardApi.getStats(),
          dashboardApi.getTopRiskPairs(5),
        ]);
        setStats(statsData);
        setRiskPairs(topRisks);
      } catch (error) {
        console.warn("API error:", error);
        setStats(null);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <DashboardSkeleton />;
  if (!stats) return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="text-5xl mb-4">⚠️</div>
      <h3 className="text-xl font-semibold text-white mb-2">Couldn&apos;t load dashboard</h3>
      <p className="text-neutral-400 mb-6 max-w-sm">
        The API may be unavailable. Check your connection or try refreshing.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
      >
        Refresh Page
      </button>
    </div>
  );

  return (
    <>
      {/* Header with mode toggle */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {mode === "focus" ? "Focus" : "Overview"}
          </h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {mode === "focus" ? "What needs your attention right now" : "Full platform snapshot"}
          </p>
        </div>
        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1 border border-gray-700">
          <button
            onClick={() => setModeAndSave("focus")}
            className={`px-3 py-1.5 text-sm rounded-md transition-all font-medium ${
              mode === "focus"
                ? "bg-indigo-600 text-white shadow"
                : "text-gray-400 hover:text-white"
            }`}
          >
            ⚡ Focus
          </button>
          <button
            onClick={() => setModeAndSave("full")}
            className={`px-3 py-1.5 text-sm rounded-md transition-all font-medium ${
              mode === "full"
                ? "bg-indigo-600 text-white shadow"
                : "text-gray-400 hover:text-white"
            }`}
          >
            📊 Full
          </button>
        </div>
      </div>

      {mode === "focus" ? (
        <FocusDashboard stats={stats} />
      ) : (
        <FullDashboard stats={stats} riskPairs={riskPairs} />
      )}
    </>
  );
}

// ─── Focus Mode ──────────────────────────────────────────────────────────────

function FocusDashboard({ stats }: { stats: DashboardStats }) {
  const kevInternetFacing = Math.min(stats.vulnerabilities.kev_listed, stats.assets.internet_exposed);
  const nextWindow = stats.windows[0];
  const [showMore, setShowMore] = useState(false);
  const [showSecondary, setShowSecondary] = useState(false);

  // Determine secondary priority items beyond the main panel
  const secondaryItems: Array<{ label: string; count: number; href: string; color: string }> = [];
  if (kevInternetFacing > 0 && stats.vulnerabilities.critical > kevInternetFacing) {
    secondaryItems.push({ label: "additional critical vulnerabilities", count: stats.vulnerabilities.critical - kevInternetFacing, href: "/vulnerabilities?severity=CRITICAL", color: "text-orange-300" });
  }
  if ((kevInternetFacing > 0 || stats.vulnerabilities.critical > 0) && stats.vulnerabilities.high > 0) {
    secondaryItems.push({ label: "high-severity vulnerabilities", count: stats.vulnerabilities.high, href: "/vulnerabilities?severity=HIGH", color: "text-yellow-300" });
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Panel 1: Right Now — THE single priority card */}
      <RightNowPanel stats={stats} kevInternetFacing={kevInternetFacing} />

      {/* Secondary priority items — collapsed by default */}
      {secondaryItems.length > 0 && (
        <div>
          {!showSecondary ? (
            <button
              onClick={() => setShowSecondary(true)}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Show {secondaryItems.length} more priority {secondaryItems.length === 1 ? "item" : "items"} →
            </button>
          ) : (
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5 space-y-3">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-sm font-semibold text-gray-300">Additional Priority Items</h3>
                <button onClick={() => setShowSecondary(false)} className="text-xs text-gray-500 hover:text-gray-300">Hide ↑</button>
              </div>
              {secondaryItems.map((item) => (
                <div key={item.href} className="flex items-center justify-between">
                  <span className={`text-sm ${item.color}`}>
                    <span className="font-bold text-base mr-1">{item.count}</span>
                    {item.label}
                  </span>
                  <Link href={item.href} className="text-xs text-blue-400 hover:underline">Review →</Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Expand toggle */}
      {!showMore && (
        <button
          onClick={() => setShowMore(true)}
          className="w-full py-2 text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded-lg transition-colors"
        >
          Show goals &amp; schedule ↓
        </button>
      )}

      {/* Panel 2: Active Goals — shown when expanded */}
      {showMore && <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Active Goals</h3>
        {stats.goals.length === 0 ? (
          <div className="text-gray-400 text-sm">
            No active goals.{" "}
            <Link href="/goals" className="text-blue-400 hover:underline">
              Create one →
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {stats.goals.slice(0, 4).map((goal) => {
              const pct =
                goal.vulnerabilities_total > 0
                  ? Math.round((goal.vulnerabilities_addressed / goal.vulnerabilities_total) * 100)
                  : 0;
              return (
                <div key={goal.id}>
                  <div className="flex items-center justify-between mb-1">
                    <Link
                      href={`/goals/${goal.id}`}
                      className="text-sm font-medium text-white hover:text-blue-300 transition-colors"
                    >
                      {goal.name}
                    </Link>
                    <span className="text-sm text-gray-400">
                      {goal.vulnerabilities_addressed}/{goal.vulnerabilities_total} vulns · {pct}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pct >= 80
                          ? "bg-green-500"
                          : pct >= 40
                          ? "bg-blue-500"
                          : "bg-yellow-500"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  {goal.target_completion_date && (
                    <p className="text-xs text-gray-500 mt-1">
                      Target:{" "}
                      {new Date(goal.target_completion_date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
        {stats.goals.length > 4 && (
          <Link href="/goals" className="mt-4 block text-sm text-blue-400 hover:underline">
            View all {stats.goals.length} goals →
          </Link>
        )}
      </div>}

      {/* Panel 3: Next Window — shown when expanded */}
      {showMore && <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Next Maintenance Window</h3>
        {nextWindow ? (
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium">{nextWindow.name}</p>
              <p className="text-gray-400 text-sm mt-1">
                {new Date(nextWindow.start_time).toLocaleDateString("en-US", {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}{" "}
                ·{" "}
                {new Date(nextWindow.start_time).toLocaleTimeString("en-US", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                · {nextWindow.duration_hours}h window
              </p>
              <p className="text-gray-500 text-xs mt-1 capitalize">{nextWindow.environment} environment</p>
            </div>
            <Link
              href="/schedule"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
            >
              View Schedule →
            </Link>
          </div>
        ) : (
          <div className="text-gray-400 text-sm">
            No upcoming maintenance windows.{" "}
            <Link href="/schedule" className="text-blue-400 hover:underline">
              Schedule one →
            </Link>
          </div>
        )}
        {stats.bundles.pending_approval > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-700 flex items-center justify-between">
            <p className="text-sm text-yellow-300">
              ⏳ {stats.bundles.pending_approval} bundle{stats.bundles.pending_approval !== 1 ? "s" : ""} pending approval
            </p>
            <Link href="/approvals" className="text-sm text-blue-400 hover:underline">
              Review →
            </Link>
          </div>
        )}
      </div>}

      {/* Collapse button */}
      {showMore && (
        <button
          onClick={() => setShowMore(false)}
          className="w-full py-2 text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          Show less ↑
        </button>
      )}
    </div>
  );
}

function RightNowPanel({
  stats,
  kevInternetFacing,
}: {
  stats: DashboardStats;
  kevInternetFacing: number;
}) {
  if (kevInternetFacing > 0) {
    return (
      <div className="bg-red-950/60 border border-red-700/60 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="text-3xl">🚨</div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-red-300 mb-1">Critical Action Required</h3>
            <p className="text-white text-base">
              <span className="font-bold text-red-200 text-2xl">{kevInternetFacing}</span>{" "}
              KEV {kevInternetFacing === 1 ? "vulnerability" : "vulnerabilities"} on internet-facing assets
            </p>
            <p className="text-red-300/80 text-sm mt-1">
              These are actively exploited in the wild. CISA BOD 22-01 mandates remediation.
            </p>
            <div className="mt-4 flex gap-3">
              <Link
                href="/vulnerabilities?filter=kev"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg transition-colors"
              >
                Patch These Now →
              </Link>
              <Link
                href="/goals?create=true"
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                Create Goal
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (stats.vulnerabilities.critical > 0) {
    return (
      <div className="bg-orange-950/60 border border-orange-700/60 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="text-3xl">⚠️</div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-orange-300 mb-1">Critical Vulnerabilities</h3>
            <p className="text-white text-base">
              <span className="font-bold text-orange-200 text-2xl">{stats.vulnerabilities.critical}</span>{" "}
              critical{" "}
              {stats.vulnerabilities.critical === 1 ? "vulnerability" : "vulnerabilities"} unpatched
            </p>
            <p className="text-orange-300/80 text-sm mt-1">
              {stats.assets.internet_exposed > 0
                ? `${stats.assets.internet_exposed} of your assets are internet-exposed.`
                : "Review your asset exposure."}
            </p>
            <div className="mt-4">
              <Link
                href="/vulnerabilities?severity=CRITICAL"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white font-semibold rounded-lg transition-colors"
              >
                Review Criticals →
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Zero vulnerabilities — clean environment or fresh account
  if (stats.vulnerabilities.total === 0) {
    return (
      <div className="bg-green-950/50 border border-green-700/40 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="text-3xl">🎉</div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-green-300 mb-1">No critical vulnerabilities — you&apos;re on track!</h3>
            <p className="text-gray-300 text-base">Your environment looks clean. Keep it that way.</p>
            <p className="text-gray-400 text-sm mt-1">
              Connect a scanner or import a CSV to keep your data current.
            </p>
            <div className="mt-4 flex gap-3">
              <Link
                href="/settings/connections"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition-colors"
              >
                Connect Scanner →
              </Link>
              <Link
                href="/import"
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                Import CSV
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-green-950/50 border border-green-700/40 rounded-xl p-6">
      <div className="flex items-start gap-4">
        <div className="text-3xl">✅</div>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-green-300 mb-1">Good Standing</h3>
          <p className="text-white text-base">No critical actions required right now.</p>
          <p className="text-green-300/70 text-sm mt-1">
            {stats.vulnerabilities.high > 0
              ? `${stats.vulnerabilities.high} high-severity vulnerabilities remain — keep them moving.`
              : `${stats.vulnerabilities.total} vulnerabilities tracked. Stay proactive.`}
          </p>
          <div className="mt-4">
            <Link
              href="/vulnerabilities"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
            >
              View All Vulnerabilities →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Full Mode ────────────────────────────────────────────────────────────────

function FullDashboard({ stats, riskPairs }: { stats: DashboardStats; riskPairs: RiskPair[] }) {
  const kevInternetFacing = Math.min(stats.vulnerabilities.kev_listed, stats.assets.internet_exposed);
  const bod2201Deadline = new Date("2026-05-15");
  const daysToDeadline = Math.ceil((bod2201Deadline.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));

  return (
    <>
      {/* Top stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <StatCard
          label="Total Vulnerabilities"
          value={stats.vulnerabilities.total.toLocaleString()}
          sub={`${stats.vulnerabilities.critical} critical · ${stats.vulnerabilities.high} high`}
          href="/vulnerabilities"
        />
        <StatCard
          label="Total Assets"
          value={stats.assets.total.toLocaleString()}
          sub={`${stats.assets.internet_exposed} internet-exposed`}
          href="/assets"
        />
        <StatCard
          label="Risk Score"
          value={stats.risk_score.total.toLocaleString()}
          sub={
            stats.risk_score.trend === "down"
              ? `↓ ${stats.risk_score.reduction_7d}% (7d)`
              : stats.risk_score.trend === "up"
              ? `↑ ${stats.risk_score.reduction_7d}% (7d)`
              : "Stable (7d)"
          }
          subColor={
            stats.risk_score.trend === "down"
              ? "text-green-400"
              : stats.risk_score.trend === "up"
              ? "text-red-400"
              : "text-gray-400"
          }
        />
        <StatCard
          label="Unpatched Criticals"
          value={stats.vulnerabilities.critical.toLocaleString()}
          sub={stats.vulnerabilities.kev_listed > 0 ? `${stats.vulnerabilities.kev_listed} KEV-listed` : "No KEV-listed"}
          subColor={stats.vulnerabilities.kev_listed > 0 ? "text-red-400" : "text-gray-400"}
          href="/vulnerabilities?severity=CRITICAL"
        />
        <StatCard
          label="Patches Scheduled"
          value={stats.bundles.scheduled.toString()}
          sub={
            stats.bundles.pending_approval > 0
              ? `${stats.bundles.pending_approval} pending approval`
              : "All approved"
          }
          href="/approvals"
        />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Critical Path */}
        <div className="card p-6">
          <h3 className="text-sm font-medium text-neutral-400 mb-3">Critical Path</h3>
          <div className="mb-2">
            <span className="text-3xl font-bold text-destructive">{kevInternetFacing}</span>
            <span className="text-neutral-400 ml-2 text-sm">KEV vulns on internet-facing assets</span>
          </div>
          <div className="text-sm text-warning mt-2">
            ⚠ BOD 22-01 deadline in <strong>{daysToDeadline} days</strong>
          </div>
          <Link
            href="/vulnerabilities?filter=kev"
            className="mt-4 block text-sm text-blue-400 hover:underline"
          >
            View KEV vulnerabilities →
          </Link>
        </div>

        {/* KEV breakdown */}
        <div className="card p-6">
          <h3 className="text-sm font-medium text-neutral-400 mb-3">Vulnerability Breakdown</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Critical", count: stats.vulnerabilities.critical, color: "text-red-400" },
              { label: "High", count: stats.vulnerabilities.high, color: "text-orange-400" },
              { label: "Medium", count: stats.vulnerabilities.medium, color: "text-yellow-400" },
              { label: "Low", count: stats.vulnerabilities.low, color: "text-green-400" },
            ].map(({ label, count, color }) => (
              <div key={label} className="text-center">
                <div className={`text-2xl font-bold ${color}`}>{count}</div>
                <div className="text-xs text-gray-400">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Goals */}
      {stats.goals.length > 0 && (
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-400">Active Goals</h3>
            <Link href="/goals" className="text-xs text-blue-400 hover:underline">
              View all →
            </Link>
          </div>
          <div className="space-y-4">
            {stats.goals.slice(0, 3).map((goal) => {
              const pct =
                goal.vulnerabilities_total > 0
                  ? Math.round((goal.vulnerabilities_addressed / goal.vulnerabilities_total) * 100)
                  : 0;
              return (
                <div key={goal.id}>
                  <div className="flex justify-between text-sm mb-1">
                    <Link href={`/goals/${goal.id}`} className="text-white hover:text-blue-300">
                      {goal.name}
                    </Link>
                    <span className="text-gray-400">{pct}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-700 rounded-full">
                    <div
                      className={`h-full rounded-full ${pct >= 80 ? "bg-green-500" : "bg-blue-500"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top risks table */}
      {riskPairs.length > 0 && (
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-400">Top Risk Pairs</h3>
            <Link href="/vulnerabilities" className="text-xs text-blue-400 hover:underline">
              View all →
            </Link>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-700">
                <th className="text-left pb-2 font-medium">Vulnerability</th>
                <th className="text-left pb-2 font-medium">Asset</th>
                <th className="text-right pb-2 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {riskPairs.slice(0, 5).map((pair) => (
                <tr key={`${pair.vulnerability_id}-${pair.asset_id}`} className="hover:bg-gray-800/50">
                  <td className="py-2 pr-4">
                    <div className="text-white font-medium truncate max-w-[200px]">
                      {pair.vulnerability_identifier}
                    </div>
                    <div className="text-xs text-gray-400 truncate max-w-[200px]">
                      {pair.vulnerability_title}
                    </div>
                  </td>
                  <td className="py-2 pr-4">
                    <div className="text-gray-300 truncate max-w-[150px]">{pair.asset_name}</div>
                    <div className="text-xs text-gray-500">{pair.asset_environment}</div>
                  </td>
                  <td className="py-2 text-right">
                    <span
                      className={`font-bold text-base ${
                        pair.risk_score >= 80
                          ? "text-red-400"
                          : pair.risk_score >= 60
                          ? "text-orange-400"
                          : "text-yellow-400"
                      }`}
                    >
                      {pair.risk_score}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Maintenance windows */}
      {stats.windows.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-400">Upcoming Maintenance Windows</h3>
            <Link href="/schedule" className="text-xs text-blue-400 hover:underline">
              Schedule →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {stats.windows.map((w) => (
              <div key={w.id} className="bg-gray-800/60 rounded-lg p-4 border border-gray-700">
                <div className="font-medium text-white text-sm">{w.name}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {new Date(w.start_time).toLocaleDateString("en-US", {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  })}{" "}
                  · {w.duration_hours}h · {w.environment}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function StatCard({
  label,
  value,
  sub,
  subColor = "text-gray-400",
  href,
}: {
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
  href?: string;
}) {
  const content = (
    <div className="card p-5 h-full">
      <p className="text-xs font-medium text-neutral-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className={`text-xs mt-1 ${subColor}`}>{sub}</p>}
    </div>
  );
  return href ? (
    <Link href={href} className="block hover:opacity-90 transition-opacity">
      {content}
    </Link>
  ) : (
    content
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 bg-gray-700 rounded w-1/4" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-xl p-5 h-28 border border-gray-700">
            <div className="h-3 bg-gray-700 rounded w-1/2 mb-3" />
            <div className="h-8 bg-gray-700 rounded w-3/4 mb-2" />
            <div className="h-3 bg-gray-700 rounded w-1/3" />
          </div>
        ))}
      </div>
      <div className="h-40 bg-gray-800 rounded-xl" />
      <div className="h-32 bg-gray-800 rounded-xl" />
    </div>
  );
}
