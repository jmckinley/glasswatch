"use client";

import { useState, useEffect } from "react";
import { rulesApi } from "@/lib/api";
import TagAutocomplete from "@/components/TagAutocomplete";

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

      {/* Create/Edit Dialog */}
      {(showCreateDialog || editingRule) && (
        <RuleDialog
          rule={editingRule}
          onClose={() => {
            setShowCreateDialog(false);
            setEditingRule(null);
          }}
          onSuccess={() => {
            setShowCreateDialog(false);
            setEditingRule(null);
            fetchRules();
          }}
        />
      )}
    </div>
  );
}

function RuleDialog({
  rule,
  onClose,
  onSuccess,
}: {
  rule: Rule | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [formData, setFormData] = useState({
    name: rule?.name || "",
    description: rule?.description || "",
    scope_type: rule?.scope_type || "global",
    scope_value: rule?.scope_value || "",
    scope_tags: rule?.scope_tags || [],
    condition_type: rule?.condition_type || "always",
    condition_config: rule?.condition_config || {},
    action_type: rule?.action_type || "warn",
    action_config: rule?.action_config || {},
    priority: rule?.priority || 100,
    enabled: rule?.enabled ?? true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (rule) {
        await rulesApi.update(rule.id, formData);
      } else {
        await rulesApi.create(formData);
      }
      onSuccess();
    } catch (error) {
      console.error("Failed to save rule:", error);
      alert("Failed to save rule. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-white mb-4">
          {rule ? "Edit Rule" : "Create Rule"}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Basic Info */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Rule Name</label>
            <input
              type="text"
              required
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., No deployments during month-end"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
            <textarea
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
              rows={2}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional: Explain when and why this rule applies"
            />
          </div>

          {/* Scope */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-sm font-semibold text-white mb-3">Scope - What does this rule apply to?</h4>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Scope Type</label>
                <select
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  value={formData.scope_type}
                  onChange={(e) => setFormData({ ...formData, scope_type: e.target.value, scope_value: "", scope_tags: [] })}
                >
                  <option value="global">Global (all deployments)</option>
                  <option value="tag">Tag</option>
                  <option value="environment">Environment</option>
                  <option value="asset_group">Asset Group</option>
                  <option value="asset">Specific Asset</option>
                </select>
              </div>

              {formData.scope_type === "tag" && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Tags</label>
                  <TagAutocomplete
                    value={formData.scope_tags || []}
                    onChange={(tags) => setFormData({ ...formData, scope_tags: tags })}
                    placeholder="Select tags..."
                  />
                </div>
              )}

              {formData.scope_type !== "global" && formData.scope_type !== "tag" && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Value</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.scope_value}
                    onChange={(e) => setFormData({ ...formData, scope_value: e.target.value })}
                    placeholder={
                      formData.scope_type === "environment"
                        ? "e.g., production"
                        : formData.scope_type === "asset_group"
                        ? "e.g., web-servers"
                        : "Asset ID or name"
                    }
                  />
                </div>
              )}
            </div>
          </div>

          {/* Condition */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-sm font-semibold text-white mb-3">Condition - When does this rule trigger?</h4>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Condition Type</label>
              <select
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                value={formData.condition_type}
                onChange={(e) => setFormData({ ...formData, condition_type: e.target.value, condition_config: {} })}
              >
                <option value="always">Always</option>
                <option value="time_of_day">Time of Day</option>
                <option value="calendar">Calendar Event</option>
              </select>
            </div>

            {formData.condition_type === "time_of_day" && (
              <div className="mt-3 grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Start Hour (0-23)</label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.condition_config.start_hour || 0}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        condition_config: { ...formData.condition_config, start_hour: parseInt(e.target.value) },
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">End Hour (0-23)</label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.condition_config.end_hour || 23}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        condition_config: { ...formData.condition_config, end_hour: parseInt(e.target.value) },
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Days of Week</label>
                  <select
                    multiple
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.condition_config.days_of_week || []}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        condition_config: {
                          ...formData.condition_config,
                          days_of_week: Array.from(e.target.selectedOptions, (option) => option.value),
                        },
                      })
                    }
                  >
                    <option value="monday">Monday</option>
                    <option value="tuesday">Tuesday</option>
                    <option value="wednesday">Wednesday</option>
                    <option value="thursday">Thursday</option>
                    <option value="friday">Friday</option>
                    <option value="saturday">Saturday</option>
                    <option value="sunday">Sunday</option>
                  </select>
                </div>
              </div>
            )}

            {formData.condition_type === "calendar" && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Calendar Type</label>
                  <select
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.condition_config.calendar_type || "month_end"}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        condition_config: { ...formData.condition_config, calendar_type: e.target.value },
                      })
                    }
                  >
                    <option value="month_end">Month End</option>
                    <option value="quarter_end">Quarter End</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Window Days</label>
                  <input
                    type="number"
                    min="1"
                    max="15"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.condition_config.window_days || 3}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        condition_config: { ...formData.condition_config, window_days: parseInt(e.target.value) },
                      })
                    }
                    placeholder="Days before/after event"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Action */}
          <div className="border-t border-gray-700 pt-4">
            <h4 className="text-sm font-semibold text-white mb-3">Action - What happens when rule triggers?</h4>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Action Type</label>
              <select
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                value={formData.action_type}
                onChange={(e) => setFormData({ ...formData, action_type: e.target.value, action_config: {} })}
              >
                <option value="warn">Warn</option>
                <option value="block">Block</option>
                <option value="require_approval">Require Approval</option>
                <option value="escalate_risk">Escalate Risk</option>
                <option value="notify">Notify</option>
              </select>
            </div>

            {formData.action_type === "block" && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-300 mb-1">Reason</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  value={formData.action_config.reason || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      action_config: { reason: e.target.value },
                    })
                  }
                  placeholder="e.g., Financial freeze period"
                />
              </div>
            )}

            {formData.action_type === "warn" && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-300 mb-1">Warning Message</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  value={formData.action_config.message || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      action_config: { message: e.target.value },
                    })
                  }
                  placeholder="e.g., High-risk period - proceed with caution"
                />
              </div>
            )}

            {formData.action_type === "require_approval" && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Min Approvers</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={formData.action_config.min_approvers || 1}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        action_config: { ...formData.action_config, min_approvers: parseInt(e.target.value) },
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Approval Roles (optional)</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                    value={(formData.action_config.approval_roles || []).join(", ")}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        action_config: {
                          ...formData.action_config,
                          approval_roles: e.target.value.split(",").map((r) => r.trim()).filter(Boolean),
                        },
                      })
                    }
                    placeholder="e.g., manager, admin"
                  />
                </div>
              </div>
            )}

            {formData.action_type === "escalate_risk" && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-300 mb-1">Escalation Factor</label>
                <input
                  type="number"
                  min="1.1"
                  max="5"
                  step="0.1"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  value={formData.action_config.escalation_factor || 1.5}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      action_config: { escalation_factor: parseFloat(e.target.value) },
                    })
                  }
                  placeholder="Multiply risk score by this factor"
                />
              </div>
            )}

            {formData.action_type === "notify" && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-300 mb-1">Notification Channels</label>
                <select
                  multiple
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                  value={formData.action_config.channels || []}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      action_config: {
                        channels: Array.from(e.target.selectedOptions, (option) => option.value),
                      },
                    })
                  }
                >
                  <option value="email">Email</option>
                  <option value="slack">Slack</option>
                  <option value="teams">Microsoft Teams</option>
                  <option value="pagerduty">PagerDuty</option>
                </select>
              </div>
            )}
          </div>

          {/* Priority & Status */}
          <div className="border-t border-gray-700 pt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Priority</label>
              <input
                type="number"
                min="0"
                max="1000"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              />
              <p className="text-xs text-gray-400 mt-1">Higher priority rules are evaluated first</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
              <label className="flex items-center mt-2">
                <input
                  type="checkbox"
                  className="mr-2"
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                />
                <span className="text-white">Enabled</span>
              </label>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex gap-3 mt-6 border-t border-gray-700 pt-4">
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              {rule ? "Update Rule" : "Create Rule"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600"
            >}
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
