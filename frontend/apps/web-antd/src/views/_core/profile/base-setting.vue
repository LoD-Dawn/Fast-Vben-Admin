<script setup lang="ts">
import type { Recordable } from '@vben/types';

import type { AuthApi } from '#/api';
import type { VbenFormSchema } from '#/adapter/form';

import { computed, onMounted, ref, watch } from 'vue';

import { ProfileBaseSetting } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';

import { message } from 'ant-design-vue';

import { getUserInfoApi, updateCurrentUserApi } from '#/api';

const props = defineProps<{
  profile?: AuthApi.FastApiUser;
}>();

const emit = defineEmits<{
  (e: 'success'): void;
}>();

const userStore = useUserStore();
const profileBaseSettingRef = ref();
const saving = ref(false);

const formSchema = computed((): VbenFormSchema[] => {
  return [
    {
      fieldName: 'full_name',
      component: 'Input',
      label: '姓名',
    },
    {
      fieldName: 'email',
      component: 'Input',
      label: '邮箱',
    },
  ];
});

function applyProfile(data?: AuthApi.FastApiUser) {
  if (!data || !profileBaseSettingRef.value) {
    return;
  }
  profileBaseSettingRef.value.getFormApi().setValues({
    email: data.email,
    full_name: data.full_name || '',
  });
}

async function handleSubmit(values: Recordable<any>) {
  saving.value = true;
  try {
    await updateCurrentUserApi({
      email: String(values.email || ''),
      full_name: String(values.full_name || ''),
    });
    userStore.setUserInfo(await getUserInfoApi());
    message.success('个人资料已更新');
    emit('success');
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  applyProfile(props.profile);
});

watch(
  () => props.profile,
  (profile) => {
    applyProfile(profile);
  },
  { deep: true },
);
</script>
<template>
  <div class="mt-4 w-full lg:w-1/2 2xl:w-2/5">
    <ProfileBaseSetting
      ref="profileBaseSettingRef"
      :class="{ 'pointer-events-none opacity-60': saving }"
      :form-schema="formSchema"
      @submit="handleSubmit"
    />
  </div>
</template>
