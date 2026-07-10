import { expect, test } from '@playwright/test';

import {
  apiBaseURL,
  confirmDeleteDialog,
  getApiToken,
  loginAsAdmin,
  uniqueName,
} from './helpers';

test('admin can manage posts', async ({ page, request }) => {
  const adminToken = await getApiToken(request);
  const postCode = uniqueName('e2e-post');
  const postName = `岗位-${postCode}`;
  let postId: string | undefined;

  try {
    await loginAsAdmin(page);
    await page.goto('/system/posts');

    await page.getByRole('button', { name: '新增岗位' }).click();
    const createDrawer = page.getByRole('dialog', { name: '新增岗位' });
    await createDrawer.getByRole('textbox', { name: '岗位名称' }).fill(postName);
    await createDrawer.getByRole('textbox', { name: '岗位编码' }).fill(postCode);
    await createDrawer.getByRole('spinbutton', { name: '排序' }).fill('91');
    await createDrawer.getByRole('textbox', { name: '备注' }).fill('E2E post');
    await createDrawer.getByRole('button', { name: /确\s*认/ }).click();
    await expect(page.getByText(postName)).toBeVisible();

    const listResponse = await request.get(`${apiBaseURL}/posts`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      params: { keyword: postCode },
    });
    expect(listResponse.ok()).toBeTruthy();
    const listBody = (await listResponse.json()) as {
      items: Array<{ id: string }>;
    };
    postId = listBody.items[0]?.id;
    expect(postId).toBeTruthy();

    await page.getByRole('textbox', { name: '关键词' }).fill(postCode);
    await page.getByRole('button', { name: '搜 索' }).click();
    await expect(page.getByRole('row').filter({ hasText: postCode })).toBeVisible();

    await page.getByRole('button', { name: '修改' }).first().click();
    const editDrawer = page.getByRole('dialog', { name: '编辑岗位' });
    await editDrawer.getByRole('textbox', { name: '岗位名称' }).fill(`${postName}-更新`);
    await editDrawer.getByRole('button', { name: /确\s*认/ }).click();
    await expect(page.getByText(`${postName}-更新`)).toBeVisible();

    await page.getByRole('button', { name: '删除' }).first().click();
    await confirmDeleteDialog(page, '确认删除岗位');
    await expect(page.getByText(`${postName}-更新`)).toHaveCount(0);
    postId = undefined;
  } finally {
    if (postId) {
      await request.delete(`${apiBaseURL}/posts/${postId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
    }
  }
});
