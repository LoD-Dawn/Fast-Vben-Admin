<script lang="ts" setup>
import type { MenuRecord, TenantRecord, TenantUsageRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { Tree as ATree, Descriptions, DescriptionsItem } from 'ant-design-vue';

import { getTenantPlanMenusApi, getTenantUsageApi, listMenusApi } from '#/api';
import { $t } from '#/locales';

interface MenuTreeNode {
  children: MenuTreeNode[];
  key: string;
  title: string;
}

const tenant = ref<TenantRecord>();
const usage = ref<TenantUsageRecord>();
const menus = ref<MenuRecord[]>([]);
const checkedMenuIds = ref<string[]>([]);

function formatLimit(value?: null | number) {
  return value === null || value === undefined
    ? $t('system.tenantPlan.unlimited')
    : value.toLocaleString();
}

function formatBytes(value?: null | number) {
  if (value === null || value === undefined) {
    return $t('system.tenantPlan.unlimited');
  }
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  return `${(value / 1024 ** 3).toFixed(1)} GB`;
}

function formatMoney(value?: null | number) {
  return new Intl.NumberFormat(undefined, {
    currency: 'CNY',
    style: 'currency',
  }).format(value ?? 0);
}

function formatMenuTitle(title: string) {
  return title.startsWith('menu.') ? $t(title) : title;
}

function collectMenuKeys(nodes: MenuTreeNode[], parentsOnly = false) {
  const keys: string[] = [];
  for (const node of nodes) {
    if (!parentsOnly || node.children.length > 0) keys.push(node.key);
    keys.push(...collectMenuKeys(node.children, parentsOnly));
  }
  return keys;
}

const menuTreeData = computed(() => {
  const tenantMenus = menus.value.filter(
    (menu) => !menu.permission_code?.startsWith('platform:'),
  );
  const childrenMap = new Map<null | string, MenuRecord[]>();
  for (const menu of tenantMenus) {
    const parentId = menu.parent_id ?? null;
    const children = childrenMap.get(parentId) ?? [];
    children.push(menu);
    childrenMap.set(parentId, children);
  }

  function build(parentId: null | string): MenuTreeNode[] {
    return (childrenMap.get(parentId) ?? [])
      .toSorted((a, b) => (a.sort ?? 0) - (b.sort ?? 0))
      .map((menu) => ({
        children: build(menu.id),
        key: menu.id,
        title: formatMenuTitle(menu.title),
      }));
  }

  return build(null);
});

const expandedMenuIds = computed(() =>
  collectMenuKeys(menuTreeData.value, true),
);

const [Drawer, drawerApi] = useVbenDrawer({
  showConfirmButton: false,
  async onOpenChange(isOpen) {
    if (!isOpen) return;
    tenant.value = drawerApi.getData<TenantRecord>();
    if (!tenant.value) return;
    drawerApi.lock();
    try {
      const [usageResult, menuResult, planMenuIds] = await Promise.all([
        getTenantUsageApi(tenant.value.id),
        listMenusApi({ page: 1, page_size: 500 }),
        getTenantPlanMenusApi(tenant.value.plan_id),
      ]);
      usage.value = usageResult;
      menus.value = menuResult.items;
      const visibleMenuIds = new Set(collectMenuKeys(menuTreeData.value));
      checkedMenuIds.value = planMenuIds.filter((id) => visibleMenuIds.has(id));
    } finally {
      drawerApi.unlock();
    }
  },
});

const drawerTitle = computed(
  () =>
    `${$t('system.tenant.overview')}${tenant.value ? ` - ${tenant.value.name}` : ''}`,
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[min(760px,calc(100vw-24px))]">
    <div v-if="tenant && usage" class="space-y-6">
      <section>
        <h3 class="mb-3 text-sm font-semibold">
          {{ $t('system.tenant.quotaUsage') }}
        </h3>
        <Descriptions bordered :column="2" size="small">
          <DescriptionsItem :label="$t('system.tenant.plan')">
            {{ usage.plan.name }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.tenant.currentAccountCount')">
            {{ usage.members }} / {{ formatLimit(usage.plan.max_members) }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.tenant.fileUsage')">
            {{ usage.file_assets }} /
            {{ formatLimit(usage.plan.max_file_assets) }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.tenant.storageUsage')">
            {{ formatBytes(usage.storage_bytes) }} /
            {{ formatBytes(usage.plan.max_storage_bytes) }}
          </DescriptionsItem>
        </Descriptions>
      </section>

      <section>
        <h3 class="mb-3 text-sm font-semibold">
          {{ $t('system.tenant.financeSummary') }}
        </h3>
        <Descriptions bordered :column="3" size="small">
          <DescriptionsItem :label="$t('system.tenant.rechargeAmount')">
            {{ formatMoney(tenant.recharge_amount) }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.tenant.paymentAmount')">
            {{ formatMoney(tenant.payment_amount) }}
          </DescriptionsItem>
          <DescriptionsItem :label="$t('system.tenant.balanceAmount')">
            {{ formatMoney(tenant.balance_amount) }}
          </DescriptionsItem>
        </Descriptions>
      </section>

      <section>
        <h3 class="mb-3 text-sm font-semibold">
          {{ $t('system.tenant.menuBaseline') }}
        </h3>
        <ATree
          :checked-keys="checkedMenuIds"
          checkable
          disabled
          :expanded-keys="expandedMenuIds"
          :tree-data="menuTreeData"
        />
      </section>
    </div>
  </Drawer>
</template>
