"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { bundlesApi } from "@/lib/api";

type TabFilter = "all" | "pending" | "approved" | "in_progress" | "completed";

const STATUS_BADGE: Record<string, string> = {
  draft:       "bg-gray-700 text-gray-300",
  scheduled:   "bg-blue-900/40 text-blue-300 border border-blue-700",
  approved:    "bg-green-900/40 text-green-300 border border-green-700",
  in_progress: "bg-yellow-900/40 text-yellow-300 border border-yellow-700",
  completed:   "bg-emerald-900/40 text-emerald-300 border border-emerald-700",
  failed:      "bg-red-900/40 text-red-300 border border-red-700",
  cancelled:   "bg-gray-700 text-gray-400",
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

export default function BundlesPage() {
  const [bundles, setBundles] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabFilter>("all");

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
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Patch Bundles</h1>
        <p className="text-gray-400">Track and manage all patch deployment bundles</p>
      </div>

      {/* Filter Tabs */}
      <div className="border-b border-gray-700 mb-6">
        <div className="flex gap-1">
          {(Object.keys(TAB_LABELS) as TabFilter[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab
                  ? "text-blue-400 border-blue-400"
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
        <div className="text-center py-16">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
          <p className="mt-4 text-gray-400">Loading bundles…</p>
        </div>
      ) : bundles.length === 0 ? (
        <div className="text-center py-16 bg-gray-800 rounded-lg border border-gray-700">
          <p className="text-gray-400 text-lg">No bundles found</p>
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
                <th className="px-4 py-3 text-left">Goal</th>
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
                    {bundle.goal_id ? bundle.goal_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/bundles/${bundle.id}`}
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded transition-colors"
                    >
                      View →
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
