import { test, expect } from '@playwright/test';

/**
 * Demo Login Flow E2E Tests
 * 
 * Critical path for showing Glasswatch to prospects.
 * This MUST work perfectly every time.
 */

test.describe('Demo Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start at the login page
    await page.goto('/auth/login');
  });

  test('should load login page without errors', async ({ page }) => {
    // Verify the page loads
    await expect(page).toHaveTitle(/Glasswatch/i);
    
    // Check for critical elements
    await expect(page.getByRole('button', { name: /Try Demo/i })).toBeVisible();
    
    // No console errors
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Wait a moment for any errors to appear
    await page.waitForTimeout(1000);
    
    // Report any errors
    if (errors.length > 0) {
      console.error('Console errors found:', errors);
    }
    expect(errors.length).toBe(0);
  });

  test('should successfully login with demo account', async ({ page }) => {
    // Click the "Try Demo" button
    await page.getByRole('button', { name: /Try Demo/i }).click();
    
    // Wait for redirection to dashboard
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    
    // Verify we're authenticated
    const url = page.url();
    expect(url).toMatch(/\/(dashboard|onboarding)/);
  });

  test('should display demo banner after login', async ({ page }) => {
    // Login with demo
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    
    // Should show demo account indicator
    const demoIndicator = page.getByText(/demo|demo@patchguide\.ai/i);
    await expect(demoIndicator).toBeVisible({ timeout: 10000 });
  });

  test('should load dashboard data without errors after demo login', async ({ page }) => {
    // Track console errors
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error' && !msg.text().includes('favicon')) {
        errors.push(msg.text());
      }
    });
    
    // Track network failures
    const failedRequests: string[] = [];
    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('/api/')) {
        failedRequests.push(`${response.status()} ${response.url()}`);
      }
    });
    
    // Login with demo
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    
    // Wait for the page to settle
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    
    // Report any issues
    if (errors.length > 0) {
      console.error('Console errors:', errors);
    }
    if (failedRequests.length > 0) {
      console.error('Failed API requests:', failedRequests);
    }
    
    expect(errors.length).toBe(0);
    expect(failedRequests.length).toBe(0);
  });

  test('should be able to navigate after demo login', async ({ page }) => {
    // Login with demo
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    
    // Wait for page to load
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    
    // Try clicking on a navigation item (e.g., Vulnerabilities)
    const vulnLink = page.locator('a[href*="/vulnerabilities"], button:has-text("Vulnerabilities")').first();
    if (await vulnLink.isVisible({ timeout: 5000 }).catch(() => false)) {
      await vulnLink.click();
      await page.waitForURL(/vulnerabilities/, { timeout: 10000 });
      
      // Page should load without errors
      await page.waitForLoadState('domcontentloaded');
    }
  });

  test('should show demo data on dashboard', async ({ page }) => {
    // Login with demo
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    
    // Wait for data to load
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    
    // Should show some content (not just loading spinners)
    // Look for numbers, cards, or lists
    const hasContent = await page.locator('text=/[0-9]+|CVE-/').count() > 0;
    expect(hasContent).toBeTruthy();
  });
});
