"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type OnboardingStep = "welcome" | "discovery" | "goals" | "schedule" | "complete";

interface AssetDiscoveryOption {
  id: string;
  name: string;
  icon: string;
  description: string;
  requiresAuth: boolean;
}

const discoveryOptions: AssetDiscoveryOption[] = [
  {
    id: "aws",
    name: "AWS",
    icon: "☁️",
    description: "Import from EC2, ECS, Lambda",
    requiresAuth: true,
  },
  {
    id: "azure",
    name: "Azure",
    icon: "☁️",
    description: "Import VMs, App Services, Functions",
    requiresAuth: true,
  },
  {
    id: "csv",
    name: "CSV Upload",
    icon: "📄",
    description: "Import from spreadsheet",
    requiresAuth: false,
  },
  {
    id: "manual",
    name: "Add Manually",
    icon: "✏️",
    description: "Start with a few assets",
    requiresAuth: false,
  },
];

const goalTemplates = [
  {
    id: "soc2",
    name: "SOC 2 Readiness",
    description: "Achieve compliance for upcoming audit",
    type: "compliance_deadline",
    risk_tolerance: "conservative",
    icon: "🛡️",
  },
  {
    id: "zero-critical",
    name: "Zero Critical in 30 Days",
    description: "Eliminate all critical vulnerabilities",
    type: "zero_critical",
    risk_tolerance: "balanced",
    icon: "🎯",
  },
  {
    id: "reduce-exposure",
    name: "Reduce Internet Exposure",
    description: "Patch all internet-facing assets first",
    type: "risk_reduction",
    risk_tolerance: "aggressive",
    icon: "🌐",
  },
  {
    id: "kev-elimination",
    name: "KEV Elimination",
    description: "Patch all CISA KEV catalog vulnerabilities",
    type: "kev_elimination",
    risk_tolerance: "conservative",
    icon: "⚠️",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<OnboardingStep>("welcome");
  const [selectedDiscovery, setSelectedDiscovery] = useState<string | null>(null);
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleComplete = async () => {
    setIsProcessing(true);
    // Simulate setup process
    setTimeout(() => {
      router.push("/");
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <div className="max-w-4xl w-full">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-neutral-400">Setup Progress</span>
            <span className="text-sm text-neutral-400">
              {step === "welcome" && "1 of 4"}
              {step === "discovery" && "2 of 4"}
              {step === "goals" && "3 of 4"}
              {step === "schedule" && "4 of 4"}
              {step === "complete" && "Complete!"}
            </span>
          </div>
          <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{
                width:
                  step === "welcome"
                    ? "25%"
                    : step === "discovery"
                    ? "50%"
                    : step === "goals"
                    ? "75%"
                    : "100%",
              }}
            />
          </div>
        </div>

        {/* Welcome Step */}
        {step === "welcome" && (
          <div className="card p-12 text-center">
            <h1 className="text-4xl font-bold mb-4">Welcome to PatchAI</h1>
            <p className="text-xl text-neutral-400 mb-8">
              Let&apos;s get you set up in just a few minutes
            </p>
            <div className="space-y-4 text-left max-w-lg mx-auto">
              <div className="flex items-start gap-3">
                <span className="text-primary mt-1">✓</span>
                <div>
                  <div className="font-medium">Import Your Assets</div>
                  <div className="text-sm text-neutral-400">
                    Connect to AWS, Azure, or upload a CSV
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-primary mt-1">✓</span>
                <div>
                  <div className="font-medium">Set Your Goals</div>
                  <div className="text-sm text-neutral-400">
                    Tell us what you want to achieve
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-primary mt-1">✓</span>
                <div>
                  <div className="font-medium">Get Your Schedule</div>
                  <div className="text-sm text-neutral-400">
                    AI generates your optimal patch plan
                  </div>
                </div>
              </div>
            </div>
            <button
              onClick={() => setStep("discovery")}
              className="mt-8 px-6 py-3 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors text-lg font-medium"
            >
              Get Started
            </button>
          </div>
        )}

        {/* Asset Discovery Step */}
        {step === "discovery" && (
          <div className="card p-12">
            <h2 className="text-3xl font-bold mb-2">Import Your Assets</h2>
            <p className="text-neutral-400 mb-8">
              How would you like to import your infrastructure?
            </p>
            <div className="grid grid-cols-2 gap-4 mb-8">
              {discoveryOptions.map((option) => (
                <button
                  key={option.id}
                  onClick={() => setSelectedDiscovery(option.id)}
                  className={`p-6 rounded-lg border-2 text-left transition-all ${
                    selectedDiscovery === option.id
                      ? "border-primary bg-primary/10"
                      : "border-neutral-700 hover:border-neutral-600"
                  }`}
                >
                  <div className="text-3xl mb-2">{option.icon}</div>
                  <h3 className="font-semibold mb-1">{option.name}</h3>
                  <p className="text-sm text-neutral-400">{option.description}</p>
                  {option.requiresAuth && (
                    <span className="text-xs text-secondary mt-2 inline-block">
                      Requires authentication
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <button
                onClick={() => setStep("welcome")}
                className="px-4 py-2 text-neutral-400 hover:text-foreground transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep("goals")}
                disabled={!selectedDiscovery}
                className="px-6 py-3 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Goals Step */}
        {step === "goals" && (
          <div className="card p-12">
            <h2 className="text-3xl font-bold mb-2">Set Your First Goal</h2>
            <p className="text-neutral-400 mb-8">
              Choose a template or we&apos;ll help you create a custom goal
            </p>
            <div className="grid grid-cols-2 gap-4 mb-8">
              {goalTemplates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => setSelectedGoal(template.id)}
                  className={`p-6 rounded-lg border-2 text-left transition-all ${
                    selectedGoal === template.id
                      ? "border-primary bg-primary/10"
                      : "border-neutral-700 hover:border-neutral-600"
                  }`}
                >
                  <div className="text-3xl mb-2">{template.icon}</div>
                  <h3 className="font-semibold mb-1">{template.name}</h3>
                  <p className="text-sm text-neutral-400">{template.description}</p>
                  <span
                    className={`text-xs mt-2 inline-block ${
                      template.risk_tolerance === "conservative"
                        ? "text-success"
                        : template.risk_tolerance === "balanced"
                        ? "text-secondary"
                        : "text-warning"
                    }`}
                  >
                    {template.risk_tolerance} risk tolerance
                  </span>
                </button>
              ))}
            </div>
            <div className="text-center mb-8">
              <button className="text-primary hover:underline">
                Or create a custom goal with AI assistance →
              </button>
            </div>
            <div className="flex justify-between">
              <button
                onClick={() => setStep("discovery")}
                className="px-4 py-2 text-neutral-400 hover:text-foreground transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep("schedule")}
                disabled={!selectedGoal}
                className="px-6 py-3 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Schedule Step */}
        {step === "schedule" && (
          <div className="card p-12">
            <h2 className="text-3xl font-bold mb-2">Configure Maintenance Windows</h2>
            <p className="text-neutral-400 mb-8">
              When can we schedule patches? We&apos;ll optimize within these windows.
            </p>
            <div className="space-y-4 mb-8">
              <div className="p-4 bg-neutral-800 rounded-lg">
                <label className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Weekly Maintenance Window</div>
                    <div className="text-sm text-neutral-400">
                      Sundays 2:00 AM - 6:00 AM (recommended)
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    defaultChecked
                    className="w-4 h-4 rounded text-primary"
                  />
                </label>
              </div>
              <div className="p-4 bg-neutral-800 rounded-lg">
                <label className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Emergency Windows</div>
                    <div className="text-sm text-neutral-400">
                      Allow critical patches outside maintenance windows
                    </div>
                  </div>
                  <input type="checkbox" className="w-4 h-4 rounded text-primary" />
                </label>
              </div>
              <div className="p-4 bg-neutral-800 rounded-lg">
                <label className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Change Freeze Periods</div>
                    <div className="text-sm text-neutral-400">
                      Block patches during holidays or critical business periods
                    </div>
                  </div>
                  <input type="checkbox" className="w-4 h-4 rounded text-primary" />
                </label>
              </div>
            </div>
            <div className="flex justify-between">
              <button
                onClick={() => setStep("goals")}
                className="px-4 py-2 text-neutral-400 hover:text-foreground transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleComplete}
                disabled={isProcessing}
                className="px-6 py-3 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? "Setting up..." : "Complete Setup"}
              </button>
            </div>
          </div>
        )}

        {/* Skip to Demo */}
        {step !== "complete" && (
          <div className="text-center mt-6">
            <Link
              href="/"
              className="text-sm text-neutral-400 hover:text-foreground transition-colors"
            >
              Skip setup and explore with demo data →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}