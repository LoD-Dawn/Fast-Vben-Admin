import { expect, test } from '@playwright/test';

import { adminEmail, adminPassword } from './helpers';

test('admin can login and reach dashboard', async ({ page }) => {
  await page.goto('/auth/login');
  await expect(page).toHaveTitle(/Fast Vben Admin/);

  await page.locator('input[name="username"]').fill(adminEmail);
  await page.locator('input[name="password"]').fill(adminPassword);
  await page.getByRole('button', { name: 'login' }).click();

  await expect(page.getByRole('heading', { name: '用户量' })).toBeVisible();
  await expect(page.getByText('流量趋势')).toBeVisible();
});
