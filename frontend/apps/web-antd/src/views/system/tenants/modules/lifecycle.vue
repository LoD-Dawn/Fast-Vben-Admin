<script lang="ts" setup>
import type { TenantRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { operateTenantLifecycleApi } from '#/api';
import { $t } from '#/locales';

import { useLifecycleFormSchema } from '../data';

interface LifecycleDrawerData {
  action: 'freeze' | 'renew';
  tenant: TenantRecord;
}

const emits = defineEmits<{ success: [] }>();
const action = ref<'freeze' | 'renew'>('renew');
const tenant = ref<TenantRecord>();

const [Form, formApi] = useVbenForm({
  schema: useLifecycleFormSchema('renew'),
  showDefaultActions: false,
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    if (!tenant.value) return;
    const { valid } = await formApi.validate();
    if (!valid) return;
    const values = await formApi.getValues();

    drawerApi.lock();
    try {
      await operateTenantLifecycleApi(tenant.value.id, {
        action: action.value,
        frozen_reason:
          action.value === 'freeze' ? values.frozen_reason : undefined,
        service_expires_at:
          action.value === 'renew' ? values.service_expires_at : undefined,
      });
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;
    const data = drawerApi.getData<LifecycleDrawerData>();
    action.value = data.action;
    tenant.value = data.tenant;
    formApi.resetForm();
    formApi.setState({ schema: useLifecycleFormSchema(data.action) });
    if (data.action === 'renew' && data.tenant.service_expires_at) {
      formApi.setValues({
        service_expires_at: data.tenant.service_expires_at,
      });
    }
  },
});

const drawerTitle = computed(() => {
  const actionTitle =
    action.value === 'renew'
      ? $t('system.tenant.renew')
      : $t('system.tenant.freeze');
  return `${actionTitle}${tenant.value ? ` - ${tenant.value.name}` : ''}`;
});
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[520px]">
    <Form />
  </Drawer>
</template>
