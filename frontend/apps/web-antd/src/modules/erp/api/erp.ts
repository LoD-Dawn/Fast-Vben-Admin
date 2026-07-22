import type {
  CounterpartyPublic,
  CustomersPublic,
  DocumentAttachmentPublic,
  DocumentAttachmentsPublic,
  FinancePaymentPublic,
  FinancePaymentsPublic,
  FinanceReceiptPublic,
  FinanceReceiptsPublic,
  DocumentActionLogsPublic,
  ProductCategoriesPublic,
  ProductCategoryPublic,
  ProductPublic,
  ProductUnitsPublic,
  PurchaseOrderPublic,
  PurchaseOrdersPublic,
  PurchaseInPublic,
  PurchaseInsPublic,
  PurchaseReturnPublic,
  PurchaseReturnsPublic,
  SaleOrderPublic,
  SaleOrdersPublic,
  SaleOutPublic,
  SaleOutsPublic,
  SaleReturnPublic,
  SaleReturnsPublic,
  SettlementAccountPublic,
  SettlementAccountsPublic,
  ProductUnitPublic,
  ProductsPublic,
  ReconciliationRunPublic,
  StockBalancesPublic,
  StockChecksPublic,
  StockCheckPublic,
  StockInsPublic,
  StockInPublic,
  StockLedgersPublic,
  StatisticsSummaryPublic,
  StatisticsTimeSeriesPublic,
  StockMovesPublic,
  StockMovePublic,
  StockOutsPublic,
  StockOutPublic,
  SuppliersPublic,
  WarehousesPublic,
  WarehousePublic,
} from '#/modules/erp/api/generated';

import { requestClient } from '#/api/request';

export type ProductRecord = ProductPublic;
export type ProductUnitRecord = ProductUnitPublic;
export type ProductCategoryRecord = ProductCategoryPublic;
export type WarehouseRecord = WarehousePublic;
export type CounterpartyRecord = CounterpartyPublic;
export type PurchaseOrderRecord = PurchaseOrderPublic;
export type PurchaseInRecord = PurchaseInPublic;
export type PurchaseReturnRecord = PurchaseReturnPublic;
export type SaleOrderRecord = SaleOrderPublic;
export type SaleOutRecord = SaleOutPublic;
export type SaleReturnRecord = SaleReturnPublic;
export type SettlementAccountRecord = SettlementAccountPublic;
export type FinancePaymentRecord = FinancePaymentPublic;
export type FinanceReceiptRecord = FinanceReceiptPublic;
export type DocumentActionLogRecord = DocumentActionLogsPublic['items'][number];
export type DocumentAttachmentRecord = DocumentAttachmentPublic;
export type StockBalanceRecord = StockBalancesPublic['items'][number];
export type StockLedgerRecord = StockLedgersPublic['items'][number];
export type ReconciliationRunRecord = ReconciliationRunPublic;
export type StatisticsSummaryRecord = StatisticsSummaryPublic;
export type StatisticsTimeSeriesRecord = StatisticsTimeSeriesPublic;
export type StockDocumentRecord =
  | StockCheckPublic
  | StockInPublic
  | StockMovePublic
  | StockOutPublic;

export interface ProductPayload {
  barcode?: null | string;
  category_id: string;
  code: string;
  is_active: boolean;
  name: string;
  min_sale_price: string;
  purchase_reference_price: string;
  remark?: null | string;
  sale_reference_price: string;
  specification?: null | string;
  unit_id: string;
  expiry_days: number;
  weight: string;
}

export interface ProductUnitPayload {
  code: string;
  is_active: boolean;
  name: string;
  symbol?: null | string;
}

export interface CounterpartyPayload {
  address?: null | string;
  bank_account?: null | string;
  bank_name?: null | string;
  contact_name?: null | string;
  email?: null | string;
  fax?: null | string;
  is_active: boolean;
  mobile?: null | string;
  name: string;
  phone?: null | string;
  remark?: null | string;
  sort: number;
  tax_no?: null | string;
  tax_rate: string;
}

export interface ProductCategoryPayload {
  code: string;
  is_active: boolean;
  name: string;
  parent_id?: null | string;
  sort: number;
}

export interface WarehousePayload {
  address?: null | string;
  code: string;
  contact_name?: null | string;
  contact_phone?: null | string;
  is_active: boolean;
  is_default: boolean;
  name: string;
  remark?: null | string;
  sort: number;
  storage_fee_reference: string;
  transport_fee_reference: string;
}

