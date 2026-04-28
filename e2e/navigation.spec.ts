import { test, expect } from '@playwright/test';

/**
 * Navigation E2E Tests
 * 
 * Ensures users can navigate through the app without errors.
 */

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Login with demo account
    await page.goto('/auth/login');
    await page.getByRole('button', { name: /Try Demo/i }).click();
    await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
    await page.waitForLoadState('networkidle', { timeout: 30000 });
  });

  test('should navigate to all main pages without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('response', (response) => {
      if (response.status() >= 400 && response.url().includes('/api/')) {
        errors.push(`${response.status()} ${response.url()}`);
      }
    });

    // Test navigation to key pages
    const pages = [
      { path: '/', name: 'Dashboard' },
      { path: '/vulnerabilities', name: 'Vulnerabilities' },
      { path: '/assets', name: 'Assets' },
      { path: '/goals', name: 'Goals' },
      { path: '/bundles', name: 'Bundles' },
      { path: '/audit-log', name: 'Audit Log' },
      { path: '/settings', name: 'Settings' },
    ];

    for (const pageInfo of pages) {
      await page.goto(pageInfo.path);
      await page.waitForLoadState('domcontentloaded');
      
      // Verify URL changed
      expect(page.url()).toContain(pageInfo.path === '/' ? '/dashboard' : pageInfo.path);
      
      // Wait a moment for any errors
      await page.waitForTimeout(1000);
    }

    // Report errors
    if (errors.length > 0) {
      console.error('Navigation errors:', errors);
    }
    expect(errors.length).toBe(0);
  });

  test('should maintain authentication across page navigation', async ({ page }) => {
    // Navigate to multiple pages
    await page.goto('/vulnerabilities');
    await page.waitForLoadState('domcontentloaded');
    
    await page.goto('/assets');
    await page.waitForLoadState('domcontentloaded');
    
    await page.goto('/bundles');
    await page.waitForLoadState('domcontentloaded');
    
    // Should still be logged in (not redirected to login)
    await expect(page).not.toHaveURL(/auth\/login/);
  });

  test('should show active navigation state', async ({ page }) => {
    await page.goto('/vulnerabilities');
    await page.waitForLoadState('domcontentloaded');
    
    // The vulnerabilities nav item should be highlighted/active
    // (This is UI-dependent, adjust selector as needed)
    const navItem = page.locator('a[href*="/vulnerabilities"]').first();
    
    if (await navItem.isVisible({ timeout: 3000 }).catch(() => false)) {
      const classes = await navItem.getAttribute('class') || '';
      // Should have some active/selected class
      const isActive = classes.includes('active') || classes.includes('selected') || classes.includes('bg-');
      expect(isActive).toBeTruthy();
    }
  });

  test('should handle browser back/forward navigation', async ({ page }) => {
    // Navigate through pages
    await page.goto('/vulnerabilities');
    await page.waitForLoadState('domcontentloaded');
    
    await page.goto('/assets');
    await page.waitForLoadState('domcontentloaded');
    
    // Go back
    await page.goBack();
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL(/vulnerabilities/);
    
    // Go forward
    await page.goForward();
    await page.waitForLoadState('domcontentloaded');
    await expect(page).toHaveURL(/assets/);
  });

  test('should handle direct URL navigation', async ({ page }) => {
    // Direct navigation to a deep page
    await page.goto('/vulnerabilities');
    await page.waitForLoadState('domcontentloaded');
    
    // Should load the page (not redirect to login)
    await expect(page).toHaveURL(/vulnerabilities/);
    
    // Page should load without errors
    await page.waitForTimeout(2000);
    const hasError = await page.locator('text=/error|failed|crash/i').count() > 0;
    expect(hasError).toBeFalsy();
  });
});
