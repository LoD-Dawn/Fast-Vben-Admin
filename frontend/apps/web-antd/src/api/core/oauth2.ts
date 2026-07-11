import { requestClient } from '#/api/request';

export interface OAuth2ClientRecord {
  access_token_validity_seconds: number;
  additional_information?: null | string;
  authorities?: null | string;
  authorized_grant_types: string;
  auto_approve_scopes?: null | string;
  client_id: string;
  client_secret?: null | string;
  created_at?: null | string;
  description?: null | string;
  id: string;
  is_active: boolean;
  logo?: null | string;
  name: string;
  redirect_uris?: null | string;
  refresh_token_validity_seconds: number;
  resource_ids?: null | string;
  scopes?: null | string;
  updated_at?: null | string;
}

export interface OAuth2ClientsResult {
  items: OAuth2ClientRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type OAuth2ClientPayload = Omit<
  OAuth2ClientRecord,
  'created_at' | 'id' | 'updated_at'
>;

export interface OAuth2TokenRecord {
  access_token: string;
  client_id: string;
  created_at?: null | string;
  expires_at: string;
  id: string;
  refresh_token?: null | string;
  revoked_at?: null | string;
  scopes?: null | string;
  user_email?: null | string;
  user_full_name?: null | string;
  user_id?: null | string;
}

export interface OAuth2TokensResult {
  items: OAuth2TokenRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface OAuth2ClientListParams {
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}

export interface OAuth2TokenListParams {
  client_id?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
  revoked?: boolean;
  user_id?: string;
}

export function listOAuth2ClientsApi(params: OAuth2ClientListParams = {}) {
  return requestClient.get<OAuth2ClientsResult>('/oauth2/clients', { params });
}

export function getOAuth2ClientApi(clientId: string) {
  return requestClient.get<OAuth2ClientRecord>(`/oauth2/clients/${clientId}`);
}

export function createOAuth2ClientApi(data: OAuth2ClientPayload) {
  return requestClient.post<OAuth2ClientRecord>('/oauth2/clients', data);
}

export function updateOAuth2ClientApi(
  clientId: string,
  data: Partial<OAuth2ClientPayload>,
) {
  return requestClient.request<OAuth2ClientRecord>(
    `/oauth2/clients/${clientId}`,
    {
      data,
      method: 'PATCH',
    },
  );
}

export function deleteOAuth2ClientApi(clientId: string) {
  return requestClient.delete<void>(`/oauth2/clients/${clientId}`);
}

export function listOAuth2TokensApi(params: OAuth2TokenListParams = {}) {
  return requestClient.get<OAuth2TokensResult>('/oauth2/tokens', { params });
}

export function revokeOAuth2TokenApi(tokenId: string) {
  return requestClient.delete<void>(`/oauth2/tokens/${tokenId}`);
}
