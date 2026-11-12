import type { PyodideInterface } from 'pyodide'
import type { PyProxy } from 'pyodide/ffi'
import files from 'virtual:engine'

// Where the engine's files go in Pyodide's own file system, and the folder it runs in, as twinky runs
// in the repo
const HOME = '/twinky'

/** browser.Engine, the page's own twinky: the methods the worker calls on it. */
export type Engine = PyProxy & {
  layout: string // its message
  frame: number // seconds a frame, core.FRAME
  init(t?: number): void
  step(t?: number): PyProxy // the frame's message, as bytes
  command(message: string): void
  changed_state(): string | undefined
}

/** Puts the engine's files (twinky's .py but those that reach for the device, the server or the TUI,
 * the layouts, looks and saves, and pytweening and xled_plus's colours) in Pyodide, and gives its
 * browser module, whose Engine() starts on the simulated cone as twinky --sim starts. */
export function installEngine(pyodide: PyodideInterface): PyProxy & { Engine(): Engine } {
  for (const [path, source] of Object.entries(files)) {
    const file = `${HOME}/${path}`
    pyodide.FS.mkdirTree(file.slice(0, file.lastIndexOf('/')))
    pyodide.FS.writeFile(file, source)
  }
  pyodide.runPython(`import os, sys\nsys.path.insert(0, ${JSON.stringify(HOME)})\nos.chdir(${JSON.stringify(HOME)})`)
  return pyodide.pyimport('browser')
}

/** A frame's message as the server sends it, out of Python's bytes. */
export function frameMessage(message: PyProxy): ArrayBuffer {
  const bytes = message.toJs() as Uint8Array
  message.destroy()
  return bytes.buffer as ArrayBuffer
}
