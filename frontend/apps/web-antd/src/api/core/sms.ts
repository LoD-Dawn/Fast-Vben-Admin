import { requestClient } from '#/api/request';

export interface SmsChannelRecord {
  api_key?: null | string;
  api_secret?: null | string;
  callback_url?: null | string;
  code: string;
  created_at?: null | string;
  id: string;
  is_active: boolean;
  is_default: boolean;
  name: string;
  provider: string;
  remark?: null | string;
  signature: string;
  updated_at?: null | string;
}

export interface SmsChannelsResult {
  items: SmsChannelRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type SmsChannelPayload = Omit<
  SmsChannelRecord,
  'created_at' | 'id' | 'updated_at'
>;

export interface SmsTemplateRecord {
  api_template_id?: null | string;
  channel_code?: null | string;
  channel_id?: null | string;
  code: string;
  content: string;
  created_at?: null | string;
  id: string;
  is_active: boolean;
  name: string;
  params: string;
  remark?: null | string;
  type: string;
  updated_at?: null | string;
}

export interface SmsTemplatesResult {
  items: SmsTemplateRecord[];
  page: number;
  page_size: number;
  total: number;
}

export type SmsTemplatePayload = Omit<
  SmsTemplateRecord,
  'channel_code' | 'created_at' | 'id' | 'params' | 'updated_at'
>;

export interface SmsLogRecord {
  api_request_id?: null | string;
  api_receive_code?: null | string;
  api_receive_message?: null | string;
  api_serial_no?: null | string;
  api_send_code?: null | string;
  api_send_message?: null | string;
  api_template_id?: null | string;
  channel_code?: null | string;
  channel_id?: null | string;
  created_at?: null | string;
  id: string;
  mobile: string;
  receive_status: string;
  received_at?: null | string;
  send_status: string;
  sent_at?: null | string;
  template_code?: null | string;
  template_content: string;
  template_id?: null | string;
  template_name?: null | string;
  template_params?: null | string;
  template_type?: null | string;
}

export interface SmsLogsResult {
  items: SmsLogRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface SmsChannelListParams {
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
  provider?: string;
}

export interface SmsTemplateListParams {
  channel_id?: string;
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
  type?: string;
}

export interface SmsLogListParams {
  channel_id?: string;
  keyword?: string;
  mobile?: string;
  page?: number;
  page_size?: number;
  receive_status?: string;
  send_status?: string;
  template_code?: string;
  template_id?: string;
}

export function listSmsChannelsApi(params: SmsChannelListParams = {}) {
  return requestClient.get<SmsChannelsResult>('/sms/channels', { params });
}

export function listSimpleSmsChannelsApi() {
  return requestClient.get<SmsChannelRecord[]>('/sms/channels/simple');
}

export function createSmsChannelApi(data: SmsChannelPayload) {
  return requestClient.post<SmsChannelRecord>('/sms/channels', data);
}

export function updateSmsChannelApi(
  channelId: string,
  data: Partial<SmsChannelPayload>,
) {
  return requestClient.request<SmsChannelRecord>(`/sms/channels/${channelId}`, {
    data,
    method: 'PATCH',
  });
}

export function deleteSmsChannelApi(channelId: string) {
  return requestClient.delete<void>(`/sms/channels/${channelId}`);
}

export function listSmsTemplatesApi(params: SmsTemplateListParams = {}) {
  return requestClient.get<SmsTemplatesResult>('/sms/templates', { params });
}

export function createSmsTemplateApi(data: SmsTemplatePayload) {
  return requestClient.post<SmsTemplateRecord>('/sms/templates', data);
}

export function updateSmsTemplateApi(
  templateId: string,
  data: Partial<SmsTemplatePayload>,
) {
  return requestClient.request<SmsTemplateRecord>(
    `/sms/templates/${templateId}`,
    {
      data,
      method: 'PATCH',
    },
  );
}

export function deleteSmsTemplateApi(templateId: string) {
  return requestClient.delete<void>(`/sms/templates/${templateId}`);
}

export function sendSmsTemplateTestApi(
  templateId: string,
  data: { mobile: string; template_params: Record<string, string> },
) {
  return requestClient.post<SmsLogRecord>(
    `/sms/templates/${templateId}/send-test`,
    data,
  );
}

export function listSmsLogsApi(params: SmsLogListParams = {}) {
  return requestClient.get<SmsLogsResult>('/sms/logs', { params });
}
