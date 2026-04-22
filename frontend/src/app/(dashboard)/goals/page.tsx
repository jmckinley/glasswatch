"use client";

import { useState, useEffect } from "react";
import { goalsApi } from "@/lib/api";
import TagAutocomplete from "@/components/TagAutocomplete";

interface Goal {
  id: string;
  name: string;
  type: string;
  active: boolean;
  progress_percentage: number;
  vulnerabilities_total: number;
  vulnerabilities_addressed: number;
  risk_score_initial: number;
  risk_score_current: number;
  target_date: string | null;
  risk_tolerance: string;
  created_at: string;
  next_bundle_date: string | null;
  estimated_completion_date: string | null;
}

const GOAL_TYPE_LABELS: Record<string, string> = {
  compliance_deadline: "Compliance Deadline",
  risk_reduction: "Risk Reduction",
  zero_critical: "Zero Critical",
  kev_elimination: "KEV Elimination",
  custom: "Custom",
};

const RISK_TOLERANCE_COLORS: Record<string, string> = {
  conservative: "text-success",
  balanced: "text-secondary",
  aggressive: "text-warning",
};

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    fetchGoals();
  }, []);

  const fetchGoals = async () => {
    try {
      setLoading(true);
      const data = await goalsApi.list({ active_only: false });
      setGoals(data);
    } catch (error) {
      console.error("Failed to fetch goals:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async (goalId: string) => {
    try {
      await goalsApi.optimize(goalId);
      await fetchGoals();
      alert("Optimization complete! Check the schedule for new bundles.");
    } catch (error) {
      console.error("Failed to optimize goal:", error);
      alert("Optimization failed. Please try again.");
    }
  };

  if (loading) {
    return <GoalsSkeleton />;
  }

  return (
    <>
      {/* Page Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Optimization Goals</h1>
          <p className="text-neutral-400 mt-1">
            Transform business objectives into optimized patch schedules
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors"
        >
          Create New Goal
        </button>
      </div>

      {/* Goals List */}
      <div className="space-y-6">
        {goals.length === 0 ? (
          <EmptyState onCreateClick={() => setShowCreateModal(true)} />
        ) : (
          goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onOptimize={() => handleOptimize(goal.id)}
            />
          ))
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateGoalModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            fetchGoals();
          }}
        />
      )}
    </>
  );
}

