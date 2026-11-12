import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { loadPyodide, type PyodideInterface } from 'pyodide'
import { beforeAll, describe, expect, it } from 'vitest'
import { frameMessage, installEngine } from './engine'

const REPO = fileURLToPath(new URL('../..', import.meta.url))
const T0 = 1000
const STEPS = 112

// twinky --sim's frames from T0 on its animation thread's clock, by CPython in the repo's venv
const SIM = `
import hashlib, random, sys
import commands, twinky
from core import FRAME
from wire import frame_message
seed, steps = int(sys.argv[1]), int(sys.argv[2])
to = int(sys.argv[3]) if len(sys.argv) > 3 else None
random.seed(seed)
animation = commands.start(twinky.open_lights(twinky.parse_args(["--sim"])))
sent = []
animation.on_frame = sent.append
animation.init(${T0})
if to is not None:
    commands.remote_command({"command": "switch", "to": to})(animation)
for k in range(steps):
    animation.write(animation.render(${T0} + k * FRAME))
print(hashlib.sha256(b"".join(frame_message(n, f) for n, f in enumerate(sent))).hexdigest())
`

function sim(seed: number, to?: number): string {
  const args = ['-c', SIM, String(seed), String(STEPS), ...(to === undefined ? [] : [String(to)])]
  return execFileSync(`${REPO}/.venv/bin/python`, args, { cwd: REPO, encoding: 'utf8' }).trim()
}

describe('the page engine', () => {
  let pyodide: PyodideInterface
  let browser: ReturnType<typeof installEngine>

  beforeAll(async () => {
    pyodide = await loadPyodide()
    browser = installEngine(pyodide)
  }, 60_000)

  // the pattern twinky starts on, a pattern switched to and an effect
  it.each([
    ['Basic Bitch', undefined],
    ['Galaxus', 5],
    ['Fireworks', 18],
  ])('plays %s frame for frame as twinky --sim does', { timeout: 60_000 }, (name, to) => {
    pyodide.runPython('import random\nrandom.seed(7)')
    const engine = browser.Engine()
    engine.init(T0)
    if (to !== undefined) engine.command(JSON.stringify({ command: 'switch', to }))
    const hash = createHash('sha256')
    for (let k = 0; k < STEPS; k++) hash.update(new Uint8Array(frameMessage(engine.step(T0 + k * engine.frame))))
    expect(JSON.parse(engine.changed_state()!).state.pattern).toBe(name)
    expect(hash.digest('hex')).toBe(sim(7, to))
    engine.destroy()
  })
})
