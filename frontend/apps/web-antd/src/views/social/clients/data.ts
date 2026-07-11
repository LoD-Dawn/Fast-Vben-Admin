import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SocialClientRecord } from '#/api';

import { z } from '#/adapter/form';

export const socialTypeOptions = [
  { label: 'Gitee', value: 'gitee' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '微信开放平台', value: 'wechat_open' },
  { label: '微信公众平台', value: 'wechat_mp' },
  { label: '微信小程序', value: 'wechat_mini' },
  { label: '企业微信', value: 'wechat_work' },
];

export const userTypeOptions = [
  { label: '管理后台', value: 'admin' },
  { label: '移动端', value: 'member' },
];

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '客户端名称 / Client ID / 备注',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: socialTypeOptions,
      },
      fieldName: 'social_type',
      label: '平台类型',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: userTypeOptions,
      },
      fieldName: 'user_type',
      label: '用户类型',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: '启用', value: true },
          { label: '禁用', value: false },
        ],
      },
      fieldName: 'is_active',
      label: '状态',
    },
  ];
}

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: '客户端名称',
      rules: z.string().min(1, '请输入客户端名称'),
    },
    {
      component: 'Select',
      componentProps: {
        options: socialTypeOptions,
      },
      fieldName: 'social_type',
      label: '平台类型',
      rules: z.string().min(1, '请选择平台类型'),
    },
    {
      component: 'Select',
      componentProps: {
        options: userTypeOptions,
      },
      defaultValue: 'admin',
      fieldName: 'user_type',
      label: '用户类型',
      rules: z.string().min(1, '请选择用户类型'),
    },
    {
      component: 'Input',
      fieldName: 'client_id',
      label: 'Client ID',
      rules: z.string().min(1, '请输入 Client ID'),
    },
    {
      component: 'InputPassword',
      fieldName: 'client_secret',
      label: 'Client Secret',
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.social_type === 'wechat_work',
        triggerFields: ['social_type'],
      },
      fieldName: 'agent_id',
      label: 'Agent ID',
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'is_active',
      label: '启用',
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 3,
      },
      fieldName: 'remark',
      label: '备注',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<SocialClientRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: SocialClientRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<SocialClientRecord> {
  return [
    {
      field: 'name',
      minWidth: 160,
      title: '客户端名称',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: socialTypeOptions,
      },
      field: 'social_type',
      title: '平台类型',
      width: 130,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: userTypeOptions,
      },
      field: 'user_type',
      title: '用户类型',
      width: 110,
    },
    {
      field: 'client_id',
      minWidth: 180,
      showOverflow: true,
      title: 'Client ID',
    },
    {
      field: 'agent_id',
      minWidth: 110,
      title: 'Agent ID',
    },
    {
      cellRender: {
        attrs: {
          auth: 'system:social-client:update',
          beforeChange: onStatusChange,
        },
        name: onStatusChange ? 'CellSwitch' : 'CellTag',
      },
      field: 'is_active',
      title: '状态',
      width: 90,
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
          nameField: 'name',
          nameTitle: '三方登录客户端',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:social-client:update',
            code: 'edit',
          },
          {
            auth: 'system:social-client:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 140,
    },
  ];
}
