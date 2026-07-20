import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(scriptDir, '..');
const backendDir = join(rootDir, 'backend');

function readOption(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
}

const edition = readOption('--edition') ?? process.env.APP_EDITION ?? 'suite';
if (!/^[a-z][a-z0-9_-]*$/.test(edition)) {
  throw new Error(`Invalid edition: ${edition}`);
}
const buildImages = process.argv.includes('--images');
const skipFrontend = process.argv.includes('--skip-frontend');
const releaseBuild = process.argv.includes('--release');
const artifactDir = join(rootDir, 'artifacts', edition);
const manifestPath = join(artifactDir, 'build-manifest.json');

function run(command, args, options = {}) {
  if (process.platform === 'win32' && command === 'pnpm') {
    const commandLine = ['call', command, ...args]
      .map((part) => (/[\s"]/u.test(part) ? `"${part.replaceAll('"', '\\"')}"` : part))
      .join(' ');
    execFileSync(process.env.ComSpec ?? 'cmd.exe', ['/d', '/s', '/c', commandLine], {
      cwd: rootDir,
      stdio: 'inherit',
      ...options,
    });
    return;
  }
  execFileSync(command, args, {
    cwd: rootDir,
    stdio: 'inherit',
    ...options,
  });
}

if (releaseBuild) {
  const status = execFileSync('git', ['status', '--porcelain'], {
    cwd: rootDir,
    encoding: 'utf8',
  }).trim();
  if (status) {
    throw new Error('--release requires a clean Git worktree');
  }
}

mkdirSync(artifactDir, { recursive: true });
run('uv', [
  'run',
  'python',
  '-m',
  'app.modules.generate_manifest',
  '--edition',
  edition,
  '--output',
  manifestPath,
], { cwd: backendDir, env: { ...process.env, APP_EDITION: edition } });

if (!skipFrontend) {
  run('node', ['scripts/generate-openapi.mjs', '--edition', edition, '--manifest', manifestPath]);
  run('pnpm', ['--dir', 'frontend', '-F', '@vben/web-antd', 'run', 'build']);
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
writeFileSync(
  join(artifactDir, 'artifact-metadata.json'),
  `${JSON.stringify({
    edition,
    source_revision: manifest.source_revision,
    manifest_digest: manifest.manifest_digest,
    schema_version: manifest.schema_version,
  }, null, 2)}\n`,
  'utf8',
);

if (buildImages) {
  const manifestArgument = `artifacts/${edition}/build-manifest.json`;
  run('docker', [
    'build',
    '--file',
    'backend/Dockerfile',
    '--build-arg',
    `BUILD_MANIFEST=${manifestArgument}`,
    '--label',
    `org.opencontainers.image.revision=${manifest.source_revision}`,
    '--label',
    `io.fast-vben.edition=${edition}`,
    '--label',
    `io.fast-vben.manifest-digest=${manifest.manifest_digest}`,
    '--tag',
    `fast-vben-admin/backend:${edition}`,
    '.',
  ]);
  run('docker', [
    'build',
    '--file',
    'frontend/Dockerfile',
    '--label',
    `org.opencontainers.image.revision=${manifest.source_revision}`,
    '--label',
    `io.fast-vben.edition=${edition}`,
    '--label',
    `io.fast-vben.manifest-digest=${manifest.manifest_digest}`,
    '--tag',
    `fast-vben-admin/frontend:${edition}`,
    '.',
  ]);
}

process.stdout.write(`${manifestPath}\n`);
