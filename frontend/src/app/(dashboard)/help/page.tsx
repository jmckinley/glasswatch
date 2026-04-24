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
  ExternalLink,
  Bell,
  BarChart2,
  Database,
  AlertTriangle,
  ClipboardList,
} from "lucide-react";

// FAQ data — sourced from docs/FAQ.md
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
      "Glasswatch accepts inbound webhooks from Tenable, Qualys, and Rapid7 InsightVM. You can also bulk-import vulnerability and asset data via CSV from the Import page.",
  },
  {
    question: "How does AI scoring work?",
    answer:
      "Each vulnerability is scored on 8 factors: CVSS base score, EPSS exploit probability, KEV listing status, asset exposure (internet-facing vs isolated), asset criticality tier, patch availability, public exploit existence, and Snapper runtime reachability data. The score is 0–100 — higher means more urgent.",
  },
  {
    question: "What is a bundle?",
    answer:
      "A bundle is a group of patches scheduled for deployment in a single maintenance window. When you create a goal, Glasswatch generates bundles automatically. Bundles move through: Draft → Pending Approval → Approved → In Progress → Completed.",
  },
  {
    question: "What is a maintenance window?",
    answer:
      "An approved time slot for applying patches. It has a start/end time, an optional environment scope (e.g. production only), and capacity limits. Bundles are scheduled within windows.",
  },
  {
    question: "How do NLP rules work?",
    answer:
      'Write deployment rules in plain English — e.g. "Block all deployments on Fridays after 3pm" or "Require approval for production changes at month-end". Glasswatch parses them with Claude (if configured) or pattern matching, and evaluates them at deployment time. Rules can block, require approval, notify, or constrain scheduling.',
  },
  {
    question: "Can I self-host?",
    answer:
      "Yes. The backend is a standard FastAPI app with PostgreSQL. A docker-compose.yml is included. Required env vars: DATABASE_URL, SECRET_KEY. Optional: ANTHROPIC_API_KEY (AI features), WORKOS_API_KEY (SSO). See the Implementation Guide for full instructions.",
  },
  {
    question: "What data does Glasswatch store?",
    answer:
      "Vulnerability metadata, asset inventory, patch history, goal definitions, bundle schedules, deployment rules, and audit logs. Glasswatch does not store scanner credentials, raw scan files, or source code.",
  },
  {
    question: "How does the demo work?",
    answer:
      "The demo runs against a shared tenant pre-loaded with synthetic data. No signup required — click Try Demo on the login page. All actions (goals, bundles, rules) work fully in demo mode. Demo data resets periodically.",
  },
  {
    question: "What does SOC 2 readiness mean?",
    answer:
      "Glasswatch maintains immutable audit logs, role-based access, JWT auth with short-lived tokens, TLS-only communication, and full tenant isolation — all aligned with SOC 2 requirements. The Compliance dashboard tracks your patching SLA adherence, which directly supports SOC 2 CC7.1 controls during an audit.",
  },
  {
    question: "How does the audit log work?",
    answer:
      "Every meaningful action in Glasswatch generates an audit event — bundle approvals, vulnerability imports, user logins (including failed attempts), invite sends, and maintenance window changes. Go to Audit Log in the sidebar to browse, filter by action type/resource/date, expand any row for full structured details, and export to CSV for auditors or compliance evidence packages.",
  },
  {
    question: "Can I see failed login attempts?",
    answer:
      "Yes. Failed logins appear in the Audit Log with action 'user.login_failed', a red ✗ status, and the source IP address. Useful for detecting brute-force attempts or compromised credentials. Navigate to Audit Log and filter by action type 'user.login_failed'.",
  },
  {
    question: "How does the goal optimizer work?",
    answer:
      "Define a goal (e.g. eliminate KEV vulns on internet-facing assets by July 1). The optimizer identifies in-scope vulns, ranks them by risk score, distributes across your maintenance windows, and generates bundles respecting all constraints. It uses Google OR-Tools; if the problem is very large it falls back to a fast heuristic.",
  },
  {
    question: "What approval workflows are supported?",
    answer:
      "Configurable approval chains: single approver, role-based (admin only), multi-stage (analyst then admin), or automatic approval for low-risk bundles below a threshold. All actions are audit-logged.",
  },
  {
    question: "How does the AI assistant work?",
    answer:
      'The floating AI assistant (bottom-right sparkle button) accepts plain English. "What needs my attention?" pulls live KEV + overdue bundle data. "Create a rule blocking Friday deployments" creates the rule directly. "Show risk score for CVE-2021-44228" looks it up. It uses your live data.',
  },
  {
    question: "Does Glasswatch support multi-tenancy?",
    answer:
      "Yes. Every object is scoped to a tenant. Tenants are isolated at the database level. Each tenant supports multiple users with different roles (admin, analyst, viewer).",
  },
  {
    question: "How do I set up Slack notifications?",
    answer:
      "Go to Settings → Integrations → Slack and paste in an incoming webhook URL from your Slack workspace. Then go to Settings → Alert Rules and create a rule with Slack as the delivery channel. The webhook just enables delivery — you still need at least one alert rule to trigger messages.",
  },
  {
    question: "How do I import vulnerabilities from a CSV?",
    answer:
      "Navigate to Import in the sidebar. Download the template CSV, fill in your data (required columns: asset_name, cve_id, severity, cvss_score, discovered_date), then upload. The asset_name must match an existing asset — import assets first if needed.",
  },
  {
    question: "What's the risk score on the dashboard?",
    answer:
      "The tenant-wide risk score (0–100) is an aggregate of all unpatched vulnerabilities weighted by their individual risk scores and asset criticality. It goes down as you complete bundles. Tracking it over time shows whether your patch program is making real progress.",
  },
];

