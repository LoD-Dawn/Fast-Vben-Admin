import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { MenuRecord } from '#/api';

import { z } from '#/adapter/form';
import { listMenusApi } from '#/api';
import { $t } from '#/locales';

function getMenuTypeOptions() {
  return [
    { label: $t('system.menu.typeDirectory'), value: 'directory' },
    { label: $t('system.menu.typeMenu'), value: 'menu' },
    { label: $t('system.menu.typeButton'), value: 'button' },
  ];
}

function getMenuTypeMap(): Record<string, { color: string; label: string }> {
  return {
    button: { color: 'purple', label: $t('system.menu.typeButton') },
    directory: { color: 'blue', label: $t('system.menu.typeDirectory') },
    menu: { color: 'green', label: $t('system.menu.typeMenu') },
  };
}

export function useFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'title',
      label: $t('system.menu.menuName'),
      rules: z
        .string()
        .min(1, $t('ui.formRules.required', [$t('system.menu.menuName')])),
    },
    {
      component: 'Select',
      componentProps: {
        options: getMenuTypeOptions(),
      },
      defaultValue: 'menu',
      fieldName: 'type',
      label: $t('system.menu.type'),
    },
    {
      component: 'ApiTreeSelect',
      componentProps: {
        allowClear: true,
        api: async () => {
          const result = await listMenusApi({ page: 1, page_size: 500 });
          return result.items.filter((menu) => menu.type !== 'button');
        },
        class: 'w-full',
        labelField: 'title',
        valueField: 'id',
      },
      fieldName: 'parent_id',
      label: $t('system.menu.parentMenu'),
    },
    {
      component: 'Input',
      fieldName: 'route_path',
      label: $t('system.menu.routePath'),
    },
    {
      component: 'Input',
      fieldName: 'route_name',
      label: $t('system.menu.routeName'),
    },
    {
      component: 'Input',
      fieldName: 'component',
      label: $t('system.menu.componentPath'),
    },
    {
      component: 'Input',
      fieldName: 'icon',
      label: $t('system.menu.icon'),
    },
    {
      component: 'Input',
      fieldName: 'permission_code',
      label: $t('system.menu.permissionCode'),
    },
    {
      component: 'InputNumber',
      componentProps: {
        class: 'w-full',
      },
      defaultValue: 0,
      fieldName: 'sort',
      label: $t('system.menu.sort'),
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'is_visible',
      label: $t('system.menu.visible'),
    },
    {
      component: 'Switch',
      defaultValue: true,
      fieldName: 'is_active',
      label: $t('common.enabled'),
    },
    {
      component: 'Switch',
      defaultValue: false,
      fieldName: 'is_keep_alive',
      label: $t('system.menu.cache'),
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
        options: getMenuTypeOptions(),
      },
      fieldName: 'type',
      label: $t('system.menu.type'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<MenuRecord>,
  onStatusChange?: (
    newStatus: boolean,
    row: MenuRecord,
  ) => PromiseLike<boolean | undefined>,
): VxeTableGridColumns<MenuRecord> {
  const menuTypeMap = getMenuTypeMap();

  return [
    {
      align: 'left',
      field: 'title',
      minWidth: 180,
      slots: { default: 'title' },
      title: $t('system.menu.menuName'),
      treeNode: true,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: Object.entries(menuTypeMap).map(([value, item]) => ({
          color: item.color,
          label: item.label,
          value,
        })),
      },
      field: 'type',
      title: $t('system.menu.type'),
      width: 100,
    },
    {
      field: 'route_path',
      formatter: ({ cellValue }) => cellValue || '-',
      minWidth: 160,
      title: $t('system.menu.route'),
    },
    {
      field: 'permission_code',
      formatter: ({ cellValue }) => cellValue || '-',
      minWidth: 160,
      title: $t('system.menu.permissionCode'),
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'success', label: $t('system.menu.visible'), value: true },
          { color: 'default', label: $t('system.menu.hidden'), value: false },
        ],
      },
      field: 'is_visible',
      title: $t('system.menu.visible'),
      width: 90,
    },
    {
      cellRender: {
        attrs: { beforeChange: onStatusChange },
        name: onStatusChange ? 'CellSwitch' : 'CellTag',
      },
      field: 'is_active',
      title: $t('system.menu.status'),
      width: 100,
    },
    {
      field: 'sort',
      title: $t('system.menu.sort'),
      width: 90,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'title',
          nameTitle: $t('system.menu.name'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: ['edit', 'delete'],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('system.menu.operation'),
      width: 130,
    },
  ];
}
