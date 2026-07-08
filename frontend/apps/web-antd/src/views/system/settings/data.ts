import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { SystemSettingRecord } from '#/api';

import { z } from '#/adapter/form';
import { $t } from '#/locales';

export function useFormSchema(isSystem = false): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.setting.name'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.setting.name')])),
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 4,
      },
      fieldName: 'value',
      label: $t('system.setting.value'),
    },
    {
      component: 'Select',
      componentProps: {
        options: [
          { label: 'string', value: 'string' },
          { label: 'number', value: 'number' },
          { label: 'boolean', value: 'boolean' },
          { label: 'json', value: 'json' },
        ],
      },
      fieldName: 'value_type',
      label: $t('system.setting.valueType'),
      rules: z
        .string()
        .min(
          1,
          $t('ui.formRules.selectRequired', [$t('system.setting.valueType')]),
        ),
    },
    {
      component: 'Input',
      fieldName: 'group',
      label: $t('system.setting.group'),
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 3,
      },
      fieldName: 'description',
      label: $t('system.setting.description'),
    },
    {
      component: 'Switch',
      defaultValue: false,
      fieldName: 'is_public',
      label: $t('system.setting.public'),
    },
    {
      component: 'Switch',
      componentProps: {
        disabled: isSystem,
      },
      defaultValue: false,
      fieldName: 'is_system',
      label: $t('system.setting.system'),
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
          { label: 'system', value: 'system' },
          { label: 'auth', value: 'auth' },
          { label: 'upload', value: 'upload' },
        ],
      },
      fieldName: 'group',
      label: $t('system.setting.group'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<SystemSettingRecord>,
): VxeTableGridColumns<SystemSettingRecord> {
  return [
    {
      field: 'name',
      minWidth: 140,
      title: $t('system.setting.name'),
    },
    {
      field: 'key',
      minWidth: 160,
      title: $t('system.setting.key'),
    },
    {
      field: 'value',
      minWidth: 180,
      showOverflow: true,
      title: $t('system.setting.value'),
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'default', label: 'string', value: 'string' },
          { color: 'processing', label: 'number', value: 'number' },
          { color: 'success', label: 'boolean', value: 'boolean' },
          { color: 'warning', label: 'json', value: 'json' },
        ],
      },
      field: 'value_type',
      title: $t('system.setting.type'),
      width: 100,
    },
    {
      field: 'group',
      title: $t('system.setting.group'),
      width: 120,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'success', label: $t('system.common.yes'), value: true },
          { color: 'default', label: $t('system.common.no'), value: false },
        ],
      },
      field: 'is_public',
      title: $t('system.setting.public'),
      width: 90,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'processing', label: $t('system.common.yes'), value: true },
          { color: 'default', label: $t('system.common.no'), value: false },
        ],
      },
      field: 'is_system',
      title: $t('system.setting.builtin'),
      width: 90,
    },
    {
      field: 'updated_at',
      title: $t('system.setting.updatedAt'),
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: $t('system.setting.item'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit'],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('system.role.operation'),
      width: 90,
    },
  ];
}
