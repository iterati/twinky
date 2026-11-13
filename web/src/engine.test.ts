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

// the heaviest effect, the Lava lamp, held at its hottest: the mean seconds of its frames, rendered
// and written as the page's engine does them
const LAVA = `
import random, time
from core import FRAME, Blender
from effects import EffectPattern, Heartbeat, LavaLamp
from sim import SimLights
random.seed(7)
lamp = EffectPattern(LavaLamp())
heat = next(sweep for sweep in lamp.features[0].sweeps if sweep.control.name == "Heat")
heat.curved.set(1)
lamp.update(set_dirty=False)
b = Blender([lamp, EffectPattern(Heartbeat())], SimLights(), 0, False)
b.init(0.0)
start = time.perf_counter()
for k in range(${STEPS}):
    b.write(b.render(k * FRAME))
(time.perf_counter() - start) / ${STEPS}
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

  // the pattern twinky starts on, a pattern switched to, the three hints, an effect and the heaviest
  it.each([
    ['Basic Bitch', undefined],
    ['Galaxus', 5],
    ['Wash', 10],
    ['Slices', 11],
    ['Hidden Field', 12],
    ['Fireworks', 15],
    ['Lava lamp', 17],
  ])('plays %s frame for frame as twinky --sim does', { timeout: 60_000 }, (name, to) => {
    pyodide.runPython('import random\nrandom.seed(7)')
    const engine = browser.Engine()
    engine.init(T0)
    if (to !== undefined) engine.command(JSON.stringify({ command: 'switch', to }))
    const hash = createHash('sha256')
    let last = new Uint8Array()
    for (let k = 0; k < STEPS; k++) {
      last = new Uint8Array(frameMessage(engine.step(T0 + k * engine.frame)))
      hash.update(last)
    }
    expect(JSON.parse(engine.changed_state()!).state.pattern).toBe(name)
    expect(hash.digest('hex')).toBe(sim(7, to))
    // the last frame, the pattern alone once a change has run, lights the tree
    expect(last.subarray(4).some((byte) => byte > 0)).toBe(true)
    engine.destroy()
  })

  it('renders the Lava lamp at its hottest within a frame', { timeout: 60_000 }, () => {
    const engine = browser.Engine()
    expect(pyodide.runPython(LAVA) as number).toBeLessThan(engine.frame)
    engine.destroy()
  })
})
