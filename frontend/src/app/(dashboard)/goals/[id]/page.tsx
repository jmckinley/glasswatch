"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { goalsApi } from "@/lib/api";

interface Goal {
  id: string;
  tenant_id: string;
  name: string;
  type: string;
  description: string | null;
  active: boolean;
  progress_percentage: number;
  vulnerabilities_total: number;
  vulnerabilities_addressed: number;
  current_risk_score: number;
  target_risk_score: number | null;
  target_completion_date: string | null;
  risk_tolerance: string;
  max_vulns_per_window: number;
  max_downtime_hours: number;
  require_vendor_approval: boolean;
  min_patch_weather_score: number;
  created_at: string;
  updated_at: string;
}

const TYPE_LABELS: Record<string, string> = {
  compliance_deadline: "Compliance Deadline",
  risk_reduction: "Risk Reduction",
  zero_critical: "Zero Critical",
  kev_elimination: "KEV Elimination",
  custom: "Custom",
};

const TOLERANCE_COLORS: Record<string, string> = {
  conservative: "text-success",
  balanced: "text-secondary",
  aggressive: "text-warning",
};

export default function GoalDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoal();
  }, [id]);

  const fetchGoal = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await goalsApi.get(id);
      setGoal(data);
    } catch (err: any) {
      setError(err.message || "Failed to load goal");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-neutral-400">Loading goal details...</div>
      </div>
    );
  }

  if (error || !goal) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="text-destructive">
          {error || "Goal not found"}
        </div>
        <Link
          href="/"
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const targetDate = goal.target_completion_date
    ? new Date(goal.target_completion_date).toLocaleDateString()
    : "No target date";
  const createdDate = new Date(goal.created_at).toLocaleDateString();
  const patchesRemaining = goal.vulnerabilities_total - goal.vulnerabilities_addressed;
  const progressPct = goal.progress_percentage;

  // Calculate velocity (patches per week)
  const patchesPerWeek = goal.vulnerabilities_addressed > 0 
    ? (goal.vulnerabilities_addressed / 30) * 7 
    : 0;
  const weeksNeeded = patchesPerWeek > 0 
    ? patchesRemaining / patchesPerWeek 
    : Infinity;

  return (
    <div className="space-y-6">
      {/* Back Navigation */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-neutral-400 hover:text-white transition-colors"
      >
        ← Back to Dashboard
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold">{goal.name}</h1>
              <span className="px-3 py-1 bg-primary/20 text-primary rounded-lg text-sm font-medium border border-primary/30">
                {TYPE_LABELS[goal.type] || goal.type}
              </span>
              {!goal.active && (
                <span className="px-3 py-1 bg-neutral-700 text-neutral-400 rounded-lg text-sm font-medium">
                  Inactive
                </span>
              )}
            </div>
            {goal.description && (
              <p className="text-neutral-300 mb-3">{goal.description}</p>
            )}
            <div className="flex items-center gap-4 text-sm text-neutral-400">
              <span>Target: {targetDate}</span>
              <span>•</span>
              <span>Created: {createdDate}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">Overall Progress</div>
          <div className="text-3xl font-bold">{progressPct.toFixed(0)}%</div>
          <div className="mt-2 h-2 bg-neutral-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all"
              style={{ width: `${Math.min(100, progressPct)}%` }}
            />
          </div>
        </div>

        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">Vulnerabilities Addressed</div>
          <div className="text-3xl font-bold">{goal.vulnerabilities_addressed}</div>
          <div className="text-xs text-neutral-500 mt-1">
            of {goal.vulnerabilities_total} total
          </div>
        </div>

        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">Remaining</div>
          <div className="text-3xl font-bold">{patchesRemaining}</div>
          <div className="text-xs text-neutral-500 mt-1">
            vulnerabilities to address
          </div>
        </div>

        <div className="card p-4">
          <div className="text-sm text-neutral-400 mb-1">Current Risk Score</div>
          <div className="text-3xl font-bold">{goal.current_risk_score || 0}</div>
          {goal.target_risk_score !== null && (
            <div className="text-xs text-neutral-500 mt-1">
              Target: {goal.target_risk_score}
            </div>
          )}
        </div>
      </div>

      {/* Velocity & Timeline */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">Velocity</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Patches Per Week</span>
              <span className="font-medium">
                {patchesPerWeek > 0 ? patchesPerWeek.toFixed(1) : "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Estimated Weeks Remaining</span>
              <span className="font-medium">
                {weeksNeeded === Infinity ? "N/A" : weeksNeeded.toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">Configuration</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Risk Tolerance</span>
              <span className={`font-medium ${TOLERANCE_COLORS[goal.risk_tolerance] || "text-white"}`}>
                {goal.risk_tolerance}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Max Vulns/Window</span>
              <span className="font-medium">{goal.max_vulns_per_window}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Max Downtime</span>
              <span className="font-medium">{goal.max_downtime_hours}h</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Min Patch Weather</span>
              <span className="font-medium">{goal.min_patch_weather_score}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-neutral-400">Vendor Approval Required</span>
              <span className="font-medium">
                {goal.require_vendor_approval ? "Yes" : "No"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Link
          href="/"
          className="px-4 py-2 bg-neutral-700 text-white rounded-lg hover:bg-neutral-600 transition-colors"
        >
          Back to Dashboard
        </Link>
        <Link
          href={`/goals/${id}/recommend`}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
        >
          Get Recommendations
        </Link>
        <Link
          href="/schedule"
          className="px-4 py-2 bg-neutral-700 text-white rounded-lg hover:bg-neutral-600 transition-colors"
        >
          View Schedule
        </Link>
      </div>
    </div>
  );
}
