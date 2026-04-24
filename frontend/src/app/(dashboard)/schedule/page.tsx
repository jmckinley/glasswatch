"use client";

import { useState, useEffect, useMemo } from "react";
import { maintenanceWindowsApi, goalsApi } from "@/lib/api";
import MaintenanceWindowDialog from "@/components/MaintenanceWindowDialog";
import ScheduleCalendar from "@/components/ScheduleCalendar";

// ─── Types ────────────────────────────────────────────────────────────────────

interface MaintenanceWindow {
  id: string;
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  type: "scheduled" | "emergency" | "blackout";
  environment?: string;
  datacenter?: string;
  geography?: string;
  timezone?: string;
  duration_hours: number;
  approved: boolean;
  active: boolean;
  max_assets?: number;
  max_risk_score?: number;
  scheduled_bundles: Bundle[];
  priority?: number;
  asset_group?: string;
  service_name?: string;
  is_default?: boolean;
}

interface Bundle {
  id: string;
  name: string;
  status: string;
  risk_score?: number;
  vulnerabilities_count?: number;
  assets_affected_count?: number;
  estimated_duration_minutes?: number;
  goal_id?: string;
  items?: BundleItem[];
}

interface BundleItem {
  id: string;
  asset_vulnerability_id: string;
  vulnerability?: { identifier: string; title: string; severity: string };
  asset?: { name: string; identifier: string };
}

