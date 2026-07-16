<script lang="ts" setup>
import type { MenuRecord, TenantPlanRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { Tree as ATree } from 'ant-design-vue';

import {
  getTenantPlanMenusApi,
  listMenusApi,
  updateTenantPlanMenusApi,
} from '#/api';
import { $t } from '#/locales';

interface MenuTreeNode {
  children: MenuTreeNode[];
  key: string;
  title: string;
}

const emits = defineEmits<{ success: [] }>();
const plan = ref<TenantPlanRecord>();
const checkedMenuIds = ref<string[]>([]);
const menus = ref<MenuRecord[]>([]);
const loading = ref(false);

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
        title: `${formatMenuTitle(menu.title)}${menu.permission_code ? ` (${menu.permission_code})` : ''}`,
      }));
  }

  return build(null);
});

const expandedMenuIds = computed(() =>
  collectMenuKeys(menuTreeData.value, true),
);

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    if (!plan.value) return;
    drawerApi.lock();
    try {
      await updateTenantPlanMenusApi(plan.value.id, {
        menu_ids: checkedMenuIds.value,
      });
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) return;
    plan.value = drawerApi.getData<TenantPlanRecord>();
    checkedMenuIds.value = [];
    loading.value = true;
    try {
      const [menuResult, planMenuIds] = await Promise.all([
        listMenusApi({ page: 1, page_size: 500 }),
        plan.value ? getTenantPlanMenusApi(plan.value.id) : Promise.resolve([]),
      ]);
      menus.value = menuResult.items;
      const visibleMenuIds = new Set(collectMenuKeys(menuTreeData.value));
      checkedMenuIds.value = planMenuIds.filter((id) => visibleMenuIds.has(id));
    } finally {
      loading.value = false;
    }
  },
});

const drawerTitle = computed(
  () =>
    `${$t('system.tenantPlan.grantMenu')}${plan.value ? ` - ${plan.value.name}` : ''}`,
);
</script>

<template>
  <Drawer :loading="loading" :title="drawerTitle" class="w-[640px]">
    <ATree
      v-if="!loading"
      v-model:checked-keys="checkedMenuIds"
      checkable
      :expanded-keys="expandedMenuIds"
      :tree-data="menuTreeData"
    />
  </Drawer>
</template>
