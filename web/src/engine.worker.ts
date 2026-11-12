import { loadPyodide } from 'pyodide'
import { frameMessage, installEngine } from './engine'

// The simulated tree, when no twinky.py answers: twinky's own engine under Pyodide, which sends the
// page what twinky's server would (the layout and the state as text, then each frame's bytes) and takes
// the remote's commands as text, run between frames as twinky's queue runs them

const post = (message: string | ArrayBuffer) =>
  self.postMessage(message, { transfer: typeof message === 'string' ? [] : [message] })

try {
  // Pyodide's files beside the pages, as the build has them
  const pyodide = await loadPyodide({ indexURL: new URL('../pyodide/', self.location.href).href })
  const engine = installEngine(pyodide).Engine()
  self.onmessage = (event: MessageEvent<string>) => engine.command(event.data)
  post(engine.layout)
  const frame = engine.frame
  engine.init()
  let next = Date.now() / 1000 + frame
  const tick = () => {
    post(frameMessage(engine.step()))
    const state = engine.changed_state()
    if (state !== undefined) post(state)
    // as twinky's wait_for: on to the next frame, or once more than a frame late, a frame from now
    const now = Date.now() / 1000
    const delay = next - now
    next = delay < -frame ? now + frame : next + frame
    setTimeout(tick, Math.max(delay, 0) * 1000)
  }
  tick()
} catch (e) {
  post(JSON.stringify({ error: (e as Error).message }))
}