export interface StockLinePayload {
  product_id: string;
  quantity?: string;
  reference_price?: string;
  warehouse_id?: string;
  actual_quantity?: string;
  from_warehouse_id?: string;
  to_warehouse_id?: string;
  remark?: string;
}

export interface StockDocumentPayload {
  business_at?: string;
  customer_id?: string;
  items: StockLinePayload[];
  remark?: string;
  supplier_id?: string;
}

export interface PurchaseOrderPayload {
  business_at?: string;
  discount_amount?: string;
  discount_rate?: string;
  deposit_amount?: string;
  items: Array<{
    product_id: string;
    quantity: string;
    remark?: string;
    tax_rate?: string;
    unit_price: string;
  }>;
  remark?: string;
  settlement_account_id?: string;
  supplier_id: string;
}

export interface SaleOrderPayload extends Omit<
  PurchaseOrderPayload,
  'supplier_id'
> {
  customer_id: string;
}

export interface SaleOutPayload {
  business_at?: string;
  discount_amount?: string;
  discount_rate?: string;
  items: Array<{
    quantity: string;
    sale_order_item_id: string;
    warehouse_id: string;
  }>;
  sale_order_id: string;
  other_deduction?: string;
  remark?: string;
  settlement_account_id?: string;
}

export interface SaleReturnPayload {
  business_at?: string;
  discount_amount?: string;
  discount_rate?: string;
  items: Array<{
    quantity: string;
    sale_out_item_id: string;
  }>;
  sale_out_id: string;
  other_deduction?: string;
  remark?: string;
  settlement_account_id?: string;
}

export interface SettlementAccountPayload {
  account_no?: string;
  is_active: boolean;
  is_default: boolean;
  name: string;
  remark?: string;
  sort: number;
}

export interface SettlementLinePayload {
  settlement_amount: string;
  source_document_id: string;
  source_type: string;
}

export interface FinancePaymentPayload {
  discount_amount?: string;
  items: SettlementLinePayload[];
  settlement_account_id: string;
  supplier_id: string;
}

export interface FinanceReceiptPayload {
  customer_id: string;
  discount_amount?: string;
  items: SettlementLinePayload[];
  settlement_account_id: string;
}

export interface PurchaseInPayload {
  business_at?: string;
  discount_amount?: string;
  discount_rate?: string;
  items: Array<{
    purchase_order_item_id: string;
    quantity: string;
    warehouse_id: string;
  }>;
  purchase_order_id: string;
  other_fee?: string;
  remark?: string;
  settlement_account_id?: string;
}

export interface PurchaseReturnPayload {
  business_at?: string;
  discount_amount?: string;
  discount_rate?: string;
  items: Array<{
    purchase_in_item_id: string;
    quantity: string;
  }>;
  purchase_in_id: string;
  other_fee?: string;
  remark?: string;
  settlement_account_id?: string;
}

export interface PageParams {
  page?: number;
  page_size?: number;
}

export interface DocumentQuery extends PageParams {
  business_from?: string;
  business_to?: string;
  customer_id?: string;
  keyword?: string;
  owner_id?: string;
  product_id?: string;
  remark?: string;
  receipt_status?: 'completed' | 'none' | 'partial';
  return_status?: 'completed' | 'none' | 'partial';
  status?: string;
  supplier_id?: string;
  warehouse_id?: string;
}

export interface ActionLogQuery extends PageParams {
  action?: string;
  resource_id?: string;
  resource_type?: string;
}

export interface ProductQuery extends PageParams {
  keyword?: string;
}

export interface CounterpartyQuery extends PageParams {
  keyword?: string;
  mobile?: string;
  name?: string;
  phone?: string;
}

export interface StockQuery extends PageParams {
  category_id?: string;
  ledger_type?: string;
  occurred_from?: string;
  occurred_to?: string;
  product_id?: string;
  source_document_no?: string;
  warehouse_id?: string;
}

export function listProductsApi(params: ProductQuery) {
  return requestClient.get<ProductsPublic>('/erp/products', { params });
}

export function listProductUnitsApi(params: ProductQuery) {
  return requestClient.get<ProductUnitsPublic>('/erp/product-units', {
    params,
  });
}

export function listProductCategoriesApi(params: ProductQuery) {
  return requestClient.get<ProductCategoriesPublic>('/erp/product-categories', {
    params,
  });
}

