"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import NotificationBell from "@/components/notifications/NotificationBell";

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/assets", label: "Assets" },
  { href: "/vulnerabilities", label: "Vulnerabilities" },
  { href: "/goals", label: "Goals" },
  { href: "/bundles", label: "Bundles", tooltip: "Patch Schedules" },
  { href: "/schedule", label: "Schedule" },
  { href: "/approvals", label: "Approvals" },
  { href: "/rules", label: "Rules" },
  { href: "/compliance", label: "Compliance" },
  { href: "/agent", label: "AI Assistant" },
  { href: "/import", label: "Import" },
  { href: "/settings", label: "Settings" },
  { href: "/help", label: "Help" },
];

export default function Navigation() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="bg-gray-800 border-b border-gray-700 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo + desktop nav */}
          <div className="flex items-center gap-6">
            <Link href="/" className="text-2xl font-bold text-white shrink-0">
              Glasswatch
            </Link>
            <nav className="hidden lg:flex space-x-1 overflow-x-auto">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  title={(link as { href: string; label: string; tooltip?: string }).tooltip}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive(link.href)
                      ? "text-white bg-indigo-700 border-b-2 border-indigo-400"
                      : "text-gray-300 hover:text-white hover:bg-gray-700"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <NotificationBell />
            {/* Hamburger – shown below lg breakpoint */}
            <button
              className="lg:hidden p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile / tablet dropdown menu */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-gray-700 bg-gray-800">
          <nav className="flex flex-col py-2 px-4 space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                title={(link as { href: string; label: string; tooltip?: string }).tooltip}
                onClick={() => setMobileOpen(false)}
                className={`px-3 py-2.5 rounded-md text-sm font-medium transition-colors border-l-2 ${
                  isActive(link.href)
                    ? "text-white bg-indigo-900/60 border-indigo-500"
                    : "text-gray-300 hover:text-white hover:bg-gray-700 border-transparent"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
