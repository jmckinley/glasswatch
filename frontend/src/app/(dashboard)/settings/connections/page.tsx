"use client";

import { useState, useEffect, useRef } from "react";
import { connectionsApi } from "@/lib/api";

interface Connection {
  id: string;
  provider: string;
  name: string;
  status: string;
  config: Record<string, any>;
  last_health_check?: string;
  last_error?: string;
  created_at: string;
  updated_at?: string;
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
  tenable: "🔍",
  qualys: "🛡️",
  rapid7: "⚡",
};

// One-liner CTAs shown in the provider picker for scanners
const SCANNER_BENEFIT: Record<string, string> = {
  tenable: "Sync Tenable.io findings to keep your vulnerability list current automatically.",
  qualys: "Pull Qualys VMDR scan results directly into Glasswatch for unified prioritization.",
  rapid7: "Import Rapid7 InsightVM data so every finding lands in your risk-scoring engine.",
};

const STATUS_CONFIG: Record<string, { dot: string; label: string; text: string }> = {
  active: { dot: "bg-green-500", label: "Connected", text: "text-green-400" },
  pending: { dot: "bg-yellow-500", label: "Pending", text: "text-yellow-400" },
  error: { dot: "bg-red-500", label: "Error", text: "text-red-400" },
  disabled: { dot: "bg-gray-500", label: "Disabled", text: "text-gray-400" },
};

function StatusDot({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
      <span className={`text-xs font-medium ${cfg.text}`}>{cfg.label}</span>
    </span>
  );
}

