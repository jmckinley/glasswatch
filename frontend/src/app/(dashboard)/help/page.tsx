"use client";

import { useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Zap,
  GitBranch,
  Link2,
  HelpCircle,
  Search,
  ChevronRight,
  Shield,
  Target,
  Package,
  Calendar,
  FileText,
  Sliders,
  Sparkles,
} from "lucide-react";

// FAQ data
const faqItems = [
  {
    question: "What is Glasswatch?",
    answer:
      "Glasswatch is an AI-driven patch management platform for enterprise security teams. It converts scanner output into organized, prioritized patch plans — with the goal being outcomes like 'patch all KEV vulns by July 1' rather than just CVE lists.",
  },
  {
    question: "How is this different from Qualys or Tenable?",
    answer:
      "Qualys and Tenable are scanners — they find vulnerabilities. Glasswatch is what comes after: it decides what to patch, when, and in what order. It integrates with those scanners via webhooks and adds scoring, scheduling, approvals, and deployment tracking.",
  },
  {
    question: "What scanners do you integrate with?",
    answer:
      "Glasswatch accepts inbound webhooks from Tenable, Qualys, and Rapid7 InsightVM. You can also bulk-import vulnerability data via the API.",
  },
  {
    question: "How does AI scoring work?",
    answer:
      "Each vulnerability is scored on 8 factors: CVSS base score, EPSS exploit probability, KEV listing status, asset exposure (internet-facing vs isolated), asset criticality tier, patch age, public exploit availability, and Snapper runtime reachability data.",
  },
  {
    question: "What is a bundle?",
    answer:
      "A bundle is a group of patches scheduled for deployment in a single maintenance window. When you create a goal, Glasswatch generates bundles automatically. Bundles move through: draft → approved → in_progress → completed.",
  },
  {
    question: "What is a maintenance window?",
    answer:
      "An approved time slot for applying patches. It has a start/end time, an optional environment scope (e.g. production only), and capacity limits. Bundles are scheduled within windows.",
  },
  {
    question: "How do NLP rules work?",
    answer:
      'Write deployment rules in plain English — e.g. "Block all deployments on Fridays after 3pm" or "Require approval for production changes at month-end". Glasswatch parses them with Claude (if configured) or pattern matching, and evaluates them at deployment time.',
  },
  {
    question: "Can I self-host?",
    answer:
      "Yes. The backend is a standard FastAPI app with PostgreSQL. A docker-compose.yml is included. Required env vars: DATABASE_URL, SECRET_KEY. Optional: ANTHROPIC_API_KEY (AI features), WORKOS_API_KEY (SSO).",
  },
  {
    question: "What data does Glasswatch store?",
    answer:
      "Vulnerability metadata, asset inventory, patch history, goal definitions, bundle schedules, deployment rules, and audit logs. Glasswatch does not store scanner credentials, raw scan files, or source code.",
  },
  {
    question: "How does the demo work?",
    answer:
      "The demo runs against a shared tenant pre-loaded with synthetic data. No signup required — click Try Demo on the login page. All actions (goals, bundles, rules) work fully in demo mode.",
  },
  {
    question: "What does SOC 2 readiness mean?",
    answer:
      "Glasswatch maintains immutable audit logs, role-based access, JWT auth with short-lived tokens, TLS-only communication, and full tenant isolation — all aligned with SOC 2 requirements. This supports your own audit by providing a verifiable patch history.",
  },
  {
    question: "How does the goal optimizer work?",
    answer:
      "Define a goal (e.g. eliminate KEV vulns on internet-facing assets by July 1). The optimizer identifies in-scope vulns, calculates the optimal patching order by risk score, distributes across your maintenance windows, and generates bundles respecting all constraints.",
  },
  {
    question: "What approval workflows are supported?",
    answer:
      "Configurable approval chains: single approver, role-based (admin only), multi-stage (analyst then admin), or automatic approval for low-risk bundles below a threshold. All actions are audit-logged.",
  },
  {
    question: "How does the AI assistant work?",
    answer:
      'The floating AI assistant accepts plain English. "What needs my attention?" pulls live KEV + overdue bundle data. "Create a rule blocking Friday deployments" creates the rule. "Show risk score for CVE-2021-44228" looks it up. It uses your live data.',
  },
  {
    question: "Does Glasswatch support multi-tenancy?",
    answer:
      "Yes. Every object is scoped to a tenant. Tenants are isolated at the database level. Each tenant supports multiple users with different roles (admin, analyst, viewer).",
  },
];

