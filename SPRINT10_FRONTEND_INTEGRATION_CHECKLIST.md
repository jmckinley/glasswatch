# Sprint 10 Frontend - Integration Checklist

This checklist helps validate that the Sprint 10 frontend works correctly with the backend.

## Backend API Requirements

### Auth Endpoints

- [ ] **POST /api/v1/auth/login**
  - Accepts: `{ provider: "sso", redirect_uri: string }`
  - Returns: `{ authorization_url: string }`
  - Frontend redirects user to `authorization_url`

- [ ] **GET /api/v1/auth/demo-login**
  - No parameters
  - Returns: `{ access_token: string }`
  - Frontend stores token and calls `/auth/me`

- [ ] **GET /api/v1/auth/me**
  - Requires: `Authorization: Bearer {token}` header
  - Returns: `{ id, email, full_name, role, tenant_id }`
  - Returns 401 if token invalid/expired

- [ ] **401 Responses** trigger auto-logout in frontend

### Approvals Endpoints

- [ ] **GET /api/v1/approvals**
  - Query params: `status` (optional: "pending" | "approved" | "rejected")
  - Returns: `{ items: Approval[] }` or `Approval[]`
  - Approval shape: `{ id, title, description, risk_level, requester: { id, full_name }, required_approvals, current_approvals, status, created_at, bundle_id? }`

- [ ] **POST /api/v1/approvals**
  - Accepts: `{ bundle_id: string, title: string, description?: string }`
  - Returns: Created approval object
  - Creates approval request with risk assessment

- [ ] **POST /api/v1/approvals/{id}/approve**
  - Accepts: `{ comment?: string }`
  - Returns: Updated approval
  - Increments approval count

- [ ] **POST /api/v1/approvals/{id}/reject**
  - Accepts: `{ comment?: string }`
  - Returns: Updated approval
  - Sets status to rejected

### Bundles Endpoints

- [ ] **GET /api/v1/bundles**
  - Query params: `status` (e.g., "draft")
  - Returns: `{ items: Bundle[] }`
  - Bundle shape: `{ id, name, patch_count, risk_score }`

- [ ] **GET /api/v1/bundles/{id}/risk-assessment**
  - Returns: `{ level: "low"|"medium"|"high"|"critical", score: number, factors: string[], impact_summary: string }`
  - Used when creating approval requests

### Comments Endpoints

- [ ] **GET /api/v1/comments**
  - Query params: `entity_type` (required), `entity_id` (required)
  - Returns: `{ items: Comment[] }` or `Comment[]`
  - Comment shape: `{ id, content, author: { id, full_name, email }, created_at, updated_at, parent_id, reactions: [{ emoji, user_ids, count }] }`

- [ ] **POST /api/v1/comments**
  - Accepts: `{ entity_type: string, entity_id: string, content: string, parent_id?: string }`
  - Returns: Created comment
  - Creates top-level comment or reply

- [ ] **PATCH /api/v1/comments/{id}**
  - Accepts: `{ content: string }`
  - Returns: Updated comment
  - Only author can edit

- [ ] **DELETE /api/v1/comments/{id}**
  - No body
  - Returns: 204 or success response
  - Only author can delete

- [ ] **POST /api/v1/comments/{id}/reactions**
  - Accepts: `{ emoji: string }`
  - Returns: Updated comment with reactions
  - Toggle reaction (add if not present, remove if present)

### Activities Endpoints

- [ ] **GET /api/v1/activities**
  - Query params: `limit` (optional, default 50)
  - Returns: `{ items: Activity[] }` or `Activity[]`
  - Activity shape: `{ id, type, title, description, actor: { id, full_name }, created_at, is_read, entity_type?, entity_id? }`
  - Types: approval_request, approval_approved, approval_rejected, comment_added, bundle_created, bundle_deployed, goal_created, goal_completed, vulnerability_discovered

- [ ] **GET /api/v1/activities/unread-count**
  - Returns: `{ count: number }`
  - Used for notification badge

- [ ] **POST /api/v1/activities/{id}/read**
  - No body
  - Returns: Success response
  - Marks single activity as read

- [ ] **POST /api/v1/activities/read-all**
  - No body
  - Returns: Success response
  - Marks all activities for current user as read

