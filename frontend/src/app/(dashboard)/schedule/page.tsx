"use client";

import { useState, useEffect } from "react";
import { maintenanceWindowsApi, goalsApi, bundlesApi, rulesApi } from "@/lib/api";
import MaintenanceWindowDialog from "@/components/MaintenanceWindowDialog";
import ScheduleCalendar from "@/components/ScheduleCalendar";

interface MaintenanceWindow {
  id: string;
  name: string;
  description?: string;
  start_time: string;
  end_time: string;
  type: "scheduled" | "emergency" | "blackout";
  environment?: string;
  timezone?: string;
  duration_hours: number;
  approved: boolean;
  active: boolean;
  max_assets?: number;
  max_risk_score?: number;
  scheduled_bundles: Bundle[];
  // Sprint 13 additions
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
  vulnerability?: {
    identifier: string;
    title: string;
    severity: string;
  };
  asset?: {
    name: string;
    identifier: string;
  };
}

interface Goal {
  id: string;
  name: string;
  target_completion_date: string | null;
  vulnerabilities_addressed: number;
  vulnerabilities_total: number;
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: "text-success",
  draft: "text-neutral-400",
  in_progress: "text-secondary",
  completed: "text-success",
  failed: "text-destructive",
  approved: "text-primary",
};

const STATUS_BG: Record<string, string> = {
  scheduled: "bg-success/10",
  draft: "bg-neutral-700",
  in_progress: "bg-secondary/10",
  completed: "bg-success/10",
  failed: "bg-destructive/10",
  approved: "bg-primary/10",
};

