import { loadPyodide } from 'pyodide'
import { frameMessage, installEngine } from './engine'

// The simulated tree, when no twinky.py answers: twinky's own engine under Pyodide, which sends the
// page what twinky's server would (the layout and the state as text, then each frame's bytes) and takes
// the remote's commands as text, run between frames as twinky's queue runs them

const post = (message: string | ArrayBuffer) =>
  self.postMessage(message, { transfer: typeof message === 'string' ? [] : [message] })
// the page shows the engine's failure, and the tree stops, as twinky's animation thread would
const fail = (e: unknown) => post(JSON.stringify({ error: (e as Error).message }))

try {
  // Pyodide's files beside the pages, as the build has them
  const pyodide = await loadPyodide({ indexURL: new URL('../pyodide/', self.location.href).href })
  const engine = installEngine(pyodide).Engine()
  self.onmessage = (event: MessageEvent<string>) => {
    // a command that fails is dropped, the tree playing on, as twinky's server drops it
    try {
      engine.command(event.data)
    } catch (e) {
      console.error(e)
    }
  }
  post(engine.layout)
  const frame = engine.frame
  engine.init()
  let next = Date.now() / 1000 + frame
  const tick = () => {
    try {
      post(frameMessage(engine.step()))
      const state = engine.changed_state()
      if (state !== undefined) post(state)
    } catch (e) {
      return fail(e)
    }
    // as twinky's wait_for: on to the next frame, or once more than a frame late, a frame from now
    const now = Date.now() / 1000
    const delay = next - now
    next = delay < -frame ? now + frame : next + frame
    setTimeout(tick, Math.max(delay, 0) * 1000)
  }
  tick()
} catch (e) {
  fail(e)
}
