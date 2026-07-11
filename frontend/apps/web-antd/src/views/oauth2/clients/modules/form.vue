<script lang="ts" setup>
import type { OAuth2ClientPayload, OAuth2ClientRecord } from '#/api';

import { computed, ref } from 'vue';

import { useVbenDrawer } from '@vben/common-ui';

import { useVbenForm } from '#/adapter/form';
import {
  createOAuth2ClientApi,
  getOAuth2ClientApi,
  updateOAuth2ClientApi,
} from '#/api';

import { arrayToCsv, csvToArray, useFormSchema } from '../data';

const emits = defineEmits<{ success: [] }>();

const clientId = ref<string>();

const [Form, formApi] = useVbenForm({
  schema: useFormSchema(),
  showDefaultActions: false,
});

const csvFields = [
  'authorized_grant_types',
  'scopes',
  'auto_approve_scopes',
  'redirect_uris',
  'authorities',
  'resource_ids',
] as const;

function toFormValues(data: OAuth2ClientRecord) {
  return {
    ...data,
    authorized_grant_types: csvToArray(data.authorized_grant_types),
    authorities: csvToArray(data.authorities),
    auto_approve_scopes: csvToArray(data.auto_approve_scopes),
    redirect_uris: csvToArray(data.redirect_uris),
    resource_ids: csvToArray(data.resource_ids),
    scopes: csvToArray(data.scopes),
  };
}

function toStringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : undefined;
}

function optionalString(value: unknown) {
  return typeof value === 'string' && value ? value : undefined;
}

function toPayload(values: Record<string, unknown>) {
  const payload = { ...values };
  for (const field of csvFields) {
    payload[field] = arrayToCsv(toStringArray(payload[field]));
  }
  if (payload.client_secret === '******') {
    delete payload.client_secret;
  }
  return {
    access_token_validity_seconds:
      Number(payload.access_token_validity_seconds) || 7200,
    additional_information: optionalString(payload.additional_information),
    authorities: optionalString(payload.authorities),
    authorized_grant_types:
      optionalString(payload.authorized_grant_types) || '',
    auto_approve_scopes: optionalString(payload.auto_approve_scopes),
    client_id: String(payload.client_id || ''),
    client_secret: optionalString(payload.client_secret),
    description: optionalString(payload.description),
    is_active:
      typeof payload.is_active === 'boolean' ? payload.is_active : true,
    logo: optionalString(payload.logo),
    name: String(payload.name || ''),
    redirect_uris: optionalString(payload.redirect_uris),
    refresh_token_validity_seconds:
      Number(payload.refresh_token_validity_seconds) || 2_592_000,
    resource_ids: optionalString(payload.resource_ids),
    scopes: optionalString(payload.scopes),
  };
}

const [Drawer, drawerApi] = useVbenDrawer({
  async onConfirm() {
    const { valid } = await formApi.validate();
    if (!valid) return;

    const values = await formApi.getValues();
    const payload = toPayload(values);

    drawerApi.lock();
    try {
      if (clientId.value) {
        await updateOAuth2ClientApi(clientId.value, payload);
      } else {
        await createOAuth2ClientApi(payload as OAuth2ClientPayload);
      }
      emits('success');
      drawerApi.close();
    } catch {
      drawerApi.unlock();
    }
  },
  async onOpenChange(isOpen) {
    if (!isOpen) return;

    const data = drawerApi.getData<OAuth2ClientRecord>();
    formApi.resetForm();
    clientId.value = data?.id;

    if (data?.id) {
      drawerApi.lock();
      try {
        const detail = await getOAuth2ClientApi(data.id);
        await formApi.setValues(toFormValues(detail));
      } finally {
        drawerApi.unlock();
      }
    }
  },
});

const drawerTitle = computed(() =>
  clientId.value ? '编辑 OAuth2 客户端' : '新增 OAuth2 客户端',
);
</script>

<template>
  <Drawer :title="drawerTitle" class="w-[760px]">
    <Form />
  </Drawer>
</template>
