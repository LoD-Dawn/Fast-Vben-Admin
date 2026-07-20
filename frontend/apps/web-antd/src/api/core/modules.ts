import { requestClient } from '#/api/request';

export interface BuildManifest {
  platform_contract_version: number;
  schema_version: 2;
  source_revision: string;
  edition: string;
  manifest_digest: string;
  modules: Array<{
    code: string;
    migration_heads: string[];
    migration_namespace: string;
    openapi_sha256: string;
    version: string;
  }>;
  platform_version: string;
}

export function getBuildManifestApi() {
  return requestClient.get<BuildManifest>('/platform/modules/manifest');
}