### Users Endpoints

- [ ] **GET /api/v1/users/search**
  - Query params: `q` (search query)
  - Returns: `{ items: User[] }` or `User[]`
  - User shape: `{ id, full_name, email }`
  - Used for @mention autocomplete

## Frontend Testing Checklist

### Authentication Flow

- [ ] Visit `/auth/login`
- [ ] Click "Demo Login" button
  - [ ] Loading state appears
  - [ ] JWT token stored in localStorage
  - [ ] Redirected to `/`
  - [ ] User profile loaded (name appears in header)
- [ ] Refresh page
  - [ ] Still authenticated (token persists)
  - [ ] User profile reloaded
- [ ] Click user avatar in header
  - [ ] Dropdown shows user name and email
  - [ ] "Sign out" button visible
- [ ] Click "Sign out"
  - [ ] Token removed from localStorage
  - [ ] Redirected to `/auth/login`
- [ ] Try to visit `/dashboard/approvals` without logging in
  - [ ] Automatically redirected to `/auth/login`

### Approvals Workflow

- [ ] Navigate to `/dashboard/approvals`
- [ ] See tab navigation (Pending | Approved | Rejected | All)
- [ ] Click each tab
  - [ ] URL updates with status filter
  - [ ] Correct approvals load
- [ ] For each approval card:
  - [ ] Risk badge shows correct color
  - [ ] Title and description visible
  - [ ] Requester name shown
  - [ ] Timestamp shown ("Xh ago")
  - [ ] Approval progress shown (X / Y approvals)
- [ ] Click "Approve" button
  - [ ] Comment modal opens
  - [ ] Can add optional comment
  - [ ] Click "Approve" → API called
  - [ ] Modal closes, list refreshes
- [ ] Click "Reject" button
  - [ ] Comment modal opens
  - [ ] Can add optional comment
  - [ ] Click "Reject" → API called
  - [ ] Modal closes, list refreshes

### Creating Approval Request

- [ ] Open ApprovalRequestModal (trigger TBD - maybe add "New Request" button)
- [ ] Bundle dropdown loads
  - [ ] Shows bundles with patch count and risk score
- [ ] Select a bundle
  - [ ] Risk assessment loads automatically
  - [ ] Risk level badge appears
  - [ ] Impact summary shown
  - [ ] Risk factors listed
- [ ] Enter title
- [ ] Enter description (optional)
- [ ] Click "Create Request"
  - [ ] API called
  - [ ] Modal closes
  - [ ] Approval appears in inbox

### Comments

- [ ] Navigate to a page with CommentThread component
- [ ] See existing comments in threaded view
- [ ] Type a comment in the text box
- [ ] Click "Post Comment"
  - [ ] Comment appears immediately
  - [ ] Author name and avatar shown
  - [ ] Timestamp shown
- [ ] Click "Reply" on a comment
  - [ ] Reply indicator appears
  - [ ] Post reply → appears nested under parent
- [ ] Type `@` in comment box
  - [ ] Autocomplete dropdown appears
  - [ ] Type name → filters users
  - [ ] Click user → inserts "@Full Name "
- [ ] Click "+ " on a comment
  - [ ] Can add emoji reaction
- [ ] Click existing reaction
  - [ ] Toggles reaction (add/remove)
- [ ] Click "Edit" on own comment
  - [ ] Textarea appears with current text
  - [ ] Edit text
  - [ ] Click "Save" → comment updates
- [ ] Click "Delete" on own comment
  - [ ] Confirmation prompt
  - [ ] Confirm → comment removed

### Activity Feed

- [ ] Navigate to `/dashboard/activities`
- [ ] See list of activities
- [ ] Each activity shows:
  - [ ] Correct icon for type
  - [ ] Correct color for type
  - [ ] Title and description
  - [ ] Actor name
  - [ ] Timestamp
  - [ ] Unread indicator (blue dot) if unread
- [ ] Click an unread activity
  - [ ] Blue dot disappears (marked as read)
  - [ ] Unread count decreases
- [ ] Click "Mark all as read"
  - [ ] All blue dots disappear
  - [ ] Unread count goes to 0

### Notification Bell

