"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { bundlesApi, vulnerabilitiesApi, maintenanceWindowsApi } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

interface BundleItem {
  id: string;
  vulnerability_id: string;
  asset_id: string;
  status: string;
  risk_score: number;
  priority: number | null;
  patch_identifier: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  rollback_performed: boolean;
  rollback_at: string | null;
  error_message: string | null;
  notes: string | null;
  vulnerability?: { id: string; identifier: string; severity: string; description: string; title?: string };
  asset?: { id: string; name: string; identifier: string; type: string; criticality: number };
}

interface Bundle {
  id: string;
  name: string;
  description: string | null;
  status: string;
  risk_score: number;
  risk_level: string | null;
  scheduled_for: string | null;
  maintenance_window_id: string | null;
  estimated_duration_minutes: number | null;
  actual_duration_minutes: number | null;
  assets_affected_count: number;
  approval_required: boolean;
  approved_by: string | null;
  approved_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  success_count: number | null;
  failure_count: number | null;
  rollback_count: number | null;
  goal_id: string | null;
  items?: BundleItem[];
  items_count?: number;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, string> = {
  draft:       "bg-gray-700 text-gray-300",
  scheduled:   "bg-blue-900/40 text-blue-300 border border-blue-700",
  approved:    "bg-green-900/40 text-green-300 border border-green-700",
  in_progress: "bg-yellow-900/40 text-yellow-300 border border-yellow-700",
  completed:   "bg-emerald-900/40 text-emerald-300 border border-emerald-700",
  failed:      "bg-red-900/40 text-red-300 border border-red-700",
  cancelled:   "bg-gray-700 text-gray-400",
};

const ITEM_STATUS_BADGE: Record<string, string> = {
  pending:     "bg-gray-700 text-gray-300",
  in_progress: "bg-yellow-900/40 text-yellow-300",
  success:     "bg-emerald-900/40 text-emerald-300",
  failed:      "bg-red-900/40 text-red-300",
  rolled_back: "bg-purple-900/40 text-purple-300",
  skipped:     "bg-gray-700 text-gray-400",
};

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-900/40 text-red-300 border border-red-700",
  HIGH:     "bg-orange-900/40 text-orange-300 border border-orange-700",
  MEDIUM:   "bg-yellow-900/40 text-yellow-300 border border-yellow-700",
  LOW:      "bg-green-900/40 text-green-300 border border-green-700",
};

const LOG_LEVEL_COLOR: Record<string, string> = {
  info:  "text-blue-400",
  warn:  "text-yellow-400",
  error: "text-red-400",
  debug: "text-gray-500",
};

const TIMELINE_STEPS = ["draft", "scheduled", "approved", "in_progress", "completed"];

