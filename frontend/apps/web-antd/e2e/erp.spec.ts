import { expect, test } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

import {
  apiBaseURL,
  createUserByApi,
  deleteUserByApi,
  loginAs,
  loginAsAdmin,
  uniqueName,
} from './helpers';

const browserFailures = new WeakMap<object, string[]>();

async function selectRemoteOption(
  page: Page,
  select: Locator,
  keyword: string,
  option: RegExp | string,
) {
  await select.click();
  const dropdown = page.locator('.ant-select-dropdown:visible');
  await select.locator('input').fill(keyword);
  await dropdown.getByText(option, { exact: false }).click();
}

async function selectSettlementSource(drawer: Locator, sourceNo: string) {
  await drawer.getByPlaceholder('按来源单号检索').fill(sourceNo);
  await drawer.getByText(sourceNo, { exact: false }).click();
}

test.beforeEach(async ({ page }) => {
  const failures: string[] = [];
  browserFailures.set(page, failures);
  page.on('console', (message) => {
    if (message.type() === 'error') {
      const location = message.location().url;
      failures.push(`console: ${message.text()}${location ? ` (${location})` : ''}`);
    }
  });
  page.on('pageerror', (error) => failures.push(`page: ${error.message}`));
  page.on('requestfailed', (request) => {
    const errorText = request.failure()?.errorText ?? '';
    if (request.url().startsWith(apiBaseURL) && !errorText.includes('ERR_ABORTED')) {
      failures.push(`request: ${request.method()} ${request.url()} ${errorText}`);
    }
  });
});

test.afterEach(async ({ page }) => {
  expect(browserFailures.get(page) ?? []).toEqual([]);
});

const erpPages = [
  { path: '/erp/home', title: 'ERP 首页' },
  { path: '/erp/product/products', title: '商品管理' },
  { path: '/erp/purchase/orders', title: '采购订单' },
  { path: '/erp/sale/orders', title: '销售订单' },
  { path: '/erp/stock/balances', title: '库存余额' },
  { path: '/erp/finance/accounts', title: '结算账户' },
];

test('ERP sidebar follows the reference product structure', async ({ page }) => {
  await loginAsAdmin(page);

  const erpSystem = page.getByText('ERP 系统', { exact: true }).first();
  await expect(erpSystem).toBeVisible();
  await erpSystem.click();

  for (const title of [
    '首页',
    '采购管理',
    '销售管理',
    '产品库存管理',
    '产品管理',
    '财务管理',
  ]) {
    await expect(page.getByText(title, { exact: true }).first()).toBeVisible();
  }
});

test('admin can open ERP P0 workspaces', async ({ page }) => {
  await loginAsAdmin(page);

  for (const erpPage of erpPages) {
    await page.goto(erpPage.path);
    await expect(page).toHaveURL(new RegExp(`${erpPage.path}$`));
    await expect(page.getByText(erpPage.title, { exact: true }).first()).toBeVisible();
  }
});

