# Sprint 15a: Maintenance Window Management UI - Verification Checklist

## Task Completion

### ✅ Task 1: Add CRUD to maintenanceWindowsApi
- [x] `create` method added to `maintenanceWindowsApi`
- [x] `update` method added to `maintenanceWindowsApi`
- [x] `delete` method added to `maintenanceWindowsApi`
- [x] Methods use correct HTTP verbs (POST/PATCH/DELETE)
- [x] Methods call correct endpoints

**File**: `frontend/src/lib/api.ts` (lines 333-337)

### ✅ Task 2: Verify Backend CRUD Endpoints
- [x] POST `/api/v1/maintenance-windows` exists
- [x] PATCH `/api/v1/maintenance-windows/{id}` exists
- [x] DELETE `/api/v1/maintenance-windows/{id}` exists
- [x] Endpoints follow existing patterns (rules/bundles)
- [x] Soft delete for scheduled windows implemented

**File**: `backend/api/v1/maintenance_windows.py`

### ✅ Task 3: Create/Edit Maintenance Window Dialog

#### Dialog Component Structure
- [x] Component created at `frontend/src/components/MaintenanceWindowDialog.tsx`
- [x] 617 lines of comprehensive form UI
- [x] Accepts `isOpen`, `onClose`, `onSave`, `windowData` props
- [x] Properly handles both create and edit modes

#### Basic Info Section
- [x] Name input (required)
- [x] Description textarea (optional)
- [x] Type selector (scheduled/emergency/blackout)
- [x] Type buttons have color coding:
  - Scheduled: blue (`bg-blue-500/20 border-blue-500 text-blue-300`)
  - Emergency: red (`bg-red-500/20 border-red-500 text-red-300`)
  - Blackout: gray (`bg-gray-600/20 border-gray-500 text-gray-300`)

#### Time Window Section
- [x] Start date picker
- [x] Start time picker
- [x] End date picker
- [x] End time picker
- [x] Timezone selector (10 common IANA timezones)
- [x] Calculated duration display (auto-updates)
- [x] Duration calculation function (`calculateDuration()`)

#### Scope Section (Key Feature)
- [x] Environment input
- [x] Asset Group input
- [x] Service Name input
- [x] Is Default toggle
- [x] Priority slider (1-10)
- [x] Priority explanation text
- [x] Scope preview feature (`getScopePreview()`)
- [x] Dynamic scope preview display
- [x] Scope fields disabled when "Is Default" checked
- [x] Visual preview shows:
  - Environment / Asset Group / Service OR
  - "This is the **default** fallback window"

#### Constraints Section
- [x] Max assets (number input)
- [x] Max risk score (number input)
- [x] Max duration hours (number input, auto-filled)
- [x] Approved activities multi-select
- [x] Six activity options:
  - Patching
  - Updates
  - Restarts
  - Migrations
  - Deployments
  - Config Changes
- [x] Activities toggle on/off with visual state

#### Status Section
- [x] Change freeze toggle
- [x] Change freeze reason textarea (conditional)
- [x] Active toggle

#### Visual Design Requirements
- [x] Dark theme (bg-gray-800, border-gray-600/700)
- [x] Sections separated with borders
- [x] Section headers (text-lg font-semibold)
- [x] Sticky header and footer
- [x] Max height with scroll (max-h-[90vh] overflow-y-auto)
- [x] Loading states (disabled buttons, spinner)
- [x] Error handling (error banner at top)
- [x] Validation messages

#### Form Behavior
- [x] Pre-fills when editing existing window
- [x] Resets form when opening for new window
- [x] Validates required fields
- [x] Validates time ranges (end > start)
- [x] Validates at least one approved activity
- [x] Calls `maintenanceWindowsApi.create()` for new
- [x] Calls `maintenanceWindowsApi.update()` for edit
- [x] Closes and refreshes on success
- [x] Shows error on failure

### ✅ Task 4: Add "New Window" Button
- [x] Button added to schedule page header
- [x] Positioned next to "Analyze Schedule" button
- [x] Green success color (`bg-success`)
- [x] "+ New Window" text
- [x] Opens dialog in create mode (`handleNewWindow()`)
- [x] Clears `editingWindow` state

**File**: `frontend/src/app/(dashboard)/schedule/page.tsx` (line ~300)

### ✅ Task 5: Add Edit/Delete to WindowCard
- [x] Edit button added (✏️ Edit)
- [x] Delete button added (🗑️ Delete)
- [x] Buttons only show for non-past windows (`!isPast` check)
- [x] Edit button opens dialog pre-filled (`handleEditWindow()`)
- [x] Delete button shows confirmation modal
- [x] Delete confirmation dialog implemented
- [x] Confirmation has Cancel and Delete buttons
- [x] Delete calls `maintenanceWindowsApi.delete()`
- [x] Refreshes data after delete
- [x] Button styling:
  - Edit: blue (`bg-blue-500/20 text-blue-300`)
  - Delete: red (`bg-red-500/20 text-red-300`)
  - Both have hover states

