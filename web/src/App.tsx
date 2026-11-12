import { useCallback, useEffect, useRef, useState } from 'react'
import { decodeFrame, type Layout } from './frame'
import Listen from './Listen'
import Tree, { type View } from './Tree'

export default function App() {
  const [layout, setLayout] = useState<Layout | null>(null)
  const [view, setView] = useState<View>('3d')
  const [closed, setClosed] = useState(false)
  // R, G, B a light, written as each frame comes and drawn on the next animation frame
  const colors = useRef(new Float32Array(0))
  const socket = useRef<WebSocket | null>(null)

  // twinky's socket, the page's one link to it: the layout and frames in, the music out
  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws`)
    socket.current = ws
    ws.binaryType = 'arraybuffer'
    ws.onmessage = (event: MessageEvent<string | ArrayBuffer>) => {
      if (typeof event.data === 'string') {
        const lights = (JSON.parse(event.data) as { layout: Layout }).layout
        colors.current = new Float32Array(lights.length * 3)
        setLayout(lights)
      } else {
        decodeFrame(event.data, colors.current)
      }
    }
    ws.onclose = () => setClosed(true)
    return () => {
      ws.onclose = null
      ws.close()
      socket.current = null
    }
  }, [])

  const send = useCallback((message: string) => {
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(message)
  }, [])

  return (
    <>
      {layout && <Tree layout={layout} colors={colors} view={view} />}
      <header>
        <span className="name">twinky</span>
        {closed ? (
          <span className="status">twinky stopped: reload once it runs again</span>
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
      <Listen send={send} />
    </>
  )
}
