import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SocialUserRecord } from '#/api';

import { socialTypeOptions } from '../clients/data';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: socialTypeOptions,
      },
      fieldName: 'type',
      label: '平台类型',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '昵称 / OpenID / UnionID',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: 'OpenID',
      },
      fieldName: 'openid',
      label: 'OpenID',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<SocialUserRecord>,
): VxeTableGridColumns<SocialUserRecord> {
  return [
    {
      cellRender: {
        name: 'CellTag',
        options: socialTypeOptions,
      },
      field: 'type',
      title: '平台类型',
      width: 130,
    },
    {
      field: 'openid',
      minWidth: 220,
      showOverflow: true,
      title: 'OpenID',
    },
    {
      field: 'nickname',
      minWidth: 160,
      title: '昵称',
    },
    {
      cellRender: {
        name: 'CellImage',
      },
      field: 'avatar',
      title: '头像',
      width: 90,
    },
    {
      field: 'user_email',
      minWidth: 180,
      title: '绑定用户',
    },
    {
      field: 'updated_at',
      title: '更新时间',
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'nickname',
          nameTitle: '社交用户',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:social-user:list',
            code: 'detail',
            text: '详情',
          },
          {
            auth: 'system:social-user:list',
            code: 'bind',
            show: (row: SocialUserRecord) => !row.user_id,
            text: '绑定用户',
          },
          {
            auth: 'system:social-user:list',
            code: 'unbind',
            show: (row: SocialUserRecord) => Boolean(row.user_id),
            text: '解绑用户',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 160,
    },
  ];
}
