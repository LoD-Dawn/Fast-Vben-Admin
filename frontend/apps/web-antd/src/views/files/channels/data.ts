import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { FileStorageChannelRecord } from '#/api';

import { z } from '#/adapter/form';

export const providerOptions = [
  { label: '本地存储', value: 'local' },
  { label: 'S3 / MinIO', value: 's3' },
];

export const addressingStyleOptions = [
  { label: 'auto', value: 'auto' },
  { label: 'path', value: 'path' },
  { label: 'virtual', value: 'virtual' },
];

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '渠道名称 / 编码 / Bucket',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: providerOptions,
      },
      fieldName: 'provider',
      label: '渠道类型',
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
      label: '渠道名称',
      rules: z.string().min(1, '请输入渠道名称'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '渠道编码',
      rules: z.string().min(1, '请输入渠道编码'),
    },
    {
      component: 'Select',
      componentProps: {
        options: providerOptions,
      },
      defaultValue: 'local',
      fieldName: 'provider',
      label: '渠道类型',
      rules: z.string().min(1, '请选择渠道类型'),
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      fieldName: 'endpoint_url',
      label: 'Endpoint',
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      defaultValue: 'us-east-1',
      fieldName: 'region',
      label: 'Region',
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      fieldName: 'bucket',
      label: 'Bucket',
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      fieldName: 'access_key_id',
      label: 'Access Key',
    },
    {
      component: 'InputPassword',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      fieldName: 'secret_access_key',
      label: 'Secret Key',
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      fieldName: 'object_prefix',
      label: '路径前缀',
    },
    {
      component: 'Select',
      componentProps: {
        options: addressingStyleOptions,
      },
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      defaultValue: 'auto',
      fieldName: 'addressing_style',
      label: '寻址方式',
    },
    {
      component: 'Switch',
      dependencies: {
        show: (values) => values.provider === 's3',
        triggerFields: ['provider'],
      },
      defaultValue: false,
      fieldName: 'auto_create_bucket',
      label: '自动建桶',
    },
    {
      component: 'Switch',
      defaultValue: false,
      fieldName: 'is_default',
      label: '默认渠道',
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
  onActionClick: OnActionClickFn<FileStorageChannelRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: FileStorageChannelRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<FileStorageChannelRecord> {
  return [
    {
      field: 'name',
      minWidth: 160,
      title: '渠道名称',
    },
    {
      field: 'code',
      minWidth: 140,
      title: '渠道编码',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'default', label: 'local', value: 'local' },
          { color: 'processing', label: 's3', value: 's3' },
        ],
      },
      field: 'provider',
      title: '类型',
      width: 110,
    },
    {
      field: 'bucket',
      minWidth: 160,
      showOverflow: true,
      title: 'Bucket',
    },
    {
      field: 'endpoint_url',
      minWidth: 180,
      showOverflow: true,
      title: 'Endpoint',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'success', label: '默认', value: true },
          { color: 'default', label: '备用', value: false },
        ],
      },
      field: 'is_default',
      title: '默认',
      width: 90,
    },
    {
      cellRender: {
        attrs: { auth: 'system:file:channel:update', beforeChange: onStatusChange },
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
          nameTitle: '存储渠道',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:file:channel:update',
            code: 'test',
            text: '测试',
          },
          {
            auth: 'system:file:channel:update',
            code: 'edit',
          },
          {
            auth: 'system:file:channel:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 180,
    },
  ];
}
