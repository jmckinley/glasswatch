"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiCall } from "@/lib/api";

export default function SecuritySettingsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [settings, setSettings] = useState({
    security: {
      auto_approve_low_risk: false,
      require_2_approvers: true,
      max_bundle_size: 50,
    },
  });
  const [saveMessage, setSaveMessage] = useState("");

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

  const updateSecurity = (key: string, value: any) => {
    setSettings({
      ...settings,
      security: {
        ...settings.security,
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
          <h1 className="text-3xl font-bold text-white">Security Settings</h1>
          <p className="text-gray-400 mt-1">
            Configure approval policies and security controls
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
        {/* Approval Policies */}
        <div className="pb-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">
            Approval Policies
          </h3>
          
          <div className="space-y-4">
            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">Auto-Approve Low Risk</div>
                <div className="text-sm text-gray-400">
                  Automatically approve patches with low risk score (&lt; 3.0)
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.security.auto_approve_low_risk}
                onChange={(e) =>
                  updateSecurity("auto_approve_low_risk", e.target.checked)
                }
                className="w-5 h-5 rounded text-blue-500"
              />
            </label>

            <label className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">
                  Require Two Approvers
                </div>
                <div className="text-sm text-gray-400">
                  High-risk patches must be approved by two people
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.security.require_2_approvers}
                onChange={(e) =>
                  updateSecurity("require_2_approvers", e.target.checked)
                }
                className="w-5 h-5 rounded text-blue-500"
              />
            </label>
          </div>
        </div>

        {/* Bundle Configuration */}
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">
            Bundle Configuration
          </h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Maximum Bundle Size
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="10"
                max="100"
                step="10"
                value={settings.security.max_bundle_size}
                onChange={(e) =>
                  updateSecurity("max_bundle_size", parseInt(e.target.value))
                }
                className="flex-1"
              />
              <div className="w-16 px-3 py-2 bg-gray-700 text-white rounded-lg text-center">
                {settings.security.max_bundle_size}
              </div>
            </div>
            <p className="text-sm text-gray-400 mt-2">
              Maximum number of patches that can be bundled together
            </p>
          </div>
        </div>

        {/* Risk Tolerance Info */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">ℹ️</span>
            <div>
              <h4 className="font-medium text-blue-400 mb-1">
                Security Recommendations
              </h4>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Keep auto-approval disabled for production environments</li>
                <li>• Require two approvers for critical infrastructure</li>
                <li>• Smaller bundle sizes reduce deployment risk</li>
                <li>• Enable critical alerts for KEV vulnerabilities</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
