"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { goalsApi } from "@/lib/api";

interface CurrentState {
  total_vulnerabilities: number;
  total_risk_score: number;
  critical_count: number;
  kev_count: number;
}

interface PlanSummary {
  vulnerabilities_scheduled: number;
  bundles_count: number;
  windows_needed: number;
  estimated_completion_days: number;
  total_risk_reduction: number;
  risk_reduction_percentage: number;
  max_vulns_per_window: number;
  avg_bundle_risk: number;
}

interface ScheduleBundle {
  date: string;
  vulnerabilities_count: number;
  risk_reduction: number;
  estimated_duration_hours: number;
  assets_affected: number;
}

interface Plan {
  strategy: string;
  label: string;
  description: string;
  summary: PlanSummary;
  schedule: ScheduleBundle[];
  trade_offs: string[];
  warnings: string[];
}

interface RecommendationResponse {
  goal_id: string;
  goal_name: string;
  current_state: CurrentState;
  plans: Plan[];
  recommendation: string;
  recommendation_reason: string;
}

const STRATEGY_ICONS: Record<string, string> = {
  conservative: "🛡️",
  balanced: "⚖️",
  aggressive: "⚡",
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-destructive/20 text-destructive border-destructive/30",
  HIGH: "bg-warning/20 text-warning border-warning/30",
  MEDIUM: "bg-secondary/20 text-secondary border-secondary/30",
  LOW: "bg-neutral-700 text-neutral-300 border-neutral-600",
};

