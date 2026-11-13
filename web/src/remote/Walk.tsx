import { useState } from 'react'
import type { Command, Walk as WalkState } from './remote'
import Stepper from './Stepper'

/** The walk's card: its On switch (Pause's, the other way round), Pace and Reach as steppers, Stay as a
 * switch, and Back and Nudge, each one of twinky's commands. The remote shows it after Music, the
 * simulator page in its knobs panel. */
export default function Walk({
  walk,
  paused,
  send,
}: {
  walk: WalkState
  paused: boolean
  send: (command: Command) => void
}) {
  const [open, setOpen] = useState(true)
  return (
    <section className={`card walk${open ? ' open' : ''}`} aria-label="Walk">
      <div className="card-header">
        <button className="card-name" aria-expanded={open} onClick={() => setOpen(!open)}>
          Walk
        </button>
        <button
          className="switch"
          role="switch"
          aria-checked={!paused}
          aria-label="Walk On"
          onClick={() => send({ command: 'pause' })}
        >
          <span />
        </button>
      </div>
      {open && (
        <>
          <Stepper
            name="Pace"
            value={walk.pace.options[walk.pace.pick]}
            onStep={(step) => send({ command: 'pace', step })}
          />
          <Stepper
            name="Reach"
            value={walk.reach.options[walk.reach.pick]}
            onStep={(step) => send({ command: 'reach', step })}
          />
          <div className="walk-stay">
            <span>Stay on this pattern</span>
            <button
              className="switch"
              role="switch"
              aria-checked={walk.stay}
              aria-label="Walk Stay"
              onClick={() => send({ command: 'stay' })}
            >
              <span />
            </button>
          </div>
          <div className="walk-steps">
            <button disabled={!walk.back} onClick={() => send({ command: 'back' })}>
              Back
            </button>
            <button onClick={() => send({ command: 'nudge' })}>Nudge</button>
          </div>
        </>
      )}
    </section>
  )
}
