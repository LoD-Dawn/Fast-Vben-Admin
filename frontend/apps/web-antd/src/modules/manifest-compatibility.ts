import { buildManifest } from './build-manifest';

interface RuntimeManifest {
  manifest_digest: string;
}

export class ManifestMismatchError extends Error {
  constructor(serverDigest: string) {
    super(
      `Edition manifest mismatch: frontend=${buildManifest.manifest_digest}, server=${serverDigest}`,
    );
    this.name = 'ManifestMismatchError';
  }
}

export function assertManifestCompatibility(manifest: RuntimeManifest): void {
  if (manifest.manifest_digest !== buildManifest.manifest_digest) {
    throw new ManifestMismatchError(manifest.manifest_digest);
  }
}
