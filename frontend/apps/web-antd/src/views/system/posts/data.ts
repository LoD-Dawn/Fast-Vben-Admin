import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { PostRecord } from '#/api';

import { z } from '#/adapter/form';
import { $t } from '#/locales';

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.post.postName'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.post.postName')])),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('system.post.postCode'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.post.postCode')])),
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
      },
      defaultValue: 0,
      fieldName: 'sort',
      label: $t('system.common.sort'),
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'is_active',
      label: $t('common.enabled'),
    },
    {
      component: 'Textarea',
      componentProps: {
        maxLength: 255,
        rows: 3,
        showCount: true,
      },
      fieldName: 'remark',
      label: $t('system.post.remark'),
    },
  ];
}

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: $t('system.common.keyword'),
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: $t('common.enabled'), value: true },
          { label: $t('common.disabled'), value: false },
        ],
      },
      fieldName: 'is_active',
      label: $t('system.post.status'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<PostRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: PostRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<PostRecord> {
  return [
    {
      field: 'name',
      minWidth: 160,
      title: $t('system.post.postName'),
    },
    {
      field: 'code',
      minWidth: 160,
      title: $t('system.post.postCode'),
    },
    {
      field: 'sort',
      title: $t('system.common.sort'),
      width: 90,
    },
    {
      cellRender: {
        attrs: { auth: 'system:post:update', beforeChange: onStatusChange },
        name: onStatusChange ? 'CellSwitch' : 'CellTag',
      },
      field: 'is_active',
      title: $t('system.post.status'),
      width: 100,
    },
    {
      field: 'remark',
      minWidth: 180,
      showOverflow: true,
      title: $t('system.post.remark'),
    },
    {
      field: 'created_at',
      title: $t('system.post.createTime'),
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: $t('system.post.name'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:post:update',
            code: 'edit',
          },
          {
            auth: 'system:post:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('system.post.operation'),
      width: 130,
    },
  ];
}
