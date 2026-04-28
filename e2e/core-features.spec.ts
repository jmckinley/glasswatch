import { test, expect } from '@playwright/test';

/**
 * Core Features E2E Tests
 * 
 * Tests all main feature pages to ensure they load and display data correctly.
 */

test.describe('Core Features', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    // Login with demo account
    await page.goto('/auth/login');
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 30000 });
  });

  test.describe('Vulnerabilities Page', () => {
    test('should load vulnerabilities page', async ({ page }) => {
      // Navigate to vulnerabilities
      await page.goto('/vulnerabilities');
      await page.waitForLoadState('domcontentloaded');
      
      // Page should load without crashing
      await expect(page).toHaveURL(/vulnerabilities/);
    });

    test('should display vulnerability list', async ({ page }) => {
      await page.goto('/vulnerabilities');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      // Should show vulnerabilities or empty state
      const hasVulns = await page.locator('text=/CVE-|vulnerability/i').count() > 0;
      const hasEmptyState = await page.locator('text=/no vulnerabilities|empty/i').count() > 0;
      
      expect(hasVulns || hasEmptyState).toBeTruthy();
    });

    test('should not have API errors on vulnerabilities page', async ({ page }) => {
      const errors: string[] = [];
      page.on('response', (response) => {
        if (response.status() >= 400 && response.url().includes('/api/')) {
          errors.push(`${response.status()} ${response.url()}`);
        }
      });
      
      await page.goto('/vulnerabilities');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      if (errors.length > 0) {
        console.error('API errors on vulnerabilities page:', errors);
      }
      expect(errors.length).toBe(0);
    });
  });

  test.describe('Assets Page', () => {
    test('should load assets page', async ({ page }) => {
      await page.goto('/assets');
      await page.waitForLoadState('domcontentloaded');
      
      await expect(page).toHaveURL(/assets/);
    });

    test('should display asset list or empty state', async ({ page }) => {
      await page.goto('/assets');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      const hasAssets = await page.locator('text=/asset|server|workstation/i').count() > 0;
      const hasEmptyState = await page.locator('text=/no assets|empty/i').count() > 0;
      
      expect(hasAssets || hasEmptyState).toBeTruthy();
    });

    test('should not have API errors on assets page', async ({ page }) => {
      const errors: string[] = [];
      page.on('response', (response) => {
        if (response.status() >= 400 && response.url().includes('/api/')) {
          errors.push(`${response.status()} ${response.url()}`);
        }
      });
      
      await page.goto('/assets');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      expect(errors.length).toBe(0);
    });
  });

  test.describe('Goals Page', () => {
    test('should load goals page', async ({ page }) => {
      await page.goto('/goals');
      await page.waitForLoadState('domcontentloaded');
      
      await expect(page).toHaveURL(/goals/);
    });

    test('should display goals or empty state', async ({ page }) => {
      await page.goto('/goals');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      const hasGoals = await page.locator('text=/goal|deadline|target/i').count() > 0;
      const hasEmptyState = await page.locator('text=/no goals|empty/i').count() > 0;
      
      expect(hasGoals || hasEmptyState).toBeTruthy();
    });

    test('should not have API errors on goals page', async ({ page }) => {
      const errors: string[] = [];
      page.on('response', (response) => {
        if (response.status() >= 400 && response.url().includes('/api/')) {
          errors.push(`${response.status()} ${response.url()}`);
        }
      });
      
      await page.goto('/goals');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      expect(errors.length).toBe(0);
    });
  });

  test.describe('Bundles Page', () => {
    test('should load bundles page', async ({ page }) => {
      await page.goto('/bundles');
      await page.waitForLoadState('domcontentloaded');
      
      await expect(page).toHaveURL(/bundles/);
    });

    test('should display bundles or empty state', async ({ page }) => {
      await page.goto('/bundles');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      const hasBundles = await page.locator('text=/bundle|patch/i').count() > 0;
      const hasEmptyState = await page.locator('text=/no bundles|empty/i').count() > 0;
      
      expect(hasBundles || hasEmptyState).toBeTruthy();
    });

    test('should not have API errors on bundles page', async ({ page }) => {
      const errors: string[] = [];
      page.on('response', (response) => {
        if (response.status() >= 400 && response.url().includes('/api/')) {
          errors.push(`${response.status()} ${response.url()}`);
        }
      });
      
      await page.goto('/bundles');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      expect(errors.length).toBe(0);
    });
  });

  test.describe('Audit Log Page', () => {
    test('should load audit log page', async ({ page }) => {
      await page.goto('/audit-log');
      await page.waitForLoadState('domcontentloaded');
      
      await expect(page).toHaveURL(/audit-log/);
    });

    test('should display audit events', async ({ page }) => {
      await page.goto('/audit-log');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      // Should show audit events (demo should have login events at minimum)
      const hasEvents = await page.locator('text=/login|event|action/i').count() > 0;
      const hasEmptyState = await page.locator('text=/no events|empty/i').count() > 0;
      
      expect(hasEvents || hasEmptyState).toBeTruthy();
    });
  });

  test.describe('Settings Page', () => {
    test('should load settings page', async ({ page }) => {
      await page.goto('/settings');
      await page.waitForLoadState('domcontentloaded');
      
      await expect(page).toHaveURL(/settings/);
    });

    test('should display settings sections', async ({ page }) => {
      await page.goto('/settings');
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      
      // Should show settings options
      const hasSettings = await page.locator('text=/profile|account|notification|integration/i').count() > 0;
      expect(hasSettings).toBeTruthy();
    });
  });
});
