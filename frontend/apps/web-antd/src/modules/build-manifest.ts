export const buildManifest = {
  "schema_version": 2,
  "edition": "erp",
  "source_revision": "2da3c929883b35cd296b49da970072c3cb6fdfa7",
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
      "code": "erp",
      "version": "0.1.0",
      "migration_namespace": "erp",
      "migration_heads": [
        "erp_trade_doc_snapshots"
      ],
      "openapi_sha256": "sha256:45d3b217d856a0f1e94122b6341aa33345a73e5376f6584972507a02c2b605a7"
    }
  ],
  "manifest_digest": "sha256:e12c159e39f90dc3c46db93be231ee1227ab1a6aca0c4f9f3474416b66c241cb"
} as const;
