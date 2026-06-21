import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import ts from 'typescript'

const projectRoot = path.resolve(process.cwd())
const sourceRoot = path.join(projectRoot, 'src')
const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'evieai-tests-'))

const args = process.argv.slice(2)
const runIndex = args.indexOf('--run')
const requestedTests = runIndex >= 0
  ? args.slice(runIndex + 1).filter((value) => !value.startsWith('--'))
  : await findFiles(sourceRoot, /\.test\.(ts|tsx|mts|cts)$/)

if (requestedTests.length === 0) {
  console.error('No test files found.')
  process.exit(1)
}

const sourceFiles = await findFiles(sourceRoot, /\.(ts|tsx|mts|cts)$/)
for (const file of sourceFiles) {
  await transpileFile(file, projectRoot, tempRoot)
}

const testTargets = requestedTests.map((file) => {
  const absolute = path.isAbsolute(file) ? file : path.join(projectRoot, file)
  const relative = path.relative(projectRoot, absolute)
  return path.join(tempRoot, relative).replace(/\.(tsx?|mts|cts)$/, '.js')
})

const result = spawnSync(process.execPath, ['--test', ...testTargets], { stdio: 'inherit' })
process.exit(result.status ?? 1)

async function transpileFile(filePath, rootDir, outRoot) {
  const source = await fs.readFile(filePath, 'utf8')
  const rewritten = rewriteImportExtensions(source)
  const output = ts.transpileModule(rewritten, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2020,
      module: ts.ModuleKind.ESNext,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: filePath,
  }).outputText

  const relative = path.relative(rootDir, filePath)
  const outPath = path.join(outRoot, relative).replace(/\.(tsx?|mts|cts)$/, '.js')
  await fs.mkdir(path.dirname(outPath), { recursive: true })
  await fs.writeFile(outPath, output)
}

function rewriteImportExtensions(source) {
  return source
    .replace(/(from\s+['"])([^'"]+)(['"])/g, (_, prefix, specifier, suffix) => `${prefix}${normalizeSpecifier(specifier)}${suffix}`)
    .replace(/(import\(\s*['"])([^'"]+)(['"]\s*\))/g, (_, prefix, specifier, suffix) => `${prefix}${normalizeSpecifier(specifier)}${suffix}`)
    .replace(/(export\s+[^'"]+from\s+['"])([^'"]+)(['"])/g, (_, prefix, specifier, suffix) => `${prefix}${normalizeSpecifier(specifier)}${suffix}`)
}

function normalizeSpecifier(specifier) {
  if (!specifier.startsWith('.')) return specifier
  if (/\.(?:js|mjs|cjs|json)$/i.test(specifier)) return specifier
  if (/\.(?:ts|tsx|mts|cts)$/i.test(specifier)) {
    return specifier.replace(/\.(?:ts|tsx|mts|cts)$/i, '.js')
  }
  return `${specifier}.js`
}

async function findFiles(rootDir, pattern) {
  const matches = []
  await walk(rootDir, pattern, matches)
  return matches
}

async function walk(currentDir, pattern, matches) {
  for (const entry of await fs.readdir(currentDir, { withFileTypes: true })) {
    const fullPath = path.join(currentDir, entry.name)
    if (entry.isDirectory()) {
      await walk(fullPath, pattern, matches)
      continue
    }
    if (entry.isFile() && pattern.test(entry.name) && !entry.name.endsWith('.d.ts')) {
      matches.push(fullPath)
    }
  }
}
