"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface MaintenanceWindow {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  type: "scheduled" | "emergency" | "blackout";
  environment?: string;
  max_duration_hours: number;
  approved: boolean;
  bundles: Bundle[];
}

interface Bundle {
  id: string;
  name: string;
  status: string;
  risk_score: number;
  vulnerabilities_count: number;
  assets_affected_count: number;
  estimated_duration_minutes: number;
}

// Mock data for now - will connect to API
const mockWindows: MaintenanceWindow[] = [
  {
    id: "1",
    name: "Weekly Maintenance - 2026-04-26",
    start_time: "2026-04-26T02:00:00Z",
    end_time: "2026-04-26T06:00:00Z",
    type: "scheduled",
    environment: "production",
    max_duration_hours: 4,
    approved: true,
    bundles: [
      {
        id: "b1",
        name: "Critical Security Patches - April",
        status: "scheduled",
        risk_score: 2450,
        vulnerabilities_count: 23,
        assets_affected_count: 45,
        estimated_duration_minutes: 120,
      },
      {
        id: "b2",
        name: "KEV Remediation Bundle",
        status: "scheduled",
        risk_score: 1820,
        vulnerabilities_count: 15,
        assets_affected_count: 28,
        estimated_duration_minutes: 90,
      },
    ],
  },
  {
    id: "2",
    name: "Weekly Maintenance - 2026-05-03",
    start_time: "2026-05-03T02:00:00Z",
    end_time: "2026-05-03T06:00:00Z",
    type: "scheduled",
    environment: "production",
    max_duration_hours: 4,
    approved: false,
    bundles: [
      {
        id: "b3",
        name: "High Priority Patches - May",
        status: "draft",
        risk_score: 1950,
        vulnerabilities_count: 18,
        assets_affected_count: 32,
        estimated_duration_minutes: 105,
      },
    ],
  },
];

const STATUS_COLORS: Record<string, string> = {
  scheduled: "text-success",
  draft: "text-neutral-400",
  in_progress: "text-secondary",
  completed: "text-success",
  failed: "text-destructive",
};

const STATUS_BG: Record<string, string> = {
  scheduled: "bg-success/10",
  draft: "bg-neutral-700",
  in_progress: "bg-secondary/10",
  completed: "bg-success/10",
  failed: "bg-destructive/10",
};

export default function SchedulePage() {
  const [windows, setWindows] = useState<MaintenanceWindow[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"calendar" | "list">("list");

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setWindows(mockWindows);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-primary">
                PatchAI
              </Link>
              <span className="ml-3 text-sm text-neutral-400">
                Intelligent Patch Optimization
              </span>
            </div>
            <nav className="flex space-x-6">
              <Link href="/" className="text-neutral-400 hover:text-foreground">
                Dashboard
              </Link>
              <Link href="/vulnerabilities" className="text-neutral-400 hover:text-foreground">
                Vulnerabilities
              </Link>
              <Link href="/goals" className="text-neutral-400 hover:text-foreground">
                Goals
              </Link>
              <Link href="/schedule" className="text-foreground hover:text-primary">
                Schedule
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Patch Schedule</h1>
            <p className="text-neutral-400 mt-1">
              Maintenance windows and scheduled patch bundles
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode("list")}
              className={`px-3 py-1 rounded ${
                viewMode === "list"
                  ? "bg-primary text-background"
                  : "bg-neutral-800 text-neutral-400"
              }`}
            >
              List View
            </button>
            <button
              onClick={() => setViewMode("calendar")}
              className={`px-3 py-1 rounded ${
                viewMode === "calendar"
                  ? "bg-primary text-background"
                  : "bg-neutral-800 text-neutral-400"
              }`}
            >
              Calendar
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <ScheduleSkeleton />
        ) : viewMode === "list" ? (
          <ListView windows={windows} />
        ) : (
          <CalendarView windows={windows} />
        )}
      </main>
    </div>
  );
}

