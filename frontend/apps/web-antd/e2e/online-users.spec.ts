import { expect, test } from '@playwright/test';

import {
  apiBaseURL,
  createUserByApi,
  deleteUserByApi,
  getApiToken,
  loginAsAdmin,
  uniqueName,
} from './helpers';

test('admin can force another online user to log out', async ({ page, request }) => {
  const adminToken = await getApiToken(request);
  const email = `${uniqueName('e2e-online-user')}@example.com`;
  let userId: string | undefined;

  try {
    const user = await createUserByApi(request, adminToken, {
      email,
      full_name: 'Online E2E User',
      password: 'changethis',
    });
    userId = user.id;

    const targetLogin = await request.post(`${apiBaseURL}/login/access-token`, {
      form: {
        password: 'changethis',
        username: email,
      },
    });
    expect(targetLogin.ok()).toBeTruthy();
    const { access_token: targetToken } = (await targetLogin.json()) as {
      access_token: string;
    };

    await loginAsAdmin(page);
    await page.goto('/system/online-users');
    await page.getByRole('textbox', { name: '关键词' }).fill(email);
    await page.getByRole('button', { name: '搜 索' }).click();
    const targetRow = page.getByRole('row').filter({ hasText: email });
    await expect(targetRow).toBeVisible();
    await page.getByRole('button', { name: '强制下线' }).click();

    const dialog = page
      .getByRole('dialog')
      .filter({ hasText: '确认强制用户' });
    await dialog.getByRole('button', { name: /确\s*定/ }).click();
    await expect(targetRow).toHaveCount(0);

    const rejected = await request.get(`${apiBaseURL}/users/me`, {
      headers: { Authorization: `Bearer ${targetToken}` },
    });
    expect(rejected.status()).toBe(403);
  } finally {
    if (userId) {
      await deleteUserByApi(request, adminToken, userId);
    }
  }
});
