# Sprint 15a: Maintenance Window Management UI - Implementation Summary

## Completed Tasks

### ✅ Task 1: Add CRUD to maintenanceWindowsApi
**File**: `frontend/src/lib/api.ts`

Added three methods to `maintenanceWindowsApi`:
```typescript
create: (window: any) => apiCall<any>("/maintenance-windows", { method: "POST", body: window }),
update: (id: string, updates: any) => apiCall<any>(`/maintenance-windows/${id}`, { method: "PATCH", body: updates }),
delete: (id: string) => apiCall<any>(`/maintenance-windows/${id}`, { method: "DELETE" }),
```

### ✅ Task 2: Verify Backend CRUD Endpoints
**File**: `backend/api/v1/maintenance_windows.py`

Verified all required endpoints exist:
- ✅ `POST /api/v1/maintenance-windows` — create window
- ✅ `PATCH /api/v1/maintenance-windows/{id}` — update window  
- ✅ `DELETE /api/v1/maintenance-windows/{id}` — delete window (soft delete for scheduled windows)

All endpoints follow existing patterns and include proper validation.

### ✅ Task 3: Create/Edit Maintenance Window Dialog
**File**: `frontend/src/components/MaintenanceWindowDialog.tsx` (new, 24KB)

**Comprehensive dialog component with all required sections:**

#### Basic Info Section
- Name (required)
- Description (optional)
- Type selector (scheduled/emergency/blackout) with color-coded buttons
  - Scheduled: blue
  - Emergency: red
  - Blackout: gray

#### Time Window Section
- Start date/time pickers
- End date/time pickers
- Timezone selector (10 common IANA timezones)
- **Calculated duration display** (auto-updates)

#### Scope Section (Key Differentiator)
- Environment input (e.g., production, staging)
- Asset Group input (e.g., web-servers, databases)
- Service Name input (e.g., api-gateway, payment-service)
- **Is Default toggle** — marks window as fallback
- **Priority slider** (1-10) with explanation text
- **Visual scope preview** that dynamically shows:
  - "This window applies to: **production** / **web-servers** / **api-gateway**"
  - Or: "This is the **default** fallback window"

#### Constraints Section
- Max assets (number input, optional)
- Max risk score (number input, optional)
- Max duration hours (auto-calculated from time window, overridable)
- **Approved activities** (multi-select):
  - Patching
  - Updates
  - Restarts
  - Migrations
  - Deployments
  - Config Changes

#### Status Section
- **Change freeze toggle** with conditional reason text area
- **Active toggle** to enable/disable window

#### Visual Design
- Dark theme (bg-gray-800, border-gray-600/700)
- Sections separated with borders and headers
- Sticky header and footer for long forms
- Responsive layout with grid columns
- Loading states and error handling
- Clear validation messages

### ✅ Task 4: Add "New Window" Button
**File**: `frontend/src/app/(dashboard)/schedule/page.tsx`

Added "+ New Window" button next to "Analyze Schedule" button:
- Green success color (`bg-success`)
- Opens dialog in create mode
- Properly positioned in header alongside filters

### ✅ Task 5: Add Edit/Delete to WindowCard
**File**: `frontend/src/app/(dashboard)/schedule/page.tsx`

Enhanced `WindowCard` component:
- **Edit button** (✏️ Edit) — blue, opens dialog pre-filled with window data
- **Delete button** (🗑️ Delete) — red, shows confirmation modal
- Buttons only appear for **non-past windows**
- Delete confirmation dialog prevents accidental deletion
- Both buttons have hover states and proper styling

### ✅ Task 6: Visual Scope Grouping
**File**: `frontend/src/app/(dashboard)/schedule/page.tsx`

Implemented intelligent visual grouping in `ListView`:

#### Three-Tier Organization:
1. **Default Fallback Windows** (separate section at top)
   - Clear label: "(apply when no specific match exists)"
   - Distinct visual treatment

2. **Blackout Windows** (highlighted section)
   - Red warning icon (⚠️)
   - Red border (`border-red-500/50`)
   - Label: "(no changes allowed)"

3. **Regular Windows** (grouped by environment)
   - Production
   - Staging  
   - Development
   - Each environment group shows:
     - Environment name as header (text-primary, capitalized)
     - All windows for that environment
     - Service name and asset group in badges

#### Visual Enhancements:
- Environment badges (shown in window header)
- Service name badges (text-primary)
- Asset group badges (text-secondary)
- Priority badges for high-priority windows
- Type badges with color coding (emergency=red, scheduled=blue)

## Technical Implementation Details

### State Management
- `dialogOpen` — controls dialog visibility
- `editingWindow` — stores window being edited (null for new)
- `deleteConfirm` — tracks window ID pending deletion

### Event Handlers
- `handleNewWindow()` — opens dialog in create mode
- `handleEditWindow(window)` — opens dialog with pre-filled data
- `handleDeleteWindow(windowId)` — executes deletion after confirmation
- `handleDialogSave()` — refreshes data after save

### Data Flow
1. User clicks "New Window" → Dialog opens (empty)
2. User fills form → Validates → Calls `maintenanceWindowsApi.create()`
3. Success → Closes dialog → Refreshes window list
4. Edit: Pre-fills form → User modifies → Calls `maintenanceWindowsApi.update()`
5. Delete: Shows confirmation → User confirms → Calls `maintenanceWindowsApi.delete()`

### Validation
- Name required
- Start/end times required and validated (end > start)
- At least one approved activity required
- Duration auto-calculated and validated
- Scope fields disabled when "Is Default" is checked

## Design Patterns Followed

✅ **Dark theme consistency** — bg-gray-800, bg-neutral-800, border-gray-600/700
✅ **Existing Tailwind classes** — no new CSS added
✅ **Component composition** — Dialog is separate reusable component
✅ **Controlled components** — All form inputs use React state
✅ **Loading states** — Disabled buttons and spinners during async operations
✅ **Error handling** — User-friendly error messages
✅ **Accessibility** — Labels, titles, semantic HTML

## Files Modified

1. `frontend/src/lib/api.ts` — Added CRUD methods
2. `frontend/src/app/(dashboard)/schedule/page.tsx` — Integrated dialog, added buttons, implemented grouping
3. `frontend/src/components/MaintenanceWindowDialog.tsx` — New comprehensive dialog component

## Git Commit

```
commit a16f4bc
Sprint 15a: Add maintenance window CRUD UI with comprehensive dialog
```

## What's Ready

✅ Users can create new maintenance windows with full scoping power
✅ Users can edit existing windows (non-past only)
✅ Users can delete windows (with confirmation, scheduled bundles check)
✅ Visual grouping makes it easy to understand scope hierarchy
✅ Scope preview helps users understand what each window covers
✅ Priority slider clarifies precedence rules
✅ All constraints and status flags are exposed
✅ Dark theme matches existing design language
✅ Form validation prevents invalid data
✅ Backend endpoints verified and working

## Next Steps (Future Enhancements)

- [ ] Autocomplete for environment/asset group/service name (could fetch from existing data)
- [ ] Calendar view implementation (currently shows placeholder)
- [ ] Drag-and-drop to reschedule windows
- [ ] Bulk operations (enable/disable multiple windows)
- [ ] Window templates for common patterns
- [ ] Conflict detection UI (visual overlap warnings)
- [ ] Window utilization charts
