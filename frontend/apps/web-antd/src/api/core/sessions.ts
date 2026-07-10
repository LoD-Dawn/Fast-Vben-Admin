import { requestClient } from '#/api/request';

export interface UserSessionRecord {
  created_at: null | string;
  email: string;
  expires_at: string;
  full_name: null | string;
  id: string;
  ip: null | string;
  last_active_at: null | string;
  user_agent: null | string;
  user_id: string;
}

export interface UserSessionListResult {
  items: UserSessionRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface UserSessionListParams {
  keyword?: string;
  page?: number;
  page_size?: number;
}

export function listUserSessionsApi(params: UserSessionListParams = {}) {
  return requestClient.get<UserSessionListResult>('/sessions', { params });
}

export function revokeUserSessionApi(sessionId: string) {
  return requestClient.post<{ message: string }>(`/sessions/${sessionId}/revoke`);
}
