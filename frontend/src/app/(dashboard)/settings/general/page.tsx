"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiCall } from "@/lib/api";

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const DATE_FORMATS = [
  { value: "MM/DD/YYYY", label: "MM/DD/YYYY (US)" },
  { value: "DD/MM/YYYY", label: "DD/MM/YYYY (European)" },
  { value: "YYYY-MM-DD", label: "YYYY-MM-DD (ISO)" },
];

const THEMES = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System Default" },
];

export default function GeneralSettingsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [settings, setSettings] = useState({
    display: {
      timezone: "America/New_York",
      date_format: "MM/DD/YYYY",
      theme: "system",
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

  const updateDisplay = (key: string, value: string) => {
    setSettings({
      ...settings,
      display: {
        ...settings.display,
        [key]: value,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="text-white">Loading settings...</div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/settings" className="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
            ← Back to Settings
          </Link>
          <h1 className="text-3xl font-bold text-white">General Settings</h1>
          <p className="text-gray-400 mt-1">Organization and display preferences</p>
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
        <div className={`p-4 rounded-lg ${saveMessage.includes("success") ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
          {saveMessage}
        </div>
      )}

      <div className="bg-gray-800 rounded-lg p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Timezone
          </label>
          <select
            value={settings.display.timezone}
            onChange={(e) => updateDisplay("timezone", e.target.value)}
            className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
          <p className="text-sm text-gray-400 mt-1">
            Used for scheduling and displaying timestamps
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Date Format
          </label>
          <select
            value={settings.display.date_format}
            onChange={(e) => updateDisplay("date_format", e.target.value)}
            className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {DATE_FORMATS.map((format) => (
              <option key={format.value} value={format.value}>
                {format.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Theme
          </label>
          <select
            value={settings.display.theme}
            onChange={(e) => updateDisplay("theme", e.target.value)}
            className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {THEMES.map((theme) => (
              <option key={theme.value} value={theme.value}>
                {theme.label}
              </option>
            ))}
          </select>
          <p className="text-sm text-gray-400 mt-1">
            Currently only dark theme is supported
          </p>
        </div>
      </div>
    </div>
  );
}
