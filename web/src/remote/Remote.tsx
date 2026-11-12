import { useCallback, useEffect, useRef, useState } from 'react'
import { cardControls, stepped, type State } from './remote'
import Ring from './Ring'

const MARKS = { '?': 'not saved', '!': 'saved', '*': 'changed' }

type Command = { command: string } & Record<string, string | number>
// the option list open: a feature's control, by its visible index
type Picking = { feature: number; control: number }

/** The remote, the Stack: the patterns along the top, the pattern's features as cards and the spin ring
 * in one scroll, and the thumb bar along the bottom. Every change is one of the TUI's commands, sent to
 * twinky, which answers with its state. */
export default function Remote() {
  const [state, setState] = useState<State | null>(null)
  const [time, setTime] = useState('')
  const [connected, setConnected] = useState(false)
  // the open card, for the pattern it was opened on: on another pattern the first card is open
  const [open, setOpen] = useState<{ pattern: string; feature: number | null }>({ pattern: '', feature: 0 })
  const [picking, setPicking] = useState<Picking | null>(null)
  // a stepper's pick shown at once, until twinky's next state says what it is
  const [stepping, setStepping] = useState<Record<string, number>>({})
  const [awake, setAwake] = useState(true)
  const socket = useRef<WebSocket | null>(null)
  const chips = useRef<HTMLElement | null>(null)

  // twinky's socket: its state and time in, the commands out, and again a second after it drops
  useEffect(() => {
    let retry = 0
    const connect = () => {
      const ws = new WebSocket(`ws://${location.host}/ws?remote`)
      socket.current = ws
      ws.onopen = () => setConnected(true)
      ws.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as { state: State } | { time: string }
        if ('state' in message) {
          setState(message.state)
          setStepping({})
        } else {
          setTime(message.time)
        }
      }
      ws.onclose = () => {
        setConnected(false)
        retry = window.setTimeout(connect, 1000)
      }
    }
    connect()
    return () => {
      window.clearTimeout(retry)
      if (socket.current) socket.current.onclose = null
      socket.current?.close()
      socket.current = null
    }
  }, [])

  // the screen kept on while the page is in view, asked again each time it comes back
  useEffect(() => {
    if (!('wakeLock' in navigator)) {
      setAwake(false)
      return
    }
    let lock: WakeLockSentinel | null = null
    let gone = false
    const ask = async () => {
      if (document.visibilityState !== 'visible') return
      try {
        lock = await navigator.wakeLock.request('screen')
        if (gone) void lock.release()
        setAwake(true)
      } catch {
        setAwake(false)
      }
    }
    void ask()
    document.addEventListener('visibilitychange', ask)
    return () => {
      gone = true
      document.removeEventListener('visibilitychange', ask)
      void lock?.release()
    }
  }, [])

  // the pattern on show's chip scrolled into the row
  const onShow = state?.pattern
  useEffect(() => {
    chips.current?.querySelector('[aria-pressed=true]')?.scrollIntoView({ inline: 'center', block: 'nearest' })
  }, [onShow])

  const send = useCallback((command: Command) => {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify(command))
  }, [])

  if (!state) {
    return <main className="remote waiting">{connected ? 'waiting for twinky' : 'connecting to twinky'}</main>
  }

  const music = state.features.length - 1
  const openFeature = open.pattern === state.pattern ? open.feature : 0
  const opened = openFeature === null ? null : state.features[openFeature]
  const pattern = state.pattern
  const step = (feature: number, control: number, by: number) => {
    navigator.vibrate(10)
    const key = `${feature}:${control}`
    const c = state.features[feature].controls[control]
    setStepping((s) => ({ ...s, [key]: stepped(s[key] ?? c.pick, by, c.options.length) }))
    send({ command: 'change', pattern, feature, control, step: by })
  }
  const pickingControl = picking && state.features[picking.feature].controls[picking.control]

  return (
    <main className="remote">
      <header>
        <div className="title">
          <h1>{state.pattern}</h1>
          {state.to ? (
            <span className="to">to {state.to}</span>
          ) : (
            <span className={`mark mark-${MARKS[state.mark].replace(' ', '-')}`}>{MARKS[state.mark]}</span>
          )}
          <span className="time">{time}</span>
        </div>
        {!connected && <div className="status">twinky stopped: reconnecting</div>}
        {!awake && <div className="status">the screen may sleep: Chrome needs twinky's address as secure</div>}
        <nav className="chips" aria-label="Patterns" ref={chips}>
          {state.patterns.map((name, i) => (
            <button
              key={name}
              aria-pressed={name === state.pattern}
              className={name === state.to ? 'next' : undefined}
              onClick={() => send({ command: 'switch', to: i })}
            >
              {name}
            </button>
          ))}
        </nav>
      </header>

      {state.features.map((feature, f) => {
        const isOpen = f === openFeature
        return (
          <section key={feature.name} className={`card${isOpen ? ' open' : ''}`}>
            <div className="card-header">
              <button
                className="card-name"
                aria-expanded={isOpen}
                onClick={() => setOpen({ pattern: state.pattern, feature: isOpen ? null : f })}
              >
                {feature.name}
              </button>
              {feature.on !== null && (
                <button
                  className="switch"
                  role="switch"
                  aria-checked={feature.on}
                  aria-label={`${feature.name} on`}
                  onClick={() => send({ command: 'set', pattern, feature: f, control: 0, option: feature.on ? 1 : 0 })}
                >
                  <span />
                </button>
              )}
            </div>
            {isOpen &&
              cardControls(feature).map(({ control, index }) => {
                const pick = stepping[`${f}:${index}`] ?? control.pick
                return (
                  <div className="stepper" key={control.name}>
                    <button aria-label={`${control.name} down`} onClick={() => step(f, index, -1)}>
                      −
                    </button>
                    <button className="value" onClick={() => setPicking({ feature: f, control: index })}>
                      <span className="control">{control.name}:</span> {control.options[pick]}
                    </button>
                    <button aria-label={`${control.name} up`} onClick={() => step(f, index, 1)}>
                      +
                    </button>
                  </div>
                )
              })}
          </section>
        )
      })}

      <Ring turn={state.ring} send={(angle) => send({ command: 'spin', angle })} />

      <footer className="thumbs">
        <button onClick={() => send({ command: 'random' })}>
          Random<small>new pattern</small>
        </button>
        <button
          onClick={() =>
            send(
              openFeature === null ? { command: 'randomize' } : { command: 'randomize', pattern, feature: openFeature },
            )
          }
        >
          Shuffle<small>{opened ? opened.name : 'whole pattern'}</small>
        </button>
        <button aria-pressed={state.paused} onClick={() => send({ command: 'pause' })}>
          {state.paused ? 'Paused' : 'Pause'}
          <small>auto change</small>
        </button>
        <button onClick={() => send({ command: openFeature === music ? 'save music' : 'save' })}>
          Save<small>{openFeature === music ? 'Music' : 'pattern'}</small>
        </button>
      </footer>

      {picking && pickingControl && (
        <div className="sheet-backdrop" onClick={() => setPicking(null)}>
          <div className="sheet" role="dialog" aria-label={pickingControl.name} onClick={(e) => e.stopPropagation()}>
            <h2>{pickingControl.name}</h2>
            <ul>
              {pickingControl.options.map((option, o) => (
                <li key={option}>
                  <button
                    aria-pressed={o === pickingControl.pick}
                    onClick={() => {
                      send({ command: 'set', pattern, feature: picking.feature, control: picking.control, option: o })
                      setPicking(null)
                    }}
                  >
                    {option}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </main>
  )
}