test('admin can create and approve a purchase order from the ERP workspace', async ({
  page,
  request,
}) => {
  test.setTimeout(90_000);
  await loginAsAdmin(page);
  const token = await page.evaluate(() => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const stored = localStorage.getItem(localStorage.key(index) ?? '');
      if (!stored) continue;
      try {
        const parsed = JSON.parse(stored) as { accessToken?: unknown };
        if (typeof parsed.accessToken === 'string') return parsed.accessToken;
      } catch {
        // Other persisted stores are not part of the authenticated session.
      }
    }
    throw new Error('Authenticated browser session does not contain an access token');
  });
  const headers = (idempotencyKey: string) => ({
    Authorization: `Bearer ${token}`,
    'Idempotency-Key': idempotencyKey,
  });
  const post = async (path: string, data: Record<string, unknown>) => {
    const response = await request.post(`${apiBaseURL}/erp${path}`, {
      data,
      headers: headers(uniqueName('erp-e2e')),
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()) as { id: string };
  };

  const suffix = uniqueName('purchase-flow');
  const unit = await post('/product-units', {
    code: `unit-${suffix}`,
    name: `Unit ${suffix}`,
  });
  const category = await post('/product-categories', {
    code: `category-${suffix}`,
    name: `Category ${suffix}`,
  });
  const productName = `Product ${suffix}`;
  await post('/products', {
    category_id: category.id,
    code: `product-${suffix}`,
    name: productName,
    purchase_reference_price: '12.50',
    unit_id: unit.id,
  });
  const supplierName = `Supplier ${suffix}`;
  await post('/suppliers', { name: supplierName });

  await page.goto('/erp/purchase/orders');
  await page.getByRole('button', { name: '新增采购订单' }).click();

  const drawer = page.locator('.ant-drawer:visible');
  await expect(drawer.getByText('新建采购订单', { exact: true })).toBeVisible();
  await drawer
    .getByText('供应商', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(supplierName, { exact: true })
    .click();

  await drawer.locator('tbody .ant-select').click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${productName} (product-${suffix})`, { exact: true })
    .click();
  const lineInputs = drawer.locator('tbody .ant-input-number-input');
  await lineInputs.nth(0).fill('100');
  await lineInputs.nth(1).fill('12.5');
  await drawer.getByRole('button', { name: '保存草稿' }).click();
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);

  const orderRow = page
    .getByText(supplierName, { exact: true })
    .locator('xpath=ancestor::tr');
  await expect(orderRow).toBeVisible();
  await orderRow.getByRole('button', { name: '审核' }).click();
  const confirmation = page.locator('.ant-popconfirm:visible');
  await expect(confirmation).toContainText('审核后可用于采购入库');
  await confirmation.getByRole('button', { name: /^确\s*定$/ }).click();
  await expect(orderRow.getByText('已审核', { exact: true })).toBeVisible();
});

test('admin can draft the P2P receipt, return, and payment workspaces', async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  await loginAsAdmin(page);
  const token = await page.evaluate(() => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const stored = localStorage.getItem(localStorage.key(index) ?? '');
      if (!stored) continue;
      try {
        const parsed = JSON.parse(stored) as { accessToken?: unknown };
        if (typeof parsed.accessToken === 'string') return parsed.accessToken;
      } catch {
        // Other persisted stores are not part of the authenticated session.
      }
    }
    throw new Error('Authenticated browser session does not contain an access token');
  });
  const headers = (idempotencyKey: string) => ({
    Authorization: `Bearer ${token}`,
    'Idempotency-Key': idempotencyKey,
  });
  const post = async (path: string, data: Record<string, unknown>) => {
    const response = await request.post(`${apiBaseURL}/erp${path}`, {
      data,
      headers: headers(uniqueName('erp-e2e')),
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()) as {
      id: string;
      items: Array<{ id: string }>;
      no: string;
      version: number;
    };
  };

  const suffix = uniqueName('p2p-workspace');
  const unit = await post('/product-units', {
    code: `unit-${suffix}`,
    name: `Unit ${suffix}`,
  });
  const category = await post('/product-categories', {
    code: `category-${suffix}`,
    name: `Category ${suffix}`,
  });
  const productName = `Product ${suffix}`;
  const product = await post('/products', {
    category_id: category.id,
    code: `product-${suffix}`,
    name: productName,
    purchase_reference_price: '12.50',
    unit_id: unit.id,
  });
  const supplierName = `Supplier ${suffix}`;
  const supplier = await post('/suppliers', { name: supplierName });
  const warehouseName = `Warehouse ${suffix}`;
  const warehouse = await post('/warehouses', {
    code: `warehouse-${suffix}`,
    name: warehouseName,
  });
  const accountName = `Account ${suffix}`;
  const account = await post('/settlement-accounts', {
    account_no: `account-${suffix}`,
    name: accountName,
  });
  const purchaseOrder = await post('/purchase-orders', {
    items: [{ product_id: product.id, quantity: '10', unit_price: '12.5' }],
    settlement_account_id: account.id,
    supplier_id: supplier.id,
  });
  await post(`/purchase-orders/${purchaseOrder.id}/approve`, {
    expected_version: purchaseOrder.version,
  });

  await page.goto('/erp/purchase/ins');
  await page.getByRole('button', { name: '新建采购入库' }).click();
  const receiptDrawer = page.locator('.ant-drawer:visible');
  await receiptDrawer
    .getByText('来源采购订单', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${purchaseOrder.no} - ${supplierName}`, { exact: true })
    .click();
  await receiptDrawer.locator('tbody .ant-select').click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${warehouseName} (warehouse-${suffix})`, { exact: true })
    .click();
  const receiptCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/purchase-ins') &&
      response.request().method() === 'POST',
  );
  await receiptDrawer.getByRole('button', { name: '保存草稿' }).click();
  const receiptResponse = await receiptCreated;
  expect(receiptResponse.ok(), await receiptResponse.text()).toBeTruthy();
  const purchaseIn = (await receiptResponse.json()) as {
    id: string;
    no: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedPurchaseIn = await post(`/purchase-ins/${purchaseIn.id}/approve`, {
    expected_version: purchaseIn.version,
  });

  await page.goto('/erp/purchase/returns');
  await page.getByRole('button', { name: '新建采购退货' }).click();
  const returnDrawer = page.locator('.ant-drawer:visible');
  await returnDrawer
    .getByText('来源采购入库单', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${approvedPurchaseIn.no} - ${supplierName}`, { exact: true })
    .click();
  const returnCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/purchase-returns') &&
      response.request().method() === 'POST',
  );
  await returnDrawer.getByRole('button', { name: '保存草稿' }).click();
  const returnResponse = await returnCreated;
  expect(returnResponse.ok(), await returnResponse.text()).toBeTruthy();
  const purchaseReturn = (await returnResponse.json()) as {
    id: string;
    no: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedPurchaseReturn = await post(
    `/purchase-returns/${purchaseReturn.id}/approve`,
    { expected_version: purchaseReturn.version },
  );

  await page.goto('/erp/finance/payments');
  await page.getByRole('button', { name: '新建付款单' }).click();
  const paymentDrawer = page.locator('.ant-drawer:visible');
  await paymentDrawer
    .getByText('供应商', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(supplierName, { exact: true })
    .click();
  await selectRemoteOption(
    page,
    paymentDrawer
      .getByText('结算账户', { exact: true })
      .locator('xpath=..')
      .locator('.ant-select'),
    accountName,
    new RegExp(`^${accountName} \\(`),
  );
  await selectSettlementSource(paymentDrawer, approvedPurchaseIn.no);
  await selectSettlementSource(paymentDrawer, approvedPurchaseReturn.no);
  const paymentCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/finance-payments') &&
      response.request().method() === 'POST',
  );
  await paymentDrawer.getByRole('button', { name: '保存草稿' }).click();
  const paymentResponse = await paymentCreated;
  expect(paymentResponse.ok(), await paymentResponse.text()).toBeTruthy();
  const payment = (await paymentResponse.json()) as { version: number; id: string };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedPayment = await post(`/finance-payments/${payment.id}/approve`, {
    expected_version: payment.version,
  });
  expect(approvedPayment.version).toBeGreaterThan(payment.version);
});

