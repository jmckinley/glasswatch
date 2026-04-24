"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { bundlesApi } from "@/lib/api";

type TabFilter = "all" | "pending" | "approved" | "in_progress" | "completed";

const STATUS_BADGE: Record<string, string> = {
  draft:       "bg-gray-700 text-gray-300",
  scheduled:   "bg-amber-900/40 text-amber-300 border border-amber-700",
  approved:    "bg-emerald-900/40 text-emerald-300 border border-emerald-700",
  in_progress: "bg-indigo-900/40 text-indigo-300 border border-indigo-700",
  completed:   "bg-gray-700/60 text-gray-400",
  failed:      "bg-red-900/40 text-red-300 border border-red-700",
  cancelled:   "bg-red-900/20 text-red-400 border border-red-800",
};

const RISK_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-900/40 text-red-300",
  HIGH:     "bg-orange-900/40 text-orange-300",
  MEDIUM:   "bg-yellow-900/40 text-yellow-300",
  LOW:      "bg-green-900/40 text-green-300",
};

const TAB_LABELS: Record<TabFilter, string> = {
  all:         "All",
  pending:     "Pending Approval",
  approved:    "Approved",
  in_progress: "In Progress",
  completed:   "Completed",
};

const TAB_STATUS_MAP: Record<TabFilter, string | undefined> = {
  all:         undefined,
  pending:     "scheduled",
  approved:    "approved",
  in_progress: "in_progress",
  completed:   "completed",
};

const STAGES = ["Draft", "Pending", "Approved", "In Progress", "Completed"];

const STATUS_TO_STAGE: Record<string, number> = {
  draft:       0,
  scheduled:   1,
  approved:    2,
  in_progress: 3,
  completed:   4,
  failed:      4,
  cancelled:   4,
};

function BundleStepper({ status }: { status: string }) {
  const currentStage = STATUS_TO_STAGE[status] ?? 0;
  const isCancelled = status === "cancelled" || status === "failed";

  return (
    <div className="flex items-center gap-0.5 mt-1">
      {STAGES.map((stage, i) => {
        const isActive = i === currentStage;
        const isPast = i < currentStage;
        const color = isCancelled && isActive
          ? "bg-red-500"
          : isPast
          ? "bg-emerald-600"
          : isActive
          ? "bg-indigo-500"
          : "bg-gray-700";
        return (
          <div key={stage} className="flex items-center gap-0.5">
            <div
              className={`w-2 h-2 rounded-full flex-shrink-0 ${color}`}
              title={stage}
            />
            {i < STAGES.length - 1 && (
              <div className={`w-4 h-px ${isPast ? "bg-emerald-700" : "bg-gray-700"}`} />
            )}
          </div>
        );
      })}
      <span className="ml-1 text-gray-500 text-xs">{STAGES[currentStage]}</span>
    </div>
  );
}

function SkeletonRow() {
  return (
    <tr className="bg-gray-900 border-b border-gray-700/50">
      {[...Array(7)].map((_, i) => (
        <td key={i} className="px-4 py-4">
          <div className="h-4 bg-gray-700 rounded animate-pulse" style={{ width: i === 0 ? "70%" : i === 6 ? "60px" : "50%" }} />
        </td>
      ))}
    </tr>
  );
}

const BANNER_KEY = "glasswatch_bundles_banner_dismissed";

