#!/usr/bin/env node
/**
 * Download KR-Gaiji charlist + PNG images from kanripo/KR-Gaiji into data/gaiji/.
 * Run from the plugin package root before release or after upstream updates.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.join(__dirname, '..');
const gaijiDir = path.join(packageRoot, 'data/gaiji');
const imagesDir = path.join(gaijiDir, 'images');
const zipPath = path.join(packageRoot, '.cache-kr-gaiji.zip');

fs.mkdirSync(imagesDir, { recursive: true });

console.log('[download-gaiji] fetching kanripo/KR-Gaiji…');
execFileSync(
  'curl',
  ['-sL', 'https://github.com/kanripo/KR-Gaiji/archive/refs/heads/master.zip', '-o', zipPath],
  { stdio: 'inherit' },
);

const tmp = path.join(packageRoot, '.cache-kr-gaiji');
fs.rmSync(tmp, { recursive: true, force: true });
fs.mkdirSync(tmp, { recursive: true });
execFileSync('unzip', ['-q', zipPath, '-d', tmp], { stdio: 'inherit' });

const extracted = path.join(tmp, 'KR-Gaiji-master');
fs.copyFileSync(path.join(extracted, 'charlist.org.txt'), path.join(gaijiDir, 'charlist.org.txt'));

for (const name of fs.readdirSync(path.join(extracted, 'images'))) {
  if (name.endsWith('.png')) {
    fs.copyFileSync(path.join(extracted, 'images', name), path.join(imagesDir, name));
  }
}

const pngCount = fs.readdirSync(imagesDir).filter((n) => n.endsWith('.png')).length;
console.log(`[download-gaiji] charlist + ${pngCount} PNG files → data/gaiji/`);

fs.rmSync(tmp, { recursive: true, force: true });
fs.rmSync(zipPath, { force: true });