export function listWarehousesApi(params: ProductQuery) {
  return requestClient.get<WarehousesPublic>('/erp/warehouses', { params });
}

export function createProductApi(
  payload: ProductPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<ProductPublic>(
    '/erp/products',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateProductApi(id: string, payload: ProductPayload) {
  return requestClient.request<ProductPublic>(`/erp/products/${id}`, {
    data: payload,
    method: 'PATCH',
  });
}

export function deleteProductApi(id: string) {
  return requestClient.delete<void>(`/erp/products/${id}`);
}

type MasterDataKind = 'category' | 'unit' | 'warehouse';

const masterDataPaths: Record<MasterDataKind, string> = {
  category: 'product-categories',
  unit: 'product-units',
  warehouse: 'warehouses',
};

export function createMasterDataApi(
  kind: MasterDataKind,
  payload: ProductCategoryPayload | ProductUnitPayload | WarehousePayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<
    ProductCategoryPublic | ProductUnitPublic | WarehousePublic
  >(`/erp/${masterDataPaths[kind]}`, payload, idempotencyHeaders(idempotencyKey));
}

export function updateMasterDataApi(
  kind: MasterDataKind,
  id: string,
  payload: ProductCategoryPayload | ProductUnitPayload | WarehousePayload,
) {
  return requestClient.request<
    ProductCategoryPublic | ProductUnitPublic | WarehousePublic
  >(`/erp/${masterDataPaths[kind]}/${id}`, {
    data: payload,
    method: 'PATCH',
  });
}

export function deleteMasterDataApi(kind: MasterDataKind, id: string) {
  return requestClient.delete<void>(`/erp/${masterDataPaths[kind]}/${id}`);
}

export function listMasterDataApi(kind: MasterDataKind, params: ProductQuery) {
  return requestClient.get<
    ProductCategoriesPublic | ProductUnitsPublic | WarehousesPublic
  >(`/erp/${masterDataPaths[kind]}`, { params });
}

type CounterpartyKind = 'customer' | 'supplier';

const counterpartyPaths: Record<CounterpartyKind, string> = {
  customer: 'customers',
  supplier: 'suppliers',
};

export function listCounterpartiesApi(
  kind: CounterpartyKind,
  params: CounterpartyQuery,
) {
  return requestClient.get<CustomersPublic | SuppliersPublic>(
    `/erp/${counterpartyPaths[kind]}`,
    { params },
  );
}

export function createCounterpartyApi(
  kind: CounterpartyKind,
  payload: CounterpartyPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<CounterpartyPublic>(
    `/erp/${counterpartyPaths[kind]}`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateCounterpartyApi(
  kind: CounterpartyKind,
  id: string,
  payload: CounterpartyPayload,
) {
  return requestClient.request<CounterpartyPublic>(
    `/erp/${counterpartyPaths[kind]}/${id}`,
    { data: payload, method: 'PATCH' },
  );
}

export function deleteCounterpartyApi(kind: CounterpartyKind, id: string) {
  return requestClient.delete<void>(`/erp/${counterpartyPaths[kind]}/${id}`);
}

export function listPurchaseOrdersApi(params: DocumentQuery) {
  return requestClient.get<PurchaseOrdersPublic>('/erp/purchase-orders', {
    params,
  });
}

export function getPurchaseOrderApi(id: string) {
  return requestClient.get<PurchaseOrderPublic>(`/erp/purchase-orders/${id}`);
}

export function createPurchaseOrderApi(
  payload: PurchaseOrderPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseOrderPublic>(
    '/erp/purchase-orders',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updatePurchaseOrderApi(
  id: string,
  payload: PurchaseOrderPayload,
  expectedVersion: number,
) {
  return requestClient.request<PurchaseOrderPublic>(
    `/erp/purchase-orders/${id}`,
    {
      data: { ...payload, expected_version: expectedVersion },
      method: 'PATCH',
    },
  );
}

export function deletePurchaseOrderApi(id: string) {
  return requestClient.delete<void>(`/erp/purchase-orders/${id}`);
}

export function approvePurchaseOrderApi(
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseOrderPublic>(
    `/erp/purchase-orders/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reversePurchaseOrderApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseOrderPublic>(
    `/erp/purchase-orders/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listPurchaseInsApi(params: DocumentQuery) {
  return requestClient.get<PurchaseInsPublic>('/erp/purchase-ins', { params });
}

export function getPurchaseInApi(id: string) {
  return requestClient.get<PurchaseInPublic>(`/erp/purchase-ins/${id}`);
}

export function createPurchaseInApi(
  payload: PurchaseInPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseInPublic>(
    '/erp/purchase-ins',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updatePurchaseInApi(id: string, payload: PurchaseInPayload, expectedVersion: number) {
  return requestClient.request<PurchaseInPublic>(`/erp/purchase-ins/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deletePurchaseInApi(id: string) { return requestClient.delete<void>(`/erp/purchase-ins/${id}`); }

export function approvePurchaseInApi(
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseInPublic>(
    `/erp/purchase-ins/${id}/approve`,
    {
      expected_version: expectedVersion,
    },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reversePurchaseInApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseInPublic>(
    `/erp/purchase-ins/${id}/reverse`,
    {
      expected_version: expectedVersion,
      reason,
    },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listPurchaseReturnsApi(params: DocumentQuery) {
  return requestClient.get<PurchaseReturnsPublic>('/erp/purchase-returns', {
    params,
  });
}

export function createPurchaseReturnApi(
  payload: PurchaseReturnPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseReturnPublic>(
    '/erp/purchase-returns',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updatePurchaseReturnApi(id: string, payload: PurchaseReturnPayload, expectedVersion: number) {
  return requestClient.request<PurchaseReturnPublic>(`/erp/purchase-returns/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deletePurchaseReturnApi(id: string) { return requestClient.delete<void>(`/erp/purchase-returns/${id}`); }

export function approvePurchaseReturnApi(
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseReturnPublic>(
    `/erp/purchase-returns/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reversePurchaseReturnApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<PurchaseReturnPublic>(
    `/erp/purchase-returns/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listSaleOrdersApi(params: DocumentQuery) {
  return requestClient.get<SaleOrdersPublic>('/erp/sale-orders', { params });
}

export function getSaleOrderApi(id: string) {
  return requestClient.get<SaleOrderPublic>(`/erp/sale-orders/${id}`);
}

export function createSaleOrderApi(
  payload: SaleOrderPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleOrderPublic>(
    '/erp/sale-orders',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateSaleOrderApi(
  id: string,
  payload: SaleOrderPayload,
  expectedVersion: number,
) {
  return requestClient.request<SaleOrderPublic>(`/erp/sale-orders/${id}`, {
    data: { ...payload, expected_version: expectedVersion },
    method: 'PATCH',
  });
}

export function deleteSaleOrderApi(id: string) {
  return requestClient.delete<void>(`/erp/sale-orders/${id}`);
}

export function approveSaleOrderApi(
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleOrderPublic>(
    `/erp/sale-orders/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reverseSaleOrderApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleOrderPublic>(
    `/erp/sale-orders/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listSaleOutsApi(params: DocumentQuery) {
  return requestClient.get<SaleOutsPublic>('/erp/sale-outs', { params });
}

export function getSaleOutApi(id: string) {
  return requestClient.get<SaleOutPublic>(`/erp/sale-outs/${id}`);
}

export function createSaleOutApi(
  payload: SaleOutPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleOutPublic>(
    '/erp/sale-outs',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateSaleOutApi(id: string, payload: SaleOutPayload, expectedVersion: number) {
  return requestClient.request<SaleOutPublic>(`/erp/sale-outs/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deleteSaleOutApi(id: string) { return requestClient.delete<void>(`/erp/sale-outs/${id}`); }

export function approveSaleOutApi(
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleOutPublic>(
    `/erp/sale-outs/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reverseSaleOutApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleOutPublic>(
    `/erp/sale-outs/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listSaleReturnsApi(params: DocumentQuery) {
  return requestClient.get<SaleReturnsPublic>('/erp/sale-returns', { params });
}

export function createSaleReturnApi(
  payload: SaleReturnPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleReturnPublic>(
    '/erp/sale-returns',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateSaleReturnApi(id: string, payload: SaleReturnPayload, expectedVersion: number) {
  return requestClient.request<SaleReturnPublic>(`/erp/sale-returns/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deleteSaleReturnApi(id: string) { return requestClient.delete<void>(`/erp/sale-returns/${id}`); }

export function approveSaleReturnApi(
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleReturnPublic>(
    `/erp/sale-returns/${id}/approve`,
    {
      expected_version: expectedVersion,
    },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reverseSaleReturnApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SaleReturnPublic>(
    `/erp/sale-returns/${id}/reverse`,
    {
      expected_version: expectedVersion,
      reason,
    },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listSettlementAccountsApi(params: ProductQuery) {
  return requestClient.get<SettlementAccountsPublic>(
    '/erp/settlement-accounts',
    {
      params,
    },
  );
}

export function listDocumentActionLogsApi(params: ActionLogQuery) {
  return requestClient.get<DocumentActionLogsPublic>('/erp/action-logs', {
    params,
  });
}

export function listDocumentAttachmentsApi(
  documentType: string,
  documentId: string,
) {
  return requestClient.get<DocumentAttachmentsPublic>(
    `/erp/documents/${documentType}/${documentId}/attachments`,
  );
}

export function createDocumentAttachmentApi(
  documentType: string,
  documentId: string,
  fileId: string,
  sort: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<DocumentAttachmentPublic>(
    `/erp/documents/${documentType}/${documentId}/attachments`,
    { file_id: fileId, sort },
    idempotencyHeaders(idempotencyKey),
  );
}

export function deleteDocumentAttachmentApi(
  documentType: string,
  documentId: string,
  attachmentId: string,
) {
  return requestClient.delete<void>(
    `/erp/documents/${documentType}/${documentId}/attachments/${attachmentId}`,
  );
}

export function listWarehouseUsersApi(warehouseId: string) {
  return requestClient.get<{
    items: Array<{ user_id: string; full_name?: string; email: string }>;
  }>(`/erp/warehouses/${warehouseId}/users`);
}

export function replaceWarehouseUsersApi(
  warehouseId: string,
  userIds: string[],
) {
  return requestClient.put(`/erp/warehouses/${warehouseId}/users`, {
    user_ids: userIds,
  });
}

export function createSettlementAccountApi(
  payload: SettlementAccountPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<SettlementAccountPublic>(
    '/erp/settlement-accounts',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateSettlementAccountApi(
  id: string,
  payload: SettlementAccountPayload,
) {
  return requestClient.request<SettlementAccountPublic>(
    `/erp/settlement-accounts/${id}`,
    { data: payload, method: 'PATCH' },
  );
}

export function deleteSettlementAccountApi(id: string) {
  return requestClient.delete<void>(`/erp/settlement-accounts/${id}`);
}

export function listFinancePaymentsApi(params: DocumentQuery) {
  return requestClient.get<FinancePaymentsPublic>('/erp/finance-payments', {
    params,
  });
}

function createIdempotencyKey() {
  return crypto.randomUUID();
}

function idempotencyHeaders(idempotencyKey: string) {
  return { headers: { 'Idempotency-Key': idempotencyKey } };
}

export function createFinancePaymentApi(
  payload: FinancePaymentPayload,
  idempotencyKey: string,
) {
  return requestClient.post<FinancePaymentPublic>(
    '/erp/finance-payments',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateFinancePaymentApi(id: string, payload: FinancePaymentPayload, expectedVersion: number) {
  return requestClient.request<FinancePaymentPublic>(`/erp/finance-payments/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deleteFinancePaymentApi(id: string) { return requestClient.delete<void>(`/erp/finance-payments/${id}`); }

export function approveFinancePaymentApi(
  id: string,
  expectedVersion: number,
  idempotencyKey: string,
) {
  return requestClient.post<FinancePaymentPublic>(
    `/erp/finance-payments/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reverseFinancePaymentApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey: string,
) {
  return requestClient.post<FinancePaymentPublic>(
    `/erp/finance-payments/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listFinanceReceiptsApi(params: DocumentQuery) {
  return requestClient.get<FinanceReceiptsPublic>('/erp/finance-receipts', {
    params,
  });
}

export function createFinanceReceiptApi(
  payload: FinanceReceiptPayload,
  idempotencyKey: string,
) {
  return requestClient.post<FinanceReceiptPublic>(
    '/erp/finance-receipts',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateFinanceReceiptApi(id: string, payload: FinanceReceiptPayload, expectedVersion: number) {
  return requestClient.request<FinanceReceiptPublic>(`/erp/finance-receipts/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deleteFinanceReceiptApi(id: string) { return requestClient.delete<void>(`/erp/finance-receipts/${id}`); }

export function approveFinanceReceiptApi(
  id: string,
  expectedVersion: number,
  idempotencyKey: string,
) {
  return requestClient.post<FinanceReceiptPublic>(
    `/erp/finance-receipts/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reverseFinanceReceiptApi(
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey: string,
) {
  return requestClient.post<FinanceReceiptPublic>(
    `/erp/finance-receipts/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}

export function listStockBalancesApi(params: StockQuery) {
  return requestClient.get<StockBalancesPublic>('/erp/stock-balances', {
    params,
  });
}

export const stockBalancesExportPath = '/erp/stock-balances/export';

export function listStockRecordsApi(params: StockQuery) {
  return requestClient.get<StockLedgersPublic>('/erp/stock-records', {
    params,
  });
}

export const stockRecordsExportPath = '/erp/stock-records/export';

export const erpExportPaths = {
  account: '/erp/settlement-accounts/export',
  customer: '/erp/customers/export',
  'finance-payment': '/erp/finance-payments/export',
  'finance-receipt': '/erp/finance-receipts/export',
  product: '/erp/products/export',
  'product-category': '/erp/product-categories/export',
  'product-unit': '/erp/product-units/export',
  'purchase-in': '/erp/purchase-ins/export',
  'purchase-order': '/erp/purchase-orders/export',
  'purchase-return': '/erp/purchase-returns/export',
  'sale-order': '/erp/sale-orders/export',
  'sale-out': '/erp/sale-outs/export',
  'sale-return': '/erp/sale-returns/export',
  'stock-check': '/erp/stock-checks/export',
  'stock-in': '/erp/stock-ins/export',
  'stock-move': '/erp/stock-moves/export',
  'stock-out': '/erp/stock-outs/export',
  supplier: '/erp/suppliers/export',
  warehouse: '/erp/warehouses/export',
} as const;

export type ErpExportResource = keyof typeof erpExportPaths;

export function getStatisticsSummaryApi() {
  return requestClient.get<StatisticsSummaryPublic>('/erp/statistics/summary');
}

export function getStatisticsTimeSeriesApi(params: {
  end: string;
  granularity?: 'day' | 'month';
  start: string;
  type: 'purchase' | 'sale';
}) {
  return requestClient.get<StatisticsTimeSeriesPublic>(
    '/erp/statistics/time-series',
    {
      params,
    },
  );
}

export function getLatestReconciliationRunApi() {
  return requestClient.get<null | ReconciliationRunPublic>(
    '/erp/reconciliation-runs/latest',
  );
}

export function runReconciliationApi(idempotencyKey: string) {
  return requestClient.post<ReconciliationRunPublic>(
    '/erp/reconciliation-runs',
    undefined,
    idempotencyHeaders(idempotencyKey),
  );
}

type StockDocumentKind = 'check' | 'in' | 'move' | 'out';

const documentPaths: Record<StockDocumentKind, string> = {
  check: 'stock-checks',
  in: 'stock-ins',
  move: 'stock-moves',
  out: 'stock-outs',
};

export function listStockDocumentsApi(
  kind: StockDocumentKind,
  params: DocumentQuery,
) {
  return requestClient.get<
    StockChecksPublic | StockInsPublic | StockMovesPublic | StockOutsPublic
  >(`/erp/${documentPaths[kind]}`, { params });
}

export function createStockDocumentApi(
  kind: StockDocumentKind,
  payload: StockDocumentPayload,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<StockDocumentRecord>(
    `/erp/${documentPaths[kind]}`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export function updateStockDocumentApi(kind: StockDocumentKind, id: string, payload: StockDocumentPayload, expectedVersion: number) {
  return requestClient.request<StockDocumentRecord>(`/erp/${documentPaths[kind]}/${id}`, { data: { ...payload, expected_version: expectedVersion }, method: 'PATCH' });
}

export function deleteStockDocumentApi(kind: StockDocumentKind, id: string) {
  return requestClient.delete<void>(`/erp/${documentPaths[kind]}/${id}`);
}

export function approveStockDocumentApi(
  kind: StockDocumentKind,
  id: string,
  expectedVersion: number,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<StockDocumentRecord>(
    `/erp/${documentPaths[kind]}/${id}/approve`,
    { expected_version: expectedVersion },
    idempotencyHeaders(idempotencyKey),
  );
}

export function reverseStockDocumentApi(
  kind: StockDocumentKind,
  id: string,
  expectedVersion: number,
  reason: string,
  idempotencyKey = createIdempotencyKey(),
) {
  return requestClient.post<StockDocumentRecord>(
    `/erp/${documentPaths[kind]}/${id}/reverse`,
    { expected_version: expectedVersion, reason },
    idempotencyHeaders(idempotencyKey),
  );
}
