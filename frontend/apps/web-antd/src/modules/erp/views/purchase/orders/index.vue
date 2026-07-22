<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { UserRecord } from '#/api';
import type {
  DocumentQuery,
  PurchaseOrderRecord,
} from '#/modules/erp/api/erp';

import { computed, onMounted, ref } from 'vue';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { IconifyIcon, Plus } from '@vben/icons';

import { Button, message, Popconfirm, Tag } from 'ant-design-vue';

import { useVbenVxeGrid, VbenTableAction } from '#/adapter/vxe-table';
import { listUsersApi } from '#/api';
import ExportCsvButton from '#/modules/erp/components/export-csv-button.vue';
import ReverseDocumentDialog from '#/modules/erp/components/reverse-document-dialog.vue';
import {
  approvePurchaseOrderApi,
  deletePurchaseOrderApi,
  listPurchaseOrdersApi,
  reversePurchaseOrderApi,
} from '#/modules/erp/api/erp';

import { useGridColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';

defineOptions({ name: 'ErpPurchaseOrder' });

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const checkedRows = ref<PurchaseOrderRecord[]>([]);
const owners = ref<UserRecord[]>([]);
const reverseOpen = ref(false);
const reverseTarget = ref<PurchaseOrderRecord>();
const exportQuery = ref<Record<string, string | undefined>>({});

const canBatchDelete = computed(
  () =>
    checkedRows.value.length > 0 &&
    checkedRows.value.every((row) => row.status === 'draft'),
);

function normalizeDate(value: unknown) {
  if (!value) return undefined;
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toISOString();
}

function mapQuery(formValues: Record<string, unknown>): DocumentQuery {
  const { order_time: orderTime, ...values } = formValues;
  const range = Array.isArray(orderTime) ? orderTime : [];
  return {
    ...(values as DocumentQuery),
    business_from: normalizeDate(range[0]),
    business_to: normalizeDate(range[1]),
  };
}

function mapExportQuery(query: DocumentQuery) {
  return Object.fromEntries(
    Object.entries(query).filter(
      (entry): entry is [string, string] =>
        typeof entry[1] === 'string' && Boolean(entry[1]),
    ),
  );
}

function handleRefresh() {
  gridApi.query();
}

function handleCreate() {
  formDrawerApi.setData({ mode: 'create' }).open();
}

function handleEdit(row: PurchaseOrderRecord) {
  formDrawerApi
    .setData({ mode: 'edit', order: row, orderId: row.id })
    .open();
}

function handleDetail(row: PurchaseOrderRecord) {
  formDrawerApi
    .setData({ mode: 'detail', order: row, orderId: row.id })
    .open();
}

async function handleDelete(rows: PurchaseOrderRecord[]) {
  if (rows.some((row) => row.status !== 'draft')) {
    message.warning('仅草稿采购订单可以删除');
    return;
  }
  const hideLoading = message.loading({ content: '正在删除...', duration: 0 });
  try {
    for (const row of rows) await deletePurchaseOrderApi(row.id);
    checkedRows.value = [];
    message.success('删除成功');
    handleRefresh();
  } finally {
    hideLoading();
  }
}

async function handleApprove(row: PurchaseOrderRecord) {
  const hideLoading = message.loading({ content: '正在审批...', duration: 0 });
  try {
    await approvePurchaseOrderApi(row.id, row.version);
    message.success('审批成功');
    handleRefresh();
  } finally {
    hideLoading();
  }
}

function handleReverse(row: PurchaseOrderRecord) {
  reverseTarget.value = row;
  reverseOpen.value = true;
}

async function confirmReverse(reason: string) {
  const row = reverseTarget.value;
  if (!row) return;
  await reversePurchaseOrderApi(row.id, row.version, reason);
  message.success('反审批成功');
  handleRefresh();
}

function handleRowCheckboxChange({
  records,
}: {
  records: PurchaseOrderRecord[];
}) {
  checkedRows.value = records;
}

function productNames(row: PurchaseOrderRecord) {
  return row.items?.map((item) => item.product_name).join('、') || '-';
}

function ownerName(row: PurchaseOrderRecord) {
  const owner = owners.value.find((item) => item.id === row.owner_id);
  return owner?.full_name || owner?.email || row.owner_id || '-';
}

function formatDate(value?: null | string) {
  return value ? value.replace('T', ' ').slice(0, 19) : '-';
}

function formatQuantity(value?: null | number | string) {
  return Number(value ?? 0).toFixed(3);
}

function formatAmount(value?: null | number | string) {
  return Number(value ?? 0).toFixed(2);
}

function receivedQuantity(row: PurchaseOrderRecord) {
  return row.items?.reduce(
    (sum, item) => sum + Number(item.received_quantity),
    0,
  );
}

function returnedQuantity(row: PurchaseOrderRecord) {
  return row.items?.reduce(
    (sum, item) => sum + Number(item.returned_quantity),
    0,
  );
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
  },
  gridOptions: {
    columns: useGridColumns(),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const query = mapQuery(formValues);
          exportQuery.value = mapExportQuery(query);
          return await listPurchaseOrdersApi({
            ...query,
            page: page.currentPage,
            page_size: page.pageSize,
          });
        },
      },
    },
    rowConfig: {
      isHover: true,
      keyField: 'id',
    },
    toolbarConfig: {
      refresh: true,
      search: true,
    },
  } as VxeTableGridOptions<PurchaseOrderRecord>,
  gridEvents: {
    checkboxAll: handleRowCheckboxChange,
    checkboxChange: handleRowCheckboxChange,
  },
});