const gettingStartedSteps = [
  {
    title: "Connect a scanner",
    desc: "Add your Tenable, Qualys, or Rapid7 connection in Settings → Connections. Glasswatch will start ingesting findings via webhook.",
    link: "/settings",
    linkLabel: "Go to Settings",
  },
  {
    title: "Review your assets",
    desc: "Check that your assets have the right exposure levels set (Internet / Intranet / Isolated) — this heavily influences scoring.",
    link: "/assets",
    linkLabel: "View Assets",
  },
  {
    title: "Create a goal",
    desc: "Define what you want to achieve and by when. The optimizer generates bundles automatically.",
    link: "/goals",
    linkLabel: "Create Goal",
  },
  {
    title: "Review and approve bundles",
    desc: "Review the generated patch bundles, adjust as needed, and approve for deployment.",
    link: "/bundles",
    linkLabel: "View Bundles",
  },
];

const keyConcepts = [
  {
    icon: Shield,
    title: "Vulnerability Scoring",
    desc: "8-factor AI scoring that goes beyond CVSS. Combines EPSS, KEV status, asset exposure, and runtime reachability into a single risk score.",
  },
  {
    icon: Target,
    title: "Goals",
    desc: 'Outcome-oriented objectives like "patch all KEV vulns by July 1". The optimizer generates the patching plan to hit your target.',
  },
  {
    icon: Package,
    title: "Bundles",
    desc: "Groups of patches scheduled for a single deployment window. Automatically generated by the optimizer, manually reviewable.",
  },
  {
    icon: Calendar,
    title: "Maintenance Windows",
    desc: "Approved time slots for patching. Bundles are scheduled within windows. Supports recurring schedules and blackout periods.",
  },
  {
    icon: FileText,
    title: "Deployment Rules",
    desc: 'NLP-powered guardrails. Write "Block Friday deployments" and Glasswatch enforces it at deployment time.',
  },
  {
    icon: Sliders,
    title: "Risk Score",
    desc: "Tenant-wide aggregate risk. The number goes down as you patch. Track reduction over time on the dashboard.",
  },
];

const workflows = [
  {
    title: "Weekly patching cycle",
    steps: [
      "Scanners push new findings via webhook",
      "Glasswatch rescores affected assets",
      "Review new high-risk items in the Vulnerabilities view",
      "Optimizer adds urgent items to existing bundles or creates new ones",
      "Approve and deploy",
    ],
  },
  {
    title: "Compliance deadline (e.g. Glasswing)",
    steps: [
      "Create a goal with a target date and vulnerability scope",
      "Run the optimizer → it generates a bundle schedule",
      "Review projected timeline and risk curve",
      "Approve bundles in sequence",
      "Track progress against goal on the Goals page",
    ],
  },
  {
    title: "Emergency patch (zero-day)",
    steps: [
      "Ingest the CVE via webhook or manual import",
      "Create an emergency maintenance window",
      "Build a targeted bundle for the CVE",
      "Fast-track approval (emergency approver)",
      "Deploy and verify",
    ],
  },
];

const integrations = [
  { name: "Tenable", type: "Scanner", direction: "Inbound webhook" },
  { name: "Qualys", type: "Scanner", direction: "Inbound webhook" },
  { name: "Rapid7 InsightVM", type: "Scanner", direction: "Inbound webhook" },
  { name: "Slack", type: "Notifications", direction: "Outbound" },
  { name: "Microsoft Teams", type: "Notifications", direction: "Outbound" },
  { name: "Jira", type: "Ticketing", direction: "Bi-directional" },
  { name: "ServiceNow", type: "ITSM", direction: "Outbound" },
  { name: "VulnCheck", type: "Threat intel", direction: "Outbound (enrichment)" },
  { name: "Snapper", type: "Runtime analysis", direction: "Outbound (scoring)" },
];

