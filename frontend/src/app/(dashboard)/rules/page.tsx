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

interface ParsedRule {
  name: string;
  description: string;
  scope_type: string;
  scope_value: string | null;
  scope_tags: string[] | null;
  condition_type: string;
  condition_config: Record<string, any>;
  action_type: string;
  action_config: Record<string, any>;
  priority: number;
  confidence: number;
  source: "ai" | "pattern";
}

const ACTION_TYPE_LABELS: Record<string, string> = {
  block: "Block",
  warn: "Warn",
  require_approval: "Require Approval",
  escalate_risk: "Escalate Risk",
  notify: "Notify",
};

const ACTION_TYPE_COLORS: Record<string, string> = {
  block: "text-red-400 bg-red-500/10",
  warn: "text-yellow-400 bg-yellow-500/10",
  require_approval: "text-blue-400 bg-blue-500/10",
  escalate_risk: "text-orange-400 bg-orange-500/10",
  notify: "text-green-400 bg-green-500/10",
};

const SCOPE_TYPE_LABELS: Record<string, string> = {
  global: "All deployments",
  tag: "By tag",
  environment: "Environment",
  asset_group: "Asset group",
  asset: "Specific asset",
};

const NLP_EXAMPLES = [
  "Block deployments on Fridays after 3pm",
  "Warn about month-end deployments to production",
  "Require 2 approvals for PCI-DSS tagged assets",
];

function formatConditionSummary(rule: Rule | ParsedRule): string {
  if (rule.condition_type === "always") return "Always applies";
  if (rule.condition_type === "time_window") {
    const c = rule.condition_config;
    if (c.type === "month_end") return `Last ${c.days_before || 3} days of month`;
    if (c.type === "quarter_end") return `Last ${c.days_before || 3} days of quarter`;
    if (c.type === "day_of_week") {
      const days = Array.isArray(c.days) ? c.days.join(", ") : c.days;
      const after = c.after_hour != null ? ` after ${c.after_hour}:00` : "";
      return `${days}${after}`;
    }
  }
  if (rule.condition_type === "calendar") {
    const c = rule.condition_config;
    if (c.type === "holiday") return `Holidays (${(c.calendars || []).join(", ")})`;
  }
  return rule.condition_type;
}

