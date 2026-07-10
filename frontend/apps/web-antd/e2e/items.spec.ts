import { expect, test } from '@playwright/test';

import {
  confirmDeleteDialog,
  confirmDialog,
  loginAsAdmin,
  uniqueName,
} from './helpers';

test('admin can create, edit, and delete an item', async ({ page }) => {
  const title = uniqueName('e2e-item');
  const updatedTitle = `${title}-updated`;

  await loginAsAdmin(page);
  await page.goto('/items');

  await page.getByRole('button', { name: '新增资源' }).click();
  const modal = page.getByRole('dialog', { name: '新增资源' });
  await modal.getByRole('textbox', { name: /标题/ }).fill(title);
  await modal.getByRole('textbox', { name: '描述' }).fill('E2E item description');
  await confirmDialog(modal);
  await expect(page.getByText(title)).toBeVisible();

  await page
    .getByRole('row')
    .filter({ hasText: title })
    .getByRole('button', { name: '修改' })
    .click();
  const editModal = page.getByRole('dialog', { name: '编辑资源' });
  await editModal.getByRole('textbox', { name: /标题/ }).fill(updatedTitle);
  await confirmDialog(editModal);
  await expect(page.getByText(updatedTitle)).toBeVisible();

  await page
    .getByRole('row')
    .filter({ hasText: updatedTitle })
    .getByRole('button', { name: '删除' })
    .click();
  await confirmDeleteDialog(page, '确认删除资源');
  await expect(page.getByText(updatedTitle)).toHaveCount(0);
});
