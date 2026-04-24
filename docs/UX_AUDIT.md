# Glasswatch UX Audit — April 2026

## Summary

Glasswatch's frontend is clean and well-structured with a consistent dark theme and solid empty-state coverage already in place. The biggest friction points are jargon (EPSS, KEV, MTTP, CVSS) left unexplained for users not steeped in vulnerability management, and a few areas where the value of connecting a scanner isn't immediately obvious. This pass tightens those gaps with tooltips, subtitles, and prompt copy — no structural changes were needed.

## Page-by-Page Findings

### Login (`/auth/login`)
- **Finding:** Solid. Demo button is prominent at top, OAuth options available, tab UI for sign-in vs register is clear.
- **Fixed:** No changes needed. Already handles loading states, errors, and redirect logic correctly.

### Onboarding (`/onboarding`)
- **Finding:** Multi-step wizard with 6 steps. Comprehensive. Goal templates and provider cards are well-labeled.
- **Fixed:** No changes needed — this page is rich and self-explanatory.

### Dashboard (`/` — focus + full modes)
- **Finding:** The "Right Now" focus panel already has four well-differentiated states: KEV critical, critical vulns, zero vulns (empty/new account), and good standing. The zero-vuln state correctly directs users to connect a scanner or import CSV with visible CTAs.
- **Fixed:** Empty state was already handled. No changes needed.

### Vulnerabilities (`/vulnerabilities`)
- **Finding:** CVSS and EPSS column headers already had `<Tooltip>` components. The KEV badge in table rows had no explanation — first-time users see a red "KEV" pill with no context. The "KEV Listed Only" filter checkbox similarly lacked a tooltip.
- **Fixed:**
  - Added `title` attribute to every KEV badge in table rows: *"CISA Known Exploited Vulnerability — actively exploited in the wild, patch immediately"*
  - Wrapped the "KEV Listed Only" filter label with a `<Tooltip>` component matching the BOD 22-01 context already used in the stats section.

### Bundles (`/bundles`)
- **Finding:** Page already had an explanatory subtitle: *"A bundle groups related patches for coordinated deployment within a maintenance window."* Empty states are excellent — different copy for "all" vs filtered tabs, with navigation links to Goals and Vulnerabilities.
- **Fixed:** No changes needed. Already well-explained.

### Compliance (`/compliance`)
- **Finding:** The MTTP section heading read "Mean Time To Patch (MTTP)" — the acronym was spelled out in the heading but no subtitle explained what it measures or why it matters. Users unfamiliar with the metric had to infer.
- **Fixed:** Added a subtitle paragraph under the MTTP section heading: *"Average days from vulnerability discovery to remediation, broken down by severity, environment, and team."*

### AI Agent (floating `AIAssistant` component)
- **Finding:** The AI assistant already showed starter prompts when the conversation was empty (`isFirstMessage` guard). The existing prompts were functional but generic ("What needs my attention right now?", "Show me critical KEV vulnerabilities").
- **Fixed:** Updated `starterPrompts` to the three specifically requested prompts plus two others:
  - "What needs my attention today?"
  - "Show me all KEV vulnerabilities overdue"
  - "How is our SOC 2 compliance trending?"
  - "Create a rule blocking Friday deployments"
  - "What maintenance windows do we have?"

### Navigation (`Navigation.tsx`)
- **Finding:** Clean horizontal nav with mobile hamburger. Active state is clear (bg-gray-900). All 12 routes present. No issues.
- **Fixed:** No changes needed.

### Settings / Connections (`/settings/connections`)
- **Finding:** The Add Connection modal showed provider cards with API-sourced descriptions. For scanners (Tenable, Qualys, Rapid7), the API description may be generic or empty. The cards had no visual differentiation or explicit "Connect" CTA text within the card itself. Empty state (no connections yet) was already excellent with a large "Add Your First Connection" button.
- **Fixed:**
  - Added `SCANNER_BENEFIT` static map with one-liner descriptions for Tenable, Qualys, and Rapid7 explaining what connecting does.
  - Scanner cards in the provider picker now show the benefit text instead of (or in place of) the generic API description.
  - Scanner cards additionally show a "Connect →" label in blue so the action intent is unambiguous.

## Needs Backend Work (not fixed)

- **KEV badge on individual vulnerability detail page** (`/vulnerabilities/[id]`) — not reviewed in this pass; may need similar tooltip treatment.
- **MTTP trend indicator** — the MTTP section shows current averages but no trend (improving/worsening vs. prior period). Would require backend time-series data.
- **Compliance framework scores for orgs without data** — framework cards default to "COMPLIANT / 100%" when no data is present, which could be misleading for new accounts. Needs a "no data yet" state from the API.
- **Scanner connection health auto-refresh** — connections page shows "Never checked" for new integrations; a background health-check trigger on add would improve confidence.
- **AI agent suggested actions per response** — the `suggested_actions` field comes from the API but many responses return an empty array; richer follow-up suggestions require backend agent improvements.

## Overall UX Score: 8/10 — Polished foundation with smart empty states; main gap is unexplained security jargon for non-specialist users, now largely addressed.
