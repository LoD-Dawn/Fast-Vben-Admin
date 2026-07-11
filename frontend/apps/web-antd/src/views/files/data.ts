import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { FileAssetRecord } from '#/api';

import { $t } from '#/locales';

export function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: $t('files.searchPlaceholder'),
      },
      fieldName: 'keyword',
      label: $t('files.keyword'),
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: 'local', value: 'local' },
          { label: 's3', value: 's3' },
        ],
      },
      fieldName: 'storage_provider',
      label: '存储类型',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: $t('system.common.yes'), value: true },
          { label: $t('system.common.no'), value: false },
        ],
      },
      fieldName: 'is_public',
      label: $t('files.public'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<FileAssetRecord>,
): VxeTableGridColumns<FileAssetRecord> {
  return [
    {
      field: 'original_name',
      minWidth: 200,
      showOverflow: true,
      title: $t('files.fileName'),
    },
    {
      field: 'extension',
      title: $t('files.extension'),
      width: 100,
    },
    {
      field: 'content_type',
      minWidth: 160,
      showOverflow: true,
      title: $t('files.contentType'),
    },
    {
      field: 'size',
      formatter: ({ cellValue }) => formatFileSize(cellValue),
      title: $t('files.size'),
      width: 120,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'default', label: 'local', value: 'local' },
          { color: 'processing', label: 's3', value: 's3' },
        ],
      },
      field: 'storage_provider',
      title: $t('files.storage'),
      width: 100,
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
      title: $t('files.public'),
      width: 90,
    },
    {
      field: 'created_at',
      title: $t('files.uploadedAt'),
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'original_name',
          nameTitle: $t('files.item'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          { code: 'download', text: $t('files.download') },
          {
            auth: 'system:file:delete',
            code: 'delete',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('files.operation'),
      width: 130,
    },
  ];
}