export default function BundlesPage() {
  const [bundles, setBundles] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabFilter>("all");
  const [bannerDismissed, setBannerDismissed] = useState(true); // start hidden, check localStorage

  useEffect(() => { document.title = 'Patch Bundles | Glasswatch'; }, []);

  useEffect(() => {
    const dismissed = localStorage.getItem(BANNER_KEY);
    if (!dismissed) setBannerDismissed(false);
  }, []);

  const dismissBanner = () => {
    localStorage.setItem(BANNER_KEY, "1");
    setBannerDismissed(true);
  };

  useEffect(() => {
    fetchBundles();
  }, [activeTab]);

  const fetchBundles = async () => {
    setLoading(true);
    try {
      const status = TAB_STATUS_MAP[activeTab];
      const data = await bundlesApi.list(status ? { status } : {});
      setBundles(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to load bundles:", err);
      setBundles([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    });
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Patch Bundles</h1>
          <p className="text-gray-400">
            A bundle groups related patches for coordinated deployment within a maintenance window.
          </p>
        </div>
        <Link
          href="/goals"
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          + New Bundle
        </Link>
      </div>

      {/* Explainer Banner */}
      {!bannerDismissed && (
        <div className="mb-5 flex items-start gap-3 px-4 py-3 bg-indigo-950/50 border border-indigo-800/50 rounded-lg text-sm text-indigo-200">
          <span className="text-base flex-shrink-0">ℹ️</span>
          <span className="flex-1">
            A patch bundle groups related vulnerabilities into a scheduled maintenance window for coordinated remediation.
            Bundles move through: <span className="font-medium">Draft → Pending Approval → Approved → In Progress → Completed</span>.
          </span>
          <button
            onClick={dismissBanner}
            className="flex-shrink-0 text-indigo-400 hover:text-white transition-colors ml-2"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="border-b border-gray-700 mb-6">
        <div className="flex gap-1">
          {(Object.keys(TAB_LABELS) as TabFilter[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab
                  ? "text-indigo-400 border-indigo-400"
                  : "text-gray-400 border-transparent hover:text-gray-300"
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="overflow-x-auto rounded-lg border border-gray-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Risk</th>
                <th className="px-4 py-3 text-left">Items</th>
                <th className="px-4 py-3 text-left">Scheduled For</th>
                <th className="px-4 py-3 text-left">Linked Goal</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </tbody>
          </table>
        </div>
      ) : bundles.length === 0 ? (
        <div className="text-center py-20 bg-gray-800 rounded-lg border border-gray-700">
          <div className="text-5xl mb-4">📦</div>
          <h3 className="text-xl font-semibold text-white mb-2">
            {activeTab === "all"
              ? "No patch bundles yet"
              : `No ${TAB_LABELS[activeTab].toLowerCase()} bundles`}
          </h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">
            {activeTab === "all"
              ? "No patch bundles yet. Create your first bundle to start scheduling remediation work."
              : "Try switching to \"All\" to see every bundle regardless of status."}
          </p>
          {activeTab === "all" && (
            <div className="mt-6 flex justify-center gap-3">
              <Link
                href="/goals"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Create Bundle →
              </Link>
              <Link
                href="/vulnerabilities"
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                Browse Vulnerabilities
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Risk</th>
                <th className="px-4 py-3 text-left">Items</th>
                <th className="px-4 py-3 text-left">Scheduled For</th>
                <th className="px-4 py-3 text-left">Linked Goal</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {bundles.map((bundle) => (
                <tr key={bundle.id} className="bg-gray-900 hover:bg-gray-800 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{bundle.name}</div>
                    {bundle.description && (
                      <div className="text-xs text-gray-500 truncate max-w-xs mt-0.5">{bundle.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${STATUS_BADGE[bundle.status] || "bg-gray-700 text-gray-400"}`}>
                      {bundle.status.replace("_", " ").toUpperCase()}
                    </span>
                    <BundleStepper status={bundle.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {bundle.risk_level && (
                        <span className={`px-2 py-0.5 rounded text-xs ${RISK_BADGE[bundle.risk_level] || "bg-gray-700 text-gray-400"}`}>
                          {bundle.risk_level}
                        </span>
                      )}
                      <span className="text-gray-300">{bundle.risk_score?.toFixed(1) ?? "—"}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {bundle.items_count ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {formatDate(bundle.scheduled_for)}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {bundle.goal_name ? (
                      <span className="text-gray-300">{bundle.goal_name}</span>
                    ) : bundle.goal_id ? (
                      <span className="text-gray-500">Goal linked</span>
                    ) : (
                      <span>—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/bundles/${bundle.id}`}
                      className="px-3 py-1.5 border border-gray-600 hover:border-indigo-500 hover:text-indigo-300 text-gray-300 text-xs font-medium rounded transition-colors"
                    >
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && bundles.length > 0 && (
        <p className="text-xs text-gray-500 mt-3">Showing {bundles.length} of {total} bundles</p>
      )}
    </div>
  );
}