export default function RecommendPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  useEffect(() => {
    fetchRecommendations();
  }, [id]);

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await goalsApi.recommend(id);
      setData(response);
      // Auto-select the recommended plan
      setSelectedPlan(response.recommendation);
    } catch (err: any) {
      setError(err.message || "Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptPlan = async () => {
    if (!selectedPlan) return;
    
    setShowConfirmModal(false);
    setAccepting(true);
    
    try {
      await goalsApi.optimize(id, { force_reoptimize: true });
      router.push("/schedule");
    } catch (err: any) {
      alert("Failed to accept plan: " + (err.message || "Unknown error"));
    } finally {
      setAccepting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-neutral-400">Generating optimization plans...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="text-destructive">{error || "Failed to load recommendations"}</div>
        <Link
          href={`/goals/${id}`}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
        >
          Back to Goal
        </Link>
      </div>
    );
  }

  const selected = data.plans.find(p => p.strategy === selectedPlan);

  return (
    <div className="space-y-6">
      {/* Back Navigation */}
      <Link
        href={`/goals/${id}`}
        className="inline-flex items-center gap-2 text-neutral-400 hover:text-white transition-colors"
      >
        ← Back to Goal
      </Link>

      {/* Header */}
      <div className="card p-6">
        <h1 className="text-2xl font-bold mb-2">Optimization Recommendations</h1>
        <h2 className="text-xl text-neutral-300 mb-4">{data.goal_name}</h2>
        <div className="flex items-center gap-4 text-sm text-neutral-400">
          <span>{data.current_state.total_vulnerabilities} vulnerabilities</span>
          <span>•</span>
          <span>{Math.round(data.current_state.total_risk_score).toLocaleString()} total risk</span>
          {data.current_state.critical_count > 0 && (
            <>
              <span>•</span>
              <span className="text-destructive">{data.current_state.critical_count} critical</span>
            </>
          )}
          {data.current_state.kev_count > 0 && (
            <>
              <span>•</span>
              <span className="text-warning">{data.current_state.kev_count} KEV-listed</span>
            </>
          )}
        </div>
      </div>

      {/* Plan Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data.plans.map((plan) => {
          const isRecommended = plan.strategy === data.recommendation;
          const isSelected = plan.strategy === selectedPlan;
          
          return (
            <div
              key={plan.strategy}
              className={`card p-6 cursor-pointer transition-all ${
                isSelected
                  ? "ring-2 ring-primary shadow-lg shadow-primary/20"
                  : "hover:ring-1 hover:ring-neutral-600"
              } ${
                isRecommended && !isSelected
                  ? "ring-1 ring-primary/40"
                  : ""
              }`}
              onClick={() => setSelectedPlan(plan.strategy)}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{STRATEGY_ICONS[plan.strategy]}</span>
                  <div>
                    <h3 className="font-bold">{plan.label}</h3>
                    {isRecommended && (
                      <span className="text-xs text-primary font-medium">★ RECOMMENDED</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-neutral-400 mb-4">{plan.description}</p>

              {/* Key Metrics */}
              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-400">Vulnerabilities</span>
                  <span className="font-medium">{plan.summary.vulnerabilities_scheduled}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-400">Windows Needed</span>
                  <span className="font-medium">{plan.summary.windows_needed}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-400">Timeline</span>
                  <span className="font-medium">{plan.summary.estimated_completion_days} days</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-400">Risk Reduction</span>
                  <span className="font-medium text-success">
                    {plan.summary.risk_reduction_percentage.toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedPlan(plan.strategy);
                }}
                className={`w-full py-2 rounded-lg text-sm font-medium transition-colors ${
                  isSelected
                    ? "bg-primary text-white"
                    : "bg-neutral-700 text-neutral-300 hover:bg-neutral-600"
                }`}
              >
                {isSelected ? "Selected" : "View Plan"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Comparison Bars */}
      {selected && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">Plan Comparison</h3>
          <div className="space-y-4">
            {/* Completion Time */}
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-neutral-400">Completion Time (days)</span>
                <span className="text-xs text-neutral-500">Faster →</span>
              </div>
              <div className="space-y-1">
                {data.plans.map((plan) => {
                  const maxDays = Math.max(...data.plans.map(p => p.summary.estimated_completion_days));
                  const width = (plan.summary.estimated_completion_days / maxDays) * 100;
                  
                  return (
                    <div key={plan.strategy} className="flex items-center gap-2">
                      <span className="text-xs w-24 text-neutral-400">{plan.label}</span>
                      <div className="flex-1 h-6 bg-neutral-800 rounded overflow-hidden">
                        <div
                          className={`h-full flex items-center px-2 text-xs ${
                            plan.strategy === selectedPlan
                              ? "bg-primary"
                              : "bg-neutral-700"
                          }`}
                          style={{ width: `${width}%` }}
                        >
                          {plan.summary.estimated_completion_days} days
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Risk Reduction */}
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-neutral-400">Risk Reduction (%)</span>
                <span className="text-xs text-neutral-500">Better →</span>
              </div>
              <div className="space-y-1">
                {data.plans.map((plan) => {
                  const width = plan.summary.risk_reduction_percentage;
                  
                  return (
                    <div key={plan.strategy} className="flex items-center gap-2">
                      <span className="text-xs w-24 text-neutral-400">{plan.label}</span>
                      <div className="flex-1 h-6 bg-neutral-800 rounded overflow-hidden">
                        <div
                          className={`h-full flex items-center px-2 text-xs ${
                            plan.strategy === selectedPlan
                              ? "bg-success"
                              : "bg-neutral-700"
                          }`}
                          style={{ width: `${Math.min(100, width)}%` }}
                        >
                          {width.toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Plan Detail */}
      {selected && (
        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">
                {STRATEGY_ICONS[selected.strategy]} {selected.label} — Detailed Schedule
              </h3>
              {data.recommendation === selected.strategy && (
                <p className="text-sm text-primary">{data.recommendation_reason}</p>
              )}
            </div>
          </div>

          {/* Schedule */}
          <div className="space-y-3 mb-6">
            <h4 className="text-sm font-medium text-neutral-400">Deployment Schedule</h4>
            {selected.schedule.map((bundle, idx) => (
              <div
                key={idx}
                className="border border-neutral-700 rounded-lg p-4 hover:border-neutral-600 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium">
                      Bundle {idx + 1}: Week of {new Date(bundle.date).toLocaleDateString()}
                    </div>
                    <div className="text-sm text-neutral-400 mt-1">
                      {bundle.vulnerabilities_count} vulnerabilities • {bundle.assets_affected} assets affected
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-success">
                      -{Math.round(bundle.risk_reduction).toLocaleString()} risk
                    </div>
                    <div className="text-xs text-neutral-500">
                      ~{bundle.estimated_duration_hours.toFixed(1)}h
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Trade-offs */}
          <div className="mb-6">
            <h4 className="text-sm font-medium text-neutral-400 mb-2">Trade-offs</h4>
            <ul className="space-y-1">
              {selected.trade_offs.map((tradeOff, idx) => (
                <li key={idx} className="text-sm text-neutral-300 flex items-start gap-2">
                  <span className="text-neutral-500">•</span>
                  <span>{tradeOff}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Warnings */}
          {selected.warnings.length > 0 && (
            <div className="mb-6 p-4 bg-warning/10 border border-warning/30 rounded-lg">
              <h4 className="text-sm font-medium text-warning mb-2">Warnings</h4>
              <ul className="space-y-1">
                {selected.warnings.map((warning, idx) => (
                  <li key={idx} className="text-sm text-warning/90 flex items-start gap-2">
                    <span>⚠️</span>
                    <span>{warning}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => setShowConfirmModal(true)}
              disabled={accepting}
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {accepting ? "Creating Bundles..." : "✅ Accept This Plan"}
            </button>
            <Link
              href={`/goals/${id}`}
              className="px-6 py-2 bg-neutral-700 text-white rounded-lg hover:bg-neutral-600 transition-colors"
            >
              ❌ Dismiss
            </Link>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold mb-4">Confirm Plan Acceptance</h3>
            <p className="text-neutral-300 mb-4">
              This will create {selected.summary.bundles_count} patch bundles and schedule them
              across {selected.summary.windows_needed} maintenance windows.
            </p>
            <p className="text-sm text-neutral-400 mb-6">
              The bundles will be created in draft status and you can review them on the schedule page.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleAcceptPlan}
                className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
              >
                Proceed
              </button>
              <button
                onClick={() => setShowConfirmModal(false)}
                className="flex-1 px-4 py-2 bg-neutral-700 text-white rounded-lg hover:bg-neutral-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
