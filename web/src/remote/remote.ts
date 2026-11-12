// What twinky sends the remote at /ws?remote, and the remote's own sums

export type Control = {
  name: string
  options: string[]
  pick: number // its option's index
}

export type Feature = {
  name: string
  switch: number | null // its On switch's index in controls, null with none
  controls: Control[] // the visible ones
}

export type State = {
  patterns: string[]
  pattern: string
  mark: '?' | '!' | '*' // not saved, saved, changed since
  to: string | null // the pattern a change is running to
  features: Feature[] // the pattern's, then Music
  paused: boolean
  ring: number // the spin ring's turn, in turns
}

/** A card's stepper rows: its visible controls but the switch on its header, each with its index among
 * the visible ones, as twinky's commands count them. */
export function cardControls(feature: Feature): { control: Control; index: number }[] {
  return feature.controls.map((control, index) => ({ control, index })).filter(({ index }) => index !== feature.switch)
}

/** The pick a minus (-1) or plus (+1) gives, wrapping round its options as twinky's do. */
export function stepped(pick: number, step: number, count: number): number {
  return (((pick + step) % count) + count) % count
}

type Point = { x: number; y: number }

// On the screen, y down: the ring's 0 is at the bottom, the side nearest him, and a turn clockwise on
// the screen turns the tree clockwise seen from above, as twinky's angle round the trunk falls
const HOME = Math.PI / 2

/** Where the knob sits on a ring of radius r round center for a turn of the tree. */
export function knob(turn: number, center: Point, r: number): Point {
  const a = HOME - turn * 2 * Math.PI
  return { x: center.x + r * Math.cos(a), y: center.y + r * Math.sin(a) }
}

/** The turn after a drag round center from one point to the next: as far round as the finger went, the
 * short way, so the tree follows it past the seam and round again. */
export function ringTurn(turn: number, center: Point, from: Point, to: Point): number {
  const swept = Math.atan2(to.y - center.y, to.x - center.x) - Math.atan2(from.y - center.y, from.x - center.x)
  const short = ((((swept + Math.PI) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) - Math.PI
  return turn - short / (2 * Math.PI)
}