**File**: `frontend/src/app/(dashboard)/schedule/page.tsx` (WindowCard component)

### ✅ Task 6: Visual Scope Grouping

#### Three-Tier Organization
- [x] Default windows section (separate, at top)
- [x] Blackout windows section (separate, red treatment)
- [x] Regular windows section (grouped by environment)

#### Default Windows
- [x] Section header: "Default Fallback Windows"
- [x] Explanatory text: "(apply when no specific match exists)"
- [x] Filters: `upcomingWindows.filter(w => w.is_default)`

#### Blackout Windows
- [x] Section header with warning icon (⚠️)
- [x] Red text: "Blackout Windows"
- [x] Explanatory text: "(no changes allowed)"
- [x] Red border wrapper: `border-2 border-red-500/50`
- [x] Filters: `upcomingWindows.filter(w => w.type === "blackout")`

#### Regular Windows
- [x] Grouped by environment
- [x] Group function: `reduce((acc, window) => ...)`
- [x] Environment headers (text-primary, capitalized)
- [x] Sorted environment keys
- [x] Filters: `filter(w => !w.is_default && w.type !== "blackout")`

#### Window Card Enhancements
- [x] Environment badge displayed
- [x] Service name badge (text-primary)
- [x] Asset group badge (text-secondary)
- [x] Priority badge for priority > 0
- [x] "DEFAULT" badge for is_default
- [x] Type badge (SCHEDULED/EMERGENCY/BLACKOUT)

**File**: `frontend/src/app/(dashboard)/schedule/page.tsx` (ListView component)

## Code Quality Checks

### Constraints Met
- [x] No new CSS added (only Tailwind classes)
- [x] Dark theme consistency (bg-gray-800, bg-neutral-800, etc.)
- [x] Follows existing code patterns
- [x] No push to git (commits only)
- [x] Descriptive commit messages

### Integration Points
- [x] Dialog import added to schedule page
- [x] Dialog state managed in schedule page
- [x] Event handlers properly connected
- [x] WindowCard receives onEdit/onDelete props
- [x] ListView receives and passes onEdit/onDelete

### Error Handling
- [x] API errors caught and displayed
- [x] Form validation before submit
- [x] Delete confirmation prevents accidents
- [x] Loading states prevent double-submit

## Git Commits

1. **Main implementation commit** (a16f4bc):
   - Added CRUD methods to API client
   - Created MaintenanceWindowDialog component
   - Integrated dialog into schedule page
   - Added edit/delete buttons
   - Implemented visual scope grouping

2. **Documentation commit** (a8470fd):
   - Added Sprint 15a summary document

## Files Modified/Created

### Modified (3 files)
1. `frontend/src/lib/api.ts` (+6 lines)
2. `frontend/src/app/(dashboard)/schedule/page.tsx` (+201 lines, ~951 total)

### Created (2 files)
1. `frontend/src/components/MaintenanceWindowDialog.tsx` (617 lines)
2. `SPRINT_15A_SUMMARY.md` (documentation)

## Testing Readiness

### Manual Testing Checklist
- [ ] Open schedule page — verify "New Window" button appears
- [ ] Click "New Window" — verify dialog opens
- [ ] Fill form and submit — verify window created
- [ ] Verify window appears in correct group (environment/default/blackout)
- [ ] Click "Edit" on a window — verify dialog pre-fills
- [ ] Modify window and save — verify changes applied
- [ ] Click "Delete" on a window — verify confirmation appears
- [ ] Confirm delete — verify window removed
- [ ] Verify past windows don't show edit/delete buttons
- [ ] Verify scope preview updates as fields change
- [ ] Verify priority slider shows current value
- [ ] Verify approved activities multi-select works
- [ ] Verify change freeze reason appears when toggle on
- [ ] Verify form validation (required fields, time range)
- [ ] Verify environment grouping displays correctly
- [ ] Verify default/blackout sections appear when relevant

### Backend Integration
- [ ] POST creates window with all fields
- [ ] PATCH updates only changed fields
- [ ] DELETE soft-deletes or hard-deletes as appropriate
- [ ] Validation errors return properly
- [ ] Timezone handling works correctly

## Success Criteria

All tasks completed ✅:
1. ✅ CRUD methods added to frontend API
2. ✅ Backend endpoints verified
3. ✅ Comprehensive dialog created with all scoping features
4. ✅ "New Window" button added
5. ✅ Edit/delete added to WindowCard
6. ✅ Visual scope grouping implemented

Code quality maintained ✅:
- Dark theme consistency
- No new CSS
- Existing patterns followed
- Proper error handling
- Loading states
- Validation

Ready for manual testing and deployment to Railway ✅
