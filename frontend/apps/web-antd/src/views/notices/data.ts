import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { NoticeRecord } from '#/api';

import { z } from '#/adapter/form';

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'title',
      label: '标题',
      rules: z.string().min(1, '请输入公告标题'),
    },
    {
      component: 'Input',
      defaultValue: 'notice',
      fieldName: 'type',
      label: '类型',
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
      },
      defaultValue: 0,
      fieldName: 'priority',
      label: '优先级',
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 8,
      },
      fieldName: 'content',
      label: '内容',
      rules: z.string().min(1, '请输入公告内容'),
    },
  ];
}

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '搜索标题或内容',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: '草稿', value: 'draft' },
          { label: '已发布', value: 'published' },
          { label: '已撤回', value: 'withdrawn' },
        ],
      },
      fieldName: 'status',
      label: '状态',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<NoticeRecord>,
): VxeTableGridColumns<NoticeRecord> {
  return [
    {
      field: 'title',
      minWidth: 200,
      showOverflow: true,
      title: '标题',
    },
    {
      field: 'type',
      title: '类型',
      width: 100,
    },
    {
      field: 'priority',
      title: '优先级',
      width: 100,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'default', label: '草稿', value: 'draft' },
          { color: 'success', label: '已发布', value: 'published' },
          { color: 'error', label: '已撤回', value: 'withdrawn' },
        ],
      },
      field: 'status',
      title: '状态',
      width: 110,
    },
    {
      field: 'published_at',
      title: '发布时间',
      width: 180,
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
          nameField: 'title',
          nameTitle: '公告',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          'edit',
          {
            code: 'publish',
            show: (row: NoticeRecord) => row.status !== 'published',
            text: '发布',
          },
          {
            code: 'withdraw',
            show: (row: NoticeRecord) => row.status === 'published',
            text: '撤回',
          },
          'delete',
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 220,
    },
  ];
}
