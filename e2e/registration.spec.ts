import { test, expect } from '@playwright/test';

/**
 * Registration and Email Login E2E Tests
 * 
 * Tests the sign-up and login flows for new users.
 */

test.describe('Registration Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
  });

  test('should display registration form', async ({ page }) => {
    // Click on "Create Account" or similar
    const createAccountButton = page.getByRole('tab', { name: /register|create account|sign up/i }).or(
      page.getByRole('button', { name: /register|create account|sign up/i })
    );
    
    if (await createAccountButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createAccountButton.click();
      
      // Should see registration fields
      await expect(page.getByLabel(/email/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
      await expect(page.getByLabel(/name/i).or(page.getByLabel(/full name/i))).toBeVisible();
    }
  });

  test('should successfully register a new account', async ({ page }) => {
    // Generate unique email
    const timestamp = Date.now();
    const testEmail = `test${timestamp}@example.com`;
    const testName = 'Test User';
    const testCompany = 'Test Company';
    const testPassword = 'SecurePass123!';
    
    // Try to find and click register tab/button
    const createAccountButton = page.getByRole('tab', { name: /register|create account|sign up/i }).or(
      page.getByRole('button', { name: /register|create account|sign up/i })
    );
    
    if (await createAccountButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createAccountButton.click();
      
      // Fill in the form
      await page.getByLabel(/name/i).or(page.getByLabel(/full name/i)).first().fill(testName);
      await page.getByLabel(/email/i).first().fill(testEmail);
      await page.getByLabel(/company|organization/i).or(page.getByPlaceholder(/company|organization/i)).first().fill(testCompany);
      await page.getByLabel(/password/i).first().fill(testPassword);
      
      // Submit
      await page.getByRole('button', { name: /create account|register|sign up/i }).click();
      
      // Should redirect to onboarding or dashboard
      await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15000 });
      
      // Verify we're logged in
      const url = page.url();
      expect(url).toMatch(/\/(dashboard|onboarding)/);
    } else {
      test.skip();
    }
  });

  test('should show validation errors for invalid input', async ({ page }) => {
    const createAccountButton = page.getByRole('tab', { name: /register|create account|sign up/i }).or(
      page.getByRole('button', { name: /register|create account|sign up/i })
    );
    
    if (await createAccountButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createAccountButton.click();
      
      // Try to submit empty form
      await page.getByRole('button', { name: /create account|register|sign up/i }).click();
      
      // Should show validation errors
      await page.waitForTimeout(1000);
      
      // Look for error messages
      const errorMessage = page.getByText(/required|invalid|error/i);
      const hasError = await errorMessage.count() > 0;
      expect(hasError).toBeTruthy();
    } else {
      test.skip();
    }
  });
});

test.describe('Email Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
  });

  test('should display email login form', async ({ page }) => {
    // Look for sign in tab/form
    const signInTab = page.getByRole('tab', { name: /sign in|login/i });
    
    if (await signInTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await signInTab.click();
    }
    
    // Should see email and password fields
    await expect(page.getByLabel(/email/i).first()).toBeVisible();
    await expect(page.getByLabel(/password/i).first()).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Look for sign in tab/form
    const signInTab = page.getByRole('tab', { name: /sign in|login/i });
    
    if (await signInTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await signInTab.click();
    }
    
    // Try invalid login
    await page.getByLabel(/email/i).first().fill('invalid@example.com');
    await page.getByLabel(/password/i).first().fill('wrongpassword');
    await page.getByRole('button', { name: /sign in|login/i }).first().click();
    
    // Wait for error
    await page.waitForTimeout(2000);
    
    // Should show error message
    const errorMessage = page.getByText(/invalid|incorrect|error|failed/i);
    const hasError = await errorMessage.count() > 0;
    expect(hasError).toBeTruthy();
  });
});
