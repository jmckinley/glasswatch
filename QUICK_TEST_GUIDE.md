# Quick Test Guide - Ensuring Demo Works

## Before Every Important Demo

Run this command to verify everything works:

```bash
cd /home/node/glasswatch
npx playwright test --project=chromium demo-login
```

This will test the most critical flow (demo login) in under 2 minutes.

## Full Test Suite

To run all E2E tests:

```bash
cd /home/node/glasswatch
npx playwright install  # First time only
npx playwright test
```

## View Test Results

After tests run:

```bash
npx playwright show-report
```

## If Tests Fail

1. Look at the HTML report (opens automatically on failure)
2. Check screenshots in `test-results/`
3. Watch videos of failed tests
4. Fix the issues
5. Re-run tests

## Quick Fix Checklist

If demo is broken:

1. Check if production is running:
   - Frontend: https://frontend-production-ef3e.up.railway.app
   - Backend: https://glasswatch-production.up.railway.app/health

2. Check for API errors:
   ```bash
   curl -s https://glasswatch-production.up.railway.app/api/v1/auth/demo-login | jq
   ```

3. Check logs in Railway dashboard

4. Run tests to identify exact failure point

## Test Files

- `e2e/demo-login.spec.ts` - Demo login flow (CRITICAL)
- `e2e/registration.spec.ts` - Sign up and login
- `e2e/core-features.spec.ts` - All main feature pages
- `e2e/navigation.spec.ts` - App navigation

## Installation (One-Time Setup)

```bash
cd /home/node/glasswatch
npx playwright install chromium firefox webkit
```

This downloads the browsers Playwright needs for testing.

## Running Specific Tests

```bash
# Just demo login (fastest, most critical)
npx playwright test demo-login

# Just one browser
npx playwright test --project=chromium

# With UI for debugging
npx playwright test --ui

# With browser visible
npx playwright test --headed
```

## CI/CD Integration

Add to your GitHub Actions or deployment pipeline:

```yaml
- name: Install Playwright
  run: npx playwright install --with-deps chromium

- name: Run E2E Tests
  run: npx playwright test --project=chromium
  env:
    PLAYWRIGHT_BASE_URL: https://frontend-production-ef3e.up.railway.app

- name: Upload test results
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Emergency Demo Recovery

If tests are failing right before a demo:

1. Check what specific test is failing
2. If it's a minor UI issue, document it and present anyway
3. If it's a showstopper (demo login broken, API errors), DO NOT demo
4. Use the test report to quickly identify and fix the issue
5. Re-run tests before trying again

## Success Criteria

✅ All tests in `demo-login.spec.ts` passing = Demo is safe to show
✅ All E2E tests passing = Production is fully healthy
✅ No console errors during tests = Clean user experience
✅ No failed API calls = Backend is working correctly