test('admin can draft the O2C shipment, return, and receipt workspaces', async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  await loginAsAdmin(page);
  const token = await page.evaluate(() => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const stored = localStorage.getItem(localStorage.key(index) ?? '');
      if (!stored) continue;
      try {
        const parsed = JSON.parse(stored) as { accessToken?: unknown };
        if (typeof parsed.accessToken === 'string') return parsed.accessToken;
      } catch {
        // Other persisted stores are not part of the authenticated session.
      }
    }
    throw new Error('Authenticated browser session does not contain an access token');
  });
  const headers = (idempotencyKey: string) => ({
    Authorization: `Bearer ${token}`,
    'Idempotency-Key': idempotencyKey,
  });
  const post = async (path: string, data: Record<string, unknown>) => {
    const response = await request.post(`${apiBaseURL}/erp${path}`, {
      data,
      headers: headers(uniqueName('erp-e2e')),
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()) as {
      id: string;
      no: string;
      version: number;
    };
  };

  const suffix = uniqueName('o2c-workspace');
  const unit = await post('/product-units', {
    code: `unit-${suffix}`,
    name: `Unit ${suffix}`,
  });
  const category = await post('/product-categories', {
    code: `category-${suffix}`,
    name: `Category ${suffix}`,
  });
  const productName = `Product ${suffix}`;
  const product = await post('/products', {
    category_id: category.id,
    code: `product-${suffix}`,
    name: productName,
    purchase_reference_price: '12.50',
    sale_reference_price: '20',
    unit_id: unit.id,
  });
  const customerName = `Customer ${suffix}`;
  const customer = await post('/customers', { name: customerName });
  const warehouseName = `Warehouse ${suffix}`;
  const warehouse = await post('/warehouses', {
    code: `warehouse-${suffix}`,
    name: warehouseName,
  });
  const accountName = `Account ${suffix}`;
  const account = await post('/settlement-accounts', {
    account_no: `account-${suffix}`,
    name: accountName,
  });
  const stockIn = await post('/stock-ins', {
    items: [{
      product_id: product.id,
      quantity: '10',
      reference_price: '12.5',
      warehouse_id: warehouse.id,
    }],
  });
  await post(`/stock-ins/${stockIn.id}/approve`, {
    expected_version: stockIn.version,
  });
  const saleOrder = await post('/sale-orders', {
    customer_id: customer.id,
    items: [{ product_id: product.id, quantity: '10', unit_price: '20' }],
    settlement_account_id: account.id,
  });
  await post(`/sale-orders/${saleOrder.id}/approve`, {
    expected_version: saleOrder.version,
  });

  await page.goto('/erp/sale/outs');
  await page.getByRole('button', { name: '新建销售出库' }).click();
  const shipmentDrawer = page.locator('.ant-drawer:visible');
  await shipmentDrawer
    .getByText('来源销售订单', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${saleOrder.no} - ${customerName}`, { exact: true })
    .click();
  await shipmentDrawer.locator('tbody .ant-select').click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${warehouseName} (warehouse-${suffix})`, { exact: true })
    .click();
  const shipmentCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/sale-outs') &&
      response.request().method() === 'POST',
  );
  await shipmentDrawer.getByRole('button', { name: '保存草稿' }).click();
  const shipmentResponse = await shipmentCreated;
  expect(shipmentResponse.ok(), await shipmentResponse.text()).toBeTruthy();
  const saleOut = (await shipmentResponse.json()) as {
    id: string;
    no: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedSaleOut = await post(`/sale-outs/${saleOut.id}/approve`, {
    expected_version: saleOut.version,
  });

  await page.goto('/erp/sale/returns');
  await page.getByRole('button', { name: '新建销售退货' }).click();
  const returnDrawer = page.locator('.ant-drawer:visible');
  await returnDrawer
    .getByText('来源销售出库单', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${approvedSaleOut.no} - ${customerName}`, { exact: true })
    .click();
  const returnCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/sale-returns') &&
      response.request().method() === 'POST',
  );
  await returnDrawer.getByRole('button', { name: '保存草稿' }).click();
  const returnResponse = await returnCreated;
  expect(returnResponse.ok(), await returnResponse.text()).toBeTruthy();
  const saleReturn = (await returnResponse.json()) as {
    id: string;
    no: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedSaleReturn = await post(`/sale-returns/${saleReturn.id}/approve`, {
    expected_version: saleReturn.version,
  });

  await page.goto('/erp/finance/receipts');
  await page.getByRole('button', { name: '新建收款单' }).click();
  const receiptDrawer = page.locator('.ant-drawer:visible');
  await receiptDrawer
    .getByText('客户', { exact: true })
    .locator('xpath=..')
    .locator('.ant-select')
    .click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(customerName, { exact: true })
    .click();
  await selectRemoteOption(
    page,
    receiptDrawer
      .getByText('结算账户', { exact: true })
      .locator('xpath=..')
      .locator('.ant-select'),
    accountName,
    new RegExp(`^${accountName} \\(`),
  );
  await selectSettlementSource(receiptDrawer, approvedSaleOut.no);
  await selectSettlementSource(receiptDrawer, approvedSaleReturn.no);
  const receiptCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/finance-receipts') &&
      response.request().method() === 'POST',
  );
  await receiptDrawer.getByRole('button', { name: '保存草稿' }).click();
  const receiptResponse = await receiptCreated;
  expect(receiptResponse.ok(), await receiptResponse.text()).toBeTruthy();
  const financeReceipt = (await receiptResponse.json()) as {
    id: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedReceipt = await post(`/finance-receipts/${financeReceipt.id}/approve`, {
    expected_version: financeReceipt.version,
  });
  expect(approvedReceipt.version).toBeGreaterThan(financeReceipt.version);
});

test('ERP document drawers remain usable on a narrow viewport', async ({ page }) => {
  await loginAsAdmin(page);
  await page.setViewportSize({ height: 844, width: 390 });

  await page.goto('/erp/purchase/ins');
  await page.getByRole('button', { name: '新建采购入库' }).click();
  const purchaseDrawer = page.locator('.ant-drawer:visible');
  await expect(purchaseDrawer).toBeVisible();
  const purchaseDrawerBox = await purchaseDrawer.boundingBox();
  expect(purchaseDrawerBox?.width).toBeLessThanOrEqual(390);
  await expect(
    purchaseDrawer.getByRole('button', { name: '保存草稿' }),
  ).toBeInViewport();

  await page.goto('/erp/stock/other-in');
  await page.getByRole('button', { name: '新建其他入库' }).click();
  const stockDrawer = page.locator('.ant-drawer:visible');
  await expect(stockDrawer).toBeVisible();
  const stockDrawerBox = await stockDrawer.boundingBox();
  expect(stockDrawerBox?.width).toBeLessThanOrEqual(390);
  await expect(
    stockDrawer.getByRole('button', { name: '保存草稿' }),
  ).toBeInViewport();
});

test('admin can draft and approve an other stock-in document', async ({
  page,
  request,
}) => {
  test.setTimeout(90_000);
  await loginAsAdmin(page);
  const token = await page.evaluate(() => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const stored = localStorage.getItem(localStorage.key(index) ?? '');
      if (!stored) continue;
      try {
        const parsed = JSON.parse(stored) as { accessToken?: unknown };
        if (typeof parsed.accessToken === 'string') return parsed.accessToken;
      } catch {
        // Other persisted stores are not part of the authenticated session.
      }
    }
    throw new Error('Authenticated browser session does not contain an access token');
  });
  const post = async (path: string, data: Record<string, unknown>) => {
    const response = await request.post(`${apiBaseURL}/erp${path}`, {
      data,
      headers: {
        Authorization: `Bearer ${token}`,
        'Idempotency-Key': uniqueName('erp-e2e'),
      },
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()) as { id: string; version: number };
  };
  const suffix = uniqueName('stock-in-workspace');
  const unit = await post('/product-units', {
    code: `unit-${suffix}`,
    name: `Unit ${suffix}`,
  });
  const category = await post('/product-categories', {
    code: `category-${suffix}`,
    name: `Category ${suffix}`,
  });
  const productName = `Product ${suffix}`;
  await post('/products', {
    category_id: category.id,
    code: `product-${suffix}`,
    name: productName,
    unit_id: unit.id,
  });
  const warehouseName = `Warehouse ${suffix}`;
  await post('/warehouses', {
    code: `warehouse-${suffix}`,
    name: warehouseName,
  });

  await page.goto('/erp/stock/other-in');
  await page.getByRole('button', { name: '新建其他入库' }).click();
  const drawer = page.locator('.ant-drawer:visible');
  const selects = drawer.locator('tbody .ant-select');
  await selects.nth(0).click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${productName} (product-${suffix})`, { exact: true })
    .click();
  await selects.nth(1).click();
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(`${warehouseName} (warehouse-${suffix})`, { exact: true })
    .click();
  const lineInputs = drawer.locator('tbody .ant-input-number-input');
  await lineInputs.nth(0).fill('5');
  await lineInputs.nth(1).fill('3.5');
  const documentCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/stock-ins') &&
      response.request().method() === 'POST',
  );
  await drawer.getByRole('button', { name: '保存草稿' }).click();
  const documentResponse = await documentCreated;
  expect(documentResponse.ok(), await documentResponse.text()).toBeTruthy();
  const stockIn = (await documentResponse.json()) as {
    id: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approved = await post(`/stock-ins/${stockIn.id}/approve`, {
    expected_version: stockIn.version,
  });
  expect(approved.version).toBeGreaterThan(stockIn.version);
});

