"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiCall, settingsApi } from "@/lib/api";

const DIGEST_FREQUENCIES = [
  { value: "realtime", label: "Real-time" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
];

export default function NotificationsSettingsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [settings, setSettings] = useState({
    notifications: {
      email_enabled: true,
      slack_enabled: false,
      slack_webhook_url: "",
      slack_channel: "",
      teams_enabled: false,
      teams_webhook_url: "",
      digest_frequency: "daily",
      critical_alerts: true,
    },
  });
  const [saveMessage, setSaveMessage] = useState("");
  const [slackTestResult, setSlackTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [teamsTestResult, setTeamsTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [testingSlack, setTestingSlack] = useState(false);
  const [testingTeams, setTestingTeams] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await apiCall<any>("/settings");
      setSettings(data.settings);
    } catch (error) {
      console.error("Failed to load settings:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async () => {
    setIsSaving(true);
    setSaveMessage("");
    try {
      await apiCall("/settings", {
        method: "PATCH",
        body: { settings },
      });
      setSaveMessage("Settings saved successfully!");
      setTimeout(() => setSaveMessage(""), 3000);
    } catch (error) {
      console.error("Failed to save settings:", error);
      setSaveMessage("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const updateNotifications = (key: string, value: any) => {
    setSettings({
      ...settings,
      notifications: {
        ...settings.notifications,
        [key]: value,
      },
    });
  };

  if (isLoading) {
    return <div className="text-white">Loading settings...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/settings"
            className="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block"
          >
            ← Back to Settings
          </Link>
          <h1 className="text-3xl font-bold text-white">Notification Settings</h1>
          <p className="text-gray-400 mt-1">
            Configure how and when you receive alerts
          </p>
        </div>
        <button
          onClick={saveSettings}
          disabled={isSaving}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
        >
          {isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {saveMessage && (
        <div
          className={`p-4 rounded-lg ${
            saveMessage.includes("success")
              ? "bg-green-500/20 text-green-400"
              : "bg-red-500/20 text-red-400"
          }`}
        >
          {saveMessage}
        </div>
      )}

      <div className="bg-gray-800 rounded-lg p-6 space-y-6">
        {/* Email Notifications */}
        <div className="pb-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Email Notifications</h3>
          
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">Enable Email Notifications</div>
                <div className="text-sm text-gray-400">
                  Receive updates via email
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.notifications.email_enabled}
                onChange={(e) =>
                  updateNotifications("email_enabled", e.target.checked)
                }
                className="w-5 h-5 rounded text-blue-500"
              />
            </label>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Digest Frequency
              </label>
              <select
                value={settings.notifications.digest_frequency}
                onChange={(e) =>
                  updateNotifications("digest_frequency", e.target.value)
                }
                disabled={!settings.notifications.email_enabled}
                className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {DIGEST_FREQUENCIES.map((freq) => (
                  <option key={freq.value} value={freq.value}>
                    {freq.label}
                  </option>
                ))}
              </select>
              <p className="text-sm text-gray-400 mt-1">
                How often to send summary emails
              </p>
            </div>
          </div>
        </div>

        {/* Slack Notifications */}
        <div className="pb-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Slack Integration</h3>
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">Enable Slack Notifications</div>
                <div className="text-sm text-gray-400">Send alerts to Slack channel</div>
              </div>
              <input type="checkbox" checked={settings.notifications.slack_enabled}
                onChange={(e) => updateNotifications("slack_enabled", e.target.checked)}
                className="w-5 h-5 rounded text-blue-500" />
            </label>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Webhook URL</label>
              <input type="url" value={(settings.notifications as any).slack_webhook_url || ""}
                onChange={(e) => updateNotifications("slack_webhook_url", e.target.value)}
                disabled={!settings.notifications.slack_enabled}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Channel Name</label>
              <input type="text" value={settings.notifications.slack_channel || ""}
                onChange={(e) => updateNotifications("slack_channel", e.target.value)}
                disabled={!settings.notifications.slack_enabled}
                placeholder="#security-alerts"
                className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
            </div>
            {settings.notifications.slack_enabled && (settings.notifications as any).slack_webhook_url && (
              <div>
                <button disabled={testingSlack}
                  onClick={async () => {
                    setTestingSlack(true);
                    try {
                      const r = await settingsApi.testConnection("slack", { webhook_url: (settings.notifications as any).slack_webhook_url });
                      setSlackTestResult(r);
                    } catch { setSlackTestResult({ success: false, message: "Request failed" }); }
                    finally { setTestingSlack(false); }
                  }}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg disabled:opacity-50">
                  {testingSlack ? "Testing..." : "Send Test Message"}
                </button>
                {slackTestResult && (
                  <div className={`mt-2 p-2 rounded text-xs ${slackTestResult.success ? "bg-green-500/10 text-green-300" : "bg-red-500/10 text-red-300"}`}>
                    {slackTestResult.success ? "✓" : "✗"} {slackTestResult.message}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Microsoft Teams */}
        <div className="pb-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Microsoft Teams</h3>
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">Enable Teams Notifications</div>
                <div className="text-sm text-gray-400">Send alerts to a Teams channel</div>
              </div>
              <input type="checkbox" checked={(settings.notifications as any).teams_enabled || false}
                onChange={(e) => updateNotifications("teams_enabled", e.target.checked)}
                className="w-5 h-5 rounded text-blue-500" />
            </label>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Incoming Webhook URL</label>
              <input type="url" value={(settings.notifications as any).teams_webhook_url || ""}
                onChange={(e) => updateNotifications("teams_webhook_url", e.target.value)}
                disabled={!(settings.notifications as any).teams_enabled}
                placeholder="https://yourcompany.webhook.office.com/..."
                className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
              <p className="text-xs text-gray-500 mt-1">Create via Teams channel → Connectors → Incoming Webhook</p>
            </div>
            {(settings.notifications as any).teams_enabled && (settings.notifications as any).teams_webhook_url && (
              <div>
                <button disabled={testingTeams}
                  onClick={async () => {
                    setTestingTeams(true);
                    try {
                      const r = await settingsApi.testConnection("teams", { webhook_url: (settings.notifications as any).teams_webhook_url });
                      setTeamsTestResult(r);
                    } catch { setTeamsTestResult({ success: false, message: "Request failed" }); }
                    finally { setTestingTeams(false); }
                  }}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg disabled:opacity-50">
                  {testingTeams ? "Testing..." : "Send Test Message"}
                </button>
                {teamsTestResult && (
                  <div className={`mt-2 p-2 rounded text-xs ${teamsTestResult.success ? "bg-green-500/10 text-green-300" : "bg-red-500/10 text-red-300"}`}>
                    {teamsTestResult.success ? "✓" : "✗"} {teamsTestResult.message}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Alert Preferences */}
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            Alert Preferences
          </h3>
          
          <label className="flex items-center justify-between">
            <div>
              <div className="font-medium text-white">Critical Alerts</div>
              <div className="text-sm text-gray-400">
                Always notify immediately for critical vulnerabilities
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.notifications.critical_alerts}
              onChange={(e) =>
                updateNotifications("critical_alerts", e.target.checked)
              }
              className="w-5 h-5 rounded text-blue-500"
            />
          </label>
        </div>
      </div>
    </div>
  );
}
