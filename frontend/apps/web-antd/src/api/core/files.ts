import type {
  FileAssetPublic,
  FileAssetsPublic,
  FileStorageChannelCreate,
  FileStorageChannelPublic,
  FileStorageChannelsPublic,
  FileStorageChannelUpdate,
  StorageConfigPublic,
  UploadConfigPublic,
  UploadConfigUpdate,
} from '#/api/generated';

import { requestClient } from '#/api/request';

export type FileAssetRecord = FileAssetPublic;
export type FileAssetListResult = FileAssetsPublic;
export type FileStorageChannelRecord = FileStorageChannelPublic;
export type FileStorageChannelListResult = FileStorageChannelsPublic;
export type FileStorageChannelCreatePayload = FileStorageChannelCreate;
export type FileStorageChannelUpdatePayload = FileStorageChannelUpdate;
export type UploadConfigRecord = UploadConfigPublic;
export type UploadConfigPayload = UploadConfigUpdate;

export interface FileAssetListParams {
  keyword?: string;
  is_public?: boolean;
  page?: number;
  page_size?: number;
  storage_provider?: string;
}

export interface FileStorageChannelListParams {
  is_active?: boolean;
  keyword?: string;
  page?: number;
  page_size?: number;
  provider?: string;
}

export function listFilesApi(params: FileAssetListParams = {}) {
  return requestClient.get<FileAssetListResult>('/files', { params });
}

export function uploadFileApi(file: File, isPublic = false) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('is_public', String(isPublic));

  return requestClient.post<FileAssetRecord>('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
}

export function deleteFileApi(fileId: string) {
  return requestClient.delete<void>(`/files/${fileId}`);
}

export function getStorageConfigApi() {
  return requestClient.get<StorageConfigPublic>('/files/storage-config');
}

export function listFileStorageChannelsApi(
  params: FileStorageChannelListParams = {},
) {
  return requestClient.get<FileStorageChannelListResult>(
    '/files/storage-channels',
    { params },
  );
}

export function createFileStorageChannelApi(
  data: FileStorageChannelCreatePayload,
) {
  return requestClient.post<FileStorageChannelRecord>(
    '/files/storage-channels',
    data,
  );
}

export function updateFileStorageChannelApi(
  channelId: string,
  data: FileStorageChannelUpdatePayload,
) {
  return requestClient.request<FileStorageChannelRecord>(
    `/files/storage-channels/${channelId}`,
    {
      data,
      method: 'PATCH',
    },
  );
}

export function deleteFileStorageChannelApi(channelId: string) {
  return requestClient.delete<void>(`/files/storage-channels/${channelId}`);
}

export function testFileStorageChannelApi(channelId: string) {
  return requestClient.post<{ message: string }>(
    `/files/storage-channels/${channelId}/test`,
  );
}

export function getUploadConfigApi() {
  return requestClient.get<UploadConfigRecord>('/files/upload-config');
}

export function updateUploadConfigApi(data: UploadConfigPayload) {
  return requestClient.request<UploadConfigRecord>('/files/upload-config', {
    data,
    method: 'PATCH',
  });
}

export function getFileDownloadUrl(fileId: string) {
  return `/files/${fileId}/download`;
}