test('admin can draft and approve stock move and stock check documents', async ({
  page,
  request,
}) => {
  test.setTimeout(120_000);
  await loginAsAdmin(page);
  const token = await page.evaluate(() => {
    for (let index = 0; index < localStorage.length; index += 1) {
      const stored = localStorage.getItem(localStorage.key(index) ?? '');
      if (!stored) continue;
      try {
        const parsed = JSON.parse(stored) as { accessToken?: unknown };
        if (typeof parsed.accessToken === 'string') return parsed.accessToken;
      } catch {
        // Other persisted stores are not part of the authenticated session.
      }
    }
    throw new Error('Authenticated browser session does not contain an access token');
  });
  const post = async (path: string, data: Record<string, unknown>) => {
    const response = await request.post(`${apiBaseURL}/erp${path}`, {
      data,
      headers: {
        Authorization: `Bearer ${token}`,
        'Idempotency-Key': uniqueName('erp-e2e'),
      },
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    return (await response.json()) as { id: string; version: number };
  };
  const suffix = uniqueName('move-check-workspace');
  const unit = await post('/product-units', {
    code: `unit-${suffix}`,
    name: `Unit ${suffix}`,
  });
  const category = await post('/product-categories', {
    code: `category-${suffix}`,
    name: `Category ${suffix}`,
  });
  const productName = `Product ${suffix}`;
  const product = await post('/products', {
    category_id: category.id,
    code: `product-${suffix}`,
    name: productName,
    unit_id: unit.id,
  });
  const sourceName = `Source ${suffix}`;
  const source = await post('/warehouses', {
    code: `source-${suffix}`,
    name: sourceName,
  });
  const destinationName = `Destination ${suffix}`;
  const destination = await post('/warehouses', {
    code: `dst-${suffix}`,
    name: destinationName,
  });
  const seed = await post('/stock-ins', {
    items: [{
      product_id: product.id,
      quantity: '5',
      reference_price: '3.5',
      warehouse_id: source.id,
    }],
  });
  await post(`/stock-ins/${seed.id}/approve`, { expected_version: seed.version });

  await page.goto('/erp/stock/move');
  await page.getByRole('button', { name: '新建库存调拨' }).click();
  const moveDrawer = page.locator('.ant-drawer:visible');
  const moveSelects = moveDrawer.locator('tbody .ant-select');
  await selectRemoteOption(page, moveSelects.nth(0), productName, `${productName} (product-${suffix})`);
  await selectRemoteOption(page, moveSelects.nth(1), sourceName, `${sourceName} (source-${suffix})`);
  await selectRemoteOption(page, moveSelects.nth(2), destinationName, `${destinationName} (dst-${suffix})`);
  const moveInputs = moveDrawer.locator('tbody .ant-input-number-input');
  await moveInputs.nth(0).fill('2');
  await moveInputs.nth(1).fill('3.5');
  const moveCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/stock-moves') &&
      response.request().method() === 'POST',
  );
  await moveDrawer.getByRole('button', { name: '保存草稿' }).click();
  const moveResponse = await moveCreated;
  expect(moveResponse.ok(), await moveResponse.text()).toBeTruthy();
  const move = (await moveResponse.json()) as { id: string; version: number };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedMove = await post(`/stock-moves/${move.id}/approve`, {
    expected_version: move.version,
  });
  expect(approvedMove.version).toBeGreaterThan(move.version);

  await page.goto('/erp/stock/check');
  await page.getByRole('button', { name: '新建库存盘点' }).click();
  const checkDrawer = page.locator('.ant-drawer:visible');
  const checkSelects = checkDrawer.locator('tbody .ant-select');
  await selectRemoteOption(page, checkSelects.nth(0), productName, `${productName} (product-${suffix})`);
  await selectRemoteOption(page, checkSelects.nth(1), sourceName, `${sourceName} (source-${suffix})`);
  const checkInputs = checkDrawer.locator('tbody .ant-input-number-input');
  await checkInputs.nth(0).fill('4');
  await checkInputs.nth(1).fill('3.5');
  const checkCreated = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/erp/stock-checks') &&
      response.request().method() === 'POST',
  );
  await checkDrawer.getByRole('button', { name: '保存草稿' }).click();
  const checkResponse = await checkCreated;
  expect(checkResponse.ok(), await checkResponse.text()).toBeTruthy();
  const stockCheck = (await checkResponse.json()) as {
    id: string;
    version: number;
  };
  await expect(page.locator('.ant-drawer-open')).toHaveCount(0);
  const approvedCheck = await post(`/stock-checks/${stockCheck.id}/approve`, {
    expected_version: stockCheck.version,
  });
  expect(approvedCheck.version).toBeGreaterThan(stockCheck.version);
});