const gettingStartedSteps = [
  {
    title: "Connect a scanner",
    desc: "Add your Tenable, Qualys, or Rapid7 connection in Settings → Integrations. Glasswatch will start ingesting findings via webhook as scans complete.",
    link: "/settings",
    linkLabel: "Go to Settings",
  },
  {
    title: "Review your assets",
    desc: "Check that your assets have the right exposure levels set (Internet / Intranet / Isolated) — this heavily influences risk scoring.",
    link: "/assets",
    linkLabel: "View Assets",
  },
  {
    title: "Create a goal",
    desc: "Define what you want to achieve and by when. The optimizer generates patch bundles automatically from your goal.",
    link: "/goals",
    linkLabel: "Create Goal",
  },
  {
    title: "Review and approve bundles",
    desc: "Review the generated patch bundles, adjust scope as needed, and approve for deployment.",
    link: "/bundles",
    linkLabel: "View Bundles",
  },
];

const keyConcepts = [
  {
    icon: Shield,
    title: "Vulnerability Scoring",
    desc: "8-factor AI scoring that goes beyond CVSS. Combines EPSS, KEV status, asset exposure, exploit availability, and runtime reachability into a single 0–100 risk score.",
  },
  {
    icon: Target,
    title: "Goals",
    desc: 'Outcome-oriented objectives like "patch all KEV vulns by July 1". The optimizer generates the full patching plan — scheduled bundles across your maintenance windows — to hit your target.',
  },
  {
    icon: Package,
    title: "Bundles",
    desc: "Groups of patches scheduled for a single deployment window. Auto-generated by the optimizer. Move through Draft → Pending Approval → Approved → In Progress → Completed.",
  },
  {
    icon: Calendar,
    title: "Maintenance Windows",
    desc: "Approved time slots for patching. Bundles are scheduled within windows. Configure per environment with recurrence, capacity limits, and blackout dates.",
  },
  {
    icon: FileText,
    title: "Deployment Rules",
    desc: 'NLP-powered governance policies. Write "Block Friday deployments in production" and Glasswatch enforces it at deployment time. Rules can block, require approval, notify, or constrain scheduling.',
  },
  {
    icon: Sliders,
    title: "Risk Score",
    desc: "Tenant-wide aggregate risk (0–100). Goes down as you complete bundles. The Compliance dashboard tracks MTTP, SLA adherence, and framework-specific posture.",
  },
  {
    icon: Bell,
    title: "Notifications",
    desc: "Real-time alerts for KEV additions, bundle status changes, and SLA warnings. Delivered in-app, via Slack, Teams, or email. Configurable per alert type.",
  },
  {
    icon: BarChart2,
    title: "Compliance & Reporting",
    desc: "BOD 22-01, SOC 2, and PCI DSS posture cards. MTTP metrics by severity, environment, and team. Export PDF reports for leadership or auditors.",
  },
  {
    icon: ClipboardList,
    title: "Audit Log",
    desc: "Complete tamper-evident record of every action in your workspace. Bundle approvals, vulnerability imports, user logins, and system events — timestamped with user, IP, and full context. Searchable, filterable, exportable to CSV for auditors.",
  },
];

