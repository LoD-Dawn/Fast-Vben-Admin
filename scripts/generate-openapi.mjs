import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(scriptDir, '..');
const backendDir = join(rootDir, 'backend');
const frontendDir = join(rootDir, 'frontend');
const openapiPath = join(mkdtempSync(join(tmpdir(), 'fast-vben-openapi-')), 'openapi.json');

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: rootDir,
    encoding: 'utf8',
    shell: options.shell ?? false,
    stdio: options.capture ? 'pipe' : 'inherit',
    ...options,
  });

  if (result.status !== 0) {
    const detail = result.stderr || result.stdout || '';
    throw new Error(`${command} ${args.join(' ')} failed\n${detail}`);
  }

  return result.stdout;
}

const openapiJson = run(
  'uv',
  [
    'run',
    'python',
    '-c',
    'import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False))',
  ],
  {
    capture: true,
    cwd: backendDir,
  },
);

writeFileSync(openapiPath, openapiJson, 'utf8');

run('pnpm', ['--dir', frontendDir, 'generate:api'], {
  env: {
    ...process.env,
    OPENAPI_INPUT: openapiPath,
  },
  shell: process.platform === 'win32',
});