test('limited user cannot access ERP APIs or enable ERP actions by direct URL', async ({
  browser,
  page,
  request,
}) => {
  await loginAsAdmin(page);
  const readAccessToken = async (targetPage = page) =>
    await targetPage.evaluate(() => {
      for (let index = 0; index < localStorage.length; index += 1) {
        const stored = localStorage.getItem(localStorage.key(index) ?? '');
        if (!stored) continue;
        try {
          const parsed = JSON.parse(stored) as { accessToken?: unknown };
          if (typeof parsed.accessToken === 'string') return parsed.accessToken;
        } catch {
          // Other persisted stores are not part of the authenticated session.
        }
      }
      throw new Error('Authenticated browser session does not contain an access token');
    });
  const adminToken = await readAccessToken();
  const password = 'changethis';
  const email = `${uniqueName('erp-limited')}@example.com`;
  const user = await createUserByApi(request, adminToken, {
    email,
    full_name: 'Limited ERP E2E User',
    is_active: true,
    is_superuser: false,
    password,
    role_ids: [],
  });

  const limitedContext = await browser.newContext({
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5174',
  });
  const limitedPage = await limitedContext.newPage();
  try {
    await loginAs(limitedPage, email, password);
    const limitedToken = await readAccessToken(limitedPage);
    const headers = { Authorization: `Bearer ${limitedToken}` };
    const list = await request.get(`${apiBaseURL}/erp/products`, { headers });
    const detail = await request.get(
      `${apiBaseURL}/erp/products/00000000-0000-0000-0000-000000000001`,
      { headers },
    );
    expect(list.status()).toBe(403);
    expect(detail.status()).toBe(403);

    await limitedPage.goto('/erp/product/products');
    await expect(
      limitedPage.getByRole('button', { name: '新增商品' }),
    ).toHaveCount(0);
  } finally {
    await limitedContext.close();
    await deleteUserByApi(request, adminToken, user.id);
  }
});