interface Goal {
  id: string;
  name: string;
  target_completion_date: string | null;
  vulnerabilities_addressed: number;
  vulnerabilities_total: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TYPE_STYLES: Record<string, { bg: string; text: string; border: string; label: string }> = {
  scheduled: {
    bg: "bg-blue-500/20",
    text: "text-blue-300",
    border: "border-blue-500/40",
    label: "Scheduled",
  },
  emergency: {
    bg: "bg-red-500/20",
    text: "text-red-300",
    border: "border-red-500/40",
    label: "Emergency",
  },
  blackout: {
    bg: "bg-gray-600/30",
    text: "text-gray-300",
    border: "border-gray-500/40",
    label: "Blackout",
  },
};

const ENV_COLORS: Record<string, string> = {
  production: "bg-red-500/20 text-red-300 border-red-500/30",
  prod: "bg-red-500/20 text-red-300 border-red-500/30",
  staging: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  stage: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  development: "bg-green-500/20 text-green-300 border-green-500/30",
  dev: "bg-green-500/20 text-green-300 border-green-500/30",
  default: "bg-neutral-600/30 text-neutral-300 border-neutral-500/30",
};

const ENV_TIMELINE_COLORS: Record<string, string> = {
  production: "#ef4444",
  prod: "#ef4444",
  staging: "#f59e0b",
  stage: "#f59e0b",
  development: "#22c55e",
  dev: "#22c55e",
  default: "#6b7280",
};

function getEnvColor(env?: string): string {
  if (!env) return ENV_COLORS.default;
  return ENV_COLORS[env.toLowerCase()] || ENV_COLORS.default;
}

function getEnvTimelineColor(env?: string): string {
  if (!env) return ENV_TIMELINE_COLORS.default;
  return ENV_TIMELINE_COLORS[env.toLowerCase()] || ENV_TIMELINE_COLORS.default;
}

function getEnvIcon(env?: string): string {
  if (!env) return "🔧";
  const e = env.toLowerCase();
  if (e.includes("prod")) return "🏭";
  if (e.includes("stag")) return "🧪";
  if (e.includes("dev")) return "💻";
  return "🔧";
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return `${Math.abs(diffDays)}d ago`;
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  if (diffDays < 7) return `In ${diffDays} days`;
  if (diffDays < 14) return "Next week";
  return `In ${Math.round(diffDays / 7)} weeks`;
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SchedulePage() {
  const [windows, setWindows] = useState<MaintenanceWindow[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);

  // View & grouping
  const [viewMode, setViewMode] = useState<"grid" | "timeline" | "calendar">("grid");
  const [groupBy, setGroupBy] = useState<"environment" | "datacenter" | "geography" | "type">("environment");

  // Filtering
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const [environments, setEnvironments] = useState<string[]>([]);
  const [assetGroups, setAssetGroups] = useState<string[]>([]);

  // Dialog
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWindow, setEditingWindow] = useState<any>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Conflicts
  const [conflicts, setConflicts] = useState<ConflictWarning[]>([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [windowsData, goalsData, envsData, groupsData] = await Promise.all([
        maintenanceWindowsApi.list({ active_only: false, future_only: false }),
        goalsApi.list({ active_only: true }),
        maintenanceWindowsApi.listEnvironments().catch(() => ({ environments: [] })),
        maintenanceWindowsApi.listAssetGroups().catch(() => ({ asset_groups: [] })),
      ]);
      const w: MaintenanceWindow[] = windowsData.items || [];
      setWindows(w);
      setGoals(goalsData || []);
      setEnvironments(envsData.environments || []);
      setAssetGroups(groupsData.asset_groups || []);
      setConflicts(detectConflicts(w));
    } catch (error) {
      console.error("Failed to fetch schedule data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Compute filter options from actual data
  const filterOptions = useMemo(() => {
    const opts = new Set<string>();
    windows.forEach((w) => {
      if (w[groupBy]) opts.add(w[groupBy] as string);
    });
    return Array.from(opts).sort();
  }, [windows, groupBy]);

  // Apply active filters
  const filteredWindows = useMemo(() => {
    if (activeFilters.size === 0) return windows;
    return windows.filter((w) => {
      const val = w[groupBy] as string | undefined;
      return val && activeFilters.has(val);
    });
  }, [windows, activeFilters, groupBy]);

  // Group filtered windows
  const groupedWindows = useMemo(() => {
    const groups = new Map<string, MaintenanceWindow[]>();
    filteredWindows.forEach((w) => {
      const key = (w[groupBy] as string) || "unspecified";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(w);
    });
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredWindows, groupBy]);

  const toggleFilter = (val: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(val)) next.delete(val);
      else next.add(val);
      return next;
    });
  };

  const handleEdit = (w: MaintenanceWindow) => {
    setEditingWindow(w);
    setDialogOpen(true);
  };
  const handleDelete = async (id: string) => {
    try {
      await maintenanceWindowsApi.delete(id);
      await fetchData();
      setDeleteConfirm(null);
    } catch (e: any) {
      alert(e.message || "Failed to delete");
    }
  };

  return (
    <>
      {/* ── Header ── */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold">Maintenance Windows</h1>
          <p className="text-neutral-400 mt-1">
            {windows.length} window{windows.length !== 1 ? "s" : ""} across{" "}
            {environments.length} environment{environments.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => { setEditingWindow(null); setDialogOpen(true); }}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 font-medium"
        >
          + New Window
        </button>
      </div>

      {/* ── Conflict Warnings ── */}
      {conflicts.length > 0 && (
        <div className="mb-6 bg-amber-900/30 border border-amber-700 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-amber-400 text-lg">⚠️</span>
            <span className="text-amber-300 font-semibold text-sm">Schedule Conflicts Detected</span>
          </div>
          {conflicts.map((c, i) => (
            <div key={i} className="flex items-start gap-2 text-amber-200 text-sm pl-2 border-l-2 border-amber-600">
              <span>{c.message}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Controls Bar ── */}
      <div className="flex flex-wrap gap-3 items-center mb-6">
        {/* View Toggle — segmented control */}
        <div className="inline-flex rounded-lg border border-gray-600 bg-gray-800 p-1 gap-1">
          {(["grid", "timeline", "calendar"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setViewMode(v)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                viewMode === v
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-gray-400 hover:text-white hover:bg-gray-700"
              }`}
            >
              {v === "grid" ? "⊞ Grid" : v === "timeline" ? "📅 Timeline" : "🗓 Calendar"}
            </button>
          ))}
        </div>

        {/* Group By */}
        <div className="flex items-center gap-2">
          <span className="text-neutral-400 text-sm">Group by:</span>
          <select
            value={groupBy}
            onChange={(e) => { setGroupBy(e.target.value as any); setActiveFilters(new Set()); }}
            className="px-3 py-2 bg-neutral-800 text-white rounded-lg border border-neutral-700 text-sm"
          >
            <option value="environment">Environment</option>
            <option value="datacenter">Datacenter</option>
            <option value="geography">Geography</option>
            <option value="type">Type</option>
          </select>
        </div>

        {/* Filter chips */}
        <div className="flex flex-wrap gap-2">
          {filterOptions.map((opt) => (
            <button
              key={opt}
              onClick={() => toggleFilter(opt)}
              className={`px-3 py-1 rounded-full text-sm border transition-colors capitalize ${
                activeFilters.has(opt)
                  ? "bg-blue-600 text-white border-blue-500"
                  : "bg-neutral-800 text-neutral-300 border-neutral-600 hover:border-neutral-400"
              }`}
            >
              {opt}
            </button>
          ))}
          {activeFilters.size > 0 && (
            <button
              onClick={() => setActiveFilters(new Set())}
              className="px-3 py-1 rounded-full text-sm text-neutral-400 hover:text-white transition-colors"
            >
              ✕ Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Content ── */}
      {loading ? (
        <ScheduleSkeleton />
      ) : viewMode === "grid" ? (
        <GridView
          groupedWindows={groupedWindows}
          groupBy={groupBy}
          goals={goals}
          onEdit={handleEdit}
          onDelete={(id) => setDeleteConfirm(id)}
        />
      ) : viewMode === "timeline" ? (
        <TimelineView windows={filteredWindows} groupedWindows={groupedWindows} groupBy={groupBy} />
      ) : (
        <ScheduleCalendar
          windows={windows}
          onWindowUpdate={fetchData}
          environments={environments}
          assetGroups={assetGroups}
        />
      )}

      {/* ── Dialog ── */}
      <MaintenanceWindowDialog
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={async () => { await fetchData(); }}
        windowData={editingWindow}
      />

      {/* ── Delete Confirm ── */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full border border-gray-600 mx-4">
            <h3 className="text-xl font-bold mb-3">Delete Maintenance Window?</h3>
            <p className="text-gray-300 mb-6">This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ─── Conflict Detection ───────────────────────────────────────────────────────

interface ConflictWarning {
  message: string;
}

function detectConflicts(windows: MaintenanceWindow[]): ConflictWarning[] {
  const warnings: ConflictWarning[] = [];
  const byEnv = new Map<string, MaintenanceWindow[]>();

  windows.forEach((w) => {
    if (w.type === "blackout") return;
    const env = w.environment || "unspecified";
    if (!byEnv.has(env)) byEnv.set(env, []);
    byEnv.get(env)!.push(w);
  });

  byEnv.forEach((envWindows, env) => {
    for (let i = 0; i < envWindows.length; i++) {
      for (let j = i + 1; j < envWindows.length; j++) {
        const a = envWindows[i];
        const b = envWindows[j];
        const aStart = new Date(a.start_time);
        const aEnd = new Date(a.end_time);
        const bStart = new Date(b.start_time);
        const bEnd = new Date(b.end_time);
        if (aStart < bEnd && bStart < aEnd) {
          const dateStr = aStart.toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
          });
          warnings.push({
            message: `"${a.name}" and "${b.name}" overlap in ${env} on ${dateStr} — consider adjusting schedule`,
          });
        }
      }
    }
  });

  return warnings;
}

// ─── Grid View ────────────────────────────────────────────────────────────────

function GridView({
  groupedWindows,
  groupBy,
  goals,
  onEdit,
  onDelete,
}: {
  groupedWindows: [string, MaintenanceWindow[]][];
  groupBy: string;
  goals: Goal[];
  onEdit: (w: MaintenanceWindow) => void;
  onDelete: (id: string) => void;
}) {
  if (groupedWindows.length === 0) {
    return (
      <div className="text-center py-16 text-neutral-400">
        <div className="text-5xl mb-4">📅</div>
        <p className="text-lg">No maintenance windows found</p>
        <p className="text-sm mt-1">Create one to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      {groupedWindows.map(([groupKey, groupWindows]) => (
        <div key={groupKey}>
          {/* Group Header */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xl">{groupBy === "environment" ? getEnvIcon(groupKey) : groupBy === "datacenter" ? "🖥" : groupBy === "geography" ? "🌍" : "📋"}</span>
            <h2 className="text-xl font-bold capitalize">
              {groupKey === "unspecified" ? "No " + groupBy.charAt(0).toUpperCase() + groupBy.slice(1) : groupKey}
            </h2>
            <span className="px-2 py-0.5 bg-neutral-700 text-neutral-300 rounded-full text-sm">
              {groupWindows.length}
            </span>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {groupWindows.map((w) => (
              <WindowCard key={w.id} window={w} goals={goals} onEdit={onEdit} onDelete={onDelete} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Window Card ─────────────────────────────────────────────────────────────

function WindowCard({
  window: w,
  goals,
  onEdit,
  onDelete,
}: {
  window: MaintenanceWindow;
  goals: Goal[];
  onEdit: (w: MaintenanceWindow) => void;
  onDelete: (id: string) => void;
}) {
  const now = new Date();
  const start = new Date(w.start_time);
  const end = new Date(w.end_time);
  const isFuture = start > now;
  const isActiveNow = start <= now && end > now;
  const isPast = end <= now;

  const typeMeta = TYPE_STYLES[w.type] || TYPE_STYLES.scheduled;
  const envColorClass = getEnvColor(w.environment);
  const bundleCount = w.scheduled_bundles?.length || 0;
  const totalRisk = (w.scheduled_bundles || []).reduce((s, b) => s + (b.risk_score || 0), 0);

  // Status dot
  const statusDot = isActiveNow
    ? { color: "bg-green-400", label: "Active Now" }
    : isPast
    ? { color: "bg-neutral-500", label: "Past" }
    : w.type === "blackout"
    ? { color: "bg-red-400", label: "Blackout" }
    : { color: "bg-blue-400", label: "Upcoming" };

  const startFmt = start.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  const timeFmt = start.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

  return (
    <div
      className={`bg-gray-900 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors flex flex-col gap-4 ${
        isPast ? "opacity-60" : ""
      } ${w.type === "blackout" ? "border-red-500/30" : ""}`}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot.color}`} title={statusDot.label} />
            <h3 className="font-semibold text-white truncate">{w.name}</h3>
          </div>
          {w.description && (
            <p className="text-xs text-neutral-400 truncate">{w.description}</p>
          )}
        </div>
        <span
          className={`flex-shrink-0 text-xs px-2 py-1 rounded-full border font-medium ${typeMeta.bg} ${typeMeta.text} ${typeMeta.border}`}
        >
          {typeMeta.label}
        </span>
      </div>

      {/* Tags row */}
      <div className="flex flex-wrap gap-1.5">
        {w.environment && (
          <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${envColorClass}`}>
            {w.environment}
          </span>
        )}
        {w.datacenter && (
          <span className="text-xs px-2 py-0.5 rounded-full border bg-purple-500/20 text-purple-300 border-purple-500/30">
            {w.datacenter}
          </span>
        )}
        {w.geography && (
          <span className="text-xs px-2 py-0.5 rounded-full border bg-cyan-500/20 text-cyan-300 border-cyan-500/30">
            {w.geography}
          </span>
        )}
        {w.is_default && (
          <span className="text-xs px-2 py-0.5 rounded-full border bg-neutral-700 text-neutral-300 border-neutral-600">
            default
          </span>
        )}
      </div>

      {/* Schedule info */}
      <div className="space-y-1 text-sm">
        <div className="flex items-center gap-2 text-neutral-300">
          <span>📅</span>
          <span>{startFmt} at {timeFmt}</span>
        </div>
        <div className="flex items-center gap-2 text-neutral-400">
          <span>⏱</span>
          <span>{w.duration_hours}h window</span>
          {w.timezone && <span className="text-neutral-500">· {w.timezone}</span>}
        </div>
        {isFuture && (
          <div className="flex items-center gap-2 text-neutral-400">
            <span>🕐</span>
            <span className="text-blue-400 font-medium">{formatRelativeTime(w.start_time)}</span>
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5 text-neutral-400">
          <span>📦</span>
          <span className="text-white font-medium">{bundleCount}</span>
          <span>bundle{bundleCount !== 1 ? "s" : ""}</span>
        </div>
        {totalRisk > 0 && (
          <div className="flex items-center gap-1.5 text-neutral-400">
            <span>⚡</span>
            <span className="text-yellow-300 font-medium">{totalRisk.toFixed(1)}</span>
            <span>risk</span>
          </div>
        )}
        {w.approved ? (
          <span className="ml-auto text-xs text-green-400 font-medium">✓ Approved</span>
        ) : (
          <span className="ml-auto text-xs text-yellow-400 font-medium">Pending</span>
        )}
      </div>

      {/* Actions */}
      {!isPast && (
        <div className="flex gap-2 pt-1 border-t border-gray-700">
          <button
            onClick={() => onEdit(w)}
            className="flex-1 px-3 py-1.5 text-xs bg-blue-500/15 text-blue-300 rounded-lg hover:bg-blue-500/25 transition-colors font-medium"
          >
            ✏️ Edit
          </button>
          <button
            onClick={() => onDelete(w.id)}
            className="flex-1 px-3 py-1.5 text-xs bg-red-500/15 text-red-300 rounded-lg hover:bg-red-500/25 transition-colors font-medium"
          >
            🗑 Delete
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Timeline View ────────────────────────────────────────────────────────────

function TimelineView({
  windows,
  groupedWindows,
  groupBy,
}: {
  windows: MaintenanceWindow[];
  groupedWindows: [string, MaintenanceWindow[]][];
  groupBy: string;
}) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; window: MaintenanceWindow } | null>(null);

  const now = new Date();
  const rangeStart = new Date(now);
  rangeStart.setHours(0, 0, 0, 0);
  const rangeEnd = new Date(rangeStart);
  rangeEnd.setDate(rangeEnd.getDate() + 28); // 4 weeks

  const totalMs = rangeEnd.getTime() - rangeStart.getTime();

  function pct(date: Date): number {
    const ms = date.getTime() - rangeStart.getTime();
    return Math.max(0, Math.min(100, (ms / totalMs) * 100));
  }

  // Week column markers
  const weekMarkers: Date[] = [];
  for (let i = 0; i <= 4; i++) {
    const d = new Date(rangeStart);
    d.setDate(d.getDate() + i * 7);
    weekMarkers.push(d);
  }

  if (windows.length === 0) {
    return (
      <div className="text-center py-16 text-neutral-400">
        <p className="text-lg">No windows to display in timeline</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
      {/* Timeline header */}
      <div className="flex items-center bg-gray-800 border-b border-gray-700">
        <div className="w-48 flex-shrink-0 p-3 text-xs text-neutral-400 font-medium uppercase tracking-wider">
          Group
        </div>
        <div className="flex-1 relative h-10">
          {weekMarkers.map((wk, i) => (
            <div
              key={i}
              className="absolute top-0 h-full flex items-center"
              style={{ left: `${(i / 4) * 100}%` }}
            >
              <div className="border-l border-gray-600 h-full" />
              <span className="text-xs text-neutral-500 pl-1.5 whitespace-nowrap">
                {wk.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              </span>
            </div>
          ))}
          {/* Today marker */}
          <div
            className="absolute top-0 h-full border-l-2 border-blue-500 z-10"
            style={{ left: `${pct(now)}%` }}
          >
            <span className="absolute -top-0 left-1 text-xs text-blue-400 font-medium">now</span>
          </div>
        </div>
      </div>

      {/* Rows */}
      {groupedWindows.map(([groupKey, groupWindows]) => (
        <div key={groupKey} className="flex items-start border-b border-gray-800 last:border-b-0 group">
          {/* Row label */}
          <div className="w-48 flex-shrink-0 p-3 flex items-center gap-2">
            <span className="text-sm">
              {groupBy === "environment" ? getEnvIcon(groupKey) : "🔹"}
            </span>
            <span className="text-sm font-medium text-neutral-300 capitalize truncate" title={groupKey}>
              {groupKey === "unspecified" ? "—" : groupKey}
            </span>
            <span className="text-xs text-neutral-500">({groupWindows.length})</span>
          </div>

          {/* Track */}
          <div className="flex-1 relative min-h-[48px] py-2">
            {/* Week grid lines */}
            {weekMarkers.map((wk, i) => (
              <div
                key={i}
                className="absolute top-0 h-full border-l border-gray-800"
                style={{ left: `${(i / 4) * 100}%` }}
              />
            ))}

            {/* Window blocks */}
            {groupWindows.map((w) => {
              const wStart = new Date(w.start_time);
              const wEnd = new Date(w.end_time);
              if (wEnd < rangeStart || wStart > rangeEnd) return null;

              const left = pct(wStart);
              const right = pct(wEnd);
              const width = Math.max(right - left, 0.5);
              const color = groupBy === "environment"
                ? getEnvTimelineColor(w.environment)
                : w.type === "blackout" ? "#6b7280" : w.type === "emergency" ? "#ef4444" : "#3b82f6";

              return (
                <div
                  key={w.id}
                  className="absolute top-2 h-8 rounded cursor-pointer opacity-80 hover:opacity-100 transition-opacity flex items-center px-1.5 overflow-hidden"
                  style={{ left: `${left}%`, width: `${width}%`, backgroundColor: color + "55", border: `1px solid ${color}` }}
                  onMouseEnter={(e) => setTooltip({ x: e.clientX, y: e.clientY, window: w })}
                  onMouseLeave={() => setTooltip(null)}
                >
                  <span className="text-xs text-white font-medium truncate">{w.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-xl text-sm pointer-events-none"
          style={{ left: tooltip.x + 12, top: tooltip.y - 60 }}
        >
          <div className="font-semibold text-white mb-1">{tooltip.window.name}</div>
          <div className="text-neutral-400 text-xs space-y-0.5">
            {tooltip.window.environment && <div>Env: {tooltip.window.environment}</div>}
            {tooltip.window.datacenter && <div>DC: {tooltip.window.datacenter}</div>}
            <div>Type: {tooltip.window.type}</div>
            <div>{(tooltip.window.scheduled_bundles || []).length} bundles</div>
            {tooltip.window.max_risk_score && <div>Max risk: {tooltip.window.max_risk_score}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function ScheduleSkeleton() {
  return (
    <div className="space-y-8">
      {[...Array(2)].map((_, g) => (
        <div key={g}>
          <div className="skeleton h-7 w-40 rounded mb-4" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="skeleton h-52 rounded-xl" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
