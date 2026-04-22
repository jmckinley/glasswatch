"use client";

import { useState, useEffect } from "react";
import { rulesApi } from "@/lib/api";

interface Rule {
  id: string;
  name: string;
  description: string | null;
  scope_type: string;
  scope_value: string | null;
  scope_tags: string[] | null;
  condition_type: string;
  condition_config: Record<string, any>;
  action_type: string;
  action_config: Record<string, any>;
  priority: number;
  enabled: boolean;
  is_default: boolean;
  created_at: string;
}

const SCOPE_TYPE_LABELS: Record<string, string> = {
  global: "Global",
  tag: "Tag",
  environment: "Environment",
  asset_group: "Asset Group",
  asset: "Asset",
};

const ACTION_TYPE_LABELS: Record<string, string> = {
  block: "Block",
  warn: "Warn",
  require_approval: "Require Approval",
  escalate_risk: "Escalate Risk",
  notify: "Notify",
};

const ACTION_TYPE_COLORS: Record<string, string> = {
  block: "text-red-400",
  warn: "text-yellow-400",
  require_approval: "text-blue-400",
  escalate_risk: "text-orange-400",
  notify: "text-green-400",
};

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const response = await rulesApi.list();
      setRules(response.rules || []);
    } catch (error) {
      console.error("Failed to fetch rules:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleEnabled = async (rule: Rule) => {
    try {
      await rulesApi.update(rule.id, { enabled: !rule.enabled });
      await fetchRules();
    } catch (error) {
      console.error("Failed to toggle rule:", error);
      alert("Failed to update rule");
    }
  };

  const deleteRule = async (rule: Rule) => {
    if (rule.is_default) {
      alert("Cannot delete default rules. Disable instead.");
      return;
    }

    if (!confirm(`Delete rule "${rule.name}"?`)) {
      return;
    }

    try {
      await rulesApi.delete(rule.id);
      await fetchRules();
    } catch (error) {
      console.error("Failed to delete rule:", error);
      alert("Failed to delete rule");
    }
  };

  const formatConditionSummary = (rule: Rule): string => {
    if (rule.condition_type === "always") {
      return "Always";
    }

    if (rule.condition_type === "time_window") {
      const config = rule.condition_config;
      if (config.type === "month_end") {
        return `Last ${config.days_before} days of month`;
      }
      if (config.type === "quarter_end") {
        return `Last ${config.days_before} days of quarter`;
      }
      if (config.type === "day_of_week") {
        const days = config.days.join(", ");
        const after = config.after_hour ? ` after ${config.after_hour}:00` : "";
        return `${days}${after}`;
      }
    }

    if (rule.condition_type === "calendar") {
      const config = rule.condition_config;
      if (config.type === "holiday") {
        return `Holidays (${config.calendars.join(", ")})`;
      }
    }

    return rule.condition_type;
  };

  const formatScopeSummary = (rule: Rule): string => {
    if (rule.scope_type === "global") {
      return "All deployments";
    }

    if (rule.scope_type === "tag") {
      if (rule.scope_tags && rule.scope_tags.length > 0) {
        return `Tags: ${rule.scope_tags.join(", ")}`;
      }
      return `Tag: ${rule.scope_value}`;
    }

    if (rule.scope_type === "environment") {
      return `Environment: ${rule.scope_value}`;
    }

    return `${SCOPE_TYPE_LABELS[rule.scope_type] || rule.scope_type}: ${rule.scope_value}`;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-gray-400">Loading rules...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Deployment Rules</h1>
          <p className="text-gray-400 mt-1">
            Governance policies for patch deployments
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + Create Rule
        </button>
      </div>

      {/* Rules table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900 border-b border-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Rule
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Scope
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Condition
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Action
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {rules.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No rules defined. Create your first rule to get started.
                </td>
              </tr>
            ) : (
              rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-750">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div>
                        <div className="text-white font-medium">{rule.name}</div>
                        {rule.description && (
                          <div className="text-sm text-gray-400 mt-1">
                            {rule.description}
                          </div>
                        )}
                        {rule.is_default && (
                          <span className="inline-block px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded mt-1">
                            Default
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {formatScopeSummary(rule)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {formatConditionSummary(rule)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-sm font-medium ${ACTION_TYPE_COLORS[rule.action_type]}`}>
                      {ACTION_TYPE_LABELS[rule.action_type] || rule.action_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {rule.priority}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleEnabled(rule)}
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        rule.enabled
                          ? "bg-green-500/20 text-green-300"
                          : "bg-gray-600/20 text-gray-400"
                      }`}
                    >
                      {rule.enabled ? "Enabled" : "Disabled"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingRule(rule)}
                        className="px-3 py-1 text-sm text-blue-400 hover:text-blue-300"
                      >
                        Edit
                      </button>
                      {!rule.is_default && (
                        <button
                          onClick={() => deleteRule(rule)}
                          className="px-3 py-1 text-sm text-red-400 hover:text-red-300"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Info box */}
      <div className="mt-6 bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-300 mb-2">
          About Deployment Rules
        </h3>
        <p className="text-sm text-gray-300">
          Rules are evaluated in priority order (highest first). Block actions override warnings.
          Default rules cannot be deleted but can be disabled. Rules can be scoped to specific
          tags, environments, or assets.
        </p>
      </div>

      {/* Create/Edit Dialog (placeholder) */}
      {(showCreateDialog || editingRule) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-white mb-4">
              {editingRule ? "Edit Rule" : "Create Rule"}
            </h3>
            
            <div className="text-gray-400 mb-4">
              Rule creation form coming soon. For now, use the API or seed scripts.
            </div>

            <button
              onClick={() => {
                setShowCreateDialog(false);
                setEditingRule(null);
              }}
              className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
