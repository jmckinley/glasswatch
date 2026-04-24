"use client";

import { useEffect, useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuditUser {
  id: string;
  email: string;
  name: string;
}

interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  resource_name: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
  user: AuditUser | null;
}

interface AuditLogResponse {
  logs: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

interface Filters {
  action: string;
  resource_type: string;
  date_from: string;
  date_to: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

const AVATAR_COLORS = [
  "bg-indigo-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-purple-500",
  "bg-blue-500",
  "bg-rose-500",
  "bg-teal-500",
];

function avatarColor(userId: string): string {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) hash = (hash * 31 + userId.charCodeAt(i)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

// Action category → style config
interface ActionStyle {
  icon: string;
  badge: string;
  border: string;
}

function getActionStyle(action: string): ActionStyle {
  if (action.startsWith("bundle."))
    return { icon: "📦", badge: "bg-indigo-900 text-indigo-300 border border-indigo-700", border: "border-indigo-500" };
  if (action.startsWith("vulnerability."))
    return { icon: "🛡️", badge: "bg-amber-900 text-amber-300 border border-amber-700", border: "border-amber-500" };
  if (action.startsWith("user."))
    return { icon: "👤", badge: "bg-emerald-900 text-emerald-300 border border-emerald-700", border: "border-emerald-500" };
  if (action.startsWith("maintenance_window."))
    return { icon: "🗓️", badge: "bg-blue-900 text-blue-300 border border-blue-700", border: "border-blue-500" };
  if (action.startsWith("goal."))
    return { icon: "🎯", badge: "bg-purple-900 text-purple-300 border border-purple-700", border: "border-purple-500" };
  return { icon: "⚙️", badge: "bg-gray-700 text-gray-300 border border-gray-600", border: "border-gray-500" };
}

const RESOURCE_TYPES = [
  "bundle",
  "vulnerability",
  "user",
  "asset",
  "goal",
  "maintenance_window",
  "rule",
];

const ACTION_PREFIXES = [
  "bundle.",
  "vulnerability.",
  "user.",
  "maintenance_window.",
  "goal.",
  "asset.",
  "rule.",
  "system.",
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Skeleton() {
  return (
    <tr className="animate-pulse border-b border-gray-700/50">
      <td className="px-4 py-3"><div className="h-4 bg-gray-700 rounded w-24" /></td>
      <td className="px-4 py-3"><div className="h-6 w-6 bg-gray-700 rounded-full" /></td>
      <td className="px-4 py-3"><div className="h-5 bg-gray-700 rounded w-36" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-700 rounded w-28" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-700 rounded w-20" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-700 rounded w-8" /></td>
    </tr>
  );
}

function FilterPill({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 bg-indigo-900/60 text-indigo-300 border border-indigo-700 text-xs px-2.5 py-1 rounded-full">
      {label}
      <button onClick={onRemove} className="ml-0.5 hover:text-white transition-colors">
        ✕
      </button>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AuditLogPage() {
  const [data, setData] = useState<AuditLogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({ action: "", resource_type: "", date_from: "", date_to: "" });
  const [pendingFilters, setPendingFilters] = useState<Filters>({ action: "", resource_type: "", date_from: "", date_to: "" });
  const [offset, setOffset] = useState(0);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const LIMIT = 50;

  useEffect(() => { document.title = "Audit Log | Glasswatch"; }, []);

  const buildParams = useCallback((f: Filters, off: number) => {
    const p = new URLSearchParams({ limit: String(LIMIT), offset: String(off) });
    if (f.action) p.set("action", f.action);
    if (f.resource_type) p.set("resource_type", f.resource_type);
    if (f.date_from) p.set("since", new Date(f.date_from).toISOString());
    if (f.date_to) p.set("until", new Date(f.date_to + "T23:59:59").toISOString());
    return p;
  }, []);

  const fetchLogs = useCallback(async (f: Filters, off: number) => {
    setLoading(true);
    setError(null);
    try {
      const params = buildParams(f, off);
      const res = await fetch(`/api/v1/audit-log?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: AuditLogResponse = await res.json();
      setData(json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  useEffect(() => {
    fetchLogs(filters, offset);
  }, [filters, offset, fetchLogs]);

  const applyFilters = useCallback(() => {
    setFilters({ ...pendingFilters });
    setOffset(0);
  }, [pendingFilters]);

  const clearFilter = useCallback((key: keyof Filters) => {
    const updated = { ...filters, [key]: "" };
    setPendingFilters(updated);
    setFilters(updated);
    setOffset(0);
  }, [filters]);

  const handleExport = () => {
    const params = buildParams(filters, 0);
    params.set("limit", "5000");
    window.open(`/api/v1/audit-log/export?${params}`);
  };

  const activeFilters = (Object.entries(filters) as [keyof Filters, string][]).filter(([, v]) => v);

  const total = data?.total ?? 0;
  const showing = data ? `${offset + 1}–${Math.min(offset + LIMIT, total)} of ${total.toLocaleString()}` : "—";

  return (
    <div className="min-h-screen bg-gray-900 text-white px-6 py-8 max-w-screen-2xl mx-auto">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <p className="text-gray-400 text-sm mt-1">
            Complete record of all actions in your workspace
            {data ? <span className="ml-1 text-gray-500">· {total.toLocaleString()} events</span> : null}
          </p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-indigo-500 text-indigo-300 text-sm font-medium hover:bg-indigo-900/40 transition-colors"
        >
          ↓ Export CSV
        </button>
      </div>

      {/* ── Filter bar ─────────────────────────────────────────────────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 mb-4 flex flex-wrap gap-3 items-end">
        {/* Action Type */}
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs text-gray-400 mb-1">Action Type</label>
          <select
            value={pendingFilters.action}
            onChange={(e) => setPendingFilters((p) => ({ ...p, action: e.target.value }))}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All actions</option>
            {ACTION_PREFIXES.map((p) => (
              <option key={p} value={p.slice(0, -1)}>{p}</option>
            ))}
          </select>
        </div>

        {/* Resource Type */}
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs text-gray-400 mb-1">Resource Type</label>
          <select
            value={pendingFilters.resource_type}
            onChange={(e) => setPendingFilters((p) => ({ ...p, resource_type: e.target.value }))}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All resources</option>
            {RESOURCE_TYPES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        {/* Date From */}
        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs text-gray-400 mb-1">Date From</label>
          <input
            type="date"
            value={pendingFilters.date_from}
            onChange={(e) => setPendingFilters((p) => ({ ...p, date_from: e.target.value }))}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Date To */}
        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs text-gray-400 mb-1">Date To</label>
          <input
            type="date"
            value={pendingFilters.date_to}
            onChange={(e) => setPendingFilters((p) => ({ ...p, date_to: e.target.value }))}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Apply */}
        <button
          onClick={applyFilters}
          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors"
        >
          Apply
        </button>
      </div>

      {/* ── Active filter pills ─────────────────────────────────────────── */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {activeFilters.map(([key, val]) => (
            <FilterPill
              key={key}
              label={`${key.replace("_", " ")}: ${val}`}
              onRemove={() => clearFilter(key)}
            />
          ))}
          <button
            onClick={() => {
              const empty: Filters = { action: "", resource_type: "", date_from: "", date_to: "" };
              setPendingFilters(empty);
              setFilters(empty);
              setOffset(0);
            }}
            className="text-xs text-gray-400 hover:text-white underline underline-offset-2 transition-colors"
          >
            Clear all
          </button>
        </div>
      )}

      {/* ── Error ──────────────────────────────────────────────────────── */}
      {error && (
        <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-xl px-4 py-3 mb-4 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* ── Table ──────────────────────────────────────────────────────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-750 border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wide">
                <th className="px-4 py-3 text-left font-medium">Timestamp</th>
                <th className="px-4 py-3 text-left font-medium">User</th>
                <th className="px-4 py-3 text-left font-medium">Action</th>
                <th className="px-4 py-3 text-left font-medium">Resource</th>
                <th className="px-4 py-3 text-left font-medium">Details</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />)
              ) : !data || data.logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-24 text-center">
                    <div className="flex flex-col items-center gap-3 text-gray-500">
                      <span className="text-5xl">🔍</span>
                      <p className="text-base font-semibold text-gray-400">No audit events yet</p>
                      <p className="text-sm max-w-xs">
                        Actions in your workspace will appear here for compliance tracking and security investigation.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                data.logs.map((entry) => {
                  const style = getActionStyle(entry.action);
                  const isExpanded = expandedRow === entry.id;
                  return (
                    <>
                      <tr
                        key={entry.id}
                        onClick={() => setExpandedRow(isExpanded ? null : entry.id)}
                        className={`border-b border-gray-700/50 border-l-2 ${style.border} cursor-pointer hover:bg-gray-700/30 transition-colors ${isExpanded ? "bg-gray-700/20" : ""}`}
                      >
                        {/* Timestamp */}
                        <td className="px-4 py-3 text-gray-400 whitespace-nowrap" title={entry.created_at}>
                          {relativeTime(entry.created_at)}
                        </td>

                        {/* User */}
                        <td className="px-4 py-3">
                          {entry.user ? (
                            <div className="flex items-center gap-2" title={entry.user.email}>
                              <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0 ${avatarColor(entry.user.id)}`}>
                                {getInitials(entry.user.name || entry.user.email)}
                              </span>
                              <span className="text-gray-300 text-xs truncate max-w-[100px]">{entry.user.name || entry.user.email}</span>
                            </div>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-700 text-gray-400 text-xs font-mono">SYS</span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${style.badge}`}>
                            <span>{style.icon}</span>
                            {entry.action}
                          </span>
                        </td>

                        {/* Resource */}
                        <td className="px-4 py-3">
                          {entry.resource_type ? (
                            <div className="flex flex-col gap-0.5">
                              <span className="text-gray-300 text-xs font-medium">{entry.resource_type}</span>
                              {entry.resource_name && (
                                <span className="text-gray-500 text-xs truncate max-w-[140px]">{entry.resource_name}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>

                        {/* Details preview */}
                        <td className="px-4 py-3 text-gray-500 text-xs">
                          {Object.keys(entry.details).length > 0 ? (
                            <span className="text-indigo-400 text-xs">
                              {isExpanded ? "▲ hide" : `▼ ${Object.keys(entry.details).length} field${Object.keys(entry.details).length !== 1 ? "s" : ""}`}
                            </span>
                          ) : (
                            <span className="text-gray-700">—</span>
                          )}
                        </td>

                        {/* Status */}
                        <td className="px-4 py-3">
                          {entry.success ? (
                            <span className="text-emerald-400 font-bold text-base" title="Success">✓</span>
                          ) : (
                            <span className="text-red-400 font-bold text-base" title={entry.error_message || "Failed"}>✗</span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded details panel */}
                      {isExpanded && (
                        <tr key={`${entry.id}-details`} className={`border-b border-gray-700/50 border-l-2 ${style.border} bg-gray-900/60`}>
                          <td colSpan={6} className="px-6 py-4">
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                              {Object.entries(entry.details).map(([k, v]) => (
                                <div key={k} className="bg-gray-800 rounded-lg px-3 py-2 border border-gray-700">
                                  <p className="text-xs text-gray-500 font-medium mb-0.5">{k}</p>
                                  <p className="text-xs text-gray-200 break-all">
                                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                                  </p>
                                </div>
                              ))}
                              {entry.ip_address && (
                                <div className="bg-gray-800 rounded-lg px-3 py-2 border border-gray-700">
                                  <p className="text-xs text-gray-500 font-medium mb-0.5">ip_address</p>
                                  <p className="text-xs text-gray-200 font-mono">{entry.ip_address}</p>
                                </div>
                              )}
                              {entry.error_message && (
                                <div className="bg-red-950 rounded-lg px-3 py-2 border border-red-800 col-span-2">
                                  <p className="text-xs text-red-400 font-medium mb-0.5">error</p>
                                  <p className="text-xs text-red-300">{entry.error_message}</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ──────────────────────────────────────────────── */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700 bg-gray-800/50">
            <p className="text-xs text-gray-400">
              Showing <span className="text-white font-medium">{showing}</span> events
              {loading && <span className="ml-2 text-gray-600">loading…</span>}
            </p>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Prev
              </button>
              <button
                disabled={offset + LIMIT >= total}
                onClick={() => setOffset(offset + LIMIT)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
