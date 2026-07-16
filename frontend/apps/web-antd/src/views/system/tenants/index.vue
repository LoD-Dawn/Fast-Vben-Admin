<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { TenantRecord } from '#/api';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';

import { Button, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  archiveTenantApi,
  listTenantsApi,
  notifyTenantMembershipsChanged,
  operateTenantLifecycleApi,
  syncTenantMenusApi,
} from '#/api';
import { $t } from '#/locales';

import { buildKeyword, confirmAction } from '../shared/utils';
import { useColumns, useGridFormSchema } from './data';
import Form from './modules/form.vue';
import Lifecycle from './modules/lifecycle.vue';
import Overview from './modules/overview.vue';

const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

const [LifecycleDrawer, lifecycleDrawerApi] = useVbenDrawer({
  connectedComponent: Lifecycle,
  destroyOnClose: true,
});

const [OverviewDrawer, overviewDrawerApi] = useVbenDrawer({
  connectedComponent: Overview,
  destroyOnClose: true,
});

function onActionClick({ code, row }: OnActionClickParams<TenantRecord>) {
  switch (code) {
    case 'archive': {
      void onArchive(row);
      break;
    }
    case 'convert': {
      void onSimpleLifecycleAction(row, 'convert_to_formal');
      break;
    }
    case 'edit': {
      formDrawerApi.setData(row).open();
      break;
    }
    case 'freeze':
    case 'renew': {
      lifecycleDrawerApi.setData({ action: code, tenant: row }).open();
      break;
    }
    case 'overview': {
      overviewDrawerApi.setData(row).open();
      break;
    }
    case 'sync-menu': {
      void onSyncMenu(row);
      break;
    }
    case 'unfreeze': {
      void onSimpleLifecycleAction(row, 'unfreeze');
      break;
    }
  }
}

async function onSimpleLifecycleAction(
  row: TenantRecord,
  action: 'convert_to_formal' | 'unfreeze',
) {
  const actionText =
    action === 'convert_to_formal'
      ? $t('system.tenant.convertFormal')
      : $t('system.tenant.unfreeze');
  try {
    await confirmAction(
      $t('system.tenant.lifecycleConfirm', [row.name, actionText]),
      actionText,
    );
    await operateTenantLifecycleApi(row.id, { action });
    message.success($t('system.common.success'));
    onRefresh();
  } catch {
    // Cancellation and request errors are handled by the shared UI layer.
  }
}

async function onSyncMenu(row: TenantRecord) {
  try {
    await confirmAction(
      $t('system.tenant.syncMenuConfirm', [row.name]),
      $t('system.tenant.syncMenu'),
    );
    const result = await syncTenantMenusApi(row.id);
    message.success(
      $t('system.tenant.syncResult', [
        result.success_count ?? 0,
        result.failed_count ?? 0,
        result.skipped_count ?? 0,
      ]),
    );
  } catch {
    // Cancellation and request errors are handled by the shared UI layer.
  }
}

async function onArchive(row: TenantRecord) {
  try {
    await confirmAction(
      `停用后该租户的现有会话将立即失效，确认停用 ${row.name} 吗？`,
      '确认停用租户',
    );
    await archiveTenantApi(row.id);
    notifyTenantMembershipsChanged();
    message.success(`${row.name} 已停用`);
    onRefresh();
  } catch {
    // Cancellation and request errors are handled by the shared UI layer.
  }
}

const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useGridFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await listTenantsApi({
            customer_source: buildKeyword(formValues.customer_source),
            expiring_in_days: formValues.expiring_in_days,
            industry: formValues.industry,
            initialization_template_id: formValues.initialization_template_id,
            keyword: buildKeyword(formValues.keyword),
            lifecycle_status: formValues.lifecycle_status,
            owner_name: buildKeyword(formValues.owner_name),
            page: page.currentPage,
            page_size: page.pageSize,
            plan_id: formValues.plan_id,
          });
        },
      },
    },
    rowConfig: {
      keyField: 'id',
    },
    toolbarConfig: {
      custom: true,
      export: false,
      refresh: true,
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<TenantRecord>,
});

function onRefresh() {
  notifyTenantMembershipsChanged();
  gridApi.query();
}

function onCreate() {
  formDrawerApi.setData(undefined).open();
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="onRefresh" />
    <LifecycleDrawer @success="onRefresh" />
    <OverviewDrawer />
    <Grid :table-title="$t('system.tenant.list')">
      <template #toolbar-tools>
        <Button
          v-access:code="'platform:tenant:create'"
          type="primary"
          @click="onCreate"
        >
          <Plus class="size-5" />
          {{ $t('system.tenant.create') }}
        </Button>
      </template>
    </Grid>
  </Page>
</template>
