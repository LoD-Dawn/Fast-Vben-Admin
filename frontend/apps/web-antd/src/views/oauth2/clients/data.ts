import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { OAuth2ClientRecord } from '#/api';

import { z } from '#/adapter/form';

export const grantTypeOptions = [
  { label: 'authorization_code', value: 'authorization_code' },
  { label: 'refresh_token', value: 'refresh_token' },
  { label: 'password', value: 'password' },
  { label: 'client_credentials', value: 'client_credentials' },
  { label: 'implicit', value: 'implicit' },
];

export function csvToArray(value?: null | string) {
  return value
    ? value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    : [];
}

export function arrayToCsv(value?: string[]) {
  return value?.filter(Boolean).join(',') || undefined;
}

function fullWidthSelectProps(placeholder: string) {
  return {
    class: 'w-full',
    placeholder,
    style: {
      width: '100%',
    },
  };
}

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '客户端 ID / 名称 / 描述',
      },
      fieldName: 'keyword',
      label: '关键词',
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
      fieldName: 'client_id',
      label: '客户端 ID',
      rules: z.string().min(1, '请输入客户端 ID'),
    },
    {
      component: 'InputPassword',
      fieldName: 'client_secret',
      label: '客户端密钥',
    },
    {
      component: 'InputPassword',
      componentProps: {
        autocomplete: 'current-password',
        placeholder: '修改客户端密钥时必填',
      },
      dependencies: {
        show: (values) =>
          Boolean(
            values.client_secret && values.client_secret !== '******',
          ),
        triggerFields: ['client_secret'],
      },
      fieldName: 'current_password',
      label: '当前管理员密码',
    },
    {
      component: 'Input',
      fieldName: 'name',
      label: '应用名称',
      rules: z.string().min(1, '请输入应用名称'),
    },
    {
      component: 'Input',
      fieldName: 'logo',
      label: 'Logo 地址',
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 2,
      },
      fieldName: 'description',
      label: '应用描述',
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 60,
      },
      defaultValue: 7200,
      fieldName: 'access_token_validity_seconds',
      label: '访问令牌秒数',
      rules: z.number().min(60, '至少 60 秒'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        min: 60,
      },
      defaultValue: 2_592_000,
      fieldName: 'refresh_token_validity_seconds',
      label: '刷新令牌秒数',
      rules: z.number().min(60, '至少 60 秒'),
    },
    {
      component: 'Select',
      componentProps: {
        ...fullWidthSelectProps('请选择授权类型'),
        mode: 'multiple',
        options: grantTypeOptions,
      },
      defaultValue: ['authorization_code', 'refresh_token'],
      fieldName: 'authorized_grant_types',
      label: '授权类型',
      rules: z.array(z.string()).min(1, '请选择授权类型'),
    },
    {
      component: 'Select',
      componentProps: {
        ...fullWidthSelectProps('请输入范围后按回车'),
        mode: 'tags',
        tokenSeparators: [','],
      },
      defaultValue: ['read', 'write'],
      fieldName: 'scopes',
      label: '授权范围',
    },
    {
      component: 'Select',
      componentProps: {
        ...fullWidthSelectProps('请输入范围后按回车'),
        mode: 'tags',
        tokenSeparators: [','],
      },
      fieldName: 'auto_approve_scopes',
      label: '自动授权范围',
    },
    {
      component: 'Select',
      componentProps: {
        ...fullWidthSelectProps('请输入回调地址后按回车'),
        mode: 'tags',
        tokenSeparators: [','],
      },
      fieldName: 'redirect_uris',
      label: '回调地址',
    },
    {
      component: 'Select',
      componentProps: {
        ...fullWidthSelectProps('请输入权限后按回车'),
        mode: 'tags',
        tokenSeparators: [','],
      },
      fieldName: 'authorities',
      label: '权限',
    },
    {
      component: 'Select',
      componentProps: {
        ...fullWidthSelectProps('请输入资源 ID 后按回车'),
        mode: 'tags',
        tokenSeparators: [','],
      },
      fieldName: 'resource_ids',
      label: '资源 ID',
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 3,
      },
      fieldName: 'additional_information',
      label: '附加信息',
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'is_active',
      label: '启用',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<OAuth2ClientRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: OAuth2ClientRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<OAuth2ClientRecord> {
  return [
    {
      field: 'client_id',
      minWidth: 180,
      title: '客户端 ID',
    },
    {
      field: 'name',
      minWidth: 160,
      title: '应用名称',
    },
    {
      field: 'authorized_grant_types',
      minWidth: 220,
      showOverflow: true,
      title: '授权类型',
    },
    {
      field: 'scopes',
      minWidth: 140,
      showOverflow: true,
      title: '授权范围',
    },
    {
      field: 'access_token_validity_seconds',
      title: '访问令牌',
      width: 110,
    },
    {
      field: 'refresh_token_validity_seconds',
      title: '刷新令牌',
      width: 110,
    },
    {
      cellRender: {
        attrs: {
          auth: 'system:oauth2-client:update',
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
          nameTitle: 'OAuth2 客户端',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:oauth2-client:update',
            code: 'edit',
          },
          {
            auth: 'system:oauth2-client:delete',
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
