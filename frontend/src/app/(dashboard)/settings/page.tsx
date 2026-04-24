"use client";

import Link from "next/link";

const SETTINGS_SECTIONS = [
  {
    id: "general",
    href: "/settings/general",
    icon: "⚙️",
    name: "General",
    description: "Organization name, timezone, and display preferences",
  },
  {
    id: "notifications",
    href: "/settings/notifications",
    icon: "🔔",
    name: "Notifications",
    description: "Email, Slack, and alert preferences",
  },
  {
    id: "integrations",
    href: "/settings/integrations",
    icon: "🔗",
    name: "Integrations",
    description: "Connect Slack, Jira, and other collaboration tools",
  },
  {
    id: "connections",
    href: "/settings/connections",
    icon: "☁️",
    name: "Connections",
    description: "Manage cloud providers and external services",
  },
  {
    id: "security",
    href: "/settings/security",
    icon: "🛡️",
    name: "Security",
    description: "Approval policies and bundle configuration",
  },
  {
    id: "alerts",
    href: "/settings/alerts",
    icon: "⚡",
    name: "Alert Rules",
    description: "Configure which events trigger Slack, email, and in-app alerts",
  },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-gray-400">Manage your Glasswatch workspace preferences</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {SETTINGS_SECTIONS.map((section) => (
          <Link
            key={section.id}
            href={section.href}
            className="block p-6 bg-gray-800 rounded-lg border-2 border-gray-700 hover:border-blue-500 transition-all group"
          >
            <div className="text-4xl mb-3">{section.icon}</div>
            <h3 className="text-xl font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
              {section.name}
            </h3>
            <p className="text-gray-400 text-sm">{section.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
