import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SiteMessageTemplateRecord } from '#/api';

import { z } from '#/adapter/form';
import { listSimpleUsersApi } from '#/api';

export const siteMessageTypeOptions = [
  { label: '通知公告', value: 'notice' },
  { label: '系统消息', value: 'system' },
  { label: '任务提醒', value: 'task' },
];

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '模板名称 / 编码 / 发送人 / 内容',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: siteMessageTypeOptions,
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
      component: 'Input',
      defaultValue: '系统通知',
      fieldName: 'sender_name',
      label: '发送人名称',
      rules: z.string().min(1, '请输入发送人名称'),
    },
    {
      component: 'Select',
      componentProps: {
        options: siteMessageTypeOptions,
      },
      defaultValue: 'system',
      fieldName: 'type',
      label: '模板类型',
      rules: z.string().min(1, '请选择模板类型'),
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '支持 {name} 形式的变量，例如：您收到一条新的任务：{task}',
        rows: 8,
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
        rows: 5,
      },
      fieldName: 'content',
      label: '模板内容',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        api: listSimpleUsersApi,
        class: 'w-full',
        labelField: 'label',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'user_id',
      label: '接收用户',
      rules: z.string().min(1, '请选择接收用户'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<SiteMessageTemplateRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: SiteMessageTemplateRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<SiteMessageTemplateRecord> {
  return [
    {
      field: 'name',
      minWidth: 150,
      title: '模板名称',
    },
    {
      field: 'code',
      minWidth: 150,
      title: '模板编码',
    },
    {
      field: 'sender_name',
      minWidth: 130,
      title: '发送人名称',
    },
    {
      field: 'content',
      minWidth: 280,
      showOverflow: true,
      title: '模板内容',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'processing', label: '通知公告', value: 'notice' },
          { color: 'success', label: '系统消息', value: 'system' },
          { color: 'warning', label: '任务提醒', value: 'task' },
        ],
      },
      field: 'type',
      title: '模板类型',
      width: 110,
    },
    {
      cellRender: {
        attrs: {
          auth: 'system:site-message-template:update',
          beforeChange: onStatusChange,
        },
        name: onStatusChange ? 'CellSwitch' : 'CellTag',
      },
      field: 'is_active',
      title: '状态',
      width: 90,
    },
    {
      field: 'params',
      minWidth: 120,
      title: '模板参数',
    },
    {
      field: 'created_at',
      title: '创建时间',
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: '站内信模板',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:site-message-template:update',
            code: 'edit',
          },
          {
            auth: 'system:site-message-template:send',
            code: 'send',
            text: '测试',
          },
          {
            auth: 'system:site-message-template:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 190,
    },
  ];
}