function formatScopeSummary(rule: Rule | ParsedRule): string {
  if (rule.scope_type === "global") return "All deployments";
  if (rule.scope_type === "tag") {
    if (rule.scope_tags && rule.scope_tags.length > 0) return `Tags: ${rule.scope_tags.join(", ")}`;
    return `Tag: ${rule.scope_value}`;
  }
  if (rule.scope_type === "environment") return `Environment: ${rule.scope_value}`;
  return `${SCOPE_TYPE_LABELS[rule.scope_type] || rule.scope_type}: ${rule.scope_value}`;
}

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);

  useEffect(() => { fetchRules(); }, []);

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
    }
  };

  const deleteRule = async (rule: Rule) => {
    if (rule.is_default) { alert("Cannot delete default rules. Disable instead."); return; }
    if (!confirm(`Delete rule "${rule.name}"?`)) return;
    try {
      await rulesApi.delete(rule.id);
      await fetchRules();
    } catch (error) {
      console.error("Failed to delete rule:", error);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-400">Loading rules...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Deployment Rules</h1>
          <p className="text-gray-400 mt-1 text-sm">
            Governance policies — evaluated in priority order when patches are deployed
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm"
        >
          + Create Rule
        </button>
      </div>

      {/* Rules list */}
      <div className="space-y-3">
        {rules.length === 0 ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-12 text-center">
            <div className="text-4xl mb-3">📋</div>
            <h3 className="text-white font-medium mb-1">No rules yet</h3>
            <p className="text-gray-400 text-sm mb-4">
              Rules control when deployments are blocked, warned, or require approval.
            </p>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              Create your first rule
            </button>
          </div>
        ) : (
          rules.map((rule) => (
            <div
              key={rule.id}
              className={`bg-gray-800 rounded-xl border p-5 flex items-center gap-4 ${
                rule.enabled ? "border-gray-700" : "border-gray-800 opacity-60"
              }`}
            >
              {/* Action badge */}
              <div className={`px-3 py-1 rounded-full text-xs font-semibold shrink-0 ${ACTION_TYPE_COLORS[rule.action_type]}`}>
                {ACTION_TYPE_LABELS[rule.action_type] || rule.action_type}
              </div>

              {/* Rule info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium">{rule.name}</span>
                  {rule.is_default && (
                    <span className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded">
                      Default
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-400 mt-0.5 flex items-center gap-3">
                  <span>🎯 {formatScopeSummary(rule)}</span>
                  <span>·</span>
                  <span>⏱ {formatConditionSummary(rule)}</span>
                  <span>·</span>
                  <span>Priority {rule.priority}</span>
                </div>
                {rule.description && (
                  <p className="text-xs text-gray-500 mt-1 truncate">{rule.description}</p>
                )}
              </div>

              {/* Controls */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => toggleEnabled(rule)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                    rule.enabled
                      ? "bg-green-500/20 text-green-300 hover:bg-green-500/30"
                      : "bg-gray-600/30 text-gray-400 hover:bg-gray-600/50"
                  }`}
                >
                  {rule.enabled ? "On" : "Off"}
                </button>
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
            </div>
          ))
        )}
      </div>

      {rules.length > 0 && (
        <div className="mt-4 bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
          <p className="text-sm text-gray-300">
            <span className="font-medium text-blue-300">How rules work:</span> Evaluated highest-priority first.
            Block overrides warn. Default rules can be disabled but not deleted.
          </p>
        </div>
      )}

      {/* NLP Create Dialog */}
      {showCreateDialog && (
        <NLPRuleDialog
          onClose={() => setShowCreateDialog(false)}
          onSuccess={() => { setShowCreateDialog(false); fetchRules(); }}
        />
      )}

      {/* Edit Dialog */}
      {editingRule && (
        <RuleFormDialog
          rule={editingRule}
          onClose={() => setEditingRule(null)}
          onSuccess={() => { setEditingRule(null); fetchRules(); }}
        />
      )}
    </div>
  );
}

// ─── NLP-first Create Dialog ──────────────────────────────────────────────────

function NLPRuleDialog({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [nlpText, setNlpText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState<ParsedRule | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [showManualForm, setShowManualForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  // Editable parsed fields
  const [editedName, setEditedName] = useState("");
  const [editedActionType, setEditedActionType] = useState("warn");

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  const handleParse = async () => {
    if (!nlpText.trim()) return;
    setParsing(true);
    setParseError(null);
    setParsed(null);
    try {
      const result = await rulesApi.parseNlp(nlpText.trim());
      setParsed(result);
      setEditedName(result.name);
      setEditedActionType(result.action_type);
    } catch (err) {
      setParseError("Couldn't parse that rule. Try the manual form below.");
      setShowManualForm(true);
    } finally {
      setParsing(false);
    }
  };

  const handleSave = async () => {
    if (!parsed) return;
    setSaving(true);
    setSaveError(null);
    try {
      await rulesApi.create({
        ...parsed,
        name: editedName || parsed.name,
        action_type: editedActionType,
      });
      onSuccess();
    } catch (err) {
      setSaveError("Failed to save rule. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-white">Create Rule</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">×</button>
          </div>

          {!showManualForm ? (
            <>
              {/* NLP Input */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Describe your rule in plain English
                </label>
                <textarea
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none text-base"
                  rows={3}
                  placeholder="e.g. Block all deployments on Friday afternoons to production..."
                  value={nlpText}
                  onChange={(e) => { setNlpText(e.target.value); setParsed(null); setParseError(null); }}
                  onKeyDown={(e) => { if (e.key === "Enter" && e.metaKey) handleParse(); }}
                  autoFocus
                />
              </div>

              {/* Example chips */}
              <div className="flex flex-wrap gap-2 mb-5">
                {NLP_EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => { setNlpText(ex); setParsed(null); }}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs rounded-full transition-colors"
                  >
                    {ex}
                  </button>
                ))}
              </div>

              {parseError && (
                <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-300 text-sm">
                  {parseError}
                </div>
              )}

              {/* Parsed preview */}
              {parsed && (
                <div className="mb-5 p-4 bg-gray-800 rounded-xl border border-gray-600">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-green-400 text-sm font-medium">
                      ✓ Rule parsed
                    </span>
                    <span className="text-xs text-gray-500">
                      {parsed.source === "ai" ? "via AI" : "via pattern matching"}
                      {" · "}
                      {Math.round(parsed.confidence * 100)}% confidence
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Rule Name</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Scope</label>
                        <div className="px-2 py-1.5 bg-gray-700 rounded-lg text-sm text-gray-300">
                          {formatScopeSummary(parsed)}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Condition</label>
                        <div className="px-2 py-1.5 bg-gray-700 rounded-lg text-sm text-gray-300">
                          {formatConditionSummary(parsed)}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Action</label>
                        <select
                          className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white focus:outline-none"
                          value={editedActionType}
                          onChange={(e) => setEditedActionType(e.target.value)}
                        >
                          <option value="block">Block</option>
                          <option value="warn">Warn</option>
                          <option value="require_approval">Require Approval</option>
                          <option value="escalate_risk">Escalate Risk</option>
                          <option value="notify">Notify</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setShowManualForm(true)}
                    className="mt-3 text-xs text-gray-500 hover:text-gray-300 underline"
                  >
                    Edit all fields manually
                  </button>
                </div>
              )}

              {saveError && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-sm">
                  {saveError}
                </div>
              )}

              <div className="flex gap-3">
                {!parsed ? (
                  <button
                    onClick={handleParse}
                    disabled={parsing || !nlpText.trim()}
                    className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {parsing ? "Parsing..." : "Parse Rule →"}
                  </button>
                ) : (
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl disabled:opacity-50 transition-colors"
                  >
                    {saving ? "Saving..." : "Save Rule ✓"}
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-colors"
                >
                  Cancel
                </button>
              </div>

              <button
                onClick={() => setShowManualForm(true)}
                className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-300 transition-colors"
              >
                Skip NLP — use the manual form
              </button>
            </>
          ) : (
            <RuleForm
              initialData={parsed || undefined}
              onSubmit={async (data) => {
                await rulesApi.create(data);
                onSuccess();
              }}
              onCancel={onClose}
              submitLabel="Create Rule"
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Edit Dialog ──────────────────────────────────────────────────────────────

function RuleFormDialog({
  rule,
  onClose,
  onSuccess,
}: {
  rule: Rule;
  onClose: () => void;
  onSuccess: () => void;
}) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-white">Edit Rule</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">×</button>
          </div>
          <RuleForm
            initialData={rule}
            onSubmit={async (data) => {
              await rulesApi.update(rule.id, data);
              onSuccess();
            }}
            onCancel={onClose}
            submitLabel="Update Rule"
          />
        </div>
      </div>
    </div>
  );
}

// ─── Shared Form ──────────────────────────────────────────────────────────────

function RuleForm({
  initialData,
  onSubmit,
  onCancel,
  submitLabel = "Save",
}: {
  initialData?: Partial<Rule | ParsedRule>;
  onSubmit: (data: any) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}) {
  const [formData, setFormData] = useState({
    name: initialData?.name || "",
    description: initialData?.description || "",
    scope_type: initialData?.scope_type || "global",
    scope_value: initialData?.scope_value || "",
    scope_tags: initialData?.scope_tags || [],
    condition_type: initialData?.condition_type || "always",
    condition_config: initialData?.condition_config || {},
    action_type: initialData?.action_type || "warn",
    action_config: initialData?.action_config || {},
    priority: initialData?.priority || 50,
    enabled: (initialData as any)?.enabled ?? true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onSubmit(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save rule.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Rule Name *</label>
        <input
          type="text"
          required
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="e.g., No deployments during month-end"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
        <textarea
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
          rows={2}
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Explain when and why this rule applies"
        />
      </div>

      {/* Scope */}
      <div className="border-t border-gray-700 pt-4">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Scope</h4>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Applies to</label>
            <select
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
              value={formData.scope_type}
              onChange={(e) => setFormData({ ...formData, scope_type: e.target.value, scope_value: "", scope_tags: [] })}
            >
              <option value="global">All deployments</option>
              <option value="environment">Environment</option>
              <option value="tag">Tag</option>
              <option value="asset_group">Asset Group</option>
              <option value="asset">Specific Asset</option>
            </select>
          </div>
          {formData.scope_type === "tag" ? (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Tags</label>
              <TagAutocomplete
                value={formData.scope_tags || []}
                onChange={(tags) => setFormData({ ...formData, scope_tags: tags })}
                placeholder="Select tags..."
              />
            </div>
          ) : formData.scope_type !== "global" ? (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Value</label>
              <input
                type="text"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
                value={formData.scope_value}
                onChange={(e) => setFormData({ ...formData, scope_value: e.target.value })}
                placeholder={formData.scope_type === "environment" ? "e.g., production" : "e.g., web-servers"}
              />
            </div>
          ) : null}
        </div>
      </div>

      {/* Condition */}
      <div className="border-t border-gray-700 pt-4">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">When does this trigger?</h4>
        <select
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none mb-3"
          value={formData.condition_type}
          onChange={(e) => setFormData({ ...formData, condition_type: e.target.value, condition_config: {} })}
        >
          <option value="always">Always</option>
          <option value="time_window">Time Window</option>
          <option value="calendar">Calendar Event</option>
        </select>

        {formData.condition_type === "time_window" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Window Type</label>
              <select
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
                value={formData.condition_config.type || "month_end"}
                onChange={(e) => setFormData({ ...formData, condition_config: { ...formData.condition_config, type: e.target.value } })}
              >
                <option value="month_end">Month End</option>
                <option value="quarter_end">Quarter End</option>
                <option value="day_of_week">Day of Week</option>
              </select>
            </div>
            {formData.condition_config.type === "day_of_week" ? (
              <div>
                <label className="block text-xs text-gray-400 mb-1">Days</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
                  value={(formData.condition_config.days || []).join(", ")}
                  onChange={(e) => setFormData({ ...formData, condition_config: { ...formData.condition_config, days: e.target.value.split(",").map((d) => d.trim()).filter(Boolean) } })}
                  placeholder="Monday, Friday"
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs text-gray-400 mb-1">Days before period end</label>
                <input
                  type="number"
                  min={1} max={15}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
                  value={formData.condition_config.days_before || 3}
                  onChange={(e) => setFormData({ ...formData, condition_config: { ...formData.condition_config, days_before: parseInt(e.target.value) } })}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action */}
      <div className="border-t border-gray-700 pt-4">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">What happens?</h4>
        <select
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
          value={formData.action_type}
          onChange={(e) => setFormData({ ...formData, action_type: e.target.value, action_config: {} })}
        >
          <option value="warn">Warn — allow but show warning</option>
          <option value="block">Block — prevent deployment</option>
          <option value="require_approval">Require Approval — gate on review</option>
          <option value="escalate_risk">Escalate Risk — multiply risk score</option>
          <option value="notify">Notify — send alert only</option>
        </select>

        {formData.action_type === "require_approval" && (
          <div className="mt-3">
            <label className="block text-xs text-gray-400 mb-1">Minimum Approvers</label>
            <input
              type="number" min={1} max={10}
              className="w-24 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
              value={formData.action_config.min_approvers || 1}
              onChange={(e) => setFormData({ ...formData, action_config: { ...formData.action_config, min_approvers: parseInt(e.target.value) } })}
            />
          </div>
        )}
      </div>

      {/* Priority & Enable */}
      <div className="border-t border-gray-700 pt-4 flex items-center justify-between gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Priority (higher = first)</label>
          <input
            type="number" min={0} max={1000}
            className="w-24 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none"
            value={formData.priority}
            onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.enabled}
            onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
            className="w-4 h-4"
          />
          Enabled
        </label>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl disabled:opacity-50 transition-colors text-sm"
        >
          {loading ? "Saving..." : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-colors text-sm"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
