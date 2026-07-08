import { expect, test } from '@playwright/test';

import { loginAsAdmin, uniqueName } from './helpers';

test('admin can create and delete a user', async ({ page }) => {
  const email = `${uniqueName('e2e-user')}@example.com`;

  await loginAsAdmin(page);
  await page.goto('/system/users');

  await page.getByRole('button', { name: '新增用户' }).click();
  const drawer = page.locator('.ant-drawer').filter({ hasText: '新增用户' });
  await drawer.locator('input').nth(0).fill(email);
  await drawer.locator('input').nth(1).fill('E2E User');
  await drawer.locator('input[type="password"]').fill('changethis');
  await drawer.getByRole('button', { name: '确 认' }).click();
  await expect(page.getByText(email)).toBeVisible();

  await page
    .getByRole('row')
    .filter({ hasText: email })
    .getByRole('button', { name: '删除' })
    .click();
  await page
    .locator('.ant-popconfirm')
    .getByRole('button', { name: /确\s*定/ })
    .click();
  await expect(page.getByText(email)).toHaveCount(0);
});