const commonWorkflows = [
  {
    title: "I want to patch all KEV vulnerabilities",
    icon: AlertTriangle,
    steps: [
      "Go to Goals → New Goal",
      'Name it something like "KEV Elimination" and set a target date',
      'Under CVE Filter, enable "KEV-listed only"',
      "Scope to your production assets (environment = production)",
      "Click Create and Optimize — bundles are generated automatically",
      "Review bundles in the Bundles view, approve the first one",
      "Track progress on the Goals page; the optimizer rebalances as you complete bundles",
    ],
  },
  {
    title: "I want to prepare an evidence package for a security audit",
    icon: Shield,
    steps: [
      "Go to Audit Log in the sidebar",
      "Set Date From to the start of your audit period",
      "Click Export CSV — this downloads all audit events in the selected range",
      "Go to Compliance → Export Report for the patching posture PDF",
      "Combine both exports as evidence: audit trail + SLA compliance data",
      "The Compliance page shows your MTTP and SLA adherence per framework (SOC 2, PCI DSS, BOD 22-01)",
    ],
  },
  {
    title: "I want to prepare for a SOC 2 audit",
    icon: Shield,
    steps: [
      "Go to Compliance — review the SOC 2 card for current posture",
      "Look at the SLA tracking table to find overdue items",
      "Create a goal scoped to your SOC 2 audit scope (usually production assets)",
      "Set the target date to your audit date",
      "The optimizer will generate bundles to clear the backlog before the deadline",
      "Use the Export Report button to generate a PDF for your auditor showing patch history and SLA compliance",
    ],
  },
  {
    title: "I want to onboard a new scanner",
    icon: Database,
    steps: [
      "Go to Settings → Integrations and select your scanner (Tenable, Qualys, or Rapid7)",
      "Enter your API credentials — Glasswatch will generate a webhook secret",
      "Copy the webhook URL shown in Glasswatch",
      "In your scanner, configure a notification webhook to POST to that URL after each scan",
      "Set the X-Webhook-Secret header to the secret Glasswatch provided",
      "Run a test scan — new findings should appear in Vulnerabilities within seconds",
      "Check Settings → Connections for a green health indicator confirming the integration is live",
    ],
  },
  {
    title: "I want to set up Slack alerts",
    icon: Bell,
    steps: [
      "In Slack, go to your workspace settings and create a new incoming webhook (Apps → Incoming Webhooks)",
      "Choose the channel where alerts should appear and copy the webhook URL",
      "In Glasswatch, go to Settings → Integrations → Slack and paste the URL",
      "Click Test to confirm delivery is working",
      "Go to Settings → Alert Rules → New Rule",
      "Choose the event type (e.g., KEV Alert), set any filters, and select Slack as the delivery channel",
      "Save — you'll now receive Slack messages for matching events",
    ],
  },
];

