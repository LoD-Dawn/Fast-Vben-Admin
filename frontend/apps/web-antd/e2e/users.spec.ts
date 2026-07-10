import { expect, test } from '@playwright/test';

import { confirmDeleteDialog, loginAsAdmin, uniqueName } from './helpers';

test('admin can create and delete a user', async ({ page }) => {
  const email = `${uniqueName('e2e-user')}@example.com`;

  await loginAsAdmin(page);
  await page.goto('/system/users');

  await page.getByRole('button', { name: '新增用户' }).click();
  const drawer = page.getByRole('dialog', { name: '新增用户' });
  await drawer.getByRole('textbox', { name: /邮箱/ }).fill(email);
  await drawer.getByRole('textbox', { name: '姓名' }).fill('E2E User');
  await drawer.getByRole('textbox', { name: /初始密码/ }).fill('changethis');
  await drawer.getByRole('button', { name: /确\s*认/ }).click();
  await expect(page.getByText(email)).toBeVisible();

  await page.getByRole('textbox', { name: '用户名' }).fill(email);
  await page.getByRole('button', { name: '搜 索' }).click();
  await expect(page.getByRole('row').filter({ hasText: email })).toBeVisible();

  await page.getByRole('button', { name: '删除' }).first().click();
  await confirmDeleteDialog(page, '确认删除用户');
  await expect(page.getByText(email)).toHaveCount(0);
});

test('admin can import and delete a user', async ({ page }) => {
  const email = `${uniqueName('e2e-import-user')}@example.com`;
  const csv = [
    'email,password,full_name,department_code,role_codes,post_codes,is_active,is_superuser',
    `${email},changethis,Imported E2E User,headquarters,user,developer,true,false`,
  ].join('\n');

  await loginAsAdmin(page);
  await page.goto('/system/users');

  await page.getByRole('button', { name: /导\s*入/ }).click();
  const modal = page.getByRole('dialog', { name: '导入用户' });
  await modal.locator('input[type="file"]').setInputFiles({
    buffer: Buffer.from(csv),
    mimeType: 'text/csv',
    name: 'users.csv',
  });
  await expect(modal).toHaveCount(0);

  await page.getByRole('textbox', { name: '用户名' }).fill(email);
  await page.getByRole('button', { name: '搜 索' }).click();
  await expect(page.getByRole('row').filter({ hasText: email })).toBeVisible();

  await page.getByRole('button', { name: '删除' }).first().click();
  await confirmDeleteDialog(page, '确认删除用户');
  await expect(page.getByText(email)).toHaveCount(0);
});
