import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SmsChannelRecord } from '#/api';

import { z } from '#/adapter/form';

export const providerOptions = [
  { label: '本地调试', value: 'debug' },
  { label: '阿里云短信', value: 'aliyun' },
  { label: '腾讯云短信', value: 'tencent' },
  { label: '华为云短信', value: 'huawei' },
];

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '渠道名称 / 编码 / 签名',
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
      defaultValue: 'debug',
      fieldName: 'provider',
      label: '渠道类型',
      rules: z.string().min(1, '请选择渠道类型'),
    },
    {
      component: 'Input',
      fieldName: 'signature',
      label: '短信签名',
      rules: z.string().min(1, '请输入短信签名'),
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider !== 'debug',
        triggerFields: ['provider'],
      },
      fieldName: 'api_key',
      label: 'API Key',
    },
    {
      component: 'InputPassword',
      dependencies: {
        show: (values) => values.provider !== 'debug',
        triggerFields: ['provider'],
      },
      fieldName: 'api_secret',
      label: 'API Secret',
    },
    {
      component: 'Input',
      dependencies: {
        show: (values) => values.provider !== 'debug',
        triggerFields: ['provider'],
      },
      fieldName: 'callback_url',
      label: '回调地址',
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
  onActionClick: OnActionClickFn<SmsChannelRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: SmsChannelRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<SmsChannelRecord> {
  return [
    {
      field: 'name',
      minWidth: 160,
      title: '渠道名称',
    },
    {
      field: 'code',
      minWidth: 130,
      title: '渠道编码',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'default', label: '调试', value: 'debug' },
          { color: 'processing', label: '阿里云', value: 'aliyun' },
          { color: 'success', label: '腾讯云', value: 'tencent' },
          { color: 'warning', label: '华为云', value: 'huawei' },
        ],
      },
      field: 'provider',
      title: '类型',
      width: 100,
    },
    {
      field: 'signature',
      minWidth: 130,
      title: '短信签名',
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
        attrs: { auth: 'system:sms-channel:update', beforeChange: onStatusChange },
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
          nameTitle: '短信渠道',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:sms-channel:update',
            code: 'edit',
          },
          {
            auth: 'system:sms-channel:delete',
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
