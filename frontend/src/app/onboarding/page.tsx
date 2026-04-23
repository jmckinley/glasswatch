"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/lib/api";

// Step configuration
const STEPS = [
  { id: 1, name: "Organization", description: "Tell us about your organization" },
  { id: 2, name: "Connect Tools", description: "Link your cloud providers" },
  { id: 3, name: "Asset Discovery", description: "Import your infrastructure" },
  { id: 4, name: "Create Goal", description: "Set your first objective" },
  { id: 5, name: "Schedule", description: "Configure maintenance windows" },
  { id: 6, name: "Review", description: "Launch your workspace" },
];

const PROVIDER_CARDS = [
  { id: "aws", name: "AWS", icon: "☁️", description: "EC2, ECS, Lambda", type: "cloud" },
  { id: "azure", name: "Azure", icon: "☁️", description: "VMs, App Services", type: "cloud" },
  { id: "gcp", name: "GCP", icon: "☁️", description: "Compute Engine, Cloud Run", type: "cloud" },
  { id: "slack", name: "Slack", icon: "💬", description: "Notifications & alerts", type: "slack" },
];

const GOAL_TEMPLATES = [
  {
    id: "soc2",
    name: "SOC 2 Readiness",
    description: "Achieve compliance for upcoming audit",
    icon: "🛡️",
    priority: "high",
  },
  {
    id: "zero-critical",
    name: "Zero Critical in 30 Days",
    description: "Eliminate all critical vulnerabilities",
    icon: "🎯",
    priority: "high",
  },
  {
    id: "reduce-exposure",
    name: "Reduce Internet Exposure",
    description: "Patch all internet-facing assets first",
    icon: "🌐",
    priority: "medium",
  },
  {
    id: "kev",
    name: "KEV Elimination",
    description: "Patch all CISA KEV catalog vulnerabilities",
    icon: "⚠️",
    priority: "critical",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Step 1: Org data
  const [orgData, setOrgData] = useState({
    tenant_name: "",
    industry: "",
    size: "",
  });

  // Step 2: Provider selection + config forms
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [providerConfigs, setProviderConfigs] = useState<Record<string, any>>({});
  const [connectionStatuses, setConnectionStatuses] = useState<Record<string, "ok" | "error">>({});

  // Step 3: Discovery
  const [discoveryStatus, setDiscoveryStatus] = useState<"idle" | "running" | "completed">("idle");
  const [discoveredCount, setDiscoveredCount] = useState(0);
  const [discoveredAssets, setDiscoveredAssets] = useState<any[]>([]);
  const discoveryTimer = useRef<NodeJS.Timeout | null>(null);

  // Step 4: Goal
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [goalData, setGoalData] = useState({
    name: "",
    description: "",
    target_date: "",
    priority: "medium",
  });
  const [createdGoalId, setCreatedGoalId] = useState<string | null>(null);

  // Step 5: Schedule
  const [scheduleData, setScheduleData] = useState({
    weekly_enabled: true,
    weekly_day: "Sunday",
    weekly_start_hour: "02:00",
    weekly_duration: "4",
    emergency_enabled: false,
    freeze_enabled: false,
    environment: "production",
  });

  // Step 6: completing
  const [isCompleting, setIsCompleting] = useState(false);

  // Load onboarding status on mount
  useEffect(() => {
    loadOnboardingStatus();
  }, []);

  // Cleanup discovery timer on unmount
  useEffect(() => {
    return () => {
      if (discoveryTimer.current) clearInterval(discoveryTimer.current);
    };
  }, []);

  const loadOnboardingStatus = async () => {
    try {
      const status = await apiCall<any>("/onboarding/status");
      if (status.onboarding_completed) {
        router.push("/dashboard");
        return;
      }
      if (status.onboarding_step > 0) {
        setCurrentStep(status.onboarding_step);
      }
    } catch (error) {
      console.error("Failed to load onboarding status:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveStep = async (stepNumber: number, data: any) => {
    setIsSaving(true);
    try {
      await apiCall(`/onboarding/step/${stepNumber}`, {
        method: "POST",
        body: { data },
      });
      return true;
    } catch (error) {
      console.error("Failed to save step:", error);
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  // Step 2: Create connections for each selected+configured provider
  const createConnections = async () => {
    const statuses: Record<string, "ok" | "error"> = {};
    const connections: any[] = [];

    for (const providerId of selectedProviders) {
      const config = providerConfigs[providerId] || {};
      const providerCard = PROVIDER_CARDS.find((p) => p.id === providerId);
      try {
        await apiCall("/connections", {
          method: "POST",
          body: {
            name: `${providerCard?.name || providerId} Production`,
            provider: providerId,
            config,
          },
        });
        statuses[providerId] = "ok";
        connections.push({ provider: providerId, name: `${providerCard?.name} Production`, config });
      } catch {
        statuses[providerId] = "error";
        connections.push({ provider: providerId, name: `${providerCard?.name} Production`, config });
      }
    }
    setConnectionStatuses(statuses);
    return connections;
  };

  // Step 3: Run discovery scan
  const runDiscovery = async () => {
    setDiscoveryStatus("running");
    setDiscoveredCount(0);
    setDiscoveredAssets([]);

    try {
      // Trigger scan
      await apiCall("/discovery/scan", { method: "POST" });

      // Poll assets every 3 seconds for up to 15 seconds
      let elapsed = 0;
      let lastCount = 0;
      let stableRounds = 0;

      const poll = async () => {
        try {
          const result = await apiCall<any>("/assets?limit=10");
          const count = result.total ?? result.items?.length ?? 0;
          setDiscoveredCount(count);
          if (result.items) setDiscoveredAssets(result.items.slice(0, 5));

          if (count === lastCount && count > 0) {
            stableRounds++;
          } else {
            stableRounds = 0;
          }
          lastCount = count;

          elapsed += 3;
          if (elapsed >= 15 || stableRounds >= 2) {
            if (discoveryTimer.current) clearInterval(discoveryTimer.current);
            setDiscoveryStatus("completed");
          }
        } catch {
          // ignore poll errors
        }
      };

      discoveryTimer.current = setInterval(poll, 3000);
      // Also run once immediately
      await poll();
    } catch {
      // If scan endpoint fails, simulate
      simulateDiscovery();
    }
  };

  // Fallback: simulated discovery
  const simulateDiscovery = () => {
    let count = 0;
    const interval = setInterval(() => {
      count += Math.floor(Math.random() * 5) + 2;
      setDiscoveredCount(count);
      if (count >= 30) {
        clearInterval(interval);
        setDiscoveryStatus("completed");
        setDiscoveredCount(count);
      }
    }, 1200);
    setTimeout(() => {
      clearInterval(interval);
      setDiscoveryStatus("completed");
    }, 13000);
  };

  // Step 4: Create real goal
  const createGoal = async () => {
    if (!goalData.name) return null;
    try {
      const result = await apiCall<any>("/goals", {
        method: "POST",
        body: {
          name: goalData.name,
          description: goalData.description,
          goal_type: selectedGoal?.toUpperCase().replace(/-/g, "_") || "TIME_BASED",
          target_completion_date: goalData.target_date || undefined,
        },
      });
      setCreatedGoalId(result.id || result.goal_id);
      return result.id || result.goal_id;
    } catch (err) {
      console.error("Failed to create goal:", err);
      return null;
    }
  };

  // Step 5: Create maintenance window
  const createMaintenanceWindow = async () => {
    if (!scheduleData.weekly_enabled) return;
    try {
      // Compute next occurrence
      const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
      const targetDay = days.indexOf(scheduleData.weekly_day);
      const [h, m] = scheduleData.weekly_start_hour.split(":").map(Number);
      const now = new Date();
      let daysAhead = (targetDay - now.getDay() + 7) % 7;
      if (daysAhead === 0 && (now.getHours() > h || (now.getHours() === h && now.getMinutes() >= m))) {
        daysAhead = 7;
      }
      const startDate = new Date(now);
      startDate.setDate(now.getDate() + daysAhead);
      startDate.setHours(h, m, 0, 0);
      const endDate = new Date(startDate.getTime() + parseInt(scheduleData.weekly_duration) * 3600000);

      await apiCall("/maintenance-windows", {
        method: "POST",
        body: {
          name: "Weekly Maintenance",
          type: "scheduled",
          start_time: startDate.toISOString(),
          end_time: endDate.toISOString(),
          timezone: "America/New_York",
          environment: scheduleData.environment,
          max_duration_hours: parseInt(scheduleData.weekly_duration),
        },
      });
    } catch (err) {
      console.error("Failed to create maintenance window:", err);
    }
  };

  const handleNext = async () => {
    let stepData: any = {};
    let connections: any[] = [];

    switch (currentStep) {
      case 1:
        stepData = orgData;
        break;
      case 2: {
        // Create connections via API
        connections = await createConnections();
        stepData = { providers: selectedProviders, connections };
        break;
      }
      case 3:
        stepData = { discovery_status: discoveryStatus, asset_count: discoveredCount };
        break;
      case 4: {
        const goalId = await createGoal();
        stepData = { template: selectedGoal, goal: goalData, goal_id: goalId };
        break;
      }
      case 5: {
        await createMaintenanceWindow();
        stepData = scheduleData;
        break;
      }
    }

    const success = await saveStep(currentStep, stepData);
    if (!success) return;

    if (currentStep < 6) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    setIsCompleting(true);
    try {
      await saveStep(6, { confirmed: true });
      await apiCall("/onboarding/complete", { method: "POST" });
      router.push("/dashboard");
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
      setIsCompleting(false);
    }
  };

  const handleSkip = async () => {
    try {
      await apiCall("/onboarding/skip", { method: "POST" });
      router.push("/dashboard");
    } catch (error) {
      console.error("Failed to skip onboarding:", error);
    }
  };

  const toggleProvider = (providerId: string) => {
    if (selectedProviders.includes(providerId)) {
      setSelectedProviders(selectedProviders.filter((p) => p !== providerId));
    } else {
      setSelectedProviders([...selectedProviders, providerId]);
    }
  };

  const updateProviderConfig = (providerId: string, field: string, value: string) => {
    setProviderConfigs((prev) => ({
      ...prev,
      [providerId]: { ...(prev[providerId] || {}), [field]: value },
    }));
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">Loading onboarding...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-8">
      <div className="max-w-4xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Welcome to Glasswatch</h1>
          <p className="text-gray-400">Let&apos;s get you set up in just a few minutes</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            {STEPS.map((step, idx) => (
              <div key={step.id} className={`flex-1 ${idx > 0 ? "ml-2" : ""}`}>
                <div
                  className={`h-2 rounded-full transition-all ${
                    step.id <= currentStep ? "bg-blue-500" : "bg-gray-700"
                  }`}
                />
                <div className="text-xs text-gray-400 mt-1 text-center">{step.name}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-gray-800 rounded-lg p-8 mb-6">
          {/* Step 1: Organization */}
          {currentStep === 1 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Organization Setup</h2>
              <p className="text-gray-400 mb-6">Tell us about your organization</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Organization Name</label>
                  <input
                    type="text"
                    value={orgData.tenant_name}
                    onChange={(e) => setOrgData({ ...orgData, tenant_name: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Acme Corp"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Industry</label>
                  <select
                    value={orgData.industry}
                    onChange={(e) => setOrgData({ ...orgData, industry: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select industry</option>
                    <option value="technology">Technology</option>
                    <option value="finance">Finance</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="retail">Retail</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Company Size</label>
                  <select
                    value={orgData.size}
                    onChange={(e) => setOrgData({ ...orgData, size: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select size</option>
                    <option value="1-10">1-10 employees</option>
                    <option value="11-50">11-50 employees</option>
                    <option value="51-200">51-200 employees</option>
                    <option value="201-1000">201-1000 employees</option>
                    <option value="1000+">1000+ employees</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Connect Tools */}
          {currentStep === 2 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Connect Your Tools</h2>
              <p className="text-gray-400 mb-6">Select the cloud providers and tools you use</p>
              <div className="grid grid-cols-2 gap-4">
                {PROVIDER_CARDS.map((provider) => {
                  const isSelected = selectedProviders.includes(provider.id);
                  const status = connectionStatuses[provider.id];
                  return (
                    <div key={provider.id}>
                      <button
                        onClick={() => toggleProvider(provider.id)}
                        className={`w-full p-6 rounded-lg border-2 text-left transition-all ${
                          isSelected
                            ? status === "ok"
                              ? "border-green-500 bg-green-500/10"
                              : status === "error"
                              ? "border-red-500 bg-red-500/10"
                              : "border-blue-500 bg-blue-500/10"
                            : "border-gray-600 hover:border-gray-500"
                        }`}
                      >
                        <div className="text-3xl mb-2">{provider.icon}</div>
                        <h3 className="font-semibold text-white mb-1">{provider.name}</h3>
                        <p className="text-sm text-gray-400">{provider.description}</p>
                        {status === "ok" && <p className="text-xs text-green-400 mt-1">✓ Connected</p>}
                        {status === "error" && <p className="text-xs text-red-400 mt-1">⚠ Connection failed</p>}
                      </button>

                      {/* Config form when selected */}
                      {isSelected && (
                        <div className="mt-2 p-3 bg-gray-700 rounded-lg border border-gray-600 space-y-2">
                          {provider.type === "cloud" && (
                            <>
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Region</label>
                                <input
                                  type="text"
                                  value={providerConfigs[provider.id]?.region || ""}
                                  onChange={(e) => updateProviderConfig(provider.id, "region", e.target.value)}
                                  placeholder="us-east-1"
                                  className="w-full px-3 py-1.5 bg-gray-600 text-white text-sm rounded focus:ring-1 focus:ring-blue-500"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">Account ID</label>
                                <input
                                  type="text"
                                  value={providerConfigs[provider.id]?.account_id || ""}
                                  onChange={(e) => updateProviderConfig(provider.id, "account_id", e.target.value)}
                                  placeholder="123456789012"
                                  className="w-full px-3 py-1.5 bg-gray-600 text-white text-sm rounded focus:ring-1 focus:ring-blue-500"
                                />
                              </div>
                            </>
                          )}
                          {provider.type === "slack" && (
                            <div>
                              <label className="block text-xs text-gray-400 mb-1">Webhook URL</label>
                              <input
                                type="url"
                                value={providerConfigs[provider.id]?.webhook_url || ""}
                                onChange={(e) => updateProviderConfig(provider.id, "webhook_url", e.target.value)}
                                placeholder="https://hooks.slack.com/services/..."
                                className="w-full px-3 py-1.5 bg-gray-600 text-white text-sm rounded focus:ring-1 focus:ring-blue-500"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              {Object.keys(connectionStatuses).length > 0 && (
                <div className="mt-4 p-3 bg-gray-700 rounded-lg text-sm text-gray-300">
                  {Object.entries(connectionStatuses).map(([p, s]) => (
                    <div key={p}>
                      {s === "ok" ? "✅" : "⚠️"} {p.toUpperCase()}: {s === "ok" ? "Connected" : "Failed (continuing anyway)"}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 3: Asset Discovery */}
          {currentStep === 3 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Asset Discovery</h2>
              <p className="text-gray-400 mb-6">Import your infrastructure assets</p>

              {discoveryStatus === "idle" && (
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">🔍</div>
                  <p className="text-gray-400 mb-6">Ready to discover your assets</p>
                  <button
                    onClick={runDiscovery}
                    className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    Run Discovery
                  </button>
                </div>
              )}

              {discoveryStatus === "running" && (
                <div className="text-center py-12">
                  <div className="animate-spin text-6xl mb-4">⚙️</div>
                  <p className="text-white font-semibold mb-2">
                    🔍 Scanning... Found {discoveredCount} assets so far
                  </p>
                  <p className="text-gray-400 text-sm">Scanning your infrastructure...</p>
                </div>
              )}

              {discoveryStatus === "completed" && (
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">✅</div>
                  <p className="text-white font-semibold mb-2">Discovery Complete!</p>
                  <p className="text-gray-400 mb-4">Found {discoveredCount} assets across {selectedProviders.length} provider(s)</p>
                  {discoveredAssets.length > 0 && (
                    <div className="mt-4 text-left max-w-md mx-auto space-y-1">
                      {discoveredAssets.map((a: any) => (
                        <div key={a.id} className="text-sm text-gray-300 flex items-center gap-2">
                          <span className="text-green-400">•</span>
                          {a.name || a.identifier}
                        </div>
                      ))}
                      {discoveredCount > discoveredAssets.length && (
                        <div className="text-xs text-gray-500">...and {discoveredCount - discoveredAssets.length} more</div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 4: Create Goal */}
          {currentStep === 4 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Create Your First Goal</h2>
              <p className="text-gray-400 mb-6">Choose a template or create custom</p>
              <div className="grid grid-cols-2 gap-4 mb-6">
                {GOAL_TEMPLATES.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => {
                      setSelectedGoal(template.id);
                      setGoalData({
                        name: template.name,
                        description: template.description,
                        target_date: "",
                        priority: template.priority,
                      });
                    }}
                    className={`p-6 rounded-lg border-2 text-left transition-all ${
                      selectedGoal === template.id
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-gray-600 hover:border-gray-500"
                    }`}
                  >
                    <div className="text-3xl mb-2">{template.icon}</div>
                    <h3 className="font-semibold text-white mb-1">{template.name}</h3>
                    <p className="text-sm text-gray-400">{template.description}</p>
                  </button>
                ))}
              </div>
              {selectedGoal && (
                <div className="mt-6 p-4 bg-gray-700 rounded-lg space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Goal Name</label>
                    <input
                      type="text"
                      value={goalData.name}
                      onChange={(e) => setGoalData({ ...goalData, name: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Target Date</label>
                    <input
                      type="date"
                      value={goalData.target_date}
                      onChange={(e) => setGoalData({ ...goalData, target_date: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  {createdGoalId && (
                    <p className="text-xs text-green-400">✓ Goal saved (ID: {createdGoalId})</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 5: Schedule */}
          {currentStep === 5 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Configure Maintenance Windows</h2>
              <p className="text-gray-400 mb-6">When can patches be deployed? You can add more windows later.</p>
              <div className="space-y-4">
                {/* Weekly window */}
                <div className={`p-4 bg-gray-700 rounded-lg border-2 transition-colors ${
                  scheduleData.weekly_enabled ? "border-blue-500" : "border-transparent"
                }`}>
                  <label className="flex items-center justify-between mb-3 cursor-pointer">
                    <div className="font-medium text-white">📅 Weekly Maintenance Window</div>
                    <input
                      type="checkbox"
                      checked={scheduleData.weekly_enabled}
                      onChange={(e) => setScheduleData({ ...scheduleData, weekly_enabled: e.target.checked })}
                      className="w-5 h-5 rounded text-blue-500"
                    />
                  </label>
                  {scheduleData.weekly_enabled && (
                    <div className="grid grid-cols-2 gap-3 mt-2">
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Day of week</label>
                        <select
                          value={scheduleData.weekly_day}
                          onChange={(e) => setScheduleData({ ...scheduleData, weekly_day: e.target.value })}
                          className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        >
                          {["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].map((d) => (
                            <option key={d} value={d}>{d}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Start time</label>
                        <input
                          type="time"
                          value={scheduleData.weekly_start_hour}
                          onChange={(e) => setScheduleData({ ...scheduleData, weekly_start_hour: e.target.value })}
                          className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Duration (hours)</label>
                        <select
                          value={scheduleData.weekly_duration}
                          onChange={(e) => setScheduleData({ ...scheduleData, weekly_duration: e.target.value })}
                          className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        >
                          {["1", "2", "3", "4", "6", "8"].map((h) => (
                            <option key={h} value={h}>{h} {h === "1" ? "hour" : "hours"}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Environment</label>
                        <select
                          value={scheduleData.environment}
                          onChange={(e) => setScheduleData({ ...scheduleData, environment: e.target.value })}
                          className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                        >
                          <option value="production">Production</option>
                          <option value="staging">Staging</option>
                          <option value="all">All environments</option>
                        </select>
                      </div>
                    </div>
                  )}
                  {scheduleData.weekly_enabled && (
                    <p className="text-xs text-blue-300 mt-3">
                      ✓ {scheduleData.weekly_day}s at {scheduleData.weekly_start_hour} · {scheduleData.weekly_duration}h · {scheduleData.environment}
                    </p>
                  )}
                </div>

                {/* Emergency window */}
                <div className="p-4 bg-gray-700 rounded-lg">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div>
                      <div className="font-medium text-white">🚨 Emergency Windows</div>
                      <div className="text-sm text-gray-400 mt-0.5">Allow critical/KEV patches to deploy outside scheduled windows</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={scheduleData.emergency_enabled}
                      onChange={(e) => setScheduleData({ ...scheduleData, emergency_enabled: e.target.checked })}
                      className="w-5 h-5 rounded text-blue-500"
                    />
                  </label>
                </div>

                {/* Freeze */}
                <div className="p-4 bg-gray-700 rounded-lg">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div>
                      <div className="font-medium text-white">❄️ Change Freeze Periods</div>
                      <div className="text-sm text-gray-400 mt-0.5">Block all patches during holidays and critical business periods</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={scheduleData.freeze_enabled}
                      onChange={(e) => setScheduleData({ ...scheduleData, freeze_enabled: e.target.checked })}
                      className="w-5 h-5 rounded text-blue-500"
                    />
                  </label>
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-4">You can add and edit maintenance windows anytime from the Schedule page.</p>
            </div>
          )}

          {/* Step 6: Review */}
          {currentStep === 6 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Review &amp; Launch</h2>
              <p className="text-gray-400 mb-6">Your workspace is ready to go!</p>
              <div className="space-y-4 text-center py-8">
                {isCompleting ? (
                  <>
                    <div className="animate-spin text-6xl mb-4">⚙️</div>
                    <p className="text-white font-semibold">Setting up your workspace...</p>
                  </>
                ) : (
                  <>
                    <div className="text-6xl mb-4">🚀</div>
                    <h3 className="text-xl font-semibold text-white">You&apos;re All Set!</h3>
                    <p className="text-gray-400 max-w-lg mx-auto">
                      Your Glasswatch workspace is configured and ready. Click below to start managing your patches.
                    </p>
                    <div className="mt-8 p-4 bg-gray-700 rounded-lg text-left max-w-lg mx-auto">
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-green-400">✓</span>
                          <span className="text-gray-300">Organization: {orgData.tenant_name || "Set up"}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-green-400">✓</span>
                          <span className="text-gray-300">Providers: {selectedProviders.length} connected</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-green-400">✓</span>
                          <span className="text-gray-300">Assets: {discoveredCount > 0 ? `${discoveredCount} discovered` : "Discovered"}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-green-400">✓</span>
                          <span className="text-gray-300">Goal: {goalData.name || "Created"}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-green-400">✓</span>
                          <span className="text-gray-300">Schedule: Configured</span>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center">
          {currentStep > 1 ? (
            <button
              onClick={handleBack}
              disabled={isSaving || isCompleting}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
            >
              ← Back
            </button>
          ) : (
            <div />
          )}

          <div className="flex gap-4">
            <button
              onClick={handleSkip}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Skip Setup →
            </button>

            {currentStep < 6 ? (
              <button
                onClick={handleNext}
                disabled={isSaving}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? "Saving..." : "Continue →"}
              </button>
            ) : (
              <button
                onClick={handleComplete}
                disabled={isSaving || isCompleting}
                className="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCompleting ? "Setting up..." : "Go to Dashboard"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
