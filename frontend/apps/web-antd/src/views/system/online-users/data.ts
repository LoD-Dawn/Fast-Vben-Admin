import type {
  OnActionClickFn,
  VxeTableGridColumns,
} from '#/adapter/vxe-table';
import type { VbenFormSchema } from '#/adapter/form';
import type { UserSessionRecord } from '#/api';

import { formatDateTime } from '@vben/utils';

import { $t } from '#/locales';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'keyword',
      label: $t('system.common.keyword'),
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<UserSessionRecord>,
): VxeTableGridColumns<UserSessionRecord> {
  return [
    {
      field: 'email',
      minWidth: 180,
      title: $t('system.onlineUser.email'),
    },
    {
      field: 'full_name',
      formatter: ({ cellValue }) => cellValue || '-',
      minWidth: 140,
      title: $t('system.onlineUser.fullName'),
    },
    {
      field: 'ip',
      formatter: ({ cellValue }) => cellValue || '-',
      title: $t('system.onlineUser.ip'),
      width: 140,
    },
    {
      field: 'user_agent',
      formatter: ({ cellValue }) => cellValue || '-',
      minWidth: 220,
      showOverflow: true,
      title: $t('system.onlineUser.userAgent'),
    },
    {
      field: 'created_at',
      formatter: ({ cellValue }) =>
        cellValue ? formatDateTime(cellValue) : '-',
      title: $t('system.onlineUser.loginTime'),
      width: 180,
    },
    {
      field: 'last_active_at',
      formatter: ({ cellValue }) =>
        cellValue ? formatDateTime(cellValue) : '-',
      title: $t('system.onlineUser.lastActiveTime'),
      width: 180,
    },
    {
      field: 'expires_at',
      formatter: ({ cellValue }) =>
        cellValue ? formatDateTime(cellValue) : '-',
      title: $t('system.onlineUser.expiresAt'),
      width: 180,
    },
    {
      align: 'center',
      cellRender: {
        attrs: {
          nameField: 'email',
          nameTitle: $t('system.onlineUser.name'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:session:revoke',
            code: 'revoke',
            text: $t('system.onlineUser.revoke'),
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('system.onlineUser.operation'),
      width: 120,
    },
  ];
}