const EDITABLE_STATUSES = ["draft", "scheduled", "approved"];

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function BundleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [items, setItems] = useState<BundleItem[]>([]);
  const [execLog, setExecLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [logExpanded, setLogExpanded] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [confirmRollback, setConfirmRollback] = useState(false);

  const fetchBundle = useCallback(async () => {
    try {
      const [bundleData, itemsData, logData] = await Promise.all([
        bundlesApi.get(id),
        bundlesApi.getItems(id),
        bundlesApi.getExecutionLog(id),
      ]);
      setBundle(bundleData);
      setItems(itemsData.items || []);
      setExecLog(logData.entries || []);
    } catch (err: any) {
      setError(err.message || "Failed to load bundle");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchBundle(); }, [fetchBundle]);

  // Poll while in_progress
  useEffect(() => {
    if (bundle?.status !== "in_progress") return;
    const timer = setInterval(fetchBundle, 5000);
    return () => clearInterval(timer);
  }, [bundle?.status, fetchBundle]);

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await bundlesApi.approve(id);
      await fetchBundle();
    } catch (err: any) {
      alert(err.message || "Failed to approve bundle");
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecute = async () => {
    setActionLoading(true);
    try {
      await bundlesApi.execute(id);
      await fetchBundle();
    } catch (err: any) {
      alert(err.message || "Failed to execute bundle");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRollback = async () => {
    setConfirmRollback(false);
    setActionLoading(true);
    try {
      await bundlesApi.rollback(id);
      await fetchBundle();
    } catch (err: any) {
      alert(err.message || "Failed to rollback bundle");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !bundle) {
    return (
      <div className="text-center py-16">
        <p className="text-red-400 mb-4">{error || "Bundle not found"}</p>
        <Link href="/bundles" className="text-blue-400 hover:underline">← Back to Bundles</Link>
      </div>
    );
  }

  const totalItems = items.length;
  const successCount = items.filter(i => i.status === "success").length;
  const progressPct = totalItems > 0 ? Math.round((successCount / totalItems) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Back nav */}
      <Link href="/bundles" className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm">
        ← Back to Bundles
      </Link>

      {/* Edit mode overlay */}
      {editMode && (
        <EditPanel
          bundle={bundle}
          items={items}
          onClose={() => setEditMode(false)}
          onSaved={() => { setEditMode(false); fetchBundle(); }}
          bundleId={id}
        />
      )}

      {/* Header */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-2">
              <h1 className="text-2xl font-bold text-white truncate">{bundle.name}</h1>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_BADGE[bundle.status] || "bg-gray-700 text-gray-400"}`}>
                {bundle.status.replace("_", " ").toUpperCase()}
              </span>
              {bundle.risk_level && (
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                  bundle.risk_level === "CRITICAL" ? "bg-red-900/40 text-red-300" :
                  bundle.risk_level === "HIGH"     ? "bg-orange-900/40 text-orange-300" :
                  bundle.risk_level === "MEDIUM"   ? "bg-yellow-900/40 text-yellow-300" :
                  "bg-green-900/40 text-green-300"
                }`}>
                  {bundle.risk_level} RISK
                </span>
              )}
            </div>
            {bundle.description && <p className="text-gray-400 text-sm">{bundle.description}</p>}
            <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-400">
              {bundle.scheduled_for && (
                <span>📅 {new Date(bundle.scheduled_for).toLocaleString()}</span>
              )}
              {bundle.estimated_duration_minutes && (
                <span>⏱ ~{bundle.estimated_duration_minutes} min estimated</span>
              )}
              {bundle.actual_duration_minutes && (
                <span>✅ {bundle.actual_duration_minutes} min actual</span>
              )}
              <span>🎯 Risk score: <strong className="text-white">{bundle.risk_score.toFixed(1)}</strong></span>
              <span>📦 {totalItems} items</span>
            </div>
          </div>
          {/* Edit button */}
          {EDITABLE_STATUSES.includes(bundle.status) && !editMode && (
            <button
              onClick={() => setEditMode(true)}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors flex items-center gap-2 shrink-0"
            >
              ✏️ Edit Bundle
            </button>
          )}
        </div>
      </div>

      {/* Status Timeline */}
      <StatusTimeline status={bundle.status} />

      {/* Pre-flight Checklist (before approved/execute) */}
      {(bundle.status === "draft" || bundle.status === "scheduled") && (
        <PreflightChecklist bundle={bundle} itemCount={totalItems} />
      )}

      {/* Action Bar */}
      <ActionBar
        bundle={bundle}
        items={items}
        progressPct={progressPct}
        successCount={successCount}
        totalItems={totalItems}
        actionLoading={actionLoading}
        onApprove={handleApprove}
        onExecute={handleExecute}
        onRollback={() => setConfirmRollback(true)}
      />

      {/* Patch Items Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <div className="px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">Patch Items</h2>
        </div>
        <PatchItemsTable items={items} />
      </div>

      {/* Execution Log */}
      <div className="bg-gray-800 rounded-lg border border-gray-700">
        <button
          onClick={() => setLogExpanded(!logExpanded)}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-700/50 transition-colors"
        >
          <h2 className="text-lg font-semibold text-white">
            Execution Log
            <span className="ml-2 text-xs text-gray-500 font-normal">{execLog.length} entries</span>
          </h2>
          <span className="text-gray-400 text-lg">{logExpanded ? "▲" : "▼"}</span>
        </button>
        {logExpanded && <ExecutionLog entries={execLog} />}
      </div>

      {/* Risk Delta (if completed) */}
      {bundle.status === "completed" && (
        <RiskDeltaSection bundle={bundle} items={items} />
      )}

      {/* Rollback confirm modal */}
      {confirmRollback && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white mb-3">⚠️ Confirm Rollback</h3>
            <p className="text-gray-300 mb-6">
              This will mark all in-progress and successful items as <strong>rolled back</strong> and set the bundle status to <strong>failed</strong>. This cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmRollback(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg">
                Cancel
              </button>
              <button onClick={handleRollback} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium">
                Yes, Rollback
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Status Timeline ──────────────────────────────────────────────────────────

function StatusTimeline({ status }: { status: string }) {
  const steps = TIMELINE_STEPS;
  const currentIdx = status === "failed" ? steps.indexOf("in_progress") : steps.indexOf(status);
  const isFailed = status === "failed";

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 px-6 py-5">
      <div className="flex items-center justify-between relative">
        {/* Connector line */}
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-gray-700 z-0 mx-8" />
        {steps.map((step, idx) => {
          const isPast    = idx < currentIdx;
          const isCurrent = idx === currentIdx;
          const isFuture  = idx > currentIdx;
          return (
            <div key={step} className="flex flex-col items-center z-10 flex-1">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${
                isCurrent && isFailed ? "bg-red-600 border-red-500 text-white" :
                isCurrent            ? "bg-blue-600 border-blue-500 text-white" :
                isPast               ? "bg-emerald-600 border-emerald-500 text-white" :
                "bg-gray-700 border-gray-600 text-gray-500"
              }`}>
                {isCurrent && isFailed ? "✗" : isPast ? "✓" : idx + 1}
              </div>
              <div className={`mt-2 text-xs font-medium capitalize text-center ${
                isCurrent && isFailed ? "text-red-400" :
                isCurrent            ? "text-blue-400" :
                isPast               ? "text-emerald-400" :
                "text-gray-500"
              }`}>
                {step.replace("_", " ")}
              </div>
            </div>
          );
        })}
      </div>
      {isFailed && (
        <p className="text-center text-red-400 text-xs mt-3">Bundle execution failed</p>
      )}
    </div>
  );
}

// ─── Pre-flight Checklist ─────────────────────────────────────────────────────

function PreflightChecklist({ bundle, itemCount }: { bundle: Bundle; itemCount: number }) {
  const checks = [
    {
      label: "Maintenance window assigned",
      pass: !!bundle.maintenance_window_id,
      warn: "Bundle should be assigned to a maintenance window before execution",
    },
    {
      label: "Items in bundle",
      pass: itemCount > 0,
      warn: "Bundle has no patch items",
    },
    {
      label: "Approval status",
      pass: bundle.status === "approved" || !bundle.approval_required,
      warn: "Bundle requires approval before execution",
    },
    {
      label: "Estimated duration set",
      pass: !!bundle.estimated_duration_minutes,
      warn: "No estimated duration — verify it fits in the maintenance window",
    },
  ];

  const allGood = checks.every(c => c.pass);

  return (
    <div className={`rounded-lg border p-5 ${allGood ? "bg-emerald-900/20 border-emerald-800" : "bg-yellow-900/20 border-yellow-800"}`}>
      <h2 className="text-sm font-semibold text-white mb-3">
        {allGood ? "✅ Pre-flight Checklist" : "⚠️ Pre-flight Checklist"}
      </h2>
      <div className="space-y-2">
        {checks.map((c) => (
          <div key={c.label} className="flex items-start gap-3 text-sm">
            <span className={c.pass ? "text-emerald-400" : "text-yellow-400"}>{c.pass ? "✓" : "✗"}</span>
            <div>
              <span className={c.pass ? "text-gray-300" : "text-yellow-200"}>{c.label}</span>
              {!c.pass && <p className="text-xs text-yellow-400 mt-0.5">{c.warn}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Action Bar ───────────────────────────────────────────────────────────────

function ActionBar({
  bundle, items, progressPct, successCount, totalItems,
  actionLoading, onApprove, onExecute, onRollback,
}: {
  bundle: Bundle;
  items: BundleItem[];
  progressPct: number;
  successCount: number;
  totalItems: number;
  actionLoading: boolean;
  onApprove: () => void;
  onExecute: () => void;
  onRollback: () => void;
}) {
  const { status } = bundle;

  if (status === "in_progress") {
    return (
      <div className="bg-gray-800 rounded-lg border border-yellow-700 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-yellow-400" />
            <span className="text-yellow-300 font-medium">Executing…</span>
          </div>
          <button onClick={onRollback} disabled={actionLoading}
            className="px-4 py-2 border border-red-600 text-red-400 hover:bg-red-900/30 rounded-lg text-sm disabled:opacity-50">
            Force Rollback
          </button>
        </div>
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{successCount} / {totalItems} patches applied</span>
            <span>{progressPct}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      </div>
    );
  }

  if (status === "approved") {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-5 flex flex-wrap gap-3">
        <button onClick={onExecute} disabled={actionLoading}
          className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg disabled:opacity-50 flex items-center gap-2">
          {actionLoading ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> : "▶"}
          Execute Now
        </button>
        <button onClick={onRollback} disabled={actionLoading}
          className="px-4 py-2.5 border border-red-600 text-red-400 hover:bg-red-900/30 rounded-lg disabled:opacity-50">
          Rollback
        </button>
      </div>
    );
  }

  if (status === "draft" || status === "scheduled") {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-5 flex flex-wrap gap-3">
        <button onClick={onApprove} disabled={actionLoading}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg disabled:opacity-50 flex items-center gap-2">
          {actionLoading ? <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> : "✓"}
          Approve Bundle
        </button>
        <Link href="/bundles"
          className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">
          Cancel
        </Link>
      </div>
    );
  }

  if (status === "failed") {
    const failedItems = items.filter(i => i.status === "failed");
    return (
      <div className="bg-red-900/20 rounded-lg border border-red-700 p-5">
        <p className="text-red-300 font-medium mb-3">
          ⚠️ Bundle failed — {failedItems.length} item(s) failed
        </p>
        <button onClick={onExecute} disabled={actionLoading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm disabled:opacity-50">
          Retry Execution
        </button>
      </div>
    );
  }

  if (status === "completed") {
    return (
      <div className="bg-emerald-900/20 rounded-lg border border-emerald-700 p-5">
        <p className="text-emerald-300 font-medium">
          ✅ Bundle completed — {bundle.success_count ?? successCount} patches applied successfully
          {(bundle.failure_count ?? 0) > 0 && (
            <span className="text-yellow-300 ml-2">({bundle.failure_count} failed)</span>
          )}
        </p>
      </div>
    );
  }

  return null;
}

// ─── Patch Items Table ────────────────────────────────────────────────────────

function PatchItemsTable({ items }: { items: BundleItem[] }) {
  if (items.length === 0) {
    return <p className="text-gray-500 text-sm px-6 py-8 text-center">No patch items in this bundle.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-900/50 border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
            <th className="px-4 py-3 text-left">Asset</th>
            <th className="px-4 py-3 text-left">CVE / Patch</th>
            <th className="px-4 py-3 text-left">Severity</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">Duration</th>
            <th className="px-4 py-3 text-left">Started</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/50">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-gray-700/30 transition-colors">
              <td className="px-4 py-3">
                <div className="text-white font-medium">{item.asset?.name ?? "—"}</div>
                <div className="text-xs text-gray-500">{item.asset?.identifier}</div>
              </td>
              <td className="px-4 py-3">
                <div className="text-blue-300 font-mono text-xs">{item.vulnerability?.identifier ?? item.patch_identifier ?? "—"}</div>
                {item.vulnerability?.title && (
                  <div className="text-xs text-gray-500 truncate max-w-48">{item.vulnerability.title}</div>
                )}
              </td>
              <td className="px-4 py-3">
                {item.vulnerability?.severity ? (
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${SEVERITY_BADGE[item.vulnerability.severity] || "bg-gray-700 text-gray-400"}`}>
                    {item.vulnerability.severity}
                  </span>
                ) : "—"}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${ITEM_STATUS_BADGE[item.status] || "bg-gray-700 text-gray-400"}`}>
                    {item.status.replace("_", " ")}
                  </span>
                  {item.rollback_performed && (
                    <span className="text-xs text-purple-400">↩ rolled back</span>
                  )}
                </div>
                {item.error_message && (
                  <div className="text-xs text-red-400 mt-1 truncate max-w-48">{item.error_message}</div>
                )}
              </td>
              <td className="px-4 py-3 text-gray-400 text-xs">
                {item.duration_seconds != null ? `${item.duration_seconds}s` : "—"}
              </td>
              <td className="px-4 py-3 text-gray-400 text-xs">
                {item.started_at ? new Date(item.started_at).toLocaleTimeString() : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Execution Log ────────────────────────────────────────────────────────────

function ExecutionLog({ entries }: { entries: any[] }) {
  if (entries.length === 0) {
    return <p className="text-gray-500 text-sm px-6 py-6 text-center">No execution log entries.</p>;
  }

  return (
    <div className="px-6 pb-4 font-mono text-xs space-y-1.5 max-h-72 overflow-y-auto">
      {entries.map((entry, idx) => (
        <div key={idx} className="flex gap-3">
          <span className="text-gray-600 shrink-0">
            {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : `#${idx + 1}`}
          </span>
          <span className={`shrink-0 uppercase w-10 ${LOG_LEVEL_COLOR[entry.level] || "text-gray-400"}`}>
            {entry.level || "info"}
          </span>
          <span className="text-gray-300 break-all">{entry.message}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Risk Delta ───────────────────────────────────────────────────────────────

function RiskDeltaSection({ bundle, items }: { bundle: Bundle; items: BundleItem[] }) {
  const successItems = items.filter(i => i.status === "success");
  const reducedRisk = successItems.reduce((s, i) => s + i.risk_score, 0);
  const originalRisk = bundle.risk_score;
  const pct = originalRisk > 0 ? Math.round((reducedRisk / originalRisk) * 100) : 0;

  return (
    <div className="bg-gray-800 rounded-lg border border-emerald-700 p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Risk Delta</h2>
      <div className="grid grid-cols-3 gap-6 text-center">
        <div>
          <div className="text-2xl font-bold text-red-300">{originalRisk.toFixed(1)}</div>
          <div className="text-xs text-gray-400 mt-1">Risk before</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-emerald-400">-{reducedRisk.toFixed(1)}</div>
          <div className="text-xs text-gray-400 mt-1">Risk removed</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-blue-300">{pct}%</div>
          <div className="text-xs text-gray-400 mt-1">Reduction</div>
        </div>
      </div>
      {bundle.success_count != null && (
        <p className="text-sm text-gray-400 mt-4 text-center">
          {bundle.success_count} patches applied • {bundle.failure_count ?? 0} failed • {bundle.rollback_count ?? 0} rolled back
        </p>
      )}
    </div>
  );
}

// ─── Edit Panel ───────────────────────────────────────────────────────────────

function EditPanel({
  bundle, items, onClose, onSaved, bundleId,
}: {
  bundle: Bundle;
  items: BundleItem[];
  onClose: () => void;
  onSaved: () => void;
  bundleId: string;
}) {
  const [tab, setTab] = useState<"details" | "items">("details");
  const [saving, setSaving] = useState(false);

  // Details form state
  const [name, setName] = useState(bundle.name);
  const [description, setDescription] = useState(bundle.description ?? "");
  const [scheduledFor, setScheduledFor] = useState(
    bundle.scheduled_for ? bundle.scheduled_for.slice(0, 16) : ""
  );
  const [riskLevel, setRiskLevel] = useState(bundle.risk_level ?? "");
  const [windows, setWindows] = useState<any[]>([]);

  // Items state
  const [localItems, setLocalItems] = useState<BundleItem[]>(items);
  const [vulnSearch, setVulnSearch] = useState("");
  const [vulnResults, setVulnResults] = useState<any[]>([]);
  const [searchingVuln, setSearchingVuln] = useState(false);
  const [selectedVuln, setSelectedVuln] = useState<any | null>(null);
  const [assetId, setAssetId] = useState("");

  useEffect(() => {
    maintenanceWindowsApi.list({ limit: 50 } as any).then((d) => setWindows(d.items || [])).catch(() => {});
  }, []);

  const handleSaveDetails = async () => {
    setSaving(true);
    setEditError(null);
    try {
      await bundlesApi.update(bundleId, {
        name,
        description: description || null,
        scheduled_for: scheduledFor || null,
        risk_level: riskLevel || null,
      });
      onSaved();
    } catch (err: any) {
      setEditError(err.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const searchVulns = async (q: string) => {
    if (q.length < 2) { setVulnResults([]); return; }
    setSearchingVuln(true);
    try {
      const data = await vulnerabilitiesApi.list({ search: q, limit: 10 } as any);
      const existing = new Set(localItems.map(i => i.vulnerability_id));
      setVulnResults((data.vulnerabilities || data.items || []).filter((v: any) => !existing.has(v.id)));
    } catch {
      setVulnResults([]);
    } finally {
      setSearchingVuln(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => searchVulns(vulnSearch), 300);
    return () => clearTimeout(t);
  }, [vulnSearch]);

  const handleRemoveItem = async (itemId: string) => {
    try {
      await bundlesApi.removeItem(bundleId, itemId);
      setLocalItems(prev => prev.filter(i => i.id !== itemId));
    } catch (err: any) {
      setEditError(err.message || "Failed to remove item");
    }
  };

  const handleAddItem = async () => {
    if (!selectedVuln || !assetId.trim()) {
      setEditError("Select a vulnerability and enter an asset ID.");
      return;
    }
    try {
      const newItem = await bundlesApi.addItem(bundleId, {
        vulnerability_id: selectedVuln.id,
        asset_id: assetId.trim(),
        risk_score: selectedVuln.cvss_score || 0,
      });
      setLocalItems(prev => [...prev, newItem]);
      setSelectedVuln(null);
      setVulnSearch("");
      setVulnResults([]);
      setAssetId("");
      setEditError(null);
    } catch (err: any) {
      setEditError(err.message || "Failed to add item");
    }
  };

  const moveItem = async (itemId: string, direction: "up" | "down") => {
    const idx = localItems.findIndex(i => i.id === itemId);
    if (idx === -1) return;
    const newItems = [...localItems];
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= newItems.length) return;
    [newItems[idx], newItems[swapIdx]] = [newItems[swapIdx], newItems[idx]];
    setLocalItems(newItems);
    // Update priorities
    try {
      await Promise.all(newItems.map((item, i) => bundlesApi.updateItem(bundleId, item.id, { priority: i + 1 })));
    } catch {/* best-effort */}
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-xl border border-gray-700 w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-white">Edit Bundle</h2>
            {bundle.status === "approved" && (
              <p className="text-yellow-400 text-xs mt-1">
                ⚠️ Editing will reset approval status to draft
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl leading-none">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700 px-6">
          {(["details", "items"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 px-4 text-sm font-medium border-b-2 transition-colors capitalize ${
                tab === t ? "text-blue-400 border-blue-400" : "text-gray-400 border-transparent hover:text-gray-300"
              }`}
            >
              {t === "details" ? "Details" : `Patch Items (${localItems.length})`}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {editError && (
            <div className="mb-4 bg-red-900/20 border border-red-700 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
              <span>⚠</span> {editError}
              <button onClick={() => setEditError(null)} aria-label="Dismiss" className="ml-auto hover:text-white">×</button>
            </div>
          )}
          {tab === "details" && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Bundle Name *</label>
                <input
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Scheduled For</label>
                <input
                  type="datetime-local"
                  value={scheduledFor}
                  onChange={e => setScheduledFor(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Risk Tolerance</label>
                <select
                  value={riskLevel}
                  onChange={e => setRiskLevel(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">— Select —</option>
                  <option value="LOW">Conservative (Low risk only)</option>
                  <option value="MEDIUM">Balanced (Medium &amp; below)</option>
                  <option value="HIGH">Aggressive (High &amp; below)</option>
                  <option value="CRITICAL">All Severities</option>
                </select>
              </div>
            </div>
          )}

          {tab === "items" && (
            <div className="space-y-4">
              {/* Current items */}
              {localItems.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-4">No items. Add vulnerabilities below.</p>
              ) : (
                <div className="space-y-2">
                  {localItems.map((item, idx) => (
                    <div key={item.id} className="flex items-center gap-3 bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
                      <div className="flex flex-col gap-1">
                        <button onClick={() => moveItem(item.id, "up")} disabled={idx === 0}
                          className="text-gray-500 hover:text-white disabled:opacity-20 text-xs leading-none">▲</button>
                        <button onClick={() => moveItem(item.id, "down")} disabled={idx === localItems.length - 1}
                          className="text-gray-500 hover:text-white disabled:opacity-20 text-xs leading-none">▼</button>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-blue-300 font-mono text-xs">{item.vulnerability?.identifier ?? item.vulnerability_id.slice(0, 8)}</span>
                          {item.vulnerability?.severity && (
                            <span className={`px-1.5 py-0.5 rounded text-xs ${SEVERITY_BADGE[item.vulnerability.severity] || "bg-gray-700 text-gray-400"}`}>
                              {item.vulnerability.severity}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">{item.asset?.name ?? item.asset_id.slice(0, 8)}</div>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs ${ITEM_STATUS_BADGE[item.status] || "bg-gray-700 text-gray-400"}`}>
                        {item.status}
                      </span>
                      <button onClick={() => handleRemoveItem(item.id)}
                        className="text-red-400 hover:text-red-300 transition-colors text-sm ml-1">✕</button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add vulnerability */}
              <div className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
                <p className="text-sm font-medium text-gray-300 mb-3">Add Vulnerability</p>
                <div className="relative mb-3">
                  <input
                    value={vulnSearch}
                    onChange={e => setVulnSearch(e.target.value)}
                    placeholder="Search by CVE ID or title…"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  {searchingVuln && <span className="absolute right-3 top-2.5 text-gray-500 text-xs">searching…</span>}
                </div>

                {vulnResults.length > 0 && !selectedVuln && (
                  <div className="border border-gray-600 rounded-lg overflow-hidden mb-3 max-h-48 overflow-y-auto">
                    {vulnResults.map(v => (
                      <button
                        key={v.id}
                        onClick={() => { setSelectedVuln(v); setVulnSearch(v.identifier); setVulnResults([]); }}
                        className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-700 text-left border-b border-gray-700 last:border-0"
                      >
                        <span className={`px-1.5 py-0.5 rounded text-xs shrink-0 ${SEVERITY_BADGE[v.severity] || "bg-gray-700 text-gray-400"}`}>
                          {v.severity}
                        </span>
                        <span className="text-blue-300 font-mono text-xs shrink-0">{v.identifier}</span>
                        <span className="text-gray-400 text-xs truncate">{v.title || v.description}</span>
                      </button>
                    ))}
                  </div>
                )}

                {selectedVuln && (
                  <div className="bg-blue-900/20 border border-blue-700 rounded-lg px-3 py-2 mb-3 flex items-center justify-between">
                    <span className="text-blue-300 text-sm">{selectedVuln.identifier}</span>
                    <button onClick={() => { setSelectedVuln(null); setVulnSearch(""); }} className="text-gray-400 hover:text-white text-xs">✕</button>
                  </div>
                )}

                <div className="flex gap-2">
                  <input
                    value={assetId}
                    onChange={e => setAssetId(e.target.value)}
                    placeholder="Asset ID (UUID)"
                    className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <button
                    onClick={handleAddItem}
                    disabled={!selectedVuln || !assetId.trim()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-50"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-700">
          <button onClick={onClose} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">
            Cancel
          </button>
          {tab === "details" && (
            <button onClick={handleSaveDetails} disabled={saving || !name.trim()}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm disabled:opacity-50 flex items-center gap-2">
              {saving && <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
              Save Changes
            </button>
          )}
          {tab === "items" && (
            <button onClick={onSaved} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg text-sm">
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
