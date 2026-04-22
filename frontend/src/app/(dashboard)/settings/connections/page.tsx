"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface Connection {
  id: string;
  provider: string;
  name: string;
  status: string;
  last_health_check?: string;
  last_error?: string;
  created_at: string;
}

interface Provider {
  name: string;
  display_name: string;
  description: string;
  required_fields: string[];
  optional_fields: string[];
}

const PROVIDER_ICONS: Record<string, string> = {
  aws: "☁️",
  azure: "🔷",
  gcp: "🌩️",
  slack: "💬",
  jira: "📋",
  servicenow: "🎫",
  webhook: "🔗",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500",
  pending: "bg-yellow-500",
  error: "bg-red-500",
  disabled: "bg-gray-500",
};

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [testingConnection, setTestingConnection] = useState<string | null>(null);

  useEffect(() => {
    fetchConnections();
    fetchProviders();
  }, []);

  const fetchConnections = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/v1/connections", {
        credentials: "include",
      });
      
      if (response.ok) {
        const data = await response.json();
        setConnections(data);
      }
    } catch (error) {
      console.error("Failed to fetch connections:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProviders = async () => {
    try {
      const response = await fetch("/api/v1/connections/providers", {
        credentials: "include",
      });
      
      if (response.ok) {
        const data = await response.json();
        setProviders(data.providers);
      }
    } catch (error) {
      console.error("Failed to fetch providers:", error);
    }
  };

  const handleAddConnection = () => {
    setShowAddModal(true);
    setSelectedProvider(null);
    setFormData({});
  };

  const handleProviderSelect = (provider: Provider) => {
    setSelectedProvider(provider);
    // Initialize form data with empty values for required fields
    const initialData: Record<string, string> = {};
    provider.required_fields.forEach((field) => {
      initialData[field] = "";
    });
    setFormData(initialData);
  };

  const handleFormChange = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmitConnection = async () => {
    if (!selectedProvider) return;

    // Validate required fields
    const missingFields = selectedProvider.required_fields.filter(
      (field) => !formData[field]
    );
    if (missingFields.length > 0) {
      alert(`Please fill in required fields: ${missingFields.join(", ")}`);
      return;
    }

    try {
      const response = await fetch("/api/v1/connections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          provider: selectedProvider.name,
          name: formData.name || `${selectedProvider.display_name} Connection`,
          config: formData,
        }),
      });

      if (response.ok) {
        setShowAddModal(false);
        fetchConnections();
      } else {
        const error = await response.json();
        alert(`Failed to create connection: ${error.detail}`);
      }
    } catch (error) {
      alert(`Failed to create connection: ${error}`);
    }
  };

  const handleTestConnection = async (connectionId: string) => {
    try {
      setTestingConnection(connectionId);
      const response = await fetch(`/api/v1/connections/${connectionId}/test`, {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        const result = await response.json();
        alert(result.success ? `✅ ${result.message}` : `❌ ${result.message}`);
        fetchConnections(); // Refresh to show updated status
      }
    } catch (error) {
      alert(`Failed to test connection: ${error}`);
    } finally {
      setTestingConnection(null);
    }
  };

  const handleDeleteConnection = async (connectionId: string) => {
    if (!confirm("Are you sure you want to delete this connection?")) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/connections/${connectionId}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        fetchConnections();
      }
    } catch (error) {
      alert(`Failed to delete connection: ${error}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Connections</h1>
          <p className="text-gray-400">Manage cloud providers and external services</p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/settings"
            className="text-blue-400 hover:text-blue-300 transition-colors"
          >
            ← Back to Settings
          </Link>
          <button
            onClick={handleAddConnection}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
          >
            + Add Connection
          </button>
        </div>
      </div>

      {/* Connections List */}
      {loading ? (
        <div className="text-gray-400">Loading connections...</div>
      ) : connections.length === 0 ? (
        <div className="bg-gray-800 rounded-lg border-2 border-gray-700 p-12 text-center">
          <div className="text-6xl mb-4">🔌</div>
          <h3 className="text-xl font-semibold text-white mb-2">No connections yet</h3>
          <p className="text-gray-400 mb-6">
            Connect cloud providers and external services to enable automated discovery
          </p>
          <button
            onClick={handleAddConnection}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
          >
            Add Your First Connection
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {connections.map((conn) => (
            <div
              key={conn.id}
              className="bg-gray-800 rounded-lg border-2 border-gray-700 p-6 hover:border-gray-600 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-4xl">{PROVIDER_ICONS[conn.provider] || "🔗"}</div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">{conn.name}</h3>
                    <p className="text-gray-400 text-sm capitalize">{conn.provider}</p>
                  </div>
                </div>
                <div
                  className={`w-3 h-3 rounded-full ${STATUS_COLORS[conn.status] || "bg-gray-500"}`}
                  title={conn.status}
                />
              </div>

              {conn.last_health_check && (
                <div className="text-sm text-gray-400 mb-2">
                  Last checked: {new Date(conn.last_health_check).toLocaleString()}
                </div>
              )}

              {conn.last_error && (
                <div className="text-sm text-red-400 mb-4 p-2 bg-red-900/20 rounded">
                  {conn.last_error}
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => handleTestConnection(conn.id)}
                  disabled={testingConnection === conn.id}
                  className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md text-sm transition-colors disabled:bg-gray-800"
                >
                  {testingConnection === conn.id ? "Testing..." : "Test"}
                </button>
                <button
                  onClick={() => handleDeleteConnection(conn.id)}
                  className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Connection Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg border-2 border-gray-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-700">
              <h2 className="text-2xl font-bold text-white">Add Connection</h2>
            </div>

            <div className="p-6">
              {!selectedProvider ? (
                <div className="grid grid-cols-2 gap-4">
                  {providers.map((provider) => (
                    <button
                      key={provider.name}
                      onClick={() => handleProviderSelect(provider)}
                      className="p-6 bg-gray-700 hover:bg-gray-600 rounded-lg text-left transition-all border-2 border-transparent hover:border-blue-500"
                    >
                      <div className="text-4xl mb-2">{PROVIDER_ICONS[provider.name] || "🔗"}</div>
                      <h3 className="text-lg font-semibold text-white mb-1">
                        {provider.display_name}
                      </h3>
                      <p className="text-gray-400 text-sm">{provider.description}</p>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Connection Name
                    </label>
                    <input
                      type="text"
                      value={formData.name || ""}
                      onChange={(e) => handleFormChange("name", e.target.value)}
                      placeholder={`${selectedProvider.display_name} Connection`}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {selectedProvider.required_fields.map((field) => (
                    <div key={field}>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        {field.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())} *
                      </label>
                      <input
                        type={field.includes("secret") || field.includes("password") ? "password" : "text"}
                        value={formData[field] || ""}
                        onChange={(e) => handleFormChange(field, e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  ))}

                  {selectedProvider.optional_fields.length > 0 && (
                    <>
                      <div className="text-sm text-gray-400 mt-4">Optional Fields</div>
                      {selectedProvider.optional_fields.map((field) => (
                        <div key={field}>
                          <label className="block text-sm font-medium text-gray-300 mb-2">
                            {field.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                          </label>
                          <input
                            type="text"
                            value={formData[field] || ""}
                            onChange={(e) => handleFormChange(field, e.target.value)}
                            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
                          />
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-700 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setSelectedProvider(null);
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md transition-colors"
              >
                Cancel
              </button>
              {selectedProvider && (
                <button
                  onClick={handleSubmitConnection}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                >
                  Create Connection
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
