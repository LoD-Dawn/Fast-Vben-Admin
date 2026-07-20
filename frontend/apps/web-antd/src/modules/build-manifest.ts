export const buildManifest = {
  "schema_version": 2,
  "edition": "suite",
  "source_revision": "c3bcfa563a93399bc6a4fcaeff28b19703c2b90b",
  "platform_contract_version": 1,
  "platform_version": "1.0.0",
  "modules": [
    {
      "code": "platform",
      "version": "1.0.0",
      "migration_namespace": "platform",
      "migration_heads": [
        "c7e1a5f9b3d6"
      ],
      "openapi_sha256": "sha256:91324c327537ab2baf38536ed6b852c4c13cbc6daba4055485e48e69a7c533ed"
    },
    {
      "code": "items",
      "version": "1.0.0",
      "migration_namespace": "items",
      "migration_heads": [
        "items_enable_tenant_rls"
      ],
      "openapi_sha256": "sha256:131ecf3acc5f1e4a6a3e06914bb117e12922ac87836d891486127afca13ce100"
    }
  ],
  "manifest_digest": "sha256:b36d3cebded42266f4db5f06e193d73b37486ceea76518f5f9998bb9288b9fa5"
} as const;
