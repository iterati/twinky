import Pin from './remote/Pin'
import type { State } from './remote/remote'
import Walk from './remote/Walk'

/** The simulated tree's picker and knobs: twinky's patterns, the remote's Walk card, and the one on
 * show's features with their pins and visible controls, each change one of the remote's commands. Music
 * is left out, as the simulated tree plays without it. */
export default function Simulated({ state, send }: { state: State; send: (message: string) => void }) {
  const { pattern } = state
  const features = state.features.slice(0, -1)
  return (
    <section className="simulated" aria-label="Simulated tree">
      <select
        value={state.patterns.indexOf(pattern)}
        onChange={(e) => send(JSON.stringify({ command: 'switch', to: Number(e.target.value) }))}
        aria-label="Pattern"
      >
        {state.patterns.map((name, i) => (
          <option key={name} value={i}>
            {name}
          </option>
        ))}
      </select>
      {state.to && <div className="to">changing to {state.to}</div>}
      <Walk walk={state.walk} paused={state.paused} send={(command) => send(JSON.stringify(command))} />
      {features.map((feature, f) => (
        <fieldset key={`${pattern} ${feature.name}`}>
          <legend>
            {feature.name}
            <Pin
              name={feature.name}
              pinned={state.walk.pins.includes(f)}
              onClick={() => send(JSON.stringify({ command: 'pin', pattern, feature: f }))}
            />
          </legend>
          {feature.controls.map((c, i) => (
            <label key={c.name}>
              <span>{c.name}</span>
              <select
                value={c.pick}
                onChange={(e) =>
                  send(
                    JSON.stringify({
                      command: 'set',
                      pattern,
                      feature: f,
                      control: i,
                      name: c.name,
                      option: Number(e.target.value),
                    }),
                  )
                }
              >
                {c.options.map((option, o) => (
                  <option key={o} value={o}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </fieldset>
      ))}
    </section>
  )
}