export default function HelpPage() {
  const [faqSearch, setFaqSearch] = useState("");
  const [activeSection, setActiveSection] = useState("getting-started");

  const filteredFaq = faqItems.filter(
    (item) =>
      item.question.toLowerCase().includes(faqSearch.toLowerCase()) ||
      item.answer.toLowerCase().includes(faqSearch.toLowerCase())
  );

  const sections = [
    { id: "getting-started", label: "Getting Started", icon: Zap },
    { id: "concepts", label: "Key Concepts", icon: BookOpen },
    { id: "workflows", label: "Workflows", icon: GitBranch },
    { id: "integrations", label: "Integrations", icon: Link2 },
    { id: "faq", label: "FAQ", icon: HelpCircle },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-blue-400" />
          Help Center
        </h1>
        <p className="text-gray-400 mt-2">
          Everything you need to get the most out of Glasswatch.
        </p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar nav */}
        <div className="w-52 shrink-0">
          <nav className="space-y-1 sticky top-24">
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left ${
                  activeSection === id
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
            <div className="pt-4 border-t border-gray-700 mt-4">
              <p className="text-xs text-gray-500 px-3 mb-2">External docs</p>
              <a
                href="https://glasswatch-production.up.railway.app/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                API Reference
                <ChevronRight className="w-3 h-3" />
              </a>
            </div>
          </nav>
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Getting Started */}
          {activeSection === "getting-started" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Getting Started</h2>
              <p className="text-gray-400 mb-6">
                Get up and running with Glasswatch in four steps.
              </p>
              <div className="space-y-4">
                {gettingStartedSteps.map((step, i) => (
                  <div
                    key={i}
                    className="bg-gray-800 border border-gray-700 rounded-lg p-5 flex items-start gap-4"
                  >
                    <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold shrink-0">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-white mb-1">{step.title}</h3>
                      <p className="text-gray-400 text-sm mb-3">{step.desc}</p>
                      <Link
                        href={step.link}
                        className="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        {step.linkLabel}
                        <ChevronRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-8 bg-blue-950 border border-blue-800 rounded-lg p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  <span className="font-semibold text-white">Try the AI assistant</span>
                </div>
                <p className="text-gray-400 text-sm">
                  Click the sparkle button in the bottom-right corner to ask questions in plain
                  English. Try: "What needs my attention right now?" or "Create a rule blocking
                  Friday deployments."
                </p>
              </div>
            </div>
          )}

          {/* Key Concepts */}
          {activeSection === "concepts" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Key Concepts</h2>
              <p className="text-gray-400 mb-6">
                The building blocks of Glasswatch.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {keyConcepts.map(({ icon: Icon, title, desc }) => (
                  <div
                    key={title}
                    className="bg-gray-800 border border-gray-700 rounded-lg p-5"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
                        <Icon className="w-4 h-4 text-blue-400" />
                      </div>
                      <h3 className="font-semibold text-white">{title}</h3>
                    </div>
                    <p className="text-gray-400 text-sm">{desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Workflows */}
          {activeSection === "workflows" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Common Workflows</h2>
              <p className="text-gray-400 mb-6">
                Step-by-step guides for common scenarios.
              </p>
              <div className="space-y-6">
                {workflows.map((wf) => (
                  <div
                    key={wf.title}
                    className="bg-gray-800 border border-gray-700 rounded-lg p-5"
                  >
                    <h3 className="font-semibold text-white mb-3">{wf.title}</h3>
                    <ol className="space-y-2">
                      {wf.steps.map((step, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm text-gray-400">
                          <span className="text-blue-400 font-mono w-4 shrink-0">{i + 1}.</span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Integrations */}
          {activeSection === "integrations" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Integrations</h2>
              <p className="text-gray-400 mb-6">
                Configure integrations in{" "}
                <Link href="/settings" className="text-blue-400 hover:underline">
                  Settings → Connections
                </Link>
                . Webhook setup docs:{" "}
                <a
                  href="https://glasswatch-production.up.railway.app/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  API Reference
                </a>
                .
              </p>
              <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left text-gray-400 font-medium px-4 py-3">Integration</th>
                      <th className="text-left text-gray-400 font-medium px-4 py-3">Type</th>
                      <th className="text-left text-gray-400 font-medium px-4 py-3">Direction</th>
                    </tr>
                  </thead>
                  <tbody>
                    {integrations.map((row) => (
                      <tr key={row.name} className="border-b border-gray-700/50 last:border-0">
                        <td className="px-4 py-3 text-white">{row.name}</td>
                        <td className="px-4 py-3 text-gray-400">{row.type}</td>
                        <td className="px-4 py-3 text-gray-400">{row.direction}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-6 bg-gray-800 border border-gray-700 rounded-lg p-5">
                <h3 className="font-semibold text-white mb-2">Webhook setup</h3>
                <p className="text-gray-400 text-sm mb-3">
                  All inbound webhooks use the pattern:
                </p>
                <code className="block bg-gray-900 text-green-400 rounded px-3 py-2 text-sm">
                  POST https://glasswatch-production.up.railway.app/api/v1/webhooks/scanner/&#123;scanner&#125;
                </code>
                <p className="text-gray-400 text-sm mt-3">
                  Authenticate with{" "}
                  <code className="text-green-400 text-xs">X-Webhook-Secret: &lt;your_secret&gt;</code>
                  . Configure the secret in Settings → Connections per integration.
                </p>
              </div>
            </div>
          )}

          {/* FAQ */}
          {activeSection === "faq" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">FAQ</h2>

              {/* Search */}
              <div className="relative mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search questions..."
                  value={faqSearch}
                  onChange={(e) => setFaqSearch(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {filteredFaq.length === 0 ? (
                <p className="text-gray-500 text-sm">No results for "{faqSearch}".</p>
              ) : (
                <div className="space-y-4">
                  {filteredFaq.map((item, i) => (
                    <div
                      key={i}
                      className="bg-gray-800 border border-gray-700 rounded-lg p-5"
                    >
                      <h3 className="font-medium text-white mb-2">{item.question}</h3>
                      <p className="text-gray-400 text-sm leading-relaxed">{item.answer}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-8 text-center py-6 border-t border-gray-700">
                <p className="text-gray-400 text-sm">
                  Didn't find what you were looking for?{" "}
                  <a href="mailto:support@glasswatch.io" className="text-blue-400 hover:underline">
                    Contact support
                  </a>{" "}
                  or use the AI assistant.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
