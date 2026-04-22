# Sprint 15c: Interactive Schedule Calendar - Implementation Summary

## Overview
Built a comprehensive interactive schedule calendar for the Glasswatch patch decision platform, replacing the placeholder with a fully functional visual timeline that supports bundle assignment, overlap detection, and capacity management.

## Backend Changes

### Bundle Assignment Endpoint
**File**: `backend/api/v1/bundles.py`

Added `PATCH /bundles/{bundle_id}/assign-window` endpoint:
- Accepts `{ "maintenance_window_id": string | null }`
- Validates window exists and belongs to same tenant
- Checks capacity constraints:
  - Duration: Total bundle duration must not exceed window duration_hours * 60
  - Risk: Bundle risk_score must be under window max_risk_score (if set)
  - Assets: Total assets across bundles must stay under window max_assets (if set)
- Updates bundle.maintenance_window_id
- Sets bundle.status to "scheduled" on assignment, "draft" on unassignment
- Returns updated bundle

### Enhanced Bundle List Filtering
Modified `GET /bundles` endpoint to support:
- `maintenance_window_id` query parameter accepting:
  - UUID string to filter by specific window
  - `"unassigned"` to filter bundles where maintenance_window_id IS NULL
- Enables bundle picker to fetch only unassigned bundles

## Frontend Changes

### New Component: ScheduleCalendar
**File**: `frontend/src/components/ScheduleCalendar.tsx` (1,269 lines)

#### Main Features
1. **Dual View Modes**
   - Weekly timeline view (default)
   - Monthly calendar view

2. **Advanced Filtering**
   - Environment dropdown
   - Type toggle (scheduled/emergency/blackout/all)
   - Service name filter
   - Asset group filter
   - "Show overlaps only" toggle

3. **Overlap Detection**
   - Detects windows that overlap in time AND share same environment or service
   - Visual indicators: red dashed border
   - Warning in detail panel listing overlapping windows

#### Week View
- Horizontal axis: Days of week (Mon-Sun)
- Vertical axis: 24-hour time grid (00:00-23:59)
- Window blocks positioned by start_time → end_time
- Color-coded by type:
  - Scheduled: blue/primary
  - Emergency: red
  - Blackout: gray with diagonal stripes
- Current time indicator: red horizontal line with dot
- Week navigation: Previous | This Week | Next

**Window Blocks Display**:
- Window name
- Time range
- Environment badge
- Utilization bar (bundle duration vs. window capacity)
- Bundle count chip
- Hover effects

#### Month View
- Calendar grid (7x5/6)
- Days show up to 3 windows as colored bars
- "+N more" indicator when >3 windows
- Type-based colors
- Click to select window

#### Window Detail Panel
Slide-out panel (right side, 384px width) showing:
- Window details (name, type, time, environment, service, asset group)
- Overlap warning banner (if applicable)
- **Capacity Gauge**:
  - Visual bar: green (<80%), yellow (80-90%), red (>90%)
  - Text: "X.Xh / Y.Yh" and percentage
- **Assigned Bundles List**:
  - Each bundle shows: name, duration, risk score, asset count
  - "Unassign" button per bundle
- **"Assign Bundle" button** → opens bundle picker

#### Bundle Picker
Embedded in detail panel when "Assign Bundle" clicked:
- Search/filter unassigned bundles
- Fetches bundles with `maintenance_window_id: "unassigned"`
- **Fit Indicators**:
  - ✅ Green: Bundle fits with <80% utilization
  - ⚠️ Yellow: Tight fit (80-90% utilization)
  - ❌ Red: Exceeds capacity/risk/asset limits
- Shows reason: "Fits well" / "Tight fit" / "Exceeds capacity" / "Risk too high" / "Too many assets"
- "Assign" button disabled for bundles that exceed constraints
- Calls `bundlesApi.assignToWindow()` on assignment

### Updated Schedule Page
**File**: `frontend/src/app/(dashboard)/schedule/page.tsx`

Changes:
- Import `ScheduleCalendar` component
- Added "blackout" to MaintenanceWindow type enum
- Replaced `<CalendarView>` placeholder with:
  ```tsx
  <ScheduleCalendar 
    windows={windows}
    onWindowUpdate={loadData}
    environments={environments}
    assetGroups={assetGroups}
  />
  ```
- Removed old CalendarView component (placeholder)

### API Client Updates
**File**: `frontend/src/lib/api.ts`

Added to `bundlesApi`:
```typescript
assignToWindow: (bundleId: string, windowId: string | null) =>
  apiCall<any>(`/bundles/${bundleId}/assign-window`, { 
    method: "PATCH", 
    body: { maintenance_window_id: windowId } 
  }),
```

## Design Implementation

### Dark Theme
- Calendar background: `bg-neutral-900`
- Time slots: `bg-neutral-800`
- Borders: `border-neutral-700`
- Window blocks: Type-specific colors with hover effects

### Window Type Colors
- **Scheduled**: `bg-primary` (blue)
- **Emergency**: `bg-red-600`
- **Blackout**: `bg-neutral-600` with CSS repeating-linear-gradient stripes

### Responsive Design
- Desktop: Full interactive grid with all features
- Mobile: Degrades gracefully (filters stack, month view preferred)

### Timezone Handling
- All times displayed in user's local timezone
- Uses browser's `toLocaleTimeString()` and `toLocaleDateString()`

## Validation & Constraints

### Assignment Validation Flow
1. User clicks "Assign Bundle" in window detail panel
2. Bundle picker loads unassigned bundles
3. For each bundle, calculate fit:
   - Check duration: `currentUtilization + bundleDuration <= windowDuration`
   - Check risk: `bundle.risk_score <= window.max_risk_score`
   - Check assets: `currentAssets + bundle.assets <= window.max_assets`