const workflows = [
  {
    title: "Weekly patching cycle",
    steps: [
      "Scanners push new findings via webhook as scans complete",
      "Glasswatch rescores affected assets immediately",
      "Review new high-risk items in the Vulnerabilities view",
      "Optimizer adds urgent items to existing bundles or proposes new ones",
      "Approve and deploy within the next maintenance window",
    ],
  },
  {
    title: "Compliance deadline (e.g. Glasswing)",
    steps: [
      "Create a goal with a target date and vulnerability scope",
      "Run the optimizer → it generates a full bundle schedule",
      "Review projected timeline and risk reduction on the goal detail page",
      "Approve bundles in sequence as maintenance windows open",
      "Track progress against goal — re-optimize if windows slip",
    ],
  },
  {
    title: "Emergency patch (zero-day)",
    steps: [
      "Ingest the CVE via scanner webhook or manual import",
      "Create an emergency maintenance window (Settings → Maintenance Windows)",
      "Use 'Patch These Now' on the dashboard or create a manual bundle",
      "Fast-track through approval (add the CVE context in the approval request)",
      "Deploy and verify; bundle execution log captures the full audit trail",
    ],
  },
];

const integrations = [
  { name: "Tenable", type: "Scanner", direction: "Inbound webhook" },
  { name: "Qualys", type: "Scanner", direction: "Inbound webhook" },
  { name: "Rapid7 InsightVM", type: "Scanner", direction: "Inbound webhook" },
  { name: "Slack", type: "Notifications", direction: "Outbound" },
  { name: "Microsoft Teams", type: "Notifications", direction: "Outbound" },
  { name: "Email (Resend)", type: "Notifications", direction: "Outbound" },
  { name: "Jira", type: "Ticketing", direction: "Bi-directional" },
  { name: "ServiceNow", type: "ITSM", direction: "Outbound" },
  { name: "VulnCheck", type: "Threat intel", direction: "Outbound (enrichment)" },
  { name: "Snapper", type: "Runtime analysis", direction: "Outbound (scoring)" },
  { name: "Audit Log (built-in)", type: "Compliance", direction: "Internal — all events auto-recorded" },
];

