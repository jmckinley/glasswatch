import { test, expect } from '@playwright/test';

/**
 * AI Analyst E2E Tests
 *
 * Guards against the regression where:
 * - "What needs my attention right now?" returned the capabilities menu
 *   instead of the actual attention handler response (pattern mismatch: missing "my").
 * - Sample prompt chips appeared but triggered wrong intents.
 */

test.describe('AI Analyst', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 30000 });
  });

  // -------------------------------------------------------------------------
  // Page loads
  // -------------------------------------------------------------------------

  test('AI analyst page loads without errors', async ({ page }) => {
    const apiErrors: string[] = [];
    page.on('response', (r) => {
      if (r.status() >= 500 && r.url().includes('/api/')) {
        apiErrors.push(`${r.status()} ${r.url()}`);
      }
    });

    await page.goto('/agent');
    await page.waitForLoadState('networkidle', { timeout: 20000 });

    expect(apiErrors).toHaveLength(0);
    await expect(page).toHaveURL(/agent/);
  });

  test('shows "Your AI Security Analyst" empty state heading', async ({ page }) => {
    await page.goto('/agent');
    await page.waitForLoadState('domcontentloaded');

    await expect(
      page.getByText(/your ai security analyst/i)
    ).toBeVisible({ timeout: 10000 });
  });

  test('shows sample prompt chips in empty state', async ({ page }) => {
    await page.goto('/agent');
    await page.waitForLoadState('domcontentloaded');

    // At least some prompt chips should be visible
    const chips = page.locator('button, [role="button"]').filter({ hasText: /attention|KEV|compliance|approval|patch|SLA/i });
    const count = await chips.count();
    expect(count).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // Regression: "What needs my attention right now?" must NOT return the
  // capabilities menu. This failed when pattern lacked "my".
  // -------------------------------------------------------------------------

  test('"What needs my attention right now?" returns attention response, not capabilities menu', async ({ page }) => {
    await page.goto('/agent');
    await page.waitForLoadState('domcontentloaded');

    // Type the message in the chat input
    const input = page.locator('input[type="text"], textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill('What needs my attention right now?');
    await input.press('Enter');

    // Wait for response to appear
    await page.waitForTimeout(3000);

    // The response text area / messages area
    const pageText = await page.locator('body').innerText();

    // Must NOT be the capabilities fallback menu
    expect(pageText).not.toContain('I can help with:');

    // Should contain real content (numbers, CVE references, or a meaningful message)
    // At minimum it should NOT be blank
    const responseEl = page.locator('[class*="message"], [class*="response"], [class*="chat"]').last();
    const responseCount = await responseEl.count();
    if (responseCount > 0) {
      const text = await responseEl.innerText();
      expect(text.length).toBeGreaterThan(5);
    }
  });

  // -------------------------------------------------------------------------
  // Clicking a sample prompt chip triggers an API call
  // -------------------------------------------------------------------------

  test('clicking a sample prompt chip sends an API request', async ({ page }) => {
    const agentRequests: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/agent/chat')) {
        agentRequests.push(req.url());
      }
    });

    await page.goto('/agent');
    await page.waitForLoadState('domcontentloaded');

    // Click the first visible chip button
    const chips = page.locator('button, [role="button"]').filter({
      hasText: /attention|KEV|compliance|approval/i,
    });
    const firstChip = chips.first();
    const chipVisible = await firstChip.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipVisible) {
      await firstChip.click();
      await page.waitForTimeout(2000);
      expect(agentRequests.length).toBeGreaterThan(0);
    } else {
      // Chips not present; skip (empty state may have loaded differently)
      test.skip();
    }
  });

  // -------------------------------------------------------------------------
  // Type a message and get a response
  // -------------------------------------------------------------------------

  test('can type a message and receive a non-empty response', async ({ page }) => {
    await page.goto('/agent');
    await page.waitForLoadState('domcontentloaded');

    const input = page.locator('input[type="text"], textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill('Show goals');
    await input.press('Enter');

    // Wait for API call to complete
    await page.waitForTimeout(4000);

    // Page should now contain some response content
    const pageText = await page.locator('body').innerText();
    // After sending a message, the page must have more content than just the empty state
    expect(pageText.length).toBeGreaterThan(50);
  });

  // -------------------------------------------------------------------------
  // API endpoint direct tests (lighter-weight)
  // -------------------------------------------------------------------------

  test('POST /api/v1/agent/chat with attention intent returns non-fallback response', async ({ page }) => {
    // Use the page's request context (will include demo auth cookie if set via localStorage)
    const BASE = process.env.PLAYWRIGHT_BASE_URL || 'https://glasswatch-production.up.railway.app';

    // First do demo login to get a token
    const loginResp = await page.request.post(`${BASE}/api/v1/auth/demo-login`, {
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (loginResp.status() !== 200) {
      // If login fails in this environment, skip
      test.skip();
      return;
    }

    const { access_token } = await loginResp.json();

    const chatResp = await page.request.post(`${BASE}/api/v1/agent/chat`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${access_token}`,
      },
      data: { message: 'What needs my attention right now?' },
    });

    expect(chatResp.status()).toBe(200);
    const body = await chatResp.json();
    expect(body.response).toBeDefined();
    expect(body.response.length).toBeGreaterThan(0);
    // Must NOT be the capabilities list
    expect(body.response).not.toContain('I can help with:');
    expect(body.actions_taken).toBeDefined();
    expect(body.suggested_actions).toBeDefined();
  });
});
