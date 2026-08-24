#!/usr/bin/env node
// Runs the full local test battery. Ignores extra argv (the global
// pre-commit hook appends `--run`). CI runs the pwsh checks with
// -RepoOnly instead of this runner; see .github/workflows/validate.yml.
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const tests = dirname(fileURLToPath(import.meta.url));
const steps = [
  ['pwsh', ['-NoProfile', '-File', join(tests, 'check-shikigarasu-contract.ps1')]],
  ['pwsh', ['-NoProfile', '-File', join(tests, 'check-codex-authority.ps1')]],
  ['python', ['-X', 'utf8', join(tests, 'test_agy_routing.py')]],
  ['python', ['-X', 'utf8', join(tests, 'test_probe_shikigarasu_contract.py')]],
];

let failed = 0;
for (const [cmd, args] of steps) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', shell: false });
  if (r.status !== 0) failed++;
}
if (failed) {
  console.error(`\n${failed} test step(s) failed`);
  process.exit(1);
}
console.log('\nall test steps passed');
