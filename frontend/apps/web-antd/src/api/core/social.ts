import { requestClient } from '#/api/request';

export interface SocialClientRecord {
  agent_id?: null | string;
  client_id: string;
  client_secret?: null | string;
  created_at?: null | string;
  id: string;
  is_active: boolean;
  name: string;
  remark?: null | string;
  social_type: string;
  updated_at?: null | string;
  user_type: string;
}

export interface SocialClientsResult {
  items: SocialClientRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type SocialClientPayload = Omit<
  SocialClientRecord,
  'created_at' | 'id' | 'updated_at'
>;

export type SocialClientUpdatePayload = Partial<SocialClientPayload> & {
  current_password?: string;
};

export interface SocialUserRecord {
  avatar?: null | string;
  code?: null | string;
  created_at?: null | string;
  id: string;
  nickname?: null | string;
  openid: string;
  raw_token_info?: null | string;
  raw_user_info?: null | string;
  social_client_id?: null | string;
  state?: null | string;
  token?: null | string;
  type: string;
  unionid?: null | string;
  updated_at?: null | string;
  user_email?: null | string;
  user_full_name?: null | string;
  user_id?: null | string;
}

export interface SocialUsersResult {
  items: SocialUserRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface SocialClientListParams {
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
  social_type?: string;
  user_type?: string;
}

export interface SocialUserListParams {
  keyword?: string;
  openid?: string;
  page?: number;
  page_size?: number;
  type?: string;
  user_id?: string;
}

export function listSocialClientsApi(params: SocialClientListParams = {}) {
  return requestClient.get<SocialClientsResult>('/social/clients', { params });
}

export function getSocialClientApi(clientId: string) {
  return requestClient.get<SocialClientRecord>(`/social/clients/${clientId}`);
}

export function createSocialClientApi(data: SocialClientPayload) {
  return requestClient.post<SocialClientRecord>('/social/clients', data);
}

export function updateSocialClientApi(
  clientId: string,
  data: SocialClientUpdatePayload,
) {
  return requestClient.request<SocialClientRecord>(
    `/social/clients/${clientId}`,
    {
      data,
      method: 'PATCH',
    },
  );
}

export function deleteSocialClientApi(clientId: string) {
  return requestClient.delete<void>(`/social/clients/${clientId}`);
}

export function listSocialUsersApi(params: SocialUserListParams = {}) {
  return requestClient.get<SocialUsersResult>('/social/users', { params });
}

export function getSocialUserApi(userId: string) {
  return requestClient.get<SocialUserRecord>(`/social/users/${userId}`);
}

export function bindSocialUserApi(socialUserId: string, userId: string) {
  return requestClient.post<SocialUserRecord>(`/social/users/${socialUserId}/bind`, {
    user_id: userId,
  });
}

export function unbindSocialUserApi(socialUserId: string) {
  return requestClient.post<SocialUserRecord>(`/social/users/${socialUserId}/unbind`);
}
