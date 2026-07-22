import type { VbenFormSchema } from '#/adapter/form';
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserRecord } from '#/api';
import type {
  CounterpartyRecord,
  ProductRecord,
  SettlementAccountRecord,
} from '#/modules/erp/api/erp';

import { z } from '#/adapter/form';
import { listUsersApi } from '#/api';
import {
  listCounterpartiesApi,
  listProductsApi,
  listSettlementAccountsApi,
} from '#/modules/erp/api/erp';

export interface PurchaseOrderLineForm {
  id?: string;
  product_amount?: number;
  product_barcode?: string;
  product_id?: string;
  product_name?: string;
  quantity?: number;
  received_quantity?: number;
  remark?: string;
  returned_quantity?: number;
  row_key: string;
  stock_quantity?: number;
  tax_amount?: number;
  tax_rate?: number;
  total_amount?: number;
  unit_name?: string;
  unit_price?: number;
}

async function getSupplierOptions(): Promise<CounterpartyRecord[]> {
  const result = await listCounterpartiesApi('supplier', {
    page: 1,
    page_size: 200,
  });
  return result.items.filter((item) => item.is_active);
}

async function getProductOptions(): Promise<ProductRecord[]> {
  const result = await listProductsApi({ page: 1, page_size: 200 });
  return result.items.filter((item) => item.is_active);
}

async function getAccountOptions(): Promise<SettlementAccountRecord[]> {
  const result = await listSettlementAccountsApi({ page: 1, page_size: 200 });
  return result.items.filter((item) => item.is_active);
}

async function getOwnerOptions(): Promise<UserRecord[]> {
  const result = await listUsersApi({
    is_active: true,
    page: 1,
    page_size: 200,
  });
  return result.items;
}

export function useOrderFormSchema(
  formType: 'create' | 'detail' | 'edit',
): VbenFormSchema[] {
  const detail = formType === 'detail';
  return [
    {
      component: 'Input',
      componentProps: {
        disabled: true,
        placeholder: '保存后自动生成',
      },
      fieldName: 'no',
      label: '订单单号',
    },
    {
      component: 'DatePicker',
      componentProps: {
        class: 'w-full',
        format: 'YYYY-MM-DD HH:mm:ss',
        placeholder: '请选择订单时间',
        showTime: true,
        valueFormat: 'YYYY-MM-DDTHH:mm:ss',
      },
      fieldName: 'business_at',
      label: '订单时间',
      rules: 'required',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: getSupplierOptions,
        class: 'w-full',
        labelField: 'name',
        placeholder: '请选择供应商',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'supplier_id',
      label: '供应商',
      rules: 'required',
    },
    {
      component: 'Textarea',
      componentProps: {
        autoSize: { maxRows: 1, minRows: 1 },
        disabled: detail,
        maxlength: 500,
        placeholder: '请输入备注',
      },
      fieldName: 'remark',
      formItemClass: 'col-span-2',
      label: '备注',
    },
    {
      component: 'Input',
      fieldName: 'attachments',
      formItemClass: 'col-span-3',
      label: '附件',
    },
    {
      component: 'Input',
      fieldName: 'items',
      formItemClass: 'col-span-3',
      label: '采购产品清单',
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        max: 100,
        min: 0,
        placeholder: '请输入优惠率',
        precision: 2,
      },
      fieldName: 'discount_rate',
      label: '优惠率(%)',
      rules: z.number().min(0).max(100).optional(),
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        disabled: true,
        precision: 2,
      },
      fieldName: 'discount_amount',
      label: '付款优惠',
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        disabled: true,
        precision: 2,
      },
      fieldName: 'total_amount',
      label: '优惠后金额',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: getAccountOptions,
        class: 'w-full',
        labelField: 'name',
        placeholder: '请选择结算账户',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'settlement_account_id',
      label: '结算账户',
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        min: 0,
        placeholder: '请输入支付订金',
        precision: 2,
      },
      fieldName: 'deposit_amount',
      label: '支付订金',
      rules: z.number().min(0).optional(),
    },
  ];
}

