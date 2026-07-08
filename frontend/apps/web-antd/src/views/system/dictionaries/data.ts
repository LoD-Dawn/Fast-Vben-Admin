import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { DictionaryItemRecord } from '#/api';

import { z } from '#/adapter/form';
import { $t } from '#/locales';

export function useTypeFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('system.dict.name'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.dict.name')])),
    },
    {
      component: 'Input',
      fieldName: 'code',
      label: $t('system.dict.code'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.dict.code')])),
    },
    {
      component: 'Textarea',
      componentProps: {
        rows: 3,
      },
      fieldName: 'description',
      label: $t('system.dict.description'),
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'is_active',
      label: $t('common.enabled'),
    },
  ];
}

export function useItemFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'label',
      label: $t('system.dict.label'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.dict.label')])),
    },
    {
      component: 'Input',
      fieldName: 'value',
      label: $t('system.dict.value'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.dict.value')])),
    },
    {
      component: 'Input',
      fieldName: 'color',
      label: $t('system.dict.color'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
      },
      defaultValue: 0,
      fieldName: 'sort',
      label: $t('system.dict.sort'),
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
        rows: 3,
      },
      fieldName: 'extra_data',
      label: $t('system.dict.extraData'),
    },
  ];
}

export function useItemGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: $t('system.common.keyword'),
    },
  ];
}

export function useItemColumns(
  onActionClick: OnActionClickFn<DictionaryItemRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: DictionaryItemRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<DictionaryItemRecord> {
  return [
    {
      field: 'label',
      minWidth: 120,
      title: $t('system.dict.label'),
    },
    {
      field: 'value',
      minWidth: 120,
      title: $t('system.dict.value'),
    },
    {
      field: 'color',
      minWidth: 140,
      slots: { default: 'color' },
      title: $t('system.dict.color'),
    },
    {
      field: 'sort',
      title: $t('system.dict.sort'),
      width: 90,
    },
    {
      cellRender: {
        attrs: { beforeChange: onStatusChange },
        name: onStatusChange ? 'CellSwitch' : 'CellTag',
      },
      field: 'is_active',
      title: $t('system.role.status'),
      width: 100,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'label',
          nameTitle: $t('system.dict.item'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit', 'delete'],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('system.role.operation'),
      width: 130,
    },
  ];
}
