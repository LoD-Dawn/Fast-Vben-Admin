import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { UserMessageRecord } from '#/api';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
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
      label: '状态',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<UserMessageRecord>,
): VxeTableGridColumns<UserMessageRecord> {
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
      width: 110,
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
      title: '状态',
      width: 100,
    },
    {
      field: 'created_at',
      title: '创建时间',
      width: 180,
    },
    {
      field: 'read_at',
      title: '阅读时间',
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'title',
          nameTitle: '消息',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          { code: 'detail', text: '详情' },
          {
            code: 'read',
            show: (row: UserMessageRecord) => !row.is_read,
            text: '已读',
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
