"use client";

import { useState, useEffect } from "react";
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
  { id: "aws", name: "AWS", icon: "☁️", description: "EC2, ECS, Lambda" },
  { id: "azure", name: "Azure", icon: "☁️", description: "VMs, App Services" },
  { id: "gcp", name: "GCP", icon: "☁️", description: "Compute Engine, Cloud Run" },
  { id: "slack", name: "Slack", icon: "💬", description: "Notifications & alerts" },
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
  
  // Step data
  const [orgData, setOrgData] = useState({
    tenant_name: "",
    industry: "",
    size: "",
  });
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [discoveryStatus, setDiscoveryStatus] = useState<string | null>(null);
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [goalData, setGoalData] = useState({
    name: "",
    description: "",
    target_date: "",
    priority: "medium",
  });
  const [scheduleData, setScheduleData] = useState({
    weekly_enabled: true,
    weekly_day: "Sunday",
    weekly_start_hour: "02:00",
    weekly_duration: "4",
    emergency_enabled: false,
    freeze_enabled: false,
    environment: "production",
  });

  // Load onboarding status on mount
  useEffect(() => {
    loadOnboardingStatus();
  }, []);

  const loadOnboardingStatus = async () => {
    try {
      const status = await apiCall<any>("/onboarding/status");
      
      // If already completed, redirect to dashboard
      if (status.onboarding_completed) {
        router.push("/");
        return;
      }
      
      // Set current step from backend
      setCurrentStep(status.onboarding_step || 1);
      
      // Load saved data if exists
      if (status.onboarding_data) {
        const data = status.onboarding_data;
        if (data.step_1) setOrgData(data.step_1);
        if (data.step_2) setSelectedProviders(data.step_2.providers || []);
        if (data.step_4) {
          setSelectedGoal(data.step_4.template);
          setGoalData(data.step_4.goal);
        }
        if (data.step_5) setScheduleData(data.step_5);
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

  const handleNext = async () => {
    let stepData: any = {};
    
    // Prepare data based on current step
    switch (currentStep) {
      case 1:
        stepData = orgData;
        break;
      case 2:
        stepData = { providers: selectedProviders };
        break;
      case 3:
        stepData = { discovery_status: discoveryStatus };
        break;
      case 4:
        stepData = { template: selectedGoal, goal: goalData };
        break;
      case 5:
        stepData = scheduleData;
        break;
    }
    
    // Save current step
    const success = await saveStep(currentStep, stepData);
    if (!success) return;
    
    // Move to next step
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
    setIsSaving(true);
    try {
      // Save final step
      await saveStep(6, { confirmed: true });
      
      // Mark as complete
      await apiCall("/onboarding/complete", { method: "POST" });
      
      // Redirect to dashboard
      router.push("/");
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
      setIsSaving(false);
    }
  };

  const handleSkip = async () => {
    try {
      await apiCall("/onboarding/skip", { method: "POST" });
      router.push("/");
    } catch (error) {
      console.error("Failed to skip onboarding:", error);
    }
  };

  const runDiscovery = async () => {
    setDiscoveryStatus("running");
    // Simulate discovery (in real app, call /discovery/scan)
    setTimeout(() => {
      setDiscoveryStatus("completed");
    }, 2000);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">Loading onboarding...</div>
      </div>
    );
  }

  const progress = (currentStep / 6) * 100;

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
              <div
                key={step.id}
                className={`flex-1 ${idx > 0 ? "ml-2" : ""}`}
              >
                <div
                  className={`h-2 rounded-full transition-all ${
                    step.id <= currentStep ? "bg-blue-500" : "bg-gray-700"
                  }`}
                />
                <div className="text-xs text-gray-400 mt-1 text-center">
                  {step.name}
                </div>
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
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Organization Name
                  </label>
                  <input
                    type="text"
                    value={orgData.tenant_name}
                    onChange={(e) => setOrgData({ ...orgData, tenant_name: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Acme Corp"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Industry
                  </label>
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
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Company Size
                  </label>
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
                {PROVIDER_CARDS.map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => {
                      if (selectedProviders.includes(provider.id)) {
                        setSelectedProviders(selectedProviders.filter(p => p !== provider.id));
                      } else {
                        setSelectedProviders([...selectedProviders, provider.id]);
                      }
                    }}
                    className={`p-6 rounded-lg border-2 text-left transition-all ${
                      selectedProviders.includes(provider.id)
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-gray-600 hover:border-gray-500"
                    }`}
                  >
                    <div className="text-3xl mb-2">{provider.icon}</div>
                    <h3 className="font-semibold text-white mb-1">{provider.name}</h3>
                    <p className="text-sm text-gray-400">{provider.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Asset Discovery */}
          {currentStep === 3 && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">Asset Discovery</h2>
              <p className="text-gray-400 mb-6">Import your infrastructure assets</p>
              
              {!discoveryStatus ? (
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
              ) : discoveryStatus === "running" ? (
                <div className="text-center py-12">
                  <div className="animate-spin text-6xl mb-4">⚙️</div>
                  <p className="text-gray-400">Scanning your infrastructure...</p>
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">✅</div>
                  <p className="text-white font-semibold mb-2">Discovery Complete</p>
                  <p className="text-gray-400">Found 42 assets across {selectedProviders.length} provider(s)</p>
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
                <div className="mt-6 p-4 bg-gray-700 rounded-lg">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Target Date
                  </label>
                  <input
                    type="date"
                    value={goalData.target_date}
                    onChange={(e) => setGoalData({ ...goalData, target_date: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
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
                  scheduleData.weekly_enabled ? 'border-blue-500' : 'border-transparent'
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
                          {['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'].map(d => (
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
                          {['1','2','3','4','6','8'].map(h => (
                            <option key={h} value={h}>{h} {h === '1' ? 'hour' : 'hours'}</option>
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
              <h2 className="text-2xl font-bold text-white mb-4">Review & Launch</h2>
              <p className="text-gray-400 mb-6">Your workspace is ready to go!</p>
              
              <div className="space-y-4 text-center py-8">
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
                      <span className="text-gray-300">Assets: Discovered</span>
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
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center">
          {currentStep > 1 ? (
            <button
              onClick={handleBack}
              disabled={isSaving}
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
                disabled={isSaving}
                className="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? "Setting up..." : "Go to Dashboard"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
