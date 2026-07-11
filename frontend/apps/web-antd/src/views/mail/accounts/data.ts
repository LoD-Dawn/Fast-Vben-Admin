import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { MailAccountRecord } from '#/api';

import { z } from '#/adapter/form';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '账号名称 / 编码 / 发件邮箱 / SMTP 主机',
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
      fieldName: 'name',
      label: '账号名称',
      rules: z.string().min(1, '请输入账号名称'),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: '账号编码',
      rules: z.string().min(1, '请输入账号编码'),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: 'sender@example.com',
      },
      fieldName: 'email',
      label: '发件邮箱',
      rules: z.string().email('请输入有效的发件邮箱'),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: 'smtp.example.com',
      },
      fieldName: 'host',
      label: 'SMTP 主机',
      rules: z.string().min(1, '请输入 SMTP 主机'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
        max: 65_535,
        min: 1,
      },
      defaultValue: 465,
      fieldName: 'port',
      label: 'SMTP 端口',
      rules: z.number().min(1, '请输入 SMTP 端口'),
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '默认使用发件邮箱',
      },
      fieldName: 'username',
      label: '认证用户名',
    },
    {
      component: 'InputPassword',
      componentProps: {
        placeholder: '编辑时留空则保留原密码',
      },
      fieldName: 'password',
      label: '认证密码',
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'ssl_enable',
      label: 'SSL 加密',
    },
    {
      component: 'Switch',
      defaultValue: false,
      fieldName: 'starttls_enable',
      label: 'STARTTLS',
    },
    {
      component: 'Switch',
      defaultValue: false,
      fieldName: 'is_default',
      label: '默认账号',
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
  onActionClick: OnActionClickFn<MailAccountRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: MailAccountRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<MailAccountRecord> {
  return [
    {
      field: 'name',
      minWidth: 160,
      title: '账号名称',
    },
    {
      field: 'code',
      minWidth: 130,
      title: '账号编码',
    },
    {
      field: 'email',
      minWidth: 210,
      title: '发件邮箱',
    },
    {
      field: 'host',
      minWidth: 180,
      title: 'SMTP 主机',
    },
    {
      field: 'port',
      title: '端口',
      width: 90,
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
        attrs: {
          auth: 'system:mail-account:update',
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
          nameTitle: '邮箱账号',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:mail-account:update',
            code: 'edit',
          },
          {
            auth: 'system:mail-account:delete',
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
