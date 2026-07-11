import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { MailTemplateRecord } from '#/api';

import { z } from '#/adapter/form';
import { listSimpleMailAccountsApi } from '#/api';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '模板名称 / 编码 / 标题 / 内容',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: listSimpleMailAccountsApi,
        class: 'w-full',
        labelField: 'name',
        valueField: 'id',
      },
      fieldName: 'account_id',
      label: '邮箱账号',
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
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: listSimpleMailAccountsApi,
        class: 'w-full',
        labelField: 'name',
        valueField: 'id',
      },
      fieldName: 'account_id',
      label: '发送账号',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '默认使用邮箱账号名称',
      },
      fieldName: 'nickname',
      label: '发件人昵称',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '例如：您好，{name}',
      },
      fieldName: 'title',
      label: '邮件标题',
      rules: z.string().min(1, '请输入邮件标题'),
    },
    {
      component: 'Textarea',
      componentProps: {
        placeholder: '支持 {name} 形式的变量，例如：<p>您好，{name}。</p>',
        rows: 10,
      },
      fieldName: 'content',
      label: '邮件内容',
      rules: z.string().min(1, '请输入邮件内容'),
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
      component: 'Input',
      fieldName: 'to_email',
      label: '收件邮箱',
      rules: z.string().email('请输入有效的收件邮箱'),
    },
    {
      component: 'Input',
      componentProps: {
        disabled: true,
      },
      fieldName: 'title',
      label: '邮件标题',
    },
    {
      component: 'Textarea',
      componentProps: {
        disabled: true,
        rows: 6,
      },
      fieldName: 'content',
      label: '邮件内容',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<MailTemplateRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: MailTemplateRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<MailTemplateRecord> {
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
      field: 'account_code',
      minWidth: 120,
      title: '发送账号',
    },
    {
      field: 'nickname',
      minWidth: 120,
      title: '发件昵称',
    },
    {
      field: 'title',
      minWidth: 220,
      showOverflow: true,
      title: '邮件标题',
    },
    {
      field: 'params',
      minWidth: 120,
      title: '模板参数',
    },
    {
      field: 'content',
      minWidth: 280,
      showOverflow: true,
      title: '邮件内容',
    },
    {
      cellRender: {
        attrs: {
          auth: 'system:mail-template:update',
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
          nameTitle: '邮件模板',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:mail-template:send',
            code: 'send',
            text: '发送测试',
          },
          {
            auth: 'system:mail-template:update',
            code: 'edit',
          },
          {
            auth: 'system:mail-template:delete',
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
