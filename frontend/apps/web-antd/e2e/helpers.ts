import type { APIRequestContext, Locator, Page } from '@playwright/test';

import { expect } from '@playwright/test';

export const adminEmail = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com';
export const adminPassword = process.env.E2E_ADMIN_PASSWORD ?? 'changethis';
export const apiBaseURL =
  process.env.E2E_API_URL ??
  process.env.VITE_GLOB_API_URL ??
  'http://localhost:8000/api/v1';

export async function loginAs(
  page: Page,
  email: string,
  password: string,
) {
  await page.goto('/auth/login');
  await page.locator('input[name="username"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: 'login' }).click();
  await expect(page.getByRole('menuitem', { name: '仪表盘' })).toBeVisible();
}

export async function loginAsAdmin(page: Page) {
  await loginAs(page, adminEmail, adminPassword);
}

export function uniqueName(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export async function confirmDialog(dialog: Locator) {
  await dialog.getByRole('button', { name: /^(OK|确\s*认|确\s*定)$/ }).click();
}

export async function confirmDeleteDialog(page: Page, title: string) {
  await page
    .locator('.ant-popconfirm')
    .filter({ hasText: title })
    .getByRole('button', { name: /^确\s*定$/ })
    .click();
}

export async function getApiToken(
  request: APIRequestContext,
  email = adminEmail,
  password = adminPassword,
) {
  const response = await request.post(`${apiBaseURL}/login/access-token`, {
    form: {
      password,
      username: email,
    },
  });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

export async function createUserByApi(
  request: APIRequestContext,
  token: string,
  data: {
    email: string;
    full_name?: string;
    is_active?: boolean;
    is_superuser?: boolean;
    password: string;
    role_ids?: string[];
  },
) {
  const response = await request.post(`${apiBaseURL}/users`, {
    data,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as { id: string };
}

export async function deleteUserByApi(
  request: APIRequestContext,
  token: string,
  userId: string,
) {
  const response = await request.delete(`${apiBaseURL}/users/${userId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  expect([200, 204, 404]).toContain(response.status());
}
