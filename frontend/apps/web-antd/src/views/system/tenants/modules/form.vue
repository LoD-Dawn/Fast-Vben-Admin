<script lang="ts" setup>
import type {
  TenantCreatePayload,
  TenantRecord,
  TenantUpdatePayload,
} from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import { createTenantApi, DEFAULT_TENANT_ID, updateTenantApi } from '#/api';
import { $t } from '#/locales';

import { useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const tenantId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(() => !!tenantId.value),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-2',
});

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    const payload: Record<string, unknown> = {
      account_count: values.account_count ?? null,
      address_code: values.address_code || null,
      address_detail: values.address_detail || null,
      code: values.code,
      contact_mobile: values.contact_mobile || null,
      contact_name: values.contact_name || null,
      customer_source: values.customer_source || null,
      description: values.description || undefined,
      effective_at: values.effective_at || null,
      follow_up_notes: values.follow_up_notes || null,
      industry: values.industry ?? null,
      name: values.name,
      owner_name: values.owner_name || null,
      plan_id: values.plan_id,
      qualifications: values.qualifications || null,
      service_expires_at: values.service_expires_at || null,
      trial_ends_at: values.trial_ends_at || null,
      type: values.type ?? null,
      website: values.website || null,
      ...(!tenantId.value && {
        initialization_template_id: values.initialization_template_id,
        lifecycle_status: values.lifecycle_status || 'formal',
        password: values.password || null,
        username: values.username || null,
      }),
    };

    if (tenantId.value === DEFAULT_TENANT_ID) {
      delete payload.effective_at;
      delete payload.service_expires_at;
      delete payload.trial_ends_at;
    }

    drawerApi.lock();
    try {
      await (tenantId.value
        ? updateTenantApi(tenantId.value, payload as TenantUpdatePayload)
        : createTenantApi(payload as TenantCreatePayload));
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<TenantRecord>();
    formApi.resetForm();
    tenantId.value = data?.id;
    if (data) {
      formApi.setValues({
        ...data,
        description: data.description || undefined,
      });
    }
  },
});

const drawerTitle = computed(() =>
  tenantId.value ? $t('system.tenant.edit') : $t('system.tenant.create'),
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[min(860px,calc(100vw-24px))]">
    <Form />
  </Drawer>
</template>
