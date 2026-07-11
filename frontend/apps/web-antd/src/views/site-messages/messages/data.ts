import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SiteMessageRecord } from '#/api';

import { listSimpleUsersApi } from '#/api';

import { siteMessageTypeOptions } from '../templates/data';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'ApiSelect',
      componentProps: {
        allowClear: true,
        api: listSimpleUsersApi,
        class: 'w-full',
        labelField: 'label',
        showSearch: true,
        valueField: 'id',
      },
      fieldName: 'user_id',
      label: '接收用户',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '模板编码',
      },
      fieldName: 'template_code',
      label: '模板编码',
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
          { label: '未读', value: false },
          { label: '已读', value: true },
        ],
      },
      fieldName: 'is_read',
      label: '阅读状态',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<SiteMessageRecord>,
): VxeTableGridColumns<SiteMessageRecord> {
  return [
    {
      field: 'user_email',
      minWidth: 220,
      title: '接收用户',
    },
    {
      field: 'template_code',
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
      title: '消息内容',
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
      field: 'template_params',
      minWidth: 180,
      showOverflow: true,
      title: '模板参数',
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'processing', label: '未读', value: false },
          { color: 'default', label: '已读', value: true },
        ],
      },
      field: 'is_read',
      title: '阅读状态',
      width: 100,
    },
    {
      field: 'read_at',
      title: '阅读时间',
      width: 180,
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
          nameField: 'title',
          nameTitle: '站内信',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            code: 'detail',
            text: '详情',
          },
          {
            auth: 'system:site-message:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 130,
    },
  ];
}
