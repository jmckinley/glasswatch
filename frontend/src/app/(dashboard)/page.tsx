"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { dashboardApi } from "@/lib/api";

interface Goal {
  id: string;
  name: string;
  goal_type: string;
  target_completion_date: string | null;
  patches_completed: number;
  patches_remaining: number;
  current_risk_score: number;
  target_risk_score: number | null;
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

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [riskPairs, setRiskPairs] = useState<RiskPair[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (!stats) {
    return <div className="text-center text-neutral-400 p-8">Error loading dashboard</div>;
  }

  // Calculate KEV + internet-facing critical path
  const kevInternetFacing = Math.min(stats.vulnerabilities.kev_listed, stats.assets.internet_exposed);
  const bod2201Deadline = new Date("2026-05-15"); // Example BOD 22-01 deadline
  const daysToDeadline = Math.ceil((bod2201Deadline.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));

  return (
    <>
      {/* Risk Posture Overview */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Risk Posture Overview</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Risk Score with Trend */}
          <div className="card p-6">
            <h3 className="text-sm font-medium text-neutral-400 mb-2">Total Risk Score</h3>
            <div className="flex items-baseline gap-3">
              <div className="metric-value">{stats.risk_score.total.toLocaleString()}</div>
              <div
                className={`flex items-center text-sm ${
                  stats.risk_score.trend === "down"
                    ? "text-success"
                    : stats.risk_score.trend === "up"
                    ? "text-destructive"
                    : "text-neutral-400"
                }`}
              >
                {stats.risk_score.trend === "down" ? "↓" : "↑"}
                {stats.risk_score.reduction_7d}% (7d)
              </div>
            </div>
            <div className="mt-4 text-sm text-neutral-400">
              {stats.vulnerabilities.total} total vulnerabilities across {stats.assets.total} assets
            </div>
          </div>

          {/* Critical Path Alert */}
          <div className="card p-6 border-l-4 border-destructive">
            <h3 className="text-sm font-medium text-neutral-400 mb-2">Critical Path Alert</h3>
            <div className="mb-2">
              <span className="text-2xl font-bold text-destructive">{kevInternetFacing}</span>
              <span className="text-neutral-400 ml-2">KEV vulns on internet-facing assets</span>
            </div>
            <div className="text-sm text-warning mt-3">
              ⚠ BOD 22-01 deadline in <strong>{daysToDeadline} days</strong>
            </div>
            <Link href="/vulnerabilities?kev=true&exposure=internet" className="text-sm text-primary hover:underline mt-2 inline-block">
              View KEV vulnerabilities →
            </Link>
          </div>

          {/* Next Maintenance */}
          <div className="card p-6 bg-primary/5 border-primary/20">
            <h3 className="text-sm font-medium text-neutral-400 mb-2">Next Patch Window</h3>
            {stats.bundles.next_window ? (
              <>
                <div className="text-lg font-medium">
                  {new Date(stats.bundles.next_window).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </div>
                <div className="text-sm text-neutral-400 mt-1">
                  {stats.bundles.scheduled} bundles scheduled
                </div>
                <Link href="/schedule" className="text-sm text-primary hover:underline mt-2 inline-block">
                  View schedule →
                </Link>
              </>
            ) : (
              <div className="text-neutral-400">No windows scheduled</div>
            )}
          </div>
        </div>
      </div>

      {/* Goal Health */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">Goal Health</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {stats.goals.length === 0 ? (
            <div className="col-span-3 card p-8 text-center text-neutral-400">
              No active goals. <Link href="/goals" className="text-primary hover:underline">Create your first goal</Link>
            </div>
          ) : (
            stats.goals.map((goal) => <GoalHealthCard key={goal.id} goal={goal} />)
          )}
        </div>
      </div>

      {/* What Needs Attention */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Riskiest Pairs */}
        <div className="card p-6">
          <h3 className="text-lg font-medium mb-4">Top 5 Riskiest Asset-Vulnerability Pairs</h3>
          {riskPairs.length === 0 ? (
            <div className="text-center text-neutral-400 py-8">No vulnerability data available</div>
          ) : (
            <div className="space-y-3">
              {riskPairs.map((pair, idx) => (
                <div key={idx} className="bg-neutral-800 rounded-lg p-4 hover:bg-neutral-750 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <Link
                        href={`/vulnerabilities/${pair.vulnerability_id}`}
                        className="font-medium hover:text-primary transition-colors"
                      >
                        {pair.vulnerability_identifier}
                      </Link>
                      <div className="text-sm text-neutral-400 mt-1">
                        {pair.asset_name} <span className="text-neutral-500">({pair.asset_environment})</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-destructive">{pair.risk_score.toFixed(1)}</div>
                      <div className="text-xs text-neutral-500">risk score</div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <RiskBadge label={pair.risk_factors.severity} type="severity" />
                    {pair.risk_factors.kev_listed && <RiskBadge label="KEV" type="critical" />}
                    {pair.risk_factors.epss_score > 0.5 && (
                      <RiskBadge label={`EPSS ${(pair.risk_factors.epss_score * 100).toFixed(0)}%`} type="warning" />
                    )}
                    {pair.risk_factors.asset_exposure === "internet-facing" && (
                      <RiskBadge label="Internet" type="warning" />
                    )}
                    {pair.risk_factors.asset_criticality >= 8 && (
                      <RiskBadge label={`Crit ${pair.risk_factors.asset_criticality}`} type="info" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming Windows */}
        <div className="card p-6">
          <h3 className="text-lg font-medium mb-4">Upcoming Maintenance Windows</h3>
          {stats.windows.length === 0 ? (
            <div className="text-center text-neutral-400 py-8">No upcoming windows scheduled</div>
          ) : (
            <div className="space-y-3">
              {stats.windows.map((window) => {
                const startDate = new Date(window.start_time);
                const bundleCount = window.scheduled_bundles?.length || 0;
                const capacityUsed = window.scheduled_bundles
                  ?.reduce((sum, b) => sum + (b.assets_affected_count || 0), 0) || 0;
                const capacityPct = window.max_assets ? (capacityUsed / window.max_assets) * 100 : 0;

                return (
                  <div key={window.id} className="bg-neutral-800 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <div className="font-medium">{window.name}</div>
                        <div className="text-sm text-neutral-400 mt-1">
                          {startDate.toLocaleDateString(undefined, { month: "short", day: "numeric" })} •{" "}
                          {startDate.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })} •{" "}
                          {window.duration_hours}h • {window.environment}
                        </div>
                      </div>
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          window.type === "emergency"
                            ? "bg-destructive/20 text-destructive"
                            : "bg-primary/20 text-primary"
                        }`}
                      >
                        {window.type.toUpperCase()}
                      </span>
                    </div>
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-neutral-400 mb-1">
                        <span>
                          {bundleCount} bundles • {capacityUsed}/{window.max_assets} assets
                        </span>
                        <span>{capacityPct.toFixed(0)}% capacity</span>
                      </div>
                      <div className="h-1.5 bg-neutral-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            capacityPct > 80 ? "bg-warning" : "bg-primary"
                          }`}
                          style={{ width: `${Math.min(capacityPct, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <Link href="/schedule" className="block mt-4 text-center text-sm text-primary hover:underline">
            View full schedule →
          </Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card p-6">
        <h3 className="text-lg font-medium mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Link
            href="/goals"
            className="block p-4 rounded-lg bg-neutral-800 hover:bg-neutral-700 transition-colors group"
          >
            <div className="font-medium">Create New Goal</div>
            <div className="text-sm text-neutral-400 mt-1">
              Define compliance or risk reduction objective
            </div>
          </Link>
          <Link
            href="/approvals"
            className="block p-4 rounded-lg bg-neutral-800 hover:bg-neutral-700 transition-colors group"
          >
            <div className="font-medium">Review Pending Approvals</div>
            <div className="text-sm text-neutral-400 mt-1">
              {stats.bundles.pending_approval} bundles awaiting approval
            </div>
          </Link>
          <Link
            href="/vulnerabilities"
            className="block p-4 rounded-lg bg-neutral-800 hover:bg-neutral-700 transition-colors group"
          >
            <div className="font-medium">Import New Assets</div>
            <div className="text-sm text-neutral-400 mt-1">
              Bulk import from CSV or integrate with CMDB
            </div>
          </Link>
        </div>
      </div>
    </>
  );
}

function GoalHealthCard({ goal }: { goal: Goal }) {
  const totalPatches = goal.patches_completed + goal.patches_remaining;
  const progressPct = totalPatches > 0 ? (goal.patches_completed / totalPatches) * 100 : 0;
  
  // Calculate velocity and projection
  const daysRemaining = goal.target_completion_date
    ? Math.ceil((new Date(goal.target_completion_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
    : null;
  
  // Assume patches were completed over the last 30 days (rough estimate)
  const patchesPerWeek = goal.patches_completed > 0 ? (goal.patches_completed / 30) * 7 : 0;
  const weeksNeeded = patchesPerWeek > 0 ? goal.patches_remaining / patchesPerWeek : Infinity;
  const weeksAvailable = daysRemaining ? daysRemaining / 7 : null;
  
  // Determine status
  let status: "on-track" | "at-risk" | "behind";
  if (weeksAvailable === null || weeksNeeded === Infinity) {
    status = progressPct >= 50 ? "on-track" : "at-risk";
  } else if (weeksNeeded <= weeksAvailable * 0.9) {
    status = "on-track";
  } else if (weeksNeeded <= weeksAvailable) {
    status = "at-risk";
  } else {
    status = "behind";
  }

  const statusColors = {
    "on-track": "border-success bg-success/5",
    "at-risk": "border-warning bg-warning/5",
    "behind": "border-destructive bg-destructive/5",
  };

  const statusLabels = {
    "on-track": "✓ On Track",
    "at-risk": "⚠ At Risk",
    "behind": "✗ Behind",
  };

  return (
    <div className={`card p-6 border-l-4 ${statusColors[status]}`}>
      <div className="flex justify-between items-start mb-3">
        <h4 className="font-medium">{goal.name}</h4>
        <span
          className={`text-xs px-2 py-1 rounded ${
            status === "on-track"
              ? "bg-success/20 text-success"
              : status === "at-risk"
              ? "bg-warning/20 text-warning"
              : "bg-destructive/20 text-destructive"
          }`}
        >
          {statusLabels[status]}
        </span>
      </div>

      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-neutral-400">Progress</span>
          <span>{progressPct.toFixed(0)}% complete</span>
        </div>
        <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              status === "on-track" ? "bg-success" : status === "at-risk" ? "bg-warning" : "bg-destructive"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-neutral-400">Patches remaining:</span>
          <span className="font-medium">{goal.patches_remaining}</span>
        </div>
        {daysRemaining !== null && (
          <div className="flex justify-between">
            <span className="text-neutral-400">Days remaining:</span>
            <span className="font-medium">{daysRemaining}</span>
          </div>
        )}
        {patchesPerWeek > 0 && (
          <div className="flex justify-between">
            <span className="text-neutral-400">Velocity:</span>
            <span className="font-medium">{patchesPerWeek.toFixed(1)} patches/week</span>
          </div>
        )}
      </div>

      {weeksNeeded !== Infinity && weeksAvailable !== null && (
        <div className="mt-3 pt-3 border-t border-neutral-700 text-xs text-neutral-400">
          {status === "on-track" && (
            <>Need {weeksNeeded.toFixed(1)} weeks, have {weeksAvailable.toFixed(1)} weeks</>
          )}
          {status === "at-risk" && (
            <>Tight timeline: {weeksNeeded.toFixed(1)} weeks needed, {weeksAvailable.toFixed(1)} available</>
          )}
          {status === "behind" && (
            <>Need {weeksNeeded.toFixed(1)} weeks, only {weeksAvailable.toFixed(1)} available — increase velocity</>
          )}
        </div>
      )}

      <Link href={`/goals/${goal.id}`} className="block mt-3 text-sm text-primary hover:underline">
        View details →
      </Link>
    </div>
  );
}

function RiskBadge({ label, type }: { label: string; type: "severity" | "critical" | "warning" | "info" }) {
  const colors = {
    severity: "bg-neutral-700 text-neutral-300",
    critical: "bg-destructive/20 text-destructive border border-destructive/30",
    warning: "bg-warning/20 text-warning",
    info: "bg-primary/20 text-primary",
  };

  return <span className={`text-xs px-2 py-0.5 rounded ${colors[type]}`}>{label}</span>;
}

function DashboardSkeleton() {
  return (
    <>
      <div className="skeleton h-32 mb-8 rounded-lg" />
      <div className="skeleton h-48 mb-8 rounded-lg" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="skeleton h-96 rounded-lg" />
        <div className="skeleton h-96 rounded-lg" />
      </div>
    </>
  );
}
