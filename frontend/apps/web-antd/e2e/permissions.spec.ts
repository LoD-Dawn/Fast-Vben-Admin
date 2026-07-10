import { expect, test } from '@playwright/test';

import {
  apiBaseURL,
  createUserByApi,
  deleteUserByApi,
  getApiToken,
  loginAs,
  uniqueName,
} from './helpers';

test('limited user cannot see protected menus or call protected APIs', async ({
  page,
  request,
}) => {
  const adminToken = await getApiToken(request);
  const password = 'changethis';
  const email = `${uniqueName('e2e-limited')}@example.com`;
  const user = await createUserByApi(request, adminToken, {
    email,
    full_name: 'Limited E2E User',
    is_active: true,
    is_superuser: false,
    password,
    role_ids: [],
  });

  try {
    const limitedToken = await getApiToken(request, email, password);
    const forbidden = await request.get(`${apiBaseURL}/users`, {
      headers: {
        Authorization: `Bearer ${limitedToken}`,
      },
    });
    expect(forbidden.status()).toBe(403);

    await loginAs(page, email, password);
    await expect(page.getByRole('menuitem', { name: '系统管理' })).toHaveCount(0);
    await expect(page.getByRole('menuitem', { name: '文件管理' })).toHaveCount(0);
    await expect(page.getByRole('menuitem', { name: '通知公告' })).toHaveCount(0);
  } finally {
    await deleteUserByApi(request, adminToken, user.id);
  }
});