export default function SchedulePage() {
  const [windows, setWindows] = useState<MaintenanceWindow[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"calendar" | "list">("list");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  // Sprint 13: Filtering
  const [filterEnvironment, setFilterEnvironment] = useState<string>("");
  const [filterAssetGroup, setFilterAssetGroup] = useState<string>("");
  const [environments, setEnvironments] = useState<string[]>([]);
  const [assetGroups, setAssetGroups] = useState<string[]>([]);
  // Rule violations
  const [ruleViolations, setRuleViolations] = useState<Record<string, any[]>>({});
  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWindow, setEditingWindow] = useState<any>(null);
  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [filterEnvironment, filterAssetGroup]);

  useEffect(() => {
    if (windows.length > 0) {
      evaluateRules();
    }
  }, [windows]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (filterEnvironment) params.environment = filterEnvironment;
      if (filterAssetGroup) params.asset_group = filterAssetGroup;
      
      const [windowsData, goalsData, envsData, groupsData] = await Promise.all([
        maintenanceWindowsApi.list(params),
        goalsApi.list({ active_only: true }),
        maintenanceWindowsApi.listEnvironments().catch(() => ({ environments: [] })),
        maintenanceWindowsApi.listAssetGroups().catch(() => ({ asset_groups: [] })),
      ]);
      setWindows(windowsData.items || []);
      setGoals(goalsData || []);
      setEnvironments(envsData.environments || []);
      setAssetGroups(groupsData.asset_groups || []);
    } catch (error) {
      console.error("Failed to fetch schedule data:", error);
      setWindows([]);
      setGoals([]);
    } finally {
      setLoading(false);
    }
  };

  const evaluateRules = async () => {
    try {
      const violations: Record<string, any[]> = {};
      
      // Evaluate rules for each window/bundle combination
      for (const window of windows) {
        for (const bundle of window.scheduled_bundles || []) {
          const result = await rulesApi.evaluate({
            window_id: window.id,
            bundle_id: bundle.id,
            environment: window.environment,
          });
          
          if (result.violations && result.violations.length > 0) {
            const key = `${window.id}-${bundle.id}`;
            violations[key] = result.violations;
          }
        }
      }
      
      setRuleViolations(violations);
    } catch (error) {
      console.error("Failed to evaluate rules:", error);
    }
  };

  const handleNewWindow = () => {
    setEditingWindow(null);
    setDialogOpen(true);
  };
  
  const handleEditWindow = (window: MaintenanceWindow) => {
    setEditingWindow(window);
    setDialogOpen(true);
  };
  
  const handleDeleteWindow = async (windowId: string) => {
    try {
      await maintenanceWindowsApi.delete(windowId);
      await fetchData();
      setDeleteConfirm(null);
    } catch (error: any) {
      alert(error.message || "Failed to delete window");
    }
  };
  
  const handleDialogSave = async () => {
    await fetchData();
  };
  
  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysisResult(null);

    try {
      // Call the optimize endpoint with preview_only if available
      // For now, provide analysis based on current data
      const totalWindows = windows.length;
      const totalBundles = windows.reduce((sum, w) => sum + (w.scheduled_bundles?.length || 0), 0);

      // Calculate average utilization
      const avgUtilization =
        windows.reduce((sum, w) => {
          const totalDuration = w.scheduled_bundles.reduce(
            (s, b) => s + (b.estimated_duration_minutes || 0),
            0
          );
          return sum + (totalDuration / (w.duration_hours * 60)) * 100;
        }, 0) / (totalWindows || 1);

      // Calculate velocity per goal
      const velocityAnalysis = goals.map((goal) => {
        const daysRemaining = goal.target_completion_date
          ? Math.ceil(
              (new Date(goal.target_completion_date).getTime() - new Date().getTime()) /
                (1000 * 60 * 60 * 24)
            )
          : null;
        const patches_remaining = goal.vulnerabilities_total - goal.vulnerabilities_addressed;
        const patchesPerWeek =
          goal.vulnerabilities_addressed > 0 ? (goal.vulnerabilities_addressed / 30) * 7 : 0;
        const weeksNeeded =
          patchesPerWeek > 0 ? patches_remaining / patchesPerWeek : Infinity;
        const weeksAvailable = daysRemaining ? daysRemaining / 7 : null;

        return {
          name: goal.name,
          daysRemaining,
          weeksNeeded,
          weeksAvailable,
          onTrack: weeksAvailable ? weeksNeeded <= weeksAvailable : null,
        };
      });

      const atRiskGoals = velocityAnalysis.filter((g) => g.onTrack === false);

      let analysis = `**Schedule Analysis Complete**\n\n`;
      analysis += `• ${totalWindows} maintenance windows scheduled\n`;
      analysis += `• ${totalBundles} patch bundles across all windows\n`;
      analysis += `• ${avgUtilization.toFixed(1)}% average window utilization\n\n`;

      if (atRiskGoals.length > 0) {
        analysis += `**Velocity Concerns:**\n`;
        atRiskGoals.forEach((g) => {
          const shortfall = g.weeksNeeded - (g.weeksAvailable || 0);
          analysis += `• "${g.name}" will miss deadline by ~${shortfall.toFixed(1)} weeks at current velocity\n`;
        });
      } else {
        analysis += `✓ All goals are on track at current patch velocity.\n`;
      }

      setAnalysisResult(analysis);
    } catch (error) {
      setAnalysisResult(
        `Analysis unavailable. Backend optimization endpoint may not be implemented yet.\n\nCurrent schedule shows ${windows.length} windows with ${windows.reduce((s, w) => s + w.scheduled_bundles.length, 0)} bundles.`
      );
    } finally {
      setTimeout(() => setAnalyzing(false), 1000);
    }
  };

  return (
    <>
      {/* Page Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Patch Schedule</h1>
          <p className="text-neutral-400 mt-1">
            Maintenance windows and scheduled patch bundles
          </p>
        </div>
        <div className="flex gap-2 items-center">
          {/* Filters */}
          <select
            value={filterEnvironment}
            onChange={(e) => setFilterEnvironment(e.target.value)}
            className="px-3 py-2 bg-neutral-800 text-white rounded-lg border border-neutral-700"
          >
            <option value="">All Environments</option>
            {environments.map((env) => (
              <option key={env} value={env}>{env}</option>
            ))}
          </select>
          <select
            value={filterAssetGroup}
            onChange={(e) => setFilterAssetGroup(e.target.value)}
            className="px-3 py-2 bg-neutral-800 text-white rounded-lg border border-neutral-700"
          >
            <option value="">All Asset Groups</option>
            {assetGroups.map((group) => (
              <option key={group} value={group}>{group}</option>
            ))}
          </select>
          <button
            onClick={handleNewWindow}
            className="px-4 py-2 bg-success text-white rounded-lg hover:bg-success/90 transition-colors flex items-center gap-2"
          >
            + New Window
          </button>
          <button
            onClick={handleAnalyze}
            disabled={analyzing || loading}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {analyzing ? (
              <>
                <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Analyzing...
              </>
            ) : (
              "Analyze Schedule"
            )}
          </button>
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

      {/* Analysis Result */}
      {analysisResult && (
        <div className="card p-6 mb-6 bg-primary/10 border-primary/30">
          <div className="flex items-start gap-3">
            <div className="text-primary text-xl">📊</div>
            <div className="flex-1">
              <h3 className="font-semibold mb-2 text-primary">Schedule Analysis</h3>
              <pre className="text-sm text-neutral-300 whitespace-pre-wrap font-sans">
                {analysisResult}
              </pre>
            </div>
            <button
              onClick={() => setAnalysisResult(null)}
              className="text-neutral-400 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Optimization Summary */}
      {!loading && goals.length > 0 && (
        <div className="card p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Optimization Summary</h2>

          {/* Goal Timelines */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-neutral-400 mb-3">Goal Progress Timeline</h3>
            <div className="space-y-3">
              {goals.map((goal) => {
                const totalPatches = goal.vulnerabilities_total;
                const progressPct =
                  totalPatches > 0 ? (goal.vulnerabilities_addressed / totalPatches) * 100 : 0;
                const daysRemaining = goal.target_completion_date
                  ? Math.ceil(
                      (new Date(goal.target_completion_date).getTime() - new Date().getTime()) /
                        (1000 * 60 * 60 * 24)
                    )
                  : null;

                return (
                  <div key={goal.id} className="bg-neutral-800 rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium">{goal.name}</span>
                      <span className="text-sm text-neutral-400">
                        {daysRemaining !== null ? `${daysRemaining} days remaining` : "No deadline"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-3 bg-neutral-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            progressPct >= 75
                              ? "bg-success"
                              : progressPct >= 40
                              ? "bg-warning"
                              : "bg-destructive"
                          }`}
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-16 text-right">
                        {progressPct.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cross-Goal Insights */}
          <div>
            <h3 className="text-sm font-medium text-neutral-400 mb-3">Cross-Goal Insights</h3>
            <div className="bg-neutral-800 rounded-lg p-4 text-sm text-neutral-300">
              {windows.length === 0 ? (
                <p>No maintenance windows scheduled yet.</p>
              ) : (
                <ul className="space-y-2">
                  <li>
                    • {windows.filter((w) => w.type === "emergency").length} emergency windows
                    prioritize critical KEV-listed vulnerabilities
                  </li>
                  <li>
                    • {windows.filter((w) => w.type === "scheduled").length} scheduled windows
                    balance capacity across environments
                  </li>
                  {goals.length > 1 && (
                    <li>
                      • Multiple goals may share maintenance windows — bundles are assigned based
                      on risk, deadline, and capacity constraints
                    </li>
                  )}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <ScheduleSkeleton />
      ) : viewMode === "list" ? (
        <ListView 
          windows={windows} 
          goals={goals} 
          ruleViolations={ruleViolations}
          onEdit={handleEditWindow}
          onDelete={(id) => setDeleteConfirm(id)}
        />
      ) : (
        <ScheduleCalendar 
          windows={windows}
          onWindowUpdate={loadData}
          environments={environments}
          assetGroups={assetGroups}
        />
      )}
      
      {/* Maintenance Window Dialog */}
      <MaintenanceWindowDialog
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={handleDialogSave}
        windowData={editingWindow}
      />
      
      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md border border-gray-600">
            <h3 className="text-xl font-bold mb-4">Delete Maintenance Window?</h3>
            <p className="text-gray-300 mb-6">
              Are you sure you want to delete this maintenance window? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteWindow(deleteConfirm)}
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

function ListView({ 
  windows, 
  goals, 
  ruleViolations,
  onEdit,
  onDelete,
}: { 
  windows: MaintenanceWindow[]; 
  goals: Goal[]; 
  ruleViolations: Record<string, any[]>;
  onEdit: (window: MaintenanceWindow) => void;
  onDelete: (id: string) => void;
}) {
  const now = new Date();
  const upcomingWindows = windows.filter((w) => new Date(w.start_time) > now);
  const pastWindows = windows.filter((w) => new Date(w.start_time) <= now);
  
  // Group upcoming windows by environment
  const groupedWindows = upcomingWindows.reduce((acc, window) => {
    const env = window.environment || "default";
    if (!acc[env]) acc[env] = [];
    acc[env].push(window);
    return acc;
  }, {} as Record<string, MaintenanceWindow[]>);
  
  // Separate default and blackout windows
  const defaultWindows = upcomingWindows.filter(w => w.is_default);
  const blackoutWindows = upcomingWindows.filter(w => w.type === "blackout");
  const regularWindows = upcomingWindows.filter(w => !w.is_default && w.type !== "blackout");

  return (
    <div className="space-y-8">
      {/* Default Windows */}
      {defaultWindows.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
            Default Fallback Windows
            <span className="text-sm text-gray-400 font-normal">(apply when no specific match exists)</span>
          </h2>
          <div className="space-y-4">
            {defaultWindows.map((window) => (
              <WindowCard 
                key={window.id} 
                window={window} 
                goals={goals} 
                ruleViolations={ruleViolations}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            ))}
          </div>
        </div>
      )}
      
      {/* Blackout Windows */}
      {blackoutWindows.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
            <span className="text-red-400">⚠️ Blackout Windows</span>
            <span className="text-sm text-gray-400 font-normal">(no changes allowed)</span>
          </h2>
          <div className="space-y-4">
            {blackoutWindows.map((window) => (
              <div key={window.id} className="border-2 border-red-500/50 rounded-lg">
                <WindowCard 
                  window={window} 
                  goals={goals} 
                  ruleViolations={ruleViolations}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Regular Windows Grouped by Environment */}
      {regularWindows.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Upcoming Maintenance</h2>
          
          {Object.keys(groupedWindows).sort().map(env => {
            const envWindows = groupedWindows[env].filter(w => !w.is_default && w.type !== "blackout");
            if (envWindows.length === 0) return null;
            
            return (
              <div key={env} className="mb-6">
                <h3 className="text-lg font-medium mb-3 text-primary capitalize">
                  {env === "default" ? "No Environment Specified" : env}
                </h3>
                <div className="space-y-4">
                  {envWindows.map((window) => (
                    <WindowCard 
                      key={window.id} 
                      window={window} 
                      goals={goals} 
                      ruleViolations={ruleViolations}
                      onEdit={onEdit}
                      onDelete={onDelete}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {upcomingWindows.length === 0 && (
        <div className="card p-8 text-center text-neutral-400">
          No upcoming maintenance windows scheduled
        </div>
      )}

      {pastWindows.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Past Maintenance</h2>
          <div className="space-y-4">
            {pastWindows.map((window) => (
              <WindowCard 
                key={window.id} 
                window={window} 
                goals={goals} 
                ruleViolations={ruleViolations}
                onEdit={onEdit}
                onDelete={onDelete}
                isPast 
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function WindowCard({
  window,
  goals,
  ruleViolations,
  onEdit,
  onDelete,
  isPast = false,
}: {
  window: MaintenanceWindow;
  goals: Goal[];
  ruleViolations: Record<string, any[]>;
  onEdit: (window: MaintenanceWindow) => void;
  onDelete: (id: string) => void;
  isPast?: boolean;
}) {
  const startDate = new Date(window.start_time);
  const endDate = new Date(window.end_time);
  const duration = window.duration_hours;
  const totalBundleDuration = window.scheduled_bundles.reduce(
    (sum, b) => sum + (b.estimated_duration_minutes || 0),
    0
  );
  const utilizationPercent = (totalBundleDuration / (duration * 60)) * 100;

  // Calculate which goals this window serves
  const goalIds = new Set(
    window.scheduled_bundles.map((b) => b.goal_id).filter((id) => id !== undefined)
  );
  const servedGoals = goals.filter((g) => goalIds.has(g.id));

  // Calculate total risk reduction
  const totalRiskReduction = window.scheduled_bundles.reduce(
    (sum, b) => sum + (b.risk_score || 0),
    0
  );

  // Count assets
  const totalAssets = window.scheduled_bundles.reduce(
    (sum, b) => sum + (b.assets_affected_count || 0),
    0
  );

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
            <span>{window.environment || "default"}</span>
            {window.service_name && (
              <>
                <span>•</span>
                <span className="text-primary">{window.service_name}</span>
              </>
            )}
            {window.asset_group && (
              <>
                <span>•</span>
                <span className="text-secondary">{window.asset_group}</span>
              </>
            )}
          </div>
          {window.description && (
            <p className="text-sm text-neutral-400 mt-2">{window.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {window.priority !== undefined && window.priority > 0 && (
            <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-400 rounded border border-purple-500/30">
              Priority {window.priority}
            </span>
          )}
          {window.is_default && (
            <span className="text-xs px-2 py-1 bg-neutral-700 text-neutral-300 rounded">
              DEFAULT
            </span>
          )}
          <span
            className={`text-xs px-2 py-1 rounded font-medium ${
              window.type === "emergency"
                ? "bg-destructive/20 text-destructive border border-destructive/30"
                : "bg-primary/20 text-primary border border-primary/30"
            }`}
          >
            {window.type.toUpperCase()}
          </span>
          {window.approved ? (
            <span className="text-xs px-2 py-1 bg-success/10 text-success rounded">APPROVED</span>
          ) : (
            <span className="text-xs px-2 py-1 bg-warning/10 text-warning rounded">
              PENDING APPROVAL
            </span>
          )}
          
          {/* Edit/Delete buttons for non-past windows */}
          {!isPast && (
            <div className="flex gap-2 ml-2">
              <button
                onClick={() => onEdit(window)}
                className="text-xs px-3 py-1 bg-blue-500/20 text-blue-300 rounded hover:bg-blue-500/30 transition-colors flex items-center gap-1"
                title="Edit window"
              >
                ✏️ Edit
              </button>
              <button
                onClick={() => onDelete(window.id)}
                className="text-xs px-3 py-1 bg-red-500/20 text-red-300 rounded hover:bg-red-500/30 transition-colors flex items-center gap-1"
                title="Delete window"
              >
                🗑️ Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Goals Served */}
      {servedGoals.length > 0 && (
        <div className="mb-4 pb-4 border-b border-neutral-700">
          <div className="text-sm text-neutral-400 mb-2">Goals Served by This Window:</div>
          <div className="flex flex-wrap gap-2">
            {servedGoals.map((goal) => (
              <span
                key={goal.id}
                className="text-xs px-3 py-1 bg-primary/10 text-primary rounded-full border border-primary/30"
              >
                {goal.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Capacity & Risk */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <div className="text-sm text-neutral-400">Capacity</div>
          <div className="text-lg font-semibold">
            {totalAssets}/{window.max_assets || "∞"}
          </div>
          <div className="text-xs text-neutral-500">
            {window.max_assets ? `${((totalAssets / window.max_assets) * 100).toFixed(0)}% used` : ""}
          </div>
        </div>
        <div>
          <div className="text-sm text-neutral-400">Utilization</div>
          <div className="text-lg font-semibold">{utilizationPercent.toFixed(0)}%</div>
          <div className="text-xs text-neutral-500">
            {totalBundleDuration}m / {duration * 60}m
          </div>
        </div>
        <div>
          <div className="text-sm text-neutral-400">Risk Reduction</div>
          <div className="text-lg font-semibold">{totalRiskReduction.toFixed(1)}</div>
          <div className="text-xs text-neutral-500">total risk score</div>
        </div>
      </div>

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
            style={{ width: `${Math.min(utilizationPercent, 100)}%` }}
          />
        </div>
      </div>

      {/* Bundles */}
      {window.scheduled_bundles && window.scheduled_bundles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-neutral-400">Scheduled Bundles</h4>
          {window.scheduled_bundles.map((bundle) => {
            const violationKey = `${window.id}-${bundle.id}`;
            const violations = ruleViolations[violationKey] || [];
            const hasBlocks = violations.some((v) => v.action_type === "block");
            const hasWarns = violations.some((v) => v.action_type === "warn");
            const hasApprovals = violations.some((v) => v.action_type === "require_approval");

            return (
              <div key={bundle.id} className="bg-neutral-800 rounded-lg p-4">
                {/* Rule Violation Banners */}
                {violations.length > 0 && (
                  <div className="mb-3 space-y-2">
                    {violations.map((violation, idx) => {
                      const bannerColor =
                        violation.action_type === "block"
                          ? "bg-red-500/20 border-red-500 text-red-300"
                          : violation.action_type === "warn"
                          ? "bg-yellow-500/20 border-yellow-500 text-yellow-300"
                          : violation.action_type === "require_approval"
                          ? "bg-blue-500/20 border-blue-500 text-blue-300"
                          : "bg-gray-500/20 border-gray-500 text-gray-300";

                      return (
                        <div
                          key={idx}
                          className={`flex items-start gap-2 p-3 border rounded-md ${bannerColor}`}
                        >
                          <span className="text-lg">
                            {violation.action_type === "block" && "⚠️"}
                            {violation.action_type === "warn" && "⚠️"}
                            {violation.action_type === "require_approval" && "🔒"}
                          </span>
                          <div className="flex-1">
                            <div className="font-medium text-sm">
                              {violation.rule_name || "Rule Triggered"}
                            </div>
                            <div className="text-xs mt-1">
                              {violation.message || violation.action_config?.reason || violation.action_config?.message || "Action required"}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h5 className="font-medium">{bundle.name}</h5>
                    <div className="flex items-center gap-4 mt-1 text-sm text-neutral-400">
                      {bundle.assets_affected_count && (
                        <>
                          <span>{bundle.assets_affected_count} assets</span>
                          <span>•</span>
                        </>
                      )}
                      {bundle.estimated_duration_minutes && (
                        <>
                          <span>{bundle.estimated_duration_minutes} min</span>
                          <span>•</span>
                        </>
                      )}
                      {bundle.risk_score && <span>Risk: {bundle.risk_score.toFixed(1)}</span>}
                    </div>
                    {bundle.items && bundle.items.length > 0 && (
                      <div className="mt-2 text-xs text-neutral-500">
                        Patches: {bundle.items.map((item) => item.vulnerability?.identifier).join(", ")}
                      </div>
                    )}
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded ${STATUS_BG[bundle.status]} ${
                      STATUS_COLORS[bundle.status]
                    }`}
                  >
                    {bundle.status.toUpperCase()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
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
