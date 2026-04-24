"use client";

import { useEffect, useState } from "react";
import { apiCall } from "@/lib/api";

interface AlertChannel {
  slack: boolean;
  teams: boolean;
  email: boolean;
  in_app: boolean;
}

interface AlertRule {
  id: string;
  label: string;
  description: string;
  channels: AlertChannel;
  available_channels: (keyof AlertChannel)[];
}

const DEFAULT_RULES: AlertRule[] = [
  {
    id: "kev_vuln",
    label: "New KEV vulnerability affects my assets",
    description: "Triggered when a vulnerability is added to CISA KEV and matches an asset you own.",
    channels: { slack: true, teams: false, email: true, in_app: true },
    available_channels: ["slack", "teams", "email", "in_app"],
  },
  {
    id: "bundle_failed",
    label: "Bundle execution failed",
    description: "Triggered when a patch bundle encounters errors during execution.",
    channels: { slack: true, teams: false, email: false, in_app: true },
    available_channels: ["slack", "in_app"],
  },
  {
    id: "approval_needed",
    label: "Approval required for bundle",
    description: "Triggered when a patch bundle requires your approval before it can run.",
    channels: { slack: true, teams: false, email: true, in_app: true },
    available_channels: ["slack", "email", "in_app"],
  },
  {
    id: "sla_breach",
    label: "SLA breach approaching (24h warning)",
    description: "Triggered 24 hours before a vulnerability's SLA deadline is breached.",
    channels: { slack: true, teams: false, email: true, in_app: true },
    available_channels: ["slack", "email", "in_app"],
  },
  {
    id: "weekly_digest",
    label: "Weekly digest",
    description: "Weekly summary of vulnerabilities, bundle outcomes, and goal progress.",
    channels: { slack: false, teams: false, email: true, in_app: false },
    available_channels: ["email"],
  },
];

const CHANNEL_LABELS: Record<keyof AlertChannel, string> = {
  slack: "Slack",
  teams: "Teams",
  email: "Email",
  in_app: "In-App",
};

const CHANNEL_ICONS: Record<keyof AlertChannel, string> = {
  slack: "💬",
  teams: "🟦",
  email: "📧",
  in_app: "🔔",
};

export default function AlertSettingsPage() {
  const [rules, setRules] = useState<AlertRule[]>(DEFAULT_RULES);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await apiCall<any>("/settings");
      const savedRules = data?.settings?.notifications?.alert_rules;
      if (savedRules && Array.isArray(savedRules)) {
        // Merge saved channels into default rules
        setRules((prev) =>
          prev.map((rule) => {
            const saved = savedRules.find((r: any) => r.id === rule.id);
            if (saved) return { ...rule, channels: { ...rule.channels, ...saved.channels } };
            return rule;
          })
        );
      }
    } catch (e) {
      console.error("Failed to load settings:", e);
    } finally {
      setLoading(false);
    }
  };

  const toggleChannel = (ruleId: string, channel: keyof AlertChannel) => {
    setRules((prev) =>
      prev.map((rule) => {
        if (rule.id !== ruleId) return rule;
        if (!rule.available_channels.includes(channel)) return rule;
        return {
          ...rule,
          channels: { ...rule.channels, [channel]: !rule.channels[channel] },
        };
      })
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiCall("/settings", {
        method: "POST",
        body: JSON.stringify({
          settings: {
            notifications: {
              alert_rules: rules.map(({ id, channels }) => ({ id, channels })),
            },
          },
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError("Failed to save settings. Please try again.");
      console.error("Save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Alert Rules</h1>
        <p className="text-gray-400">
          Configure which events trigger notifications and how you receive them.
        </p>
      </div>

      {/* Rules */}
      <div className="space-y-4">
        {rules.map((rule) => (
          <div key={rule.id} className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <div className="mb-3">
              <h3 className="text-white font-semibold">{rule.label}</h3>
              <p className="text-gray-400 text-sm mt-0.5">{rule.description}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              {(["slack", "teams", "email", "in_app"] as (keyof AlertChannel)[]).map((ch) => {
                const available = rule.available_channels.includes(ch);
                const active = rule.channels[ch];
                return (
                  <button
                    key={ch}
                    onClick={() => toggleChannel(rule.id, ch)}
                    disabled={!available}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                      !available
                        ? "opacity-30 cursor-not-allowed border-gray-700 text-gray-500"
                        : active
                        ? "bg-blue-600 border-blue-500 text-white"
                        : "bg-gray-700 border-gray-600 text-gray-300 hover:border-gray-500"
                    }`}
                    title={!available ? "Not available for this alert type" : undefined}
                  >
                    <span>{CHANNEL_ICONS[ch]}</span>
                    <span>{CHANNEL_LABELS[ch]}</span>
                    {available && (
                      <span
                        className={`w-2 h-2 rounded-full ${active ? "bg-white" : "bg-gray-500"}`}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Save button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
        >
          {saving ? "Saving…" : "Save Alert Rules"}
        </button>
        {saved && (
          <span className="text-green-400 text-sm font-medium">✓ Saved!</span>
        )}
      </div>

      {/* Help note */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
        <p className="text-gray-400 text-sm">
          <span className="text-gray-300 font-medium">Note:</span> Slack and Teams notifications
          require webhook URLs configured in{" "}
          <a href="/settings/notifications" className="text-blue-400 hover:underline">
            Settings → Notifications
          </a>
          . Email requires a verified address in your profile.
        </p>
      </div>
    </div>
  );
}
