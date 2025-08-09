#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const pythonScript = path.join(repoRoot, 'scripts', 'build_executable.py');

const cmd = process.platform === 'win32' ? 'python' : 'python3';

const child = spawn(cmd, [pythonScript], {
  stdio: 'inherit',
  cwd: repoRoot,
});

child.on('close', (code) => {
  process.exit(code);
});