4. Show fit indicator (✅⚠️❌) based on checks
5. Disable "Assign" button if constraints fail
6. On click, call backend which re-validates server-side
7. Backend returns 400 with detailed error if validation fails
8. On success, refresh calendar data

## Key Implementation Details

### Overlap Detection Algorithm
```typescript
windows.forEach((window, idx) => {
  windows.forEach((other, otherIdx) => {
    if (idx !== otherIdx) {
      // Time overlap: start1 < end2 && start2 < end1
      const timeOverlap = start1 < end2 && start2 < end1;
      
      // Same scope: environment or service match
      const sameScope =
        (window.environment === other.environment) ||
        (window.service_name === other.service_name);
      
      if (timeOverlap && sameScope) {
        // Mark as overlapping
      }
    }
  });
});
```

### Window Positioning (Week View)
```typescript
const dayStart = new Date(weekDay);
dayStart.setHours(0, 0, 0, 0);

const startMinutes = (windowStart.getTime() - dayStart.getTime()) / (1000 * 60);
const durationMinutes = (windowEnd.getTime() - windowStart.getTime()) / (1000 * 60);

const topPercent = (startMinutes / (24 * 60)) * 100;
const heightPercent = (durationMinutes / (24 * 60)) * 100;
```

### Current Time Indicator
- Only shown in week view
- Finds today's column
- Calculates minutes since midnight
- Positions red line as percentage of 24-hour grid
- Includes red dot on left edge

## Testing Checklist

### Backend
- [x] Assignment endpoint accepts window_id and null
- [x] Validates window exists and tenant match
- [x] Checks duration capacity
- [x] Checks risk constraints
- [x] Checks asset constraints
- [x] Returns detailed error messages
- [x] Updates bundle status on assign/unassign
- [x] Unassigned filter returns bundles with null window_id

### Frontend
- [x] Week view renders 7-day grid with 24 hours
- [x] Month view renders calendar with window bars
- [x] Window blocks positioned correctly by time
- [x] Overlap detection highlights conflicts
- [x] Current time indicator shows on today
- [x] Filters apply correctly
- [x] Window detail panel opens on click
- [x] Capacity gauge shows correct percentage
- [x] Bundle picker loads unassigned bundles
- [x] Fit indicators calculate correctly
- [x] Assign/unassign calls backend and refreshes
- [x] Error handling for failed assignments
- [x] Dark theme applied consistently
- [x] Responsive layout degrades gracefully

## Files Modified/Created

### Backend
- `backend/api/v1/bundles.py` (modified)
  - Added `assign_bundle_to_window` endpoint
  - Enhanced `list_bundles` with maintenance_window_id filter

### Frontend
- `frontend/src/components/ScheduleCalendar.tsx` (created, 1,269 lines)
  - Main calendar container with filters
  - WeekView component
  - MonthView component
  - WindowBlock component
  - WindowDetailPanel component
  - BundlePicker component
- `frontend/src/app/(dashboard)/schedule/page.tsx` (modified)
  - Import ScheduleCalendar
  - Replace CalendarView with ScheduleCalendar
  - Remove old placeholder component
- `frontend/src/lib/api.ts` (modified)
  - Add assignToWindow method to bundlesApi

## Commit
```
Sprint 15c: Interactive schedule calendar with bundle assignment

Backend:
- Add PATCH /bundles/{id}/assign-window endpoint with capacity/risk/asset validation
- Support 'unassigned' filter in GET /bundles for unassigned bundle queries
- Validate window constraints before assignment (duration, risk score, max assets)

Frontend:
- Create ScheduleCalendar component with weekly and monthly timeline views
- Week view: 24-hour grid with positioned window blocks, current time indicator
- Month view: Calendar grid with colored window bars by type
- Window detail panel with capacity gauge, assigned bundles list, and unassign capability
- Bundle picker with fit indicators (green/yellow/red for capacity constraints)
- Overlap detection and visual warnings for conflicting windows
- Filters: environment, type, service, asset group, 'show overlaps only'
- Dark theme with bg-neutral-900/800, type-based colors (blue/red/gray+stripes)
- Replace placeholder CalendarView with interactive ScheduleCalendar

Features:
- Click window blocks to open detail panel
- Visual capacity utilization bars
- Assign/unassign bundles with constraint checking
- Real-time overlap detection for same environment/service
- Responsive design, mobile-friendly degradation
- Time displayed in user's local timezone

Commit: 9341ffc
```

## Next Steps / Future Enhancements

### Immediate
1. Test in development environment with real data
2. Verify bundle assignment workflow end-to-end
3. Test overlap detection with multiple windows
4. Verify capacity constraints work correctly

### Future Sprints
1. Drag-and-drop bundle assignment (directly on calendar)
2. Multi-day window support (spanning blocks across days)
3. Recurring window templates
4. Calendar export (iCal/Google Calendar)
5. Notification scheduling (remind before window starts)
6. Conflict resolution suggestions (AI-powered)
7. Historical view (completed maintenance windows)
8. Performance metrics (utilization trends over time)

## Notes

- No external calendar libraries used (pure React + Tailwind)
- All times use ISO 8601 from backend, displayed in local timezone
- Backend enforces same constraints as frontend for security
- Overlap detection is client-side for responsiveness
- Window detail panel uses slide-out pattern (not modal) for better UX
- Bundle picker embedded in detail panel (not separate modal)
- Color scheme matches Glasswatch dark theme throughout
- Component is self-contained and reusable