const docLinks = [
  {
    title: "User Guide",
    desc: "Every feature explained for security managers and analysts.",
    href: "https://github.com/your-org/glasswatch/blob/main/docs/USER_GUIDE.md",
    icon: BookOpen,
  },
  {
    title: "Implementation Guide",
    desc: "Deployment, scanner setup, auth configuration, and ops for IT/SecOps teams.",
    href: "https://github.com/your-org/glasswatch/blob/main/docs/IMPLEMENTATION_GUIDE.md",
    icon: Database,
  },
  {
    title: "API Reference",
    desc: "Interactive Swagger docs for all 150+ API endpoints.",
    href: "https://glasswatch-production.up.railway.app/docs",
    icon: FileText,
    external: true,
  },
  {
    title: "FAQ",
    desc: "Quick answers to common questions.",
    href: "#",
    icon: HelpCircle,
    internal: "faq",
  },
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
    { id: "workflows", label: "Common Workflows", icon: GitBranch },
    { id: "integrations", label: "Integrations", icon: Link2 },
    { id: "audit", label: "Audit Log", icon: ClipboardList },
    { id: "docs", label: "Documentation", icon: ExternalLink },
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
                <p className="text-gray-400 text-sm mb-3">
                  Click the sparkle button in the bottom-right corner to ask questions in plain
                  English. Some things to try:
                </p>
                <ul className="space-y-1 text-sm text-gray-400">
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">›</span>
                    "What needs my attention right now?"
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">›</span>
                    "How many KEV vulnerabilities do we have open?"
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">›</span>
                    "Create a rule blocking Friday deployments in production"
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-400 mt-0.5">›</span>
                    "Show me bundles pending my approval"
                  </li>
                </ul>
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

          {/* Common Workflows */}
          {activeSection === "workflows" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Common Workflows</h2>
              <p className="text-gray-400 mb-6">
                Step-by-step guides for the most common scenarios.
              </p>

              {/* Task-oriented workflows */}
              <div className="space-y-6 mb-10">
                {commonWorkflows.map((wf) => (
                  <div
                    key={wf.title}
                    className="bg-gray-800 border border-gray-700 rounded-lg p-5"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center shrink-0">
                        <wf.icon className="w-4 h-4 text-blue-400" />
                      </div>
                      <h3 className="font-semibold text-white">{wf.title}</h3>
                    </div>
                    <ol className="space-y-2">
                      {wf.steps.map((step, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm text-gray-400">
                          <span className="text-blue-400 font-mono w-4 shrink-0 mt-0.5">{i + 1}.</span>
                          {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                ))}
              </div>

              {/* Recurring cycle workflows */}
              <h3 className="text-lg font-semibold text-white mb-4">Operational Cycles</h3>
              <div className="space-y-6">
                {workflows.map((wf) => (
                  <div
                    key={wf.title}
                    className="bg-gray-800 border border-gray-700 rounded-lg p-5"
                  >
                    <h4 className="font-semibold text-white mb-3">{wf.title}</h4>
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
                  Settings → Integrations
                </Link>
                . Full setup instructions are in the{" "}
                <a
                  href="https://github.com/your-org/glasswatch/blob/main/docs/IMPLEMENTATION_GUIDE.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  Implementation Guide
                </a>
                .
              </p>
              <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden mb-6">
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

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 mb-6">
                <h3 className="font-semibold text-white mb-2">Scanner webhooks</h3>
                <p className="text-gray-400 text-sm mb-3">
                  All inbound scanner webhooks use the pattern:
                </p>
                <code className="block bg-gray-900 text-green-400 rounded px-3 py-2 text-sm mb-3">
                  POST https://glasswatch-production.up.railway.app/api/v1/webhooks/&#123;scanner&#125;
                </code>
                <p className="text-gray-400 text-sm">
                  Authenticate with{" "}
                  <code className="text-green-400 text-xs">X-Webhook-Secret: &lt;your_secret&gt;</code>
                  . Configure the secret in Settings → Connections per integration.
                </p>
              </div>

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
                <h3 className="font-semibold text-white mb-2">SIEM / CMDB export</h3>
                <p className="text-gray-400 text-sm mb-3">
                  Pull vulnerability and asset data into your SIEM or CMDB using the export endpoints:
                </p>
                <code className="block bg-gray-900 text-green-400 rounded px-3 py-2 text-sm mb-2">
                  GET /api/v1/export/vulnerabilities?format=csv
                </code>
                <code className="block bg-gray-900 text-green-400 rounded px-3 py-2 text-sm">
                  GET /api/v1/export/assets?format=json
                </code>
                <p className="text-gray-400 text-sm mt-3">
                  Authenticate with an API key from Settings → API Keys using the{" "}
                  <code className="text-green-400 text-xs">X-API-Key</code> header.
                </p>
              </div>
            </div>
          )}

          {/* Audit Log */}
          {activeSection === "audit" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Audit Log</h2>
              <p className="text-gray-400 mb-6">
                A complete record of every action taken in your workspace.{" "}
                <Link href="/audit-log" className="text-blue-400 hover:underline">
                  Open Audit Log →
                </Link>
              </p>

              {/* What's recorded */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 mb-5">
                <h3 className="font-semibold text-white mb-3">What&apos;s recorded</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {[
                    { badge: "📦", color: "bg-indigo-900/40 text-indigo-300 border-indigo-700", label: "Bundle events", examples: "created, approved, status changed, executed" },
                    { badge: "🛡️", color: "bg-amber-900/40 text-amber-300 border-amber-700", label: "Vulnerability events", examples: "CSV imported, webhook ingestion" },
                    { badge: "👤", color: "bg-emerald-900/40 text-emerald-300 border-emerald-700", label: "User events", examples: "login, failed login, invited, accepted" },
                    { badge: "🗓️", color: "bg-blue-900/40 text-blue-300 border-blue-700", label: "Maintenance events", examples: "window created, deleted" },
                    { badge: "🎯", color: "bg-purple-900/40 text-purple-300 border-purple-700", label: "Goal events", examples: "created, updated" },
                    { badge: "⚙️", color: "bg-gray-900/40 text-gray-300 border-gray-700", label: "System events", examples: "config changes, integration events" },
                  ].map((cat) => (
                    <div key={cat.label} className={`border rounded-lg p-3 ${cat.color}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span>{cat.badge}</span>
                        <span className="font-medium">{cat.label}</span>
                      </div>
                      <p className="text-xs opacity-75">{cat.examples}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tips */}
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 mb-5">
                <h3 className="font-semibold text-white mb-3">Tips</h3>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li className="flex items-start gap-2"><span className="text-blue-400 mt-0.5">›</span>Click any row to expand the full structured details — useful for seeing old/new status on bundle changes</li>
                  <li className="flex items-start gap-2"><span className="text-blue-400 mt-0.5">›</span>Set a date range and click Export CSV to generate an evidence package for auditors</li>
                  <li className="flex items-start gap-2"><span className="text-blue-400 mt-0.5">›</span>Filter by action &ldquo;user.login_failed&rdquo; to review failed login attempts with source IPs</li>
                  <li className="flex items-start gap-2"><span className="text-blue-400 mt-0.5">›</span>Audit entries are never modified or deleted — suitable for compliance evidence</li>
                </ul>
              </div>

              <Link
                href="/audit-log"
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
              >
                <ClipboardList className="w-4 h-4" />
                Open Audit Log
              </Link>
            </div>
          )}

          {/* Documentation */}
          {activeSection === "docs" && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-4">Documentation</h2>
              <p className="text-gray-400 mb-6">
                Full reference documentation for Glasswatch.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                {docLinks.map(({ title, desc, href, icon: Icon, external, internal }) => (
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
                    <p className="text-gray-400 text-sm mb-3">{desc}</p>
                    {internal ? (
                      <button
                        onClick={() => setActiveSection(internal)}
                        className="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        View FAQ
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    ) : (
                      <a
                        href={href}
                        target={external ? "_blank" : undefined}
                        rel={external ? "noopener noreferrer" : undefined}
                        className="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        Open {title}
                        {external ? <ExternalLink className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      </a>
                    )}
                  </div>
                ))}
              </div>

              <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
                <h3 className="font-semibold text-white mb-3">Quick tips by feature</h3>
                <div className="space-y-4 text-sm text-gray-400">
                  <div>
                    <p className="text-white font-medium mb-1">Vulnerabilities</p>
                    <p>Filter by KEV to find the highest-urgency items first. Click any CVE to see affected assets, risk score breakdown, and patch details. The SLA column tells you when it needs to be resolved.</p>
                  </div>
                  <div>
                    <p className="text-white font-medium mb-1">Assets</p>
                    <p>Stale assets (no scan data in 30+ days) are flagged with a warning indicator. Set accurate criticality levels (1–5) — this is one of the biggest factors in risk scoring. Use "Patch This Asset" for urgent one-off remediation.</p>
                  </div>
                  <div>
                    <p className="text-white font-medium mb-1">Goals</p>
                    <p>Start with a focused goal (KEV only, one environment) rather than trying to address everything at once. Re-run the optimizer after completing bundles to rebalance the remaining work.</p>
                  </div>
                  <div>
                    <p className="text-white font-medium mb-1">Bundles</p>
                    <p>Edit/Tweak Mode on an approved bundle resets it to Draft and clears the approval — you'll need to re-approve. Check the pre-flight checklist before executing; it catches common blockers automatically.</p>
                  </div>
                  <div>
                    <p className="text-white font-medium mb-1">Rules</p>
                    <p>Write rules in natural language — Glasswatch parses them. If a rule isn't firing as expected, check the parsed version shown in the rule detail to confirm it was interpreted correctly.</p>
                  </div>
                  <div>
                    <p className="text-white font-medium mb-1">Notifications</p>
                    <p>A Slack webhook in Settings only enables the delivery channel. You still need an alert rule (Settings → Alert Rules) that uses Slack as its channel. Both are required for alerts to send.</p>
                  </div>
                  <div>
                    <p className="text-white font-medium mb-1">Audit Log</p>
                    <p>Use date range filters to narrow audit exports for a specific audit period. Expand any row to see the full structured details JSON — especially useful for &ldquo;bundle.status_changed&rdquo; events which show before/after values. Failed logins show the source IP in the details panel.</p>
                  </div>
                </div>
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
                <p className="text-gray-500 text-sm">No results for &ldquo;{faqSearch}&rdquo;.</p>
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
                  Didn&apos;t find what you were looking for?{" "}
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