function ListView({ windows }: { windows: MaintenanceWindow[] }) {
  const upcomingWindows = windows.filter(
    (w) => new Date(w.start_time) > new Date()
  );
  const pastWindows = windows.filter(
    (w) => new Date(w.start_time) <= new Date()
  );

  return (
    <div className="space-y-8">
      {/* Upcoming Windows */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Upcoming Maintenance</h2>
        <div className="space-y-4">
          {upcomingWindows.length === 0 ? (
            <div className="card p-8 text-center text-neutral-400">
              No upcoming maintenance windows scheduled
            </div>
          ) : (
            upcomingWindows.map((window) => (
              <WindowCard key={window.id} window={window} />
            ))
          )}
        </div>
      </div>

      {/* Past Windows */}
      {pastWindows.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Past Maintenance</h2>
          <div className="space-y-4">
            {pastWindows.map((window) => (
              <WindowCard key={window.id} window={window} isPast />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function WindowCard({ window, isPast = false }: { window: MaintenanceWindow; isPast?: boolean }) {
  const startDate = new Date(window.start_time);
  const endDate = new Date(window.end_time);
  const duration = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60);
  const totalBundleDuration = window.bundles.reduce(
    (sum, b) => sum + b.estimated_duration_minutes,
    0
  );
  const utilizationPercent = (totalBundleDuration / (duration * 60)) * 100;

  return (
    <div className={`card p-6 ${isPast ? "opacity-60" : ""}`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">{window.name}</h3>
          <div className="flex items-center gap-4 mt-1 text-sm text-neutral-400">
            <span>
              {startDate.toLocaleDateString()} {startDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            <span>•</span>
            <span>{duration}h window</span>
            <span>•</span>
            <span>{window.environment}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {window.approved ? (
            <span className="text-xs px-2 py-1 bg-success/10 text-success rounded">
              APPROVED
            </span>
          ) : (
            <span className="text-xs px-2 py-1 bg-warning/10 text-warning rounded">
              PENDING APPROVAL
            </span>
          )}
          {window.type === "emergency" && (
            <span className="text-xs px-2 py-1 bg-destructive/10 text-destructive rounded">
              EMERGENCY
            </span>
          )}
        </div>
      </div>

      {/* Window Utilization */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-neutral-400">Window Utilization</span>
          <span>{utilizationPercent.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              utilizationPercent > 80 ? "bg-warning" : "bg-primary"
            }`}
            style={{ width: `${utilizationPercent}%` }}
          />
        </div>
      </div>

      {/* Bundles */}
      {window.bundles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-neutral-400">Scheduled Bundles</h4>
          {window.bundles.map((bundle) => (
            <div key={bundle.id} className="bg-neutral-800 rounded-lg p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h5 className="font-medium">{bundle.name}</h5>
                  <div className="flex items-center gap-4 mt-1 text-sm text-neutral-400">
                    <span>{bundle.vulnerabilities_count} vulnerabilities</span>
                    <span>•</span>
                    <span>{bundle.assets_affected_count} assets</span>
                    <span>•</span>
                    <span>{bundle.estimated_duration_minutes} min</span>
                  </div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded ${STATUS_BG[bundle.status]} ${
                    STATUS_COLORS[bundle.status]
                  }`}
                >
                  {bundle.status.toUpperCase()}
                </span>
              </div>
              <div className="mt-2 text-sm">
                <span className="text-neutral-400">Risk Score:</span>{" "}
                <span className="font-medium">{bundle.risk_score}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CalendarView({ windows }: { windows: MaintenanceWindow[] }) {
  // Simple calendar view - in real app would use a proper calendar component
  const currentMonth = new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" });

  return (
    <div className="card p-6">
      <h2 className="text-xl font-semibold mb-4">{currentMonth}</h2>
      <div className="text-center text-neutral-400">
        Calendar view coming soon...
      </div>
      <div className="mt-8 space-y-2">
        {windows.map((window) => {
          const date = new Date(window.start_time);
          return (
            <div key={window.id} className="flex items-center gap-4 p-2">
              <div className="text-sm font-medium w-20">{date.toLocaleDateString()}</div>
              <div className="flex-1 bg-primary/20 rounded p-2">
                <div className="text-sm font-medium">{window.name}</div>
                <div className="text-xs text-neutral-400">
                  {window.bundles.length} bundles scheduled
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScheduleSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="skeleton h-48 rounded-lg" />
      ))}
    </div>
  );
}