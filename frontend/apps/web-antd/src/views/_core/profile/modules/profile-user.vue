<script setup lang="ts">
import type { AuthApi } from '#/api';

import { computed, ref, watch } from 'vue';

import { IconifyIcon } from '@vben/icons';
import { useUserStore } from '@vben/stores';
import { formatDateTime } from '@vben/utils';

import {
  Descriptions,
  DescriptionsItem,
  Tooltip,
  Upload,
  message,
} from 'ant-design-vue';

import { DEFAULT_AVATAR, getUserInfoApi, uploadAvatarApi } from '#/api';

const props = defineProps<{
  profile?: AuthApi.FastApiUser;
}>();

const emit = defineEmits<{
  (e: 'success'): void;
}>();

const userStore = useUserStore();
const uploading = ref(false);
const avatarLoadFailed = ref(false);

const avatarUrl = computed(() => {
  if (!avatarLoadFailed.value && props.profile?.avatar_url) {
    return props.profile.avatar_url;
  }
  return DEFAULT_AVATAR;
});

watch(
  () => props.profile?.avatar_url,
  () => {
    avatarLoadFailed.value = false;
  },
);

async function handleAvatarUpload(options: any) {
  const file = options.file as File;

  uploading.value = true;
  try {
    await uploadAvatarApi(file);
    userStore.setUserInfo(await getUserInfoApi());
    message.success('头像已更新');
    emit('success');
    options.onSuccess?.({}, file);
  } catch (error) {
    options.onError?.(error);
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <div v-if="profile">
    <div class="flex justify-center py-4">
      <Upload
        accept="image/*"
        :custom-request="handleAvatarUpload"
        :disabled="uploading"
        :show-upload-list="false"
      >
        <Tooltip title="点击更换头像">
          <div
            class="group relative cursor-pointer overflow-hidden rounded-full"
          >
            <img
              alt="用户头像"
              class="size-[120px] object-cover"
              :src="avatarUrl"
              @error="avatarLoadFailed = true"
            />
            <div
              class="absolute inset-0 flex items-center justify-center bg-black/45 text-white opacity-0 transition-opacity group-hover:opacity-100"
            >
              <IconifyIcon
                :class="{ 'animate-spin': uploading }"
                :icon="uploading ? 'lucide:loader-circle' : 'lucide:camera'"
                class="text-2xl"
              />
            </div>
          </div>
        </Tooltip>
      </Upload>
    </div>

    <Descriptions
      class="mt-6"
      :column="{ xs: 1, sm: 1, md: 1, lg: 1, xl: 1, xxl: 2 }"
      size="small"
    >
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:user" class="mr-1" />用户名称
          </span>
        </template>
        {{ profile.full_name || profile.email }}
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:user-cog" class="mr-1" />所属角色
          </span>
        </template>
        {{ profile.is_superuser ? '超级管理员' : '普通成员' }}
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:phone" class="mr-1" />手机号码
          </span>
        </template>
        {{ profile.mobile || '-' }}
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:mail" class="mr-1" />邮箱
          </span>
        </template>
        {{ profile.email }}
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:badge-check" class="mr-1" />账号状态
          </span>
        </template>
        {{ profile.is_active ? '正常' : '停用' }}
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:fingerprint" class="mr-1" />用户 ID
          </span>
        </template>
        <span class="break-all">{{ profile.id }}</span>
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:clock" class="mr-1" />创建时间
          </span>
        </template>
        {{ profile.created_at ? formatDateTime(profile.created_at) : '-' }}
      </DescriptionsItem>
      <DescriptionsItem>
        <template #label>
          <span class="inline-flex items-center">
            <IconifyIcon icon="lucide:refresh-cw" class="mr-1" />最近更新
          </span>
        </template>
        {{ profile.updated_at ? formatDateTime(profile.updated_at) : '-' }}
      </DescriptionsItem>
    </Descriptions>
  </div>
</template>
