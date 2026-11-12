import { describe, expect, it } from 'vitest'
import { cardControls, knob, ringTurn, stepped, type Feature } from './remote'

function feature(on: boolean | null, names: string[]): Feature {
  return { name: 'Flicker', on, controls: names.map((name) => ({ name, options: ['a', 'b'], pick: 0 })) }
}

describe('cardControls', () => {
  it('leaves the On switch to the header, keeping each control its visible index', () => {
    const rows = cardControls(feature(true, ['Enabled', 'Start', 'Curved']))
    expect(rows.map(({ control, index }) => [control.name, index])).toEqual([
      ['Start', 1],
      ['Curved', 2],
    ])
  })

  it('shows no rows for a feature switched off', () => {
    expect(cardControls(feature(false, ['Enabled']))).toEqual([])
  })

  it('shows every control of a feature with no switch', () => {
    expect(cardControls(feature(null, ['Transition', 'Grain'])).map(({ index }) => index)).toEqual([0, 1])
  })
})

describe('stepped', () => {
  it('wraps round the options both ways', () => {
    expect(stepped(0, -1, 4)).toBe(3)
    expect(stepped(3, 1, 4)).toBe(0)
    expect(stepped(1, 1, 4)).toBe(2)
    expect(stepped(0, 1, 1)).toBe(0)
  })
})

describe('ringTurn', () => {
  const center = { x: 100, y: 100 }

  it('turns the tree back a quarter for a quarter clockwise on the screen', () => {
    // right to bottom, with y down
    expect(ringTurn(0, center, { x: 180, y: 100 }, { x: 100, y: 180 })).toBeCloseTo(-0.25)
    expect(ringTurn(0.5, center, { x: 100, y: 180 }, { x: 180, y: 100 })).toBeCloseTo(0.75)
  })

  it('goes the short way past the seam, and keeps counting round', () => {
    // just above the left to just below it: a sliver anticlockwise, not most of a turn
    const turn = ringTurn(2, center, { x: 20, y: 99 }, { x: 20, y: 101 })
    expect(turn).toBeGreaterThan(2)
    expect(turn).toBeLessThan(2.01)
  })

  it('keeps the knob under the finger', () => {
    for (const start of [0, 0.3, -1.2]) {
      const finger = { x: 30, y: 60 }
      const at = knob(ringTurn(start, center, knob(start, center, 80), finger), center, 80)
      const direction = Math.atan2(finger.y - center.y, finger.x - center.x)
      expect(Math.atan2(at.y - center.y, at.x - center.x)).toBeCloseTo(direction)
    }
  })

  it('puts the knob at the bottom at home', () => {
    const at = knob(0, center, 80)
    expect(at.x).toBeCloseTo(100)
    expect(at.y).toBeCloseTo(180)
  })
})