function TestResult({ result }: { result: { success: boolean; message: string } | null }) {
  if (!result) return null;
  return (
    <div
      className={`mt-2 p-2 rounded-lg text-xs ${
        result.success
          ? "bg-green-500/10 border border-green-500/20 text-green-300"
          : "bg-red-500/10 border border-red-500/20 text-red-300"
      }`}
    >
      {result.success ? "✓" : "✗"} {result.message}
    </div>
  );
}

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [conns, prov] = await Promise.all([
        connectionsApi.list().catch(() => []),
        connectionsApi.providers().catch(() => ({ providers: [] })),
      ]);
      setConnections(Array.isArray(conns) ? conns : []);
      setProviders(prov?.providers ?? []);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const result = await connectionsApi.test(id);
      setTestResults((prev) => ({ ...prev, [id]: result }));
      await loadData(); // refresh status
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: { success: false, message: "Request failed" } }));
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this connection? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      await connectionsApi.delete(id);
      setConnections((prev) => prev.filter((c) => c.id !== id));
    } finally {
      setDeletingId(null);
    }
  };

  const startEdit = (conn: Connection) => {
    setEditingId(conn.id);
    // Build editable form from current config (masked values shown as empty)
    const prov = providers.find((p) => p.name === conn.provider);
    const fields = [...(prov?.required_fields ?? []), ...(prov?.optional_fields ?? [])];
    const initial: Record<string, string> = { name: conn.name };
    fields.forEach((f) => { initial[f] = ""; }); // start empty so user can enter new values
    setEditForm(initial);
  };

  const handleSaveEdit = async (id: string) => {
    setSaving(true);
    try {
      const config: Record<string, string> = {};
      const prov = providers.find((p) => p.name === connections.find((c) => c.id === id)?.provider);
      const fields = [...(prov?.required_fields ?? []), ...(prov?.optional_fields ?? [])];
      fields.forEach((f) => {
        if (editForm[f]) config[f] = editForm[f];
      });
      await connectionsApi.update(id, {
        name: editForm.name || undefined,
        config: Object.keys(config).length > 0 ? config : undefined,
      });
      setEditingId(null);
      await loadData();
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitNew = async () => {
    if (!selectedProvider) return;
    const missing = selectedProvider.required_fields.filter((f) => !formData[f]);
    if (missing.length) {
      alert(`Fill in required fields: ${missing.join(", ")}`);
      return;
    }
    setSaving(true);
    try {
      await connectionsApi.create({
        provider: selectedProvider.name,
        name: formData.name || `${selectedProvider.display_name} Connection`,
        config: formData,
      });
      setShowAddModal(false);
      setSelectedProvider(null);
      setFormData({});
      await loadData();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Connections</h1>
          <p className="text-gray-400">Manage cloud providers, scanners, and external services</p>
        </div>
        <button
          onClick={() => { setShowAddModal(true); setSelectedProvider(null); setFormData({}); }}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          + Add Connection
        </button>
      </div>

      {/* Connection cards */}
      {loading ? (
        <div className="text-gray-400 text-sm">Loading connections…</div>
      ) : connections.length === 0 ? (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center">
          <div className="text-5xl mb-4">🔌</div>
          <h3 className="text-xl font-semibold text-white mb-2">No connections yet</h3>
          <p className="text-gray-400 mb-6">Connect scanners and cloud providers to enable vulnerability sync</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Add Your First Connection
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {connections.map((conn) => (
            <div key={conn.id} className="bg-gray-800 border border-gray-700 rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                {/* Left: icon + name + status */}
                <div className="flex items-center gap-4 min-w-0">
                  <span className="text-3xl flex-shrink-0">{PROVIDER_ICONS[conn.provider] ?? "🔗"}</span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-white font-semibold">{conn.name}</h3>
                      <span className="text-gray-500 text-xs capitalize">{conn.provider}</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <StatusDot status={conn.status} />
                      {conn.last_health_check && (
                        <span className="text-gray-500 text-xs">
                          Checked {new Date(conn.last_health_check).toLocaleString()}
                        </span>
                      )}
                      {!conn.last_health_check && (
                        <span className="text-gray-600 text-xs">Never checked</span>
                      )}
                    </div>
                    {conn.last_error && (
                      <p className="text-red-400 text-xs mt-1 truncate max-w-lg">{conn.last_error}</p>
                    )}
                  </div>
                </div>

                {/* Right: actions */}
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleTest(conn.id)}
                    disabled={testingId === conn.id}
                    className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded-lg disabled:opacity-50 transition-colors"
                  >
                    {testingId === conn.id ? "Testing…" : "Test"}
                  </button>
                  <button
                    onClick={() => editingId === conn.id ? setEditingId(null) : startEdit(conn)}
                    className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded-lg transition-colors"
                  >
                    {editingId === conn.id ? "Cancel" : "Edit"}
                  </button>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    disabled={deletingId === conn.id}
                    className="px-3 py-1.5 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded-lg disabled:opacity-50 transition-colors"
                  >
                    {deletingId === conn.id ? "…" : "Delete"}
                  </button>
                </div>
              </div>

              {/* Test result */}
              {testResults[conn.id] && <TestResult result={testResults[conn.id]} />}

              {/* Inline edit form */}
              {editingId === conn.id && (() => {
                const prov = providers.find((p) => p.name === conn.provider);
                const allFields = [...(prov?.required_fields ?? []), ...(prov?.optional_fields ?? [])];
                return (
                  <div className="mt-4 pt-4 border-t border-gray-700 space-y-3">
                    <p className="text-xs text-gray-400">Leave credential fields empty to keep current values.</p>
                    <div>
                      <label className="block text-xs font-medium text-gray-300 mb-1">Connection Name</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        value={editForm.name ?? conn.name}
                        onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                      />
                    </div>
                    {allFields.map((field) => (
                      <div key={field}>
                        <label className="block text-xs font-medium text-gray-300 mb-1">
                          {field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                        </label>
                        <input
                          type={field.includes("secret") || field.includes("password") || field.includes("key") ? "password" : "text"}
                          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                          value={editForm[field] ?? ""}
                          onChange={(e) => setEditForm((f) => ({ ...f, [field]: e.target.value }))}
                          placeholder="Enter new value to update…"
                        />
                      </div>
                    ))}
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSaveEdit(conn.id)}
                        disabled={saving}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-50 transition-colors"
                      >
                        {saving ? "Saving…" : "Save Changes"}
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      )}

      {/* Add Connection Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-gray-700">
              <h2 className="text-xl font-bold text-white">
                {selectedProvider ? `Configure ${selectedProvider.display_name}` : "Add Connection"}
              </h2>
              <button
                onClick={() => { setShowAddModal(false); setSelectedProvider(null); }}
                className="text-gray-400 hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="p-5">
              {!selectedProvider ? (
                <div className="grid grid-cols-2 gap-3">
                  {providers.map((prov) => (
                    <button
                      key={prov.name}
                      onClick={() => {
                        setSelectedProvider(prov);
                        const init: Record<string, string> = {};
                        [...prov.required_fields, ...prov.optional_fields].forEach((f) => { init[f] = ""; });
                        setFormData(init);
                      }}
                      className="p-4 bg-gray-700 hover:bg-gray-600 border-2 border-transparent hover:border-blue-500 rounded-xl text-left transition-all"
                    >
                      <div className="text-3xl mb-2">{PROVIDER_ICONS[prov.name] ?? "🔗"}</div>
                      <h3 className="text-white font-medium text-sm mb-1">{prov.display_name}</h3>
                      <p className="text-gray-400 text-xs">
                        {SCANNER_BENEFIT[prov.name] ?? prov.description}
                      </p>
                      {SCANNER_BENEFIT[prov.name] && (
                        <span className="mt-2 inline-block text-xs font-semibold text-blue-400">
                          Connect →
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Connection Name</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                      value={formData.name ?? ""}
                      onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                      placeholder={`${selectedProvider.display_name} Connection`}
                    />
                  </div>
                  {selectedProvider.required_fields.map((field) => (
                    <div key={field}>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        {field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} <span className="text-red-400">*</span>
                      </label>
                      <input
                        type={field.includes("secret") || field.includes("password") || field.includes("key") ? "password" : "text"}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        value={formData[field] ?? ""}
                        onChange={(e) => setFormData((f) => ({ ...f, [field]: e.target.value }))}
                      />
                    </div>
                  ))}
                  {selectedProvider.optional_fields.length > 0 && (
                    <>
                      <p className="text-xs text-gray-500 mt-2">Optional</p>
                      {selectedProvider.optional_fields.map((field) => (
                        <div key={field}>
                          <label className="block text-sm font-medium text-gray-300 mb-1">
                            {field.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                          </label>
                          <input
                            type="text"
                            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                            value={formData[field] ?? ""}
                            onChange={(e) => setFormData((f) => ({ ...f, [field]: e.target.value }))}
                          />
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-between p-5 border-t border-gray-700">
              <button
                onClick={() => {
                  if (selectedProvider) setSelectedProvider(null);
                  else setShowAddModal(false);
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                {selectedProvider ? "← Back" : "Cancel"}
              </button>
              {selectedProvider && (
                <button
                  onClick={handleSubmitNew}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
                >
                  {saving ? "Creating…" : "Create Connection"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
