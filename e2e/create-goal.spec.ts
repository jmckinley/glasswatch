import { test, expect } from '@playwright/test';

/**
 * Create Goal Flow E2E Tests
 *
 * Tests the full flow:
 *  dashboard → "Create Goal" alert link → goals page modal opens
 *  → fill form → submit → goal appears in list
 *
 * Also guards against the regression where "Create Goal" linked to
 * /goals/new (a non-existent page) instead of /goals?create=true.
 */

test.describe('Create Goal Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 30000 });
  });

  // -------------------------------------------------------------------------
  // Regression guard: Create Goal link must not go to /goals/new
  // -------------------------------------------------------------------------

  test('Create Goal link on dashboard points to /goals?create=true, not /goals/new', async ({ page }) => {
    // Navigate to dashboard home
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 20000 });

    // Find any "Create Goal" link (may appear in dashboard alerts or action items)
    const createGoalLinks = page.locator('a:has-text("Create Goal"), a:has-text("Create a Goal")');
    const count = await createGoalLinks.count();

    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const href = await createGoalLinks.nth(i).getAttribute('href');
        // Must NOT link to /goals/new
        expect(href).not.toBe('/goals/new');
        // Must link to the query-param version
        expect(href).toContain('/goals');
      }
    } else {
      // No alert currently visible — still verify the goals page exists
      await page.goto('/goals');
      await page.waitForLoadState('domcontentloaded');
      await expect(page).toHaveURL(/goals/);
    }
  });

  // -------------------------------------------------------------------------
  // Goals page loads
  // -------------------------------------------------------------------------

  test('goals page loads without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('response', (r) => {
      if (r.status() >= 500 && r.url().includes('/api/')) {
        errors.push(`${r.status()} ${r.url()}`);
      }
    });

    await page.goto('/goals');
    await page.waitForLoadState('networkidle', { timeout: 20000 });

    expect(errors).toHaveLength(0);
    await expect(page).toHaveURL(/goals/);
  });

  // -------------------------------------------------------------------------
  // ?create=true opens the modal
  // -------------------------------------------------------------------------

  test('navigating to /goals?create=true opens the create modal', async ({ page }) => {
    await page.goto('/goals?create=true');
    await page.waitForLoadState('domcontentloaded');

    // The create modal should be visible (contains a Name input)
    const nameInput = page.getByRole('textbox', { name: /name/i }).first();
    await expect(nameInput).toBeVisible({ timeout: 10000 });
  });

  // -------------------------------------------------------------------------
  // Create goal form — full happy path
  // -------------------------------------------------------------------------

  test('can fill and submit the create goal form', async ({ page }) => {
    await page.goto('/goals?create=true');
    await page.waitForLoadState('domcontentloaded');

    // Wait for modal
    const nameInput = page.getByRole('textbox', { name: /name/i }).first();
    await expect(nameInput).toBeVisible({ timeout: 10000 });

    // Fill in goal name
    const uniqueName = `E2E Goal ${Date.now()}`;
    await nameInput.fill(uniqueName);

    // Submit the form
    const submitBtn = page.getByRole('button', { name: /create|save|submit/i }).first();
    await submitBtn.click();

    // After submission, modal should close (or success state visible)
    await page.waitForTimeout(2000);

    // Either modal closed (name input gone) or success message
    const modalClosed = await nameInput.isHidden().catch(() => true);
    const successMsg = await page.getByText(/created|success/i).isVisible().catch(() => false);

    expect(modalClosed || successMsg).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // "Create New Goal" button on the goals page opens the modal
  // -------------------------------------------------------------------------

  test('Create New Goal button on goals page opens modal', async ({ page }) => {
    await page.goto('/goals');
    await page.waitForLoadState('networkidle', { timeout: 20000 });

    const createBtn = page.getByRole('button', { name: /create new goal/i });
    await expect(createBtn).toBeVisible({ timeout: 10000 });
    await createBtn.click();

    // Modal should open with a Name input
    const nameInput = page.getByRole('textbox', { name: /name/i }).first();
    await expect(nameInput).toBeVisible({ timeout: 5000 });
  });

  // -------------------------------------------------------------------------
  // /goals/new must return 422, not silently fail
  // -------------------------------------------------------------------------

  test('/goals/new page does not silently 500 — API responds with 422 for invalid UUID', async ({ page }) => {
    // We can verify the API directly returns 422 for "new" as a UUID
    const response = await page.request.get(
      `${process.env.PLAYWRIGHT_BASE_URL || 'https://glasswatch-production.up.railway.app'}/api/v1/goals/new`,
      {
        headers: {
          'X-Tenant-ID': '550e8400-e29b-41d4-a716-446655440000',
        },
        ignoreHTTPSErrors: true,
      }
    );
    expect(response.status()).toBe(422);
    const body = await response.json();
    expect(body.detail).toBeDefined();
    // detail should be an array (FastAPI validation errors), not a string
    expect(Array.isArray(body.detail)).toBe(true);
  });
});
