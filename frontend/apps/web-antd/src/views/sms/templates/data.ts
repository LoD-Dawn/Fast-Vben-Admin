import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SmsTemplateRecord } from '#/api';

import { z } from '#/adapter/form';
import { listSimpleSmsChannelsApi } from '#/api';

export const templateTypeOptions = [
  { label: '验证码', value: 'verification' },
  { label: '通知', value: 'notification' },
  { label: '营销', value: 'marketing' },
];

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '模板名称 / 编码 / 内容',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: templateTypeOptions,
      },
      fieldName: 'type',
      label: '模板类型',
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
      label: '模板名称',
      rules: z.string().min(1, '请输入模板名称'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '模板编码',
      rules: z.string().min(1, '请输入模板编码'),
    },
    {
      component: 'Select',
      componentProps: {
        options: templateTypeOptions,
      },
      defaultValue: 'notification',
      fieldName: 'type',
      label: '模板类型',
      rules: z.string().min(1, '请选择模板类型'),
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: listSimpleSmsChannelsApi,
        class: 'w-full',
        labelField: 'name',
        valueField: 'id',
      },
      fieldName: 'channel_id',
      label: '发送渠道',
    },
    {
      component: 'Input',
      fieldName: 'api_template_id',
      label: '平台模板 ID',
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '例如：您的验证码为 {code}，5 分钟内有效。',
        rows: 6,
      },
      fieldName: 'content',
      label: '模板内容',
      rules: z.string().min(1, '请输入模板内容'),
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

export function useSendFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Textarea',
      componentProps: {
        disabled: true,
        rows: 4,
      },
      fieldName: 'content',
      label: '模板内容',
    },
    {
      component: 'Input',
      fieldName: 'mobile',
      label: '手机号',
      rules: z.string().min(6, '请输入手机号'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<SmsTemplateRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: SmsTemplateRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<SmsTemplateRecord> {
  return [
    {
      field: 'name',
      minWidth: 150,
      title: '模板名称',
    },
    {
      field: 'code',
      minWidth: 140,
      title: '模板编码',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'processing', label: '验证码', value: 'verification' },
          { color: 'success', label: '通知', value: 'notification' },
          { color: 'warning', label: '营销', value: 'marketing' },
        ],
      },
      field: 'type',
      title: '类型',
      width: 100,
    },
    {
      field: 'channel_code',
      minWidth: 120,
      title: '发送渠道',
    },
    {
      field: 'params',
      minWidth: 120,
      title: '模板参数',
    },
    {
      field: 'content',
      minWidth: 260,
      showOverflow: true,
      title: '模板内容',
    },
    {
      cellRender: {
        attrs: { auth: 'system:sms-template:update', beforeChange: onStatusChange },
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
          nameTitle: '短信模板',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:sms-template:send',
            code: 'send',
            text: '发送测试',
          },
          {
            auth: 'system:sms-template:update',
            code: 'edit',
          },
          {
            auth: 'system:sms-template:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 210,
    },
  ];
}