function GoalCard({ goal, onOptimize }: { goal: Goal; onOptimize: () => void }) {
  const isAtRisk = goal.progress_percentage < 30 && goal.target_date;
  const daysRemaining = goal.target_date
    ? Math.floor((new Date(goal.target_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;

  return (
    <div className="card p-6">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h3 className="text-xl font-semibold">{goal.name}</h3>
            {!goal.active && (
              <span className="text-xs px-2 py-1 bg-neutral-700 text-neutral-300 rounded">
                INACTIVE
              </span>
            )}
            {isAtRisk && (
              <span className="text-xs px-2 py-1 bg-destructive/20 text-destructive rounded">
                AT RISK
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-neutral-400">
            <span>{GOAL_TYPE_LABELS[goal.type]}</span>
            <span>•</span>
            <span className={RISK_TOLERANCE_COLORS[goal.risk_tolerance]}>
              {goal.risk_tolerance} tolerance
            </span>
            {goal.target_date && (
              <>
                <span>•</span>
                <span>
                  {daysRemaining !== null && daysRemaining >= 0
                    ? `${daysRemaining} days remaining`
                    : "Overdue"}
                </span>
              </>
            )}
          </div>
        </div>
        <button
          onClick={onOptimize}
          className="px-3 py-1 text-sm bg-primary/10 text-primary rounded hover:bg-primary/20 transition-colors"
        >
          Optimize Schedule
        </button>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-neutral-400">Progress</span>
          <span>{goal.progress_percentage.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${goal.progress_percentage}%` }}
          />
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="text-2xl font-semibold">
            {goal.vulnerabilities_addressed}/{goal.vulnerabilities_total}
          </div>
          <div className="text-xs text-neutral-400">Vulnerabilities Addressed</div>
        </div>
        <div>
          <div className="text-2xl font-semibold">
            {((goal.risk_score_current / goal.risk_score_initial) * 100).toFixed(0)}%
          </div>
          <div className="text-xs text-neutral-400">Current Risk Level</div>
        </div>
        <div>
          <div className="text-2xl font-semibold">
            {goal.next_bundle_date
              ? new Date(goal.next_bundle_date).toLocaleDateString()
              : "Not scheduled"}
          </div>
          <div className="text-xs text-neutral-400">Next Bundle</div>
        </div>
        <div>
          <div className="text-2xl font-semibold">
            {goal.estimated_completion_date
              ? new Date(goal.estimated_completion_date).toLocaleDateString()
              : "TBD"}
          </div>
          <div className="text-xs text-neutral-400">Est. Completion</div>
        </div>
      </div>
    </div>
  );
}

function CreateGoalModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: "",
    type: "compliance_deadline",
    description: "",
    target_date: "",
    risk_tolerance: "balanced",
    max_vulns_per_window: 10,
    max_downtime_hours: 4,
    tags: [] as string[],
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        target_date: formData.target_date ? new Date(formData.target_date).toISOString() : null,
      };
      await goalsApi.create(payload);
      onSuccess();
    } catch (error) {
      console.error("Failed to create goal:", error);
      alert("Failed to create goal. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-lg p-6 max-w-lg w-full">
        <h2 className="text-2xl font-bold mb-4">Create New Goal</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Goal Name</label>
            <input
              type="text"
              required
              className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Glasswing Readiness Q3"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Goal Type</label>
            <select
              className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            >
              <option value="compliance_deadline">Compliance Deadline</option>
              <option value="risk_reduction">Risk Reduction</option>
              <option value="zero_critical">Zero Critical</option>
              <option value="kev_elimination">KEV Elimination</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Describe your business objective..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Target Date</label>
            <input
              type="date"
              className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              value={formData.target_date}
              onChange={(e) => setFormData({ ...formData, target_date: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Risk Tolerance</label>
            <select
              className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              value={formData.risk_tolerance}
              onChange={(e) => setFormData({ ...formData, risk_tolerance: e.target.value })}
            >
              <option value="conservative">Conservative - Minimize all risk</option>
              <option value="balanced">Balanced - Risk/efficiency trade-off</option>
              <option value="aggressive">Aggressive - Speed over safety</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Max Vulns/Window</label>
              <input
                type="number"
                min="1"
                max="100"
                className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                value={formData.max_vulns_per_window}
                onChange={(e) =>
                  setFormData({ ...formData, max_vulns_per_window: parseInt(e.target.value) })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Downtime (hrs)</label>
              <input
                type="number"
                min="0.5"
                max="24"
                step="0.5"
                className="w-full px-3 py-2 bg-neutral-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                value={formData.max_downtime_hours}
                onChange={(e) =>
                  setFormData({ ...formData, max_downtime_hours: parseFloat(e.target.value) })
                }
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Tags</label>
            <TagAutocomplete
              value={formData.tags}
              onChange={(tags) => setFormData({ ...formData, tags })}
              placeholder="Categorize this goal with tags..."
            />
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-neutral-400 hover:text-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors"
            >
              Create Goal
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="card p-12 text-center">
      <h3 className="text-xl font-semibold mb-2">No goals yet</h3>
      <p className="text-neutral-400 mb-6">
        Create your first optimization goal to start transforming business objectives into patch
        schedules.
      </p>
      <button
        onClick={onCreateClick}
        className="px-4 py-2 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors"
      >
        Create Your First Goal
      </button>
    </div>
  );
}

function GoalsSkeleton() {
  return (
    <>
      <div className="skeleton h-10 w-64 mb-8 rounded" />
      <div className="space-y-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="skeleton h-48 rounded-lg" />
        ))}
      </div>
    </>
  );
}
