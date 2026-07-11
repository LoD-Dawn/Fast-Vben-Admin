import { listUsersApi } from './users';
import { requestClient } from '#/api/request';

export interface SiteMessageTemplateRecord {
  code: string;
  content: string;
  created_at?: null | string;
  id: string;
  is_active: boolean;
  name: string;
  params: string;
  remark?: null | string;
  sender_name: string;
  type: string;
  updated_at?: null | string;
}

export interface SiteMessageTemplatesResult {
  items: SiteMessageTemplateRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type SiteMessageTemplatePayload = Omit<
  SiteMessageTemplateRecord,
  'created_at' | 'id' | 'params' | 'updated_at'
>;

export interface SiteMessageRecord {
  content: string;
  created_at?: null | string;
  id: string;
  is_read: boolean;
  notice_id?: null | string;
  read_at?: null | string;
  sender_name?: null | string;
  template_code?: null | string;
  template_id?: null | string;
  template_name?: null | string;
  template_params?: null | string;
  title: string;
  type: string;
  user_email?: null | string;
  user_full_name?: null | string;
  user_id: string;
}

export interface SiteMessagesResult {
  items: SiteMessageRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface SiteMessageTemplateListParams {
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
  type?: string;
}

export interface SiteMessageListParams {
  is_read?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
  template_code?: string;
  type?: string;
  user_id?: string;
}

export function listSiteMessageTemplatesApi(
  params: SiteMessageTemplateListParams = {},
) {
  return requestClient.get<SiteMessageTemplatesResult>(
    '/site-messages/templates',
    { params },
  );
}

export function createSiteMessageTemplateApi(
  data: SiteMessageTemplatePayload,
) {
  return requestClient.post<SiteMessageTemplateRecord>(
    '/site-messages/templates',
    data,
  );
}

export function updateSiteMessageTemplateApi(
  templateId: string,
  data: Partial<SiteMessageTemplatePayload>,
) {
  return requestClient.request<SiteMessageTemplateRecord>(
    `/site-messages/templates/${templateId}`,
    {
      data,
      method: 'PATCH',
    },
  );
}

export function deleteSiteMessageTemplateApi(templateId: string) {
  return requestClient.delete<void>(`/site-messages/templates/${templateId}`);
}

export function sendSiteMessageTemplateTestApi(
  templateId: string,
  data: { template_params: Record<string, string>; user_id: string },
) {
  return requestClient.post<SiteMessageRecord>(
    `/site-messages/templates/${templateId}/send-test`,
    data,
  );
}

export function listSiteMessagesApi(params: SiteMessageListParams = {}) {
  return requestClient.get<SiteMessagesResult>('/site-messages/messages', {
    params,
  });
}

export function deleteSiteMessageApi(messageId: string) {
  return requestClient.delete<void>(`/site-messages/messages/${messageId}`);
}

export async function listSimpleUsersApi() {
  const result = await listUsersApi({ is_active: true, page: 1, page_size: 100 });
  return result.items.map((user) => ({
    ...user,
    label: user.full_name ? `${user.full_name} (${user.email})` : user.email,
  }));
}
