import { useEffect, useRef, useState } from 'react'
import { decodeFrame, type Layout } from './frame'
import Tree, { type View } from './Tree'

export default function App() {
  const [layout, setLayout] = useState<Layout | null>(null)
  const [view, setView] = useState<View>('3d')
  const [closed, setClosed] = useState(false)
  // R, G, B a light, written as each frame comes and drawn on the next animation frame
  const colors = useRef(new Float32Array(0))

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws`)
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
    }
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
    </>
  )
}