onMounted(async () => {
  try {
    const result = await listUsersApi({
      is_active: true,
      page: 1,
      page_size: 200,
    });
    owners.value = result.items;
  } catch {
    owners.value = [];
  }
});
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="handleRefresh" />
    <ReverseDocumentDialog
      v-model:open="reverseOpen"
      impact="反审批后，采购订单将恢复为草稿，不能再作为已审批采购依据。"
      :on-confirm="confirmReverse"
      title="反审批采购订单"
    />

    <Grid table-title="采购订单列表">
      <template #toolbar-tools>
        <div class="flex items-center gap-1">
          <Button
            v-access:code="'erp:purchase-order:create'"
            class="gap-1"
            type="primary"
            @click="handleCreate"
          >
            <Plus class="size-5" />
            <span>新增采购订单</span>
          </Button>
          <ExportCsvButton
            file-name="采购订单列表.csv"
            permission="erp:purchase-order:export"
            :query="exportQuery"
            resource="purchase-order"
          />
          <Popconfirm
            title="是否删除所选中数据？"
            @confirm="handleDelete(checkedRows)"
          >
            <Button
              v-access:code="'erp:purchase-order:delete'"
              :disabled="!canBatchDelete"
              class="gap-1"
              danger
            >
              <IconifyIcon class="size-4" icon="lucide:trash-2" />
              <span>批量删除</span>
            </Button>
          </Popconfirm>
        </div>
      </template>

      <template #productNames="{ row }">
        <span :title="productNames(row)">{{ productNames(row) }}</span>
      </template>
      <template #businessAt="{ row }">
        {{ formatDate(row.business_at) }}
      </template>
      <template #ownerName="{ row }">
        {{ ownerName(row) }}
      </template>
      <template #totalQuantity="{ row }">
        {{ formatQuantity(row.total_quantity) }}
      </template>
      <template #receivedQuantity="{ row }">
        {{ formatQuantity(receivedQuantity(row)) }}
      </template>
      <template #returnedQuantity="{ row }">
        {{ formatQuantity(returnedQuantity(row)) }}
      </template>
      <template #productAmount="{ row }">
        {{ formatAmount(row.product_amount) }}
      </template>
      <template #totalAmount="{ row }">
        {{ formatAmount(row.total_amount) }}
      </template>
      <template #depositAmount="{ row }">
        {{ formatAmount(row.deposit_amount) }}
      </template>
      <template #status="{ row }">
        <Tag :color="row.status === 'approved' ? 'success' : 'default'">
          {{ row.status === 'approved' ? '已审批' : '草稿' }}
        </Tag>
      </template>
      <template #actions="{ row }">
        <VbenTableAction
          :actions="[
            {
              auth: ['erp:purchase-order:list'],
              icon: 'lucide:eye',
              onClick: handleDetail.bind(null, row),
              text: '详情',
              variant: 'link',
            },
            {
              auth: ['erp:purchase-order:update'],
              icon: 'lucide:square-pen',
              ifShow: () => row.status === 'draft',
              onClick: handleEdit.bind(null, row),
              text: '编辑',
              variant: 'link',
            },
            {
              auth:
                row.status === 'draft'
                  ? ['erp:purchase-order:approve']
                  : ['erp:purchase-order:reverse'],
              icon: 'lucide:clipboard-check',
              onClick:
                row.status === 'draft'
                  ? undefined
                  : handleReverse.bind(null, row),
              popConfirm:
                row.status === 'draft'
                  ? {
                      cancelText: '取消',
                      confirm: handleApprove.bind(null, row),
                      okText: '确认',
                      title: '确认审批该订单吗？',
                    }
                  : undefined,
              text: row.status === 'draft' ? '审批' : '反审批',
              variant: 'link',
            },
            {
              auth: ['erp:purchase-order:delete'],
              danger: true,
              icon: 'lucide:trash-2',
              ifShow: () => row.status === 'draft',
              popConfirm: {
                cancelText: '取消',
                confirm: handleDelete.bind(null, [row]),
                okText: '确认',
                title: `确认删除采购订单 ${row.no} 吗？`,
              },
              text: '删除',
              variant: 'link',
            },
          ]"
        />
      </template>
    </Grid>
  </Page>
</template>
