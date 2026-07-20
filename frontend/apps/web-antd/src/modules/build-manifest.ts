export const buildManifest = {
  "schema_version": 2,
  "edition": "suite",
  "source_revision": "f4e81e61090a36ac13ab0e64e8591d1d8a85d731",
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
  "manifest_digest": "sha256:8c644581b6acb105bf02677f409827b9c8a19a3b49f1820d26b6d370b6e674f4"
} as const;
