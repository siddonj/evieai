import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

const args = process.argv.slice(2)
const runFlagIndex = args.indexOf('--run')
const testTargets = runFlagIndex >= 0
  ? args.slice(runFlagIndex + 1).filter((value) => !value.startsWith('--'))
  : findTestFiles(path.resolve('src'))

if (testTargets.length === 0) {
  console.error('No test files found.')
  process.exit(1)
}

const result = spawnSync(process.execPath, ['--test', '--experimental-strip-types', ...testTargets], {
  stdio: 'inherit',
})

process.exit(result.status ?? 1)

function findTestFiles(rootDir) {
  const files = []
  walk(rootDir, files)
  return files
}

function walk(currentDir, files) {
  for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
    const fullPath = path.join(currentDir, entry.name)
    if (entry.isDirectory()) {
      walk(fullPath, files)
      continue
    }
    if (entry.isFile() && /\.test\.(ts|tsx|mts|cts)$/.test(entry.name)) {
      files.push(fullPath)
    }
  }
}
