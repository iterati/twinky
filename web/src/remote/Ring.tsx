import { useRef, useState, type PointerEvent } from 'react'
import { knob, ringTurn } from './remote'

const SIZE = 260
const R = 100
const CENTER = { x: SIZE / 2, y: SIZE / 2 }
// twinky takes a command a frame, 16 a second, so a drag sends fewer
const SEND_EVERY = 80

/** The spin ring: drag round it and the tree turns with the finger, live, staying where it's let go.
 * Its bottom is the side of the tree nearest him. */
export default function Ring({ turn, send }: { turn: number; send: (angle: number) => void }) {
  // the turn and the last point while dragging, in the ring's own units
  const [drag, setDrag] = useState<{ turn: number; at: { x: number; y: number } } | null>(null)
  const sent = useRef(0)

  const point = (e: PointerEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect()
    return { x: ((e.clientX - box.left) * SIZE) / box.width, y: ((e.clientY - box.top) * SIZE) / box.height }
  }
  const shown = drag ? drag.turn : turn
  const at = knob(shown, CENTER, R)
  const degrees = Math.round((((-shown % 1) + 1) % 1) * 360) % 360

  return (
    <section className="card ring">
      <div className="card-header">
        <span className="card-name">Spin ring</span>
        <span className="degrees">{degrees}°</span>
      </div>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="slider"
        aria-label="Spin ring"
        aria-valuemin={0}
        aria-valuemax={359}
        aria-valuenow={degrees}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId)
          setDrag({ turn, at: point(e) })
        }}
        onPointerMove={(e) => {
          if (!drag) return
          const to = point(e)
          const next = ringTurn(drag.turn, CENTER, drag.at, to)
          setDrag({ turn: next, at: to })
          if (e.timeStamp - sent.current >= SEND_EVERY) {
            sent.current = e.timeStamp
            send(next)
          }
        }}
        onPointerUp={() => {
          if (drag) send(drag.turn)
          setDrag(null)
        }}
        onPointerCancel={() => {
          if (drag) send(drag.turn)
          setDrag(null)
        }}
      >
        <circle className="track" cx={CENTER.x} cy={CENTER.y} r={R} />
        <circle className="home" cx={CENTER.x} cy={CENTER.y + R + 22} r={4} />
        <text x={CENTER.x} y={CENTER.y} dominantBaseline="middle" textAnchor="middle">
          drag round
        </text>
        <circle className="knob" cx={at.x} cy={at.y} r={22} />
      </svg>
    </section>
  )
}
