"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface SlackStatus {
  connected: boolean;
  team_name?: string;
  team_id?: string;
  installed_at?: string;
}

export default function IntegrationsPage() {
  const [slackStatus, setSlackStatus] = useState<SlackStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [testChannel, setTestChannel] = useState("#general");
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    fetchSlackStatus();
  }, []);

  const fetchSlackStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/v1/slack/status", {
        credentials: "include",
      });
      
      if (response.ok) {
        const data = await response.json();
        setSlackStatus(data);
      }
    } catch (error) {
      console.error("Failed to fetch Slack status:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectSlack = async () => {
    try {
      const response = await fetch("/api/v1/slack/install", {
        credentials: "include",
      });
      
      if (response.ok) {
        const data = await response.json();
        // Redirect to Slack OAuth
        window.location.href = data.authorization_url;
      }
    } catch (error) {
      console.error("Failed to initiate Slack connection:", error);
    }
  };

  const handleDisconnectSlack = async () => {
    if (!confirm("Are you sure you want to disconnect Slack?")) {
      return;
    }

    try {
      const response = await fetch("/api/v1/slack/disconnect", {
        method: "DELETE",
        credentials: "include",
      });
      
      if (response.ok) {
        setSlackStatus({ connected: false });
      }
    } catch (error) {
      console.error("Failed to disconnect Slack:", error);
    }
  };

  const handleTestMessage = async () => {
    try {
      setTestLoading(true);
      setTestResult(null);
      
      const response = await fetch("/api/v1/slack/test-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          channel: testChannel,
          text: "🧪 Test message from Glasswatch!",
        }),
      });
      
      if (response.ok) {
        setTestResult("✅ Test message sent successfully!");
      } else {
        const error = await response.json();
        setTestResult(`❌ Failed: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      setTestResult(`❌ Failed: ${error}`);
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Integrations</h1>
          <p className="text-gray-400">Connect collaboration tools and services</p>
        </div>
        <Link
          href="/settings"
          className="text-blue-400 hover:text-blue-300 transition-colors"
        >
          ← Back to Settings
        </Link>
      </div>

      {/* Slack Integration */}
      <div className="bg-gray-800 rounded-lg border-2 border-gray-700 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="text-5xl">💬</div>
            <div>
              <h2 className="text-2xl font-semibold text-white mb-1">Slack</h2>
              <p className="text-gray-400">
                Send patch alerts and approval requests to Slack channels
              </p>
            </div>
          </div>
          
          {loading ? (
            <div className="text-gray-400">Loading...</div>
          ) : slackStatus?.connected ? (
            <button
              onClick={handleDisconnectSlack}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors"
            >
              Disconnect
            </button>
          ) : (
            <button
              onClick={handleConnectSlack}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
            >
              Connect to Slack
            </button>
          )}
        </div>

        {slackStatus?.connected && (
          <div className="space-y-4">
            <div className="bg-gray-700 rounded-md p-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-gray-400 text-sm mb-1">Workspace</div>
                  <div className="text-white font-medium">{slackStatus.team_name}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm mb-1">Team ID</div>
                  <div className="text-white font-mono text-sm">{slackStatus.team_id}</div>
                </div>
                {slackStatus.installed_at && (
                  <div>
                    <div className="text-gray-400 text-sm mb-1">Connected</div>
                    <div className="text-white text-sm">
                      {new Date(slackStatus.installed_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Test Message Section */}
            <div className="border-t border-gray-700 pt-4">
              <h3 className="text-lg font-medium text-white mb-3">Test Connection</h3>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={testChannel}
                  onChange={(e) => setTestChannel(e.target.value)}
                  placeholder="#channel"
                  className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleTestMessage}
                  disabled={testLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-md transition-colors"
                >
                  {testLoading ? "Sending..." : "Send Test Message"}
                </button>
              </div>
              {testResult && (
                <div className={`mt-3 p-3 rounded-md ${
                  testResult.startsWith("✅") 
                    ? "bg-green-900/30 text-green-400 border border-green-700" 
                    : "bg-red-900/30 text-red-400 border border-red-700"
                }`}>
                  {testResult}
                </div>
              )}
            </div>

            {/* Channel Configuration */}
            <div className="border-t border-gray-700 pt-4">
              <h3 className="text-lg font-medium text-white mb-3">Channel Configuration</h3>
              <p className="text-gray-400 text-sm mb-3">
                Configure which Slack channels receive different types of notifications
              </p>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Patch Alerts
                  </label>
                  <input
                    type="text"
                    defaultValue="#alerts"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
                    placeholder="#alerts"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Approval Requests
                  </label>
                  <input
                    type="text"
                    defaultValue="#approvals"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
                    placeholder="#approvals"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Coming Soon Integrations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg border-2 border-gray-700 p-6 opacity-60">
          <div className="flex items-center gap-4 mb-3">
            <div className="text-4xl">📋</div>
            <div>
              <h3 className="text-xl font-semibold text-white">Jira</h3>
              <p className="text-gray-400 text-sm">Create tickets from patches</p>
            </div>
          </div>
          <div className="text-gray-500 text-sm">Coming soon</div>
        </div>

        <div className="bg-gray-800 rounded-lg border-2 border-gray-700 p-6 opacity-60">
          <div className="flex items-center gap-4 mb-3">
            <div className="text-4xl">🎫</div>
            <div>
              <h3 className="text-xl font-semibold text-white">ServiceNow</h3>
              <p className="text-gray-400 text-sm">ITSM integration</p>
            </div>
          </div>
          <div className="text-gray-500 text-sm">Coming soon</div>
        </div>
      </div>
    </div>
  );
}
