# Glasswatch UX Audit — April 2026

## Overall Assessment

The dark-theme foundation is consistent and solid throughout the app, with well-structured layouts and working API integration across all pages. The weakest areas were missing empty states, inconsistent CTA hierarchy (scattered blue/green/gray buttons with no visual priority system), and the AI assistant being hidden as a floating widget with no discoverability as a primary feature. Overall quality is good for a sprint-9 product — the bones are right, the polish layer is what this audit addresses.

## Sprint A Pages (Login, Dashboard, Vulnerabilities, Nav)
*Sprint A agent covers Login, Dashboard, Vulnerabilities, and Navigation in detail. Nav now includes "AI Analyst" link pointing to the new `/agent` page.*

---

## Sprint B Pages

### Bundles

**Found:**
- Status badge colors were incorrect: `in_progress` was yellow (should be indigo/blue), `scheduled` (Pending) was blue (should be amber), `cancelled` had same gray style as `draft`
- No explainer banner — first-time users had no context for what a bundle is or the lifecycle
- Loading state was a centered spinner, not skeleton rows (jarring layout shift)
- "View →" CTA had no visual hierarchy (plain blue, same as primary actions)
- No "New Bundle" button in the header — unclear how to create one
- Empty state text was generic ("Bundles are created automatically…") without a clear action

**Fixed:**
- STATUS_BADGE colors updated: Draft=gray, Pending(scheduled)=amber, Approved=emerald, In Progress=indigo, Completed=gray-muted, Cancelled=red
- Added dismissible explainer banner (stored in localStorage via `glasswatch_bundles_banner_dismissed` key)
- Added `BundleStepper` component — subtle dot/line progress indicator under each status badge
- Replaced spinner with 3 skeleton table rows
- Added "New Bundle →" indigo filled button in header (links to `/goals`)
- Updated "View →" to "View Details" with secondary outline style
- Updated empty state to: "No patch bundles yet. Create your first bundle to start scheduling remediation work." with "Create Bundle →" indigo filled CTA

---

### Compliance

**Found:**
- Export PDF button was blue-600, buried in header — not prominently indigo, label was generic "Export PDF"
- Framework cards showed raw counts (e.g., `0 / 0 KEV`) as primary metric instead of the compliance %
- No trend arrows on framework cards or MTTP table
- MTTP description was verbose, not the canonical definition
- No empty state for when no framework data is available
- MTTP by-team table had no trend indicators

**Fixed:**
- Export button changed to `bg-indigo-600`, label updated to "Export Audit Report", added `shadow-lg`
- All three framework cards (BOD 22-01, SOC 2, PCI DSS) now show primary % in `text-5xl font-bold`
- % color-coded: ≥90% = emerald, 70-89% = amber, <70% = red
- Trend arrow added next to each %, colored to match severity (↑ emerald, → gray, ↓ red)
- MTTP subtitle updated to canonical: `Mean Time To Patch (MTTP) — average days from vulnerability discovery to confirmed remediation`
- MTTP by-team table now shows ↓ emerald (improving), ↑ red (worsening), → gray (stable) based on `target_days` vs `avg_days`
- Empty state added when `frameworks` object is empty

---

### AI Agent

**Found:**
- No dedicated page — AI assistant was only accessible as a small floating button in the bottom-right corner, easily missed
- No suggested prompts visible before a conversation starts
- Input had no label or meaningful placeholder
- No nav link in the top navigation

**Fixed:**
- Created `/agent/page.tsx` — full-page dedicated chat interface with proper layout
- Empty conversation state shows "⚡ Your AI Security Analyst" headline with description
- 6 suggested prompt chips in 3×2 grid shown in empty state and 3 quick chips above input once chat starts
- Clicking a prompt chip sends immediately (no extra click)
- Input area has visible label "Ask your AI security analyst" and specific placeholder "e.g. What critical vulnerabilities need patching this week?"
- User messages: right-aligned, indigo background
- AI messages: left-aligned, gray-800 background, "AI" avatar badge
- `whitespace-pre-wrap` on message content for proper line-break rendering
- Typing indicator (3-dot bounce animation)
- Actions taken chips (emerald) and suggested follow-up action chips shown per message
- Added "AI Analyst" to top navigation (`Navigation.tsx`)

---

### Settings

**Found:**
- Navigation cards were unordered — Integrations/Connections were buried in the middle
- No scanner quick-connect section for new users
- "Connections" section was labeled generically, not specifically for scanners
- Hover state used `border-blue-500` (should be indigo)
- No visual priority indication (all cards identical weight)

**Fixed:**
- Reordered sections: Integrations → Scanner Connections → Alert Rules → Notifications → Team → Security → General
- Added "Start here" badge (indigo) on Integrations card
- Added "Scanner Connections" quick-connect section at top with 3 scanner cards (Tenable, Qualys, Rapid7) with "Connect" indigo filled CTA
- Changed hover border to `hover:border-indigo-500` throughout
- Section labeled "Scanner Connections" for clarity (links to `/settings/connections`)

---

### Import

**Found:**
- "↓ template" download buttons were tiny text links with no visual weight
- Drop zone hover state switched to `hover:border-gray-500` (nearly invisible)
- Success/error states were already implemented (no change needed there)

**Fixed:**
- Download template buttons converted to outline buttons: `border border-indigo-600 text-indigo-400 hover:bg-indigo-600/20 text-xs font-medium rounded-md px-3 py-1`
- Drop zone drag color updated to `border-indigo-500 bg-indigo-900/20` (more visible)
- Hover state updated to `hover:border-indigo-600` (stronger contrast)

---

### Maintenance Windows

**Found:**
- "New Window" button was blue-600 (should be indigo to match system CTA color)
- View mode toggle (Grid/Timeline/Calendar) looked like a basic outline border group, not a clear segmented control
- Conflict warnings were subtle `bg-yellow-500/10 border border-yellow-500/30` — easy to miss
- Cards already show environment badges (production/staging/dev) with appropriate colors — no change needed

**Fixed:**
- "New Window" button changed to `bg-indigo-600 hover:bg-indigo-700`
- View toggle redesigned as a proper segmented control: `bg-gray-800 border border-gray-600 rounded-lg p-1 gap-1` with active state `bg-indigo-600 shadow-sm` and inactive state `hover:bg-gray-700`
- Conflict warning block replaced with prominent amber banner: `bg-amber-900/30 border border-amber-700 rounded-xl p-4` with header "⚠️ Schedule Conflicts Detected" and each conflict as a `border-l-2 border-amber-600` item

---

## Needs Backend Work

- **Bundle Approve/Cancel inline actions**: Bundle approve/cancel CTAs can't be added to the list view without API endpoints that support inline status changes (currently only available on detail pages)
- **Trend data for compliance**: Trend arrows on framework cards currently use current % as a proxy (≥90 = ↑). True trending requires time-series data from the API (`/api/v1/reporting/compliance/trend`)
- **MTTP target_days**: MTTP by-team trend arrows require `target_days` in the API response; currently the field may not be populated
- **Scanner connection status**: The Settings scanner cards show static "Not Connected" state — requires API call to `/settings/connections` to reflect real connection status

## UX Score: 7.5/10

*Pre-sprint: ~5.5/10. The core architecture is solid but first-run experience, empty states, and CTA hierarchy were underdeveloped. Sprint B addresses the most user-visible gaps across 6 pages.*