export function useOrderItemColumns(
  disabled: boolean,
): VxeTableGridOptions<PurchaseOrderLineForm>['columns'] {
  return [
    { fixed: 'left', minWidth: 50, title: '序号', type: 'seq' },
    {
      field: 'product_id',
      minWidth: 200,
      slots: { default: 'productId' },
      title: '产品名称',
    },
    { field: 'stock_quantity', minWidth: 80, title: '库存' },
    { field: 'product_barcode', minWidth: 120, title: '条码' },
    { field: 'unit_name', minWidth: 80, title: '单位' },
    {
      field: 'remark',
      minWidth: 150,
      slots: { default: 'remark' },
      title: '备注',
    },
    {
      field: 'quantity',
      fixed: 'right',
      minWidth: 120,
      slots: { default: 'quantity' },
      title: '数量',
    },
    {
      field: 'unit_price',
      fixed: 'right',
      minWidth: 120,
      slots: { default: 'unitPrice' },
      title: '产品单价',
    },
    {
      field: 'product_amount',
      fixed: 'right',
      minWidth: 120,
      slots: { default: 'productAmount' },
      title: '金额',
    },
    {
      field: 'tax_rate',
      fixed: 'right',
      minWidth: 105,
      slots: { default: 'taxRate' },
      title: '税率(%)',
    },
    {
      field: 'tax_amount',
      fixed: 'right',
      minWidth: 120,
      slots: { default: 'taxAmount' },
      title: '税额',
    },
    {
      field: 'total_amount',
      fixed: 'right',
      minWidth: 120,
      slots: { default: 'totalAmount' },
      title: '税额合计',
    },
    {
      fixed: 'right',
      slots: { default: 'actions' },
      title: '操作',
      visible: !disabled,
      width: 60,
    },
  ];
}

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: { allowClear: true, placeholder: '请输入订单单号' },
      fieldName: 'keyword',
      label: '订单单号',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: getProductOptions,
        class: 'w-full',
        labelField: 'name',
        placeholder: '请选择产品名称',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'product_id',
      label: '产品名称',
    },
    {
      component: 'RangePicker',
      componentProps: {
        allowClear: true,
        class: 'w-full',
        format: 'YYYY-MM-DD HH:mm:ss',
        placeholder: ['开始时间', '结束时间'],
        showTime: true,
        valueFormat: 'YYYY-MM-DDTHH:mm:ss',
      },
      fieldName: 'order_time',
      label: '订单时间',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: getSupplierOptions,
        class: 'w-full',
        labelField: 'name',
        placeholder: '请选择供应商',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'supplier_id',
      label: '供应商',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: getOwnerOptions,
        class: 'w-full',
        labelField: 'full_name',
        placeholder: '请选择创建人',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'owner_id',
      label: '创建人',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: '草稿', value: 'draft' },
          { label: '已审核', value: 'approved' },
        ],
        placeholder: '请选择审批状态',
      },
      fieldName: 'status',
      label: '审批状态',
    },
    {
      component: 'Input',
      componentProps: { allowClear: true, placeholder: '请输入备注' },
      fieldName: 'remark',
      label: '备注',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: '未入库', value: 'none' },
          { label: '部分入库', value: 'partial' },
          { label: '全部入库', value: 'completed' },
        ],
        placeholder: '请选择入库状态',
      },
      fieldName: 'receipt_status',
      label: '入库状态',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: '未退货', value: 'none' },
          { label: '部分退货', value: 'partial' },
          { label: '全部退货', value: 'completed' },
        ],
        placeholder: '请选择退货状态',
      },
      fieldName: 'return_status',
      label: '退货状态',
    },
  ];
}

export function useGridColumns(): VxeTableGridOptions['columns'] {
  return [
    { fixed: 'left', type: 'checkbox', width: 50 },
    { field: 'no', fixed: 'left', title: '订单单号', width: 200 },
    {
      field: 'product_names',
      minWidth: 120,
      showOverflow: 'tooltip',
      slots: { default: 'productNames' },
      title: '产品名称',
    },
    { field: 'supplier_name', minWidth: 120, title: '供应商' },
    {
      field: 'business_at',
      slots: { default: 'businessAt' },
      title: '订单时间',
      width: 160,
    },
    {
      field: 'owner_id',
      minWidth: 120,
      slots: { default: 'ownerName' },
      title: '创建人',
    },
    {
      field: 'total_quantity',
      minWidth: 120,
      slots: { default: 'totalQuantity' },
      title: '总数量',
    },
    {
      field: 'received_quantity',
      minWidth: 120,
      slots: { default: 'receivedQuantity' },
      title: '入库数量',
    },
    {
      field: 'returned_quantity',
      minWidth: 120,
      slots: { default: 'returnedQuantity' },
      title: '退货数量',
    },
    {
      field: 'product_amount',
      minWidth: 120,
      slots: { default: 'productAmount' },
      title: '金额合计',
    },
    {
      field: 'total_amount',
      minWidth: 120,
      slots: { default: 'totalAmount' },
      title: '含税金额',
    },
    {
      field: 'deposit_amount',
      minWidth: 120,
      slots: { default: 'depositAmount' },
      title: '支付订金',
    },
    {
      field: 'status',
      minWidth: 120,
      slots: { default: 'status' },
      title: '审批状态',
    },
    {
      fixed: 'right',
      slots: { default: 'actions' },
      title: '操作',
      width: 320,
    },
  ];
}
