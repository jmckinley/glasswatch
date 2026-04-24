"use client";

import Link from "next/link";

// Reordered: Integrations/Connections first, then Notifications, Team, Account
const SETTINGS_SECTIONS = [
  {
    id: "integrations",
    href: "/settings/integrations",
    icon: "🔗",
    name: "Integrations",
    description: "Connect Slack, Jira, and other collaboration tools",
    badge: "Start here",
    badgeColor: "bg-indigo-600 text-white",
  },
  {
    id: "connections",
    href: "/settings/connections",
    icon: "☁️",
    name: "Scanner Connections",
    description: "Connect Tenable, Qualys, or Rapid7 to sync vulnerability data automatically",
    badge: null,
    badgeColor: "",
  },
  {
    id: "alerts",
    href: "/settings/alerts",
    icon: "⚡",
    name: "Alert Rules",
    description: "Configure which events trigger Slack, email, and in-app alerts",
    badge: null,
    badgeColor: "",
  },
  {
    id: "notifications",
    href: "/settings/notifications",
    icon: "🔔",
    name: "Notifications",
    description: "Email, Slack, and Teams notification preferences",
    badge: null,
    badgeColor: "",
  },
  {
    id: "team",
    href: "/settings/team",
    icon: "👥",
    name: "Team",
    description: "Manage team members, roles, and send invitations",
    badge: null,
    badgeColor: "",
  },
  {
    id: "security",
    href: "/settings/security",
    icon: "🛡️",
    name: "Security",
    description: "Approval policies and bundle configuration",
    badge: null,
    badgeColor: "",
  },
  {
    id: "general",
    href: "/settings/general",
    icon: "⚙️",
    name: "General",
    description: "Organization name, timezone, and display preferences",
    badge: null,
    badgeColor: "",
  },
];

// Quick-connect scanner cards
const SCANNERS = [
  {
    id: "tenable",
    name: "Tenable.io",
    icon: "🔍",
    description: "Connect Tenable.io to sync vulnerability data automatically",
    href: "/settings/connections?scanner=tenable",
  },
  {
    id: "qualys",
    name: "Qualys",
    icon: "🛡️",
    description: "Connect Qualys VMDR to ingest vulnerability findings via webhook",
    href: "/settings/connections?scanner=qualys",
  },
  {
    id: "rapid7",
    name: "Rapid7 InsightVM",
    icon: "📡",
    description: "Connect Rapid7 InsightVM to receive scan results in real time",
    href: "/settings/connections?scanner=rapid7",
  },
];

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-gray-400">Manage your Glasswatch workspace preferences</p>
      </div>

      {/* Quick-connect scanners */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-1">Connect a Scanner</h2>
        <p className="text-sm text-gray-400 mb-4">
          Glasswatch ingests vulnerability data from these scanners via webhook. Connect at least one to start.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SCANNERS.map((scanner) => (
            <div
              key={scanner.id}
              className="bg-gray-800 rounded-lg border border-gray-700 p-5 flex flex-col gap-3"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{scanner.icon}</span>
                <div>
                  <h3 className="font-semibold text-white text-sm">{scanner.name}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-400">
                    Not Connected
                  </span>
                </div>
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">{scanner.description}</p>
              <Link
                href={scanner.href}
                className="block text-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Connect
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* All settings sections */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4">All Settings</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {SETTINGS_SECTIONS.map((section) => (
            <Link
              key={section.id}
              href={section.href}
              className="block p-6 bg-gray-800 rounded-lg border-2 border-gray-700 hover:border-indigo-500 transition-all group relative"
            >
              {section.badge && (
                <span className={`absolute top-3 right-3 text-xs px-2 py-0.5 rounded-full font-medium ${section.badgeColor}`}>
                  {section.badge}
                </span>
              )}
              <div className="text-3xl mb-3">{section.icon}</div>
              <h3 className="text-lg font-semibold text-white mb-1 group-hover:text-indigo-400 transition-colors">
                {section.name}
              </h3>
              <p className="text-gray-400 text-sm">{section.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
