"use client";

import { useState, useEffect } from "react";
import { settingsApi } from "@/lib/api";

interface IntegrationSettings {
  vulncheck_api_key: string | null;
  vulncheck_api_key_configured: boolean;
  snapper_webhook_secret: string | null;
  snapper_webhook_secret_configured: boolean;
  jira_url: string | null;
  jira_email: string | null;
  jira_api_token: string | null;
  jira_api_token_configured: boolean;
  jira_project_key: string | null;
  servicenow_url: string | null;
  servicenow_username: string | null;
  servicenow_password: string | null;
  servicenow_password_configured: boolean;
}

interface AISettings {
  anthropic_api_key: string | null;
  anthropic_api_key_configured: boolean;
  ai_assistant_enabled: boolean;
  nlp_rules_enabled: boolean;
}

function ConfiguredBadge({ configured }: { configured: boolean }) {
  return configured ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-300 text-xs rounded-full">
      ✓ Configured
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-600/30 text-gray-400 text-xs rounded-full">
      Not set
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

function MaskedInput({
  label,
  value,
  onChange,
  placeholder,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm pr-16 focus:outline-none focus:border-blue-500"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "Enter value..."}
          autoComplete="off"
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 text-xs px-2 py-1"
        >
          {show ? "Hide" : "Show"}
        </button>
      </div>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});

  // VulnCheck
  const [vulncheckKey, setVulncheckKey] = useState("");
  const [vulncheckConfigured, setVulncheckConfigured] = useState(false);

  // Snapper
  const [snapperSecret, setSnapperSecret] = useState("");
  const [snapperConfigured, setSnapperConfigured] = useState(false);

  // Jira
  const [jiraUrl, setJiraUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [jiraProjectKey, setJiraProjectKey] = useState("");

  // ServiceNow
  const [snowUrl, setSnowUrl] = useState("");
  const [snowUser, setSnowUser] = useState("");
  const [snowPass, setSnowPass] = useState("");
  const [snowConfigured, setSnowConfigured] = useState(false);

  // AI
  const [anthropicKey, setAnthropicKey] = useState("");
  const [anthropicConfigured, setAnthropicConfigured] = useState(false);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [nlpEnabled, setNlpEnabled] = useState(true);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await settingsApi.get();
      const int: IntegrationSettings = data.settings?.integrations || {};
      const ai: AISettings = data.settings?.ai || {};

      setVulncheckConfigured(int.vulncheck_api_key_configured || false);
      setSnapperConfigured(int.snapper_webhook_secret_configured || false);
      setJiraUrl(int.jira_url || "");
      setJiraEmail(int.jira_email || "");
      setJiraConfigured(int.jira_api_token_configured || false);
      setJiraProjectKey(int.jira_project_key || "");
      setSnowUrl(int.servicenow_url || "");
      setSnowUser(int.servicenow_username || "");
      setSnowConfigured(int.servicenow_password_configured || false);
      setAnthropicConfigured(ai.anthropic_api_key_configured || false);
      setAiEnabled(ai.ai_assistant_enabled ?? true);
      setNlpEnabled(ai.nlp_rules_enabled ?? true);
    } catch (err) {
      console.error("Failed to load settings", err);
    } finally {
      setLoading(false);
    }
  };

  const save = async (section: string, data: any) => {
    setSaving(section);
    try {
      await settingsApi.update({ [section]: data });
      await loadSettings();
    } catch (err) {
      console.error("Save failed", err);
      alert("Failed to save settings");
    } finally {
      setSaving(null);
    }
  };

  const testConn = async (key: string, integration: string, config: Record<string, string>) => {
    setTesting(key);
    try {
      const result = await settingsApi.testConnection(integration, config);
      setTestResults((prev) => ({ ...prev, [key]: result }));
    } catch (err) {
      setTestResults((prev) => ({ ...prev, [key]: { success: false, message: "Request failed" } }));
    } finally {
      setTesting(null);
    }
  };

  if (loading) return <div className="p-6 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Integrations</h1>
        <p className="text-gray-400">Connect external services and configure API access</p>
      </div>

      {/* VulnCheck */}
      <Section title="VulnCheck" icon="🔍" description="Commercial vulnerability intelligence — CVE enrichment and exploit data">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">Status:</span>
            <ConfiguredBadge configured={vulncheckConfigured} />
          </div>
          <MaskedInput
            label="API Key"
            value={vulncheckKey}
            onChange={setVulncheckKey}
            placeholder={vulncheckConfigured ? "Enter new key to replace..." : "vc-..."}
            hint="Get your key from vulncheck.com/dashboard"
          />
          <div className="flex gap-2">
            <SaveBtn
              loading={saving === "vulncheck"}
              disabled={!vulncheckKey}
              onClick={() => save("integrations", { vulncheck_api_key: vulncheckKey })}
            />
            {vulncheckConfigured && (
              <ClearBtn onClick={() => save("integrations", { vulncheck_api_key: null, vulncheck_api_key_configured: false })} />
            )}
          </div>
        </div>
      </Section>

      {/* Snapper */}
      <Section title="Snapper Runtime" icon="🐟" description="Runtime reachability analysis — confirms which vulnerable code paths are actually executed">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">Status:</span>
            <ConfiguredBadge configured={snapperConfigured} />
          </div>
          <MaskedInput
            label="Webhook Secret"
            value={snapperSecret}
            onChange={setSnapperSecret}
            placeholder={snapperConfigured ? "Enter new secret to replace..." : "whsec_..."}
            hint="Used to validate incoming Snapper runtime events"
          />
          <SaveBtn
            loading={saving === "snapper"}
            disabled={!snapperSecret}
            onClick={() => save("integrations", { snapper_webhook_secret: snapperSecret })}
          />
        </div>
      </Section>

      {/* AI / Anthropic */}
      <Section title="AI Features" icon="🤖" description="Powers the AI assistant and natural language rule creation">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">API Key:</span>
            <ConfiguredBadge configured={anthropicConfigured} />
          </div>
          <MaskedInput
            label="Anthropic API Key"
            value={anthropicKey}
            onChange={setAnthropicKey}
            placeholder={anthropicConfigured ? "Enter new key to replace..." : "sk-ant-..."}
            hint="From console.anthropic.com — used for the AI assistant and NLP rule parsing"
          />
          <div className="grid grid-cols-2 gap-4">
            <Toggle
              label="AI Assistant"
              description="Chat assistant in sidebar"
              checked={aiEnabled}
              onChange={(v) => { setAiEnabled(v); save("ai", { ai_assistant_enabled: v }); }}
            />
            <Toggle
              label="NLP Rule Creation"
              description="Plain-English rule parser"
              checked={nlpEnabled}
              onChange={(v) => { setNlpEnabled(v); save("ai", { nlp_rules_enabled: v }); }}
            />
          </div>
          <div className="flex gap-2">
            <SaveBtn
              loading={saving === "ai"}
              disabled={!anthropicKey}
              onClick={() => save("ai", { anthropic_api_key: anthropicKey })}
            />
            {anthropicConfigured && (
              <ClearBtn onClick={() => save("ai", { anthropic_api_key: null, anthropic_api_key_configured: false })} />
            )}
          </div>
        </div>
      </Section>

      {/* Jira */}
      <Section title="Jira" icon="📋" description="Create tickets and track remediation in your Jira projects">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">Status:</span>
            <ConfiguredBadge configured={jiraConfigured} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Jira URL</label>
              <input
                type="url"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                value={jiraUrl}
                onChange={(e) => setJiraUrl(e.target.value)}
                placeholder="https://yourcompany.atlassian.net"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Project Key</label>
              <input
                type="text"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                value={jiraProjectKey}
                onChange={(e) => setJiraProjectKey(e.target.value)}
                placeholder="SEC"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input
              type="email"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              value={jiraEmail}
              onChange={(e) => setJiraEmail(e.target.value)}
              placeholder="your@company.com"
            />
          </div>
          <MaskedInput
            label="API Token"
            value={jiraToken}
            onChange={setJiraToken}
            placeholder={jiraConfigured ? "Enter new token to replace..." : "ATATT3x..."}
            hint="Generate from id.atlassian.com/manage-profile/security/api-tokens"
          />
          <div className="flex gap-2">
            <SaveBtn
              loading={saving === "jira"}
              disabled={!jiraUrl || !jiraEmail}
              onClick={() =>
                save("integrations", {
                  jira_url: jiraUrl,
                  jira_email: jiraEmail,
                  jira_api_token: jiraToken || undefined,
                  jira_project_key: jiraProjectKey,
                })
              }
            />
            <button
              disabled={!jiraUrl || !jiraEmail || !jiraToken || testing === "jira"}
              onClick={() => testConn("jira", "jira", { jira_url: jiraUrl, jira_email: jiraEmail, jira_api_token: jiraToken })}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg disabled:opacity-50 transition-colors"
            >
              {testing === "jira" ? "Testing..." : "Test Connection"}
            </button>
          </div>
          <TestResult result={testResults.jira || null} />
        </div>
      </Section>

      {/* ServiceNow */}
      <Section title="ServiceNow" icon="🎫" description="Sync remediation workflows with ServiceNow ITSM">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">Status:</span>
            <ConfiguredBadge configured={snowConfigured} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Instance URL</label>
            <input
              type="url"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              value={snowUrl}
              onChange={(e) => setSnowUrl(e.target.value)}
              placeholder="https://yourinstance.service-now.com"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
              <input
                type="text"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                value={snowUser}
                onChange={(e) => setSnowUser(e.target.value)}
                placeholder="glasswatch_svc"
              />
            </div>
            <MaskedInput
              label="Password"
              value={snowPass}
              onChange={setSnowPass}
              placeholder={snowConfigured ? "Enter new password..." : "••••••••"}
            />
          </div>
          <div className="flex gap-2">
            <SaveBtn
              loading={saving === "snow"}
              disabled={!snowUrl || !snowUser}
              onClick={() =>
                save("integrations", {
                  servicenow_url: snowUrl,
                  servicenow_username: snowUser,
                  servicenow_password: snowPass || undefined,
                })
              }
            />
            <button
              disabled={!snowUrl || !snowUser || !snowPass || testing === "snow"}
              onClick={() => testConn("snow", "servicenow", { servicenow_url: snowUrl, servicenow_username: snowUser, servicenow_password: snowPass })}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg disabled:opacity-50 transition-colors"
            >
              {testing === "snow" ? "Testing..." : "Test Connection"}
            </button>
          </div>
          <TestResult result={testResults.snow || null} />
        </div>
      </Section>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function Section({ title, icon, description, children }: { title: string; icon: string; description: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
      <div className="flex items-start gap-3 mb-5">
        <span className="text-2xl">{icon}</span>
        <div>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <p className="text-sm text-gray-400">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function SaveBtn({ loading, disabled, onClick }: { loading: boolean; disabled?: boolean; onClick: () => void }) {
  return (
    <button
      disabled={loading || disabled}
      onClick={onClick}
      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg disabled:opacity-50 transition-colors font-medium"
    >
      {loading ? "Saving..." : "Save"}
    </button>
  );
}

function ClearBtn({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={() => { if (confirm("Clear this credential?")) onClick(); }}
      className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded-lg transition-colors"
    >
      Clear
    </button>
  );
}

function Toggle({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer p-3 bg-gray-700/50 rounded-lg">
      <div className="relative mt-0.5">
        <input
          type="checkbox"
          className="sr-only"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div className={`w-9 h-5 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-gray-600"}`} />
        <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${checked ? "translate-x-4" : ""}`} />
      </div>
      <div>
        <div className="text-sm font-medium text-white">{label}</div>
        <div className="text-xs text-gray-400">{description}</div>
      </div>
    </label>
  );
}
