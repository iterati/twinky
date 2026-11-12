import { useCallback, useEffect, useRef, useState } from 'react'
import { decodeFrame, type Layout } from './frame'
import Listen from './Listen'
import type { State } from './remote/remote'
import Simulated from './Simulated'
import Tree, { type View } from './Tree'

// Once twinky drops, how long it has to come back before the page simulates the tree, and how often
// the page tries for it meanwhile; and while simulating, how often it looks for twinky again
const COME_BACK = 3000
const RETRY = 1000
const LOOK_AGAIN = 5000

// connecting on load; live while twinky answers; dropped while it may come back; simulated, twinky's
// engine running in the page
type Mode = 'connecting' | 'live' | 'dropped' | 'simulated'

export default function App() {
  const [layout, setLayout] = useState<Layout | null>(null)
  const [view, setView] = useState<View>('3d')
  const [mode, setMode] = useState<Mode>('connecting')
  // the simulated tree's state, as the remote gets it, and its engine's failure
  const [state, setState] = useState<State | null>(null)
  const [error, setError] = useState<string | null>(null)
  // R, G, B a light, written as each frame comes and drawn on the next animation frame
  const colors = useRef(new Float32Array(0))
  // where the page's messages go: twinky's socket, or the simulated tree
  const link = useRef<((message: string) => void) | null>(null)

  // twinky's socket, the page's one link to it: the layout and frames in, the music out. With no
  // twinky, its engine in a worker sends the same messages, and takes the remote's commands
  useEffect(() => {
    let socket: WebSocket | null = null
    let worker: Worker | null = null
    let timer: ReturnType<typeof setTimeout> | undefined
    let dropped: number | null = null // when twinky went, while it may come back
    // a page from the site, over HTTPS, has no twinky to find
    const local = location.protocol !== 'https:'

    const receive = (event: MessageEvent<string | ArrayBuffer>) => {
      if (typeof event.data !== 'string') {
        decodeFrame(event.data, colors.current)
        return
      }
      const message = JSON.parse(event.data) as { layout?: Layout; state?: State; error?: string }
      if (message.layout) {
        colors.current = new Float32Array(message.layout.length * 3)
        setLayout(message.layout)
      }
      if (message.state) setState(message.state)
      if (message.error) setError(message.error)
    }

    const simulate = () => {
      const w = new Worker(new URL('./engine.worker.ts', import.meta.url), { type: 'module' })
      w.onmessage = receive
      // a worker that never loads
      w.onerror = (event) => setError(event.message || 'the engine did not load')
      worker = w
      link.current = (message) => w.postMessage(message)
      setMode('simulated')
    }

    const live = (ws: WebSocket) => {
      worker?.terminate()
      worker = null
      dropped = null
      socket = ws
      link.current = (message) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(message)
      }
      setState(null)
      setError(null)
      setMode('live')
    }

    // a try no twinky answered
    const unanswered = () => {
      if (worker) {
        if (local) timer = setTimeout(connect, LOOK_AGAIN)
      } else if (dropped !== null && Date.now() - dropped < COME_BACK) {
        timer = setTimeout(connect, RETRY)
      } else {
        simulate()
        if (local) timer = setTimeout(connect, LOOK_AGAIN)
      }
    }

    const connect = () => {
      const ws = new WebSocket(`ws://${location.host}/ws`)
      socket = ws
      ws.binaryType = 'arraybuffer'
      let answered = false
      ws.onmessage = (event: MessageEvent<string | ArrayBuffer>) => {
        if (!answered) {
          answered = true
          live(ws)
        }
        receive(event)
      }
      ws.onclose = () => {
        socket = null
        if (!answered) return unanswered()
        dropped = Date.now()
        link.current = null
        setMode('dropped')
        timer = setTimeout(connect, RETRY)
      }
    }

    if (local) connect()
    else simulate()
    return () => {
      clearTimeout(timer)
      worker?.terminate()
      if (socket) {
        socket.onclose = null
        socket.close()
      }
      link.current = null
    }
  }, [])

  const send = useCallback((message: string) => link.current?.(message), [])

  return (
    <>
      {layout && <Tree layout={layout} colors={colors} view={view} />}
      <header>
        <span className="name">twinky</span>
        {mode === 'simulated' ? (
          <span className="status">
            Simulated tree: no twinky.py answered. Run twinky.py to play your tree live.
            {error ? ` It failed: ${error}` : !layout && ' Starting it.'}
          </span>
        ) : mode === 'dropped' ? (
          <span className="status">twinky stopped: waiting for it to come back</span>
        ) : (
          !layout && <span className="status">connecting</span>
        )}
        <div className="views" role="group" aria-label="View">
          <button aria-pressed={view === '3d'} onClick={() => setView('3d')}>
            3D
          </button>
          <button aria-pressed={view === 'unrolled'} onClick={() => setView('unrolled')}>
            Unrolled
          </button>
        </div>
      </header>
      {mode === 'simulated' && state && <Simulated state={state} send={send} />}
      {mode === 'simulated' ? (
        <section className="listen">Listening needs twinky.py: the simulated tree plays without music.</section>
      ) : (
        <Listen send={send} />
      )}
    </>
  )
}
