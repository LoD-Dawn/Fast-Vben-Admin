import { requestClient } from '#/api/request';

export interface MailAccountRecord {
  code: string;
  created_at?: null | string;
  email: string;
  host: string;
  id: string;
  is_active: boolean;
  is_default: boolean;
  name: string;
  password?: null | string;
  port: number;
  remark?: null | string;
  ssl_enable: boolean;
  starttls_enable: boolean;
  updated_at?: null | string;
  username?: null | string;
}

export interface MailAccountsResult {
  items: MailAccountRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type MailAccountPayload = Omit<
  MailAccountRecord,
  'created_at' | 'id' | 'updated_at'
>;

export interface MailTemplateRecord {
  account_code?: null | string;
  account_id?: null | string;
  code: string;
  content: string;
  created_at?: null | string;
  id: string;
  is_active: boolean;
  name: string;
  nickname?: null | string;
  params: string;
  remark?: null | string;
  title: string;
  updated_at?: null | string;
}

export interface MailTemplatesResult {
  items: MailTemplateRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type MailTemplatePayload = Omit<
  MailTemplateRecord,
  'account_code' | 'created_at' | 'id' | 'params' | 'updated_at'
>;

export interface MailLogRecord {
  account_code?: null | string;
  account_id?: null | string;
  account_name?: null | string;
  content: string;
  created_at?: null | string;
  from_email: string;
  from_name?: null | string;
  id: string;
  message_id?: null | string;
  send_code?: null | string;
  send_message?: null | string;
  send_status: string;
  sent_at?: null | string;
  template_code?: null | string;
  template_id?: null | string;
  template_name?: null | string;
  template_params?: null | string;
  title: string;
  to_email: string;
}

export interface MailLogsResult {
  items: MailLogRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface MailAccountListParams {
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}

export interface MailTemplateListParams {
  account_id?: string;
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
}

export interface MailLogListParams {
  account_id?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
  send_status?: string;
  template_id?: string;
  to_email?: string;
}

export function listMailAccountsApi(params: MailAccountListParams = {}) {
  return requestClient.get<MailAccountsResult>('/mail/accounts', { params });
}

export function listSimpleMailAccountsApi() {
  return requestClient.get<MailAccountRecord[]>('/mail/accounts/simple');
}

export function createMailAccountApi(data: MailAccountPayload) {
  return requestClient.post<MailAccountRecord>('/mail/accounts', data);
}

export function updateMailAccountApi(
  accountId: string,
  data: Partial<MailAccountPayload>,
) {
  return requestClient.request<MailAccountRecord>(`/mail/accounts/${accountId}`, {
    data,
    method: 'PATCH',
  });
}

export function deleteMailAccountApi(accountId: string) {
  return requestClient.delete<void>(`/mail/accounts/${accountId}`);
}

export function listMailTemplatesApi(params: MailTemplateListParams = {}) {
  return requestClient.get<MailTemplatesResult>('/mail/templates', { params });
}

export function createMailTemplateApi(data: MailTemplatePayload) {
  return requestClient.post<MailTemplateRecord>('/mail/templates', data);
}

export function updateMailTemplateApi(
  templateId: string,
  data: Partial<MailTemplatePayload>,
) {
  return requestClient.request<MailTemplateRecord>(
    `/mail/templates/${templateId}`,
    {
      data,
      method: 'PATCH',
    },
  );
}

export function deleteMailTemplateApi(templateId: string) {
  return requestClient.delete<void>(`/mail/templates/${templateId}`);
}

export function sendMailTemplateTestApi(
  templateId: string,
  data: { template_params: Record<string, string>; to_email: string },
) {
  return requestClient.post<MailLogRecord>(
    `/mail/templates/${templateId}/send-test`,
    data,
  );
}

export function listMailLogsApi(params: MailLogListParams = {}) {
  return requestClient.get<MailLogsResult>('/mail/logs', { params });
}

export function resendMailLogApi(logId: string) {
  return requestClient.post<MailLogRecord>(`/mail/logs/${logId}/resend`);
}
