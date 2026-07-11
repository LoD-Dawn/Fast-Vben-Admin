import type { VbenFormSchema } from '#/adapter/form';
import type { OnActionClickFn, VxeTableGridColumns } from '#/adapter/vxe-table';
import type { OAuth2TokenRecord } from '#/api';

export function useGridFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      componentProps: {
        placeholder: '令牌 / 用户 / 邮箱',
      },
      fieldName: 'keyword',
      label: '关键词',
    },
    {
      component: 'Input',
      componentProps: {
        placeholder: '客户端 ID',
      },
      fieldName: 'client_id',
      label: '客户端',
    },
    {
      component: 'Select',
      componentProps: {
        allowClear: true,
        options: [
          { label: '有效', value: false },
          { label: '已吊销', value: true },
        ],
      },
      fieldName: 'revoked',
      label: '状态',
    },
  ];
}

export function useColumns(
  onActionClick: OnActionClickFn<OAuth2TokenRecord>,
): VxeTableGridColumns<OAuth2TokenRecord> {
  return [
    {
      field: 'access_token',
      minWidth: 240,
      showOverflow: true,
      title: '访问令牌',
    },
    {
      field: 'refresh_token',
      minWidth: 220,
      showOverflow: true,
      title: '刷新令牌',
    },
    {
      field: 'client_id',
      minWidth: 150,
      title: '客户端 ID',
    },
    {
      field: 'user_email',
      minWidth: 180,
      title: '用户邮箱',
    },
    {
      field: 'scopes',
      minWidth: 130,
      showOverflow: true,
      title: '授权范围',
    },
    {
      field: 'expires_at',
      title: '过期时间',
      width: 180,
    },
    {
      cellRender: {
        name: 'CellTag',
        options: [
          { color: 'success', label: '有效', value: 'active' },
          { color: 'error', label: '已吊销', value: 'revoked' },
        ],
      },
      field: 'revoked_at',
      formatter: ({ cellValue }) => (cellValue ? 'revoked' : 'active'),
      title: '状态',
      width: 100,
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
          nameField: 'access_token',
          nameTitle: 'OAuth2 令牌',
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          {
            auth: 'system:oauth2-token:delete',
            code: 'revoke',
            text: '吊销',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: '操作',
      width: 100,
    },
  ];
}
