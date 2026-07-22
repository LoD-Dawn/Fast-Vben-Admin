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
  await completeSliderCaptcha(page);
  await expect(page.getByRole('menuitem', { name: '仪表盘' })).toBeVisible();
}

export async function completeSliderCaptcha(page: Page) {
  const bar = page.locator('.verify-bar-area:visible').last();
  await expect(bar).toBeVisible();
  const background = page.locator('.verify-background:visible').last();
  await expect(background).toHaveJSProperty('naturalWidth', 400);
  const targetImageX = await background
    .evaluate(async (element) => {
      const image = element as HTMLImageElement;
      if (!image.complete) await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('验证码图片无法读取');
      context.drawImage(image, 0, 0);
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      let darkestX = 150;
      let darkestValue = Number.POSITIVE_INFINITY;
      for (let x = 150; x <= canvas.width - 70; x += 1) {
        let luminance = 0;
        for (let y = 80; y < 112; y += 4) {
          for (let sampleX = x + 8; sampleX < x + 40; sampleX += 4) {
            const index = (y * canvas.width + sampleX) * 4;
            luminance +=
              (pixels[index] ?? 0) +
              (pixels[index + 1] ?? 0) +
              (pixels[index + 2] ?? 0);
          }
        }
        if (luminance < darkestValue) {
          darkestValue = luminance;
          darkestX = x;
        }
      }
      return darkestX;
    });
  const barBox = await bar.boundingBox();
  const action = bar.locator('.verify-move-block');
  const actionBox = await action.boundingBox();
  if (!barBox || !actionBox) throw new Error('滑动验证码未找到');

  const startX = actionBox.x + actionBox.width / 2;
  const startY = actionBox.y + actionBox.height / 2;
  const targetX =
    barBox.x + actionBox.width / 2 + (targetImageX * barBox.width) / 400;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(targetX, startY, { steps: 20 });
  await page.mouse.up();
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
