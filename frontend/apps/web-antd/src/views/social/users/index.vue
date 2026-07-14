<script lang="ts" setup>
import type {
  OnActionClickParams,
  VxeTableGridOptions,
} from '#/adapter/vxe-table';
import type { SocialUserRecord, UserRecord } from '#/api';

import { ref } from 'vue';

import { Page, useVbenDrawer } from '@vben/common-ui';

import { Modal, Select, message } from 'ant-design-vue';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  bindSocialUserApi,
  listSocialUsersApi,
  listUsersApi,
  unbindSocialUserApi,
} from '#/api';

import { confirmAction } from '../../system/shared/utils';

import { useColumns, useGridFormSchema } from './data';
import Detail from './modules/detail.vue';

const [DetailDrawer, detailDrawerApi] = useVbenDrawer({
  connectedComponent: Detail,
  destroyOnClose: true,
});

const bindingSocialUser = ref<SocialUserRecord>();
const bindingUserId = ref<string>();
const bindingUsers = ref<UserRecord[]>([]);
const bindingOpen = ref(false);
const bindingSaving = ref(false);

function onActionClick({ code, row }: OnActionClickParams<SocialUserRecord>) {
  if (code === 'detail') {
    detailDrawerApi.setData(row).open();
  }
  if (code === 'bind') {
    void openBindModal(row);
  }
  if (code === 'unbind') {
    void unbindUser(row);
  }
}

async function openBindModal(row: SocialUserRecord) {
  const result = await listUsersApi({ is_active: true, page: 1, page_size: 200 });
  bindingUsers.value = result.items;
  bindingSocialUser.value = row;
  bindingUserId.value = undefined;
  bindingOpen.value = true;
}

async function confirmBind() {
  if (!bindingSocialUser.value || !bindingUserId.value) {
    message.warning('请选择要绑定的用户');
    return;
  }
  bindingSaving.value = true;
  try {
    await bindSocialUserApi(bindingSocialUser.value.id, bindingUserId.value);
    bindingOpen.value = false;
    message.success('社交账号已绑定');
    gridApi.query();
  } finally {
    bindingSaving.value = false;
  }
}

async function unbindUser(row: SocialUserRecord) {
  try {
    await confirmAction(`确认解除社交账号 ${row.openid} 的用户绑定吗？`, '解绑用户');
    await unbindSocialUserApi(row.id);
    message.success('社交账号已解绑');
    gridApi.query();
  } catch {
    // 用户取消或接口失败时由全局错误处理接管
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
          return await listSocialUsersApi({
            keyword: formValues.keyword || undefined,
            openid: formValues.openid || undefined,
            page: page.currentPage,
            page_size: page.pageSize,
            type: formValues.type || undefined,
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
  } as VxeTableGridOptions<SocialUserRecord>,
});
</script>

<template>
  <Page auto-content-height>
    <DetailDrawer />
    <Grid table-title="三方登录用户管理" />
    <Modal
      v-model:open="bindingOpen"
      :confirm-loading="bindingSaving"
      title="绑定本地用户"
      @ok="confirmBind"
    >
      <Select
        v-model:value="bindingUserId"
        class="w-full"
        :field-names="{ label: 'email', value: 'id' }"
        :options="bindingUsers"
        placeholder="选择要绑定的用户"
        show-search
      />
    </Modal>
  </Page>
</template>
