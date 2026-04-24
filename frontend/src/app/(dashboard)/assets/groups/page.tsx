"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { assetsApi } from "@/lib/api";

interface AssetGroup {
  name: string;
  count: number;
  avg_risk_score: number;
  total_vulns: number;
  patched_vulns: number;
  pct_patched: number;
  asset_ids: string[];
}

const GROUP_BY_OPTIONS = [
  { value: "environment", label: "Environment" },
  { value: "owner_team", label: "Owner Team" },
  { value: "criticality", label: "Criticality" },
  { value: "patch_group", label: "Patch Group" },
];

const RISK_COLOR = (score: number) => {
  if (score >= 80) return "text-red-400";
  if (score >= 60) return "text-orange-400";
  if (score >= 40) return "text-yellow-400";
  return "text-green-400";
};

const RISK_BAR_COLOR = (score: number) => {
  if (score >= 80) return "bg-red-500";
  if (score >= 60) return "bg-orange-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-green-500";
};

const COVERAGE_COLOR = (pct: number) => {
  if (pct >= 80) return "bg-green-500";
  if (pct >= 50) return "bg-orange-500";
  return "bg-red-500";
};

const COVERAGE_TEXT = (pct: number) => {
  if (pct >= 80) return "text-green-400";
  if (pct >= 50) return "text-orange-400";
  return "text-red-400";
};

export default function AssetGroupsPage() {
  const [groups, setGroups] = useState<AssetGroup[]>([]);
  const [groupBy, setGroupBy] = useState("environment");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGroups();
  }, [groupBy]);

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const data = await assetsApi.groups(groupBy);
      setGroups(data.groups || []);
    } catch (err) {
      console.error("Failed to fetch groups:", err);
    } finally {
      setLoading(false);
    }
  };

  const totalAssets = groups.reduce((s, g) => s + g.count, 0);
  const totalVulns = groups.reduce((s, g) => s + g.total_vulns, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Asset Groups</h1>
          <p className="text-gray-400 text-sm mt-1">
            Group and compare assets by dimension to prioritize patching
          </p>
        </div>
        <Link
          href="/assets"
          className="text-blue-400 hover:text-blue-300 text-sm"
        >
          ← All Assets
        </Link>
      </div>

      {/* Group By Selector */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex flex-wrap items-center gap-3">
        <span className="text-sm text-gray-400">Group by:</span>
        <div className="flex gap-2 flex-wrap">
          {GROUP_BY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setGroupBy(opt.value)}
              className={`px-4 py-1.5 text-sm rounded-lg transition-colors border ${
                groupBy === opt.value
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="ml-auto text-xs text-gray-500">
          {totalAssets} assets · {totalVulns} vulnerabilities
        </div>
      </div>

      {/* Summary Stats */}
      {!loading && groups.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-2xl font-bold text-white">{groups.length}</div>
            <div className="text-sm text-gray-400">Groups</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-2xl font-bold text-white">{totalAssets}</div>
            <div className="text-sm text-gray-400">Total Assets</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-2xl font-bold text-orange-400">
              {groups.filter(g => g.avg_risk_score >= 60).length}
            </div>
            <div className="text-sm text-gray-400">High-Risk Groups</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-2xl font-bold text-red-400">
              {groups.filter(g => g.pct_patched < 50 && g.total_vulns > 0).length}
            </div>
            <div className="text-sm text-gray-400">&lt;50% Patched</div>
          </div>
        </div>
      )}

      {/* Groups Grid */}
      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">Loading groups…</div>
      ) : groups.length === 0 ? (
        <div className="text-center py-16 text-gray-500">No data found</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {groups.map(group => (
            <GroupCard
              key={group.name}
              group={group}
              groupByParam={groupBy}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function GroupCard({
  group,
  groupByParam,
}: {
  group: AssetGroup;
  groupByParam: string;
}) {
  const viewHref = `/assets?${groupByParam}=${encodeURIComponent(group.name)}`;

  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 hover:border-gray-600 transition-colors flex flex-col gap-4">
      {/* Title row */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-white font-semibold text-base capitalize">{group.name}</div>
          <div className="text-xs text-gray-500 mt-0.5">
            {group.count} asset{group.count !== 1 ? "s" : ""}
          </div>
        </div>
        <Link
          href={viewHref}
          className="px-3 py-1 text-xs bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-600/30 transition-colors flex-shrink-0"
        >
          View Group →
        </Link>
      </div>

      {/* Risk score */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500">Avg Risk Score</span>
          <span className={`text-sm font-bold ${RISK_COLOR(group.avg_risk_score)}`}>
            {group.avg_risk_score.toFixed(1)}
          </span>
        </div>
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${RISK_BAR_COLOR(group.avg_risk_score)}`}
            style={{ width: `${Math.min(100, group.avg_risk_score)}%` }}
          />
        </div>
      </div>

      {/* Patch coverage */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500">Patch Coverage</span>
          <span className={`text-sm font-bold ${COVERAGE_TEXT(group.pct_patched)}`}>
            {group.total_vulns > 0 ? `${group.pct_patched.toFixed(0)}%` : "N/A"}
          </span>
        </div>
        {group.total_vulns > 0 && (
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${COVERAGE_COLOR(group.pct_patched)}`}
              style={{ width: `${group.pct_patched}%` }}
            />
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="flex justify-between text-xs text-gray-500 border-t border-gray-700 pt-3">
        <span>
          <span className="text-gray-300">{group.total_vulns}</span> total vulns
        </span>
        <span>
          <span className="text-green-400">{group.patched_vulns}</span> patched
        </span>
        <span>
          <span className={group.total_vulns - group.patched_vulns > 0 ? "text-red-400" : "text-gray-400"}>
            {group.total_vulns - group.patched_vulns}
          </span>{" "}
          unpatched
        </span>
      </div>
    </div>
  );
}
