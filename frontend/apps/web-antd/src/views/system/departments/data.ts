import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { DepartmentRecord } from '#/api';

import { z } from '#/adapter/form';
import { formatDateTime } from '@vben/utils';
import { listDepartmentsApi } from '#/api';
import { $t } from '#/locales';

import { buildDepartmentTree } from '../shared/utils';

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.dept.deptName'),
      rules: z
        .string()
        .min(
          2,
          $t('ui.formRules.minLength', [$t('system.dept.deptName'), 2]),
        )
        .max(
          20,
          $t('ui.formRules.maxLength', [$t('system.dept.deptName'), 20]),
        ),
    },
    {
      component: 'ApiTreeSelect',
      componentProps: {
        allowClear: true,
        api: async () => {
          const result = await listDepartmentsApi({ page: 1, page_size: 500 });
          return buildDepartmentTree(result.items);
        },
        class: 'w-full',
        childrenField: 'children',
        labelField: 'name',
        valueField: 'id',
      },
      fieldName: 'parent_id',
      label: $t('system.dept.parentDept'),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        buttonStyle: 'solid',
        options: [
          { label: $t('common.enabled'), value: true },
          { label: $t('common.disabled'), value: false },
        ],
        optionType: 'button',
      },
      defaultValue: true,
      fieldName: 'is_active',
      label: $t('system.dept.status'),
    },
    {
      component: 'Textarea',
      componentProps: {
        maxLength: 50,
        rows: 3,
        showCount: true,
      },
      fieldName: 'remark',
      label: $t('system.dept.remark'),
      rules: z
        .string()
        .max(
          50,
          $t('ui.formRules.maxLength', [$t('system.dept.remark'), 50]),
        )
        .optional(),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<DepartmentRecord>,
  hasChildren?: (departmentId?: null | string) => boolean,
): VxeTableGridColumns<DepartmentRecord> {
  return [
    {
      align: 'left',
      field: 'name',
      fixed: 'left',
      title: $t('system.dept.deptName'),
      treeNode: true,
      width: 150,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'success', label: $t('common.enabled'), value: true },
          { color: 'error', label: $t('common.disabled'), value: false },
        ],
      },
      field: 'is_active',
      title: $t('system.dept.status'),
      width: 100,
    },
    {
      field: 'created_at',
      formatter: ({ cellValue }) =>
        cellValue ? formatDateTime(cellValue) : '-',
      title: $t('system.dept.createTime'),
      width: 180,
    },
    {
      field: 'remark',
      formatter: ({ cellValue }) => cellValue || '-',
      title: $t('system.dept.remark'),
    },
    {
      align: 'right',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: $t('system.dept.name'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:department:create',
            code: 'append',
            text: $t('system.dept.appendChild'),
          },
          {
            auth: 'system:department:update',
            code: 'edit',
          },
          {
            auth: 'system:department:delete',
            code: 'delete',
            disabled: (row: DepartmentRecord) => hasChildren?.(row.id) ?? false,
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      headerAlign: 'center',
      showOverflow: false,
      title: $t('system.dept.operation'),
      width: 200,
    },
  ];
}

function generateDepartmentCode(name: string) {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return `${slug || 'dept'}_${Date.now().toString(36)}`;
}

export { generateDepartmentCode };