- [ ] Look at top-right header
- [ ] NotificationBell icon visible
- [ ] If unread activities exist:
  - [ ] Red badge shows count
  - [ ] Count accurate (or "9+" if > 9)
- [ ] Click bell icon
  - [ ] Dropdown opens
  - [ ] Shows recent 10 activities
  - [ ] Unread activities highlighted
  - [ ] "Mark all read" button visible
- [ ] Click an activity in dropdown
  - [ ] Marked as read
  - [ ] Badge count decreases
- [ ] Click "Mark all read"
  - [ ] All activities marked read
  - [ ] Badge disappears
- [ ] Click "View all activity →"
  - [ ] Navigates to `/dashboard/activities`
  - [ ] Dropdown closes
- [ ] Click outside dropdown
  - [ ] Dropdown closes
- [ ] Wait 30+ seconds
  - [ ] Unread count refreshes automatically

### Dashboard Layout

- [ ] On any protected page
- [ ] Header visible at top
  - [ ] "Glasswatch" branding
  - [ ] Navigation links (Dashboard, Approvals, Vulnerabilities, Goals)
  - [ ] NotificationBell
  - [ ] User avatar/menu
- [ ] Click navigation links
  - [ ] Navigate correctly
  - [ ] Active link highlighted
- [ ] Scroll down page
  - [ ] Header sticks to top (sticky)
- [ ] Resize window (mobile)
  - [ ] Layout responsive
  - [ ] Navigation may collapse (depends on implementation)

### Dark Theme

- [ ] All pages use dark theme
- [ ] Backgrounds: gray-900
- [ ] Cards: gray-800
- [ ] Borders: gray-700
- [ ] Text readable (white/gray-300/gray-400)
- [ ] Hover states visible
- [ ] Focus states visible (blue ring)
- [ ] Risk colors distinct and readable

### Error Handling

- [ ] Try to access protected route while logged out
  - [ ] Redirect to login
- [ ] Login with invalid token
  - [ ] Error message shown
- [ ] API returns 401
  - [ ] Auto-logout triggered
  - [ ] Redirect to login
- [ ] API returns 500
  - [ ] Error message shown
  - [ ] Does not crash app
- [ ] Submit form with missing required field
  - [ ] Form validation error shown
  - [ ] Submit button disabled

## Environment Variables

- [ ] **NEXT_PUBLIC_API_URL** set correctly
  - Default: `http://localhost:8000`
  - Production: Set to actual backend URL

## Browser Compatibility

- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Mobile Chrome (Android)

## Performance

- [ ] Activity polling does not cause lag (30s interval is reasonable)
- [ ] Large comment threads render smoothly
- [ ] Long activity feeds scroll smoothly
- [ ] Page loads under 2 seconds (with backend response time)

## Accessibility (Future)

- [ ] Add ARIA labels to icon buttons
- [ ] Add keyboard navigation support
- [ ] Add focus management for modals
- [ ] Add screen reader announcements for dynamic content

---

## Known Issues / Pre-existing Errors

These errors existed before Sprint 10 work and do not affect new components:

- MUI dependencies missing (affects Discovery page, not Sprint 10)
- Axios imports in old services (Sprint 10 uses fetch)
- Some TypeScript strict mode warnings in existing files

## Integration Notes

1. **JWT Token Format:** Frontend expects a JWT string from backend, stores in localStorage as `glasswatch_token`
2. **Authorization Header:** All authenticated requests include `Authorization: Bearer {token}`
3. **Tenant ID:** Auth context expects `tenant_id` in user profile response (for multi-tenant support)
4. **Entity Types:** Comments use generic `entity_type` + `entity_id` (e.g., "approval", "123")
5. **Activity Types:** Must match the 9 types defined in ActivityFeed component
6. **Risk Levels:** Must be one of: "low", "medium", "high", "critical" (lowercase)

## Next Steps After Integration

1. Manual testing with real backend
2. Fix any API response format mismatches
3. Add error recovery (retry logic, offline handling)
4. Add loading skeletons (instead of spinners)
5. Add pagination for long lists
6. Add search/filter for approvals and activities
7. Add WebSocket support for real-time updates
8. Add notification preferences
9. Add keyboard shortcuts

---

**Ready for backend integration!** 🚀
