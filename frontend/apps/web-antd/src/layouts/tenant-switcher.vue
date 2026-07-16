<script lang="ts" setup>
import type { TenantMembershipRecord } from '#/api';

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { ChevronDown, IconifyIcon } from '@vben/icons';

import { Button, Dropdown, Menu, Tag, message } from 'ant-design-vue';

import { listMyTenantsApi, TENANT_MEMBERSHIPS_CHANGED_EVENT } from '#/api';
import { $t } from '#/locales';
import { useAuthStore } from '#/store';

const authStore = useAuthStore();
const emit = defineEmits<{
  currentTenantChange: [tenantName: string];
}>();
const memberships = ref<TenantMembershipRecord[]>([]);
const switchingTenantId = ref<string>();
const hasMultipleMemberships = computed(() => memberships.value.length > 1);

const currentMembership = computed(
  () =>
    memberships.value.find((membership) => membership.is_current) ||
    memberships.value.find((membership) => membership.is_default) ||
    memberships.value[0],
);

watch(
  currentMembership,
  (membership) => emit('currentTenantChange', membership?.tenant.name || ''),
  { immediate: true },
);

async function fetchMemberships() {
  try {
    memberships.value = await listMyTenantsApi();
  } catch {
    memberships.value = [];
  }
}

async function handleMenuClick(info: { key: number | string }) {
  const tenantId = String(info.key);
  const membership = memberships.value.find(
    (item) => item.tenant.id === tenantId,
  );
  if (!membership?.is_active || membership.is_current) return;

  switchingTenantId.value = tenantId;
  const hideLoading = message.loading({
    content: `${$t('system.tenant.switch')}...`,
    duration: 0,
    key: 'tenant_switch',
  });
  try {
    await authStore.switchTenant(tenantId);
  } catch {
    hideLoading();
    switchingTenantId.value = undefined;
  }
}

onMounted(() => {
  void fetchMemberships();
  window.addEventListener(TENANT_MEMBERSHIPS_CHANGED_EVENT, fetchMemberships);
});

onBeforeUnmount(() => {
  window.removeEventListener(
    TENANT_MEMBERSHIPS_CHANGED_EVENT,
    fetchMemberships,
  );
});
</script>

<template>
  <Dropdown
    v-if="currentMembership && hasMultipleMemberships"
    placement="bottomRight"
    :trigger="['click']"
  >
    <Button
      class="tenant-trigger"
      type="text"
      :aria-label="$t('system.tenant.switch')"
      :title="$t('system.tenant.switch')"
    >
      <IconifyIcon class="tenant-icon size-4 shrink-0" icon="lucide:building-2" />
      <span class="tenant-name min-w-0 truncate text-sm">
        {{ currentMembership.tenant.name }}
      </span>
      <ChevronDown
        v-if="hasMultipleMemberships"
        class="tenant-chevron size-3.5 shrink-0"
      />
    </Button>
    <template #overlay>
      <Menu
        class="min-w-56"
        :selected-keys="[currentMembership.tenant.id]"
        @click="handleMenuClick"
      >
        <Menu.Item
          v-for="membership in memberships"
          :key="membership.tenant.id"
          :disabled="
            !membership.is_active || membership.tenant.id === switchingTenantId
          "
        >
          <div class="flex min-w-0 items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate">{{ membership.tenant.name }}</div>
              <div class="truncate text-xs text-muted-foreground">
                {{ membership.tenant.code }}
              </div>
            </div>
            <Tag v-if="!membership.is_active" class="mr-0" color="default">
              {{ $t('common.disabled') }}
            </Tag>
          </div>
        </Menu.Item>
      </Menu>
    </template>
  </Dropdown>
</template>

<style scoped>
.tenant-trigger {
  display: inline-flex;
  height: 2rem;
  max-width: 11rem;
  align-items: center;
  gap: 0.375rem;
  margin: 0 0.25rem;
  padding: 0 0.625rem;
  color: hsl(var(--foreground) / 80%);
  line-height: 1;
  background: hsl(var(--accent) / 70%);
  border: 1px solid transparent;
  border-radius: 0.375rem;
  box-shadow: none;
}

.tenant-trigger:hover,
.tenant-trigger:focus-visible,
.tenant-trigger.ant-dropdown-open {
  color: hsl(var(--foreground));
  background: hsl(var(--accent));
  border-color: hsl(var(--border));
}

.tenant-icon {
  color: hsl(var(--muted-foreground));
}

@media (max-width: 639px) {
  .tenant-name,
  .tenant-chevron {
    display: none;
  }

  .tenant-trigger {
    width: 2rem;
    justify-content: center;
    padding: 0;
  }
}
</style>
