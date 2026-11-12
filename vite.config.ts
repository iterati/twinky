import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const ROOT = import.meta.dirname
// what reaches for the device, the server's sockets and threads, or the TUI, which the page's engine
// leaves to twinky.py
const OUT_OF_PAGE = ['device.py', 'server.py', 'twinky.py']
// Pyodide's own files, which the page's engine loads from the build, never a CDN
const PYODIDE = join(ROOT, 'node_modules', 'pyodide')
const PYODIDE_FILES = ['pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json']

function list(dir: string, test: (name: string) => boolean): string[] {
  return existsSync(join(ROOT, dir))
    ? readdirSync(join(ROOT, dir))
        .filter(test)
        .map((name) => join(dir, name))
    : []
}

/** The files the page's engine runs, by their path in the repo or under site-packages: twinky's .py
 * but those, the layouts, the looks and the saves, and from .venv pytweening and xled_plus's
 * colours, which are pure Python. */
function engineFiles(): Record<string, string> {
  const lib = join('.venv', 'lib')
  const python = list(lib, (name) => name.startsWith('python'))[0]
  if (!python) throw new Error('No .venv/lib/python*: make the venv and install requirements.txt (README)')
  const site = join(python, 'site-packages')
  const paths = [
    ...list('.', (name) => name.endsWith('.py') && !OUT_OF_PAGE.includes(name)),
    ...['layouts', 'looks', 'saves'].flatMap((dir) => list(dir, (name) => name.endsWith('.json'))),
  ]
  const packages = [
    ...list(join(site, 'pytweening'), (name) => name.endsWith('.py')),
    join(site, 'xled_plus', '__init__.py'),
    join(site, 'xled_plus', 'ledcolor.py'),
  ]
  return Object.fromEntries([
    ...paths.map((path) => [path, readFileSync(join(ROOT, path), 'utf8')]),
    ...packages.map((path) => [path.slice(site.length + 1), readFileSync(join(ROOT, path), 'utf8')]),
  ])
}

/** virtual:engine, the engine's files, read as the page builds. */
function engine(): Plugin {
  const id = 'virtual:engine'
  return {
    name: 'twinky-engine',
    resolveId: (source) => (source === id ? '\0' + id : undefined),
    load(source) {
      if (source !== '\0' + id) return
      const files = engineFiles()
      for (const path of Object.keys(files)) if (existsSync(join(ROOT, path))) this.addWatchFile(join(ROOT, path))
      return `export default ${JSON.stringify(files)}`
    },
  }
}

/** Pyodide at pyodide/ beside the pages, served by the dev server and copied into the build. */
function pyodide(): Plugin {
  return {
    name: 'twinky-pyodide',
    configureServer(server) {
      server.middlewares.use('/pyodide', (request, response, next) => {
        const name = (request.url ?? '').slice(1).split('?')[0]
        if (!PYODIDE_FILES.includes(name)) return next()
        response.setHeader('Content-Type', name.endsWith('.wasm') ? 'application/wasm' : 'application/octet-stream')
        response.end(readFileSync(join(PYODIDE, name)))
      })
    },
    generateBundle() {
      for (const name of PYODIDE_FILES) {
        this.emitFile({ type: 'asset', fileName: `pyodide/${name}`, source: readFileSync(join(PYODIDE, name)) })
      }
    },
  }
}

export default defineConfig({
  root: 'web',
  // relative, so the pages work from any folder, such as the site's /twinky/
  base: './',
  plugins: [react(), engine(), pyodide()],
  worker: { format: 'es', plugins: () => [engine()] },
  optimizeDeps: { exclude: ['pyodide'] },
  build: {
    outDir: 'dist',
    // three is most of the simulator, which twinky serves locally, so one big chunk is fine
    chunkSizeWarningLimit: 1000,
    // the simulator at /, the remote at /remote
    rollupOptions: { input: { main: 'web/index.html', remote: 'web/remote/index.html' } },
  },
  server: {
    proxy: { '/ws': { target: 'ws://localhost:8016', ws: true } },
  },
})
