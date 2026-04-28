# Glasswatch E2E Test Plan

## Objective
Ensure the Glasswatch demo works perfectly every time, with no errors or failures when showing to prospects, investors, or partners.

## Critical User Flows

### 1. Demo Login Flow (HIGHEST PRIORITY)
**Why it's critical:** This is how we show Glasswatch to prospects. It MUST work.

**Test Coverage:**
- ✅ Login page loads without errors
- ✅ "Try Demo" button is visible and clickable
- ✅ Demo login redirects to dashboard/onboarding
- ✅ Demo account indicator is shown
- ✅ Dashboard loads data without API errors
- ✅ Navigation works after demo login
- ✅ Demo data is visible (not empty/broken)

**Test File:** `e2e/demo-login.spec.ts`

### 2. Registration & Email Login
**Why it's critical:** New users need to be able to sign up and log in.

**Test Coverage:**
- ✅ Registration form displays correctly
- ✅ New account registration works end-to-end
- ✅ Validation errors show for invalid input
- ✅ Email login form works
- ✅ Invalid credentials show error message

**Test File:** `e2e/registration.spec.ts`

### 3. Core Feature Pages
**Why it's critical:** These are the main product features. They must load and work.

**Test Coverage:**
- ✅ Vulnerabilities page loads and displays data
- ✅ Assets page loads and displays data
- ✅ Goals page loads and displays data
- ✅ Bundles page loads and displays data
- ✅ Audit Log page loads and displays events
- ✅ Settings page loads
- ✅ No API errors on any page

**Test File:** `e2e/core-features.spec.ts`

### 4. Navigation
**Why it's critical:** Users need to move through the app smoothly.

**Test Coverage:**
- ✅ All main pages accessible without errors
- ✅ Authentication persists across navigation
- ✅ Active navigation state shows correctly
- ✅ Browser back/forward works
- ✅ Direct URL navigation works

**Test File:** `e2e/navigation.spec.ts`

## Test Execution

### Running Tests

```bash
# Install dependencies
npm install -D @playwright/test

# Install browsers
npx playwright install

# Run all E2E tests
npm run test:e2e

# Run tests in headed mode (see browser)
npm run test:e2e:headed

# Run tests in UI mode (interactive debugging)
npm run test:e2e:ui

# Run only demo login tests (most critical)
npx playwright test demo-login

# Run tests against production
PLAYWRIGHT_BASE_URL=https://frontend-production-ef3e.up.railway.app npm run test:e2e
```

### Test Environments

1. **Production** (default): `https://frontend-production-ef3e.up.railway.app`
2. **Local Dev**: `http://localhost:3000`

Configure via `PLAYWRIGHT_BASE_URL` environment variable.

### Browser Coverage

Tests run against:
- ✅ Chrome (Desktop)
- ✅ Firefox (Desktop)
- ✅ Safari/WebKit (Desktop)
- ✅ Chrome (Mobile)
- ✅ Safari (Mobile)

## Success Criteria

For the demo to be "production-ready":

1. **100% pass rate** on demo login tests
2. **100% pass rate** on core features tests
3. **No console errors** during normal flows
4. **No API errors (4xx/5xx)** during normal flows
5. **All tests pass** on Chrome, Firefox, and Safari

## Debugging Failed Tests

When tests fail:

1. Check the test report: `playwright-report/index.html`
2. Review screenshots in `test-results/`
3. Watch videos of failed tests in `test-results/`
4. Run in headed mode to see what's happening: `npm run test:e2e:headed`
5. Run in UI mode for interactive debugging: `npm run test:e2e:ui`

## Continuous Integration

Tests should run:
- ✅ On every pull request
- ✅ Before every deployment to production
- ✅ On a nightly schedule

## Known Limitations

- OAuth flows (Google/GitHub) are not yet configured in production, so those buttons should be hidden
- Some pages may have empty states if demo data is not seeded

## Test Maintenance

- **Review and update tests** whenever UX changes
- **Add new tests** for new features before they go to production
- **Run tests locally** before every demo or important meeting
- **Check test reports** after every deployment

## Emergency Pre-Demo Checklist

Before showing Glasswatch to anyone important:

1. ✅ Run `npm run test:e2e` and confirm 100% pass rate
2. ✅ Manually test demo login flow
3. ✅ Check production is running: https://frontend-production-ef3e.up.railway.app
4. ✅ Verify backend is healthy: https://glasswatch-production.up.railway.app/health
5. ✅ Clear browser cache and test as a fresh user
6. ✅ Test on the actual device/browser you'll use for the demo

## Reporting Issues

If tests fail or the demo breaks:

1. Capture screenshots/videos from Playwright
2. Note any console errors
3. Check API responses in test output
4. Document steps to reproduce
5. File issue with all details above
