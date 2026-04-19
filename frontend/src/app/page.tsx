"use client";

import { useState, useEffect } from "react";
import { AIAssistant } from "@/components/AIAssistant";

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
  goals: {
    active: number;
    on_track: number;
    at_risk: number;
  };
  bundles: {
    scheduled: number;
    next_window: string | null;
    pending_approval: number;
  };
  risk_score: {
    total: number;
    trend: "up" | "down" | "stable";
    reduction_7d: number;
  };
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Mock data for now - will connect to API
  useEffect(() => {
    setTimeout(() => {
      setStats({
        vulnerabilities: {
          total: 2347,
          critical: 142,
          high: 498,
          medium: 1203,
          low: 504,
          kev_listed: 23,
        },
        assets: {
          total: 1284,
          internet_exposed: 342,
          critical_assets: 87,
        },
        goals: {
          active: 5,
          on_track: 3,
          at_risk: 2,
        },
        bundles: {
          scheduled: 12,
          next_window: "2026-04-26 02:00 UTC",
          pending_approval: 3,
        },
        risk_score: {
          total: 84720,
          trend: "down",
          reduction_7d: 12.4,
        },
      });
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (!stats) {
    return <div>Error loading dashboard</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-primary">PatchAI</h1>
              <span className="ml-3 text-sm text-neutral-400">
                Intelligent Patch Optimization
              </span>
            </div>
            <nav className="flex space-x-6">
              <a href="#" className="text-foreground hover:text-primary">
                Dashboard
              </a>
              <a href="#" className="text-neutral-400 hover:text-foreground">
                Vulnerabilities
              </a>
              <a href="#" className="text-neutral-400 hover:text-foreground">
                Goals
              </a>
              <a href="#" className="text-neutral-400 hover:text-foreground">
                Schedule
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Risk Score Hero */}
        <div className="card p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg text-neutral-400 mb-2">
                Total Risk Score
              </h2>
              <div className="flex items-baseline gap-4">
                <div className="metric-value">
                  {stats.risk_score.total.toLocaleString()}
                </div>
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
            </div>
            <div className="text-right">
              <div className="text-sm text-neutral-400">Next Patch Window</div>
              <div className="text-lg font-medium">
                {stats.bundles.next_window || "Not scheduled"}
              </div>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Critical Vulnerabilities */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-neutral-400">
                Critical Vulnerabilities
              </h3>
              <span className="text-xs text-destructive">CRITICAL</span>
            </div>
            <div className="metric-value status-critical">
              {stats.vulnerabilities.critical}
            </div>
            <div className="mt-2 text-sm text-neutral-500">
              {stats.vulnerabilities.kev_listed} in KEV catalog
            </div>
          </div>

          {/* Internet Exposed */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-neutral-400">
                Internet Exposed Assets
              </h3>
              <span className="text-xs text-warning">HIGH RISK</span>
            </div>
            <div className="metric-value">
              {stats.assets.internet_exposed}
            </div>
            <div className="mt-2 text-sm text-neutral-500">
              of {stats.assets.total} total assets
            </div>
          </div>

          {/* Active Goals */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-neutral-400">
                Active Goals
              </h3>
              {stats.goals.at_risk > 0 && (
                <span className="text-xs text-warning">
                  {stats.goals.at_risk} AT RISK
                </span>
              )}
            </div>
            <div className="metric-value">{stats.goals.active}</div>
            <div className="mt-2 text-sm text-neutral-500">
              {stats.goals.on_track} on track
            </div>
          </div>

          {/* Scheduled Bundles */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-neutral-400">
                Scheduled Bundles
              </h3>
              {stats.bundles.pending_approval > 0 && (
                <span className="text-xs text-secondary">
                  {stats.bundles.pending_approval} PENDING
                </span>
              )}
            </div>
            <div className="metric-value">{stats.bundles.scheduled}</div>
            <div className="mt-2 text-sm text-neutral-500">
              Next window in 7 days
            </div>
          </div>
        </div>

        {/* Vulnerability Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <h3 className="text-lg font-medium mb-4">
              Vulnerability Severity Distribution
            </h3>
            <div className="space-y-3">
              <VulnBar
                label="Critical"
                count={stats.vulnerabilities.critical}
                total={stats.vulnerabilities.total}
                color="destructive"
              />
              <VulnBar
                label="High"
                count={stats.vulnerabilities.high}
                total={stats.vulnerabilities.total}
                color="warning"
              />
              <VulnBar
                label="Medium"
                count={stats.vulnerabilities.medium}
                total={stats.vulnerabilities.total}
                color="secondary"
              />
              <VulnBar
                label="Low"
                count={stats.vulnerabilities.low}
                total={stats.vulnerabilities.total}
                color="success"
              />
            </div>
          </div>

          <div className="card p-6">
            <h3 className="text-lg font-medium mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <button className="w-full text-left p-4 rounded-lg bg-neutral-800 hover:bg-neutral-700 flex items-center justify-between group">
                <div>
                  <div className="font-medium">Create New Goal</div>
                  <div className="text-sm text-neutral-400">
                    Define compliance or risk reduction objective
                  </div>
                </div>
                <span className="text-neutral-400 group-hover:text-primary">
                  →
                </span>
              </button>
              <button className="w-full text-left p-4 rounded-lg bg-neutral-800 hover:bg-neutral-700 flex items-center justify-between group">
                <div>
                  <div className="font-medium">Review Pending Approvals</div>
                  <div className="text-sm text-neutral-400">
                    {stats.bundles.pending_approval} bundles awaiting approval
                  </div>
                </div>
                <span className="text-neutral-400 group-hover:text-primary">
                  →
                </span>
              </button>
              <button className="w-full text-left p-4 rounded-lg bg-neutral-800 hover:bg-neutral-700 flex items-center justify-between group">
                <div>
                  <div className="font-medium">Import New Assets</div>
                  <div className="text-sm text-neutral-400">
                    Bulk import from CSV or integrate with CMDB
                  </div>
                </div>
                <span className="text-neutral-400 group-hover:text-primary">
                  →
                </span>
              </button>
            </div>
          </div>
        </div>
      </main>
      
      {/* AI Assistant */}
      <AIAssistant />
    </div>
  );
}

function VulnBar({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: "destructive" | "warning" | "secondary" | "success";
}) {
  const percentage = (count / total) * 100;
  const colorClasses = {
    destructive: "bg-destructive",
    warning: "bg-warning",
    secondary: "bg-secondary",
    success: "bg-success",
  };

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className={`status-${color}`}>{label}</span>
        <span className="text-neutral-400">
          {count} ({percentage.toFixed(1)}%)
        </span>
      </div>
      <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClasses[color]} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="h-16" />
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="skeleton h-32 mb-8 rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-40 rounded-lg" />
          ))}
        </div>
      </main>
    </div>
  );
}